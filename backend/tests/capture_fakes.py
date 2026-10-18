"""Offline capture doubles. Never used by normal application startup."""

import json

import httpx
from app.capture.service import MODEL
from app.config import AMDSettings
from app.inference.amd import AMDInference
from app.storage.capture_schema import ProposedStructure

KEY = "synthetic-capture-test-key"


def proposal_for(source):
    result = {name: [] for name in ProposedStructure.model_fields}
    result["machineContext"] = [{"source": "machineId", "quote": source["machineId"]}]
    result["reportedSymptoms"] = [{"source": "symptom", "quote": source["symptom"]}]
    result["observations"] = [{"source": "content", "quote": source["content"]}]
    return result


def response_for(proposal):
    return httpx.Response(
        200,
        json={
            "model": "self-dploy/" + MODEL,
            "choices": [
                {
                    "message": {"role": "assistant", "content": json.dumps(proposal)},
                    "finish_reason": "stop",
                }
            ],
            "usage": {
                "prompt_tokens": 100,
                "completion_tokens": 50,
                "total_tokens": 150,
            },
        },
    )


def handler(request):
    source = json.loads(json.loads(request.content)["messages"][1]["content"])
    return response_for(proposal_for(source))


def provider(callback=handler):
    return AMDInference(
        AMDSettings(
            _env_file=None, AMD_API_KEY=KEY, AMD_MODEL=MODEL, AMD_MAX_RETRIES=0
        ),
        transport=httpx.MockTransport(callback),
    )
