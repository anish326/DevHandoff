"""
DevHandoff — Modern Dark Glassmorphic Frontend
================================================
Futuristic dark-mode UI with cosmic aurora splash landing, real-time subagent
telemetry cards, and interactive 11-section handoff document explorer.
Powered by IBM watsonx.ai (meta-llama/llama-3-3-70b-instruct).

Run with:
    python -m streamlit run frontend/app.py
"""

from __future__ import annotations

import base64
import logging
import os
import time
from pathlib import Path
from typing import Any

import httpx
import streamlit as st

try:
    from frontend.pdf_exporter import generate_handoff_pdf
except ImportError:
    from pdf_exporter import generate_handoff_pdf

_logger = logging.getLogger("devhandoff.frontend")

# ---------------------------------------------------------------------------
# Config & Environment
# ---------------------------------------------------------------------------

BACKEND_URL = "http://localhost:8000"
_API_KEY: str | None = os.getenv("DEVHANDOFF_API_KEY") or None
REQUEST_TIMEOUT = 600  # seconds


def _extract_secrets_map() -> dict[str, str]:
    """Recursively extract key-value pairs from st.secrets."""
    out: dict[str, str] = {}
    try:
        if hasattr(st, "secrets"):
            def _walk(obj: Any) -> None:
                if isinstance(obj, dict) or hasattr(obj, "items"):
                    for k, v in obj.items():
                        if isinstance(v, str):
                            out[str(k)] = v
                            out[str(k).upper()] = v
                        elif isinstance(v, (dict, object)) and hasattr(v, "items"):
                            _walk(v)
            _walk(st.secrets)
    except Exception:
        pass
    return out


def _ensure_backend_running() -> None:
    """Auto-start FastAPI backend in background if running on cloud platforms (e.g. Streamlit Cloud)."""
    root_dir = Path(__file__).resolve().parent.parent
    sub_env = os.environ.copy()
    sub_env["PYTHONPATH"] = str(root_dir)

    sec_map = _extract_secrets_map()
    for k, v in sec_map.items():
        sub_env[k] = v
        os.environ[k] = v

    try:
        r = httpx.get(f"{BACKEND_URL}/health", timeout=1.2)
        if r.status_code == 200:
            return
    except Exception:
        pass
    import subprocess
    import sys
    _logger.info("Auto-launching DevHandoff backend daemon...")
    try:
        subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "backend.main:app", "--port", "8000", "--host", "127.0.0.1"],
            cwd=str(root_dir),
            env=sub_env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        for _ in range(12):
            time.sleep(0.5)
            try:
                if httpx.get(f"{BACKEND_URL}/health", timeout=1.0).status_code == 200:
                    break
            except Exception:
                pass
    except Exception as exc:
        _logger.warning(f"Could not auto-start backend: {exc}")


_ensure_backend_running()

HANDOFF_SECTIONS = [
    "Context",
    "What Changed",
    "Why",
    "Current Implementation",
    "Known Problems",
    "Unfinished Work",
    "Key Files",
    "Dependencies",
    "Tests to Run",
    "Risks",
    "Recommended Next Actions",
]

# Configure Streamlit page — NO default expandable sidebar
st.set_page_config(
    page_title="DevHandoff // AI Developer Transition Platform",
    page_icon="🔀",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ---------------------------------------------------------------------------
# Asset Helpers (Base64 for reliable, zero-broken-link offline rendering)
# ---------------------------------------------------------------------------

def _get_base64_image(filename: str) -> str:
    path = Path(__file__).resolve().parent / filename
    if path.is_file():
        try:
            data = path.read_bytes()
            return f"data:image/jpeg;base64,{base64.b64encode(data).decode()}"
        except Exception:
            pass
    return ""

AURORA_BG_URI = _get_base64_image("aurora_bg.jpg")
COSMIC_BG_URI = _get_base64_image("cosmic_bg.jpg")

# ---------------------------------------------------------------------------
# Global Design System & Custom CSS (Futuristic Dark Glassmorphism)
# ---------------------------------------------------------------------------

_AURORA_URL = f"url('{AURORA_BG_URI}')" if AURORA_BG_URI else "linear-gradient(135deg, #07101f 0%, #0b1b33 45%, #12203a 100%)"

st.markdown(
    f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700;800&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

:root {{
    --page-bg: {_AURORA_URL};
    --cyan: #38bdf8;
    --cyan-hot: #00f2fe;
    --violet: #a78bfa;
    --orange: #fb923c;
    --glass: rgba(10, 18, 36, 0.48);
}}

[data-testid="stSidebar"], section[data-testid="stSidebar"], div[data-testid="collapsedControl"] {{
    display: none !important;
}}
header[data-testid="stHeader"] {{
    background: transparent !important;
}}
#MainMenu, footer, .stDeployButton, [data-testid="stToolbar"] {{
    visibility: hidden !important;
    display: none !important;
}}
.block-container {{
    padding-top: 1.15rem !important;
    padding-bottom: 5rem !important;
    max-width: 1360px !important;
    position: relative;
    z-index: 2;
}}

html, body, [data-testid="stAppViewContainer"], .stApp {{
    font-family: 'Plus Jakarta Sans', 'Outfit', sans-serif;
    color: #e2e8f0;
    background-color: #020617 !important;
}}
[data-testid="stAppViewContainer"] {{
    background: transparent !important;
}}
[data-testid="stAppViewContainer"]::before {{
    content: "" !important;
    display: block !important;
    position: fixed !important;
    inset: -6% !important;
    width: 112% !important;
    height: 112% !important;
    z-index: 0 !important;
    pointer-events: none !important;
    background-image:
        linear-gradient(180deg, rgba(2, 6, 23, 0.30) 0%, rgba(2, 6, 23, 0.62) 100%),
        {f"url('{AURORA_BG_URI}')" if AURORA_BG_URI else "none"} !important;
    background-size: cover !important;
    background-position: center center !important;
    background-repeat: no-repeat !important;
    animation: cosmic-bg-drift 24s ease-in-out infinite alternate !important;
    transform-origin: center center !important;
    will-change: transform !important;
}}
@keyframes cosmic-bg-drift {{
    0% {{ transform: scale(1) translate(0%, 0%); }}
    33% {{ transform: scale(1.06) translate(-1.2%, -0.8%); }}
    66% {{ transform: scale(1.09) translate(1%, 0.8%); }}
    100% {{ transform: scale(1.04) translate(-0.6%, 1.2%); }}
}}
[data-testid="stAppViewContainer"] > .main {{
    background: transparent !important;
}}
[data-testid="stDecoration"] {{
    display: none !important;
}}
</style>
""",
    unsafe_allow_html=True,
)

st.markdown(
    """
