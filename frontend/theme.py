"""TripWeaver's premium airport-lounge visual system."""
import gradio as gr

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600&"
    "family=JetBrains+Mono:wght@500;600&display=swap');"
)

TRIPWEAVER_THEME = gr.themes.Base(
    primary_hue=gr.themes.colors.orange,
    secondary_hue=gr.themes.colors.cyan,
    neutral_hue=gr.themes.colors.slate,
    font=[gr.themes.GoogleFont("Inter"), "ui-sans-serif", "system-ui", "sans-serif"],
    font_mono=[gr.themes.GoogleFont("JetBrains Mono"), "ui-monospace", "monospace"],
).set(
    body_background_fill="#0A1120",
    body_text_color="#F7F8FC",
    background_fill_primary="#101A2C",
    background_fill_secondary="#142238",
    border_color_primary="#27364D",
    button_primary_background_fill="#FF7A59",
    button_primary_background_fill_hover="#FF9277",
    button_primary_text_color="#0A1120",
    button_secondary_background_fill="#142238",
    button_secondary_text_color="#F7F8FC",
    block_background_fill="#101A2C",
    block_border_color="#27364D",
    input_background_fill="#0D1728",
    block_title_text_color="#F7F8FC",
    body_text_color_subdued="#A7B1C2",
)

