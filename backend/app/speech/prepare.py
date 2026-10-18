"""Explicit public model download. Never runs during recording or transcription."""

import json
from pathlib import Path

from huggingface_hub import snapshot_download

from app.config import Settings
from app.speech.constants import MODEL, REVISION


def main():
    directory = Path(Settings().speech_model_path).resolve()
    snapshot_download(
        MODEL,
        revision=REVISION,
        local_dir=directory,
        allow_patterns=["config.json", "model.bin", "tokenizer.json", "vocabulary.txt"],
        token=False,
    )
    (directory / "shift-model.json").write_text(
        json.dumps({"model": MODEL, "revision": REVISION})
    )
    print(
        "Local English speech model prepared. Recordings will not be sent to an external service."
    )


if __name__ == "__main__":
    main()
