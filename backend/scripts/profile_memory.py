#!/usr/bin/env python3
"""Measure real SHIFT model and retrieval memory without calling a remote LLM."""

from __future__ import annotations

import argparse
from array import array
import hashlib
import json
import os
import resource
import sys
import tempfile
import time
import wave
from pathlib import Path

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


def _read_number(path: str) -> int | None:
    try:
        value = Path(path).read_text().strip()
        return None if value == "max" else int(value)
    except (FileNotFoundError, PermissionError, ValueError):
        return None


def _proc_status() -> dict[str, int]:
    values: dict[str, int] = {}
    try:
        for line in Path("/proc/self/status").read_text().splitlines():
            key, _, value = line.partition(":")
            if key in {"VmRSS", "VmHWM"}:
                values[key.lower() + "_bytes"] = int(value.split()[0]) * 1024
    except FileNotFoundError:
        pass
    return values


def _memory() -> dict[str, int | None]:
    result: dict[str, int | None] = {
        "process_max_rss_bytes": int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
        * (1024 if os.uname().sysname == "Linux" else 1),
        "cgroup_current_bytes": _read_number("/sys/fs/cgroup/memory.current"),
        "cgroup_peak_bytes": _read_number("/sys/fs/cgroup/memory.peak"),
        "cgroup_limit_bytes": _read_number("/sys/fs/cgroup/memory.max"),
    }
    result.update(_proc_status())
    return result


class Recorder:
    def __init__(self, output: Path, metadata: dict[str, str]):
        self.output = output
        self.started = time.monotonic()
        self.report: dict[str, object] = {**metadata, "stages": []}

    def stage(self, name: str, **details: object) -> None:
        entry = {
            "stage": name,
            "elapsed_seconds": round(time.monotonic() - self.started, 3),
            **_memory(),
            **details,
        }
        stages = self.report["stages"]
        assert isinstance(stages, list)
        stages.append(entry)
        temporary = self.output.with_suffix(".tmp")
        temporary.write_text(json.dumps(self.report, indent=2) + "\n")
        temporary.replace(self.output)
        print(json.dumps(entry), flush=True)


def load_embedding(loader: str):
    if loader == "candidate":
        from app.rag.embeddings import local_model

        first = local_model()
        assert local_model() is first
        return first

    from huggingface_hub import snapshot_download
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    snapshot = snapshot_download(
        MODEL,
        revision=REVISION,
        local_files_only=True,
        token=False,
        allow_patterns=["*.json", "*.txt", "*.safetensors", "1_Pooling/*"],
    )
    return HuggingFaceEmbedding(
        model_name=snapshot,
        device="cpu",
        normalize=True,
        embed_batch_size=8,
        max_length=256,
        local_files_only=True,
        trust_remote_code=False,
    )


def vector_hash(model) -> str:
    import numpy as np

    vector = np.asarray(
        model.get_text_embedding("Synthetic hackathon deployment observation"),
        dtype=np.float32,
    )
    assert vector.shape == (384,)
    return hashlib.sha256(vector.tobytes()).hexdigest()


def run_rag(recorder: Recorder, loader: str) -> object:
    from app.rag.retrieval import ApprovedRetriever, valid_evidence
    from app.storage.database import connect, initialize

    database = Path(tempfile.mkdtemp(prefix="shift-profile-")) / "profile.sqlite3"
    initialize(str(database), seed=True)
    recorder.stage("sqlite_initialized")

    model = load_embedding(loader)
    digest = vector_hash(model)
    recorder.stage("embedding_loaded", embedding_dimensions=384, vector_sha256=digest)

    retriever = ApprovedRetriever(str(database), "CNC-01", embed_model=model)
    retriever._sync(model)
    with connect(str(database)) as connection:
        chunks = connection.execute("SELECT count(*) FROM knowledge_chunks").fetchone()[0]
    assert chunks > 0
    recorder.stage("approved_index_built", indexed_chunks=chunks)

    nodes = retriever.retrieve("What should I check for spindle vibration?")
    records = sorted({node.node.metadata["record_id"] for node in nodes})
    assert records == ["NOTE-002", "SOP-001"]
    assert valid_evidence(str(database), "CNC-01", nodes)
    recorder.stage("troubleshooting_retrieval", evidence_records=records)

    repeated = retriever.retrieve("What should I check for spindle vibration?")
    assert [node.node.node_id for node in repeated] == [node.node.node_id for node in nodes]
    recorder.stage("cached_troubleshooting_retrieval", evidence_records=records)
    return model


def run_speech(recorder: Recorder) -> object:
    from faster_whisper import WhisperModel

    model_path = os.environ.get("SHIFT_SPEECH_MODEL_PATH", "/opt/models/whisper")
    if not Path(model_path).is_dir():
        raise FileNotFoundError(f"Pinned local speech model is missing: {model_path}")
    speech = WhisperModel(
        model_path, device="cpu", compute_type="int8", cpu_threads=1, num_workers=1
    )
    recorder.stage("speech_model_loaded")
    audio_path = Path(tempfile.mkdtemp(prefix="shift-audio-profile-")) / "silence.wav"
    with wave.open(str(audio_path), "wb") as audio:
        audio.setnchannels(1)
        audio.setsampwidth(2)
        audio.setframerate(16_000)
        audio.writeframes(array("h", [0]) * 32_000)
    segments, info = speech.transcribe(str(audio_path), beam_size=1)
    list(segments)
    recorder.stage("speech_transcription", detected_language=info.language)
    return speech


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--loader", choices=("baseline", "candidate"), required=True)
    parser.add_argument(
        "--scenario", choices=("startup", "rag", "speech", "combined"), required=True
    )
    parser.add_argument(
        "--output", type=Path, default=Path("/tmp/shift-memory-profile.json")
    )
    args = parser.parse_args()
    recorder = Recorder(
        args.output,
        {
            "loader": args.loader,
            "scenario": args.scenario,
            "python": os.sys.version.split()[0],
        },
    )
    recorder.stage("process_started")

    import app.main  # noqa: F401

    recorder.stage("application_imported")
    if args.scenario == "startup":
        return
    if args.scenario == "rag":
        run_rag(recorder, args.loader)
        return
    if args.scenario == "speech":
        run_speech(recorder)
        return
    embedding = run_rag(recorder, args.loader)
    speech = run_speech(recorder)
    assert embedding is not None and speech is not None
    recorder.stage("combined_models_resident")


if __name__ == "__main__":
    main()
