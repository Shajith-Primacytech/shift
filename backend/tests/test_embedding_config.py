from pathlib import Path
import tomllib

from app.rag import embeddings


def test_embedding_loader_is_lazy_cached_and_low_memory(monkeypatch):
    calls = []

    class FakeEmbedding:
        def __init__(self, **kwargs):
            calls.append(kwargs)

    monkeypatch.setattr(
        "huggingface_hub.snapshot_download", lambda *args, **kwargs: "/fixed/model"
    )
    monkeypatch.setattr(
        "llama_index.embeddings.huggingface.HuggingFaceEmbedding", FakeEmbedding
    )
    embeddings.local_model.cache_clear()
    try:
        first = embeddings.local_model()
        assert embeddings.local_model() is first
    finally:
        embeddings.local_model.cache_clear()

    assert len(calls) == 1
    assert calls[0]["model_name"] == "/fixed/model"
    assert calls[0]["device"] == "cpu"
    assert calls[0]["normalize"] is True
    assert calls[0]["model_kwargs"] == {"low_cpu_mem_usage": True}


def test_linux_lock_uses_official_cpu_only_torch():
    locked = tomllib.loads((Path(__file__).parents[1] / "uv.lock").read_text())
    packages = locked["package"]
    torch = [package for package in packages if package["name"] == "torch"]

    assert {
        (package["version"], package["source"]["registry"]) for package in torch
    } == {
        ("2.14.1", "https://pypi.org/simple"),
        ("2.14.1+cpu", "https://download.pytorch.org/whl/cpu"),
    }
    assert not any(
        package["name"].startswith(("cuda-", "nvidia-"))
        or package["name"] == "triton"
        for package in packages
    )
