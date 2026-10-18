"""Opt-in PostgreSQL repository; explicit SQL, short units, no SQLite SQL shim.

Phase 2 permits only loopback development databases. The API runtime never
creates schemas, seeds data, provisions users or owns its tables.
"""

import hashlib
import re
import secrets
import time
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta

from fastapi import HTTPException
from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.storage.backend import StorageUnavailable
from app.storage.capture_schema import SubmissionFields, mapped_submission
from app.storage.security import now, token_hash, verify_password

SCHEMA = "shift_private"
LATEST = "v.revision=(SELECT MAX(v2.revision) FROM shift_private.knowledge_versions v2 WHERE v2.record_id=v.record_id)"
ELIGIBLE = f"v.status='Approved' AND {LATEST}"


class PostgresSettings(BaseSettings):
    # PostgreSQL credentials are environment-only, never loaded from .env files.
    model_config = SettingsConfigDict(
        env_prefix="SHIFT_POSTGRES_", env_file=None, hide_input_in_errors=True
    )
    dsn: SecretStr = Field(repr=False, exclude=True)
    pool_max: int = Field(default=4, ge=1, le=4)
    connect_timeout: int = Field(default=5, ge=1, le=10)


def local_connection_parameters(dsn):
    """Reject remote hosts, libpq services/passfiles/overrides before connecting."""
    from psycopg.conninfo import conninfo_to_dict

    try:
        params = conninfo_to_dict(dsn)
    except Exception:
        raise StorageUnavailable("Invalid local PostgreSQL configuration") from None
    allowed = {"host", "port", "dbname", "user", "password", "sslmode"}
    if (
        set(params) - allowed
        or params.get("host") not in ("127.0.0.1", "localhost", "::1")
        or not re.fullmatch(
            r"shift_(?:test|dev)_[a-z0-9_]{1,40}", params.get("dbname", "")
        )
        or not params.get("user")
        or not params.get("password")
        or params.get("sslmode", "disable") != "disable"
        or not params.get("port", "5432").isdigit()
        or not 1 <= int(params.get("port", "5432")) <= 65535
    ):
        raise StorageUnavailable(
            "Phase 2 requires an explicit loopback development database"
        )
    # Pin addresses; never let environment variables override the parsed target.
    params.update(
        hostaddr="::1" if params["host"] == "::1" else "127.0.0.1",
        passfile="/dev/null",
        sslmode="disable",
    )
    return params


