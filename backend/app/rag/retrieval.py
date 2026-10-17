"""LlamaIndex nodes/retriever, persisted SQLite vectors and FTS5 rank fusion."""

import hashlib
import re
from collections import defaultdict

import numpy as np
from llama_index.core import Document
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.retrievers import BaseRetriever
from llama_index.core.schema import NodeWithScore, QueryBundle, TextNode

from app.rag.embeddings import EMBEDDING_KEY, MODEL_LOCK, local_model, tokenizer
from app.storage.database import connect

ELIGIBLE = "v.status='Approved' AND v.revision=(SELECT MAX(v2.revision) FROM knowledge_versions v2 WHERE v2.record_id=v.record_id)"
STOP = set(
    "a an the i my we our is are was were it this that what which how why when should can could would do does did to for of on in and or with please machine cnc tell about check inspect unusual".split()
)


def terms(text):
    return sorted(
        {w for w in re.findall(r"[a-z][a-z0-9]+", text.lower()) if w not in STOP}
    )


def document_text(row):
    return "\n\n".join(
        [row["title"], row["symptom"], row["content"]]
        + [
            row[k]
            for k in ("problem", "root_cause", "resolution", "safety_notes")
            if row[k]
        ]
    )


def fingerprint(row):
    return hashlib.sha256(document_text(row).encode()).hexdigest()


def valid_evidence(path, machine_id, nodes):
    """Fresh database checks; cached approval flags are never trusted."""
    with connect(path) as db:
        for scored in nodes:
            node = scored.node
            row = db.execute(
                f"SELECT v.* FROM knowledge_versions v WHERE v.id=? AND v.machine_id=? AND {ELIGIBLE}",
                (node.metadata["version_id"], machine_id),
            ).fetchone()
            chunk = db.execute(
                "SELECT content_hash FROM knowledge_chunks WHERE id=? AND version_id=?",
                (node.node_id, node.metadata["version_id"]),
            ).fetchone()
            if (
                not row
                or not chunk
                or fingerprint(row) != node.metadata["fingerprint"]
                or hashlib.sha256(node.text.encode()).hexdigest()
                != chunk["content_hash"]
            ):
                return False
    return True


class QueryTooLong(ValueError):
    pass


