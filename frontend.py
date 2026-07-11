"""
frontend.py
TripWeaver Gradio Chat Interface.

Features
--------
  - Streaming token-by-token responses via SSE from the FastAPI backend
  - Agent-activity indicator ("🏨 Searching hotel suggestions...", etc.)
  - Loading spinner while agents work
  - User-friendly error messages (no raw stack traces)
  - Travel-themed responsive layout with dark teal palette
  - Conversation history maintained across turns

Run:
  python frontend.py

The BACKEND_URL env var controls which FastAPI instance to connect to.
Default: http://localhost:8000
"""

from __future__ import annotations
import os
import json
import httpx
import gradio as gr
from dotenv import load_dotenv

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")
GRADIO_PORT = int(os.getenv("GRADIO_PORT", "7860"))


# ─────────────────────────────────────────────────────────────
# Core chat function (streaming generator)
# ─────────────────────────────────────────────────────────────

async def chat_fn(message: str, history: list[dict]) -> str:
    """
    Async generator that streams the agent response token-by-token.
    Gradio's ChatInterface calls this for every user message.

    Yields the current accumulated response string on each update so
    Gradio can display live partial text.
    """
    if not message.strip():
        yield "Please type a message to get started. 🌍"
        return

    # Build API history format
    api_history = []
    for turn in history:
        api_history.append({"role": turn["role"], "content": turn["content"]})

    activity_text = ""
    response_text = ""

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{BACKEND_URL}/chat",
                json={"message": message, "history": api_history},
                headers={"Accept": "text/event-stream"},
            ) as stream:
                stream.raise_for_status()

                async for raw_line in stream.aiter_lines():
                    if not raw_line.startswith("data: "):
                        continue

                    try:
                        data = json.loads(raw_line[6:])
                    except json.JSONDecodeError:
                        continue

                    dtype = data.get("type", "")

                    if dtype == "activity":
                        activity_text = data["content"]
                        # Show activity indicator while no response text yet
                        if not response_text:
                            yield f"*{activity_text}*"
                        else:
                            yield response_text

                    elif dtype == "token":
                        response_text += data["content"]
                        yield response_text

                    elif dtype == "error":
                        err_msg = data["content"]
                        if response_text:
                            yield response_text + f"\n\n⚠️ *{err_msg}*"
                        else:
                            yield f"⚠️ {err_msg}"

                    elif dtype == "done":
                        break

    except httpx.ConnectError:
        yield (
            "⚠️ **Cannot connect to TripWeaver backend.**\n\n"
            f"Make sure the FastAPI server is running:\n```\nuvicorn main:app --reload\n```\n"
            f"Backend URL: `{BACKEND_URL}`"
        )
        return
    except httpx.TimeoutException:
        yield "⚠️ **Request timed out.** The agent is taking too long. Please try again."
        return
    except Exception as exc:
        yield f"⚠️ **Unexpected error:** {str(exc)}"
        return

    # Final clean output (removes any leftover activity prefix)
    if response_text:
        yield response_text
    elif not response_text:
        yield "I'm sorry, I couldn't generate a response. Please try again."


# ─────────────────────────────────────────────────────────────
# Custom CSS — Travel-themed dark teal design
# ─────────────────────────────────────────────────────────────

CUSTOM_CSS = """
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');

/* ── Global ── */
* { box-sizing: border-box; }

body, .gradio-container {
    font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif !important;
    background: #0a1628 !important;
    color: #e2e8f0 !important;
}

/* ── Header / Title ── */
.tripweaver-header {
    background: linear-gradient(135deg, #0d4f6e 0%, #1a7a8c 50%, #0f5e7a 100%);
    border-radius: 16px;
    padding: 28px 32px;
    margin-bottom: 16px;
    border: 1px solid rgba(56, 189, 213, 0.25);
    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.4);
    text-align: center;
}

.tripweaver-header h1 {
    font-size: 2.2rem;
    font-weight: 700;
    color: #ffffff;
    margin: 0 0 6px 0;
    letter-spacing: -0.5px;
}

.tripweaver-header p {
    font-size: 1rem;
    color: rgba(255,255,255,0.75);
    margin: 0;
    font-weight: 300;
}

/* ── Chatbot container ── */
.chatbot-wrap .wrap {
    background: #0f1f38 !important;
    border: 1px solid rgba(56, 189, 213, 0.15) !important;
    border-radius: 14px !important;
}

/* ── Message bubbles ── */
.message.user {
    background: linear-gradient(135deg, #1d4e89, #1a6e8c) !important;
    border-radius: 18px 18px 4px 18px !important;
    color: #ffffff !important;
    padding: 12px 16px !important;
    box-shadow: 0 2px 12px rgba(0,0,0,0.3) !important;
}

.message.bot {
    background: #152942 !important;
    border: 1px solid rgba(56, 189, 213, 0.2) !important;
    border-radius: 4px 18px 18px 18px !important;
    color: #e2e8f0 !important;
    padding: 12px 16px !important;
}

/* ── Input area ── */
.input-row textarea {
    background: #152942 !important;
    border: 1px solid rgba(56, 189, 213, 0.3) !important;
    border-radius: 12px !important;
    color: #e2e8f0 !important;
    font-size: 0.95rem !important;
    font-family: 'Inter', sans-serif !important;
    padding: 12px 16px !important;
    transition: border-color 0.2s ease;
}

.input-row textarea:focus {
    border-color: rgba(56, 189, 213, 0.7) !important;
    outline: none !important;
    box-shadow: 0 0 0 3px rgba(56, 189, 213, 0.1) !important;
}

/* ── Submit button ── */
#submit-btn, button.primary {
    background: linear-gradient(135deg, #1a7a8c, #38bdd5) !important;
    border: none !important;
    border-radius: 10px !important;
    color: white !important;
    font-weight: 600 !important;
    font-family: 'Inter', sans-serif !important;
    padding: 10px 20px !important;
    transition: all 0.2s ease !important;
}

#submit-btn:hover, button.primary:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(56, 189, 213, 0.4) !important;
}

/* ── Example queries ── */
.example-set {
    display: flex;
    flex-wrap: wrap;
    gap: 8px;
    margin-top: 10px;
}

.example-btn {
    background: rgba(56, 189, 213, 0.12) !important;
    border: 1px solid rgba(56, 189, 213, 0.3) !important;
    border-radius: 20px !important;
    color: #38bdd5 !important;
    font-size: 0.82rem !important;
    padding: 6px 14px !important;
    cursor: pointer !important;
    transition: all 0.2s ease !important;
    font-family: 'Inter', sans-serif !important;
}

.example-btn:hover {
    background: rgba(56, 189, 213, 0.25) !important;
    border-color: rgba(56, 189, 213, 0.6) !important;
    transform: translateY(-1px) !important;
}

/* ── Scrollbar ── */
::-webkit-scrollbar { width: 6px; }
::-webkit-scrollbar-track { background: #0a1628; }
::-webkit-scrollbar-thumb { background: #1a7a8c; border-radius: 3px; }

/* ── Responsive ── */
@media (max-width: 768px) {
    .tripweaver-header h1 { font-size: 1.6rem; }
    .tripweaver-header { padding: 20px; }
}
"""

