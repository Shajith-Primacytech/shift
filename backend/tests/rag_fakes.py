"""Offline test doubles only. Production uses real MiniLM and the AMD adapter."""

import json

import httpx

from app.config import AMDSettings
from app.inference.amd import AMDInference
from app.rag.retrieval import ApprovedRetriever


class ConstantEmbedding:
    # Not a semantic model; isolates SQL/approval/citation behavior in unit tests.
    def get_text_embedding_batch(self, texts):
        return [[1.0] * 384 for _ in texts]

    def get_query_embedding(self, text):
        return [1.0] * 384


def test_retriever(path, machine):
    return ApprovedRetriever(
        path,
        machine,
        embed_model=ConstantEmbedding(),
        embedding_key="test-only-constant-384",
        token_fn=lambda text: text.split(),
    )


def selection(request):
    payload = json.loads(request.content)
    evidence = json.loads(payload["messages"][1]["content"])["approved_evidence"]
    steps = []
    for source in evidence[:2]:
        steps.append(
            {
                "source_id": source["source_id"],
                "passage_id": source["passages"][-1]["passage_id"],
            }
        )
    return {"sufficient": bool(steps), "steps": steps}


def response_for(selection_data):
    return httpx.Response(
        200,
        json={
            "model": "test-only-mocked-amd",
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": json.dumps(selection_data),
                    },
                    "finish_reason": "stop",
                }
            ],
            "usage": {"prompt_tokens": 20, "completion_tokens": 20, "total_tokens": 40},
        },
    )


def mocked_provider(handler=None):
    return AMDInference(
        AMDSettings(
            _env_file=None, AMD_API_KEY="synthetic-rag-test-token", AMD_MAX_RETRIES=0
        ),
        transport=httpx.MockTransport(
            handler or (lambda request: response_for(selection(request)))
        ),
    )
