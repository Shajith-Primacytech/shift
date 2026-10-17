"""Explicit one-time public model download and approved-record indexing."""

from app.config import Settings
from app.rag.embeddings import MODEL, REVISION, local_model
from app.rag.retrieval import ApprovedRetriever
from app.storage.database import connect, initialize


def main():
    from huggingface_hub import snapshot_download

    snapshot_download(
        MODEL,
        revision=REVISION,
        allow_patterns=["*.json", "*.txt", "*.safetensors", "1_Pooling/*"],
        token=False,
    )
    settings = Settings()
    initialize(settings.database_path, settings.seed_synthetic)
    model = local_model()
    with connect(settings.database_path) as db:
        machines = [r["id"] for r in db.execute("SELECT id FROM machines")]
    for machine in machines:
        ApprovedRetriever(settings.database_path, machine, embed_model=model)._sync(
            model
        )
    print(
        "Local embedding model ready. Approved written records indexed; no AMD calls made."
    )


if __name__ == "__main__":
    main()
