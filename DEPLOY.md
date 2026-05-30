# Deploy checklist ($0 tiers)

Everything below runs on free tiers. Items marked **[you]** need your account /
credentials — I can't create those or push to your hosts for you, but the configs
are all wired and ready.

## 1. Backend → Render (Docker, free web service)
1. **[you]** Push this repo to GitHub.
2. **[you]** In Render: New → Blueprint → pick this repo. It reads `render.yaml`
   (Docker build from `backend/Dockerfile`, health check `/api/health`).
3. Note the service URL, e.g. `https://aegis-backend.onrender.com`.
   - WebSocket endpoint: `wss://aegis-backend.onrender.com/ws`.
4. Optional env (Render dashboard → Environment):
   - `SAR_MODEL=groq/llama-3.1-70b-versatile` + `GROQ_API_KEY` **[you]** — LLM SARs.
   - `REDIS_URL` **[you, Upstash]** — Redis Streams bus.
   - `DATABASE_URL` **[you, Supabase/Neon]** — Postgres instead of SQLite.
   - `ENABLE_ETH=true` + `ETH_WS_URL` **[you, free node provider]** — ETH feed.

> Render free instances sleep when idle and have limited egress; the demo fallback
> keeps the wall alive even if a feed can't connect. For an always-on live feed,
> Fly.io or a small always-on instance is smoother.

## 2. Frontend → Vercel
1. **[you]** Vercel → Import Project → select the `ui/` directory.
2. **[you]** Set env `NEXT_PUBLIC_API_BASE` = your backend URL (https://…). The WS
   URL is derived automatically (`https`→`wss`).
3. Deploy. The wall is live at your Vercel URL.

## 3. Managed services (optional, all free tier)
- **Upstash Redis** **[you]** → copy the `redis://` URL into `REDIS_URL`.
- **Supabase / Neon Postgres** **[you]** → copy the connection string into
  `DATABASE_URL`. Uncomment `psycopg[binary]` in `backend/requirements.txt`.
- **Groq / Gemini** **[you]** → API key for LLM-drafted SARs. (Or run **Ollama**
  locally and set `SAR_MODEL=ollama/llama3` for a $0 local LLM.)

## 4. Sanctions list refresh (automatic)
`.github/workflows/nightly-lists.yml` refreshes OFAC lists nightly and commits them.
No action needed beyond enabling Actions on the repo **[you]**.

## 5. CI gates
`.github/workflows/ci.yml` trains a baseline model and runs the eval gates
(parity/latency/detection) + UI build on every push.

---

### What I can't do for you
- Create Render/Vercel/Upstash/Supabase accounts or push to them (needs your creds).
- Provide third-party API keys (Groq/Gemini/ETH RPC).

Everything else — code, Docker images, deploy manifests, CI — is done and verified
to build/run locally.
