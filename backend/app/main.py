from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.ai import router as ai_router
from app.api.capture import router as capture_router
from app.api.speech import router as speech_router
from app.api.health import router
from app.api.storage import router as storage_router
from app.api.troubleshooting import router as troubleshooting_router
from app.config import Settings
from app.storage.database import initialize


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or Settings()

    @asynccontextmanager
    async def lifespan(app):
        initialize(settings.database_path, settings.seed_synthetic)
        yield

    app = FastAPI(
        title="SHIFT API",
        version="0.2.0",
        description="Stage 2 persistent knowledge and authenticated review",
        lifespan=lifespan,
    )
    app.state.settings = settings

    @app.middleware("http")
    async def request_security(request: Request, call_next):
        if request.method not in ("GET", "HEAD", "OPTIONS"):
            origin = request.headers.get("origin")
            if (origin and origin not in settings.cors_origins) or request.headers.get(
                "x-shift-request"
            ) != "1":
                return JSONResponse(
                    {
                        "detail": "Untrusted request origin or missing X-Shift-Request header"
                    },
                    status_code=403,
                )
            size = 0
            chunks = []
            async for chunk in request.stream():
                size += len(chunk)
                if size > 42 * 1024 * 1024:
                    return JSONResponse(
                        {"detail": "Request exceeds 42 MB"}, status_code=413
                    )
                chunks.append(chunk)
            request._body = b"".join(chunks)
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        return response

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["GET", "POST"],
        allow_headers=["Accept", "Content-Type", "X-Shift-Request"],
    )
    app.include_router(router, prefix="/api/v1")
    app.include_router(storage_router, prefix="/api/v1")
    app.include_router(troubleshooting_router, prefix="/api/v1")
    app.include_router(capture_router, prefix="/api/v1")
    app.include_router(ai_router, prefix="/api/v1")
    app.include_router(speech_router, prefix="/api/v1")
    return app


app = create_app()
