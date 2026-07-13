# TripWeaver — SYSTEM.md (v1.0)

This is the canonical architecture document for TripWeaver. Every design
decision below is **locked and implemented** unless explicitly marked
`[ROADMAP]`. If you are a coding agent (Codex or otherwise) continuing this
build: read this file fully before writing code, don't re-derive decisions
already made here, and update this file whenever you make a new one.

Companion docs, don't duplicate their content here:
- `README.md` — quickstart, repo layout, deploy steps
- `SECURITY.md` — full threat table and security rationale
- `MCP_SETUP.md` — SerpApi credentials, search contracts, and MCP deployment

---

## 0. Project summary

A traveller chats in natural language. A LangGraph workflow classifies
intent and routes to one of three specialist agents (General QA, Hotel,
Flight). The Hotel and Flight agents reach real external data **only**
through their own MCP server, which wraps SerpApi's Google Hotels and Google
Flights engines. Responses stream token-by-token to a responsive Next.js
travel workspace over Server-Sent Events, with live agent and MCP activity.

Built against the "MCP-Based Multi-Agent Travel Planner" Extension Sprint
SRS. Section references below (e.g. "SRS §5") point at that spec.

---

## 1. Locked decisions (Dx)

| # | Decision | Rationale | Alternatives considered |
|---|---|---|---|
| D1 | LLM provider: **OpenAI** (`gpt-4o-mini` for both router and agents, env-overridable) | User choice; `agents/llm.py` is the single seam if this ever changes | Groq, Anthropic — both would be a one-file swap |
| D2 | **Supervisor/router pattern**, not `create_react_agent` | Manual tool-call loop in `agents/specialist_runner.py` is fully visible/explainable code — defensible line-by-line in a viva, vs. a black-box prebuilt agent | LangGraph prebuilt ReAct agent — faster to write, harder to defend live |
| D3 | Tools scoped **per agent, per MCP server** via `client.session(name)` + `load_mcp_tools`, not a shared tool bag | `MultiServerMCPClient.get_tools()` aggregates all servers with no per-server filter (confirmed against the installed `langchain-mcp-adapters==0.3.0`) — session-scoping is the documented way to get an agent-specific tool list, and it's what makes "Hotel agent can't call a flight tool" true by construction, not by prompt instruction | Bind all tools to every agent + rely on the prompt to self-restrict — rejected, not actually decoupled |
| D4 | Standalone **`fastmcp`** package (v3.x) for both MCP servers, not the bundled `mcp[cli]` SDK | Confirmed working `host`/`port` kwargs on `mcp.run(transport="http", ...)`, which Railway's dynamic `$PORT` needs; actively the more current recommended path as of this build | Bundled `mcp.server.fastmcp.FastMCP` — also viable, more ceremony for host/port binding |
| D5 | Transport string **`"http"`** (streamable HTTP) on both client and server config | Matches the current `fastmcp`/`langchain-mcp-adapters` documented examples; consistent terminology end-to-end avoids a "http" vs "streamable-http" mismatch bug | `"streamable-http"` alias — also valid, chose the shorter current-recommended form |
| D6 | Hotel/flight **search** uses SerpApi's `google_hotels` and `google_flights` engines; **booking is simulated** (`"simulated": true` in every confirmation) | SerpApi provides search data, not TripWeaver's real payment/booking workflow; another search provider remains isolated to `serpapi_client.py` | Fully mock search too — rejected, live provider data is stronger for the viva; real booking — rejected, scope/compliance |
| D7 | **Circuit breaker** per MCP server (3 failures → 60s cooldown) in `agents/mcp_client.py` | SRS §5 resilience requirement — stops every turn paying a timeout against a server that's already known-down | Naive retry-per-call — rejected, doesn't bound latency |
| D8 | **`MemorySaver`** checkpointer, keyed by `session_id` as LangGraph `thread_id` | Gives cross-turn memory (SRS §9 stretch: "refine without repeating themselves") essentially for free | Custom Redis/Postgres state store — deferred, see §13 roadmap for durability across restarts |
| D9 | **Untrusted-data fencing** (`<tool_data>...</tool_data>`) + a shared `GUARDRAILS` prompt block on every agent | Defends against indirect prompt injection carried in a tool result — see `SECURITY.md` §3 for the full rationale and its limits | Trusting tool output implicitly — rejected as unsafe for an MCP-based system by definition |
| D10 | **`MAX_TOOL_ROUNDS = 3`** hard cap per turn in `run_specialist` | Bounds worst-case OpenAI/SerpApi cost per message; a model that keeps calling tools is forced to summarize after 3 rounds instead of looping | Unbounded tool loop — rejected, cost/latency risk |
| D11 | **API-key auth + per-identity rate limiting** on every billable endpoint (`core/security.py`) | The chat endpoint costs real money per call; SRS doesn't mandate this but a "product, not a demo" does | Leave open, rely on obscurity — rejected |
| D12 | Session ids are **server-issued UUID4 hex**, validated on every use, never client-chosen | Prevents one traveller reading another's conversation by guessing/enumerating a `thread_id` | Client-generated session ids — rejected, no unguessability guarantee |
| D13 | Docker-buildable **Railway-compatible services** for backend, frontend, and both MCP servers | One deployment model keeps the four-service topology reproducible locally and in production | Hugging Face Spaces Gradio frontend - replaced when the UI moved to Next.js |
| D14 | Responsive **shadcn/ui TripWeaver workspace** with conversation history, streaming chat, live tool state, trip context, quick actions, settings, and mobile sheets | Matches the approved TripWeaver interface while keeping provider-backed capabilities honest: flight/hotel are active, future MCPs are visibly unavailable | Generic minimal chat shell - replaced because it did not represent the product workflow |

