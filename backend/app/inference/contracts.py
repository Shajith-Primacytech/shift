"""Provider-independent text completion contracts. No retrieval or HTTP objects."""

from typing import Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field


class Message(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=32000)


class CompletionRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    messages: tuple[Message, ...] = Field(min_length=1, max_length=32)
    max_tokens: int = Field(default=512, ge=1, le=4096, strict=True)


class TokenUsage(BaseModel):
    model_config = ConfigDict(frozen=True)
    prompt_tokens: int | None = None
    completion_tokens: int | None = None
    total_tokens: int | None = None
    reasoning_tokens: int | None = None


class CompletionResult(BaseModel):
    model_config = ConfigDict(frozen=True)
    text: str
    provider: str
    requested_model: str
    model: str | None
    usage: TokenUsage
    finish_reason: str | None
    latency_ms: float
    attempts: int


ErrorCode = Literal[
    "configuration",
    "authentication",
    "rate_limit",
    "timeout",
    "network",
    "http",
    "model",
    "invalid_response",
]
MESSAGES = {
    "configuration": "Inference configuration is missing or invalid.",
    "authentication": "The inference provider rejected authentication or access.",
    "rate_limit": "The inference provider is rate limited. Try again later.",
    "timeout": "Inference timed out. No answer is available.",
    "network": "The inference provider could not be reached reliably.",
    "http": "The inference provider returned an unsuccessful HTTP response.",
    "model": "The model did not produce a usable complete text answer.",
    "invalid_response": "The inference provider returned an invalid completion.",
}


class InferenceError(Exception):
    """Only fixed messages and safe metadata; never retain provider payloads."""

    def __init__(
        self,
        code: ErrorCode,
        *,
        status: int | None = None,
        attempts: int = 0,
        latency_ms: float = 0,
    ):
        self.code = code
        self.status = status
        self.attempts = attempts
        self.latency_ms = latency_ms
        super().__init__(MESSAGES[code])


class InferenceProvider(Protocol):
    async def complete(self, request: CompletionRequest) -> CompletionResult: ...
