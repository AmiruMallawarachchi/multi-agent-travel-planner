"""
frontend/theme.py
TripWeaver's visual identity: a "dusk departure" theme - the deep indigo of
a night sky just after takeoff, a warm coral/amber horizon glow, and a
split-flap "departure board" motif for agent activity, which does double
duty as the SRS section 9 "agent-activity visualisation" requirement and a
genuinely on-brand piece of travel UI rather than a generic spinner.

Palette
  Midnight Indigo #14132B  - page background base
  Dusk Violet     #241F47  - panels, chat bubbles (assistant)
  Horizon Coral   #FF6B5B  - primary accent: send button, links, active states
  Amber Beacon    #FFB84D  - secondary accent: activity ticker, highlights
  Cloud White     #F5F3FF  - primary text on dark
  Mist Grey       #9B95C9  - secondary / muted text

Type
  Space Grotesk - display / headings (a little personality, still legible)
  Inter         - body text
  JetBrains Mono - flight numbers, prices, confirmation codes (departure-
                   board authenticity for anything that's really "data")
"""
import gradio as gr

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&"
    "family=JetBrains+Mono:wght@500;600&display=swap');"
)

TRIPWEAVER_THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.orange,
    secondary_hue=gr.themes.colors.purple,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(
    body_background_fill="#14132B",
    body_text_color="#F5F3FF",
    background_fill_primary="#1B1940",
    background_fill_secondary="#241F47",
    border_color_primary="#3A3470",
    button_primary_background_fill="#FF6B5B",
    button_primary_background_fill_hover="#FF8879",
    button_primary_text_color="#14132B",
    button_secondary_background_fill="#241F47",
    button_secondary_text_color="#F5F3FF",
    block_background_fill="#1B1940",
    block_border_color="#3A3470",
    input_background_fill="#241F47",
    block_title_text_color="#F5F3FF",
    body_text_color_subdued="#9B95C9",
)

CUSTOM_CSS = f"""
{FONT_IMPORT}

:root {{
  --tw-indigo: #14132B;
  --tw-violet: #241F47;
  --tw-coral: #FF6B5B;
  --tw-amber: #FFB84D;
  --tw-cloud: #F5F3FF;
  --tw-mist: #9B95C9;
}}

.gradio-container {{
  background: radial-gradient(ellipse 120% 80% at 50% -10%, #2B2760 0%, var(--tw-indigo) 55%) !important;
  font-family: 'Inter', ui-sans-serif, sans-serif !important;
}}

/* ---- Header ------------------------------------------------------- */
#tw-header h1 {{
  font-family: 'Space Grotesk', ui-sans-serif, sans-serif !important;
  font-weight: 700;
  background: linear-gradient(90deg, var(--tw-cloud) 0%, var(--tw-amber) 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  letter-spacing: -0.02em;
  margin-bottom: 0 !important;
}}
#tw-header p {{ color: var(--tw-mist) !important; margin-top: 2px !important; }}

/* ---- Split-flap activity ticker ------------------------------------ */
#tw-ticker {{
  font-family: 'JetBrains Mono', monospace;
  font-size: 0.82rem;
  font-weight: 600;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: var(--tw-amber);
  background: #100F26;
  border: 1px solid #3A3470;
  border-radius: 8px;
  padding: 8px 14px;
  min-height: 18px;
  display: flex;
  align-items: center;
  gap: 8px;
}}
#tw-ticker.tw-idle {{ color: var(--tw-mist); opacity: 0.7; }}
#tw-ticker .tw-dot {{
  width: 7px; height: 7px; border-radius: 50%;
  background: var(--tw-amber);
  animation: tw-pulse 1.1s ease-in-out infinite;
}}
@keyframes tw-pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: 0.35; transform: scale(0.75); }}
}}

/* ---- Chat bubbles ---------------------------------------------------- */
#tw-chat .message.user {{
  background: var(--tw-coral) !important;
  color: var(--tw-indigo) !important;
  border-radius: 16px 16px 4px 16px !important;
}}
#tw-chat .message.bot {{
  background: var(--tw-violet) !important;
  color: var(--tw-cloud) !important;
  border: 1px solid #3A3470 !important;
  border-radius: 16px 16px 16px 4px !important;
}}
#tw-chat .message.bot code {{
  font-family: 'JetBrains Mono', monospace;
  color: var(--tw-amber);
  background: #100F26;
}}

/* ---- Quick-reply chips ------------------------------------------------ */
.tw-chip button {{
  border-radius: 999px !important;
  border: 1px solid #3A3470 !important;
  background: #1B1940 !important;
  color: var(--tw-mist) !important;
  font-size: 0.85rem !important;
  padding: 6px 14px !important;
}}
.tw-chip button:hover {{
  border-color: var(--tw-coral) !important;
  color: var(--tw-cloud) !important;
}}

/* ---- Misc -------------------------------------------------------------- */
#tw-footer {{ color: var(--tw-mist) !important; font-size: 0.78rem; text-align: center; opacity: 0.8; }}
#tw-send-row {{ gap: 8px; }}

@media (max-width: 640px) {{
  #tw-header h1 {{ font-size: 1.4rem !important; }}
  #tw-ticker {{ font-size: 0.72rem; }}
}}
"""


def ticker_html(text: str, *, idle: bool = False) -> str:
    """Render the activity ticker. `idle=True` dims it between turns."""
    cls = "tw-idle" if idle else ""
    dot = "" if idle else '<span class="tw-dot"></span>'
    return f'<div id="tw-ticker" class="{cls}">{dot}{text}</div>'