---

## 2. Tech stack — exact versions validated in this build

These aren't guesses — every package below was actually `pip install`'d
into a clean venv, and every module was import-checked (see §12 for what
was run). Pin these (or newer within the same major line) for a
reproducible build.

| Package | Version installed | Used by |
|---|---|---|
| `fastapi` | 0.139.0 | backend |
| `uvicorn` | 0.51.0 | backend |
| `pydantic` | 2.13.4 | backend |
| `langgraph` | 1.2.9 | backend |
| `langgraph-checkpoint` | 4.1.1 | backend |
| `langchain-core` | 1.4.9 | backend |
| `langchain-openai` | 1.3.4 | backend |
| `langchain-mcp-adapters` | 0.3.0 | backend |
| `httpx` | 0.28.1 | backend, both MCP servers |
| `mcp` | 1.28.1 | pulled in by `langchain-mcp-adapters` |
| `fastmcp` | 3.4.4 | both MCP servers |
| `pytest` / `pytest-asyncio` | 9.1.1 / 1.4.0 | backend tests |
| `next` / `react` | 15.5.20 / 19.2.7 | frontend |
| `highlight.js` / `react-markdown` | 11.11.1 / 9.1.0 | frontend markdown/code blocks |
| `vitest` | 4.1.10 | frontend tests |

Note: `langchain-core` crossed to a `1.x` major version in this build —
if you're extending this later and something in `langchain_core.messages`
behaves differently than older `0.3.x`-era examples online suggest, trust
what's actually installed (`pip show langchain-core`) over training data.

---

## 3. Repository structure