class PostgresStore:
    backend = "postgres"

    def __init__(self, settings):
        import psycopg
        from pgvector.psycopg import register_vector
        from psycopg.rows import dict_row
        from psycopg_pool import ConnectionPool

        self._settings = settings
        params = local_connection_parameters(settings.dsn.get_secret_value())
        params.update(
            connect_timeout=settings.connect_timeout,
            application_name="shift-phase2",
            autocommit=True,
            row_factory=dict_row,
            prepare_threshold=None,
        )

        # One direct/session pool per app; explicit open, no import-time connections.
        def configure(conn):
            conn.execute("SET search_path TO pg_catalog, shift_private, extensions")
            conn.execute("SET statement_timeout TO '10s'")
            conn.execute("SET lock_timeout TO '2s'")
            conn.execute("SET idle_in_transaction_session_timeout TO '10s'")
            register_vector(conn)

        self.pool = ConnectionPool(
            kwargs=params,
            min_size=0,
            max_size=settings.pool_max,
            timeout=settings.connect_timeout,
            max_waiting=16,
            configure=configure,
            open=False,
            name="shift-phase2",
        )
        self.pool.open()
        self._driver_error = psycopg.Error

    def close(self):
        self.pool.close()

    @contextmanager
    def connection(self, *, transaction=False):
        from psycopg_pool import PoolClosed, PoolTimeout, TooManyRequests

        try:
            with self.pool.connection() as conn:
                if transaction:
                    with conn.transaction():
                        yield conn
                else:
                    yield conn
        except (self._driver_error, PoolClosed, PoolTimeout, TooManyRequests):
            # No retries of ambiguous commits or external inference.
            raise StorageUnavailable("PostgreSQL operation failed") from None

    def validate(self):
        with self.connection() as conn:
            row = conn.execute(
                "SELECT current_user AS name, r.rolsuper, r.rolbypassrls, r.rolcreaterole, r.rolcreatedb, r.rolreplication, pg_has_role(current_user, 'shift_owner', 'MEMBER') AS owner_member FROM pg_catalog.pg_roles r WHERE r.rolname=current_user"
            ).fetchone()
            if row["name"] != "shift_runtime" or any(
                row[k]
                for k in (
                    "rolsuper",
                    "rolbypassrls",
                    "rolcreaterole",
                    "rolcreatedb",
                    "rolreplication",
                    "owner_member",
                )
            ):
                raise StorageUnavailable(
                    "PostgreSQL requires the restricted runtime role"
                )
            # Validate accessible table shape; startup never runs DDL or seeding.
            conn.execute(
                "SELECT id, username, password_hash, role FROM shift_private.users LIMIT 0"
            )
            conn.execute(
                "SELECT original_submission, execution, reviewed_structure FROM shift_private.capture_ai_runs LIMIT 0"
            )
            conn.execute(
                "SELECT vector::extensions.vector(384) FROM shift_private.chunk_embeddings LIMIT 0"
            )
            conn.execute(
                "SELECT search_vector FROM shift_private.knowledge_chunks LIMIT 0"
            )
            if conn.execute(
                "SELECT has_schema_privilege(current_user, 'shift_private', 'CREATE') AS allowed"
            ).fetchone()["allowed"]:
                raise StorageUnavailable("Runtime must not create schema objects")

    @staticmethod
    def lock(conn, namespace, key):
        # Transaction scoped, stable across processes; no parent-table UPDATE grant.
        conn.execute(
            "SELECT pg_advisory_xact_lock(hashtextextended(%s, 0))",
            (f"shift:{namespace}:{key}",),
        )

    def current_user(self, token):
        with self.connection() as conn:
            user = conn.execute(
                "SELECT u.* FROM shift_private.users u JOIN shift_private.sessions s ON s.user_id=u.id WHERE s.token_hash=%s AND s.expires_at>%s",
                (token_hash(token), int(time.time())),
            ).fetchone()
        if not user:
            raise HTTPException(401, "Sign in to continue")
        return user

    def login(self, username, password, key, previous_token, seconds):
        failure = None
        user = None
        token = None
        with self.connection(transaction=True) as conn:
            self.lock(conn, "login", key)
            timestamp = int(time.time())
            conn.execute(
                "DELETE FROM shift_private.login_attempts WHERE attempted_at<%s",
                (timestamp - 900,),
            )
            attempts = conn.execute(
                "SELECT count(*) AS total FROM shift_private.login_attempts WHERE key=%s",
                (key,),
            ).fetchone()["total"]
            if attempts >= 5:
                failure = HTTPException(
                    429, "Too many attempts. Try again in 15 minutes."
                )
            else:
                user = conn.execute(
                    "SELECT * FROM shift_private.users WHERE username=%s",
                    (username.strip().lower(),),
                ).fetchone()
                from app.api.storage import DUMMY_PASSWORD_HASH

                valid = verify_password(
                    password, user["password_hash"] if user else DUMMY_PASSWORD_HASH
                )
                if not user or not valid:
                    conn.execute(
                        "INSERT INTO shift_private.login_attempts (key,attempted_at) VALUES (%s,%s)",
                        (key, timestamp),
                    )
                    failure = HTTPException(401, "Invalid username or password")
                else:
                    conn.execute(
                        "DELETE FROM shift_private.login_attempts WHERE key=%s", (key,)
                    )
                    conn.execute(
                        "DELETE FROM shift_private.sessions WHERE expires_at<=%s OR token_hash=%s",
                        (timestamp, token_hash(previous_token)),
                    )
                    token = secrets.token_urlsafe(32)
                    conn.execute(
                        "INSERT INTO shift_private.sessions (token_hash,user_id,expires_at) VALUES (%s,%s,%s)",
                        (token_hash(token), user["id"], timestamp + seconds),
                    )
        # Commit attempts BEFORE raising an authentication error.
        if failure:
            raise failure
        return user, token

    def logout(self, token):
        with self.connection() as conn:
            conn.execute(
                "DELETE FROM shift_private.sessions WHERE token_hash=%s",
                (token_hash(token),),
            )

    def machine_exists(self, machine_id):
        with self.connection() as conn:
            return bool(
                conn.execute(
                    "SELECT 1 FROM shift_private.machines WHERE id=%s", (machine_id,)
                ).fetchone()
            )

    def machines(self):
        with self.connection() as conn:
            return [
                row["data"]
                for row in conn.execute(
                    "SELECT data FROM shift_private.machines ORDER BY id"
                )
            ]

    @staticmethod
    def serialize(conn, row):
        from app.api.storage import serialize_record

        review = conn.execute(
            "SELECT * FROM shift_private.review_events WHERE version_id=%s ORDER BY id DESC LIMIT 1",
            (row["id"],),
        ).fetchone()
        docs = conn.execute(
            "SELECT id,name,size,media_type AS type,sha256 FROM shift_private.source_documents WHERE version_id=%s",
            (row["id"],),
        ).fetchall()
        ai = conn.execute(
            "SELECT * FROM shift_private.capture_ai_runs WHERE version_id=%s",
            (row["id"],),
        ).fetchone()
        return serialize_record(row, review, docs, ai)

    def knowledge(self, machine, query):
        # Match SQLite's ASCII lower() and literal instr(), including '%' and '_'.
        fold = "translate(v.title || ' ' || v.symptom || ' ' || v.content, 'ABCDEFGHIJKLMNOPQRSTUVWXYZ', 'abcdefghijklmnopqrstuvwxyz')"
        folded = query.translate(
            str.maketrans("ABCDEFGHIJKLMNOPQRSTUVWXYZ", "abcdefghijklmnopqrstuvwxyz")
        )
        with self.connection() as conn:
            rows = conn.execute(
                f"SELECT v.* FROM shift_private.knowledge_versions v WHERE {ELIGIBLE} AND (%s='' OR v.machine_id=%s) AND (%s='' OR strpos({fold},%s)>0) ORDER BY v.created_at DESC",
                (machine, machine, query, folded),
            ).fetchall()
            return [self.serialize(conn, r) for r in rows]

    def submissions(self, user):
        with self.connection() as conn:
            rows = conn.execute(
                f"SELECT v.* FROM shift_private.knowledge_versions v JOIN shift_private.knowledge_records r ON r.id=v.record_id WHERE {LATEST} AND (%s='supervisor' OR r.owner_id=%s) ORDER BY v.created_at DESC",
                (user["role"], user["id"]),
            ).fetchall()
            return [self.serialize(conn, r) for r in rows]

    def save_submission(self, body, sources, user, record_id=None):
        from psycopg.types.json import Jsonb
        from pydantic import ValidationError

        with self.connection(transaction=True) as conn:
            timestamp = now()
            revision = 1
            if record_id:
                self.lock(conn, "record", record_id)
                record = conn.execute(
                    "SELECT * FROM shift_private.knowledge_records WHERE id=%s",
                    (record_id,),
                ).fetchone()
                if not record or (
                    record["owner_id"] != user["id"] and user["role"] != "supervisor"
                ):
                    raise HTTPException(404, "Submission not found")
                revision = conn.execute(
                    "SELECT MAX(revision)+1 AS next FROM shift_private.knowledge_versions WHERE record_id=%s",
                    (record_id,),
                ).fetchone()["next"]
            else:
                record_id = "SUB-" + secrets.token_hex(8).upper()
                conn.execute(
                    "INSERT INTO shift_private.knowledge_records (id,owner_id,created_at) VALUES (%s,%s,%s)",
                    (record_id, user["id"], timestamp),
                )
            version_id = record_id + f"-v{revision}"
            ai_review = body.aiReview
            if ai_review is not None:
                run = conn.execute(
                    "SELECT * FROM shift_private.capture_ai_runs WHERE id=%s AND owner_id=%s FOR UPDATE",
                    (ai_review.runId, user["id"]),
                ).fetchone()
                if (
                    not run
                    or run["version_id"]
                    or run["execution"]["status"] != "success"
                ):
                    raise HTTPException(
                        422,
                        "AI run is unavailable, failed, or already submitted. Discard AI to submit manually.",
                    )
                original = SubmissionFields.model_validate(
                    body.model_dump(exclude={"aiReview"})
                )
                if original.model_dump() != run["original_submission"]:
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
            conn.execute(
                """INSERT INTO shift_private.knowledge_versions
                (id,record_id,revision,machine_id,title,symptom,content,kind,author,submitted_by,problem,root_cause,resolution,safety_notes,status,created_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)""",
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
                claimed = conn.execute(
                    "UPDATE shift_private.capture_ai_runs SET version_id=%s,reviewed_structure=%s WHERE id=%s AND owner_id=%s AND version_id IS NULL RETURNING id",
                    (
                        version_id,
                        Jsonb(ai_review.fields.model_dump()),
                        ai_review.runId,
                        user["id"],
                    ),
                ).fetchone()
                if not claimed:
                    raise HTTPException(
                        422,
                        "AI run is unavailable, failed, or already submitted. Discard AI to submit manually.",
                    )
            for name, media, data in sources:
                conn.execute(
                    "INSERT INTO shift_private.source_documents (id,version_id,name,media_type,size,sha256,data,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s,%s)",
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
            row = conn.execute(
                "SELECT * FROM shift_private.knowledge_versions WHERE id=%s",
                (version_id,),
            ).fetchone()
            result = self.serialize(conn, row)
        return result

    def review(self, record_id, body, user):
        with self.connection(transaction=True) as conn:
            self.lock(conn, "record", record_id)
            row = conn.execute(
                f"SELECT v.*,r.owner_id FROM shift_private.knowledge_versions v JOIN shift_private.knowledge_records r ON r.id=v.record_id WHERE v.record_id=%s AND {LATEST}",
                (record_id,),
            ).fetchone()
            if not row:
                raise HTTPException(404, "Submission not found")
            if row["owner_id"] == user["id"] or row["submitted_by"] == user["id"]:
                raise HTTPException(
                    403, "A different supervisor must review your submission"
                )
            expected = "Approved" if body.decision == "Revoked" else "Pending"
            if row["id"] != body.versionId or row["status"] != expected:
                raise HTTPException(
                    409,
                    "This version has changed or was already reviewed. Refresh the queue.",
                )
            if body.decision != "Approved" and not body.note:
                raise HTTPException(
                    422, "A reason is required for rejection or revocation"
                )
            updated = conn.execute(
                "UPDATE shift_private.knowledge_versions SET status=%s WHERE id=%s AND status=%s RETURNING *",
                (body.decision, row["id"], expected),
            ).fetchone()
            if not updated:
                raise HTTPException(
                    409,
                    "This version has changed or was already reviewed. Refresh the queue.",
                )
            conn.execute(
                "INSERT INTO shift_private.review_events (version_id,reviewer_id,reviewer_name,previous_status,decision,note,created_at) VALUES (%s,%s,%s,%s,%s,%s,%s)",
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
            result = self.serialize(conn, updated)
        return result

    def history(self, record_id, user):
        with self.connection() as conn:
            record = conn.execute(
                "SELECT * FROM shift_private.knowledge_records WHERE id=%s",
                (record_id,),
            ).fetchone()
            if not record or (
                record["owner_id"] != user["id"] and user["role"] != "supervisor"
            ):
                raise HTTPException(404, "Submission not found")
            rows = conn.execute(
                "SELECT * FROM shift_private.knowledge_versions WHERE record_id=%s ORDER BY revision",
                (record_id,),
            ).fetchall()
            reviews = conn.execute(
                "SELECT e.* FROM shift_private.review_events e JOIN shift_private.knowledge_versions v ON v.id=e.version_id WHERE v.record_id=%s ORDER BY e.id",
                (record_id,),
            ).fetchall()
            return {
                "versions": [self.serialize(conn, r) for r in rows],
                "reviews": reviews,
            }

    def document(self, document_id):
        # Authorization remains in the shared HTTP route, before returning bytes.
        with self.connection() as conn:
            return conn.execute(
                f"SELECT d.*,v.status,r.owner_id,({LATEST}) AS latest FROM shift_private.source_documents d JOIN shift_private.knowledge_versions v ON v.id=d.version_id JOIN shift_private.knowledge_records r ON r.id=v.record_id WHERE d.id=%s",
                (document_id,),
            ).fetchone()

    def capture_receipt(self, body, user):
        from psycopg.types.json import Jsonb
        from app.capture.service import MODEL, PROVIDER

        with self.connection(transaction=True) as conn:
            self.lock(conn, "capture", user["id"])
            cutoff = (datetime.now(UTC) - timedelta(seconds=30)).isoformat()
            if conn.execute(
                "SELECT 1 FROM shift_private.capture_ai_runs WHERE owner_id=%s AND created_at>%s",
                (user["id"], cutoff),
            ).fetchone():
                raise HTTPException(
                    429,
                    "Wait 30 seconds between AI requests. Manual capture is available.",
                )
            run_id = secrets.token_hex(16)
            timestamp = now()
            execution = {
                "provider": PROVIDER,
                "requested_model": MODEL,
                "model_id": MODEL,
                "requested_at": timestamp,
                "latency_ms": None,
                "usage": None,
                "status": "interrupted",
                "http_status": None,
                "error_code": "interrupted",
            }
            conn.execute(
                "INSERT INTO shift_private.capture_ai_runs (id,owner_id,original_submission,execution,created_at) VALUES (%s,%s,%s,%s,%s)",
                (
                    run_id,
                    user["id"],
                    Jsonb(body.model_dump()),
                    Jsonb(execution),
                    timestamp,
                ),
            )
        return run_id

    def capture_result(self, run_id, result):
        from psycopg.types.json import Jsonb

        with self.connection(transaction=True) as conn:
            conn.execute(
                "UPDATE shift_private.capture_ai_runs SET proposal=%s,execution=%s WHERE id=%s",
                (
                    Jsonb(result["proposal"]) if "proposal" in result else None,
                    Jsonb(result["execution"]),
                    run_id,
                ),
            )

    def approved_rows(self, machine):
        with self.connection() as conn:
            return conn.execute(
                f"SELECT v.* FROM shift_private.knowledge_versions v WHERE {ELIGIBLE} AND v.machine_id=%s",
                (machine,),
            ).fetchall()

    def generation(self, version_id):
        with self.connection() as conn:
            return conn.execute(
                "SELECT * FROM shift_private.rag_generations WHERE version_id=%s",
                (version_id,),
            ).fetchone()

    def replace_index(self, row, digest, key, chunks):
        from app.rag.retrieval import fingerprint

        with self.connection(transaction=True) as conn:
            self.lock(conn, "record", row["record_id"])
            current = conn.execute(
                f"SELECT v.* FROM shift_private.knowledge_versions v WHERE v.id=%s AND {ELIGIBLE}",
                (row["id"],),
            ).fetchone()
            if not current or fingerprint(current) != digest:
                return
            conn.execute(
                "DELETE FROM shift_private.knowledge_chunks WHERE version_id=%s",
                (row["id"],),
            )
            for chunk_id, position, text, chunk_hash, vector in chunks:
                conn.execute(
                    "INSERT INTO shift_private.knowledge_chunks (id,version_id,position,section,content,content_hash) VALUES (%s,%s,%s,%s,%s,%s)",
                    (
                        chunk_id,
                        row["id"],
                        position,
                        "Approved written record",
                        text,
                        chunk_hash,
                    ),
                )
                conn.execute(
                    "INSERT INTO shift_private.chunk_embeddings (chunk_id,embedding_key,vector) VALUES (%s,%s,%s)",
                    (chunk_id, key, vector),
                )
            conn.execute(
                "INSERT INTO shift_private.rag_generations (version_id,fingerprint,embedding_key) VALUES (%s,%s,%s) ON CONFLICT (version_id) DO UPDATE SET fingerprint=EXCLUDED.fingerprint,embedding_key=EXCLUDED.embedding_key",
                (row["id"], digest, key),
            )

    def candidates(self, machine, key, query_vector, query_terms):
        with self.connection() as conn:
            # Both branches are restricted before ranking, with no premature LIMIT.
            rows = conn.execute(
                f"""SELECT c.id,c.version_id,c.content,c.content_hash,v.record_id,v.title,v.machine_id,g.fingerprint,e.vector,
                1-(e.vector OPERATOR(extensions.<=>) %s::extensions.vector(384)) AS similarity,
                ts_rank_cd(c.search_vector,to_tsquery('pg_catalog.simple'::regconfig,%s)) AS lexical_rank,
                c.search_vector @@ to_tsquery('pg_catalog.simple'::regconfig,%s) AS lexical_match
                FROM shift_private.knowledge_chunks c JOIN shift_private.knowledge_versions v ON v.id=c.version_id
                JOIN shift_private.chunk_embeddings e ON e.chunk_id=c.id JOIN shift_private.rag_generations g ON g.version_id=v.id
                WHERE {ELIGIBLE} AND v.machine_id=%s AND e.embedding_key=%s AND g.embedding_key=%s""",
                (
                    query_vector,
                    " | ".join(query_terms),
                    " | ".join(query_terms),
                    machine,
                    key,
                    key,
                ),
            ).fetchall()
        return rows

    def valid_evidence(self, machine, nodes):
        from app.rag.retrieval import fingerprint

        if not nodes:
            return True
        ids = [n.node.node_id for n in nodes]
        with self.connection() as conn:
            # One fresh committed-state snapshot per validation phase.
            rows = conn.execute(
                f"""SELECT v.*,c.id AS chunk_id,c.content AS chunk_content,c.content_hash,e.embedding_key,g.fingerprint AS generation_fingerprint
                FROM shift_private.knowledge_chunks c JOIN shift_private.knowledge_versions v ON v.id=c.version_id
                JOIN shift_private.chunk_embeddings e ON e.chunk_id=c.id
                JOIN shift_private.rag_generations g ON g.version_id=v.id AND g.embedding_key=e.embedding_key
                WHERE {ELIGIBLE} AND v.machine_id=%s AND c.id=ANY(%s)""",
                (machine, ids),
            ).fetchall()
        lookup = {r["chunk_id"]: r for r in rows}
        for scored in nodes:
            n = scored.node
            row = lookup.get(n.node_id)
            if (
                not row
                or row["id"] != n.metadata["version_id"]
                or row["record_id"] != n.metadata["record_id"]
                or row["embedding_key"] != n.metadata.get("embedding_key")
                or row["generation_fingerprint"] != n.metadata["fingerprint"]
                or fingerprint(row) != n.metadata["fingerprint"]
                or row["chunk_content"] != n.text
                or hashlib.sha256(n.text.encode()).hexdigest() != row["content_hash"]
            ):
                return False
        return True
