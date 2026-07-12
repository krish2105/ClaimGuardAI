from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from app.api import routes_admin, routes_analytics, routes_claims, routes_escalations, ws
from app.config import get_settings
from app.rate_limit import limiter

settings = get_settings()

app = FastAPI(
    title="ClaimGuard AI",
    description="Agentic health insurance claims triage & prior-authorization RAG assistant (UAE market, synthetic data).",
    version="1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(routes_claims.router)
app.include_router(routes_escalations.router)
app.include_router(routes_analytics.router)
app.include_router(routes_admin.router)
app.include_router(ws.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_mock_mode": settings.llm_mock_mode,
    }
