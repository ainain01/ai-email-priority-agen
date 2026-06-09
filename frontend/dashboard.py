"""
AI Email Agent — Streamlit Dashboard
"""

import os
import sys
import time
import threading
from datetime import datetime

import streamlit as st

# ── path setup ─────────────────────────────────────────────────────────────────
sys.path.insert(0, os.path.dirname(__file__))

from database import init_db
from agent import process_emails, get_important_emails, get_stats

# ── page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="AI Email Agent",
    page_icon="📬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&family=Syne:wght@400;600;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Syne', sans-serif;
}

.main { background-color: #0a0e1a; }

/* Hero header */
.hero {
    background: linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #0f172a 100%);
    border: 1px solid #1e40af33;
    border-radius: 16px;
    padding: 2rem 2.5rem;
    margin-bottom: 1.5rem;
    position: relative;
    overflow: hidden;
}
.hero::before {
    content: '';
    position: absolute;
    top: -50%;
    left: -50%;
    width: 200%;
    height: 200%;
    background: radial-gradient(circle at 30% 50%, #1d4ed820 0%, transparent 50%),
                radial-gradient(circle at 80% 20%, #7c3aed15 0%, transparent 40%);
    pointer-events: none;
}
.hero h1 {
    color: #f8fafc;
    font-size: 2rem;
    font-weight: 800;
    margin: 0 0 0.25rem 0;
    letter-spacing: -0.5px;
}
.hero p { color: #94a3b8; margin: 0; font-size: 0.95rem; }

/* Stat cards */
.stat-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    text-align: center;
    transition: border-color 0.2s;
}
.stat-card:hover { border-color: #374151; }
.stat-number { font-size: 2rem; font-weight: 800; font-family: 'JetBrains Mono', monospace; }
.stat-label { color: #6b7280; font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; margin-top: 0.25rem; }

/* Priority badges */
.badge {
    display: inline-block;
    padding: 0.2rem 0.65rem;
    border-radius: 6px;
    font-size: 0.72rem;
    font-weight: 700;
    font-family: 'JetBrains Mono', monospace;
    letter-spacing: 0.5px;
}
.badge-HIGH   { background: #7f1d1d; color: #fca5a5; border: 1px solid #991b1b; }
.badge-MEDIUM { background: #78350f; color: #fcd34d; border: 1px solid #92400e; }
.badge-LOW    { background: #1e3a5f; color: #93c5fd; border: 1px solid #1e40af; }

/* Email notification card */
.email-card {
    background: #111827;
    border: 1px solid #1f2937;
    border-left: 4px solid #374151;
    border-radius: 12px;
    padding: 1.25rem 1.5rem;
    margin-bottom: 0.875rem;
    transition: all 0.2s;
}
.email-card:hover { border-color: #374151; border-left-color: #3b82f6; background: #131d30; }
.email-card.HIGH  { border-left-color: #ef4444 !important; }
.email-card.MEDIUM{ border-left-color: #f59e0b !important; }
.email-card.LOW   { border-left-color: #3b82f6 !important; }

.email-subject { color: #f1f5f9; font-size: 1rem; font-weight: 600; margin-bottom: 0.3rem; }
.email-sender  { color: #6b7280; font-size: 0.82rem; font-family: 'JetBrains Mono', monospace; }
.email-reason  { color: #94a3b8; font-size: 0.85rem; margin-top: 0.5rem; font-style: italic; }
.email-meta    { color: #4b5563; font-size: 0.75rem; margin-top: 0.6rem; font-family: 'JetBrains Mono', monospace; }
.email-preview { color: #64748b; font-size: 0.82rem; margin-top: 0.4rem; line-height: 1.5; }

/* Category chip */
.category {
    display: inline-block;
    background: #1f2937;
    color: #9ca3af;
    border: 1px solid #374151;
    border-radius: 4px;
    padding: 0.1rem 0.5rem;
    font-size: 0.7rem;
    font-family: 'JetBrains Mono', monospace;
    margin-left: 0.5rem;
}

/* Sidebar */
section[data-testid="stSidebar"] {
    background: #0d1117 !important;
    border-right: 1px solid #1f2937;
}

/* Buttons */
.stButton > button {
    background: #1d4ed8;
    color: white;
    border: none;
    border-radius: 8px;
    font-family: 'Syne', sans-serif;
    font-weight: 600;
    transition: background 0.2s;
}
.stButton > button:hover { background: #2563eb; }

/* No emails */
.empty-state {
    text-align: center;
    padding: 4rem 2rem;
    color: #374151;
}
.empty-state h3 { font-size: 1.25rem; color: #4b5563; }
.empty-state p  { font-size: 0.9rem; margin-top: 0.5rem; }

/* Live indicator */
.live-dot {
    display: inline-block;
    width: 8px; height: 8px;
    background: #22c55e;
    border-radius: 50%;
    animation: pulse 2s infinite;
    margin-right: 6px;
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.4; }
}
</style>
""", unsafe_allow_html=True)


# ── init DB once ───────────────────────────────────────────────────────────────
@st.cache_resource
def startup():
    init_db()
    return True

startup()


# ── sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚙️ Controls")
    st.divider()

    email_source = os.getenv("EMAIL_SOURCE", "mock").upper()
    openai_key = os.getenv("OPENAI_API_KEY", "")
    ai_mode = "🤖 OpenAI GPT" if (openai_key and openai_key != "your-openai-api-key-here") else "📋 Rule-based"

    st.markdown(f"**Email Source:** `{email_source}`")
    st.markdown(f"**AI Engine:** {ai_mode}")
    st.divider()

    if st.button("🔄 Run Agent Now", use_container_width=True):
        with st.spinner("Processing emails..."):
            count = process_emails()
        st.success(f"Processed {count} new emails!")
        time.sleep(1)
        st.rerun()

    st.divider()

    # Auto-refresh toggle
    auto_refresh = st.toggle("⚡ Auto-refresh (30s)", value=False)
    if auto_refresh:
        st.markdown('<span class="live-dot"></span>**Live mode ON**', unsafe_allow_html=True)

    st.divider()

    # Priority filter
    st.markdown("**Filter by Priority**")
    show_high = st.checkbox("🔴 HIGH", value=True)
    show_medium = st.checkbox("🟡 MEDIUM", value=True)
    show_low = st.checkbox("🔵 LOW", value=True)

    st.divider()
    st.markdown("<p style='color:#374151;font-size:0.75rem;'>AI Email Agent v1.0<br>Built with Streamlit + OpenAI</p>", unsafe_allow_html=True)


# ── header ────────────────────────────────────────────────────────────────────
st.markdown("""
<div class="hero">
    <h1>📬 AI Email Agent</h1>
    <p>Intelligent inbox monitoring — only what matters, nothing else.</p>
</div>
""", unsafe_allow_html=True)


# ── stats row ─────────────────────────────────────────────────────────────────
stats = get_stats()
emails = get_important_emails()

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number" style="color:#f8fafc">{stats['total_processed']}</div>
        <div class="stat-label">Total Scanned</div>
    </div>""", unsafe_allow_html=True)

with col2:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number" style="color:#3b82f6">{stats['total_important']}</div>
        <div class="stat-label">Important</div>
    </div>""", unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number" style="color:#ef4444">{stats['high']}</div>
        <div class="stat-label">High Priority</div>
    </div>""", unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number" style="color:#f59e0b">{stats['medium']}</div>
        <div class="stat-label">Medium Priority</div>
    </div>""", unsafe_allow_html=True)

with col5:
    st.markdown(f"""
    <div class="stat-card">
        <div class="stat-number" style="color:#6b7280">{stats['ignored']}</div>
        <div class="stat-label">Ignored</div>
    </div>""", unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)


# ── notifications ─────────────────────────────────────────────────────────────
st.markdown("### 🔔 Important Email Notifications")
st.markdown("---")

# Apply filters
priority_filter = []
if show_high:   priority_filter.append("HIGH")
if show_medium: priority_filter.append("MEDIUM")
if show_low:    priority_filter.append("LOW")

filtered = [e for e in emails if e["priority"] in priority_filter]

if not filtered:
    st.markdown("""
    <div class="empty-state">
        <h3>No important emails yet</h3>
        <p>Click <strong>Run Agent Now</strong> in the sidebar to scan your inbox.</p>
    </div>
    """, unsafe_allow_html=True)
else:
    for em in filtered:
        priority = em.get("priority", "LOW")
        category = em.get("category", "GENERAL")
        subject  = em.get("subject", "(No Subject)")
        sender   = em.get("sender", "unknown")
        reason   = em.get("reason", "")
        preview  = em.get("body_preview", "")
        received = em.get("received_at") or em.get("processed_at") or ""

        if received:
            try:
                dt = datetime.fromisoformat(received.replace("Z", "+00:00"))
                received = dt.strftime("%b %d, %Y  %H:%M UTC")
            except Exception:
                pass

        badge_html = f'<span class="badge badge-{priority}">{priority}</span>'
        cat_html   = f'<span class="category">{category}</span>'

        st.markdown(f"""
        <div class="email-card {priority}">
            <div style="display:flex; align-items:center; gap:0.5rem; margin-bottom:0.4rem;">
                {badge_html}{cat_html}
            </div>
            <div class="email-subject">{subject}</div>
            <div class="email-sender">From: {sender}</div>
            <div class="email-preview">{preview[:200]}{"..." if len(preview) > 200 else ""}</div>
            <div class="email-reason">💡 {reason}</div>
            <div class="email-meta">🕐 {received}</div>
        </div>
        """, unsafe_allow_html=True)


# ── auto-refresh ──────────────────────────────────────────────────────────────
if auto_refresh:
    time.sleep(30)
    st.rerun()