<style>
/* ---------- Atmosphere: celestial shimmer ---------- */
.cosmic-aurora-glow {
    position: fixed;
    inset: 0;
    z-index: 1;
    pointer-events: none;
    background:
        radial-gradient(ellipse 65% 45% at 20% 30%, rgba(0, 242, 254, 0.14), transparent 60%),
        radial-gradient(ellipse 60% 50% at 80% 65%, rgba(167, 139, 250, 0.16), transparent 60%),
        radial-gradient(ellipse 45% 40% at 50% 85%, rgba(56, 189, 248, 0.10), transparent 50%);
    animation: aurora-shimmer 10s ease-in-out infinite alternate;
    mix-blend-mode: screen;
}
@keyframes aurora-shimmer {
    0% { opacity: 0.45; transform: scale(0.98); }
    100% { opacity: 0.95; transform: scale(1.04); }
}

/* ---------- Landing Page & Zoom Animations ---------- */
@keyframes landing-zoom-in {
    0% {
        opacity: 0;
        transform: scale(1.08);
        filter: blur(14px);
    }
    100% {
        opacity: 1;
        transform: scale(1);
        filter: blur(0);
    }
}

.landing-screen {
    animation: landing-zoom-in 0.95s cubic-bezier(0.16, 1, 0.3, 1) both;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 24px 0 20px;
    max-width: 980px;
    margin: 0 auto;
}

.landing-hero-card {
    background: rgba(8, 14, 28, 0.55);
    backdrop-filter: blur(28px) saturate(150%);
    -webkit-backdrop-filter: blur(28px) saturate(150%);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 32px;
    padding: 60px 48px;
    text-align: center;
    box-shadow:
        0 30px 90px rgba(0, 0, 0, 0.65),
        0 0 100px rgba(56, 189, 248, 0.15),
        inset 0 1px 0 rgba(255, 255, 255, 0.18);
    position: relative;
    overflow: hidden;
    margin-bottom: 24px;
}

.landing-hero-card::before {
    content: "";
    position: absolute;
    top: -50%; left: -20%; right: -20%; bottom: -50%;
    background: radial-gradient(circle at 50% 30%, rgba(56, 189, 248, 0.14), transparent 60%);
    pointer-events: none;
}

.landing-title {
    font-family: Outfit, sans-serif;
    font-size: clamp(2.8rem, 5.5vw, 4.2rem);
    font-weight: 800;
    line-height: 1.05;
    letter-spacing: -0.035em;
    margin: 0 0 20px;
    color: #ffffff;
}

