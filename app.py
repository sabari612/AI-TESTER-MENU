import json
import base64

import streamlit as st

from comparator.menu_comparator import compare_menus
from extractor.factory import extract_menu_from_source
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


def collect_source(label, modes, key_prefix, icon="📄", desc=""):
    """Collect menu source input inside a styled card."""
    st.markdown(f"""
    <div class="source-card">
        <div class="source-card-title">{icon} {label}</div>
        <div class="source-card-desc">{desc}</div>
    </div>
    """, unsafe_allow_html=True)
    source_type = st.selectbox("Source Type", modes, key=f"{key_prefix}_type", label_visibility="collapsed")
    payload = {"source_type": source_type, "text": None, "url": None, "file_bytes": None}
    if source_type in TEXT_MODES:
        payload["text"] = st.text_area("Paste content", height=160, key=f"{key_prefix}_text",
                                       placeholder="Paste your JSON or API response here...")
    elif source_type == "Website URL":
        payload["url"] = st.text_input("Enter URL", key=f"{key_prefix}_url",
                                       placeholder="https://example.com/menu")
    elif source_type in FILE_MODES:
        upload = st.file_uploader("Upload file", key=f"{key_prefix}_file")
        payload["file_bytes"] = upload.getvalue() if upload else None
    return payload


def load_menu(payload):
    source_type = payload["source_type"]
    return extract_menu_from_source(
        source_type=source_type,
        file_bytes=payload.get("file_bytes"),
        text=payload.get("text"),
        url=payload.get("url"),
    )


def show_issue_section(title, rows):
    if rows:
        st.dataframe(rows, use_container_width=True)
    else:
        st.success(f"✅ No {title.lower()} found — looking good!")


ISSUE_ICONS = {
    "Missing Items": "🔍",
    "Extra Items": "➕",
    "Price Mismatches": "💰",
    "Description Mismatches": "📝",
    "Spelling Errors": "🔤",
    "Missing Images": "🖼️",
    "Category Mismatches": "📂",
}


