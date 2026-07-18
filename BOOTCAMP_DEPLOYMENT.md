# TripWeaver bootcamp deployment

This guide deploys the assessed MCP architecture without putting provider code
inside the backend process:

```text
Vercel Hobby (Next.js)
  -> Render Free (FastAPI backend)
      -> Render Free (Hotel MCP)    -> SerpApi Google Hotels
      -> Render Free (Flight MCP)   -> SerpApi Google Flights
      -> Render Free (Itinerary MCP)
      -> Render Free (Weather MCP)  -> Open-Meteo
      -> Render Free (Currency MCP) -> Frankfurter
      -> Render Free (Location MCP) -> SerpApi / Nominatim
  -> Supabase Free (Postgres and Google identity verification)
```

The backend uses LangChain's `MultiServerMCPClient` with streamable HTTP. Local
tool adapters remain available only as a development fallback.

Never paste secrets into chat, commit them, or put them in tracked `.env`
files. Store secrets only in the Render, Vercel, and Supabase dashboards.

## 1. Deploy the Render Blueprint

The repository's `render.yaml` defines the backend and all six MCP services.

1. Merge the release branch into `main` after CI passes.
2. In Render, choose **New -> Blueprint**.
3. Connect `AmiruMallawarachchi/multi-agent-travel-planner`.
4. Select `render.yaml` and apply the Blueprint.
5. Confirm that Render creates these seven web services:

```text
tripweaver-backend
tripweaver-hotel-search-mcp
tripweaver-flight-search-mcp
tripweaver-itinerary-mcp
tripweaver-weather-mcp
tripweaver-currency-mcp
tripweaver-place-search-mcp
```

The Blueprint automatically injects each MCP service's Render hostname into
the backend and sets:

```text
TRIPWEAVER_TOOL_MODE=mcp
```

Do not change that production value to `local`.

The injected `*_MCP_HOST` values are authoritative in a Blueprint deployment.
They intentionally take precedence over any older `*_MCP_URL` values left on
an existing backend service. Complete `*_MCP_URL` values are reserved for the
manual setup described below.

### Render secrets

Enter `SERPAPI_API_KEY` on `tripweaver-hotel-search-mcp`. The Blueprint shares
that secret with the flight and location MCP services. Render prompts for
`sync: false` values during initial Blueprint creation. When synchronizing an
existing Blueprint, Render ignores newly added `sync: false` entries, so add
any missing secret manually in the affected service's **Environment** page.

The provider-backed MCP services intentionally use dedicated `*-search-mcp`
names. Earlier manually created services with the shorter names can point to
retired images while still occupying their public Render URLs. After the three
new services pass `/health` and the backend reports them available, the retired
`tripweaver-hotel-mcp`, `tripweaver-flight-mcp`, and
`tripweaver-location-mcp` services can be deleted from the Render dashboard.

Enter these secrets on `tripweaver-backend`:

```text
OPENAI_API_KEY=your OpenAI key
TRIPWEAVER_API_KEYS=one long random API key
DATABASE_URL=your Supabase pooled Postgres URL
ALLOWED_ORIGINS=https://multi-agent-travel-planner-jet.vercel.app,http://localhost:3000
SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
SUPABASE_PUBLISHABLE_KEY=your Supabase publishable key
```

The backend does not need `SERPAPI_API_KEY` in MCP mode. Provider credentials
belong only to the MCP services that use them.

## 2. Configure Supabase

Use the pooled Postgres connection string from **Project Settings -> Database**
as Render's `DATABASE_URL`. Percent-encode special characters in the password,
or use the encoded connection string supplied by Supabase.

Copy the browser-safe values from **Project Settings -> API**:

```text
NEXT_PUBLIC_SUPABASE_URL
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY
```

Only the publishable key may be exposed to the frontend. Never expose a secret
or service-role key.

### Google sign-in

1. Create a Web application OAuth client in Google Auth Platform.
2. Add the Vercel URL as an authorized JavaScript origin.
3. Add `https://YOUR_PROJECT_REF.supabase.co/auth/v1/callback` as an authorized
   redirect URI.
4. Enable Google in **Supabase Authentication -> Providers** and enter the
   Google client ID and secret there.
5. In **Authentication -> URL Configuration**, set the Site URL to the Vercel
   URL and add `https://YOUR_VERCEL_URL/auth/callback` to Redirect URLs.

TripWeaver verifies the Supabase identity on the backend before creating its
own account-scoped session.

