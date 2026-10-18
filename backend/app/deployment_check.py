"""Explicit local integration smoke. Live Gemma is opt-in and called at most once."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory

from dotenv import dotenv_values
from fastapi.testclient import TestClient

from app.config import AMDSettings, Settings
from app.demo import provision
from app.main import create_app


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audio", type=Path, required=True, help="Short synthetic English WAV")
    parser.add_argument("--live-gemma", action="store_true")
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    config = Settings()
    key = AMDSettings().api_key.get_secret_value().strip()
    if args.live_gemma and not key:
        raise SystemExit("Configure AMD_API_KEY privately on the backend; no inference attempted")
    evidence = {"tested_at": datetime.now(timezone.utc).isoformat(), "mode": "local real services, isolated synthetic database", "live_gemma_calls": 0}
    with TemporaryDirectory(prefix="shift-deployment-") as directory:
        database = directory + "/test.sqlite3"
        credentials_file = directory + "/judges.env"
        provision(database, credentials_file)
        credentials = dotenv_values(credentials_file)
        settings = Settings(_env_file=None, environment="test", database_path=database, speech_model_path=config.speech_model_path)
        app = create_app(settings)
        with TestClient(app, headers={"X-Shift-Request": "1"}) as client:
            def login(username, password):
                response = client.post("/api/v1/auth/login", json={"username": username, "password": password})
                assert response.status_code == 200
                return response.json()["role"]
            assert login("judge-tech", credentials["SHIFT_DEMO_TECHNICIAN_PASSWORD"]) == "technician"
            assert client.get("/api/v1/capture/voice/status").json()["available"]
            speech = client.post("/api/v1/capture/transcribe", files={"file": ("synthetic.wav", args.audio.read_bytes(), "audio/wav")})
            evidence["whisper"] = {"http_status": speech.status_code}
            assert speech.status_code == 200
            speech_body = speech.json()
            evidence["whisper"].update({k: speech_body[k] for k in ("provider", "model", "latency_ms", "duration_seconds", "language")})
            evidence["whisper"]["transcript_nonempty"] = bool(speech_body["text"].strip())
            source = {"machineId": "CNC-02", "title": "Synthetic demo observation", "symptom": "Vibration", "content": "Synthetic vibration after a tool change. Cause is unconfirmed. Inspection is planned.", "kind": "Field note"}
            if args.live_gemma:
                evidence["live_gemma_calls"] = 1
                response = client.post("/api/v1/capture/structure", json=source)
                body = response.json()
                evidence["gemma"] = {"http_status": response.status_code, "execution": body.get("execution")}
                # Only sanitized execution metadata is retained, never prompts or credentials.
                if response.status_code == 200:
                    source["aiReview"] = {"runId": body["runId"], "fields": body["fields"], "reviewed": True}
                    evidence["gemma"]["unconfirmed_root_cause_blank"] = not body["fields"]["confirmedRootCause"]
            submission = client.post("/api/v1/submissions", data={"metadata": json.dumps(source)})
            assert submission.status_code == 201
            record = submission.json()
            assert record["status"] == "Pending"
            def excluded():
                return record["id"] not in [r["id"] for r in client.get("/api/v1/knowledge").json()]
            assert excluded()
            decision = {"versionId": record["versionId"], "decision": "Approved", "note": "Synthetic judge validation only"}
            endpoint = f"/api/v1/submissions/{record['id']}/review"
            assert client.post(endpoint, json=decision).status_code == 403
            assert login("judge-supervisor", credentials["SHIFT_DEMO_SUPERVISOR_PASSWORD"]) == "supervisor"
            assert client.post(endpoint, json=decision).status_code == 200
            assert not excluded()
            decision["decision"] = "Revoked"
            assert client.post(endpoint, json=decision).status_code == 200
            assert excluded()
            evidence["approval_gating"] = {"pending_on_submit": True, "technician_approval_denied": True, "supervisor_approval_succeeds": True, "pending_and_revoked_excluded": True}
    output = json.dumps(evidence, indent=2)
    assert not key or key not in output
    args.report.write_text(output + "\n")
    print(output)
    if args.live_gemma and evidence["gemma"]["http_status"] != 200:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