def show_issue_tabs(report):
    tab_specs = [
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
            show_issue_section(title, rows)


METRIC_ICONS = {
    "missing_items": "🔍",
    "extra_items": "➕",
    "price_mismatches": "💰",
    "description_mismatches": "📝",
    "spelling_errors": "🔤",
}


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
    render_steps()

    # ── Source Inputs ────────────────────────────────────────
    st.markdown("""
    <div class="section-header">
        <h3>📤 Upload Your Menus</h3>
    </div>
    """, unsafe_allow_html=True)

    left, right = st.columns(2, gap="large")
    with left:
        our_payload = collect_source(
            "Our Menu",
            ["JSON Text", "JSON File", "API Response Text", "Website URL"],
            "our",
            icon="📋",
            desc="Your current restaurant menu data",
        )
    with right:
        reference_payload = collect_source(
            "Reference Menu",
            ["PDF", "Image", "Word Document", "Website URL", "JSON File"],
            "reference",
            icon="📑",
            desc="The reference menu to compare against",
        )

    # ── Compare Button ───────────────────────────────────────
    st.markdown("")
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
    with btn_col2:
        compare_clicked = st.button("🚀  Compare Menus", type="primary", use_container_width=True)

    if compare_clicked:
        # ── Progress bar ─────────────────────────────────────
        progress_bar = st.progress(0, text="🔄 Loading menus...")
        try:
            progress_bar.progress(15, text="📋 Extracting our menu...")
            our_raw = load_menu(our_payload)
            progress_bar.progress(35, text="📑 Extracting reference menu...")
            reference_raw = load_menu(reference_payload)
            progress_bar.progress(55, text="⚙️ Normalizing menus...")
            our_normalized = normalize_menu(our_raw)
            reference_normalized = normalize_menu(reference_raw)
            progress_bar.progress(75, text="🔍 Comparing menus...")
            report = compare_menus(our_normalized, reference_normalized)
            progress_bar.progress(90, text="📄 Generating report...")
            pdf_bytes = build_pdf_bytes(report)
            progress_bar.progress(100, text="✅ Analysis complete!")
        except Exception as exc:  # pragma: no cover
            progress_bar.empty()
            st.error(f"⚠️ {exc}")
            return

        import time
        time.sleep(0.5)
        progress_bar.empty()

        # ── Divider ──────────────────────────────────────────
        st.markdown('<div class="orange-divider"></div>', unsafe_allow_html=True)

        # ── Stats Banner ────────────────────────────────────
        metrics = report["summary"]
        metric_keys = ["missing_items", "extra_items", "price_mismatches",
                       "description_mismatches", "spelling_errors"]
        total = sum(metrics.get(k, 0) for k in metric_keys)

        st.markdown(f"""
        <div class="stats-banner">
            <div class="stat-item">
                <div class="stat-value">{total}</div>
                <div class="stat-label">Total Issues</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{metrics.get('missing_items', 0)}</div>
                <div class="stat-label">Missing</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{metrics.get('extra_items', 0)}</div>
                <div class="stat-label">Extra</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{metrics.get('price_mismatches', 0)}</div>
                <div class="stat-label">Price Issues</div>
            </div>
            <div class="stat-item">
                <div class="stat-value">{'PASS' if total == 0 else 'REVIEW'}</div>
                <div class="stat-label">Status</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # ── Result Banner ────────────────────────────────────
        if total == 0:
            st.markdown("""
            <div class="result-pass">
                🎉 Perfect Match! No issues found between the menus.
            </div>
            """, unsafe_allow_html=True)
        else:
            st.markdown(f"""
            <div class="result-fail">
                ⚠️ {total} issue(s) detected — review details below
            </div>
            """, unsafe_allow_html=True)

        # ── Summary Metrics ──────────────────────────────────
        st.markdown("""
        <div class="section-header">
            <h3>📊 Detailed Breakdown</h3>
        </div>
        """, unsafe_allow_html=True)

        metric_cols = st.columns(5, gap="medium")
        for col, key in zip(metric_cols, metric_keys):
            icon = METRIC_ICONS.get(key, "")
            label = f"{icon} {key.replace('_', ' ').title()}"
            col.metric(label, metrics[key])

        # ── Normalized Menu Preview ──────────────────────────
        with st.expander("🔎 Normalized Menu Preview", expanded=False):
            prev_left, prev_right = st.columns(2)
            with prev_left:
                st.markdown("##### 📋 Our Menu")
                st.json(our_normalized)
            with prev_right:
                st.markdown("##### 📑 Reference Menu")
                st.json(reference_normalized)

        # ── Issue Details ────────────────────────────────────
        st.markdown("""
        <div class="section-header">
            <h3>🔎 Issue Details</h3>
        </div>
        """, unsafe_allow_html=True)
        show_issue_tabs(report)

        # ── Downloads ────────────────────────────────────────
        st.markdown('<div class="orange-divider"></div>', unsafe_allow_html=True)

        st.markdown("""
        <div class="section-header">
            <h3>📥 Export Results</h3>
        </div>
        """, unsafe_allow_html=True)

        dl_col1, dl_col2, dl_col3 = st.columns([1, 2, 1])
        with dl_col2:
            st.download_button(
                "📥  Download PDF Report",
                data=pdf_bytes,
                file_name="menu_verification_report.pdf",
                mime="application/pdf",
                use_container_width=True,
            )

        # ── JSON Report ──────────────────────────────────────
        with st.expander("📄 Raw JSON Report", expanded=False):
            st.code(json.dumps(report, indent=2), language="json")

    # ── Footer ───────────────────────────────────────────────
    st.markdown("""
    <div class="app-footer">
        <p class="app-footer-text">
            Built with ❤️ by <span class="app-footer-brand">Boons</span> ·
            AI-Powered Menu Verification System · v2.0
        </p>
        <p class="app-footer-text" style="font-size:0.7rem; margin-top:4px;">
            🔒 Your data is processed securely and never stored
        </p>
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