CUSTOM_CSS = f"""
{FONT_IMPORT}

:root {{
  --tw-ink: #0A1120;
  --tw-cabin: #101A2C;
  --tw-panel: #142238;
  --tw-line: #27364D;
  --tw-coral: #FF7A59;
  --tw-cyan: #62D9F5;
  --tw-green: #72D6A0;
  --tw-cloud: #F7F8FC;
  --tw-mist: #A7B1C2;
}}

.gradio-container {{
  max-width: none !important;
  padding: 0 24px !important;
  background: var(--tw-ink) !important;
  font-family: 'Inter', ui-sans-serif, sans-serif !important;
}}

#tw-topbar {{
  width: min(1440px, 100%);
  min-height: 74px;
  margin: 0 auto;
  align-items: center;
  border-bottom: 1px solid rgba(167, 177, 194, 0.16);
}}
#tw-topbar > .form {{ align-items: center; }}
.tw-brand {{ display: flex; align-items: center; gap: 12px; }}
.tw-brand-mark {{
  width: 36px; height: 36px; display: grid; place-items: center;
  border: 1px solid rgba(98, 217, 245, 0.55); border-radius: 8px;
  color: var(--tw-cyan); font: 600 0.72rem 'JetBrains Mono', monospace;
  background: rgba(98, 217, 245, 0.08);
}}
.tw-brand div {{ display: flex; flex-direction: column; gap: 1px; }}
.tw-brand strong {{ font: 700 1rem 'Space Grotesk', sans-serif; color: var(--tw-cloud); }}
.tw-brand span:last-child {{ color: var(--tw-mist); font-size: 0.72rem; }}
#tw-new-trip {{ max-width: 112px; min-width: 112px; border-radius: 6px !important; }}

#tw-workspace {{
  width: min(1440px, 100%);
  min-height: 760px;
  margin: 24px auto 0;
  gap: 18px;
  align-items: stretch;
}}
#tw-chat-shell, #tw-context-rail {{ gap: 14px; }}
#tw-chat-shell {{
  padding: 28px !important;
  background: rgba(16, 26, 44, 0.96);
  border: 1px solid var(--tw-line);
  border-radius: 8px;
  box-shadow: 0 28px 70px rgba(0, 0, 0, 0.28);
}}
.tw-chat-heading, .tw-panel-heading {{
  display: flex; justify-content: space-between; align-items: flex-start; gap: 16px;
}}
.tw-chat-heading h1 {{
  margin: 4px 0 0; color: var(--tw-cloud);
  font: 700 2.55rem/1.05 'Space Grotesk', sans-serif;
  letter-spacing: 0;
}}
.tw-eyebrow {{
  color: var(--tw-cyan); font: 600 0.67rem 'JetBrains Mono', monospace;
  letter-spacing: 0.12em; text-transform: uppercase;
}}
.tw-online, .tw-live-pill {{
  display: inline-flex; align-items: center; gap: 7px;
  color: var(--tw-green); font: 600 0.7rem 'JetBrains Mono', monospace;
  text-transform: uppercase;
}}
.tw-online i, .tw-live-pill i {{
  width: 7px; height: 7px; border-radius: 50%; background: var(--tw-green);
  box-shadow: 0 0 0 4px rgba(114, 214, 160, 0.1);
}}

#tw-ticker {{
  min-height: 36px; display: flex; align-items: center; gap: 8px;
  padding: 9px 12px; border: 1px solid var(--tw-line); border-radius: 6px;
  background: #0D1728; color: var(--tw-cyan);
  font: 600 0.72rem 'JetBrains Mono', monospace;
  letter-spacing: 0.1em; text-transform: uppercase;
}}
#tw-ticker.tw-idle {{ color: var(--tw-mist); opacity: 0.7; }}
#tw-ticker .tw-dot {{
  width: 7px; height: 7px; border-radius: 50%; background: var(--tw-cyan);
  animation: tw-pulse 1.1s ease-in-out infinite;
}}
@keyframes tw-pulse {{
  0%, 100% {{ opacity: 1; transform: scale(1); }}
  50% {{ opacity: 0.35; transform: scale(0.75); }}
}}

#tw-chat {{
  min-height: 400px; border: 0 !important; background: transparent !important;
}}
#tw-chat .bubble-wrap {{ padding-left: 0 !important; padding-right: 0 !important; }}
#tw-chat .message.user {{
  background: var(--tw-coral) !important; color: var(--tw-ink) !important;
  border-radius: 8px 8px 2px 8px !important;
}}
#tw-chat .message.bot {{
  background: var(--tw-panel) !important; color: var(--tw-cloud) !important;
  border: 1px solid var(--tw-line) !important;
  border-radius: 8px 8px 8px 2px !important;
}}
#tw-chat .message.bot code {{
  color: var(--tw-cyan); background: #0D1728;
  font-family: 'JetBrains Mono', monospace;
}}

#tw-suggestions {{ gap: 8px; flex-wrap: wrap; }}
#tw-suggestions button {{
  min-width: fit-content !important; padding: 7px 10px !important;
  border: 1px solid var(--tw-line) !important; border-radius: 6px !important;
  background: #0D1728 !important; color: var(--tw-mist) !important;
  font-size: 0.75rem !important;
}}
#tw-suggestions button:hover {{
  border-color: var(--tw-coral) !important; color: var(--tw-cloud) !important;
}}
#tw-send-row {{
  gap: 8px; padding: 6px; border: 1px solid var(--tw-line);
  border-radius: 8px; background: #0D1728;
}}
#tw-send-row textarea {{
  min-height: 44px !important; border: 0 !important; box-shadow: none !important;
}}
#tw-send {{ min-width: 82px; max-width: 82px; border-radius: 6px !important; }}
.tw-composer-note, .tw-footer {{
  display: flex; justify-content: space-between; gap: 12px;
  color: var(--tw-mist); font-size: 0.68rem;
}}

#tw-context-rail {{ position: relative; }}
#tw-backdrop {{
  height: 282px !important; min-height: 282px !important;
  border: 1px solid var(--tw-line); border-radius: 8px; overflow: hidden;
}}
#tw-backdrop img {{
  width: 100% !important; height: 282px !important; object-fit: cover !important;
}}
.tw-visual-caption {{
  min-height: 84px; margin-top: -98px; padding: 22px;
  position: relative; z-index: 2; pointer-events: none;
  background: linear-gradient(0deg, rgba(10, 17, 32, 0.94), rgba(10, 17, 32, 0));
  border-radius: 0 0 8px 8px;
}}
.tw-visual-caption span {{
  color: var(--tw-cyan); font: 600 0.66rem 'JetBrains Mono', monospace;
  text-transform: uppercase; letter-spacing: 0.12em;
}}
.tw-visual-caption strong {{
  display: block; margin-top: 5px; color: var(--tw-cloud);
  font: 600 1.25rem/1.15 'Space Grotesk', sans-serif;
}}
.tw-panel {{
  padding: 19px; background: rgba(16, 26, 44, 0.96);
  border: 1px solid var(--tw-line); border-radius: 8px;
}}
.tw-panel-heading h2 {{
  margin: 3px 0 0; color: var(--tw-cloud);
  font: 600 1rem 'Space Grotesk', sans-serif; letter-spacing: 0;
}}
.tw-secure-mark {{
  padding: 4px 6px; border: 1px solid var(--tw-line); border-radius: 4px;
  color: var(--tw-mist); font: 500 0.66rem 'JetBrains Mono', monospace;
}}
.tw-trip-grid {{
  display: grid; grid-template-columns: 1fr 1fr; gap: 1px;
  margin-top: 16px; background: var(--tw-line);
}}
.tw-metric {{ min-width: 0; padding: 12px; background: var(--tw-cabin); }}
.tw-metric span {{ display: block; margin-bottom: 5px; color: var(--tw-mist); font-size: 0.65rem; }}
.tw-metric strong {{
  display: block; overflow-wrap: anywhere; color: var(--tw-cloud);
  font: 600 0.73rem 'JetBrains Mono', monospace; text-transform: capitalize;
}}
.tw-lanes {{
  display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px; margin-top: 17px;
}}
.tw-lane {{
  display: flex; flex-direction: column; align-items: center; gap: 7px;
  color: var(--tw-mist); font: 500 0.62rem 'JetBrains Mono', monospace;
}}
.tw-lane-dot {{ width: 100%; height: 3px; border-radius: 2px; background: var(--tw-line); }}
.tw-lane-active {{ color: var(--tw-cyan); }}
.tw-lane-active .tw-lane-dot {{
  background: var(--tw-cyan); box-shadow: 0 0 12px rgba(98, 217, 245, 0.45);
}}
.tw-tool-readout {{
  min-height: 34px; margin-top: 14px; padding: 9px 10px;
  border: 1px solid var(--tw-line); border-radius: 6px; background: #0D1728;
  color: var(--tw-mist); font: 500 0.66rem 'JetBrains Mono', monospace;
  text-transform: capitalize;
}}
.tw-footer {{
  width: min(1440px, 100%); margin: 14px auto 0; padding: 0 2px 22px; opacity: 0.72;
}}

@media (max-width: 900px) {{
  .gradio-container {{ padding: 0 14px !important; }}
  #tw-workspace {{ flex-direction: column !important; min-height: auto; }}
  #tw-chat-shell, #tw-context-rail {{ min-width: 100% !important; }}
  #tw-context-rail {{
    display: grid !important; grid-template-columns: 1fr 1fr; align-items: start;
  }}
  #tw-backdrop, .tw-visual-caption {{ grid-column: 1 / -1; }}
}}

@media (max-width: 640px) {{
  .gradio-container {{ padding: 0 10px !important; }}
  #tw-topbar {{ min-height: 64px; }}
  #tw-workspace {{ margin-top: 10px; }}
  #tw-chat-shell {{ min-width: 0 !important; padding: 18px !important; }}
  .tw-chat-heading h1 {{ font-size: 1.75rem; }}
  #tw-chat {{ height: 400px !important; }}
  #tw-suggestions {{ flex-wrap: nowrap; overflow-x: auto; padding-bottom: 3px; }}
  #tw-suggestions button {{ flex: 0 0 auto; }}
  #tw-context-rail {{ display: flex !important; flex-direction: column; }}
  #tw-backdrop, #tw-backdrop img {{ height: 220px !important; min-height: 220px !important; }}
  .tw-composer-note {{ display: none; }}
  .tw-footer {{ flex-direction: column; padding-bottom: 16px; }}
}}
"""


def ticker_html(text: str, *, idle: bool = False) -> str:
    """Render the compact live activity ticker."""
    css_class = "tw-idle" if idle else ""
    dot = "" if idle else '<span class="tw-dot"></span>'
    return f'<div id="tw-ticker" class="{css_class}">{dot}{text}</div>'
