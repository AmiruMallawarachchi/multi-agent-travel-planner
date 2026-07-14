# TripWeaver frontend

Responsive Next.js travel workspace built with shadcn/ui, Radix primitives,
Tailwind CSS, and Lucide icons. The interface has three coordinated areas:
conversation history, the streaming chat, and live tools/trip context.

Implemented interactions include:

- guest browser history and account-backed history for signed-in travellers
- conversation search, new chat, and clear history
- export, copy, and Web Share support
- text-file attachments and browser speech recognition when available
- live agent/MCP status driven by backend SSE events
- trip-context extraction for destination, dates, travellers, budget, and preferences
- working flight, hotel, itinerary, weather, currency, and location quick actions
- typed result views for all six travel capabilities
- settings for persistence, tool activity, and light/dark appearance
- login, registration, sign out, and help centre dialogs
- responsive history and status sheets on smaller screens

The browser never receives OpenAI, SerpApi, backend API credentials, or account
session tokens. `BACKEND_API_KEY` is read only by Next.js server routes, and
account sessions are stored as httpOnly cookies. `/api/health` performs a real
backend health check so the UI does not show a fabricated online state.

## Local dev

```bash
npm install
cp .env.example .env
npm run dev
```

Open http://localhost:3000.

## Checks

```bash
npm test
npm run lint
npm run typecheck
npm run build
npm audit
```

Vitest covers the API proxy, health reporting, conversation helpers, trip
context extraction, SSE-to-tool-state handling, structured result rendering,
and user-facing workspace interactions.

## Environment

- `BACKEND_URL` - FastAPI backend URL.
- `BACKEND_API_KEY` - one accepted value from backend `TRIPWEAVER_API_KEYS`.
- `PORT` - production server port, defaults to `3000`.
