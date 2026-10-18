"""Stage 2 APIs. All technician-facing source reads share an approval gate."""

import hashlib
import json
import secrets
import time
from pathlib import Path
from typing import Annotated, Literal
from urllib.parse import quote

from fastapi import (
    APIRouter,
    Depends,
    File,
    Form,
    HTTPException,
    Request,
    Response,
    UploadFile,
)
from pydantic import BaseModel, ConfigDict, Field, ValidationError

from app.storage.capture_schema import Submission, SubmissionFields, mapped_submission
from app.storage.database import connect
from app.storage.backend import is_postgres
from starlette.concurrency import run_in_threadpool
from app.storage.security import hash_password, now, token_hash, verify_password

router = APIRouter()
DUMMY_PASSWORD_HASH = hash_password(secrets.token_urlsafe(24))
COOKIE = "shift_session"


def database(request: Request):
    if request.app.state.settings.storage_backend == "postgres":
        yield request.app.state.storage
        return
    with connect(request.app.state.settings.database_path) as db:
        yield db


def current_user(request: Request, db=Depends(database, scope="function")):
    token = request.cookies.get(COOKIE, "")
    if is_postgres(db):
        return db.current_user(token)
    user = db.execute(
        "SELECT u.* FROM users u JOIN sessions s ON s.user_id=u.id WHERE s.token_hash=? AND s.expires_at>?",
        (token_hash(token), int(time.time())),
    ).fetchone()
    if not user:
        raise HTTPException(401, "Sign in to continue")
    return dict(user)


def supervisor(user=Depends(current_user, scope="function")):
    if user["role"] != "supervisor":
        raise HTTPException(403, "Supervisor access required")
    return user


def public_user(user):
    return {key: user[key] for key in ("id", "username", "name", "role")}


class Login(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=False)
    username: str = Field(min_length=1, max_length=100)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def login(
    body: Login,
    request: Request,
    response: Response,
    db=Depends(database, scope="function"),
):
    timestamp = int(time.time())
    key = f"{request.client.host if request.client else 'local'}:{body.username.strip().lower()}"
    if is_postgres(db):
        seconds = request.app.state.settings.session_hours * 3600
        user, token = db.login(
            body.username, body.password, key, request.cookies.get(COOKIE, ""), seconds
        )
        return session_response(request, response, user, token, seconds)
    db.execute("DELETE FROM login_attempts WHERE attempted_at<?", (timestamp - 900,))
    if (
        db.execute(
            "SELECT count(*) FROM login_attempts WHERE key=?", (key,)
        ).fetchone()[0]
        >= 5
    ):
        db.commit()
        raise HTTPException(429, "Too many attempts. Try again in 15 minutes.")
    user = db.execute(
        "SELECT * FROM users WHERE username=?", (body.username.strip().lower(),)
    ).fetchone()
    valid = verify_password(
        body.password, user["password_hash"] if user else DUMMY_PASSWORD_HASH
    )
    if not user or not valid:
        db.execute("INSERT INTO login_attempts VALUES (?,?)", (key, timestamp))
        db.commit()
        raise HTTPException(401, "Invalid username or password")
    db.execute("DELETE FROM login_attempts WHERE key=?", (key,))
    db.execute(
        "DELETE FROM sessions WHERE expires_at<=? OR token_hash=?",
        (timestamp, token_hash(request.cookies.get(COOKIE, ""))),
    )
    token = secrets.token_urlsafe(32)
    seconds = request.app.state.settings.session_hours * 3600
    db.execute(
        "INSERT INTO sessions VALUES (?,?,?)",
        (token_hash(token), user["id"], timestamp + seconds),
    )
    return session_response(request, response, user, token, seconds)


def session_response(request, response, user, token, seconds):
    response.set_cookie(
        COOKIE,
        token,
        max_age=seconds,
        httponly=True,
        samesite="lax",
        secure=request.app.state.settings.environment == "production",
        path="/",
    )
    return public_user(user)


@router.get("/auth/me")
def me(user=Depends(current_user, scope="function")):
    return public_user(user)


