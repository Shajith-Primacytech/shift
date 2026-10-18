"""Private temporary audio, offline CPU worker, bounded time and no retained transcripts."""

import importlib.util
import json
import os
import subprocess
import sys
import time
from pathlib import Path
from tempfile import TemporaryDirectory

from app.speech.constants import (
    MAX_BYTES,
    MAX_SECONDS,
    MODEL,
    PROVIDER,
    REVISION,
    TIMEOUT_SECONDS,
)

ERRORS = {
    "invalid_audio": "The recording could not be decoded as audio. Record again or continue manually.",
    "empty_audio": "The recording is empty or too short. Record a short spoken observation.",
    "no_speech": "No clear speech was detected. Check the microphone and record again, or type the observation.",
    "too_long": "Recording exceeds the two-minute or transcript length limit. Use a shorter recording.",
    "transcription_failed": "Local transcription failed. Your recording and written observation are unchanged.",
    "unavailable": "Local transcription is not prepared. Install the voice extra and run python -m app.speech.prepare on the backend. Manual capture is available.",
    "timeout": "Local transcription timed out. No automatic retry was made; manual capture is available.",
}


class SpeechFailure(Exception):
    def __init__(self, code, status=422):
        self.code = code
        self.status = status
        super().__init__(ERRORS[code])


class LocalSpeech:
    def __init__(self, model_path):
        self.model_path = Path(model_path).resolve()

    def status(self):
        ready = False
        try:
            manifest = json.loads((self.model_path / "shift-model.json").read_text())
            ready = (
                manifest == {"model": MODEL, "revision": REVISION}
                and all(
                    (self.model_path / name).is_file()
                    for name in ("model.bin", "config.json", "tokenizer.json")
                )
                and importlib.util.find_spec("faster_whisper") is not None
            )
        except (OSError, ValueError):
            pass
        return {
            "available": ready,
            "provider": PROVIDER,
            "model": MODEL,
            "language": "en",
            "max_duration_seconds": MAX_SECONDS,
        }

    def transcribe(self, data):
        start = time.perf_counter()
        if not data or len(data) > MAX_BYTES:
            raise SpeechFailure("empty_audio" if not data else "too_long")
        if not self.status()["available"]:
            raise SpeechFailure("unavailable", 503)
        with TemporaryDirectory(prefix="shift-speech-") as directory:
            audio = Path(directory) / "recording"
            result_file = Path(directory) / "result.json"
            audio.write_bytes(data)
            env = {
                k: v
                for k, v in os.environ.items()
                if not k.startswith("AMD_")
                and k not in ("HF_TOKEN", "HUGGING_FACE_HUB_TOKEN")
            }
            env.update(
                HF_HUB_OFFLINE="1",
                TRANSFORMERS_OFFLINE="1",
                HF_HUB_DISABLE_TELEMETRY="1",
            )
            try:
                result = subprocess.run(
                    [
                        sys.executable,
                        "-m",
                        "app.speech.worker",
                        str(audio),
                        str(self.model_path),
                        str(result_file),
                    ],
                    cwd=Path(__file__).resolve().parents[2],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=TIMEOUT_SECONDS,
                    check=False,
                )
            except subprocess.TimeoutExpired:
                raise SpeechFailure("timeout", 504) from None
            except OSError:
                raise SpeechFailure("transcription_failed", 503) from None
            try:
                if result.returncode != 0 or result_file.stat().st_size > 64000:
                    raise ValueError()
                output = json.loads(result_file.read_text())
                if not isinstance(output, dict):
                    raise TypeError()
                code = output.get("error")
                if isinstance(code, str) and code in ERRORS:
                    raise SpeechFailure(code)
                text, duration = output.get("text"), output.get("duration_seconds")
                if not isinstance(text, str) or not text.strip() or len(text) > 8000:
                    raise ValueError()
                if (
                    type(duration) not in (int, float)
                    or not 0 < duration <= MAX_SECONDS
                ):
                    raise ValueError()
            except (TypeError, ValueError, OSError):
                raise SpeechFailure("transcription_failed", 503) from None
        return {
            "text": text.strip(),
            "duration_seconds": duration,
            "language": "en",
            "provider": PROVIDER,
            "model": MODEL,
            "latency_ms": round((time.perf_counter() - start) * 1000, 1),
        }