# ─────────────────────────────────────────────────────────────
# Example queries (quick-start prompts)
# ─────────────────────────────────────────────────────────────

EXAMPLE_QUERIES = [
    "Find me hotels in Paris for 2 guests, checking in 2025-08-10, checking out 2025-08-15",
    "Search flights from London to Tokyo on 2025-09-01 for 2 passengers, economy class",
    "Book hotel H002 for John Smith, check-in 2025-08-10, check-out 2025-08-15, 2 guests",
    "What are the top things to do in Barcelona?",
    "List all available flights from New York to Dubai on 2025-12-20",
    "Search hotels in Tokyo under $200 per night for 3 stars or more, 1 guest",
]


# ─────────────────────────────────────────────────────────────
# Build Gradio UI
# ─────────────────────────────────────────────────────────────

def build_ui() -> gr.Blocks:
    with gr.Blocks(
        css=CUSTOM_CSS,
        title="TripWeaver — AI Travel Planner",
        theme=gr.themes.Base(
            primary_hue=gr.themes.colors.cyan,
            neutral_hue=gr.themes.colors.slate,
        ),
    ) as demo:

        # ── Header ──────────────────────────────────────────────────
        gr.HTML("""
        <div class="tripweaver-header">
            <h1>✈️ TripWeaver</h1>
            <p>Your MCP-Powered Multi-Agent Travel Planning Assistant</p>
        </div>
        """)

        # ── Chat interface ───────────────────────────────────────────
        chatbot = gr.ChatInterface(
            fn=chat_fn,
            type="messages",
            chatbot=gr.Chatbot(
                label="TripWeaver",
                height=520,
                show_label=False,
                elem_classes=["chatbot-wrap"],
                placeholder=(
                    "<div style='text-align:center; padding: 40px; color: #64748b;'>"
                    "<div style='font-size: 3rem; margin-bottom: 12px;'>🌍</div>"
                    "<div style='font-size: 1.1rem; font-weight: 500; color: #94a3b8;'>Welcome to TripWeaver!</div>"
                    "<div style='font-size: 0.9rem; margin-top: 8px;'>Ask me to find hotels, search flights, or answer any travel question.</div>"
                    "</div>"
                ),
                avatar_images=(None, "https://api.dicebear.com/7.x/bottts/svg?seed=tripweaver&backgroundColor=0d9488"),
                render_markdown=True,
                type="messages",
            ),
            textbox=gr.Textbox(
                placeholder="Ask about hotels, flights, or travel tips... 🌍",
                show_label=False,
                lines=1,
                max_lines=5,
                elem_classes=["input-row"],
                submit_btn="Send ✈️",
            ),
            examples=EXAMPLE_QUERIES,
            cache_examples=False,
            autofocus=True,
        )

        # ── Footer ──────────────────────────────────────────────────
        gr.HTML("""
        <div style="text-align:center; padding: 16px; color: #475569; font-size: 0.8rem; margin-top: 8px;">
            Powered by <strong style="color:#38bdd5;">LangGraph</strong> · 
            <strong style="color:#38bdd5;">MCP</strong> · 
            <strong style="color:#38bdd5;">FastAPI</strong> · 
            <strong style="color:#38bdd5;">Gradio</strong>
            &nbsp;|&nbsp; TripWeaver v1.0
        </div>
        """)

    return demo


# ─────────────────────────────────────────────────────────────
# Entry point
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    demo = build_ui()
    demo.launch(
        server_name="0.0.0.0",
        server_port=GRADIO_PORT,
        share=False,       # set True to get a public Gradio link
        show_error=True,
    )
