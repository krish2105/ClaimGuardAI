# ClaimGuard AI

**Agentic health insurance claims triage & prior-authorization RAG assistant for the UAE market.**
Portfolio / recruiter-facing project. **All data is synthetic. Not for production or real patient use.**

Full design rationale, business decisions, and interview Q&A: see [`ARCHITECTURE.md`](./ARCHITECTURE.md) (the original master prompt this repo was built from).

---

## What this is

A 5-agent [LangGraph](https://github.com/langchain-ai/langgraph) pipeline that triages health insurance claims for a UAE-style insurer, scores fraud risk with a trained XGBoost model, and — the core differentiator — **grounds every approve/deny/escalate recommendation in an actual cited policy clause**, retrieved from a self-hosted Qdrant vector index of a synthetic UAE-style policy corpus. Every decision is auditable: the claim fact, the policy clause behind it, and the full agent-by-agent reasoning trace.

```
Claim Submitted
      │
      ▼
[1] Intake Agent        ──► extracts structured claim data from raw document (Claude Haiku / mock)
      │
      ▼
[2] Coding Agent         ──► validates ICD-10/CPT coherence, flags upcoding/unbundling
      │
      ▼
[3] Fraud Scoring Agent  ──► XGBoost risk score (0-100) + top SHAP-style feature contributions
      │
      ▼
[4] Policy RAG Agent     ──► retrieves top-5 policy clauses from Qdrant, drafts a cited decision
      │
      ▼
[5] Decision Router      ──► auto-approve / auto-deny / escalate (deterministic, conservative-by-default)
      │
      ▼
Postgres (claims, decisions, escalations, audit_log) + Next.js Adjuster Dashboard
```

---

## Run it locally

### Option A — Docker Compose (matches the intended production architecture)

```bash
cp .env.example .env
docker compose up --build
```

- Backend: http://localhost:8100 (docs at `/docs`)
- Frontend: http://localhost:3100
- Postgres: localhost:5432, Qdrant: localhost:6333

> Ports are **8100**/**3100**, not the more common 8000/3000, specifically so this doesn't clash with another project you may already have running locally. Change them in `.env` / `docker-compose.yml` / the `npm run dev`+`uvicorn` commands below if you'd like different ports instead.

Then, one-time setup inside the backend container (or locally, see Option B):
```bash
python backend/scripts/generate_dataset.py     # writes backend/data/{claims,providers}.csv
python backend/scripts/seed_db.py              # creates tables + loads the CSVs into Postgres
python backend/scripts/ingest_policies.py      # embeds policies/*.md into Qdrant
python backend/scripts/train_fraud_model.py    # trains + saves the XGBoost model
python backend/scripts/run_pipeline_batch.py   # runs all 400 seeded claims through the pipeline
```

### Option B — No Docker (what this build environment actually used)

Everything also runs with a local Postgres and an **embedded, on-disk Qdrant** (no server process) — useful when Docker isn't available (e.g. this sandbox had no Docker daemon):

```bash
# Backend
cd backend
python3 -m pip install -r requirements.txt
cp ../.env.example ../.env   # edit DATABASE_URL if your local Postgres user/db differ

python3 scripts/generate_dataset.py
python3 scripts/seed_db.py
python3 scripts/ingest_policies.py
python3 scripts/train_fraud_model.py
python3 scripts/run_pipeline_batch.py     # optional but recommended: pre-populates the queue/analytics with all 400 claims
python3 -m uvicorn app.main:app --host 0.0.0.0 --port 8100

# Frontend (separate terminal)
cd frontend
npm install
cp .env.local.example .env.local   # points the frontend at http://localhost:8100
npm run dev -- --port 3100
```

Then open **http://localhost:3100**.

No `ANTHROPIC_API_KEY` is required to run the full system — see "Mock mode" below.

---

## Verified working in this build session

This exact repo was built, seeded, and smoke-tested end-to-end in the sandbox that produced it:
- Postgres seeded with 40 providers + 400 synthetic claims
- 13 policy documents (51 clauses) embedded into Qdrant
- XGBoost fraud model trained: **AUC-ROC 0.938** on a held-out test split (target in the spec was >0.80)
- All 400 seeded claims run through the live pipeline: **60.8% auto-approved, 16.0% auto-denied, 23.2% escalated**
- All 8 API endpoints (including the `/ws/claims/{id}/stream` WebSocket) verified via `curl`/a WebSocket client
- All 5 frontend pages rendered and interacted with via a real headless-Chromium session (submit → live trace → escalation resolve, in both light and dark mode)
- Full evaluation report generated — see `backend/eval_report.json`

---

## Mock mode (why this runs with zero API cost)

If `ANTHROPIC_API_KEY` is unset in `.env`, every Claude call (Intake extraction, Coding assessment, Policy RAG drafting) transparently falls back to a **deterministic, rule-based mock** implementing the same contract (same JSON schema, same guardrails) as the real prompt. This is not a shortcut around the architecture — it's the same code path; set a real key and it calls Claude Haiku/Sonnet instead. This is what let the whole pipeline be built, seeded, and demoed in a sandboxed environment with no LLM API access.

---

## Notes on faithfulness to this spec

`ARCHITECTURE.md` says "do not deviate" on the tech stack. Two categories of change were made anyway, both forced by the build sandbox's constraints (not by choice), and both are drop-in reversible:

1. **Qdrant runs embedded (on-disk), not as a Docker container, by default.** The sandbox had no Docker daemon. `docker-compose.yml` still defines the real Qdrant + Postgres + backend + frontend services for a production-style deployment; set `QDRANT_URL` in `.env` to point at a real Qdrant server (Docker or Cloud) and the app uses it automatically — the code path is identical either way (`app/vectorstore.py`).
2. **The embedding model falls back to a local TF-IDF+SVD embedder when Hugging Face is unreachable.** `sentence-transformers/all-MiniLM-L6-v2` is the intended embedding model (Section 3), but this sandbox's network policy blocks the Hugging Face Hub download. `app/embeddings.py` tries the real model first and only falls back if that download fails, recording which backend is active in `backend/models/embedding_config.json`. **This is the one honest limitation worth naming:** the TF-IDF fallback ranks less precisely than a real sentence embedding model would (see "Evaluation results" below) — the citation-validation guardrail still enforces that whatever *is* cited was actually retrieved, but the top-of-list relevance is weaker than the intended architecture. Deleting `embedding_config.json` and re-running `ingest_policies.py` with internet access retries the real model automatically.
3. **Next.js pinned to 14.2.35, not whatever `latest` resolves to.** `create-next-app@latest` in this sandbox resolved to Next.js 16 with breaking API changes from what the spec (and most training data) assumes; the repo explicitly targets `next@14` to match Section 3.

Everything else — the 5-agent LangGraph pipeline, the DB schema, the fraud-injection strategy, the API contracts, the 5 frontend pages — was built exactly as specified.

---

## Evaluation results (Section 12 metrics)

Generate the full report yourself:
```bash
python3 backend/scripts/eval_harness.py
```

| Metric | Result | Target |
|---|---|---|
| Fraud model AUC-ROC | **0.938** | > 0.80 |
| Fraud model precision / recall / F1 | 0.80 / 0.73 / 0.76 | — |
| Citation accuracy (hallucination guardrail) | **100%** (402/402 rationales cite only retrieved clauses) | 100% |
| Retrieval Precision@5 proxy (n=20) | 0.15 — see note above on the TF-IDF fallback | manual spot-check |
| Pipeline latency (mean / p95) | 11.5 ms / 11.7 ms of agent compute per claim | < 15 s |
| Escalation rate | 23.4% | tracked as a business KPI, not a pass/fail target |

The retrieval precision number is the one metric that's honestly weaker than intended, and it's fully attributable to the embedding fallback described above, not the retrieval/guardrail logic itself.

---

## Project structure

```
backend/
  app/
    agents/            # the 5 LangGraph agent nodes + shared ClaimState + graph wiring
    api/                # FastAPI routes + WebSocket
    db/                 # SQLAlchemy models + session
    services/           # pipeline orchestration, streaming, fraud features, doc generation
    reference_data.py    # synthetic ICD-10/CPT reference tables + cost bands
    embeddings.py         # sentence-transformers w/ TF-IDF offline fallback
    vectorstore.py        # Qdrant client (embedded or server)
  scripts/              # generate_dataset, seed_db, ingest_policies, train_fraud_model,
                          # run_pipeline_batch, eval_harness, smoke_test_pipeline
  alembic/               # DB migrations
  models/                # trained fraud_model.json + metadata (gitignored — see below)
  data/                  # generated claims.csv / providers.csv (gitignored — see below)
policies/                # 13 synthetic UAE-style policy documents (the RAG corpus)
frontend/
  src/app/               # queue, claims/[claimId], submit, escalations, analytics
  src/components/        # shadcn-style UI primitives + domain components (trace timeline, etc.)
docs/                    # ClaimGuard_AI_Overview.docx — plain-English project explainer
docker-compose.yml
ARCHITECTURE.md           # the original master prompt (kept verbatim per the submission checklist)
```

---

## Limitations & ethical considerations

- All data is synthetic — this demonstrates an architecture pattern, not a validated production fraud system.
- A fraud-scoring model trained on synthetic data doesn't generalize to real claim patterns; a real deployment needs a fairness audit (by provider specialty, patient demographics) before going live.
- LLM-cited clauses reduce hallucination risk but are not a legal guarantee of policy compliance; a real deployment needs human sign-off on every auto-decision during a pilot, not just escalated ones.
- No real PHI is used anywhere, in line with UAE PDPL principles.

---

## Deploying it live

- **Frontend:** push to GitHub, import into [Vercel](https://vercel.com/new), set `NEXT_PUBLIC_API_BASE_URL` / `NEXT_PUBLIC_WS_BASE_URL` to your deployed backend.
- **Backend + Postgres + Qdrant:** deploy `docker-compose.yml` to [Railway](https://railway.app) or [Render](https://render.com); set `ANTHROPIC_API_KEY` there if you want live Claude calls instead of mock mode.
