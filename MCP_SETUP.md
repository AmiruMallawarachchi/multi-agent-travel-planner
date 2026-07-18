# MCP server setup

TripWeaver runs each travel capability as an independent FastMCP HTTP service.
The backend discovers tools through `/mcp` and probes service health through
`/health`.

## Service map

| Service | Port | Tools | External provider |
| --- | ---: | --- | --- |
| `hotel-mcp` | 8001 | `list_hotels`, `search_hotels`, `book_hotel` | SerpApi Google Hotels |
| `flight-mcp` | 8002 | `list_flights`, `search_flights`, `book_flight` | SerpApi Google Flights |
| `itinerary-mcp` | 8003 | `create_itinerary` | None |
| `weather-mcp` | 8004 | `get_current_weather`, `get_weather_forecast` | Open-Meteo |
| `currency-mcp` | 8005 | `convert_currency`, `get_exchange_rate`, `list_supported_currencies` | Frankfurter |
| `location-mcp` | 8006 | `resolve_location`, `search_places` | Open-Meteo and SerpApi Google Maps |

Every tool returns a dictionary with an `ok` boolean. Invalid input and provider
failures are represented as controlled tool results instead of transport-level
exceptions. The backend maps `ok: false` to a failed tool event.

## SerpApi credentials

Hotel search, flight search, and local place search share one SerpApi key.

1. Create an account at https://serpapi.com/.
2. Obtain a private API key from the account dashboard.
3. Copy the three examples below to `.env`.
4. Put the same key in all three files.
5. Never commit the `.env` files or paste the key into source code.

`mcp_servers/hotel_mcp/.env`:

```dotenv
SERPAPI_API_KEY=replace-with-your-private-key
SERPAPI_BASE_URL=https://serpapi.com/search.json
PORT=8001
```

`mcp_servers/flight_mcp/.env`:

```dotenv
SERPAPI_API_KEY=replace-with-your-private-key
SERPAPI_BASE_URL=https://serpapi.com/search.json
PORT=8002
```

`mcp_servers/location_mcp/.env`:

```dotenv
SERPAPI_API_KEY=replace-with-your-private-key
SERPAPI_BASE_URL=https://serpapi.com/search.json
OPEN_METEO_GEOCODING_URL=https://geocoding-api.open-meteo.com/v1/search
PORT=8006
```

Hotel and flight no longer use Amadeus OAuth. Do not add
`AMADEUS_CLIENT_ID`, `AMADEUS_CLIENT_SECRET`, or `AMADEUS_BASE_URL`.

The key is sent to SerpApi only as the `api_key` query parameter. Provider
errors and logs are sanitized so the key is not included in application logs.

## Keyless services

The remaining services can use their committed example defaults:

`mcp_servers/itinerary_mcp/.env.example`:

```dotenv
PORT=8003
```

`mcp_servers/weather_mcp/.env.example`:

```dotenv
OPEN_METEO_GEOCODING_URL=https://geocoding-api.open-meteo.com/v1/search
OPEN_METEO_FORECAST_URL=https://api.open-meteo.com/v1/forecast
PORT=8004
```

`mcp_servers/currency_mcp/.env.example`:

```dotenv
FRANKFURTER_BASE_URL=https://api.frankfurter.dev/v1
PORT=8005
```

You only need private `.env` copies for these services when overriding a
default URL or port.

## Provider contracts

### Flight MCP

`search_flights` calls SerpApi with `engine=google_flights` and supports:

- `departure_id` and `arrival_id` as three-letter IATA codes
- `outbound_date` and optional `return_date` in `YYYY-MM-DD` format
- `adults`, `children`, `travel_class`, `currency`, and optional `max_price`

The service sends `type=1` for round trips and `type=2` for one-way searches.
It combines `best_flights` and `other_flights`, normalizes segments and
layovers, and returns at most ten options. Travel classes use SerpApi values
1 through 4: economy, premium economy, business, and first.

