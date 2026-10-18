"""Bounded one-job worker. Called with local file paths, never transcript arguments."""

import json
import sys
from pathlib import Path

from app.speech.constants import MAX_SECONDS


class AudioFailure(Exception):
    pass


def decode_bounded(path):
    import av
    import numpy as np

    resampler = av.AudioResampler(format="s16", layout="mono", rate=16000)
    chunks = []
    count = 0
    with av.open(path) as container:
        if not container.streams.audio:
            raise AudioFailure("invalid_audio")
        for frame in container.decode(audio=0):
            for converted in resampler.resample(frame):
                samples = converted.to_ndarray().reshape(-1)
                count += len(samples)
                if count > MAX_SECONDS * 16000:
                    raise AudioFailure("too_long")
                chunks.append(samples)
        for converted in resampler.resample(None):
            samples = converted.to_ndarray().reshape(-1)
            count += len(samples)
            if count > MAX_SECONDS * 16000:
                raise AudioFailure("too_long")
            chunks.append(samples)
    if count < 1600:
        raise AudioFailure("empty_audio")
    waveform = np.concatenate(chunks).astype(np.float32) / 32768.0
    if float(np.sqrt(np.mean(waveform * waveform))) < 0.003:
        raise AudioFailure("no_speech")
    return waveform


def transcribe(path, model_path):
    from faster_whisper import WhisperModel

    audio = decode_bounded(path)
    model = WhisperModel(
        model_path,
        device="cpu",
        compute_type="int8",
        cpu_threads=4,
        num_workers=1,
        local_files_only=True,
    )
    segments, _ = model.transcribe(
        audio,
        language="en",
        task="transcribe",
        beam_size=1,
        temperature=0,
        condition_on_previous_text=False,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 500},
        without_timestamps=True,
    )
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if not text:
        raise AudioFailure("no_speech")
    if len(text) > 8000:
        raise AudioFailure("too_long")
    return {"text": text, "duration_seconds": round(len(audio) / 16000, 2)}


def main():
    output = Path(sys.argv[3])
    try:
        result = transcribe(sys.argv[1], sys.argv[2])
    except AudioFailure as exc:
        result = {"error": str(exc)}
    except Exception:  # noqa: BLE001 -- sanitize all third-party decoder/model failures at the worker boundary
        # Decoder/model exceptions may contain local paths or sensitive data.
        result = {"error": "transcription_failed"}
    output.write_text(json.dumps(result))


if __name__ == "__main__":
    main()