```
backend/
  main.py                    ASGI entrypoint (`uvicorn main:app`)
  config.py                  Typed settings loaded from environment
  api/
    app.py                    FastAPI app factory + CORS setup
    routes.py                 /health, /session, /chat/stream handlers
    schemas.py                HTTP and SSE Pydantic models
    sse.py                    LangGraph event -> SSE event normalization
  conftest.py                 pytest sys.path bootstrap
  pytest.ini                   asyncio_mode = auto
  requirements.txt / requirements-dev.txt
  Dockerfile / railway.json / .env.example
  agents/
    __init__.py
    entity.py                  TripWeaverState + Intent/ActivityState/ToolCallStatus enums (§4)
    llm.py                     get_router_llm() / get_agent_llm() - OpenAI factory (D1)
    prompts.py                  All system prompts + shared GUARDRAILS block (D9)
    mcp_client.py                get_tools_for(server) - scoped loading + circuit breaker (D3, D7)
    history.py                   Bounded conversation-tail helper (D10)
    tool_results.py              Untrusted-data fencing + simulated booking extraction (D6, D9)
    specialist_runner.py         Shared hotel/flight tool-call loop (D2, D10)
    nodes.py                     Thin LangGraph node adapters: classify_intent, general_qa_node,
                                  hotel_node, flight_node, clarify_node, route_from_intent
    graph.py                     StateGraph wiring + MemorySaver (D8)
  core/
    __init__.py
    security.py                  require_api_key, check_rate_limit, sanitize_user_message,
                                  new_session_id/validate_session_id (D11, D12)
  tests/
    __init__.py
    test_agent_helpers.py         Conversation trimming + tool-result extraction tests
    test_api.py                   Endpoint security + SSE bridge tests
    test_graph.py                 Routing + graceful-degradation + tool-loop-cap tests
    test_security.py               Auth/rate-limit/validation tests
    test_sse.py                    SSE event normalization tests

mcp_servers/
  hotel_mcp/
    serpapi_client.py            Owns SerpApi hotel transport + normalized results (D6)
    server.py                     FastMCP app: list_hotels, search_hotels, book_hotel
    requirements.txt / Dockerfile / railway.json / .env.example
  flight_mcp/
    serpapi_client.py            Owns SerpApi flight transport + normalized results (D6)
    server.py                     FastMCP app: list_flights, search_flights, book_flight
    requirements.txt / Dockerfile / railway.json / .env.example

frontend/
  app/                           Next.js routes + same-origin backend/health proxy
  components/ui/                 shadcn/ui source components
  components/tripweaver/         Workspace, chat, history, settings, status panels
  features/tripweaver/           Conversation, trip-context, stream-state domain logic
  lib/                           SSE parser + shared helpers
  package.json / Dockerfile / README.md / .env.example

docker-compose.yml              All 4 services wired together for local dev
README.md / SECURITY.md / MCP_SETUP.md / SYSTEM.md (this file)
```

---

## 4. Shared state schema (`backend/agents/entity.py`)

`TripWeaverState` (a `TypedDict`) is the **only** channel of communication
between nodes (SRS §7). Full field list:

| Field | Type | Set by |
|---|---|---|
| `messages` | `Annotated[list[AnyMessage], add_messages]` | every node (LangGraph reducer appends) |
| `intent` | `Intent \| None` | `classify_intent` |
| `active_agent` | `str \| None` | whichever specialist ran |
| `activity` | `ActivityState \| None` | every node (drives the frontend live state) |
| `missing_fields` | `list[str]` | reserved for explicit missing-field tracking — currently agents ask via natural language in `messages` rather than populating this list structurally; see §13 roadmap |
| `clarification_question` | `str \| None` | `clarify_node` |
| `hotel_results` / `flight_results` | `list[dict]` | reserved for structured result storage — currently results live in `messages` as tool output; see §13 |
| `booking_confirmation` | `dict \| None` | `run_specialist` after a successful simulated `book_hotel` / `book_flight` tool call; includes `type`, `server`, `tool_name`, provider-style confirmation fields, and `"simulated": true` |
| `tool_calls` | `list[ToolCallRecord]` | `run_specialist` (every call this turn, success or failure) |
| `session_id` | `str` | `api/routes.py`, becomes the LangGraph `thread_id` |

`Intent`, `ActivityState`, `ToolCallStatus` are `str` Enums matching SRS §2
and §6's tables exactly — the frontend's `ACTIVITY_LABELS` dict in
`frontend/features/tripweaver/stream-state.ts` maps `ActivityState` and tool
events into the chat activity rows and right-side MCP status panel.

---

