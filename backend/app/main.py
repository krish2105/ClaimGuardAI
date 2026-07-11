from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import routes_analytics, routes_claims, routes_escalations, ws
from app.config import get_settings

settings = get_settings()

app = FastAPI(
    title="ClaimGuard AI",
    description="Agentic health insurance claims triage & prior-authorization RAG assistant (UAE market, synthetic data).",
    version="1.0.0",
)

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
app.include_router(ws.router)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "llm_mock_mode": settings.llm_mock_mode,
    }