## 3. Configure Vercel

Use these project settings:

```text
Framework: Next.js
Root Directory: frontend
Install Command: npm install
Build Command: npm run build
Output Directory: .next
```

Set these environment variables for Production and Preview:

```text
BACKEND_URL=https://tripweaver-backend-9fz2.onrender.com
BACKEND_API_KEY=the exact value used by Render TRIPWEAVER_API_KEYS
NEXT_PUBLIC_SUPABASE_URL=https://YOUR_PROJECT_REF.supabase.co
NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY=your Supabase publishable key
```

Redeploy after changing environment variables.

## 4. Prove the deployed MCP runtime

Start with the cheap liveness endpoint:

```text
https://tripweaver-backend-9fz2.onrender.com/health/live
```

Then open the readiness endpoint. It contacts all six MCP services and can take
up to about 70 seconds on the first request because Render Free services sleep:

```text
https://tripweaver-backend-9fz2.onrender.com/health
```

The important evidence is:

```json
{
  "status": "ok",
  "mcp_servers": {
    "hotel-mcp": "available",
    "flight-mcp": "available",
    "itinerary-mcp": "available",
    "weather-mcp": "available",
    "currency-mcp": "available",
    "location-mcp": "available"
  },
  "account_storage": {
    "backend": "postgres",
    "status": "available"
  },
  "tool_runtime": {
    "mode": "mcp",
    "transport": "streamable_http",
    "configured_servers": 6
  }
}
```

Also open `/health` on each MCP service. The `/mcp` route is a protocol
endpoint and is not expected to render a human-friendly browser page.

If only some services remain `unavailable`:

1. Synchronize the Blueprint from the latest `main` commit.
2. Confirm the affected Render service is **Live** and its own `/health`
   endpoint returns HTTP 200.
3. Confirm the backend contains the matching Blueprint-generated
   `*_MCP_HOST` variable.
4. Remove obsolete localhost or retired-service `*_MCP_URL` values to keep the
   dashboard unambiguous, then redeploy the backend.
5. On the free plan, open the affected service's `/health` once and allow its
   cold start to finish before checking backend readiness again.

After migrating from the retired provider service names, verify these three
endpoints directly before checking the backend:

```text
https://tripweaver-hotel-search-mcp.onrender.com/health
https://tripweaver-flight-search-mcp.onrender.com/health
https://tripweaver-place-search-mcp.onrender.com/health
```

Render can add a suffix when a preferred public hostname is already taken. If
that happens, use the URL displayed on the service page; the Blueprint still
injects the correct generated hostname into the backend.

Finally verify the frontend proxy:

```text
https://multi-agent-travel-planner-jet.vercel.app/api/health
```

## 5. Manual Render setup

Use this only if Render Blueprint creation is unavailable. Create six Docker
web services using each service directory as its Docker context and its
existing `Dockerfile`. Use `/health` as every MCP health path. Then create the
backend with:

```text
Dockerfile: deploy/render/backend.Dockerfile
Health check path: /health/live
TRIPWEAVER_TOOL_MODE=mcp
HOTEL_MCP_URL=https://YOUR_HOTEL_SERVICE/mcp
FLIGHT_MCP_URL=https://YOUR_FLIGHT_SERVICE/mcp
ITINERARY_MCP_URL=https://YOUR_ITINERARY_SERVICE/mcp
WEATHER_MCP_URL=https://YOUR_WEATHER_SERVICE/mcp
CURRENCY_MCP_URL=https://YOUR_CURRENCY_SERVICE/mcp
LOCATION_MCP_URL=https://YOUR_LOCATION_SERVICE/mcp
```

## 6. Free-tier limits

This is a bootcamp demonstration deployment, not a production SLA:

- Render Free services can sleep, so the first request can be slow.
- Seven Render services consume the workspace's shared free instance hours.
- Provider quotas still apply to OpenAI and SerpApi.
- `/health/live` is the Render health check so routine probes do not wake all
  six MCP services; `/health` is the explicit readiness and architecture proof.
- A real public product should add paid always-on compute, tracing, alerting,
  backups, dependency scanning, and secret rotation.

## 7. Booking boundary

Flight and hotel booking confirmations are intentionally simulated. SerpApi is
a search provider and does not create reservations. Real booking would require
supplier contracts, payment handling, cancellation rules, and compliance work.
The current tools demonstrate MCP tool selection, validation, confirmation
state, and failure handling without pretending to complete a real transaction.
