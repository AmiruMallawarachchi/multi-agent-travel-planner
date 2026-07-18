# Bootcamp assessment evidence

This matrix maps the supplied project specification to concrete TripWeaver
evidence. It separates implementation from deployment proof so the submission
does not claim that a service is live before Render has deployed it.

## Core criteria

| Criterion | Status | Evidence and verification |
| --- | --- | --- |
| General travel agent routes requests to specialists | Met | `backend/agents/graph.py`, `backend/agents/nodes.py`, and `backend/tests/test_graph.py` cover intent routing, specialist execution, and fallback behaviour. |
| Hotel agent uses a Hotel MCP server | Implemented; live proof required after Blueprint sync | `mcp_servers/hotel_mcp/server.py` exposes the MCP tool. `backend/agents/mcp_client.py` connects through streamable HTTP. Backend `/health` must report `mode=mcp` and `hotel-mcp=available`. |
| Flight agent uses a Flight MCP server | Implemented; live proof required after Blueprint sync | `mcp_servers/flight_mcp/server.py` exposes the MCP tool. The same runtime proof must report `flight-mcp=available`. |
| Tools return normalized, structured data | Met | Provider clients normalize flight, hotel, weather, currency, location, and itinerary payloads. Provider contract tests live under each `mcp_servers/*/tests` directory. |
| Invalid input and provider failures are handled safely | Met | MCP clients validate airport codes, dates, currency values, and provider responses. Backend and frontend tests cover structured errors and interrupted SSE streams. |
| Multi-agent state is preserved through a workflow | Met | LangGraph state, trip context, structured results, and tool events are defined and exercised in `backend/agents` and `backend/tests/test_graph.py`. |

## Frontend criteria

| Criterion | Status | Evidence and verification |
| --- | --- | --- |
| Interactive chat interface | Met with approved framework deviation | TripWeaver uses a responsive Next.js/Shadcn interface rather than Gradio. `frontend/components/tripweaver/chat-workspace.tsx` is the main workspace. |
| Streaming responses and visible tool activity | Met | `backend/api/sse.py`, `frontend/lib/sse.ts`, and their tests cover typed SSE events, tool progress, completion, and errors. |
| Structured travel results | Met | The frontend renders flight, hotel, place, itinerary, weather, and currency results separately from model prose. |
| Responsive desktop/mobile experience | Met | The workspace has responsive navigation, account-scoped history, theme controls, and mobile panels. Frontend component and layout tests protect the core behaviour. |
| Authentication and private history | Met | Email/password and Supabase Google identity exchange use backend-issued HTTP-only sessions. Account tests verify user isolation. Supabase is identity verification and managed Postgres, not a trusted browser-side authorization shortcut. |

## Deployment and engineering criteria

| Criterion | Status | Evidence and verification |
| --- | --- | --- |
| Standalone MCP services in deployed runtime | Implemented; live proof required after Blueprint sync | `render.yaml` declares six independent MCP web services and one backend. The backend is configured with `TRIPWEAVER_TOOL_MODE=mcp`. `/health` exposes runtime mode, transport, and per-service readiness. |
| Containerized services | Met | The backend and every MCP service have dedicated Docker build definitions. GitHub CI builds all seven images. |
| Continuous integration on push and pull request | Met | `.github/workflows/ci.yml` runs Python tests and compilation, frontend tests/lint/typecheck/build, and a seven-image Docker build matrix. |
| Secrets excluded from source control | Met | Deploy manifests use dashboard-provided secrets; examples contain placeholders. Provider keys stay with the MCP services that consume them. |
| Public deployment documentation | Met | `BOOTCAMP_DEPLOYMENT.md`, `MCP_SETUP.md`, `SYSTEM.md`, and `README.md` describe the runtime, environment contract, health proof, and limitations. |

## Stretch criteria and honest boundaries

| Stretch criterion | Status | Boundary |
| --- | --- | --- |
| Additional MCP services | Met | Itinerary, weather, currency, and location are implemented alongside hotel and flight. |
| Rich multi-agent orchestration | Partial | Itinerary planning can combine location discovery and itinerary generation. A single turn still selects one primary specialist; there is no concurrent flight + hotel + weather fan-out workflow. |
| Durable memory | Partial to met for product history | Account-scoped conversations and plans persist in Postgres. Agent working memory remains request/session scoped rather than a semantic long-term memory system. |
| Observability | Partial | Structured logs, liveness/readiness, MCP status, and frontend tool events exist. OpenTelemetry/LangSmith traces, metrics, dashboards, and alerting remain future production work. |
| Real hotel/flight booking | Intentionally partial | Search is live, but confirmation is simulated because SerpApi does not reserve inventory. No claim of a supplier reservation is made. |

## Booking viva explanation

Use this exact, honest explanation:

> The booking tools demonstrate the complete MCP booking lifecycle, validation,
> tool selection, confirmation state, and error handling. They intentionally
> simulate the irreversible transaction because the selected search provider
> does not provide a reservation API, and real booking would require supplier
> agreements, payment handling, and cancellation compliance.

## Submission gate

Do not mark the deployed MCP criterion complete until all of these are true:

1. GitHub CI passes on the release commit.
2. Render shows seven live services from `render.yaml`.
3. Backend `/health/live` returns `status=ok`.
4. Backend `/health` reports all six MCP servers as `available`.
5. Backend `/health` reports:

```json
{
  "tool_runtime": {
    "mode": "mcp",
    "transport": "streamable_http",
    "configured_servers": 6
  }
}
```

6. The Vercel UI completes one live flight search, one hotel search, one
   itinerary, one weather lookup, one currency conversion, and one location
   search while displaying the corresponding MCP activity.
7. Two different accounts cannot see or mutate each other's conversations or
   plans.

## Final verdict

After the Render Blueprint is synchronized and the health evidence above is
captured, TripWeaver meets the core multi-agent and MCP requirements except for
any assessor who interprets the brief as requiring literal Gradio or a real
paid supplier booking transaction. Those two deviations must be stated rather
than hidden. Rich concurrent orchestration and full distributed tracing remain
stretch improvements, not missing core functionality.
