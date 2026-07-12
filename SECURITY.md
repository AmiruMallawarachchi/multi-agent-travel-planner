# SECURITY.md

What TripWeaver defends against, how, and where the line is deliberately
drawn. Written to be defensible live in the viva (SRS section 11).

## 1. Threat model

TripWeaver is a chat app that (a) costs money per message (OpenAI + Amadeus
usage), (b) executes tool calls based on LLM decisions, and (c) pulls
third-party data (Amadeus) back into the conversation. The relevant threats:

| # | Threat | Where it's handled |
|---|--------|---------------------|
| 1 | Unauthenticated / anonymous abuse running up API cost | API-key auth on every billable endpoint |
| 2 | A single client exhausting the shared OpenAI/Amadeus budget | Per-identity sliding-window rate limiting |
| 3 | Oversized / malformed input | Length caps + control-char stripping, before the graph ever sees it |
| 4 | One traveller reading another's conversation | Server-issued, unguessable (UUID4) session ids; anything else rejected |
| 5 | A malicious/compromised MCP server returning instructions instead of data (indirect prompt injection / "tool poisoning") | Untrusted-data fencing + explicit guardrail prompt (section 3 below) |
| 6 | A model looping on tool calls and burning cost | Hard cap: `MAX_TOOL_ROUNDS` per turn |
| 7 | One dead external service taking the whole app down | Circuit breaker in `agents/mcp_client.py`; every tool call is try/except'd |
| 8 | Secrets leaking into logs, git, or browser JavaScript | `.env` files are gitignored; backend never echoes raw provider error bodies; the Next.js server proxy keeps `BACKEND_API_KEY` server-side; frontend never receives OpenAI or Amadeus keys |
| 9 | Open CORS turning the backend into a public API for anyone's website | `ALLOWED_ORIGINS` explicit allowlist, no `*` in production |

## 2. Auth & rate limiting (`backend/core/security.py`)

- `X-API-Key` header, checked against `TRIPWEAVER_API_KEYS` (comma-separated
  env var). Unset in local dev only - `main.py` logs a loud warning if the
  app starts without it, so it's never silently left open.
- Sliding-window limiter, per API key (or per IP if no key configured):
  `RATE_LIMIT_REQUESTS` per `RATE_LIMIT_WINDOW_SECONDS` (default 20/60s).
  Single-instance in-memory by design - swap for Redis if you scale to
  multiple backend replicas.
- Applied on both `/session` and `/chat/stream`, sharing one bucket per
  identity, so the two endpoints can't be combined to double a budget.

## 3. Prompt-injection / tool-poisoning defence (`agents/nodes.py`, `agents/prompts.py`)

MCP tool results are third-party data, not trusted instructions. Two layers:

1. **Fencing** - every tool result is wrapped in
   `<tool_data source="external, untrusted...">...</tool_data>` before it
   re-enters the conversation (`_fence_untrusted` in `agents/nodes.py`),
   so the boundary between "data" and "instruction" is explicit in the
   transcript, not implicit.
2. **Model-level guardrail** - `agents/prompts.py`'s `GUARDRAILS` block,
   appended to every agent-facing system prompt, explicitly tells the model
   to treat `<tool_data>` content as data to report, never as commands, and
   to never reveal its system prompt, tool schemas, or credentials.

This is prompt-level, not a cryptographic guarantee - see "Known
limitations" below.

## 4. Input validation, defence in depth

Validated at **three** layers independently, deliberately redundant:

1. **Pydantic** (`ChatRequest` in `main.py`) - type/length at the API
   boundary.
2. **`core/security.sanitize_user_message`** - strips control characters,
   re-checks length against `MAX_MESSAGE_LENGTH`.
3. **MCP server inputs** (`mcp_servers/*/amadeus_client.py`) - city/airport
   codes, dates, and IDs are format-validated *before* any network call,
   independent of what called the tool. An MCP server should never trust
   its caller either - a future second agent client, or a compromised
   agent process, is still bound by these checks.

## 5. Resilience (SRS section 5 & 7)

- `agents/mcp_client.py` implements a per-server circuit breaker: after 3
  consecutive failures, that server is skipped (empty tool list returned)
  for 60 seconds instead of every turn paying a timeout.
- Every external call (`tool.ainvoke(...)`) is wrapped in try/except inside
  `_run_specialist` - a failure becomes a `ToolCallStatus.FAILED` record and
  a fenced error message the model reports honestly, never an unhandled
  exception.
- `main.py`'s SSE generator wraps the entire `astream_events` loop in
  try/except, so *any* unexpected failure becomes a graceful `{"type":
  "error", ...}` event instead of a dropped connection or a 500.

## 6. What TripWeaver deliberately does NOT do (and why)

- **No WAF / bot detection** - out of scope for a course project; the
  rate limiter is the practical mitigation at this scale.
- **No cryptographic prompt-injection prevention** - there isn't one, for
  any LLM system that consumes external data. The fencing + guardrail
  approach here reduces risk and gives the model an explicit signal, but a
  sufficiently adversarial tool result is still a research-open problem.
  Mitigating factor: `book_*` results are always deterministic,
  server-generated confirmations, never model-authored - even a fully
  "convinced" model can't fabricate a real booking.
- **No payment/PCI flow** - booking is intentionally simulated (see
  `amadeus_client.py` docstrings); real payment handling is out of scope.
- **In-memory rate limiting** resets on backend restart and doesn't share
  state across replicas - acceptable for a single-instance deployment,
  flagged here so it's not a surprise at scale.
