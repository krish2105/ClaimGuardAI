# Deploying ClaimGuard AI to a public URL

This gets you a real `https://` link anyone can open — not just something that
works on your own machine. Two free-tier hosts, no server administration,
and everything self-hosted (no separate Qdrant Cloud account needed):

| Piece | Where | Why |
|---|---|---|
| Frontend (Next.js) | [Vercel](https://vercel.com) | zero-config Next.js hosting |
| Backend (FastAPI) + Postgres + Qdrant | [Render](https://render.com) | one Blueprint (`render.yaml` in this repo) deploys all three in one step |

You'll do the account clicks (I can't create accounts or paste API keys on
your behalf); everything else — including the one-time data load — is a
single `curl` command, no shell access to the host required.

---

## 1. Render — backend + Postgres + Qdrant

1. Push this repo to your GitHub (already done — `krish2105/ClaimGuardAI`, branch `claude/claimguard-ai-build-wchf2x`).
2. Go to https://dashboard.render.com/blueprints → **New Blueprint Instance** → pick this repo/branch. Render reads `render.yaml` at the repo root and provisions three things in one step:
   - a free Postgres database (`claimguard-postgres`)
   - a **private** Qdrant service (`claimguard-qdrant`) — internal-only, not reachable from outside Render, so nobody but your own backend can hit it
   - the FastAPI backend (`claimguard-backend`), built from `backend/Dockerfile`
3. Render will ask you to fill in a couple of env vars it can't infer (marked `sync: false` in `render.yaml`):
   - `CORS_ORIGINS` → leave blank for now; you'll set this in step 3 below once you have your Vercel URL
   - `ANTHROPIC_API_KEY` → optional; leave blank to run in mock mode (no cost, fully functional), or paste a real key for live Claude calls
   - `ADMIN_SEED_TOKEN` is generated automatically by Render (`generateValue: true`) — you don't need to set it, just go find the value Render generated: `claimguard-backend` → **Environment** tab, after the first deploy.
4. Deploy (first build takes a few minutes — it's building the Docker image and downloading dependencies). Once live, note the backend's URL, e.g. `https://claimguard-backend.onrender.com`.

### Load the data (one HTTP call, no shell needed)

Render's free tier gives you no interactive shell, and Qdrant is a *private*
service with no external address — so instead of running scripts against a
remote database from your laptop, this repo exposes a one-time bootstrap
endpoint on the backend itself (`app/api/routes_admin.py`). It generates the
synthetic dataset, seeds Postgres, embeds the policy corpus into Qdrant,
trains the fraud model, and runs all 400 claims through the pipeline — all
in the background, inside Render's network where everything can actually
reach everything else.

```bash
# Get ADMIN_SEED_TOKEN from Render → claimguard-backend → Environment
curl -X POST https://claimguard-backend.onrender.com/admin/seed \
  -H "X-Admin-Token: <the generated token>"

# Poll until status is "done" (takes about a minute)
curl https://claimguard-backend.onrender.com/admin/seed/status
```

> The free-tier Qdrant private service has no persistent disk, so its index
> is wiped on every redeploy/restart of that service specifically — just
> re-run the `curl` above afterward (it's idempotent; safe to run more than
> once). Upgrade `claimguard-qdrant` to a paid instance type with a disk in
> `render.yaml` if you want the index to survive restarts.

## 2. Vercel — frontend

1. Go to https://vercel.com/new, import `krish2105/ClaimGuardAI`.
2. Set **Root Directory** to `frontend` (important — the Next.js app lives in a subfolder).
3. Add environment variables:
   - `NEXT_PUBLIC_API_BASE_URL` = your Render backend URL from step 1 (e.g. `https://claimguard-backend.onrender.com`)
   - `NEXT_PUBLIC_WS_BASE_URL` = the same host with `wss://` instead of `https://` (e.g. `wss://claimguard-backend.onrender.com`)
4. Deploy. Vercel gives you a URL like `https://claim-guard-ai.vercel.app` — **this is the real, shareable link.**

## 3. Close the loop

Go back to Render → `claimguard-backend` → Environment → set `CORS_ORIGINS` to your Vercel URL from step 2, and let it redeploy so the backend accepts requests from the live frontend.

---

That's it — `https://<your-project>.vercel.app` now works for anyone, from any device, no local setup required.

## If you'd rather use a real, persistent Qdrant Cloud cluster instead

The self-hosted approach above is the path of least resistance (no extra
account, works within Render's free tier). If you'd prefer a managed Qdrant
Cloud cluster instead (free 1GB tier, persists across restarts):

1. Sign up at https://cloud.qdrant.io and create a cluster; copy its URL and API key.
2. In `render.yaml`, delete the `claimguard-qdrant` private service block entirely, and change the backend's `QDRANT_URL` env var to `sync: false` instead of a hardcoded value, and add a `QDRANT_API_KEY` env var (also `sync: false`).
3. After deploying, paste the Qdrant Cloud URL/key into Render's dashboard for those two variables.
4. The `/admin/seed` endpoint works exactly the same either way — it doesn't need to know which kind of Qdrant it's talking to.