### Hotel MCP

`search_hotels` calls SerpApi with `engine=google_hotels` and supports:

- destination query, check-in date, and check-out date
- adults, children, currency, optional minimum/maximum price, and rating

It normalizes the `properties` array into name, description, nightly price,
rating, review count, hotel class, amenities, image, coordinates, and property
token. It returns at most ten properties.

### Itinerary MCP

`create_itinerary` validates destination, dates, travelers, interests, pace,
budget, currency, and optional provider-backed activities. It creates a stable
day-by-day structure for trips up to 21 days.

When no verified activities are supplied, it creates an honest planning
framework instead of inventing place names. Extra activities are returned as
unscheduled rather than silently dropped.

### Weather MCP

The weather service resolves a place with Open-Meteo geocoding and then calls
the forecast API. It supports current conditions, daily forecasts, explicit
date ranges, temperature/wind/precipitation units, and a maximum 16-day
forecast horizon.

### Currency MCP

The currency service uses Frankfurter current or historical reference rates.
Inputs are validated as ISO-style three-letter currency codes and monetary
calculations use `Decimal` rounding. Same-currency conversion does not make a
network request.

Call `list_supported_currencies` before offering a currency in the UI when
provider coverage matters. For example, Frankfurter may not publish LKR even
though it publishes USD and EUR.

### Location MCP

`resolve_location` uses keyless Open-Meteo geocoding. `search_places` uses
SerpApi `engine=google_maps`; it accepts a nearby place name or explicit
latitude/longitude and returns normalized local results.

## Local run

Install dependencies from the repository root:

```powershell
.\.venv\Scripts\python.exe -m pip install -r mcp_servers\hotel_mcp\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r mcp_servers\flight_mcp\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r mcp_servers\itinerary_mcp\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r mcp_servers\weather_mcp\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r mcp_servers\currency_mcp\requirements.txt
.\.venv\Scripts\python.exe -m pip install -r mcp_servers\location_mcp\requirements.txt
```

Start each server in its own terminal:

```powershell
.\.venv\Scripts\python.exe mcp_servers\hotel_mcp\server.py
.\.venv\Scripts\python.exe mcp_servers\flight_mcp\server.py
.\.venv\Scripts\python.exe mcp_servers\itinerary_mcp\server.py
.\.venv\Scripts\python.exe mcp_servers\weather_mcp\server.py
.\.venv\Scripts\python.exe mcp_servers\currency_mcp\server.py
.\.venv\Scripts\python.exe mcp_servers\location_mcp\server.py
```

Health endpoints:

```text
http://localhost:8001/health
http://localhost:8002/health
http://localhost:8003/health
http://localhost:8004/health
http://localhost:8005/health
http://localhost:8006/health
```

MCP endpoints use the same hosts and ports with `/mcp`.

## Backend registration

`backend/.env` must point to each MCP endpoint:

```dotenv
HOTEL_MCP_URL=http://localhost:8001/mcp
FLIGHT_MCP_URL=http://localhost:8002/mcp
ITINERARY_MCP_URL=http://localhost:8003/mcp
WEATHER_MCP_URL=http://localhost:8004/mcp
CURRENCY_MCP_URL=http://localhost:8005/mcp
LOCATION_MCP_URL=http://localhost:8006/mcp
```

`backend/agents/mcp_client.py` owns the service registry. Specialists request
tools with `MultiServerMCPClient.get_tools(server_name=...)`; the resulting
connection-backed tools open a fresh MCP session when invoked. Do not return
tools loaded from a temporary session because they would remain bound to a
closed stream.

The current permissions are:

| Agent | Allowed MCP services |
| --- | --- |
| Hotel | `hotel-mcp` |
| Flight | `flight-mcp` |
| Itinerary | `location-mcp`, `itinerary-mcp` |
| Weather | `weather-mcp` |
| Currency | `currency-mcp` |
| Location | `location-mcp` |

