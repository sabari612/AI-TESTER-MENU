import json
import base64
import time

import pandas as pd
import streamlit as st

from comparator.menu_comparator import compare_menus
from database.db import (
    create_comparison, update_comparison, get_comparison,
    list_comparisons, delete_comparison, save_report, load_report,
)
from extractor.factory import extract_menu_from_source
from extractor.web_scraper import scrape_menu_hierarchy
from processing.normalize_menu import normalize_menu
from reports.pdf_report import build_pdf_bytes

TEXT_MODES = {"JSON Text", "API Response Text"}
FILE_MODES = {"JSON File", "PDF", "Image", "Word Document"}

# ── Boons logo (inline SVG) ──────────────────────────────────────────
BOONS_LOGO_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 280 80">
  <defs>
    <linearGradient id="boons_grad" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:#FF8C00"/>
      <stop offset="50%" style="stop-color:#FF6B00"/>
      <stop offset="100%" style="stop-color:#F05A28"/>
    </linearGradient>
  </defs>
  <text x="0" y="62" font-family="Arial Black, Arial, Helvetica, sans-serif"
        font-size="68" font-weight="900" fill="url(#boons_grad)"
        letter-spacing="-2">boons</text>
</svg>
"""

# ── Step labels for workflow ─────────────────────────────────────────
STEPS = [
    ("1", "Upload Menus", "Upload or paste your menu data"),
    ("2", "Compare", "AI analyzes differences"),
    ("3", "Review & Export", "Download detailed report"),
]


def inject_custom_css():
    """Inject modern CSS theme with Boons orange branding and animations."""
    st.markdown("""
    <style>
    /* ── Google Font ──────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap');

    /* ── Animations ──────────────────────────────────────── */
    @keyframes fadeInUp {
        from { opacity: 0; transform: translateY(20px); }
        to   { opacity: 1; transform: translateY(0); }
    }
    @keyframes shimmer {
        0%   { background-position: -200% 0; }
        100% { background-position: 200% 0; }
    }
    @keyframes pulse-glow {
        0%, 100% { box-shadow: 0 0 5px rgba(255,107,0,0.2); }
        50%      { box-shadow: 0 0 20px rgba(255,107,0,0.4); }
    }
    @keyframes float {
        0%, 100% { transform: translateY(0px); }
        50%      { transform: translateY(-6px); }
    }

    /* ── Global ─────────────────────────────────────────── */
    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: linear-gradient(180deg, #FFFCF9 0%, #FFF8F2 40%, #FFFFFF 100%);
    }
    .block-container {
        padding-top: 1rem !important;
        max-width: 1200px;
    }

    /* ── Hide default Streamlit chrome ───────────────────── */
    #MainMenu, header, footer { visibility: hidden; }

    /* ── Hero ─────────────────────────────────────────────── */
    .hero-container {
        background: linear-gradient(135deg, #FFF7F0 0%, #FFE8D6 50%, #FFD4B0 100%);
        border-radius: 20px;
        padding: 2.5rem 3rem;
        margin-bottom: 1.5rem;
        border: 1px solid #FFD4B0;
        box-shadow: 0 8px 32px rgba(255,107,0,0.1);
        position: relative;
        overflow: hidden;
        animation: fadeInUp 0.6s ease-out;
    }
    .hero-container::before {
        content: '';
        position: absolute;
        top: -50%; right: -20%;
        width: 300px; height: 300px;
        background: radial-gradient(circle, rgba(255,107,0,0.08) 0%, transparent 70%);
        border-radius: 50%;
    }
    .hero-logo { width: 150px; margin-bottom: 0.25rem; }
    .hero-title {
        font-size: 1.75rem; font-weight: 800; color: #1a1a2e;
        margin: 0.25rem 0 0.15rem 0; letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 0.95rem; color: #6B7280; margin: 0;
        font-weight: 400; line-height: 1.6; max-width: 500px;
    }
    .hero-badge {
        display: inline-block;
        background: linear-gradient(135deg, #FF6B00, #F05A28);
        color: white; padding: 5px 16px; border-radius: 20px;
        font-size: 0.72rem; font-weight: 700;
        letter-spacing: 1px; margin-top: 0.75rem;
        text-transform: uppercase;
        animation: pulse-glow 2s ease-in-out infinite;
    }
    .hero-emojis {
        font-size: 4rem; opacity: 0.15; line-height: 1;
        animation: float 3s ease-in-out infinite;
    }

    /* ── Step Indicator ──────────────────────────────────── */
    .steps-bar {
        display: flex; justify-content: center; gap: 0;
        margin: 0.5rem 0 2rem 0; animation: fadeInUp 0.8s ease-out;
    }
    .step-item {
        display: flex; align-items: center; gap: 10px;
        padding: 12px 24px; position: relative;
    }
    .step-num {
        width: 32px; height: 32px; border-radius: 50%;
        background: linear-gradient(135deg, #FF6B00, #F05A28);
        color: white; display: flex; align-items: center;
        justify-content: center; font-weight: 800; font-size: 0.85rem;
        box-shadow: 0 3px 10px rgba(255,107,0,0.3);
    }
    .step-text { text-align: left; }
    .step-label { font-weight: 700; font-size: 0.85rem; color: #1a1a2e; }
    .step-desc  { font-size: 0.72rem; color: #9CA3AF; }
    .step-arrow {
        color: #FFB347; font-size: 1.2rem; margin: 0 4px;
        animation: pulse-glow 2s ease-in-out infinite;
    }

    /* ── Source Cards ────────────────────────────────────── */
    .source-card {
        background: #FFFFFF;
        border: 1px solid #F0F0F0;
        border-radius: 16px;
        padding: 1.5rem 1.75rem;
        box-shadow: 0 4px 20px rgba(0,0,0,0.04);
        transition: all 0.3s ease;
        animation: fadeInUp 0.7s ease-out;
        border-top: 3px solid #FF6B00;
    }
    .source-card:hover {
        box-shadow: 0 8px 30px rgba(255,107,0,0.1);
        transform: translateY(-2px);
    }
    .source-card-title {
        font-size: 1.1rem; font-weight: 800; color: #1a1a2e;
        margin-bottom: 0.3rem; display: flex;
        align-items: center; gap: 8px;
    }
    .source-card-desc {
        font-size: 0.82rem; color: #9CA3AF; margin-bottom: 1rem;
    }

    /* ── Metric Cards ────────────────────────────────────── */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #F0F0F0;
        border-radius: 14px;
        padding: 1.2rem 1.25rem;
        box-shadow: 0 4px 16px rgba(0,0,0,0.04);
        transition: all 0.3s ease;
        border-left: 4px solid #FF6B00;
    }
    div[data-testid="stMetric"]:hover {
        box-shadow: 0 6px 24px rgba(255,107,0,0.1);
        transform: translateY(-2px);
    }
    div[data-testid="stMetric"] label {
        color: #6B7280 !important; font-weight: 600 !important;
        font-size: 0.75rem !important; text-transform: uppercase;
        letter-spacing: 0.8px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 2.2rem !important; font-weight: 900 !important;
        color: #1a1a2e !important;
    }

    /* ── Buttons ─────────────────────────────────────────── */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #FF6B00 0%, #F05A28 100%) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important;
        padding: 0.75rem 3rem !important;
        font-weight: 800 !important; font-size: 1.05rem !important;
        letter-spacing: 0.5px;
        box-shadow: 0 6px 20px rgba(240,90,40,0.35) !important;
        transition: all 0.3s ease !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        box-shadow: 0 8px 28px rgba(240,90,40,0.5) !important;
        transform: translateY(-2px) !important;
    }
    .stDownloadButton > button {
        background: linear-gradient(135deg, #FF6B00 0%, #F05A28 100%) !important;
        color: white !important; border: none !important;
        border-radius: 12px !important;
        padding: 0.7rem 2.5rem !important; font-weight: 700 !important;
        box-shadow: 0 6px 20px rgba(240,90,40,0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 8px 28px rgba(240,90,40,0.45) !important;
    }

    /* ── Tabs ────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px; background: #F9FAFB;
        border-radius: 12px; padding: 5px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 10px; padding: 10px 18px;
        font-weight: 600; font-size: 0.83rem;
        transition: all 0.2s ease;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #FF6B00, #F05A28) !important;
        color: white !important; border-radius: 10px;
        box-shadow: 0 3px 12px rgba(255,107,0,0.3);
    }

    /* ── Expander ────────────────────────────────────────── */
    .streamlit-expanderHeader {
        font-weight: 700; color: #374151;
        font-size: 0.95rem; border-radius: 12px;
    }

    /* ── Section Headers ─────────────────────────────────── */
    .section-header {
        display: flex; align-items: center; gap: 10px;
        margin: 1.5rem 0 1rem 0; padding-bottom: 0.5rem;
        border-bottom: 3px solid #FFE0C2;
        animation: fadeInUp 0.5s ease-out;
    }
    .section-header h3 {
        margin: 0; font-size: 1.2rem;
        font-weight: 800; color: #1a1a2e;
    }

    /* ── Divider ─────────────────────────────────────────── */
    .orange-divider {
        height: 3px;
        background: linear-gradient(90deg, #FF6B00, #FFB347, #FFD4B0, transparent);
        border: none; border-radius: 2px; margin: 2rem 0;
    }

    /* ── Rounded elements ────────────────────────────────── */
    .stDataFrame { border-radius: 12px; overflow: hidden; }
    .stAlert { border-radius: 12px !important; }
    [data-testid="stFileUploader"] { border-radius: 12px; }
    [data-testid="stSelectbox"] > div > div { border-radius: 10px !important; }

    /* ── Stats Banner ────────────────────────────────────── */
    .stats-banner {
        background: linear-gradient(135deg, #1a1a2e 0%, #2d2d44 100%);
        border-radius: 16px; padding: 1.5rem 2rem;
        display: flex; justify-content: center; gap: 3rem;
        margin: 1rem 0; animation: fadeInUp 0.6s ease-out;
    }
    .stat-item { text-align: center; }
    .stat-value {
        font-size: 1.8rem; font-weight: 900; color: #FF6B00;
        line-height: 1;
    }
    .stat-label {
        font-size: 0.72rem; color: #9CA3AF; text-transform: uppercase;
        letter-spacing: 1px; margin-top: 4px;
    }

    /* ── Result Badge ────────────────────────────────────── */
    .result-pass {
        background: linear-gradient(135deg, #10B981, #059669);
        color: white; padding: 1rem 2rem; border-radius: 14px;
        text-align: center; font-weight: 700; font-size: 1.1rem;
        box-shadow: 0 4px 16px rgba(16,185,129,0.3);
        animation: fadeInUp 0.5s ease-out;
    }
    .result-fail {
        background: linear-gradient(135deg, #F59E0B, #D97706);
        color: white; padding: 1rem 2rem; border-radius: 14px;
        text-align: center; font-weight: 700; font-size: 1.1rem;
        box-shadow: 0 4px 16px rgba(245,158,11,0.3);
        animation: fadeInUp 0.5s ease-out;
    }

    /* ── Sidebar ─────────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #1a1a2e 0%, #2d2d44 100%) !important;
    }
    [data-testid="stSidebar"] * {
        color: #E5E7EB !important;
    }
    [data-testid="stSidebar"] .sidebar-title {
        color: #FF6B00 !important; font-weight: 800;
        font-size: 1.1rem; margin-bottom: 0.5rem;
    }
    [data-testid="stSidebar"] .sidebar-text {
        font-size: 0.82rem; color: #9CA3AF !important;
        line-height: 1.6;
    }
    [data-testid="stSidebar"] .sidebar-format-badge {
        display: inline-block;
        background: rgba(255,107,0,0.15);
        color: #FF6B00 !important;
        padding: 3px 10px; border-radius: 6px;
        font-size: 0.75rem; font-weight: 600;
        margin: 2px 3px;
    }

    /* ── Footer ──────────────────────────────────────────── */
    .app-footer {
        text-align: center; padding: 2rem 0 1rem 0;
        border-top: 1px solid #F0F0F0; margin-top: 2rem;
    }
    .app-footer-text {
        color: #9CA3AF; font-size: 0.78rem;
    }
    .app-footer-brand {
        color: #FF6B00; font-weight: 800;
    }
    </style>
    """, unsafe_allow_html=True)


def render_sidebar():
    """Render a helpful sidebar with instructions and supported formats."""
    with st.sidebar:
        st.markdown(f'<div style="text-align:center; margin:1rem 0;">{BOONS_LOGO_SVG}</div>',
                    unsafe_allow_html=True)
        st.markdown('<p class="sidebar-title">📖 How to Use</p>', unsafe_allow_html=True)
        st.markdown("""
        <div class="sidebar-text">
        <strong>Step 1:</strong> Upload or paste your menu on the left side.<br><br>
        <strong>Step 2:</strong> Upload the reference menu on the right side.<br><br>
        <strong>Step 3:</strong> Click <strong>Compare Menus</strong> to see results.<br><br>
        <strong>Step 4:</strong> Download the PDF report.
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sidebar-title">📂 Supported Formats</p>', unsafe_allow_html=True)
        st.markdown("""
        <div style="margin-bottom:1rem;">
            <span class="sidebar-format-badge">JSON</span>
            <span class="sidebar-format-badge">PDF</span>
            <span class="sidebar-format-badge">Image</span>
            <span class="sidebar-format-badge">Word</span>
            <span class="sidebar-format-badge">Website</span>
            <span class="sidebar-format-badge">API</span>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("---")
        st.markdown('<p class="sidebar-title">💡 Tips</p>', unsafe_allow_html=True)
        st.markdown("""
        <div class="sidebar-text">
        • Use JSON format for fastest results<br>
        • Ensure images are clear for OCR<br>
        • PDF menus work best with text-based PDFs<br>
        • Check all issue tabs after comparison
        </div>
        """, unsafe_allow_html=True)


def render_header():
    """Render the branded hero header with Boons logo."""
    st.markdown(f"""
    <div class="hero-container">
        <div style="display:flex; align-items:center; gap:20px; flex-wrap:wrap;">
            <div style="flex:1; min-width:280px;">
                <div class="hero-logo">{BOONS_LOGO_SVG}</div>
                <p class="hero-title">🍽️ AI Menu Verification System</p>
                <p class="hero-subtitle">
                    Compare your restaurant menu against a reference source — detect mismatches,
                    missing items, price errors & more with AI-powered analysis.
                </p>
                <span class="hero-badge">✨ AI-POWERED ANALYSIS</span>
            </div>
            <div class="hero-emojis">
                🍔🍕🥗
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


def render_steps():
    """Render the step indicator bar."""
    steps_html = '<div class="steps-bar">'
    for i, (num, label, desc) in enumerate(STEPS):
        steps_html += f"""
        <div class="step-item">
            <div class="step-num">{num}</div>
            <div class="step-text">
                <div class="step-label">{label}</div>
                <div class="step-desc">{desc}</div>
            </div>
        </div>
        """
        if i < len(STEPS) - 1:
            steps_html += '<div class="step-arrow">➤</div>'
    steps_html += '</div>'
    st.markdown(steps_html, unsafe_allow_html=True)


def _init_wizard_state(prefix):
    """Initialise session-state keys for one menu wizard."""
    defaults = {
        f"{prefix}_wizard_step": 0,       # 0=url, 1=categories, 2=subcategories, 3=items
        f"{prefix}_url": "",
        f"{prefix}_hierarchy": None,
        f"{prefix}_categories": [],
        f"{prefix}_selected_cat": None,
        f"{prefix}_subcategories": [],
        f"{prefix}_selected_sub": None,
        f"{prefix}_items": [],
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


def _reset_wizard(prefix):
    """Reset wizard to step 0."""
    keys = [k for k in st.session_state if k.startswith(prefix + "_wizard") or
            k in (f"{prefix}_hierarchy", f"{prefix}_categories",
                  f"{prefix}_selected_cat", f"{prefix}_subcategories",
                  f"{prefix}_selected_sub", f"{prefix}_items")]
    for k in keys:
        if k in st.session_state:
            del st.session_state[k]
    _init_wizard_state(prefix)


def collect_source(label, modes, key_prefix, icon="📄", desc=""):
    """Collect menu source input inside a styled card with wizard for Website URL."""
    _init_wizard_state(key_prefix)

    st.markdown(f"""
    <div class="source-card">
        <div class="source-card-title">{icon} {label}</div>
        <div class="source-card-desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)
    source_type = st.selectbox("Source Type", modes, key=f"{key_prefix}_type",
                               label_visibility="collapsed")

    # ── Non-website modes (unchanged) ────────────────────────
    if source_type != "Website URL":
        payload = {"source_type": source_type, "text": None, "url": None, "file_bytes": None}
        if source_type in TEXT_MODES:
            payload["text"] = st.text_area("Paste content", height=160, key=f"{key_prefix}_text",
                                           placeholder="Paste your JSON or API response here...")
        elif source_type in FILE_MODES:
            upload = st.file_uploader("Upload file", key=f"{key_prefix}_file")
            payload["file_bytes"] = upload.getvalue() if upload else None
        return payload

    # ── Website URL wizard ───────────────────────────────────
    step = st.session_state[f"{key_prefix}_wizard_step"]

    # Step 0 — enter URL
    url = st.text_input("Enter URL", key=f"{key_prefix}_url_input",
                        placeholder="https://example.com/menu",
                        value=st.session_state.get(f"{key_prefix}_url", ""))

    if step == 0:
        if st.button("Next ➤", key=f"{key_prefix}_next_0", type="primary"):
            if not url:
                st.warning("Please enter a URL first.")
                return None
            with st.spinner("🔍 Scraping page content…"):
                try:
                    hierarchy = scrape_menu_hierarchy(url)
                except Exception as exc:
                    st.error(f"⚠️ Scraping failed: {exc}")
                    return None
            cats = list(hierarchy.get("categories", {}).keys())
            if not cats:
                st.warning("No menu categories found on this page.")
                return None
            st.session_state[f"{key_prefix}_url"] = url
            st.session_state[f"{key_prefix}_hierarchy"] = hierarchy
            st.session_state[f"{key_prefix}_categories"] = cats
            st.session_state[f"{key_prefix}_wizard_step"] = 1
            st.rerun()
        return None

    hierarchy = st.session_state.get(f"{key_prefix}_hierarchy") or {}
    cats = st.session_state.get(f"{key_prefix}_categories", [])

    # Step 1 — pick category
    if step >= 1:
        st.markdown("##### 📂 Categories found:")
        cat_options = ["All"] + cats
        selected_cat = st.selectbox("Select a category", cat_options,
                                    key=f"{key_prefix}_cat_select")
        if step == 1:
            col_back, col_next = st.columns(2)
            with col_back:
                if st.button("◀ Back", key=f"{key_prefix}_back_1"):
                    _reset_wizard(key_prefix)
                    st.rerun()
            with col_next:
                if st.button("Next ➤", key=f"{key_prefix}_next_1", type="primary"):
                    st.session_state[f"{key_prefix}_selected_cat"] = selected_cat
                    if selected_cat == "All":
                        # Gather all items from every category
                        all_items = []
                        for cat_name, cat_data in hierarchy.get("categories", {}).items():
                            all_items.extend(cat_data.get("items", []))
                            for sub_items in cat_data.get("subcategories", {}).values():
                                if isinstance(sub_items, list):
                                    all_items.extend(sub_items)
                        st.session_state[f"{key_prefix}_subcategories"] = []
                        st.session_state[f"{key_prefix}_items"] = all_items
                        st.session_state[f"{key_prefix}_wizard_step"] = 3
                    else:
                        cat_data = hierarchy.get("categories", {}).get(selected_cat, {})
                        subs = list(cat_data.get("subcategories", {}).keys())
                        st.session_state[f"{key_prefix}_subcategories"] = subs
                        if subs:
                            st.session_state[f"{key_prefix}_wizard_step"] = 2
                        else:
                            # No subcategories → go straight to items
                            items = cat_data.get("items", [])
                            st.session_state[f"{key_prefix}_items"] = items
                            st.session_state[f"{key_prefix}_wizard_step"] = 3
                    st.rerun()
            return None

    selected_cat = st.session_state.get(f"{key_prefix}_selected_cat")
    subs = st.session_state.get(f"{key_prefix}_subcategories", [])

    # Step 2 — pick subcategory
    if step >= 2 and subs:
        st.markdown("##### 📁 Subcategories:")
        selected_sub = st.selectbox("Select a subcategory", subs,
                                    key=f"{key_prefix}_sub_select")
        if step == 2:
            col_back, col_next = st.columns(2)
            with col_back:
                if st.button("◀ Back", key=f"{key_prefix}_back_2"):
                    st.session_state[f"{key_prefix}_wizard_step"] = 1
                    st.rerun()
            with col_next:
                if st.button("Next ➤", key=f"{key_prefix}_next_2", type="primary"):
                    cat_data = hierarchy.get("categories", {}).get(selected_cat, {})
                    items = cat_data.get("subcategories", {}).get(selected_sub, [])
                    st.session_state[f"{key_prefix}_selected_sub"] = selected_sub
                    st.session_state[f"{key_prefix}_items"] = items
                    st.session_state[f"{key_prefix}_wizard_step"] = 3
                    st.rerun()
            return None

    # Step 3 — show items
    if step == 3:
        items = st.session_state.get(f"{key_prefix}_items", [])
        selected_sub = st.session_state.get(f"{key_prefix}_selected_sub")
        loc_label = selected_sub if selected_sub else selected_cat
        st.markdown(f"##### 🍽️ Items in **{loc_label}** ({len(items)} found)")

        if items:
            import pandas as pd
            df = pd.DataFrame(items)
            display_cols = [c for c in ["item", "price", "description"] if c in df.columns]
            st.dataframe(df[display_cols], use_container_width=True, hide_index=True)
        else:
            st.info("No items found in this selection.")

        if st.button("◀ Back", key=f"{key_prefix}_back_3"):
            if subs:
                st.session_state[f"{key_prefix}_wizard_step"] = 2
            else:
                st.session_state[f"{key_prefix}_wizard_step"] = 1
            st.rerun()

        # Return a payload so comparison can proceed
        return {
            "source_type": "Website URL",
            "text": None,
            "url": st.session_state.get(f"{key_prefix}_url"),
            "file_bytes": None,
            "_scraped_items": items,
        }

    return None


def load_menu(payload):
    # If items were already scraped via the wizard, return them directly
    if payload.get("_scraped_items") is not None:
        return payload["_scraped_items"]
    source_type = payload["source_type"]
    return extract_menu_from_source(
        source_type=source_type,
        file_bytes=payload.get("file_bytes"),
        text=payload.get("text"),
        url=payload.get("url"),
    )


def show_issue_section(title, rows):
    if not rows:
        st.success(f"✅ No {title.lower()} found — looking good!")
        return

    # Paginate
    page_size = 10
    total_pages = max(1, -(-len(rows) // page_size))
    page_key = f"issue_page_{title.replace(' ', '_')}"
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1,
                           step=1, key=page_key)
    start = (page - 1) * page_size
    end = start + page_size
    st.caption(f"Showing {start + 1}–{min(end, len(rows))} of {len(rows)}  ·  Page {page} of {total_pages}")
    st.dataframe(rows[start:end], use_container_width=True)


ISSUE_ICONS = {
    "Matched Items": "🔗",
    "Missing Items": "🔍",
    "Extra Items": "➕",
    "Price Mismatches": "💰",
    "Description Mismatches": "📝",
    "Spelling Errors": "🔤",
    "Missing Images": "🖼️",
    "Category Mismatches": "📂",
}


def _diff_badge(is_same, label_same="SAME", label_diff="DIFFERENT"):
    if is_same:
        return f'<span style="background:#D1FAE5;color:#065F46;padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;">✅ {label_same}</span>'
    return f'<span style="background:#FEE2E2;color:#991B1B;padding:2px 8px;border-radius:4px;font-size:0.7rem;font-weight:700;">❌ {label_diff}</span>'


ITEMS_PER_PAGE = 10


def _render_matched_items_table(matched_items):
    """Render rich matched items cards showing all differences like the terminal output."""
    if not matched_items:
        st.info("No items matched between the two menus.")
        return

    # Summary bar
    perfect = sum(1 for m in matched_items if m.get("is_perfect_match"))
    with_diffs = len(matched_items) - perfect
    st.markdown(f"**{len(matched_items)}** matched items — **{perfect}** perfect, **{with_diffs}** with differences")

    # Filter option
    show_filter = st.radio("Show:", ["All", "With Differences Only", "Perfect Only"],
                           horizontal=True, key="matched_filter")

    filtered = matched_items
    if show_filter == "With Differences Only":
        filtered = [m for m in matched_items if not m.get("is_perfect_match")]
    elif show_filter == "Perfect Only":
        filtered = [m for m in matched_items if m.get("is_perfect_match")]

    if not filtered:
        st.info("No items match the selected filter.")
        return

    # Pagination
    total_pages = max(1, -(-len(filtered) // ITEMS_PER_PAGE))  # ceil division
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1,
                           step=1, key="matched_page")
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_items = filtered[start_idx:end_idx]

    st.caption(f"Showing {start_idx + 1}–{min(end_idx, len(filtered))} of {len(filtered)} items  ·  Page {page} of {total_pages}")

    for m in page_items:
        diffs = m.get("differences", [])
        is_perfect = m.get("is_perfect_match", False)
        score = m.get("score", 0)

        border_color = "#10B981" if is_perfect else "#F59E0B"
        header_bg = "#D1FAE5" if is_perfect else "#FEF3C7"
        header_fg = "#065F46" if is_perfect else "#92400E"
        status_text = "✅ Perfect Match" if is_perfect else f"⚠️ {len(diffs)} difference(s): {', '.join(diffs)}"

        price_same = str(m.get("our_price", "")).strip() == str(m.get("reference_price", "")).strip()
        cat_same = str(m.get("our_category", "")).strip().lower() == str(m.get("reference_category", "")).strip().lower()
        desc_same = str(m.get("our_description", "")).strip().lower() == str(m.get("reference_description", "")).strip().lower()
        name_same = str(m.get("our_item", "")).strip().lower() == str(m.get("reference_item", "")).strip().lower()

        html = f'''
        <div style="border:2px solid {border_color}; border-radius:10px; margin-bottom:12px; overflow:hidden; font-size:0.82rem;">
            <div style="background:{header_bg}; color:{header_fg}; padding:8px 14px; font-weight:700;">
                🔗 {m.get("our_item","")} &nbsp;↔&nbsp; {m.get("reference_item","")}
                &nbsp;&nbsp; <span style="font-size:0.75rem; font-weight:400;">Match: {score:.0f}%</span>
                &nbsp;&nbsp; {status_text}
            </div>
            <table style="width:100%; border-collapse:collapse;">
                <thead><tr style="background:#F3F4F6;">
                    <th style="padding:6px 12px; text-align:left; width:15%;">Field</th>
                    <th style="padding:6px 12px; text-align:left; width:35%;">Our Menu</th>
                    <th style="padding:6px 12px; text-align:left; width:35%;">Reference Menu</th>
                    <th style="padding:6px 12px; text-align:center; width:15%;">Status</th>
                </tr></thead><tbody>
                <tr style="border-bottom:1px solid #E5E7EB;">
                    <td style="padding:6px 12px; font-weight:600;">Name</td>
                    <td style="padding:6px 12px;">{m.get("our_item","")}</td>
                    <td style="padding:6px 12px;">{m.get("reference_item","")}</td>
                    <td style="padding:6px 12px; text-align:center;">{_diff_badge(name_same)}</td>
                </tr>
                <tr style="border-bottom:1px solid #E5E7EB; {"background:#FEF3C7;" if not price_same else ""}">
                    <td style="padding:6px 12px; font-weight:600;">💰 Price</td>
                    <td style="padding:6px 12px; {"font-weight:700;" if not price_same else ""}">{"$"+str(m.get("our_price","")) if m.get("our_price") else "—"}</td>
                    <td style="padding:6px 12px; {"font-weight:700;" if not price_same else ""}">{"$"+str(m.get("reference_price","")) if m.get("reference_price") else "—"}</td>
                    <td style="padding:6px 12px; text-align:center;">{_diff_badge(price_same)}</td>
                </tr>
                <tr style="border-bottom:1px solid #E5E7EB; {"background:#F3E8FF;" if not cat_same else ""}">
                    <td style="padding:6px 12px; font-weight:600;">📂 Category</td>
                    <td style="padding:6px 12px;">{m.get("our_category","")}</td>
                    <td style="padding:6px 12px;">{m.get("reference_category","")}</td>
                    <td style="padding:6px 12px; text-align:center;">{_diff_badge(cat_same)}</td>
                </tr>
                <tr style="{"background:#E0E7FF;" if not desc_same else ""}">
                    <td style="padding:6px 12px; font-weight:600;">📝 Description</td>
                    <td style="padding:6px 12px;">{(m.get("our_description","") or "—")[:120]}</td>
                    <td style="padding:6px 12px;">{(m.get("reference_description","") or "—")[:120]}</td>
                    <td style="padding:6px 12px; text-align:center;">{_diff_badge(desc_same)}</td>
                </tr>
                </tbody>
            </table>
        </div>'''
        st.markdown(html, unsafe_allow_html=True)


def show_issue_tabs(report):
    tab_specs = [
        ("Matched Items", report.get("matched_items", [])),
        ("Missing Items", report["missing_items"]),
        ("Extra Items", report["extra_items"]),
        ("Price Mismatches", report["price_mismatches"]),
        ("Description Mismatches", report["description_mismatches"]),
        ("Spelling Errors", report["spelling_errors"]),
        ("Missing Images", report["missing_images"]),
        ("Category Mismatches", report["category_mismatches"]),
    ]
    tab_labels = [f"{ISSUE_ICONS.get(t, '')} {t} ({len(r)})" for t, r in tab_specs]
    tabs = st.tabs(tab_labels)
    for tab, (title, rows) in zip(tabs, tab_specs):
        with tab:
            if title == "Matched Items":
                _render_matched_items_table(rows)
            else:
                show_issue_section(title, rows)


METRIC_ICONS = {
    "missing_items": "🔍",
    "extra_items": "➕",
    "price_mismatches": "💰",
    "description_mismatches": "📝",
    "spelling_errors": "🔤",
}


def _flatten_hierarchy(hierarchy: dict) -> list[dict]:
    """Flatten a scrape_menu_hierarchy result into a list of item dicts."""
    items = []
    for cat_name, cat_data in hierarchy.get("categories", {}).items():
        for item in cat_data.get("items", []):
            # Ensure category is set
            if not item.get("category"):
                item["category"] = cat_name
            items.append(item)
        for sub_name, sub_items in cat_data.get("subcategories", {}).items():
            if isinstance(sub_items, list):
                for item in sub_items:
                    if not item.get("category"):
                        item["category"] = f"{cat_name} > {sub_name}"
                    items.append(item)
    return items


def _run_comparison(comp_id: str):
    """Execute the full comparison pipeline and persist results to DB."""
    comp = get_comparison(comp_id)
    if not comp:
        return

    update_comparison(comp_id, status="Processing")

    url_our = comp["url_our"]
    url_reference = comp["url_reference"]

    # Use scrape_menu_hierarchy for website URLs — it handles Playwright,
    # RSC parsing, card-based layouts, and all extraction strategies properly.
    our_hierarchy = scrape_menu_hierarchy(url_our)
    our_raw = _flatten_hierarchy(our_hierarchy)
    print(f"[comparison] Our menu: {len(our_raw)} items from {len(our_hierarchy.get('categories', {}))} categories", flush=True)

    ref_hierarchy = scrape_menu_hierarchy(url_reference)
    ref_raw = _flatten_hierarchy(ref_hierarchy)
    print(f"[comparison] Ref menu: {len(ref_raw)} items from {len(ref_hierarchy.get('categories', {}))} categories", flush=True)

    our_norm = normalize_menu(our_raw)
    ref_norm = normalize_menu(ref_raw)
    report = compare_menus(our_norm, ref_norm)
    pdf_bytes = build_pdf_bytes(report)

    save_report(comp_id, report, pdf_bytes, our_raw, ref_raw, our_norm, ref_norm)


# ── Highlighter Report helpers ───────────────────────────────────────

_HIGHLIGHT_COLORS = {
    "missing_items":            ("#FECACA", "#991B1B", "Missing Item"),
    "extra_items":              ("#DBEAFE", "#1E40AF", "Extra Item"),
    "price_mismatches":         ("#FEF3C7", "#92400E", "Price Mismatch"),
    "description_mismatches":   ("#E0E7FF", "#3730A3", "Description Mismatch"),
    "category_mismatches":      ("#F3E8FF", "#6B21A8", "Category Mismatch"),
    "spelling_errors":          ("#CCFBF1", "#065F46", "Spelling Error"),
}


def _build_highlight_rows(report: dict, filters: dict[str, bool]) -> list[dict]:
    """Build a flat list of highlighted difference rows based on active filters."""
    rows = []
    if filters.get("missing_items"):
        for it in report.get("missing_items", []):
            rows.append({
                "Type": "Missing Item",
                "Item": it.get("item", ""),
                "Matched With": "—",
                "Category": it.get("category", ""),
                "Our Value": "—",
                "Expected Value": it.get("item", ""),
                "Reason": "Item exists in reference but not found in our menu",
            })
    if filters.get("extra_items"):
        for it in report.get("extra_items", []):
            rows.append({
                "Type": "Extra Item",
                "Item": it.get("item", ""),
                "Matched With": "—",
                "Category": it.get("category", ""),
                "Our Value": it.get("item", ""),
                "Expected Value": "—",
                "Reason": "Item exists in our menu but not in reference",
            })
    if filters.get("price_mismatches"):
        for it in report.get("price_mismatches", []):
            try:
                diff = abs(float(it.get('our_price', 0)) - float(it.get('reference_price', 0)))
                diff_str = f"${diff:.2f}"
            except (ValueError, TypeError):
                diff_str = "N/A"
            rows.append({
                "Type": "Price Mismatch",
                "Item": it.get("our_item", it.get("item", "")),
                "Matched With": it.get("item", ""),
                "Category": "",
                "Our Value": f"${it.get('our_price', '')}",
                "Expected Value": f"${it.get('reference_price', '')}",
                "Reason": it.get("reason", f"Price differs by {diff_str}"),
            })
    if filters.get("description_mismatches"):
        for it in report.get("description_mismatches", []):
            rows.append({
                "Type": "Description Mismatch",
                "Item": it.get("our_item", it.get("item", "")),
                "Matched With": it.get("item", ""),
                "Category": "",
                "Our Value": (it.get("our_description") or "")[:80],
                "Expected Value": (it.get("reference_description") or "")[:80],
                "Reason": it.get("reason", "Description text differs"),
            })
    if filters.get("category_mismatches"):
        for it in report.get("category_mismatches", []):
            rows.append({
                "Type": "Category Mismatch",
                "Item": it.get("our_item", it.get("item", "")),
                "Matched With": it.get("item", ""),
                "Category": "",
                "Our Value": it.get("our_category", ""),
                "Expected Value": it.get("reference_category", ""),
                "Reason": it.get("reason", "Item is in a different category"),
            })
    if filters.get("spelling_errors"):
        for it in report.get("spelling_errors", []):
            rows.append({
                "Type": "Spelling Error",
                "Item": it.get("our_item", it.get("item", "")),
                "Matched With": it.get("item", ""),
                "Category": "",
                "Our Value": it.get("our", ""),
                "Expected Value": it.get("reference", ""),
                "Reason": f"Spelling difference in {it.get('field', 'text')}",
            })
    return rows


def _render_highlighted_table(rows: list[dict]):
    """Render the highlighted differences table with colored rows."""
    if not rows:
        st.success("✅ No differences found for the selected filters.")
        return

    # Summary counts by type
    type_counts = {}
    for r in rows:
        t = r.get("Type", "")
        type_counts[t] = type_counts.get(t, 0) + 1
    summary_parts = [f"**{count}** {typ}" for typ, count in type_counts.items()]
    st.markdown(f"Showing **{len(rows)}** differences: " + " · ".join(summary_parts))

    # Pagination
    total_pages = max(1, -(-len(rows) // ITEMS_PER_PAGE))
    page = st.number_input("Page", min_value=1, max_value=total_pages, value=1,
                           step=1, key="highlight_page")
    start_idx = (page - 1) * ITEMS_PER_PAGE
    end_idx = start_idx + ITEMS_PER_PAGE
    page_rows = rows[start_idx:end_idx]
    st.caption(f"Showing {start_idx + 1}–{min(end_idx, len(rows))} of {len(rows)}  ·  Page {page} of {total_pages}")

    cols = ["Type", "Item", "Matched With", "Our Value", "Expected Value", "Reason"]
    html = '<table style="width:100%; border-collapse:collapse; font-size:0.82rem;">'
    html += '<thead><tr style="background:#1a1a2e; color:white;">'
    for col in cols:
        html += f'<th style="padding:10px 12px; text-align:left;">{col}</th>'
    html += '</tr></thead><tbody>'

    for row in page_rows:
        bg, fg, _ = _HIGHLIGHT_COLORS.get(
            next((k for k, v in _HIGHLIGHT_COLORS.items() if v[2] == row["Type"]), ""),
            ("#FFF", "#000", "")
        )
        html += f'<tr style="background:{bg}; color:{fg}; border-bottom:1px solid #e5e7eb;">'
        for col in cols:
            val = row.get(col, "")
            if col == "Expected Value" and val and val != "—":
                html += f'<td style="padding:8px 12px; font-weight:700;">{val}</td>'
            elif col == "Our Value":
                html += f'<td style="padding:8px 12px; text-decoration:line-through; opacity:0.8;">{val}</td>'
            else:
                html += f'<td style="padding:8px 12px;">{val}</td>'
        html += '</tr>'

    html += '</tbody></table>'
    st.markdown(html, unsafe_allow_html=True)


# ── Tab: Comparison ──────────────────────────────────────────────────

def render_comparison_tab():
    """Main comparison tab — add new comparison + run processing."""

    # ── Add Comparison dialog ────────────────────────────────
    col_title, col_add = st.columns([4, 1])
    with col_title:
        st.markdown("""
        <div class="section-header"><h3>📊 Menu Comparisons</h3></div>
        """, unsafe_allow_html=True)
    with col_add:
        st.markdown("")
        add_clicked = st.button("➕ Add Comparison", type="primary", use_container_width=True)

    if add_clicked:
        st.session_state["show_add_dialog"] = True

    if st.session_state.get("show_add_dialog"):
        with st.container(border=True):
            st.markdown("##### ✏️ New Comparison")
            c_title = st.text_input("Title", placeholder="e.g. New Thai vs DoorDash", key="new_comp_title")
            c1, c2 = st.columns(2)
            with c1:
                c_url1 = st.text_input("Our Menu URL", placeholder="https://...", key="new_comp_url1")
            with c2:
                c_url2 = st.text_input("Reference Menu URL", placeholder="https://...", key="new_comp_url2")

            btn_c1, btn_c2, _ = st.columns([1, 1, 3])
            with btn_c1:
                if st.button("Save & Process", type="primary", key="save_comp"):
                    if not c_title or not c_url1 or not c_url2:
                        st.warning("Please fill in all fields.")
                    else:
                        comp_id = create_comparison(c_title, c_url1, c_url2)
                        st.session_state["show_add_dialog"] = False
                        st.session_state["processing_id"] = comp_id
                        st.rerun()
            with btn_c2:
                if st.button("Cancel", key="cancel_comp"):
                    st.session_state["show_add_dialog"] = False
                    st.rerun()

    # ── Process if needed ────────────────────────────────────
    if st.session_state.get("processing_id"):
        comp_id = st.session_state.pop("processing_id")
        progress = st.progress(0, text="🔄 Starting comparison...")
        try:
            progress.progress(10, text="📋 Extracting menus...")
            _run_comparison(comp_id)
            progress.progress(100, text="✅ Comparison complete!")
            time.sleep(0.5)
        except Exception as exc:
            import traceback
            traceback.print_exc()
            update_comparison(comp_id, status="Failed")
            progress.empty()
            st.error(f"⚠️ Processing failed: {exc}")
            return
        progress.empty()
        st.rerun()

    # ── Data Grid ────────────────────────────────────────────
    comparisons = list_comparisons()
    if not comparisons:
        st.info("No comparisons yet. Click **➕ Add Comparison** to get started.")
        return

    grid_data = []
    for c in comparisons:
        grid_data.append({
            "ID": c["id"],
            "Title": c["title"],
            "Our URL": c["url_our"][:50] + ("..." if len(c["url_our"]) > 50 else ""),
            "Reference URL": c["url_reference"][:50] + ("..." if len(c["url_reference"]) > 50 else ""),
            "Status": c["status"],
            "Date": c["created_at"][:19].replace("T", " "),
        })

    df = pd.DataFrame(grid_data)

    # Status styling
    st.dataframe(
        df,
        use_container_width=True,
        hide_index=True,
        column_config={
            "ID": st.column_config.TextColumn("ID", width="small"),
            "Title": st.column_config.TextColumn("Title", width="medium"),
            "Status": st.column_config.TextColumn("Status", width="small"),
            "Date": st.column_config.TextColumn("Date", width="medium"),
        },
    )

    # ── Actions per comparison ───────────────────────────────
    st.markdown("##### ⚡ Actions")
    sel_id = st.selectbox("Select comparison", [c["id"] for c in comparisons],
                          format_func=lambda x: next(
                              (c["title"] for c in comparisons if c["id"] == x), x),
                          key="action_select")

    act_cols = st.columns(4)
    with act_cols[0]:
        if st.button("📄 View Report", key="view_report_btn"):
            st.session_state["view_report_id"] = sel_id
            st.rerun()
    with act_cols[1]:
        if st.button("🔄 Re-process", key="reprocess_btn"):
            st.session_state["processing_id"] = sel_id
            update_comparison(sel_id, status="Pending")
            st.rerun()
    with act_cols[2]:
        if st.button("🗑️ Delete", key="delete_btn"):
            delete_comparison(sel_id)
            st.rerun()


# ── Tab: Reports ─────────────────────────────────────────────────────

def render_reports_tab():
    """Reports tab — view detailed comparison reports with highlighting."""
    comparisons = list_comparisons()
    completed = [c for c in comparisons if c["status"] == "Completed"]

    if not completed:
        st.info("No completed comparisons yet. Run a comparison first.")
        return

    sel_id = st.selectbox(
        "Select a report to view",
        [c["id"] for c in completed],
        format_func=lambda x: next(
            (f"{c['title']} — {c['created_at'][:10]}" for c in completed if c["id"] == x), x),
        key="report_select",
    )

    report, pdf_bytes = load_report(sel_id)
    if not report or not report.get("summary"):
        st.warning("Report data not available. Try re-processing this comparison.")
        return

    comp = get_comparison(sel_id)

    # ── Report header ────────────────────────────────────────
    st.markdown(f"""
    <div class="source-card" style="margin-bottom:1rem;">
        <div class="source-card-title">📑 {comp['title']}</div>
        <div class="source-card-desc">
            <strong>Our:</strong> {comp['url_our'][:80]}<br>
            <strong>Ref:</strong> {comp['url_reference'][:80]}
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Report sub-tabs ──────────────────────────────────────
    report_tab1, report_tab2 = st.tabs(["📋 Standard Report", "🎨 Highlighter Report"])

    with report_tab1:
        # Stats banner
        metrics = report["summary"]
        metric_keys = ["missing_items", "extra_items", "price_mismatches",
                       "description_mismatches", "spelling_errors", "category_mismatches"]
        total = sum(metrics.get(k, 0) for k in metric_keys)
        matched = metrics.get("matched_total", 0)
        perfect = metrics.get("perfect_matches", 0)
        with_diffs = metrics.get("items_with_differences", 0)

        st.markdown(f"""
        <div class="stats-banner">
            <div class="stat-item"><div class="stat-value">{matched}</div><div class="stat-label">Matched</div></div>
            <div class="stat-item"><div class="stat-value">{perfect}</div><div class="stat-label">Perfect</div></div>
            <div class="stat-item"><div class="stat-value">{with_diffs}</div><div class="stat-label">With Diffs</div></div>
            <div class="stat-item"><div class="stat-value">{metrics.get('missing_items', 0)}</div><div class="stat-label">Missing</div></div>
            <div class="stat-item"><div class="stat-value">{metrics.get('extra_items', 0)}</div><div class="stat-label">Extra</div></div>
            <div class="stat-item"><div class="stat-value">{total}</div><div class="stat-label">Total Issues</div></div>
            <div class="stat-item"><div class="stat-value">{'PASS' if total == 0 else 'REVIEW'}</div><div class="stat-label">Status</div></div>
        </div>
        """, unsafe_allow_html=True)

        if total == 0:
            st.markdown('<div class="result-pass">🎉 Perfect Match! All items matched with no differences.</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="result-fail">⚠️ {total} issue(s) detected across {with_diffs} items</div>', unsafe_allow_html=True)

        # Download button at top
        if pdf_bytes:
            st.download_button(
                "📥 Download PDF Report", data=pdf_bytes,
                file_name=f"report_{comp['title'].replace(' ', '_')}.pdf",
                mime="application/pdf", use_container_width=True,
            )

        show_issue_tabs(report)

        with st.expander("📄 Raw JSON Report", expanded=False):
            st.code(json.dumps(report, indent=2), language="json")

    with report_tab2:
        st.markdown("##### 🎨 Highlighter Report — Toggle categories to filter")

        # Filter checkboxes
        fcols = st.columns(6)
        filters = {}
        labels = [
            ("missing_items", "🔍 Missing"),
            ("extra_items", "➕ Extra"),
            ("price_mismatches", "💰 Price"),
            ("description_mismatches", "📝 Description"),
            ("category_mismatches", "📂 Category"),
            ("spelling_errors", "🔤 Spelling"),
        ]
        for col, (key, label) in zip(fcols, labels):
            with col:
                count = len(report.get(key, []))
                filters[key] = st.checkbox(f"{label} ({count})", value=True, key=f"hl_{sel_id}_{key}")

        # Color legend
        legend_html = '<div style="display:flex; gap:12px; flex-wrap:wrap; margin:8px 0 16px 0;">'
        for key, (bg, fg, label) in _HIGHLIGHT_COLORS.items():
            if filters.get(key):
                legend_html += f'<span style="background:{bg}; color:{fg}; padding:3px 10px; border-radius:6px; font-size:0.75rem; font-weight:600;">{label}</span>'
        legend_html += '</div>'
        st.markdown(legend_html, unsafe_allow_html=True)

        # Build and render table
        rows = _build_highlight_rows(report, filters)
        _render_highlighted_table(rows)


# ── Main ─────────────────────────────────────────────────────────────

def main():
    st.set_page_config(
        page_title="Boons · AI Menu Verifier",
        page_icon="🍽️",
        layout="wide",
        initial_sidebar_state="auto",
    )

    inject_custom_css()
    render_sidebar()
    render_header()

    # ── Check if we should jump to a report ──────────────────
    view_id = st.session_state.pop("view_report_id", None)

    # ── Main Tabs ────────────────────────────────────────────
    tab_comparison, tab_reports = st.tabs(["📊 Comparisons", "📑 Reports"])

    with tab_comparison:
        render_comparison_tab()

    with tab_reports:
        if view_id:
            # Pre-select the report
            st.session_state["report_select"] = view_id
        render_reports_tab()

    # ── Footer ───────────────────────────────────────────────
    st.markdown("""
    <div class="app-footer">
        <p class="app-footer-text">
            Built with ❤️ by <span class="app-footer-brand">Boons</span> ·
            AI-Powered Menu Verification System · v3.0
        </p>
        <p class="app-footer-text" style="font-size:0.7rem; margin-top:4px;">
            🔒 Data stored locally in SQLite · Never sent to external servers
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
