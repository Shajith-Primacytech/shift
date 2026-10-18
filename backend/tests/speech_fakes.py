"""Offline speech double for isolated browser/API tests only."""

from app.speech.constants import MODEL, PROVIDER

TEXT = "Synthetic vibration after a tool change. The root cause is not confirmed."


class FakeSpeech:
    def status(self):
        return {
            "available": True,
            "provider": PROVIDER,
            "model": MODEL,
            "language": "en",
            "max_duration_seconds": 120,
        }

    def transcribe(self, data):
        return {
            "text": TEXT,
            "provider": PROVIDER,
            "model": MODEL,
            "language": "en",
            "duration_seconds": 3.0,
            "latency_ms": 5,
        }
