# Deploying ClaimGuard AI to a public URL

This gets you a real `https://` link anyone can open — not just something that
works on your own machine. Three managed free tiers, ~15 minutes, no server
administration:

| Piece | Where | Why |
|---|---|---|
| Frontend (Next.js) | [Vercel](https://vercel.com) | zero-config Next.js hosting |
| Backend (FastAPI) + Postgres | [Render](https://render.com) | one Blueprint deploys both from `render.yaml` in this repo |
| Vector store (Qdrant) | [Qdrant Cloud](https://cloud.qdrant.io) | free 1GB cluster, no self-hosting needed |

You'll do the account clicks (I can't create accounts or paste API keys on your
behalf); everything else is copy/paste.

---

## 1. Qdrant Cloud (do this first — the backend needs its URL)

1. Sign up free at https://cloud.qdrant.io and create a cluster (free tier, ~1 min to provision).
2. Copy the cluster's **URL** (looks like `https://xxxx.cloud.qdrant.io`) and its **API key**.

## 2. Render — backend + Postgres

1. Push this repo to your GitHub (already done — `krish2105/ClaimGuardAI`, branch `claude/claimguard-ai-build-wchf2x`).
2. Go to https://dashboard.render.com/blueprints → **New Blueprint Instance** → pick this repo/branch. Render reads `render.yaml` at the repo root and provisions:
   - a free Postgres database (`claimguard-postgres`)
   - a web service (`claimguard-backend`) built from `backend/Dockerfile`
3. Render will ask you to fill in a few env vars it can't infer (marked `sync: false` in `render.yaml`):
   - `QDRANT_URL` → paste the Qdrant Cloud URL from step 1
   - `CORS_ORIGINS` → you'll fill this in *after* step 3 (Vercel), once you know your frontend's URL — you can leave it blank for now and edit it later in Render → your service → Environment.
   - `ANTHROPIC_API_KEY` → optional; leave blank to run in mock mode (no cost, fully functional), or paste a real key for live Claude calls.
4. Deploy. Once live, note the backend's URL, e.g. `https://claimguard-backend.onrender.com`.

### Seed the database and vector store (run once, from your own machine)

Render's free tier doesn't give you an interactive shell, so run the seed
scripts locally, pointed at your *remote* Postgres and Qdrant — they'll load
data into the cloud services directly:

```bash
cd backend
python3 -m pip install -r requirements.txt

# Get the external Postgres URL from Render → claimguard-postgres → "External Database URL"
export DATABASE_URL="postgresql+psycopg2://...render-external-url.../claimguard"
export QDRANT_URL="https://xxxx.cloud.qdrant.io"
export QDRANT_API_KEY="..."   # if your Qdrant Cloud client needs it, see note below

python3 scripts/generate_dataset.py
python3 scripts/seed_db.py
python3 scripts/ingest_policies.py
python3 scripts/train_fraud_model.py
python3 scripts/run_pipeline_batch.py   # populates the queue/analytics with all 400 claims
```

`QDRANT_API_KEY` is already wired up in `app/config.py`/`app/vectorstore.py` — set it (alongside `QDRANT_URL`) in both your local shell above and in Render's environment variables if your Qdrant Cloud cluster requires one.

## 3. Vercel — frontend

1. Go to https://vercel.com/new, import `krish2105/ClaimGuardAI`.
2. Set **Root Directory** to `frontend` (important — the Next.js app lives in a subfolder).
3. Add environment variables:
   - `NEXT_PUBLIC_API_BASE_URL` = your Render backend URL from step 2 (e.g. `https://claimguard-backend.onrender.com`)
   - `NEXT_PUBLIC_WS_BASE_URL` = the same host with `wss://` instead of `https://` (e.g. `wss://claimguard-backend.onrender.com`)
4. Deploy. Vercel gives you a URL like `https://claim-guard-ai.vercel.app` — **this is the real, shareable link.**

## 4. Close the loop

Go back to Render → `claimguard-backend` → Environment → set `CORS_ORIGINS` to your Vercel URL from step 3, and redeploy the backend so it accepts requests from the live frontend.

---

That's it — `https://<your-project>.vercel.app` now works for anyone, from any device, no local setup required.
