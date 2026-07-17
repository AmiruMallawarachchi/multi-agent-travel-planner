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

If the database password contains special characters, use the Supabase-provided
encoded connection string or percent-encode the password before pasting it into
Render. After any database URL has been exposed in chat, reset the Supabase
database password and use the new connection string only in Render.

Copy the publishable browser values from:

```text
Supabase project -> Project Settings -> API
```

These values go in Vercel only:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
```

Supabase is used here as managed Postgres storage for:

- users
- auth sessions
- linked Google identities
- per-user conversation history

TripWeaver still owns account records and history authorization. Supabase Auth
is also used to verify optional Google sign-in without exposing Google secrets
to the browser.

### Google sign-in

1. In Google Auth Platform, create a Web application OAuth client.
2. Add your Vercel URL as an authorized JavaScript origin.
3. Add `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback` as an authorized
   redirect URI.
4. In Supabase, open Authentication -> Providers -> Google, enable the provider,
   and enter the Google client ID and client secret.
5. In Supabase Authentication -> URL Configuration, set the Site URL to your
   Vercel URL and add `https://YOUR_VERCEL_URL/auth/callback` to Redirect URLs.

Do not put the Google client secret in Vercel, Render, Git, or frontend code.

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
Root directory: .
Runtime: Docker
Dockerfile: deploy/render/backend.Dockerfile
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
TRIPWEAVER_TOOL_MODE=local
SUPABASE_URL=your Supabase project URL
SUPABASE_PUBLISHABLE_KEY=your Supabase publishable key
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
NEXT_PUBLIC_SUPABASE_URL=your Supabase project URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your Supabase publishable key
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

### Account sign-in troubleshooting

If Google opens the account chooser and then returns to the TripWeaver sign-in
dialog, the Google-to-Supabase step is working but the TripWeaver account
exchange failed. Check these values:

- Render has `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`.
- Render has `TRIPWEAVER_API_KEYS`.
- Vercel has `BACKEND_URL` with no trailing slash.
- Vercel has `BACKEND_API_KEY` exactly matching one Render
  `TRIPWEAVER_API_KEYS` value.
- Supabase Authentication URL Configuration has the Vercel site URL and
  `https://YOUR_VERCEL_URL/auth/callback` in Redirect URLs.

Email/password sign-in or registration showing the account backend as
unavailable usually means the Render service is sleeping, `BACKEND_URL` points
to the wrong service, or `BACKEND_API_KEY` does not match Render.

## 5. What works on this free demo path

This path supports:

- polished responsive Next.js UI on Vercel
- backend API on Render
- user registration and login
- optional Google sign-in through Supabase Auth
- per-user conversation history persisted in Supabase Postgres
- server-side proxying so browser users never receive backend API keys
- OpenAI-backed general chat when `OPENAI_API_KEY` has quota
- in-process flight, hotel, itinerary, weather, currency, and location tools
  inside the single Render backend service

## 6. Current limitation

The bootcamp deployment uses `TRIPWEAVER_TOOL_MODE=local`, which keeps the demo
inside one Render Free service by running tool adapters in the backend process.
The full production architecture still uses six separate MCP services for
stronger isolation and clearer ownership boundaries.

Provider-backed tools still depend on their upstream services:

- OpenAI quota for chat
- SerpApi quota for hotel, flight, and place search
- Open-Meteo availability for weather/geocoding
- Frankfurter availability and supported currency list for exchange rates

## 7. Zero-payment safety

Use only:

- Vercel Hobby
- Render Free
- Supabase Free

Do not add a credit card-only paid compute service for this demo. Render Free
can sleep after inactivity, so the first request may be slow. That is acceptable
for a bootcamp demo, but not for a real production launch.