This is enforced by tool binding, not only by prompts.

## Tests

Provider HTTP tests use `httpx.MockTransport`. They validate request mapping,
normalization, limits, timeouts, malformed inputs, empty result arrays, and
secret redaction without consuming API credits.

```powershell
.\.venv\Scripts\python.exe -m pytest -q mcp_servers\hotel_mcp\tests
.\.venv\Scripts\python.exe -m pytest -q mcp_servers\flight_mcp\tests
.\.venv\Scripts\python.exe -m pytest -q mcp_servers\itinerary_mcp\tests
.\.venv\Scripts\python.exe -m pytest -q mcp_servers\weather_mcp\tests
.\.venv\Scripts\python.exe -m pytest -q mcp_servers\currency_mcp\tests
.\.venv\Scripts\python.exe -m pytest -q mcp_servers\location_mcp\tests
```

Live provider calls are optional manual checks. They spend SerpApi credits and
must not be part of CI.

## Deployment

`render.yaml` deploys all six MCP directories as independent Render services
and deploys the backend as a seventh service. Production must use:

```text
TRIPWEAVER_TOOL_MODE=mcp
```

Render injects each MCP service's `RENDER_EXTERNAL_HOSTNAME` into the backend as
`HOTEL_MCP_HOST`, `FLIGHT_MCP_HOST`, `ITINERARY_MCP_HOST`,
`WEATHER_MCP_HOST`, `CURRENCY_MCP_HOST`, or `LOCATION_MCP_HOST`. The backend
converts those hostnames to HTTPS `/mcp` URLs and connects through
`MultiServerMCPClient` with streamable HTTP.

When a generated `*_MCP_HOST` is present, it takes precedence over the matching
`*_MCP_URL`. This prevents stale manual URLs from bypassing the service wired by
the current Blueprint. Set complete `*_MCP_URL` values only when deploying the
services manually and no generated host variables are available.

For a manual container deployment, set the complete public URLs instead:

```text
HOTEL_MCP_URL=https://YOUR_HOTEL_SERVICE/mcp
FLIGHT_MCP_URL=https://YOUR_FLIGHT_SERVICE/mcp
ITINERARY_MCP_URL=https://YOUR_ITINERARY_SERVICE/mcp
WEATHER_MCP_URL=https://YOUR_WEATHER_SERVICE/mcp
CURRENCY_MCP_URL=https://YOUR_CURRENCY_SERVICE/mcp
LOCATION_MCP_URL=https://YOUR_LOCATION_SERVICE/mcp
```

Add provider credentials only to the services that require them. The MCP
services do not receive the OpenAI key, and the backend does not receive the
SerpApi key in MCP mode. Only the backend needs `OPENAI_API_KEY`.

Confirm every MCP `/health` endpoint, then check backend `/health`. Runtime
proof requires `tool_runtime.mode` to be `mcp`, transport to be
`streamable_http`, all six servers to be `available`, and
`configured_servers` to be `6`. See `BOOTCAMP_DEPLOYMENT.md` for the complete
Blueprint procedure and free-tier limitations.

`TRIPWEAVER_TOOL_MODE=local` is retained only as an explicit local-development
fallback. It does not prove MCP transport and must not be used for the assessed
deployment.

## Adding another MCP service

1. Create a sibling directory with a provider client, `server.py`, tests,
   `.env.example`, `Dockerfile`, and `railway.json`.
2. Validate and normalize all provider data at the service boundary.
3. Return `{"ok": false, "error": ...}` for expected failures and redact
   credentials from errors and logs.
4. Register the server name and URL in `backend/agents/mcp_client.py`.
5. Bind it only to the intended specialist in `backend/agents/nodes.py`.
6. Add intent routing and prompt changes only when the capability needs a new
   agent.
7. Map structured results in `backend/api/sse.py` and frontend stream types.
8. Add health, backend contract, SSE, reducer, component, and provider tests.
9. Add the service to Compose and deployment documentation.