@router.post("/auth/logout", status_code=204)
def logout(
    request: Request, response: Response, db=Depends(database, scope="function")
):
    if is_postgres(db):
        db.logout(request.cookies.get(COOKIE, ""))
        response.delete_cookie(COOKIE, path="/")
        return
    db.execute(
        "DELETE FROM sessions WHERE token_hash=?",
        (token_hash(request.cookies.get(COOKIE, "")),),
    )
    response.delete_cookie(COOKIE, path="/")


@router.get("/machines")
def machines(
    user=Depends(current_user, scope="function"), db=Depends(database, scope="function")
):
    if is_postgres(db):
        return db.machines()
    return [
        json.loads(r["data"])
        for r in db.execute("SELECT data FROM machines ORDER BY id")
    ]


# Latest submitted version is authoritative. An edit immediately withdraws the old
# version from technician reads until the new version receives review.
LATEST = "v.revision=(SELECT MAX(v2.revision) FROM knowledge_versions v2 WHERE v2.record_id=v.record_id)"


def serialize(db, row):
    r = dict(row)
    review = db.execute(
        "SELECT * FROM review_events WHERE version_id=? ORDER BY id DESC LIMIT 1",
        (r["id"],),
    ).fetchone()
    attachments = [
        dict(a)
        for a in db.execute(
            "SELECT id,name,size,media_type AS type,sha256 FROM source_documents WHERE version_id=?",
            (r["id"],),
        )
    ]
    ai = db.execute(
        "SELECT * FROM capture_ai_runs WHERE version_id=?", (r["id"],)
    ).fetchone()
    return serialize_record(r, review, attachments, ai)


def json_value(value):
    return json.loads(value) if isinstance(value, str) else value


def serialize_record(r, review, attachments, ai):
    """Shared public representation, independent of storage JSON codecs."""
    return dict(
        aiCapture={
            "runId": ai["id"],
            "execution": json_value(ai["execution"]),
            "original": json_value(ai["original_submission"]),
            "fields": json_value(ai["reviewed_structure"]),
        }
        if ai
        else None,
        id=r["record_id"],
        versionId=r["id"],
        revision=r["revision"],
        machineId=r["machine_id"],
        title=r["title"],
        symptom=r["symptom"],
        content=r["content"],
        kind=r["kind"],
        status=r["status"],
        author=r["author"],
        date=r["created_at"][:10],
        createdAt=r["created_at"],
        problem=r["problem"],
        rootCause=r["root_cause"],
        resolution=r["resolution"],
        safetyNotes=r["safety_notes"],
        attachments=attachments,
        reviewer=review["reviewer_name"] if review else None,
        reviewNote=review["note"] if review else None,
        reviewedAt=review["created_at"] if review else None,
    )


@router.get("/knowledge")
def knowledge(
    q: str = "",
    machine: str = "",
    user=Depends(current_user, scope="function"),
    db=Depends(database, scope="function"),
):
    if is_postgres(db):
        return db.knowledge(machine, q)
    # Do not reuse the privileged submission list for retrieval.
    rows = db.execute(
        f"SELECT v.* FROM knowledge_versions v WHERE {LATEST} AND v.status='Approved' AND (?='' OR v.machine_id=?) AND (?='' OR instr(lower(v.title || ' ' || v.symptom || ' ' || v.content),lower(?))>0) ORDER BY v.created_at DESC",
        (machine, machine, q, q),
    )
    return [serialize(db, r) for r in rows]


@router.get("/submissions")
def submissions(
    user=Depends(current_user, scope="function"), db=Depends(database, scope="function")
):
    if is_postgres(db):
        return db.submissions(user)
    rows = db.execute(
        f"SELECT v.* FROM knowledge_versions v JOIN knowledge_records r ON r.id=v.record_id WHERE {LATEST} AND (?='supervisor' OR r.owner_id=?) ORDER BY v.created_at DESC",
        (user["role"], user["id"]),
    )
    return [serialize(db, r) for r in rows]