## 5. Request lifecycle (one turn, step by step)

1. Browser POSTs `{message, session_id}` to the same-origin Next.js
   `POST /api/chat` route. The server-only proxy adds `X-API-Key` and
   forwards the request to FastAPI `POST /chat/stream` without buffering the
   SSE body.
2. `api/routes.py:chat_stream` — `require_api_key` → `check_rate_limit` →
   `sanitize_user_message` → `validate_session_id` (mint one via
   `new_session_id()` if none supplied) → builds `inputs` for the graph.
3. `graph.astream_events(inputs, config={"configurable": {"thread_id": session_id}}, version="v2")`
   drives the whole turn; `api/routes.py` always starts the SSE stream with
   `{"type": "session", "session_id": ...}` and translates graph events:
   - `on_chain_start` for a known node name → `{"type": "status", "state": ...}`
   - `on_tool_start` / `on_tool_end` / `on_tool_error` → `{"type": "tool", "status": "INVOKED|SUCCEEDED|FAILED", ...}`
   - `on_chat_model_stream` → `{"type": "token", "content": ...}` with provider-specific chunk shapes normalized to plain text
4. Inside the graph: `classify_intent` → conditional edge
   (`route_from_intent`) → one of `general_qa_node` / `hotel_node` /
   `flight_node` / `clarify_node` → `END`.
5. Inside `hotel_node`/`flight_node` (`run_specialist`): load scoped tools
   → bind → up to `MAX_TOOL_ROUNDS` rounds of (LLM decides → tool call,
   fenced + recorded → LLM sees result) → final answer.
6. Any exception anywhere in step 3–5 is caught by `api/routes.py`'s top-level
   try/except and turned into `{"type": "error", "message": "..."}` followed
   by `{"type": "done"}` — the generator still completes cleanly, the app
   never crashes.
7. Frontend renders tokens into the last chat message live, and the
   ticker (`theme.ticker_html`) reflects routing status plus every tool
   `INVOKED` / `SUCCEEDED` / `FAILED` event.

---

## 6. LangGraph topology

```
START -> classify_intent -> [conditional] -> general_qa -> END
                                           -> hotel      -> END
                                           -> flight     -> END
                                           -> clarify    -> END
                                           -> END (intent == "end")
```

