# MCP server setup

How to run and deploy TripWeaver's hotel and flight MCP servers with
SerpApi-backed Google Hotels and Google Flights search.

## 1. Services and tools

The MCP servers are independent `fastmcp` processes. They keep the existing
tool names and streamable HTTP `/mcp` endpoints so the backend integration does
not change.

| Server | Tools | Local port |
|---|---|---:|
| `hotel-mcp` | `list_hotels`, `search_hotels`, `book_hotel` | 8001 |
| `flight-mcp` | `list_flights`, `search_flights`, `book_flight` | 8002 |

Searches use SerpApi. Bookings remain simulated and always include
`"simulated": true`; TripWeaver does not perform real travel booking or payment.

## 2. Get a SerpApi key

1. Create or sign in to a SerpApi account at https://serpapi.com.
2. Open https://serpapi.com/manage-api-key and copy your private API key.
3. Use the same key for both MCP services.
4. Never paste the key into chat, commit it, or expose it to the frontend.

Create `mcp_servers/hotel_mcp/.env`:

```dotenv
SERPAPI_API_KEY=your-private-serpapi-key
SERPAPI_BASE_URL=https://serpapi.com/search.json
PORT=8001
```

Create `mcp_servers/flight_mcp/.env`:

```dotenv
SERPAPI_API_KEY=your-private-serpapi-key
SERPAPI_BASE_URL=https://serpapi.com/search.json
PORT=8002
```

The `.env` files are ignored by Git. The committed `.env.example` files contain
placeholders only.

## 3. Flight search contract

`search_flights` calls SerpApi with `engine=google_flights` and supports:

Official parameters and response examples: https://serpapi.com/google-flights-api.

- `departure_id`, `arrival_id`: three-letter IATA airport codes
- `outbound_date`: required `YYYY-MM-DD` date
- `return_date`: optional; present means round trip
- `adults`, `children`: maximum nine passengers in total
- `travel_class`: `1` economy, `2` premium economy, `3` business, `4` first
- `currency`: three-letter currency code such as `USD`
- `max_price`: optional maximum ticket price

The client sets `type=1` for a round trip and `type=2` for a one-way trip. It
combines `best_flights` and `other_flights`, then returns at most ten normalized
options. Every option includes its first airline/flight number, endpoint
airports and times, all segments, layovers, total duration, price, currency,
travel class, and `booking_token` when SerpApi supplies one.

## 4. Hotel search contract

`search_hotels` calls SerpApi with `engine=google_hotels` and supports:

Official parameters and response examples: https://serpapi.com/google-hotels-api.

- `destination`: a place or complete hotel query
- `check_in_date`, `check_out_date`: required `YYYY-MM-DD` dates
- `adults`, `children`: maximum ten guests in total
- `currency`: three-letter currency code such as `USD`
- `min_price`, `max_price`: optional nightly-price filters
- `rating`: optional SerpApi filter `7` (3.5+), `8` (4.0+), or `9` (4.5+)

A plain destination such as `Dubai` becomes the query `Hotels in Dubai`; a
complete query such as `Hotels near Dubai Marina` is preserved. The client reads
`properties` and returns at most ten normalized records containing the name,
description, nightly price, currency, rating, review count, hotel class,
amenities, primary image, coordinates, and `property_token`.

## 5. Run locally

Use one terminal per service:

```powershell
cd mcp_servers/hotel_mcp
..\..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\..\.venv\Scripts\python.exe server.py
```

```powershell
cd mcp_servers/flight_mcp
..\..\.venv\Scripts\python.exe -m pip install -r requirements.txt
..\..\.venv\Scripts\python.exe server.py
```

The existing backend configuration remains unchanged:

```dotenv
HOTEL_MCP_URL=http://localhost:8001/mcp
FLIGHT_MCP_URL=http://localhost:8002/mcp
```

You can also start all services with `docker compose up --build` after every
service's local `.env` file is configured.

## 6. Verify without spending credits

The provider tests use `httpx.MockTransport`; they never contact SerpApi:

```powershell
.\.venv\Scripts\python.exe -m pytest -q `
  mcp_servers/flight_mcp/tests/test_serpapi_client.py `
  mcp_servers/hotel_mcp/tests/test_hotel_serpapi_client.py
```

To inspect the live MCP tool schema without making a provider request:

```powershell
cd mcp_servers/flight_mcp
..\..\.venv\Scripts\python.exe -c "import asyncio; from server import mcp; print([tool.name for tool in asyncio.run(mcp.list_tools())])"
```

Only run a live search after confirming the dates and understanding that it may
consume SerpApi account credits. Missing credentials and provider errors return
structured `{ "ok": false, "error": "..." }` tool results rather than crashing
the MCP process.

## 7. Backend discovery

`backend/agents/mcp_client.py` reads `HOTEL_MCP_URL` and `FLIGHT_MCP_URL` and
loads tools within a server-specific MCP session. The hotel agent cannot call
flight tools, and the flight agent cannot call hotel tools, by construction.

## 8. Railway deployment

Deploy each MCP directory as its own Railway service:

1. Set the hotel service root to `mcp_servers/hotel_mcp`.
2. Set `SERPAPI_API_KEY` and
   `SERPAPI_BASE_URL=https://serpapi.com/search.json` in Railway Variables.
3. Let Railway provide `PORT` automatically.
4. Repeat with root `mcp_servers/flight_mcp` and the same SerpApi key.
5. Put each public `/mcp` URL in the backend's `HOTEL_MCP_URL` and
   `FLIGHT_MCP_URL` variables.

Do not place `SERPAPI_API_KEY` in frontend variables or any variable beginning
with `NEXT_PUBLIC_`.

## 9. Adding another MCP server

Keep each provider integration independently deployable:

1. Add a new directory under `mcp_servers/` with its own `server.py`, provider
   client, requirements, Dockerfile, Railway config, and `.env.example`.
2. Register only that server's URL in `backend/agents/mcp_client.py`.
3. Add a matching specialist prompt/node and one graph route.
4. Mock the provider HTTP boundary in tests; never use live credits in CI.

Do not give every agent a shared tool bag. Continue loading tools through the
server-specific MCP session so provider capabilities remain isolated.