async def save_submission(metadata, files, user, db, record_id=None):
    try:
        body = Submission.model_validate_json(metadata)
    except ValidationError:
        raise HTTPException(
            422,
            "Invalid submission fields; title, machine, symptom and observation are required",
        )
    exists = (
        (await run_in_threadpool(db.machine_exists, body.machineId))
        if is_postgres(db)
        else db.execute(
            "SELECT 1 FROM machines WHERE id=?", (body.machineId,)
        ).fetchone()
    )
    if not exists:
        raise HTTPException(422, "Unknown machine")
    if len(files) > 4:
        raise HTTPException(422, "Maximum four attachments including voice recording")
    sources = []
    for f in files:
        name = Path((f.filename or "attachment").replace("\\", "/")).name[:180]
        ext = Path(name).suffix.lower()
        media = f.content_type or "application/octet-stream"
        if ext not in (
            ".pdf",
            ".txt",
            ".md",
            ".webm",
            ".wav",
            ".mp3",
            ".m4a",
            ".ogg",
            ".mp4",
        ):
            raise HTTPException(422, "Unsupported attachment type")
        data = await f.read(10 * 1024 * 1024 + 1)
        if len(data) > 10 * 1024 * 1024 or not data:
            raise HTTPException(422, "Attachments must be nonempty and at most 10 MB")
        sources.append((name, media, data))
    if is_postgres(db):
        return await run_in_threadpool(
            db.save_submission, body, sources, user, record_id
        )
    db.execute("BEGIN IMMEDIATE")
    revision = 1
    timestamp = now()
    if record_id:
        record = db.execute(
            "SELECT * FROM knowledge_records WHERE id=?", (record_id,)
        ).fetchone()
        if not record or (
            record["owner_id"] != user["id"] and user["role"] != "supervisor"
        ):
            raise HTTPException(404, "Submission not found")
        revision = db.execute(
            "SELECT MAX(revision)+1 FROM knowledge_versions WHERE record_id=?",
            (record_id,),
        ).fetchone()[0]
    else:
        record_id = "SUB-" + secrets.token_hex(8).upper()
        db.execute(
            "INSERT INTO knowledge_records VALUES (?,?,?)",
            (record_id, user["id"], timestamp),
        )
    version_id = record_id + f"-v{revision}"
    ai_review = body.aiReview
    if ai_review is not None:
        run = db.execute(
            "SELECT * FROM capture_ai_runs WHERE id=? AND owner_id=?",
            (ai_review.runId, user["id"]),
        ).fetchone()
        if (
            not run
            or run["version_id"]
            or json.loads(run["execution"])["status"] != "success"
        ):
            raise HTTPException(
                422,
                "AI run is unavailable, failed, or already submitted. Discard AI to submit manually.",
            )
        original = SubmissionFields.model_validate(
            body.model_dump(exclude={"aiReview"})
        )
        if original.model_dump() != json.loads(run["original_submission"]):
            raise HTTPException(
                422,
                "Original fields changed after structuring. Discard the AI proposal or structure again.",
            )
        try:
            body = mapped_submission(original, ai_review.fields)
        except ValidationError:
            raise HTTPException(
                422,
                "Reviewed structure exceeds submission limits. Shorten the fields or submit manually.",
            ) from None
    db.execute(
        "INSERT INTO knowledge_versions VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (
            version_id,
            record_id,
            revision,
            body.machineId,
            body.title,
            body.symptom,
            body.content,
            body.kind,
            user["name"],
            user["id"],
            body.problem,
            body.rootCause,
            body.resolution,
            body.safetyNotes,
            "Pending",
            timestamp,
        ),
    )
    if ai_review is not None:
        db.execute(
            "UPDATE capture_ai_runs SET version_id=?,reviewed_structure=? WHERE id=?",
            (version_id, ai_review.fields.model_dump_json(), ai_review.runId),
        )
    for name, media, data in sources:
        db.execute(
            "INSERT INTO source_documents VALUES (?,?,?,?,?,?,?,?)",
            (
                secrets.token_hex(16),
                version_id,
                name,
                media,
                len(data),
                hashlib.sha256(data).hexdigest(),
                data,
                timestamp,
            ),
        )
    return serialize(
        db,
        db.execute(
            "SELECT * FROM knowledge_versions WHERE id=?", (version_id,)
        ).fetchone(),
    )


@router.post("/submissions", status_code=201)
async def submit(
    metadata: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()] = [],
    user=Depends(current_user, scope="function"),
    db=Depends(database, scope="function"),
):
    return await save_submission(metadata, files, user, db)


