# TripWeaver frontend

Next.js travel cockpit for TripWeaver. The browser talks only to same-origin
Next.js routes; those server routes proxy the FastAPI SSE stream and keep
`BACKEND_API_KEY` out of client JavaScript.

## Local development

```bash
npm install
copy .env.example .env.local
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

The bundled destination images are generated product assets. Hotel, flight,
and booking card content is populated only from structured backend SSE events.
