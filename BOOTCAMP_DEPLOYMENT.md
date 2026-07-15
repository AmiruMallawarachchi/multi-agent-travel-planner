# TripWeaver bootcamp deployment

This is the zero-payment demo path:

```text
Vercel Hobby frontend
  -> Render Free FastAPI backend
  -> Supabase Free Postgres for accounts and conversation history
```

Do not paste secrets into chat, commit them, or place them in `.env` files that
Git can track. Add secrets only inside the Vercel, Render, and Supabase
dashboards.

## 1. GitHub

Repository:

```text
https://github.com/AmiruMallawarachchi/multi-agent-travel-planner
```

All deploy platforms should connect to this repository. Codex can keep working
by pushing feature branches and pull requests to GitHub; Vercel and Render can
then deploy from those branches or from `dev` after you merge.

## 2. Supabase

Create a new Supabase project for TripWeaver.

Copy the database connection string from:

```text
Supabase project -> Project Settings -> Database -> Connection string
```

Use the pooled connection string when available. It usually starts with
`postgresql://` and contains your database password. This value is the backend
`DATABASE_URL`.

Supabase is used here as managed Postgres storage for:

- users
- auth sessions
- per-user conversation history

TripWeaver still owns the register/login API. Supabase Auth is not required for
this bootcamp deployment.

## 3. Render backend

Use Render Blueprint or create one web service manually.

### Blueprint path

1. Render -> New -> Blueprint
2. Select the GitHub repository.
3. Render reads `render.yaml`.
4. Create the `tripweaver-backend` service on the Free plan.

### Manual path

Use these settings if you create the Render service manually:

```text
Service type: Web Service
Repository: AmiruMallawarachchi/multi-agent-travel-planner
Root directory: backend
Runtime: Docker
Dockerfile: backend/Dockerfile
Health check path: /health
Plan: Free
```

Set these Render environment variables:

```text
OPENAI_API_KEY=your OpenAI key
DATABASE_URL=your Supabase Postgres connection string
TRIPWEAVER_API_KEYS=make one long random string
ALLOWED_ORIGINS=https://your-vercel-project.vercel.app,http://localhost:3000
ROUTER_MODEL=gpt-4o-mini
AGENT_MODEL=gpt-4o-mini
RATE_LIMIT_REQUESTS=20
RATE_LIMIT_WINDOW_SECONDS=60
MAX_MESSAGE_LENGTH=2000
```

Optional when live search tools are enabled:

```text
SERPAPI_API_KEY=your SerpApi key
```

After deploy, Render gives you a backend URL like:

```text
https://tripweaver-backend.onrender.com
```

Open:

```text
https://tripweaver-backend.onrender.com/health
```

Expected backend result:

```json
{
  "status": "ok",
  "service": "tripweaver-backend"
}
```

## 4. Vercel frontend

Your Vercel project is:

```text
https://vercel.com/amirunoel8-7855s-projects/multi-agent-travel-planner
```

Project settings should be:

```text
Framework: Next.js
Root Directory: frontend
Install Command: npm install
Build Command: npm run build
Output Directory: .next
```

Set these Vercel environment variables:

```text
BACKEND_URL=https://tripweaver-backend.onrender.com
BACKEND_API_KEY=the same value used in Render TRIPWEAVER_API_KEYS
```

Deploy Vercel after Render is live.

Open:

```text
https://your-vercel-project.vercel.app/api/health
```

Expected frontend proxy result:

```json
{
  "online": true,
  "backend": "online",
  "service": "tripweaver-frontend"
}
```

## 5. What works on this free demo path

This path supports:

- polished responsive Next.js UI on Vercel
- backend API on Render
- user registration and login
- per-user conversation history persisted in Supabase Postgres
- server-side proxying so browser users never receive backend API keys
- OpenAI-backed general chat when `OPENAI_API_KEY` has quota

## 6. Current limitation

The full TripWeaver production stack has one backend plus six separate MCP
services. Render Free is not a good fit for seven always-on backend services.

For the bootcamp demo, the next engineering step is to collapse the MCP calls
into a single-process backend mode or keep only the most important tools live.
Until that is done, the backend can still deploy on Render, but unavailable MCP
services will appear as unavailable in the UI.

Recommended next phase:

```text
TRIPWEAVER_TOOL_MODE=local
```

In that mode, the backend should call provider clients in-process instead of
requiring six separate MCP web services. That keeps the demo inside one Render
Free service.

## 7. Zero-payment safety

Use only:

- Vercel Hobby
- Render Free
- Supabase Free

Do not add a credit card-only paid compute service for this demo. Render Free
can sleep after inactivity, so the first request may be slow. That is acceptable
for a bootcamp demo, but not for a real production launch.