@router.post("/submissions/{record_id}/revisions", status_code=201)
async def revise(
    record_id: str,
    metadata: Annotated[str, Form()],
    files: Annotated[list[UploadFile], File()] = [],
    user=Depends(current_user, scope="function"),
    db=Depends(database, scope="function"),
):
    return await save_submission(metadata, files, user, db, record_id)


class Review(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)
    versionId: str
    decision: Literal["Approved", "Rejected", "Revoked"]
    note: str = Field(default="", max_length=2000)


@router.post("/submissions/{record_id}/review")
def review(
    record_id: str,
    body: Review,
    user=Depends(supervisor, scope="function"),
    db=Depends(database, scope="function"),
):
    if is_postgres(db):
        return db.review(record_id, body, user)
    db.execute("BEGIN IMMEDIATE")
    row = db.execute(
        f"SELECT v.*,r.owner_id FROM knowledge_versions v JOIN knowledge_records r ON r.id=v.record_id WHERE v.record_id=? AND {LATEST}",
        (record_id,),
    ).fetchone()
    if not row:
        raise HTTPException(404, "Submission not found")
    if row["owner_id"] == user["id"] or row["submitted_by"] == user["id"]:
        raise HTTPException(403, "A different supervisor must review your submission")
    expected = "Approved" if body.decision == "Revoked" else "Pending"
    if row["id"] != body.versionId or row["status"] != expected:
        raise HTTPException(
            409, "This version has changed or was already reviewed. Refresh the queue."
        )
    if body.decision != "Approved" and not body.note:
        raise HTTPException(422, "A reason is required for rejection or revocation")
    db.execute(
        "UPDATE knowledge_versions SET status=? WHERE id=?", (body.decision, row["id"])
    )
    db.execute(
        "INSERT INTO review_events (version_id,reviewer_id,reviewer_name,previous_status,decision,note,created_at) VALUES (?,?,?,?,?,?,?)",
        (
            row["id"],
            user["id"],
            user["name"],
            row["status"],
            body.decision,
            body.note,
            now(),
        ),
    )
    return serialize(
        db,
        db.execute(
            "SELECT * FROM knowledge_versions WHERE id=?", (row["id"],)
        ).fetchone(),
    )


@router.get("/submissions/{record_id}/history")
def history(
    record_id: str,
    user=Depends(current_user, scope="function"),
    db=Depends(database, scope="function"),
):
    if is_postgres(db):
        return db.history(record_id, user)
    row = db.execute(
        "SELECT * FROM knowledge_records WHERE id=?", (record_id,)
    ).fetchone()
    if not row or (row["owner_id"] != user["id"] and user["role"] != "supervisor"):
        raise HTTPException(404, "Submission not found")
    return {
        "versions": [
            serialize(db, r)
            for r in db.execute(
                "SELECT * FROM knowledge_versions WHERE record_id=? ORDER BY revision",
                (record_id,),
            )
        ],
        "reviews": [
            dict(r)
            for r in db.execute(
                "SELECT e.* FROM review_events e JOIN knowledge_versions v ON v.id=e.version_id WHERE v.record_id=? ORDER BY e.id",
                (record_id,),
            )
        ],
    }


@router.get("/documents/{document_id}")
def document(
    document_id: str,
    user=Depends(current_user, scope="function"),
    db=Depends(database, scope="function"),
):
    row = (
        db.document(document_id)
        if is_postgres(db)
        else db.execute(
            f"SELECT d.*,v.status,r.owner_id,({LATEST}) AS latest FROM source_documents d JOIN knowledge_versions v ON v.id=d.version_id JOIN knowledge_records r ON r.id=v.record_id WHERE d.id=?",
            (document_id,),
        ).fetchone()
    )
    if not row or not (
        user["role"] == "supervisor"
        or row["owner_id"] == user["id"]
        or (row["status"] == "Approved" and row["latest"])
    ):
        raise HTTPException(404, "Source not found")
    return Response(
        row["data"],
        media_type="application/octet-stream",
        headers={
            "Content-Disposition": "attachment; filename*=UTF-8''" + quote(row["name"]),
            "X-Content-Type-Options": "nosniff",
        },
    )
