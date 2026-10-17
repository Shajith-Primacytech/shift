"""One pinned CPU model per process; no downloads during a technician request."""

from functools import lru_cache
from threading import RLock

MODEL = "sentence-transformers/all-MiniLM-L6-v2"
REVISION = "1110a243fdf4706b3f48f1d95db1a4f5529b4d41"
EMBEDDING_KEY = f"{MODEL}@{REVISION}:384:chunk180-overlap25:v1"
MODEL_LOCK = RLock()


@lru_cache(maxsize=1)
def local_model():
    from huggingface_hub import snapshot_download
    from llama_index.embeddings.huggingface import HuggingFaceEmbedding

    with MODEL_LOCK:
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


def tokenizer(model):
    return lambda text: model._model.tokenizer.encode(text, add_special_tokens=False)
