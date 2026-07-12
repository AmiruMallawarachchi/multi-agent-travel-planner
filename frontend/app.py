"""TripWeaver's Gradio frontend and backend SSE client."""
from __future__ import annotations

from html import escape
import json
import os
from pathlib import Path

import gradio as gr
import httpx
from dotenv import load_dotenv

from theme import CUSTOM_CSS, TRIPWEAVER_THEME, ticker_html

load_dotenv()

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000").rstrip("/")
BACKEND_API_KEY = os.getenv("BACKEND_API_KEY", "")
REQUEST_TIMEOUT = httpx.Timeout(90.0, connect=10.0)
BACKDROP_PATH = Path(__file__).parent / "assets" / "travel-cockpit-backdrop.png"

ACTIVITY_LABELS = {
    "ROUTING": "plotting the best path",
    "SEARCHING": "searching live availability",
    "BOOKING": "preparing your confirmation",
    "RESPONDING": "assembling your itinerary",
    "CLARIFYING": "waiting for one more detail",
}

QUICK_REPLIES = [
    "Paris hotels, Sep 10-14",
    "CMB to London, Sep 1",
    "When should I visit Kyoto?",
    "Plan a quiet weekend escape",
]

WELCOME_MESSAGE = {
    "role": "assistant",
    "content": (
        "Welcome aboard. Tell me where you want to go, and I can search live hotel and "
        "flight options or help shape the trip."
    ),
}

IDLE_TICKER = ticker_html("ready for a new route", idle=True)
LANES = [
    ("ROUTING", "Route"),
    ("SEARCHING", "Search"),
    ("BOOKING", "Book"),
    ("RESPONDING", "Reply"),
]


def timeline_html(
    active_state: str | None = None,
    *,
    tool_name: str = "",
    tool_status: str = "",
) -> str:
    """Render the live orchestration rail."""
    active_state = active_state or ""
    lanes = []
    for state, label in LANES:
        classes = ["tw-lane"]
        if state == active_state:
            classes.append("tw-lane-active")
        lanes.append(
            f'<div class="{" ".join(classes)}">'
            f'<span class="tw-lane-dot"></span><span>{escape(label)}</span>'
            "</div>"
        )

    tool_copy = "Standing by for live tools"
    if tool_name:
        tool_copy = f"{tool_name.replace('_', ' ')}: {tool_status.lower() or 'working'}"

    return (
        '<section class="tw-panel tw-agent-panel" aria-label="Agent activity">'
        '<div class="tw-panel-heading"><div><span class="tw-eyebrow">Live orchestration</span>'
        '<h2>Agent activity</h2></div><span class="tw-live-pill"><i></i>Live</span></div>'
        '<div class="tw-lanes">'
        + "".join(lanes)
        + "</div>"
        f'<div class="tw-tool-readout">{escape(tool_copy)}</div>'
        "</section>"
    )


def trip_panel_html(session_id: str | None = None, *, mode: str = "idle") -> str:
    """Render non-sensitive trip session metadata."""
    short_session = f"{session_id[:8]}..." if session_id else "new trip"
    metrics = [
        ("Session", short_session),
        ("Live data", "Amadeus test"),
        ("Booking", "simulated only"),
        ("Mode", mode),
    ]
    return (
        '<section class="tw-panel tw-trip-panel" aria-label="Trip details">'
        '<div class="tw-panel-heading"><div><span class="tw-eyebrow">Current journey</span>'
        '<h2>Trip details</h2></div><span class="tw-secure-mark">Secure</span></div>'
        '<div class="tw-trip-grid">'
        + "".join(
            '<div class="tw-metric">'
            f'<span>{escape(label)}</span><strong>{escape(value)}</strong>'
            "</div>"
            for label, value in metrics
        )
        + "</div></section>"
    )


def _headers() -> dict[str, str]:
    headers = {"Content-Type": "application/json"}
    if BACKEND_API_KEY:
        headers["X-API-Key"] = BACKEND_API_KEY
    return headers


def _busy(value: str = "") -> dict:
    return gr.update(value=value, interactive=False)


def _free(value: str = "") -> dict:
    return gr.update(value=value, interactive=True)


