"""Exact pgvector + PostgreSQL FTS; same approved evidence and RRF gates."""

import hashlib
from collections import defaultdict

import numpy as np
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, TextNode

from app.rag.embeddings import EMBEDDING_KEY, MODEL_LOCK, local_model, tokenizer
from app.rag.retrieval import QueryTooLong, document_text, fingerprint, terms


def vector384(value):
    if hasattr(value, "to_numpy"):
        value = value.to_numpy()
    array = np.asarray(value, dtype=np.float32)
    if (
        array.shape != (384,)
        or not np.isfinite(array).all()
        or not float(np.linalg.norm(array)) > 0
    ):
        raise ValueError("Invalid embedding vector")
    return array


class PostgresRetriever(BaseRetriever):
    def __init__(
        self,
        store,
        machine_id,
        embed_model=None,
        embedding_key=EMBEDDING_KEY,
        token_fn=None,
    ):
        super().__init__()
        self.store = store
        self.machine_id = machine_id
        self.embed_model = embed_model
        self.embedding_key = embedding_key
        self.token_fn = token_fn

    def _sync(self, model):
        for row in self.store.approved_rows(self.machine_id):
            digest = fingerprint(row)
            old = self.store.generation(row["id"])
            if (
                old
                and old["fingerprint"] == digest
                and old["embedding_key"] == self.embedding_key
            ):
                continue
            split = SentenceSplitter(
                chunk_size=180,
                chunk_overlap=25,
                tokenizer=self.token_fn or tokenizer(model),
                include_metadata=False,
            )
            nodes = split.get_nodes_from_documents(
                [Document(text=document_text(row), id_=row["id"])]
            )
            texts = [node.text for node in nodes]
            vectors = model.get_text_embedding_batch(texts)
            chunks = []
            for position, (text, vector) in enumerate(zip(texts, vectors, strict=True)):
                digest_chunk = hashlib.sha256(text.encode()).hexdigest()
                chunk_id = f"{row['id']}:c{position}:{digest_chunk[:12]}"
                chunks.append(
                    (chunk_id, position, text, digest_chunk, vector384(vector))
                )
            self.store.replace_index(row, digest, self.embedding_key, chunks)

    def _retrieve(self, query_bundle):
        query = query_bundle.query_str
        query_terms = terms(query)[:32]
        if not query_terms:
            return []
        with MODEL_LOCK:
            if not self.store.approved_rows(self.machine_id):
                return []
            model = self.embed_model or local_model()
            if len((self.token_fn or tokenizer(model))(query)) > 240:
                raise QueryTooLong()
            self._sync(model)
            q = vector384(model.get_query_embedding(query))
            rows = self.store.candidates(
                self.machine_id, self.embedding_key, q, query_terms
            )
            # pgvector does exact cosine search. Preserve the original float32
            # threshold/tie semantics by scoring returned scoped vectors in NumPy.
            q = q / max(float(np.linalg.norm(q)), 1e-12)
            scores = {}
            for row in rows:
                vector = vector384(row["vector"])
                scores[row["id"]] = float(
                    np.dot(q, vector) / max(float(np.linalg.norm(vector)), 1e-12)
                )
            eligible = {
                r["id"]
                for r in rows
                if scores[r["id"]] >= 0.35
                and set(query_terms) & set(terms(r["content"]))
            }
            semantic = sorted(eligible, key=lambda key: (-scores[key], key))[:20]
            lexical = [
                r["id"]
                for r in sorted(rows, key=lambda r: (-r["lexical_rank"], r["id"]))
                if r["lexical_match"] and r["id"] in eligible
            ][:20]
            fused = defaultdict(float)
            for branch in (semantic, lexical):
                for rank, chunk_id in enumerate(branch, 1):
                    fused[chunk_id] += 1 / (60 + rank)
            lookup = {r["id"]: r for r in rows}
            result = []
            for chunk_id in sorted(fused, key=lambda key: (-fused[key], key))[:5]:
                row = lookup[chunk_id]
                metadata = {
                    k: row[k]
                    for k in (
                        "record_id",
                        "version_id",
                        "title",
                        "machine_id",
                        "fingerprint",
                    )
                }
                metadata["embedding_key"] = self.embedding_key
                node = TextNode(
                    id_=chunk_id,
                    text=row["content"],
                    metadata=metadata,
                    excluded_embed_metadata_keys=list(metadata),
                )
                result.append(NodeWithScore(node=node, score=fused[chunk_id]))
            return result
