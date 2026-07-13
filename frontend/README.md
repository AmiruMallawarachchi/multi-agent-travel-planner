# TripWeaver frontend

Minimal Next.js chat frontend for TripWeaver. It keeps the UI intentionally
simple: a shadcn/prompt-kit inspired chat shell, markdown rendering, code
blocks, quick prompts, and a server-side SSE proxy to the FastAPI backend.

The browser never receives OpenAI, Amadeus, or backend API credentials.
`BACKEND_API_KEY` is read only by the Next.js server route at `/api/chat`.

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
```

## Environment

- `BACKEND_URL` - FastAPI backend URL.
- `BACKEND_API_KEY` - one accepted value from backend `TRIPWEAVER_API_KEYS`.
- `PORT` - production server port, defaults to `3000`.