def _tool_label(tool_name: str, status: str) -> str:
    pretty_tool = (tool_name or "service").replace("_", " ")
    if status == "INVOKED":
        if "book" in tool_name:
            return "preparing simulated booking"
        if "search" in tool_name or "list" in tool_name:
            return "searching live availability"
        return f"using {pretty_tool}"
    if status == "SUCCEEDED":
        if "book" in tool_name:
            return "booking confirmation received"
        return f"{pretty_tool} responded"
    if status == "FAILED":
        return f"{pretty_tool} unavailable - recovering"
    return "working on it"


async def stream_turn(message: str, history: list, session_id: str | None):
    """Stream one backend turn into the seven live cockpit surfaces."""
    message = (message or "").strip()
    if not message:
        yield (
            history,
            gr.update(),
            session_id,
            _free(),
            gr.update(interactive=True),
            gr.update(),
            trip_panel_html(session_id),
        )
        return

    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": ""},
    ]
    yield (
        history,
        ticker_html("connecting to your travel team"),
        session_id,
        _busy(),
        gr.update(interactive=False),
        timeline_html("ROUTING"),
        trip_panel_html(session_id, mode="connecting"),
    )

    payload = {"message": message}
    if session_id:
        payload["session_id"] = session_id

    assistant_text = ""
    try:
        async with httpx.AsyncClient(timeout=REQUEST_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{BACKEND_URL}/chat/stream",
                json=payload,
                headers=_headers(),
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
                    event_type = event.get("type")

                    if event_type == "session":
                        session_id = event["session_id"]
                        yield (
                            history,
                            ticker_html("session secured"),
                            session_id,
                            _busy(),
                            gr.update(interactive=False),
                            timeline_html("ROUTING"),
                            trip_panel_html(session_id, mode="routing"),
                        )

                    elif event_type == "status":
                        state = event.get("state", "")
                        label = ACTIVITY_LABELS.get(state, str(state))
                        yield (
                            history,
                            ticker_html(label),
                            session_id,
                            _busy(),
                            gr.update(interactive=False),
                            timeline_html(state),
                            trip_panel_html(session_id, mode=state.lower() or "working"),
                        )

                    elif event_type == "tool":
                        tool = event.get("tool", "service")
                        status = event.get("status", "")
                        active_state = "BOOKING" if "book" in tool else "SEARCHING"
                        yield (
                            history,
                            ticker_html(_tool_label(tool, status)),
                            session_id,
                            _busy(),
                            gr.update(interactive=False),
                            timeline_html(active_state, tool_name=tool, tool_status=status),
                            trip_panel_html(session_id, mode=active_state.lower()),
                        )

                    elif event_type == "token":
                        assistant_text += event.get("content", "")
                        history[-1]["content"] = assistant_text
                        yield (
                            history,
                            ticker_html("assembling your itinerary"),
                            session_id,
                            _busy(),
                            gr.update(interactive=False),
                            timeline_html("RESPONDING"),
                            trip_panel_html(session_id, mode="responding"),
                        )

                    elif event_type == "error":
                        assistant_text = assistant_text or event.get(
                            "message", "Something went wrong on our side - please try again."
                        )
                        history[-1]["content"] = assistant_text
                        yield (
                            history,
                            ticker_html("something went wrong", idle=True),
                            session_id,
                            _free(),
                            gr.update(interactive=True),
                            timeline_html(),
                            trip_panel_html(session_id, mode="attention"),
                        )
                        return

                    elif event_type == "done":
                        break

        if not assistant_text:
            history[-1]["content"] = "I did not get a reply that time - please try again."
        yield (
            history,
            IDLE_TICKER,
            session_id,
            _free(),
            gr.update(interactive=True),
            timeline_html(),
            trip_panel_html(session_id, mode="ready"),
        )

    except PermissionError:
        history[-1]["content"] = (
            "TripWeaver could not authenticate with its backend. This is a site "
            "configuration issue, not a problem with your request."
        )
        yield _error_frame(history, "configuration error", session_id, "attention")
    except TimeoutError:
        history[-1]["content"] = (
            "You are sending messages a little fast. Please wait a few seconds and try again."
        )
        yield _error_frame(history, "slow down a little", session_id, "paused")
    except (httpx.RequestError, httpx.HTTPStatusError):
        history[-1]["content"] = (
            "I cannot reach the TripWeaver backend right now. Please try again in a moment."
        )
        yield _error_frame(history, "backend unreachable", session_id, "offline")


def _error_frame(history: list, label: str, session_id: str | None, mode: str) -> tuple:
    return (
        history,
        ticker_html(label, idle=True),
        session_id,
        _free(),
        gr.update(interactive=True),
        timeline_html(),
        trip_panel_html(session_id, mode=mode),
    )


def new_trip():
    return (
        [WELCOME_MESSAGE],
        IDLE_TICKER,
        None,
        _free(),
        gr.update(interactive=True),
        timeline_html(),
        trip_panel_html(),
    )


def build_app() -> gr.Blocks:
    with gr.Blocks(
        theme=TRIPWEAVER_THEME,
        css=CUSTOM_CSS,
        title="TripWeaver",
        fill_height=True,
    ) as demo:
        session_id = gr.State(None)

        with gr.Row(elem_id="tw-topbar"):
            gr.HTML(
                '<div class="tw-brand"><span class="tw-brand-mark">TW</span>'
                '<div><strong>TripWeaver</strong><span>AI travel studio</span></div></div>'
            )
            new_trip_btn = gr.Button(
                "New trip", size="sm", variant="secondary", elem_id="tw-new-trip"
            )

        with gr.Row(elem_id="tw-workspace", equal_height=True):
            with gr.Column(scale=7, min_width=420, elem_id="tw-chat-shell"):
                gr.HTML(
                    '<div class="tw-chat-heading"><div><span class="tw-eyebrow">Travel concierge</span>'
                    '<h1>Where to next?</h1></div><span class="tw-online"><i></i>Online</span></div>'
                )
                ticker = gr.HTML(IDLE_TICKER)
                chatbot = gr.Chatbot(
                    value=[WELCOME_MESSAGE],
                    type="messages",
                    elem_id="tw-chat",
                    height=480,
                    show_copy_button=True,
                    avatar_images=(None, None),
                )

                with gr.Row(elem_id="tw-suggestions"):
                    chip_buttons = [gr.Button(q, size="sm") for q in QUICK_REPLIES]

                with gr.Row(elem_id="tw-send-row"):
                    msg_box = gr.Textbox(
                        placeholder="Ask about a place, flight, or hotel...",
                        show_label=False,
                        scale=8,
                        autofocus=True,
                        lines=1,
                        max_lines=4,
                    )
                    send_btn = gr.Button(
                        "Send", variant="primary", scale=1, elem_id="tw-send"
                    )

                gr.HTML(
                    '<div class="tw-composer-note"><span>Powered by specialist travel agents</span>'
                    '<span>Bookings are simulated</span></div>'
                )

            with gr.Column(scale=4, min_width=320, elem_id="tw-context-rail"):
                gr.Image(
                    value=str(BACKDROP_PATH),
                    show_label=False,
                    show_download_button=False,
                    interactive=False,
                    container=False,
                    elem_id="tw-backdrop",
                )
                gr.HTML(
                    '<div class="tw-visual-caption"><span>Departure lounge</span>'
                    '<strong>One conversation.<br>Every moving part.</strong></div>'
                )
                trip_panel = gr.HTML(trip_panel_html())
                timeline = gr.HTML(timeline_html())

        gr.HTML(
            '<footer class="tw-footer"><span>TripWeaver</span>'
            '<span>Live search via Amadeus test environment</span></footer>'
        )

        outputs = [chatbot, ticker, session_id, msg_box, send_btn, timeline, trip_panel]
        send_btn.click(stream_turn, inputs=[msg_box, chatbot, session_id], outputs=outputs)
        msg_box.submit(stream_turn, inputs=[msg_box, chatbot, session_id], outputs=outputs)

        for chip, question in zip(chip_buttons, QUICK_REPLIES):
            chip.click(lambda q=question: q, outputs=msg_box).then(
                stream_turn,
                inputs=[msg_box, chatbot, session_id],
                outputs=outputs,
            )

        new_trip_btn.click(new_trip, outputs=outputs)

    return demo


demo = build_app()

if __name__ == "__main__":
    demo.queue(max_size=32).launch(
        server_name="0.0.0.0",
        server_port=int(os.getenv("PORT", "7860")),
    )
