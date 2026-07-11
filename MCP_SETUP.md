# MCP_SETUP.md

How to get the two MCP servers (`hotel-mcp`, `flight-mcp`) running locally
and deployed, including getting real Amadeus test credentials.

## 1. What these are

Two independent, standalone processes (SRS section 7: "MCP servers run as
their own processes"). Each is a `fastmcp` app exposing three tools over
streamable HTTP at `/mcp`:

| Server | Tools | Port (local) |
|---|---|---|
| `hotel-mcp` | `list_hotels`, `search_hotels`, `book_hotel` | 8001 |
| `flight-mcp` | `list_flights`, `search_flights`, `book_flight` | 8002 |

Search hits Amadeus's real self-service **test** API (live data, sandboxed
environment). Booking is a simulated, realistically-shaped confirmation -
see the docstring at the top of each `amadeus_client.py` for why.

## 2. Get Amadeus test credentials (free, ~2 minutes)

1. Go to https://developers.amadeus.com and create an account.
2. Create a new app (Self-Service). You'll get an **API Key** (=
   `AMADEUS_CLIENT_ID`) and **API Secret** (= `AMADEUS_CLIENT_SECRET`)
   immediately - no approval wait, these are test-environment credentials
   by default.
3. The test environment has a generous free quota and real (if limited)
   inventory - plenty for development and for a viva demo.
4. One app's credentials work for both `hotel-mcp` and `flight-mcp`.

## 3. Run locally

Each server is self-contained:

```bash
cd mcp_servers/hotel_mcp
cp .env.example .env        # fill in AMADEUS_CLIENT_ID / AMADEUS_CLIENT_SECRET
pip install -r requirements.txt
python server.py            # serves http://localhost:8001/mcp
```

```bash
cd mcp_servers/flight_mcp
cp .env.example .env        # same Amadeus app's credentials
pip install -r requirements.txt
python server.py            # serves http://localhost:8002/mcp
```

Or run everything (both MCP servers + backend + frontend) together:

```bash
docker compose up --build
```

## 4. Verify a server is actually working

With the server running:

```bash
python -c "
import asyncio
from fastmcp import Client

async def main():
    async with Client('http://localhost:8001/mcp') as client:
        tools = await client.list_tools()
        print([t.name for t in tools])
        result = await client.call_tool('list_hotels', {'city_code': 'PAR'})
        print(result)

asyncio.run(main())
"
```

You should see `['list_hotels', 'search_hotels', 'book_hotel']` and either a
real list of Paris hotels (credentials configured correctly) or a graceful
`{"ok": false, "error": "..."}` (credentials missing/wrong) - never a stack
trace or a hang, either way. That graceful-failure behaviour is exactly
what SRS section 5 asks for, and it's a good thing to demonstrate live in
the viva by temporarily removing the env var.

## 5. How the backend discovers these servers

`backend/agents/mcp_client.py` reads `HOTEL_MCP_URL` / `FLIGHT_MCP_URL` from
env and loads each server's tools **scoped to that server only**, via
`langchain-mcp-adapters`' `client.session(server_name)` +
`load_mcp_tools(session)`. This is the actual mechanism behind the "Hotel
Agent can never call a flight tool" design decision (SRS section 2) - it's
not a prompt instruction, the tool literally isn't in that agent's tool
list.

## 6. Adding a new MCP server (e.g. the "activities" stretch goal)

1. Copy `mcp_servers/hotel_mcp/` as a template - keep the same shape
   (`server.py` + a `*_client.py` that owns the third-party request/response
   shape + its own `requirements.txt`/`Dockerfile`/`railway.json`).
2. Add its URL to `backend/agents/mcp_client.py`'s `_client` config dict.
3. Add one node + one prompt in `agents/nodes.py` / `agents/prompts.py`,
   and one branch in `agents/graph.py`'s conditional edges.

No existing agent code changes - this is the decoupling SRS section 9-E1
asks you to prove, demonstrated by doing it.

## 7. Deploying (Railway)

Each MCP server is its own Railway service, deployed from its own
subdirectory:

1. Railway dashboard -> New Project -> Deploy from GitHub repo.
2. **Add service** -> set **Root Directory** to `mcp_servers/hotel_mcp`
   (Railway builds using the `Dockerfile` + `railway.json` in that folder).
3. Set the service's Variables: `AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`,
   `AMADEUS_BASE_URL`. Railway injects `PORT` automatically - `server.py`
   already reads it.
4. Repeat for `mcp_servers/flight_mcp` (root directory `mcp_servers/flight_mcp`).
5. Copy each service's public URL (Settings -> Networking -> Generate
   Domain) - you'll need both for the backend's `HOTEL_MCP_URL` /
   `FLIGHT_MCP_URL` (root `README.md` "Deployment" section has the full
   order of operations).
