# =============================================================================
# AI Gateway — main.py
# FastAPI-based master API key router for the unified self-hosted AI platform.
#
# Endpoints:
#   POST /v1/chat              → Ollama (LLM chat, OpenAI-compatible)
#   POST /v1/code              → Ollama (code model, OpenAI-compatible)
#   POST /v1/generate-image    → Automatic1111 REST API
#   POST /v1/rag/query         → ChromaDB similarity search
#   POST /v1/rag/ingest        → ChromaDB document ingestion
#   GET  /v1/models            → List available Ollama models
#   POST /auth/token           → Issue a short-lived JWT from a master key
#   GET  /health               → Health probe (used by Docker healthcheck)
#   GET  /admin/keys           → List active key aliases (admin key required)
#
# Auth flow:
#   Every request must include header:  Authorization: Bearer <key>
#   <key> is either:
#     - A static master key from GATEWAY_API_KEYS env var  (sk-local-xxx)
#     - A short-lived JWT obtained from POST /auth/token
#
# Rate limiting:
#   RATE_LIMIT_PER_MINUTE env var caps requests per key per 60-second window.
# =============================================================================

from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import httpx
from fastapi import Depends, FastAPI, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

# =============================================================================
# CONFIGURATION
# =============================================================================

class Settings(BaseSettings):
    # Comma-separated list of valid static master API keys
    gateway_api_keys: str = "sk-local-CHANGE_ME_1"
    # Internal service base URLs
    ollama_url: str = "http://ollama:11434"
    chromadb_url: str = "http://chromadb:8000"
    auto1111_url: str = "http://auto1111:7860"
    # JWT settings
    jwt_secret: str = "CHANGE_ME_jwt_secret"
    jwt_algorithm: str = "HS256"
    jwt_expiry_seconds: int = 86400
    # Rate limiting (requests per minute per API key)
    rate_limit_per_minute: int = 60
    # Logging
    log_level: str = "info"

    class Config:
        env_file = ".env"


settings = Settings()

# Parse the comma-separated key list into a set for O(1) lookup
VALID_KEYS: set[str] = {
    k.strip() for k in settings.gateway_api_keys.split(",") if k.strip()
}

# =============================================================================
# LOGGING
# =============================================================================

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger("gateway")

# =============================================================================
# RATE LIMITING
# =============================================================================

def _get_key_identifier(request: Request) -> str:
    """Use the Bearer token as the rate-limit key (falls back to IP)."""
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[7:40]  # first 33 chars of token — enough to identify it
    return get_remote_address(request)


limiter = Limiter(key_func=_get_key_identifier)

# =============================================================================
# APP
# =============================================================================

app = FastAPI(
    title="Local AI Gateway",
    description="Master API key router for the self-hosted AI platform.",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Shared async HTTP client — reused across requests for connection pooling
_http_client: Optional[httpx.AsyncClient] = None


@app.on_event("startup")
async def startup():
    global _http_client
    _http_client = httpx.AsyncClient(timeout=httpx.Timeout(120.0, connect=10.0))
    log.info("Gateway started. Valid key count: %d", len(VALID_KEYS))


@app.on_event("shutdown")
async def shutdown():
    if _http_client:
        await _http_client.aclose()

# =============================================================================
# AUTHENTICATION HELPERS
# =============================================================================

security = HTTPBearer(auto_error=False)


def _verify_static_key(token: str) -> bool:
    return token in VALID_KEYS


def _verify_jwt(token: str) -> Optional[Dict[str, Any]]:
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
        return payload
    except JWTError:
        return None


def _issue_jwt(key_alias: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {
        "sub": key_alias,
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_expiry_seconds),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


async def require_auth(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> str:
    """Dependency — validates either a static key or a JWT. Returns the key/subject."""
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header. Use: Bearer <api-key>",
            headers={"WWW-Authenticate": "Bearer"},
        )
    token = credentials.credentials
    # 1. Try static key
    if _verify_static_key(token):
        return token
    # 2. Try JWT
    payload = _verify_jwt(token)
    if payload:
        return payload.get("sub", token)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired API key.",
        headers={"WWW-Authenticate": "Bearer"},
    )


# =============================================================================
# PYDANTIC MODELS
# =============================================================================

class ChatMessage(BaseModel):
    role: str = Field(..., examples=["user"])
    content: str


class ChatRequest(BaseModel):
    model: str = Field(default="mistral:7b-instruct-q4_K_M")
    messages: List[ChatMessage]
    stream: bool = False
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)


class CodeRequest(BaseModel):
    model: str = Field(default="deepseek-coder:6.7b-instruct-q4_K_M")
    messages: List[ChatMessage]
    stream: bool = False
    temperature: float = Field(default=0.2, ge=0.0, le=2.0)
    max_tokens: Optional[int] = Field(default=None, ge=1)


