"""
frontend/app.py
TripWeaver's chat frontend (SRS section 9 - Frontend Extensions: streaming
responses, agent-activity visualisation, user-friendly errors, a travel-
themed responsive layout).

This talks to the FastAPI backend's /chat/stream SSE endpoint over httpx -
it never calls OpenAI or Amadeus directly, and it never receives or stores
their credentials; BACKEND_API_KEY here authenticates the frontend TO the
backend, it is not exposed to the browser.
"""
from __future__ import annotations

import json
import os

import gradio as gr
import httpx
from dotenv import load_dotenv

from theme import CUSTOM_CSS, TRIPWEAVER_THEME, ticker_html

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY", "")
REQUEST_TIMEOUT = httpx.Timeout(90.0, connect=10.0)

ACTIVITY_LABELS = {
    "ROUTING": "figuring out where this goes",
    "SEARCHING": "searching live availability",
    "BOOKING": "confirming your booking",
    "RESPONDING": "writing your answer",
    "CLARIFYING": "need one more detail from you",
}

QUICK_REPLIES = [
    "Find hotels in Paris for 2 adults, Sep 10-14",
    "Search flights from Colombo to London on 2026-09-01",
    "What's the best time of year to visit Kyoto?",
    "Book the first hotel option for John Doe",
]

WELCOME_MESSAGE = {
    "role": "assistant",
    "content": (
        "Hey, I'm TripWeaver ✈️ Tell me where you're headed and I'll pull real hotel and "
        "flight options for you. Try something like *\"Find hotels in Paris, Sep 10-14, "
        "2 adults\"* or tap a suggestion below to get started."
    ),
}

IDLE_TICKER = ticker_html("ready when you are", idle=True)


def _headers() -> dict:
    headers = {"Content-Type": "application/json"}
    if BACKEND_API_KEY:
        headers["X-API-Key"] = BACKEND_API_KEY
    return headers


def _busy(value: str = "") -> dict:
    return gr.update(value=value, interactive=False)


def _free(value: str = "") -> dict:
    return gr.update(value=value, interactive=True)


async def stream_turn(message: str, history: list, session_id: str | None):
    """The one function every send path (button, Enter, quick-reply chips)
    calls. An async generator: each yield pushes a fresh frame to the UI as
    the turn progresses, which is what makes the chat feel like it's
    actually thinking rather than freezing until a full reply arrives."""
    message = (message or "").strip()
    if not message:
        yield history, gr.update(), session_id, _free(), gr.update(interactive=True)
        return

    history = history + [{"role": "user", "content": message}, {"role": "assistant", "content": ""}]
    yield history, ticker_html("connecting…"), session_id, _busy(), gr.update(interactive=False)

    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id

    assistant_text = ""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            async with client.stream(
                "POST", f"{BACKEND_URL}/chat/stream", json=payload, headers=_headers()
            ) as response:
                if response.status_code == 401:
                    raise PermissionError
                if response.status_code == 429:
                    raise TimeoutError
                response.raise_for_status()

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    event = json.loads(line[6:])
                    etype = event.get("type")

                    if etype == "session":
                        session_id = event["session_id"]

                    elif etype == "status":
                        label = ACTIVITY_LABELS.get(event.get("state"), str(event.get("state", "")))
                        yield history, ticker_html(label), session_id, _busy(), gr.update(interactive=False)

                    elif etype == "tool" and event.get("status") == "FAILED":
                        tool = event.get("tool", "a service")
                        yield history, ticker_html(f"{tool} unavailable — recovering"), session_id, _busy(), gr.update(interactive=False)

                    elif etype == "token":
                        assistant_text += event.get("content", "")
                        history[-1]["content"] = assistant_text
                        yield history, ticker_html("writing your answer"), session_id, _busy(), gr.update(interactive=False)

                    elif etype == "error":
                        assistant_text = assistant_text or event.get(
                            "message", "Something went wrong on our side - please try again."
                        )
                        history[-1]["content"] = assistant_text
                        yield history, ticker_html("something went wrong", idle=True), session_id, _free(), gr.update(interactive=True)
                        return

                    elif etype == "done":
                        break

        if not assistant_text:
            history[-1]["content"] = "I didn't get a reply that time - please try again."
        yield history, IDLE_TICKER, session_id, _free(), gr.update(interactive=True)

    except PermissionError:
        history[-1]["content"] = (
            "TripWeaver couldn't authenticate with its own backend. That's a configuration "
            "issue on our end, not yours - please let the site owner know."
        )
        yield history, ticker_html("configuration error", idle=True), session_id, _free(), gr.update(interactive=True)

    except TimeoutError:
        history[-1]["content"] = "You're sending messages a little fast - please wait a few seconds and try again."
        yield history, ticker_html("slow down a little", idle=True), session_id, _free(), gr.update(interactive=True)

    except httpx.RequestError:
        history[-1]["content"] = "I can't reach the TripWeaver backend right now. Please try again in a moment."
        yield history, ticker_html("backend unreachable", idle=True), session_id, _free(), gr.update(interactive=True)


def new_trip():
    return [WELCOME_MESSAGE], IDLE_TICKER, None


def build_app() -> gr.Blocks:
    with gr.Blocks(theme=TRIPWEAVER_THEME, css=CUSTOM_CSS, title="TripWeaver", fill_height=True) as demo:
        session_id = gr.State(None)

        with gr.Column(elem_id="tw-header"):
            gr.Markdown("# TripWeaver ✈")
            gr.Markdown("Your multi-agent travel planner - real hotel & flight search, one chat away.")

        ticker = gr.HTML(IDLE_TICKER)

        chatbot = gr.Chatbot(
            value=[WELCOME_MESSAGE],
            type="messages",
            elem_id="tw-chat",
            height=440,
            show_copy_button=True,
            avatar_images=(None, None),
        )

        with gr.Row(elem_classes=["tw-chip"]):
            chip_buttons = [gr.Button(q, size="sm") for q in QUICK_REPLIES]

        with gr.Row(elem_id="tw-send-row"):
            msg_box = gr.Textbox(
                placeholder="Where are we going?",
                show_label=False,
                scale=8,
                autofocus=True,
            )
            send_btn = gr.Button("Send", variant="primary", scale=1)

        new_trip_btn = gr.Button("New trip", size="sm", variant="secondary")

        gr.Markdown(
            "Hotel & flight search runs on Amadeus's test environment; bookings are simulated "
            "confirmations, not real reservations.",
            elem_id="tw-footer",
        )

        outputs = [chatbot, ticker, session_id, msg_box, send_btn]

        send_btn.click(stream_turn, inputs=[msg_box, chatbot, session_id], outputs=outputs)
        msg_box.submit(stream_turn, inputs=[msg_box, chatbot, session_id], outputs=outputs)

        for chip, question in zip(chip_buttons, QUICK_REPLIES):
            chip.click(lambda q=question: q, outputs=msg_box).then(
                stream_turn, inputs=[msg_box, chatbot, session_id], outputs=outputs
            )

        new_trip_btn.click(new_trip, outputs=[chatbot, ticker, session_id])

    return demo


demo = build_app()

if __name__ == "__main__":
    demo.queue(max_size=32).launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
    )