Single-hop by design (SRS §9 core scope doesn't require multi-agent
itineraries combining hotel+flight in one turn — that's the "richer
orchestration" **[ROADMAP]** stretch item, see §13).

---

## 7. MCP layer

| Server | Tools | Backing | Booking |
|---|---|---|---|
| `hotel-mcp` | `list_hotels(destination)`, `search_hotels(destination, check_in_date, check_out_date, adults, children, currency, min_price, max_price, rating)`, `book_hotel(offer_id, guest_name)` | SerpApi `engine=google_hotels`; normalized from `properties` | Simulated (D6) |
| `flight-mcp` | `list_flights(departure_id, arrival_id)`, `search_flights(departure_id, arrival_id, outbound_date, return_date, adults, children, travel_class, currency, max_price)`, `book_flight(offer_id, traveller_name)` | SerpApi `engine=google_flights`; normalized from `best_flights` + `other_flights` | Simulated (D6) |

Every tool returns `{"ok": bool, ...}` — never raises to the MCP transport
layer — so the calling agent always gets structured data to reason about,
even on failure (verified live in §12).

---

## 8. Security & guardrails

Full detail in `SECURITY.md`. Summary of what's implemented:

- API-key auth (`X-API-Key`) + sliding-window rate limiting on `/session`
  and `/chat/stream`
- Three-layer input validation (Pydantic → `sanitize_user_message` →
  per-tool validation in each `serpapi_client.py`)
- Unguessable, server-issued session ids
- CORS locked to an explicit `ALLOWED_ORIGINS` allowlist
- Untrusted-data fencing + guardrail prompt against tool-result prompt
  injection
- Circuit breaker + full try/except coverage for external-service failures
- `MAX_TOOL_ROUNDS` cap against runaway tool-calling cost

---

## 9. Environment variables (all services)

| Var | Service | Purpose |
|---|---|---|
| `OPENAI_API_KEY` | backend | LLM calls |
| `ROUTER_MODEL`, `AGENT_MODEL` | backend | model overrides (default `gpt-4o-mini`) |
| `HOTEL_MCP_URL`, `FLIGHT_MCP_URL` | backend | where to reach each MCP server |
| `TRIPWEAVER_API_KEYS` | backend | comma-separated accepted `X-API-Key` values |
| `ALLOWED_ORIGINS` | backend | comma-separated CORS allowlist |
| `RATE_LIMIT_REQUESTS`, `RATE_LIMIT_WINDOW_SECONDS` | backend | rate limiter tuning |
| `MAX_MESSAGE_LENGTH` | backend | input length cap |
| `SERPAPI_API_KEY`, `SERPAPI_BASE_URL` | both MCP servers | SerpApi query authentication and endpoint |
| `PORT` | all four services | injected by the platform; each service reads it itself |
| `BACKEND_URL` | frontend server | backend URL used by the same-origin proxy |
| `BACKEND_API_KEY` | frontend server | server-only value matching one backend `TRIPWEAVER_API_KEYS` entry |

---

## 10. Deployment topology & order

See `README.md` "Deploying" for the exact order (MCP servers → backend →
frontend → backend CORS redeploy). Each of the 4 services is independently
buildable from its own Dockerfile.

---

## 11. Testing strategy

`backend/tests/` — all offline:
- `test_agent_helpers.py` — conversation-history windowing, tool-result JSON
  handling, untrusted-data fencing, and simulated booking-confirmation extraction.
- `test_api.py` — endpoint auth/rate-limit/session behavior and the streaming
  bridge using a fake graph.
- `test_graph.py` — routing correctness (every `Intent` value, invalid-
  label fallback to `CLARIFY`), graceful degradation when a tool server is
  down, a failing tool call being recorded without crashing, and the
  `MAX_TOOL_ROUNDS` cap actually stopping a looping model.
- `test_security.py` — sanitization edge cases, session-id validation
  (including a SQL-injection-shaped string, deliberately), rate-limit
  trip/independent-buckets, and all four API-key auth branches.
- `test_sse.py` — LangGraph event to SSE event normalization and safe error
  messages.

Frontend Vitest suites cover the SSE parser, API proxy and backend-health
bridge, conversation persistence/search/export, trip-context extraction,
SSE-to-MCP state mapping, and end-user workspace interactions.

`mcp_servers/*/tests/` — 32 offline SerpApi contract tests covering request
mapping, normalized results, input validation, result caps, missing arrays,
provider errors, and API-key redaction without consuming provider credits.

`tests/test_docker_secret_hygiene.py` — verifies every service-level Docker
build context excludes local `.env` files while retaining `.env.example`.

LLM and MCP tool calls are mocked (`unittest.mock`) — no `OPENAI_API_KEY`
or SerpApi credentials are needed to run the suites or in CI.

---

## 12. What was actually verified in this build (not just written)

- `pip install` of backend and MCP requirements plus `npm install` for the
  Next.js frontend — no dependency conflicts, versions in §2.
- `py_compile` of every `.py` file in the repo.
- The backend pytest suite passes against the real installed `langgraph`/
  `langchain-*` versions above (not just mocked at the import level —
  the actual graph, node, and security code executes).
- SerpApi contract tests — 32/32 passing with `httpx.MockTransport`; no live
  request or provider credit is used.
- Docker secret-hygiene test — confirmed all four service build contexts
  exclude local `.env` files from container images.
- Both MCP servers imported and their tools listed via `mcp.list_tools()`
  — confirmed `['list_hotels', 'search_hotels', 'book_hotel']` and
  `['list_flights', 'search_flights', 'book_flight']`.
- `book_hotel_offer` / `book_flight_offer` called in offline tests — confirmed
  simulated booking works with zero provider dependencies.
- `search_hotels` called with malformed dates/query values — confirmed
  input validation rejects it before any network call.
- Both clients exercised with an explicitly empty SerpApi key — confirmed a
  controlled configuration error before any network request.
- Full FastAPI app booted with `uvicorn` and hit with `curl`:
  `/health` (200, no auth), `/session` (401 without key, 200 with),
  `/chat/stream` (422 on empty message, 401 without key), a CORS
  preflight from a disallowed origin (correctly no
  `Access-Control-Allow-Origin` echoed back), and the rate limiter
  (confirmed 429s after the configured threshold, per-identity buckets
  independent). One real bug was caught this way — `/session` was
  missing its `check_rate_limit` call — and fixed; see D11.
- Frontend `vitest`, ESLint, TypeScript, `npm audit`, and optimized `next build`
  pass for the shadcn/ui workspace and same-origin API proxy.

Live SerpApi verification completed on 2026-07-13 through the MCP transport:
- A round-trip Google Flights search from CMB to DXB for 2026-08-01 through
  2026-08-07 returned nine normalized flight options.
- A Google Hotels search for Dubai for the same dates returned ten normalized
  properties.
- Credentials remained in ignored local `.env` files; verification output did
  not print API keys, booking tokens, or property tokens.

What was **not** verified in this change: a real OpenAI completion. Real travel
booking and payment are intentionally out of scope; booking confirmations are
simulated and explicitly labelled as such.

---

## 13. Implementation status vs. SRS

**Core (SRS §9), all implemented:**
E1 (MCP servers + registration), E2 (intent routing + scoped tools +
missing-input/edge-case handling), E3 (graceful external-failure
handling), streaming, activity visualisation, user-friendly errors,
travel-themed responsive UI, both deployments, env-var hygiene, docs.

**Stretch (SRS §9), status:**

| Item | Status |
|---|---|
| Memory / context across turns | Done (D8, `MemorySaver`) |
| Additional MCP services (activities/transport/weather) | `[ROADMAP]` — `MCP_SETUP.md` §9 documents the exact steps |
| Richer orchestration (combined hotel+flight itinerary in one turn) | `[ROADMAP]` — would add a `plan` node that fans out to both specialists and merges before responding |
| Observability (structured tracing) | Partial — structured request-id logging exists in `api/routes.py`; no distributed tracing (e.g. LangSmith) wired up |
| Provider-backed flight/hotel result cards | `[ROADMAP]` — tool progress and itinerary dialogs are implemented, but provider results still arrive as markdown because `hotel_results`/`flight_results` are not populated yet |
| Containerisation | Done (Dockerfile per service + docker-compose) |
| CI | `[ROADMAP]` — no GitHub Actions workflow yet; `pytest` + `py_compile` from §12 is exactly what a CI job should run |

## 14. Extension points

- **New MCP server**: `MCP_SETUP.md` §9.
- **New agent**: add a node + prompt pair, one conditional-edge branch in
  `graph.py`, extend `Intent` in `entity.py`.
- **Swap LLM provider**: edit `agents/llm.py` only.
- **Real payment/booking**: replace `serpapi_client.py`'s `book_*_offer`
  functions only — the tool interface (`server.py`) and every agent are
  already written against the simulated confirmation shape.
- **Structured result cards**: populate `hotel_results`/`flight_results` in
  `run_specialist`'s return dict (fields already exist, unused today), then
  add typed card renderers under `frontend/components/tripweaver/` alongside
  the existing markdown response.
- **Horizontal scaling**: swap `core/security.py`'s in-memory rate-limit
  dict and `MemorySaver` for Redis-backed equivalents — both are isolated
  behind small interfaces already.

## 15. Known limitations

Restated from `SECURITY.md` §6: no WAF, no cryptographic prompt-injection
guarantee (mitigated, not solved — bookings are always server-generated so
a "convinced" model still can't fabricate a real one), no payment/PCI flow,
in-memory rate limiting doesn't survive a restart or scale across replicas.