class ImageRequest(BaseModel):
    prompt: str = Field(..., min_length=1)
    negative_prompt: str = ""
    width: int = Field(default=512, ge=64, le=1024)
    height: int = Field(default=512, ge=64, le=1024)
    steps: int = Field(default=20, ge=1, le=150)
    cfg_scale: float = Field(default=7.0, ge=1.0, le=30.0)
    sampler_name: str = "Euler a"
    # Number of images to generate (1 recommended for 12 GB VRAM)
    batch_size: int = Field(default=1, ge=1, le=4)


class RAGIngestRequest(BaseModel):
    collection_name: str
    documents: List[str]
    ids: Optional[List[str]] = None
    metadatas: Optional[List[Dict[str, Any]]] = None


class RAGQueryRequest(BaseModel):
    collection_name: str
    query: str
    n_results: int = Field(default=5, ge=1, le=20)


class TokenRequest(BaseModel):
    api_key: str


# =============================================================================
# HEALTH
# =============================================================================

@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "timestamp": int(time.time())}


# =============================================================================
# AUTH ENDPOINTS
# =============================================================================

@app.post("/auth/token", tags=["auth"])
async def issue_token(body: TokenRequest):
    """
    Exchange a valid static master API key for a short-lived JWT.
    The JWT can be used as a Bearer token for all other endpoints.
    Expiry is controlled by JWT_EXPIRY_SECONDS (default: 24 hours).
    """
    if not _verify_static_key(body.api_key):
        raise HTTPException(status_code=401, detail="Invalid API key.")
    token = _issue_jwt(body.api_key[:12] + "***")
    return {
        "access_token": token,
        "token_type": "bearer",
        "expires_in": settings.jwt_expiry_seconds,
    }


# =============================================================================
# MODELS LIST
# =============================================================================

