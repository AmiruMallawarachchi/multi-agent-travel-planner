"""Focused contract tests for the TripWeaver cockpit UI."""
import pytest

import app


def test_dynamic_panels_escape_backend_values():
    timeline = app.timeline_html(
        "SEARCHING", tool_name="<script>", tool_status="SUCCEEDED"
    )
    trip_panel = app.trip_panel_html("a" * 32, mode="<offline>")

    assert "<script>" not in timeline
    assert "&lt;script&gt;" in timeline
    assert "<offline>" not in trip_panel
    assert "&lt;offline&gt;" in trip_panel


def test_new_trip_resets_every_cockpit_surface():
    frame = app.new_trip()

    assert len(frame) == 7
    assert frame[0] == [app.WELCOME_MESSAGE]
    assert frame[2] is None
    assert "Standing by for live tools" in frame[5]
    assert "new trip" in frame[6]


@pytest.mark.asyncio
async def test_empty_message_returns_complete_ui_frame():
    frames = [frame async for frame in app.stream_turn("  ", [], None)]

    assert len(frames) == 1
    assert len(frames[0]) == 7
    assert frames[0][0] == []