class ApprovedRetriever(BaseRetriever):
    def __init__(
        self,
        path,
        machine_id,
        embed_model=None,
        embedding_key=EMBEDDING_KEY,
        token_fn=None,
    ):
        super().__init__()
        self.path = path
        self.machine_id = machine_id
        self.embed_model = embed_model
        self.embedding_key = embedding_key
        self.token_fn = token_fn

    def _sync(self, model):
        with connect(self.path) as db:
            rows = db.execute(
                f"SELECT v.* FROM knowledge_versions v WHERE {ELIGIBLE} AND v.machine_id=?",
                (self.machine_id,),
            ).fetchall()
        for row in rows:
            digest = fingerprint(row)
            with connect(self.path) as db:
                old = db.execute(
                    "SELECT * FROM rag_generations WHERE version_id=?", (row["id"],)
                ).fetchone()
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
            texts = [n.text for n in nodes]
            vectors = model.get_text_embedding_batch(texts)
            with connect(self.path) as db:
                db.execute("BEGIN IMMEDIATE")
                current = db.execute(
                    f"SELECT v.* FROM knowledge_versions v WHERE v.id=? AND {ELIGIBLE}",
                    (row["id"],),
                ).fetchone()
                if not current or fingerprint(current) != digest:
                    continue
                db.execute("DELETE FROM rag_fts WHERE version_id=?", (row["id"],))
                db.execute(
                    "DELETE FROM knowledge_chunks WHERE version_id=?", (row["id"],)
                )
                for position, (text, vector) in enumerate(
                    zip(texts, vectors, strict=True)
                ):
                    chunk_hash = hashlib.sha256(text.encode()).hexdigest()
                    chunk_id = f"{row['id']}:c{position}:{chunk_hash[:12]}"
                    db.execute(
                        "INSERT INTO knowledge_chunks (id,version_id,position,section,content,content_hash) VALUES (?,?,?,?,?,?)",
                        (
                            chunk_id,
                            row["id"],
                            position,
                            "Approved written record",
                            text,
                            chunk_hash,
                        ),
                    )
                    array = np.asarray(vector, dtype=np.float32)
                    if array.shape != (384,) or not np.isfinite(array).all():
                        raise ValueError("Invalid embedding vector")
                    db.execute(
                        "INSERT INTO chunk_embeddings VALUES (?,?,?)",
                        (chunk_id, self.embedding_key, array.tobytes()),
                    )
                    db.execute(
                        "INSERT INTO rag_fts VALUES (?,?,?)",
                        (chunk_id, row["id"], text),
                    )
                db.execute(
                    "INSERT OR REPLACE INTO rag_generations VALUES (?,?,?)",
                    (row["id"], digest, self.embedding_key),
                )

    def _retrieve(self, query_bundle: QueryBundle):
        query = query_bundle.query_str
        query_terms = terms(query)[:32]
        if not query_terms:
            return []
        with MODEL_LOCK:
            # An empty approved scope needs no model download/load or API call.
            with connect(self.path) as db:
                if not db.execute(
                    f"SELECT 1 FROM knowledge_versions v WHERE {ELIGIBLE} AND v.machine_id=?",
                    (self.machine_id,),
                ).fetchone():
                    return []
            model = self.embed_model or local_model()
            if len((self.token_fn or tokenizer(model))(query)) > 240:
                raise QueryTooLong()
            self._sync(model)
            with connect(self.path) as db:
                rows = db.execute(
                    f"""SELECT c.*,v.record_id,v.title,v.machine_id,g.fingerprint,e.vector
                    FROM knowledge_chunks c JOIN knowledge_versions v ON v.id=c.version_id
                    JOIN chunk_embeddings e ON e.chunk_id=c.id JOIN rag_generations g ON g.version_id=v.id
                    WHERE {ELIGIBLE} AND v.machine_id=? AND e.embedding_key=?""",
                    (self.machine_id, self.embedding_key),
                ).fetchall()
                lexical = db.execute(
                    f"""SELECT f.chunk_id FROM rag_fts f JOIN knowledge_versions v ON v.id=f.version_id
                    WHERE rag_fts MATCH ? AND {ELIGIBLE} AND v.machine_id=? ORDER BY bm25(rag_fts) LIMIT 20""",
                    (" OR ".join('"' + w + '"' for w in query_terms), self.machine_id),
                ).fetchall()
            if not rows:
                return []
            q = np.asarray(model.get_query_embedding(query), dtype=np.float32)
            q = q / max(float(np.linalg.norm(q)), 1e-12)
            scores = {}
            for row in rows:
                vector = np.frombuffer(row["vector"], dtype=np.float32)
                scores[row["id"]] = float(
                    np.dot(q, vector) / max(float(np.linalg.norm(vector)), 1e-12)
                )
            # Conservative evidence gate: meaningful term overlap plus semantic similarity.
            # This intentionally abstains on some paraphrases; scores are not confidence.
            eligible = {
                r["id"]
                for r in rows
                if scores[r["id"]] >= 0.35
                and set(query_terms) & set(terms(r["content"]))
            }
            vectors = sorted(eligible, key=lambda key: (-scores[key], key))[:20]
            lexical_ids = [r["chunk_id"] for r in lexical if r["chunk_id"] in eligible]
            fused = defaultdict(float)
            for branch in (vectors, lexical_ids):
                for rank, chunk_id in enumerate(branch, 1):
                    fused[chunk_id] += 1 / (60 + rank)
            lookup = {r["id"]: r for r in rows}
            result = []
            for chunk_id in sorted(fused, key=lambda key: (-fused[key], key))[:5]:
                row = lookup[chunk_id]
                node = TextNode(
                    id_=chunk_id,
                    text=row["content"],
                    metadata={
                        k: row[k]
                        for k in (
                            "record_id",
                            "version_id",
                            "title",
                            "machine_id",
                            "fingerprint",
                        )
                    },
                    excluded_embed_metadata_keys=[
                        "record_id",
                        "version_id",
                        "title",
                        "machine_id",
                        "fingerprint",
                    ],
                )
                result.append(NodeWithScore(node=node, score=fused[chunk_id]))
            return result
