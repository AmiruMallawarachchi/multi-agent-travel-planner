# TripWeaver ✈️
## MCP-Based Multi-Agent Travel Planner

TripWeaver is a conversational travel-planning assistant powered by **LangGraph**, **Model Context Protocol (MCP)**, **FastAPI**, and **Gradio**. A traveller describes what they need in natural language; an intent router dispatches to the right specialist agent (Hotel or Flight), which reaches live services through MCP servers to search and book — then streams the answer back to the chat interface.

---

## Architecture

```
Traveller (Gradio Chat UI)
        │  HTTP SSE streaming
        ▼
  FastAPI Backend  (main.py)
        │  LangGraph astream_events
        ▼
  ┌────────────────────────────────┐
  │  Intent Router (detect_intent) │  ← classifies query
  └──────┬─────────────────────────┘
         │  conditional edge
    ┌────┴───────────┬───────────────┐
    ▼                ▼               ▼
General QA      Hotel Agent     Flight Agent
(No MCP call)  (MCP tools)     (MCP tools)
                    │               │
                    ▼               ▼
           Hotel MCP Server   Flight MCP Server
           ┌─────────────┐   ┌──────────────┐
           │ list_hotels │   │ list_flights │
           │search_hotels│   │search_flights│
           │  book_hotel │   │  book_flight │
           └─────────────┘   └──────────────┘
```

---

## Project Structure

```
multi-agent-travel-planner/
├── agents/
│   ├── entity.py        # Shared AgentState (LangGraph TypedDict)
│   ├── llm.py           # LLM factory (get_llm)
│   ├── prompts.py       # System prompts for all agents
│   ├── tools.py         # MCP client + LangChain @tool definitions
│   ├── nodes.py         # Node functions: detect_intent, hotel, flight, general_qa
│   └── graph.py         # LangGraph StateGraph + intent router
├── mcp_servers/
│   ├── hotel_server.py  # Hotel MCP Server (list/search/book)
│   └── flight_server.py # Flight MCP Server (list/search/book)
├── main.py              # FastAPI backend (SSE streaming /chat endpoint)
├── frontend.py          # Gradio chat UI
├── requirements.txt
├── .env.example
└── README.md
```

---

## Quick Start

### 1 — Clone & set up environment