.landing-title span {
    background: linear-gradient(115deg, #67e8f9 0%, #38bdf8 35%, #a78bfa 70%, #c4b5fd 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}

.landing-subtitle {
    font-size: 1.15rem;
    line-height: 1.7;
    color: #cbd5e1;
    max-width: 720px;
    margin: 0 auto 30px;
}

.landing-meta-row {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    justify-content: center;
    gap: 12px;
}

.landing-meta-item {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    background: rgba(15, 23, 42, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 999px;
    padding: 8px 18px;
    font-size: 0.84rem;
    font-weight: 600;
    color: #94a3b8;
    backdrop-filter: blur(12px);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.25);
}

@keyframes console-zoom-enter {
    0% {
        opacity: 0;
        transform: scale(0.90);
        filter: blur(14px);
    }
    100% {
        opacity: 1;
        transform: scale(1);
        filter: blur(0);
    }
}

.console-zoom-container {
    animation: console-zoom-enter 0.8s cubic-bezier(0.16, 1, 0.3, 1) both;
}

/* Pulsing Enter Button glow */
div[data-testid="stButton"] button[key="enter_console_btn"],
div.stButton > button:has(p:contains("Enter DevHandoff Console")) {
    background: linear-gradient(135deg, #0284c7 0%, #2563eb 50%, #7c3aed 100%) !important;
    border: 1px solid rgba(255, 255, 255, 0.35) !important;
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.08em !important;
    padding: 16px 36px !important;
    border-radius: 999px !important;
    box-shadow: 0 10px 40px rgba(37, 99, 235, 0.4), 0 0 30px rgba(124, 58, 237, 0.3) !important;
    color: #ffffff !important;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1) !important;
}

div.stButton > button[key="enter_console_btn"]:hover,
div[data-testid="stButton"] > button:has(p:contains("Enter DevHandoff Console")):hover {
    transform: translateY(-3px) scale(1.02) !important;
    box-shadow: 0 16px 50px rgba(37, 99, 235, 0.6), 0 0 45px rgba(124, 58, 237, 0.5) !important;
}

/* ---------- Top Navigation Dock ---------- */
.top-nav {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(8, 14, 28, 0.55);
    backdrop-filter: blur(22px) saturate(140%);
    -webkit-backdrop-filter: blur(22px) saturate(140%);
    border: 1px solid rgba(255, 255, 255, 0.12);
    border-radius: 20px;
    padding: 12px 22px;
    margin-bottom: 22px;
    box-shadow:
        0 18px 50px rgba(0, 0, 0, 0.45),
        inset 0 1px 0 rgba(255, 255, 255, 0.12);
    animation: float-in 0.7s ease both;
    position: relative;
    overflow: hidden;
}
.top-nav::after {
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(110deg, transparent 20%, rgba(56,189,248,0.08) 50%, transparent 80%);
    pointer-events: none;
}
.brand-group { display: flex; align-items: center; gap: 12px; }
.brand-mark {
    width: 38px; height: 38px;
    border-radius: 12px;
    display: grid; place-items: center;
    font-weight: 800;
    font-family: Outfit, sans-serif;
    font-size: 1.05rem;
    color: #fff;
    background: linear-gradient(145deg, rgba(56,189,248,0.35), rgba(124,58,237,0.4));
    border: 1px solid rgba(255,255,255,0.2);
    box-shadow: 0 0 22px rgba(56,189,248,0.35);
}
.brand-logo {
    font-family: Outfit, sans-serif;
    font-size: 1.22rem;
    font-weight: 700;
    letter-spacing: 0.14em;
    color: #f8fafc;
}
.brand-tag {
    font-size: 0.64rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.12em;
    background: rgba(56, 189, 248, 0.12);
    color: #7dd3fc;
    border: 1px solid rgba(56, 189, 248, 0.35);
    padding: 4px 10px;
    border-radius: 999px;
}
.status-badge {
    display: flex;
    align-items: center;
    gap: 8px;
    background: rgba(16, 185, 129, 0.12);
    border: 1px solid rgba(52, 211, 153, 0.35);
    color: #6ee7b7;
    font-size: 0.76rem;
    font-weight: 600;
    padding: 7px 14px;
    border-radius: 999px;
    backdrop-filter: blur(12px);
}
.pulse-dot {
    width: 8px; height: 8px;
    background: #34d399;
    border-radius: 50%;
    box-shadow: 0 0 12px #34d399;
    animation: pulse 2s infinite;
}
@keyframes pulse {
    0% { transform: scale(0.9); opacity: 0.65; }
    50% { transform: scale(1.25); opacity: 1; }
    100% { transform: scale(0.9); opacity: 0.65; }
}

/* ---------- Hero splash (aurora glass) ---------- */
.hero-container {
    position: relative;
    border-radius: 28px;
    overflow: hidden;
    border: 1px solid rgba(255, 255, 255, 0.14);
    box-shadow:
        0 30px 80px rgba(0, 0, 0, 0.55),
        0 0 80px rgba(56, 189, 248, 0.08);
    background: rgba(8, 14, 28, 0.45);
    backdrop-filter: blur(20px) saturate(140%);
    -webkit-backdrop-filter: blur(20px) saturate(140%);
    padding: 56px 52px 50px;
    margin-bottom: 22px;
    animation: float-in 0.85s 0.05s ease both;
    min-height: 220px;
}
.hero-container::before {
    display: none !important;
}
.hero-overlay {
    display: none !important;
}
.hero-content { position: relative; z-index: 2; max-width: 760px; }
.hero-pill {
    display: inline-flex;
    align-items: center;
    gap: 8px;
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: #7dd3fc;
    background: rgba(8, 16, 32, 0.45);
    border: 1px solid rgba(56, 189, 248, 0.4);
    padding: 7px 14px;
    border-radius: 999px;
    margin-bottom: 22px;
    backdrop-filter: blur(16px);
    box-shadow: 0 0 24px rgba(56, 189, 248, 0.15);
}
.hero-title {
    font-family: Outfit, sans-serif;
    font-size: clamp(2.4rem, 4.6vw, 3.55rem);
    font-weight: 700;
    line-height: 1.08;
    letter-spacing: -0.03em;
    margin: 0 0 18px;
    color: #ffffff;
    text-shadow: 0 10px 40px rgba(0,0,0,0.45);
}
.hero-title span {
    background: linear-gradient(115deg, #67e8f9 0%, #38bdf8 35%, #a78bfa 70%, #c4b5fd 100%);
    -webkit-background-clip: text;
    background-clip: text;
    -webkit-text-fill-color: transparent;
}
.hero-subtitle {
    font-size: 1.02rem;
    line-height: 1.65;
    color: #cbd5e1;
    max-width: 640px;
    margin: 0;
}

/* ---------- Pillar / glass cards ---------- */
.pillar-card {
    background: rgba(10, 18, 36, 0.5);
    backdrop-filter: blur(18px) saturate(150%);
    -webkit-backdrop-filter: blur(18px) saturate(150%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 22px 20px 20px;
    height: 100%;
    position: relative;
    overflow: hidden;
    box-shadow: 0 16px 40px rgba(0,0,0,0.28), inset 0 1px 0 rgba(255,255,255,0.1);
    animation: float-card 7s ease-in-out infinite;
    transition: transform 0.35s ease, border-color 0.35s ease, box-shadow 0.35s ease;
}
.pillar-card:nth-child(1), .stColumn:nth-child(1) .pillar-card { animation-delay: 0s; }
.stColumn:nth-child(2) .pillar-card { animation-delay: 0.9s; }
.stColumn:nth-child(3) .pillar-card { animation-delay: 1.8s; }
.stColumn:nth-child(4) .pillar-card { animation-delay: 2.6s; }
.pillar-card::before {
    content: "";
    position: absolute;
    width: 140px; height: 140px;
    right: -40px; top: -50px;
    background: radial-gradient(circle, rgba(56,189,248,0.22), transparent 70%);
    pointer-events: none;
}
.pillar-card:hover {
    transform: translateY(-8px);
    border-color: rgba(56, 189, 248, 0.45);
    box-shadow: 0 22px 50px rgba(56, 189, 248, 0.16), 0 0 40px rgba(167, 139, 250, 0.08);
}
@keyframes float-card {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-6px); }
}
.pillar-icon {
    width: 42px; height: 42px;
    border-radius: 12px;
    display: grid; place-items: center;
    font-size: 1.25rem;
    margin-bottom: 14px;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.25);
}
.pillar-title {
    font-family: Outfit, sans-serif;
    font-weight: 650;
    font-size: 1.02rem;
    color: #f8fafc;
    margin-bottom: 6px;
}
.pillar-desc {
    font-size: 0.84rem;
    color: #94a3b8;
    line-height: 1.5;
}

/* ---------- Control console ---------- */
    .control-box {
        background: rgba(9, 16, 32, 0.58);
        backdrop-filter: blur(26px) saturate(160%);
        -webkit-backdrop-filter: blur(26px) saturate(160%);
        border: 1px solid rgba(56, 189, 248, 0.28);
        border-radius: 24px;
        padding: 8px 8px 18px;
        margin-top: 8px;
        margin-bottom: 18px;
        box-shadow:
            0 24px 60px rgba(0, 0, 0, 0.4),
            0 0 50px rgba(56, 189, 248, 0.07),
            inset 0 1px 0 rgba(255,255,255,0.1);
        animation: float-in 0.8s 0.15s ease both;
    }
.console-head {
    display: flex;
    align-items: baseline;
    justify-content: space-between;
    gap: 12px;
    padding: 18px 22px 4px;
}
.console-title {
    font-family: Outfit, sans-serif;
    font-size: 1.28rem;
    font-weight: 650;
    color: #f8fafc;
    margin: 0;
}
.console-kicker {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.7rem;
    letter-spacing: 0.14em;
    text-transform: uppercase;
    color: #38bdf8;
}

/* ---------- Telemetry cards ---------- */
.telemetry-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin: 28px 0 16px 0;
}
.telemetry-title {
    font-family: Outfit, sans-serif;
    font-size: 1.28rem;
    font-weight: 650;
    color: #f8fafc;
}
.agent-glass-card {
    background: rgba(9, 16, 32, 0.58);
    backdrop-filter: blur(18px) saturate(150%);
    -webkit-backdrop-filter: blur(18px) saturate(150%);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 20px;
    padding: 20px 22px;
    position: relative;
    overflow: hidden;
    margin-bottom: 16px;
    min-height: 210px;
    display: flex;
    flex-direction: column;
    justify-content: space-between;
    box-shadow: 0 16px 36px rgba(0,0,0,0.32), inset 0 1px 0 rgba(255,255,255,0.08);
    animation: float-card 8s ease-in-out infinite;
}
.agent-glass-card::after {
    content: "";
    position: absolute;
    width: 180px; height: 180px;
    right: -50px; bottom: -70px;
    background: radial-gradient(circle, rgba(56,189,248,0.18), transparent 70%);
    pointer-events: none;
}
.agent-glass-card.running {
    border-color: rgba(56, 189, 248, 0.55);
    box-shadow: 0 0 32px rgba(56, 189, 248, 0.18), inset 0 1px 0 rgba(255,255,255,0.1);
}
.agent-glass-card.done { border-top: 3px solid #34d399; }
.agent-glass-card.error { border-top: 3px solid #f87171; }
.agent-head {
    display: flex;
    align-items: flex-start;
    justify-content: space-between;
    gap: 10px;
    margin-bottom: 10px;
}
.agent-title {
    font-family: Outfit, sans-serif;
    font-weight: 650;
    font-size: 0.98rem;
    color: #f1f5f9;
}
.agent-tag-done, .agent-tag-running {
    font-size: 0.66rem;
    font-weight: 700;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    padding: 4px 9px;
    border-radius: 999px;
    white-space: nowrap;
}
.agent-tag-done {
    background: rgba(16, 185, 129, 0.15);
    color: #6ee7b7;
    border: 1px solid rgba(16, 185, 129, 0.35);
}
.agent-tag-running {
    background: rgba(56, 189, 248, 0.15);
    color: #7dd3fc;
    border: 1px solid rgba(56, 189, 248, 0.35);
    animation: pulse 1.8s infinite;
}
.agent-summary-box {
    background: rgba(5, 8, 20, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.06);
    border-radius: 14px;
    padding: 12px 14px;
    font-size: 0.84rem;
    line-height: 1.55;
    color: #cbd5e1;
    margin-top: 10px;
}

/* ---------- Solid Black Surrounding Boxes for Text ---------- */
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: rgba(4, 7, 18, 0.94) !important;
    backdrop-filter: blur(28px) saturate(180%) !important;
    -webkit-backdrop-filter: blur(28px) saturate(180%) !important;
    border: 1px solid rgba(255, 255, 255, 0.16) !important;
    border-radius: 20px !important;
    padding: 24px 28px !important;
    margin-bottom: 22px !important;
    box-shadow: 0 20px 50px rgba(0, 0, 0, 0.8), 0 0 35px rgba(0, 0, 0, 0.6) !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] p,
div[data-testid="stVerticalBlockBorderWrapper"] li,
div[data-testid="stVerticalBlockBorderWrapper"] div.stMarkdown {
    color: #f1f5f9 !important;
    font-size: 1.02rem !important;
    line-height: 1.75 !important;
}

div[data-testid="stVerticalBlockBorderWrapper"] h1,
div[data-testid="stVerticalBlockBorderWrapper"] h2,
div[data-testid="stVerticalBlockBorderWrapper"] h3,
div[data-testid="stVerticalBlockBorderWrapper"] h4 {
    color: #ffffff !important;
    font-family: Outfit, sans-serif !important;
    margin-top: 0 !important;
    margin-bottom: 12px !important;
}

code {
    background: rgba(10, 16, 32, 0.95) !important;
    color: #38bdf8 !important;
    border: 1px solid rgba(56, 189, 248, 0.35) !important;
    padding: 3px 8px !important;
    border-radius: 6px !important;
    font-family: 'JetBrains Mono', monospace !important;
    font-size: 0.9em !important;
}

div[data-testid="stAlert"] {
    background: rgba(4, 7, 18, 0.92) !important;
    border: 1px solid rgba(56, 189, 248, 0.35) !important;
    border-radius: 16px !important;
    color: #f1f5f9 !important;
}

.section-badge {
    font-family: 'JetBrains Mono', monospace;
    font-size: 0.72rem;
    font-weight: 600;
    color: #38bdf8;
    background: rgba(56, 189, 248, 0.12);
    border: 1px solid rgba(56, 189, 248, 0.28);
    padding: 3px 8px;
    border-radius: 8px;
    margin-right: 10px;
}

/* ---------- Streamlit widgets ---------- */
.stTextInput > div > div > input {
    background-color: rgba(6, 10, 22, 0.72) !important;
    border: 1px solid rgba(255, 255, 255, 0.14) !important;
    border-radius: 14px !important;
    color: #f1f5f9 !important;
    padding: 12px 18px !important;
    font-size: 0.95rem !important;
}
.stTextInput > div > div > input:focus {
    border-color: #38bdf8 !important;
    box-shadow: 0 0 18px rgba(56, 189, 248, 0.32) !important;
}
.stTextInput label, .stCaption, [data-testid="stWidgetLabel"] p {
    color: #94a3b8 !important;
}

div[data-testid="stForm"] {
    background: rgba(9, 16, 32, 0.78) !important;
    backdrop-filter: blur(26px) saturate(160%) !important;
    -webkit-backdrop-filter: blur(26px) saturate(160%) !important;
    border: 1px solid rgba(56, 189, 248, 0.28) !important;
    border-radius: 24px !important;
    padding: 18px 20px 12px !important;
    margin-top: 4px !important;
    box-shadow:
        0 24px 60px rgba(0, 0, 0, 0.4),
        0 0 50px rgba(56, 189, 248, 0.07),
        inset 0 1px 0 rgba(255,255,255,0.1) !important;
}
[data-testid="stSkillsNudge"] { display: none !important; }
div[data-testid="stFormSubmitButton"] > button, .stButton > button {
    background: linear-gradient(135deg, #0284c7 0%, #2563eb 48%, #7c3aed 100%) !important;
    color: #ffffff !important;
    border: 1px solid rgba(255, 255, 255, 0.28) !important;
    border-radius: 14px !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    box-shadow: 0 8px 28px rgba(37, 99, 235, 0.45) !important;
    transition: all 0.25s ease !important;
}
div[data-testid="stFormSubmitButton"] > button:hover,
.stButton > button:hover {
    transform: translateY(-2px) !important;
    box-shadow: 0 12px 36px rgba(56, 189, 248, 0.55) !important;
}
div[data-testid="stFormSubmitButton"] > button p,
div[data-testid="stFormSubmitButton"] > button span {
    color: #ffffff !important;
    font-weight: 800 !important;
}

[data-testid="stExpander"] {
    background: rgba(9, 16, 32, 0.5) !important;
    border: 1px solid rgba(255,255,255,0.1) !important;
    border-radius: 18px !important;
    backdrop-filter: blur(16px);
}
[data-testid="stExpander"] summary {
    color: #e2e8f0 !important;
}
div[data-testid="stTabs"] [data-baseweb="tab-list"] {
    background: rgba(9, 16, 32, 0.45);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 14px;
    padding: 4px;
    gap: 4px;
}
div[data-testid="stTabs"] button[data-baseweb="tab"] {
    color: #94a3b8 !important;
    border-radius: 10px !important;
}
div[data-testid="stTabs"] button[aria-selected="true"] {
    background: rgba(56, 189, 248, 0.14) !important;
    color: #e0f2fe !important;
}
.stAlert {
    background: rgba(9, 16, 32, 0.7) !important;
    border: 1px solid rgba(56, 189, 248, 0.25) !important;
    border-radius: 14px !important;
    backdrop-filter: blur(12px);
}
h1, h2, h3, h4 { font-family: Outfit, sans-serif !important; color: #f8fafc !important; }

@keyframes float-in {
    from { opacity: 0; transform: translateY(16px); }
    to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 900px) {
    .hero-container { padding: 36px 24px; }
    .hero-title { font-size: 2.15rem; }
    .top-nav { flex-wrap: wrap; gap: 10px; }
}
</style>
""",
    unsafe_allow_html=True,
)


# ---------------------------------------------------------------------------
# Session State & Credentials Management
# ---------------------------------------------------------------------------

def _get_initial_env_val(keys: list[str]) -> str:
    """Read environment variable, st.secrets, or fallback to .env directly."""
    for k in keys:
        val = os.getenv(k, "").strip()
        if val:
            return val
    sec_map = _extract_secrets_map()
    for k in keys:
        if k in sec_map and sec_map[k].strip():
            return sec_map[k].strip()
        if k.upper() in sec_map and sec_map[k.upper()].strip():
            return sec_map[k.upper()].strip()
    try:
        env_path = Path(__file__).resolve().parent.parent / ".env"
        if env_path.is_file():
            for line in env_path.read_text(encoding="utf-8").splitlines():
                for k in keys:
                    if line.strip().startswith(f"{k}=") and not line.strip().startswith("#"):
                        v = line.split("=", 1)[1].strip()
                        if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
                            v = v[1:-1].strip()
                        return v
    except Exception:
        pass
    return ""


def _init_state() -> None:
    defaults = {
        "handoff_markdown": "",
        "subagent_statuses": [],
        "raw_data": {},
        "summaries": {},
        "generating": False,
        "total_duration": None,
        "regen_loading": {},      # section -> bool
        "section_overrides": {},  # section -> override markdown
        "repo_path_input": "demo-repo",
        "branch_input": "master",
        "entered_app": False,
        "watsonx_api_key": _get_initial_env_val(["WATSONX_API_KEY", "IBM_API_KEY", "IBM_CLOUD_API_KEY"]),
        "watsonx_project_id": _get_initial_env_val(["WATSONX_PROJECT_ID", "IBM_PROJECT_ID"]),
        "watsonx_url": _get_initial_env_val(["WATSONX_URL", "IBM_URL"]) or "https://eu-de.ml.cloud.ibm.com",
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


_init_state()

# ---------------------------------------------------------------------------
# Backend API Calls
# ---------------------------------------------------------------------------

def _auth_headers() -> dict[str, str]:
    if _API_KEY:
        return {"X-API-Key": _API_KEY}
    return {}


def _raise_for_status_with_context(resp: httpx.Response) -> None:
    if resp.status_code == 401:
        raise PermissionError("Authentication failed (HTTP 401): Backend API key rejected.")
    if resp.status_code == 422:
        try:
            data = resp.json()
            details = data.get("detail", [])
            if isinstance(details, list):
                messages = [d.get("msg", "").replace("Value error, ", "") for d in details]
                raise ValueError("; ".join(messages))
        except Exception as e:
            if isinstance(e, ValueError):
                raise
    resp.raise_for_status()


def call_generate_handoff(
    repo_path: str,
    branch: str,
    watsonx_api_key: str | None = None,
    watsonx_project_id: str | None = None,
    watsonx_url: str | None = None,
) -> dict:
    payload: dict[str, Any] = {"repo_path": repo_path, "branch": branch}
    if watsonx_api_key:
        payload["watsonx_api_key"] = watsonx_api_key
    if watsonx_project_id:
        payload["watsonx_project_id"] = watsonx_project_id
    if watsonx_url:
        payload["watsonx_url"] = watsonx_url

    resp = httpx.post(
        f"{BACKEND_URL}/generate-handoff",
        json=payload,
        headers=_auth_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status_with_context(resp)
    return resp.json()


def call_regenerate_section(
    section: str,
    repo_path: str,
    branch: str,
    summaries: dict,
    raw: dict,
    watsonx_api_key: str | None = None,
    watsonx_project_id: str | None = None,
    watsonx_url: str | None = None,
) -> str:
    payload: dict[str, Any] = {
        "section": section,
        "repo_path": repo_path,
        "branch": branch,
        "inflight_summary": summaries.get("inflight", ""),
        "archaeologist_summary": summaries.get("archaeologist", ""),
        "drift_summary": summaries.get("drift", ""),
        "inflight_raw": raw.get("inflight", {}),
        "archaeologist_raw": raw.get("archaeologist", {}),
        "drift_raw": raw.get("drift", {}),
    }
    if watsonx_api_key:
        payload["watsonx_api_key"] = watsonx_api_key
    if watsonx_project_id:
        payload["watsonx_project_id"] = watsonx_project_id
    if watsonx_url:
        payload["watsonx_url"] = watsonx_url

    resp = httpx.post(
        f"{BACKEND_URL}/regenerate-section",
        json=payload,
        headers=_auth_headers(),
        timeout=REQUEST_TIMEOUT,
    )
    _raise_for_status_with_context(resp)
    return resp.json().get("markdown", "")


def _split_into_sections(markdown: str) -> dict[str, str]:
    sections: dict[str, str] = {}
    current_section = ""
    current_lines: list[str] = []
    for line in markdown.splitlines():
        if line.startswith("## "):
            if current_section:
                sections[current_section] = "\n".join(current_lines).strip()
            current_section = line[3:].strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_section:
        sections[current_section] = "\n".join(current_lines).strip()
    return sections


def _rebuild_markdown(parsed: dict[str, str], overrides: dict[str, str]) -> str:
    parts = []
    for s in HANDOFF_SECTIONS:
        body = overrides.get(s, parsed.get(s, ""))
        parts.append(f"## {s}\n\n{body}")
    return "\n\n---\n\n".join(parts)


# ---------------------------------------------------------------------------
# UI Components
# ---------------------------------------------------------------------------

def render_atmosphere() -> None:
    st.markdown(
        """
<div class="cosmic-aurora-glow" aria-hidden="true"></div>
""",
        unsafe_allow_html=True,
    )


def render_top_bar(show_home_btn: bool = False) -> None:
    if show_home_btn:
        col_nav, col_home = st.columns([5, 1.3])
        with col_nav:
            st.markdown(
                """
<div class="top-nav" style="margin-bottom: 0;">
  <div class="brand-group">
    <div class="brand-mark">DH</div>
    <div class="brand-logo">DevHandoff</div>
  </div>
</div>
""",
                unsafe_allow_html=True,
            )
        with col_home:
            if st.button("🏠 Landing Screen", use_container_width=True, key="back_to_landing_btn"):
                st.session_state["entered_app"] = False
                st.rerun()
        st.markdown("<div style='margin-bottom: 20px;'></div>", unsafe_allow_html=True)
    else:
        st.markdown(
            """
<div class="top-nav">
  <div class="brand-group">
    <div class="brand-mark">DH</div>
    <div class="brand-logo">DevHandoff</div>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )


def render_landing_page() -> None:
    render_top_bar(show_home_btn=False)
    st.markdown(
        """
<div class="landing-screen">
  <div class="landing-hero-card">
    <div class="hero-pill">Autonomous developer transition intelligence</div>
    <h1 class="landing-title">Welcome to <span>DevHandoff</span></h1>
    <p class="landing-subtitle">
      Eliminate the chaos of developer transitions. Three concurrent AI subagents reconstruct 
      uncommitted work, commit chronology, and doc-to-reality drift in seconds — synthesized 
      into an 11-pillar handoff document by IBM watsonx.ai.
    </p>
    <div class="landing-meta-row">
      <div class="landing-meta-item">⚡ 3 Concurrent Subagents</div>
      <div class="landing-meta-item">🧠 IBM watsonx.ai Engine</div>
      <div class="landing-meta-item">🛡️ 11 Architectural Pillars</div>
      <div class="landing-meta-item">⏱️ Sub-Minute Discovery</div>
    </div>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )

    col_l, col_btn, col_r = st.columns([1.5, 2, 1.5])
    with col_btn:
        if st.button("🚀 Enter DevHandoff Console", use_container_width=True, key="enter_console_btn"):
            st.session_state["entered_app"] = True
            st.rerun()


def render_hero_splash() -> None:
    st.markdown(
        """
<div class="hero-container">
  <div class="hero-overlay"></div>
  <div class="hero-content">
    <div class="hero-pill">Autonomous developer transition intelligence</div>
    <h1 class="hero-title">New Era of <span>Technology</span></h1>
    <p class="hero-subtitle">
      Eliminate the chaos of developer transitions. Three concurrent AI subagents reconstruct 
      uncommitted work, commit chronology, and doc-to-reality drift in seconds — synthesized 
      into an 11-pillar handoff document by IBM watsonx.ai.
    </p>
  </div>
</div>
""",
        unsafe_allow_html=True,
    )


def render_subagent_matrix(statuses: list[dict]) -> None:
    st.markdown(
        """
<div class="telemetry-header">
  <div class="telemetry-title">⚡ Multi-Agent Execution Telemetry</div>
</div>
""",
        unsafe_allow_html=True,
    )

    col1, col2, col3 = st.columns(3)
    agent_defs = [
        ("🔍 In-Flight State Analyzer", "Git diffs, uncommitted state, GitHub issue linkage, test runner"),
        ("⛏️ Commit Archaeologist", "Git log archaeology, commit rationale, author velocity"),
        ("📄 Doc & Reality Drift", "AST symbol extraction, docstring coverage, TODO / FIXME markers"),
    ]

    cards = [col1, col2, col3]
    for i, (col, (name, role)) in enumerate(zip(cards, agent_defs)):
        with col:
            if i < len(statuses):
                s = statuses[i]
                status_str = s.get("status", "done")
                tag_class = "agent-tag-done" if status_str == "done" else "agent-tag-running"
                dur = f" · {s['duration_seconds']:.1f}s" if s.get("duration_seconds") else ""
                summary_text = s.get("summary", "") or "Subagent completed analysis."
                st.markdown(
                    f"""
<div class="agent-glass-card {status_str}">
  <div>
    <div class="agent-head">
      <div class="agent-title">{name}</div>
      <div class="{tag_class}">{status_str.upper()}{dur}</div>
    </div>
    <div style="font-size: 0.78rem; color: #64748b; margin-bottom: 8px;">{role}</div>
  </div>
  <div class="agent-summary-box">
    {summary_text[:280] + ('...' if len(summary_text) > 280 else '')}
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )
            else:
                st.markdown(
                    f"""
<div class="agent-glass-card running">
  <div>
    <div class="agent-head">
      <div class="agent-title">{name}</div>
      <div class="agent-tag-running">RUNNING…</div>
    </div>
    <div style="font-size: 0.78rem; color: #64748b; margin-bottom: 8px;">{role}</div>
  </div>
  <div class="agent-summary-box" style="color: #38bdf8;">
    ⏳ Parallel subagent analyzing repository…
  </div>
</div>
""",
                    unsafe_allow_html=True,
                )


# ---------------------------------------------------------------------------
# Main Application Flow
# ---------------------------------------------------------------------------

def main() -> None:
    render_atmosphere()

    # If user hasn't clicked "Enter DevHandoff Console", show the Landing Page
    if not st.session_state.get("entered_app", False) and not st.session_state.get("handoff_markdown") and not st.session_state.get("generating"):
        render_landing_page()
        return

    # Console view wrapped in zoom-and-enter animated container
    st.markdown('<div class="console-zoom-container">', unsafe_allow_html=True)
    render_top_bar(show_home_btn=not bool(st.session_state.get("handoff_markdown") or st.session_state.get("generating")))

    # Show hero landing banner
    if not st.session_state["handoff_markdown"] and not st.session_state["generating"]:
        render_hero_splash()

    # Command Center Console Form
    with st.container():
        st.markdown(
            """
<div class="control-box">
  <div class="console-head">
    <p class="console-title">Launch analysis console</p>
    <span class="console-kicker">mission control</span>
  </div>
</div>
""",
            unsafe_allow_html=True,
        )

        with st.form("handoff_launch_form"):
            col_path, col_branch = st.columns([3, 1])
            with col_path:
                repo_path = st.text_input(
                    "Repository Directory Path or Public GitHub URL",
                    value=st.session_state["repo_path_input"],
                    placeholder="e.g. demo-repo or https://github.com/org/repo",
                )
            with col_branch:
                branch = st.text_input(
                    "Target Branch",
                    value=st.session_state["branch_input"],
                )

            has_creds = bool(st.session_state.get("watsonx_api_key") and st.session_state.get("watsonx_project_id"))
            exp_label = "⚙️ IBM watsonx.ai AI Settings (Connected ✅)" if has_creds else "⚙️ IBM watsonx.ai AI Settings (API Key & Project ID)"
            with st.expander(exp_label, expanded=not has_creds):
                st.caption("Provide IBM watsonx.ai credentials below, or configure them in Streamlit Cloud Secrets / .env for full LLM synthesis.")
                c_key, c_proj = st.columns(2)
                with c_key:
                    wx_key_input = st.text_input(
                        "IBM Cloud API Key",
                        value=st.session_state.get("watsonx_api_key", ""),
                        type="password",
                        help="Your IBM Cloud API key",
                    )
                with c_proj:
                    wx_proj_input = st.text_input(
                        "watsonx.ai Project ID",
                        value=st.session_state.get("watsonx_project_id", ""),
                        help="Your watsonx.ai project UUID",
                    )
                wx_url_input = st.text_input(
                    "watsonx.ai Regional Endpoint URL",
                    value=st.session_state.get("watsonx_url", "https://eu-de.ml.cloud.ibm.com"),
                    help="e.g. https://eu-de.ml.cloud.ibm.com (Frankfurt) or https://us-south.ml.cloud.ibm.com (Dallas)",
                )

            launch_clicked = st.form_submit_button(
                "⚡ INITIATE MULTI-AGENT ANALYSIS",
                use_container_width=True,
            )

    st.markdown('</div>', unsafe_allow_html=True)

    # -----------------------------------------------------------------------
    # Generation Handler
    # -----------------------------------------------------------------------
    if launch_clicked and repo_path:
        # Save credentials entered in form
        if wx_key_input.strip():
            st.session_state["watsonx_api_key"] = wx_key_input.strip()
        if wx_proj_input.strip():
            st.session_state["watsonx_project_id"] = wx_proj_input.strip()
        if wx_url_input.strip():
            st.session_state["watsonx_url"] = wx_url_input.strip()

        st.session_state["generating"] = True
        st.session_state["handoff_markdown"] = ""
        st.session_state["subagent_statuses"] = []
        st.session_state["section_overrides"] = {}
        st.session_state["regen_loading"] = {}

        # Show running matrix
        placeholder_matrix = st.empty()
        with placeholder_matrix.container():
            render_subagent_matrix([])

        status_box = st.empty()
        status_box.info("🛰️ Subagents dispatched concurrently to IBM watsonx.ai runtime…")

        # Resolve local relative repo path to absolute path before sending
        clean_repo = repo_path.strip().strip("'\"")
        if not clean_repo.startswith(("https://", "http://", "git@")):
            p_local = Path(clean_repo)
            if p_local.is_dir():
                clean_repo = str(p_local.resolve())
            elif (Path(__file__).resolve().parent.parent / clean_repo).is_dir():
                clean_repo = str((Path(__file__).resolve().parent.parent / clean_repo).resolve())

        try:
            t0 = time.perf_counter()
            result = call_generate_handoff(
                repo_path=clean_repo,
                branch=branch,
                watsonx_api_key=st.session_state.get("watsonx_api_key") or None,
                watsonx_project_id=st.session_state.get("watsonx_project_id") or None,
                watsonx_url=st.session_state.get("watsonx_url") or None,
            )
            elapsed = time.perf_counter() - t0

            st.session_state["handoff_markdown"] = result["markdown"]
            st.session_state["subagent_statuses"] = result["subagent_statuses"]
            st.session_state["total_duration"] = result["total_duration_seconds"]
            st.session_state["raw_data"] = result.get("raw", {})
            st.session_state["last_repo_path"] = repo_path
            st.session_state["last_branch"] = branch

            # Cache summaries
            sas = result["subagent_statuses"]
            st.session_state["summaries"] = {
                "inflight": sas[0]["summary"] if len(sas) > 0 else "",
                "archaeologist": sas[1]["summary"] if len(sas) > 1 else "",
                "drift": sas[2]["summary"] if len(sas) > 2 else "",
            }

            with placeholder_matrix.container():
                render_subagent_matrix(result["subagent_statuses"])

            status_box.success(
                f"🎉 Handoff document successfully synthesized in {result['total_duration_seconds']:.1f}s via IBM watsonx.ai!"
            )

        except httpx.ConnectError:
            status_box.error(
                "❌ Backend unreachable. Start it in a terminal with: "
                "`python -m uvicorn backend.main:app --reload --port 8000`"
            )
        except Exception as exc:
            _logger.exception("Handoff generation failed")
            status_box.error(f"❌ Analysis failed: {exc}")
        finally:
            st.session_state["generating"] = False

    # -----------------------------------------------------------------------
    # Render Document & Explorer
    # -----------------------------------------------------------------------
    if st.session_state["handoff_markdown"]:
        # Subagent status matrix
        if not launch_clicked:
            render_subagent_matrix(st.session_state["subagent_statuses"])

        # Explorer Toolbar
        st.markdown("<br>", unsafe_allow_html=True)
        with st.container(border=True):
            t_col1, t_col2, t_col3 = st.columns([3, 1.3, 1.2])
            parsed_sections = _split_into_sections(st.session_state["handoff_markdown"])
            full_doc_md = _rebuild_markdown(parsed_sections, st.session_state["section_overrides"])
            clean_repo_name = Path(st.session_state.get('last_repo_path', repo_path)).name or "repo"

            with t_col1:
                st.markdown(
                    f"### 📑 Synthesized Handoff Document &bull; `{st.session_state.get('last_repo_path', repo_path)}` ({st.session_state.get('last_branch', branch)})"
                )
                if st.session_state.get("total_duration"):
                    st.caption(f"⚡ Synthesis completed in {st.session_state['total_duration']:.1f} seconds across 11 architectural pillars.")
            with t_col2:
                try:
                    pdf_bytes = generate_handoff_pdf(
                        full_doc_md,
                        repo_name=clean_repo_name,
                        branch=st.session_state.get('last_branch', branch),
                    )
                    st.download_button(
                        "📄 Download PDF Report",
                        data=pdf_bytes,
                        file_name=f"DevHandoff_{clean_repo_name}.pdf",
                        mime="application/pdf",
                        use_container_width=True,
                        key="download_pdf_top",
                    )
                except Exception as exc:
                    _logger.error(f"Failed to generate PDF: {exc}")
            with t_col3:
                if st.button("🔄 Analyze Another Repo", use_container_width=True):
                    st.session_state["handoff_markdown"] = ""
                    st.session_state["subagent_statuses"] = []
                    st.rerun()

        # Tabs for Document | Raw Markdown | Raw JSON
        tab_doc, tab_raw_md, tab_raw_json = st.tabs(
            ["📘 Interactive Handoff Document", "📝 Raw Markdown Source", "🔧 Raw Subagent Telemetry"]
        )

        with tab_doc:
            for idx, section_name in enumerate(HANDOFF_SECTIONS, start=1):
                override = st.session_state["section_overrides"].get(section_name)
                content = override if override else parsed_sections.get(
                    section_name, "_No data recorded for this section._"
                )

                with st.container(border=True):
                    h_col, b_col = st.columns([5, 1.1])
                    with h_col:
                        st.markdown(f"#### <span class='section-badge'>{idx:02d}</span> {section_name}", unsafe_allow_html=True)
                    with b_col:
                        regen_key = f"regen_btn_{section_name}"
                        is_loading = st.session_state["regen_loading"].get(section_name, False)
                        btn_label = "⏳ Regenerating…" if is_loading else "🔄 Regenerate"
                        if st.button(btn_label, key=regen_key, disabled=is_loading, use_container_width=True):
                            st.session_state["regen_loading"][section_name] = True
                            try:
                                new_content = call_regenerate_section(
                                    section=section_name,
                                    repo_path=st.session_state.get("last_repo_path", repo_path),
                                    branch=st.session_state.get("last_branch", branch),
                                    summaries=st.session_state["summaries"],
                                    raw=st.session_state["raw_data"],
                                    watsonx_api_key=st.session_state.get("watsonx_api_key") or None,
                                    watsonx_project_id=st.session_state.get("watsonx_project_id") or None,
                                    watsonx_url=st.session_state.get("watsonx_url") or None,
                                )
                                if new_content.startswith(f"## {section_name}"):
                                    new_content = new_content[len(f"## {section_name}"):].strip()
                                st.session_state["section_overrides"][section_name] = new_content
                            except Exception as e:
                                st.error(f"Failed to regenerate section: {e}")
                            finally:
                                st.session_state["regen_loading"][section_name] = False
                            st.rerun()

                    st.markdown(content)

        with tab_raw_md:
            with st.container(border=True):
                st.text_area("Full Document Markdown", value=full_doc_md, height=500)
                d_col1, d_col2 = st.columns(2)
                with d_col1:
                    st.download_button(
                        "⬇️ Download Markdown (.md)",
                        data=full_doc_md,
                        file_name=f"DevHandoff_{clean_repo_name}.md",
                        mime="text/markdown",
                        use_container_width=True,
                        key="download_md_tab",
                    )
                with d_col2:
                    try:
                        pdf_bytes_tab = generate_handoff_pdf(
                            full_doc_md,
                            repo_name=clean_repo_name,
                            branch=st.session_state.get('last_branch', branch),
                        )
                        st.download_button(
                            "📄 Download PDF Report (.pdf)",
                            data=pdf_bytes_tab,
                            file_name=f"DevHandoff_{clean_repo_name}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            key="download_pdf_tab",
                        )
                    except Exception as exc:
                        _logger.error(f"Failed to generate PDF in tab: {exc}")

        with tab_raw_json:
            with st.container(border=True):
                st.json(st.session_state["raw_data"])


if __name__ == "__main__":
    main()