@app.get("/v1/models", tags=["models"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def list_models(
    request: Request,
    _key: str = Depends(require_auth),
):
    """Return the list of locally available Ollama models."""
    try:
        resp = await _http_client.get(f"{settings.ollama_url}/api/tags")
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        log.error("Ollama /api/tags failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Ollama unreachable: {exc}")


# =============================================================================
# CHAT — proxies to Ollama /api/chat (OpenAI-compatible format)
# =============================================================================

@app.post("/v1/chat", tags=["inference"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def chat(
    request: Request,
    body: ChatRequest,
    _key: str = Depends(require_auth),
):
    """
    Chat with a local LLM via Ollama.
    Default model: mistral:7b-instruct-q4_K_M
    Supports streaming when stream=true.
    """
    payload = {
        "model": body.model,
        "messages": [m.model_dump() for m in body.messages],
        "stream": body.stream,
        "options": {
            "temperature": body.temperature,
            **({"num_predict": body.max_tokens} if body.max_tokens else {}),
        },
    }
    log.info("CHAT | model=%s | stream=%s | key=%.12s", body.model, body.stream, _key)

    if body.stream:
        return StreamingResponse(
            _stream_ollama(payload),
            media_type="text/event-stream",
        )

    try:
        resp = await _http_client.post(
            f"{settings.ollama_url}/api/chat",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        log.error("Ollama /api/chat failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")


async def _stream_ollama(payload: dict):
    """Async generator that streams Ollama response as SSE."""
    async with _http_client.stream(
        "POST", f"{settings.ollama_url}/api/chat", json=payload
    ) as resp:
        async for line in resp.aiter_lines():
            if line:
                yield f"data: {line}\n\n"
    yield "data: [DONE]\n\n"


# =============================================================================
# CODE ASSISTANT — same Ollama backend, different default model
# =============================================================================

@app.post("/v1/code", tags=["inference"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def code_assistant(
    request: Request,
    body: CodeRequest,
    _key: str = Depends(require_auth),
):
    """
    Code generation and completion via DeepSeek Coder on Ollama.
    Lower default temperature (0.2) for more deterministic code output.
    """
    payload = {
        "model": body.model,
        "messages": [m.model_dump() for m in body.messages],
        "stream": body.stream,
        "options": {
            "temperature": body.temperature,
            **({"num_predict": body.max_tokens} if body.max_tokens else {}),
        },
    }
    log.info("CODE | model=%s | key=%.12s", body.model, _key)

    if body.stream:
        return StreamingResponse(
            _stream_ollama(payload),
            media_type="text/event-stream",
        )

    try:
        resp = await _http_client.post(
            f"{settings.ollama_url}/api/chat",
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()
    except httpx.HTTPError as exc:
        log.error("Ollama code failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Ollama error: {exc}")


# =============================================================================
# IMAGE GENERATION — proxies to Automatic1111 /sdapi/v1/txt2img
# =============================================================================

@app.post("/v1/generate-image", tags=["inference"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def generate_image(
    request: Request,
    body: ImageRequest,
    _key: str = Depends(require_auth),
):
    """
    Generate images via Stable Diffusion (Automatic1111).
    Returns base64-encoded PNG(s) in the 'images' field.
    RTX 3060 12GB can comfortably handle 512x512 and 768x768.
    For 1024x1024 use steps <= 20 to avoid OOM.
    """
    payload = {
        "prompt": body.prompt,
        "negative_prompt": body.negative_prompt,
        "width": body.width,
        "height": body.height,
        "steps": body.steps,
        "cfg_scale": body.cfg_scale,
        "sampler_name": body.sampler_name,
        "batch_size": body.batch_size,
    }
    log.info(
        "IMAGE | size=%dx%d | steps=%d | key=%.12s",
        body.width, body.height, body.steps, _key
    )
    try:
        resp = await _http_client.post(
            f"{settings.auto1111_url}/sdapi/v1/txt2img",
            json=payload,
            timeout=300.0,  # image gen can take 30-120s on first run
        )
        resp.raise_for_status()
        data = resp.json()
        return {
            "images": data.get("images", []),
            "parameters": data.get("parameters", {}),
            "info": data.get("info", ""),
        }
    except httpx.HTTPError as exc:
        log.error("Auto1111 txt2img failed: %s", exc)
        raise HTTPException(status_code=502, detail=f"Auto1111 error: {exc}")


# =============================================================================
# RAG — ChromaDB document ingestion and similarity search
# =============================================================================

@app.post("/v1/rag/ingest", tags=["rag"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def rag_ingest(
    request: Request,
    body: RAGIngestRequest,
    _key: str = Depends(require_auth),
):
    """
    Ingest documents into a ChromaDB collection.
    Creates the collection if it does not exist.
    Provide 'ids' for deterministic deduplication.
    """
    # Ensure the collection exists
    collection_url = f"{settings.chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections"

    # Check if collection exists
    try:
        list_resp = await _http_client.get(collection_url)
        list_resp.raise_for_status()
        existing = {c["name"] for c in list_resp.json()}
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"ChromaDB unreachable: {exc}")

    if body.collection_name not in existing:
        create_resp = await _http_client.post(
            collection_url,
            json={"name": body.collection_name, "get_or_create": True},
        )
        if create_resp.status_code not in (200, 201):
            raise HTTPException(status_code=502, detail="Failed to create ChromaDB collection.")
        collection_id = create_resp.json()["id"]
    else:
        # Get collection id
        get_resp = await _http_client.get(f"{collection_url}/{body.collection_name}")
        get_resp.raise_for_status()
        collection_id = get_resp.json()["id"]

    # Add documents
    add_url = f"{settings.chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/add"
    ids = body.ids or [f"doc_{int(time.time())}_{i}" for i in range(len(body.documents))]
    add_payload: Dict[str, Any] = {"ids": ids, "documents": body.documents}
    if body.metadatas:
        add_payload["metadatas"] = body.metadatas

    try:
        add_resp = await _http_client.post(add_url, json=add_payload)
        add_resp.raise_for_status()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"ChromaDB add failed: {exc}")

    log.info(
        "RAG INGEST | collection=%s | docs=%d | key=%.12s",
        body.collection_name, len(body.documents), _key
    )
    return {"status": "ingested", "collection": body.collection_name, "count": len(body.documents)}


@app.post("/v1/rag/query", tags=["rag"])
@limiter.limit(f"{settings.rate_limit_per_minute}/minute")
async def rag_query(
    request: Request,
    body: RAGQueryRequest,
    _key: str = Depends(require_auth),
):
    """
    Query a ChromaDB collection for the top-N most similar documents.
    Returns documents, distances, and metadatas.
    """
    collection_url = f"{settings.chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{body.collection_name}"

    try:
        coll_resp = await _http_client.get(collection_url)
        if coll_resp.status_code == 404:
            raise HTTPException(status_code=404, detail=f"Collection '{body.collection_name}' not found.")
        coll_resp.raise_for_status()
        collection_id = coll_resp.json()["id"]
    except httpx.HTTPStatusError:
        raise
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"ChromaDB unreachable: {exc}")

    query_url = f"{settings.chromadb_url}/api/v2/tenants/default_tenant/databases/default_database/collections/{collection_id}/query"
    query_payload = {
        "query_texts": [body.query],
        "n_results": body.n_results,
        "include": ["documents", "distances", "metadatas"],
    }

    try:
        qresp = await _http_client.post(query_url, json=query_payload)
        qresp.raise_for_status()
        result = qresp.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"ChromaDB query failed: {exc}")

    log.info(
        "RAG QUERY | collection=%s | n=%d | key=%.12s",
        body.collection_name, body.n_results, _key
    )
    return {
        "collection": body.collection_name,
        "query": body.query,
        "results": {
            "documents": result.get("documents", [[]])[0],
            "distances": result.get("distances", [[]])[0],
            "metadatas": result.get("metadatas", [[]])[0],
        },
    }


# =============================================================================
# ADMIN — key listing (requires a valid key; no separate admin tier in v1)
# =============================================================================

@app.get("/admin/keys", tags=["admin"])
async def list_key_aliases(_key: str = Depends(require_auth)):
    """Return masked versions of all active static API keys."""
    masked = [k[:8] + "****" + k[-4:] if len(k) > 12 else "****" for k in VALID_KEYS]
    return {"active_keys": sorted(masked), "count": len(VALID_KEYS)}