```bash
git clone https://github.com/your-username/multi-agent-travel-planner.git
cd multi-agent-travel-planner

# Create virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (macOS/Linux)
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2 — Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and add your OpenAI API key:

```env
OPENAI_API_KEY=sk-...your-key-here...
OPENAI_MODEL=gpt-4o-mini
BACKEND_URL=http://localhost:8000
```

> **No hotel/flight API keys needed** — the MCP servers use realistic mock data by default.

### 3 — Start the application

Open **two terminals**:

**Terminal 1 — FastAPI Backend:**
```bash
uvicorn main:app --reload --port 8000
```

**Terminal 2 — Gradio Frontend:**
```bash
python frontend.py
```

Then open your browser at: **http://localhost:7860**

> The MCP servers are launched automatically as subprocesses by the agent tools — you do **not** need to start them manually.

---

## MCP Server Guide

The two MCP servers (`mcp_servers/hotel_server.py` and `mcp_servers/flight_server.py`) run as **separate processes** using the MCP stdio transport. They are invoked by the agents via `agents/tools.py`.

### Testing MCP servers standalone

You can call a server directly for debugging:

```bash
# Test hotel server manually
python mcp_servers/hotel_server.py
```

Or use the MCP inspector (if installed):
```bash
npx @modelcontextprotocol/inspector python mcp_servers/hotel_server.py
```

### MCP Tool Reference

**Hotel MCP Server** (`hotel_server.py`)

| Tool | Required Args | Optional Args |
|---|---|---|
| `list_hotels` | `city`, `check_in`, `check_out` | — |
| `search_hotels` | `city`, `check_in`, `check_out` | `budget`, `guests`, `stars` |
| `book_hotel` | `hotel_id`, `guest_name`, `check_in`, `check_out` | `guests` |

**Flight MCP Server** (`flight_server.py`)

| Tool | Required Args | Optional Args |
|---|---|---|
| `list_flights` | `origin`, `destination`, `date` | — |
| `search_flights` | `origin`, `destination`, `date` | `passengers`, `cabin_class`, `budget` |
| `book_flight` | `flight_id`, `passenger_name`, `origin`, `destination`, `date` | `passengers`, `cabin_class` |

### Replacing mock data with a real API

The mock data lives entirely inside the MCP servers. To connect to a real provider:
1. Replace the `_HOTELS` / `_FLIGHTS` lists with live API calls.
2. No changes needed in `agents/`, `main.py`, or `frontend.py` — the MCP layer decouples them.

---

## Example Conversations

| User says | What happens |
|---|---|
| "Find hotels in Paris for 2 guests, Aug 10–15" | Hotel Agent → `search_hotels` MCP tool → formatted results |
| "Book hotel H002 for John Smith" | Hotel Agent → `book_hotel` MCP tool → confirmation number |
| "Flights from London to Tokyo on Dec 10, business class" | Flight Agent → `search_flights` MCP tool → filtered results |
| "What documents do I need to travel to Japan?" | General QA Agent → direct LLM answer, no MCP call |
| "Book flight F003 for Jane Doe" | Flight Agent → `book_flight` MCP tool → confirmation |

---

## Agent Routing Logic

```
User message
    │
    ▼ detect_intent_node (LLM classifier)
    │
    ├── "hotel"   → Hotel Agent  → LLM decides: list / search / book
    ├── "flight"  → Flight Agent → LLM decides: list / search / book
    └── "general" → General QA  → direct LLM response
```

The LangGraph conditional edge reads `state["intent"]` set by `detect_intent_node` and routes to the correct node. Each specialist agent uses LangChain tool binding (`llm.bind_tools(...)`) to let the LLM autonomously decide which MCP tool to call and with what parameters.

---

## Graceful Error Handling

- If an MCP server fails or the service is unavailable, the error is **caught at the tool level** (`agents/tools.py`) and returned as a JSON error string.
- The agent's LLM sees the error and responds with a user-friendly message.
- The application **never crashes** — the rest of the conversation continues normally.
- The frontend displays ⚠️ error banners instead of raw stack traces.

---

## Deployment

### Backend (FastAPI)

Deploy to any Python hosting service (Railway, Render, Fly.io, etc.):

```bash
# Render / Railway — set environment variables in dashboard
uvicorn main:app --host 0.0.0.0 --port $PORT
```

### Frontend (Gradio)

Deploy to Hugging Face Spaces:

1. Create a new Space (Gradio SDK).
2. Push your code to the Space repo.
3. Set `BACKEND_URL` to your deployed FastAPI URL in Space secrets.
4. Set `OPENAI_API_KEY` in Space secrets.

Or generate a public share link locally:
```python
# In frontend.py, change:
demo.launch(share=True)
```

### Environment Variables

| Variable | Required | Default | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | ✅ Yes | — | OpenAI API key |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | LLM model name |
| `BACKEND_URL` | No | `http://localhost:8000` | FastAPI backend URL |
| `GRADIO_PORT` | No | `7860` | Gradio server port |

> **Never commit `.env` to version control.** It is listed in `.gitignore`.

---

## Tech Stack

| Concern | Technology |
|---|---|
| Agent orchestration | LangGraph `StateGraph` |
| LLM integration | LangChain + ChatOpenAI |
| External service bridge | Model Context Protocol (MCP) |
| API framework | FastAPI + Uvicorn |
| Streaming | Server-Sent Events (SSE) |
| Chat UI | Gradio |

---

*TripWeaver — Built as part of the AI Engineer Program Enhancement Sprint.*
