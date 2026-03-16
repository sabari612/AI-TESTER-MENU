import json
import base64

import streamlit as st

from comparator.menu_comparator import compare_menus
from extractor.factory import extract_menu_from_source
from processing.normalize_menu import normalize_menu
from reports.pdf_report import build_pdf_bytes

TEXT_MODES = {"JSON Text", "API Response Text"}
FILE_MODES = {"JSON File", "PDF", "Image", "Word Document"}

# ── Boons logo (inline SVG base64) ──────────────────────────────────────────
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


def inject_custom_css():
    """Inject modern CSS theme with Boons orange branding."""
    st.markdown("""
    <style>
    /* ── Global ─────────────────────────────────────────── */
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');

    .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }
    .block-container {
        padding-top: 1rem !important;
        max-width: 1200px;
    }

    /* ── Hide default Streamlit header/footer ────────────── */
    #MainMenu {visibility: hidden;}
    header {visibility: hidden;}
    footer {visibility: hidden;}

    /* ── Header / Hero ───────────────────────────────────── */
    .hero-container {
        background: linear-gradient(135deg, #FFF7F0 0%, #FFF0E5 50%, #FFE8D6 100%);
        border-radius: 16px;
        padding: 2rem 2.5rem;
        margin-bottom: 2rem;
        border: 1px solid #FFD4B0;
        box-shadow: 0 4px 24px rgba(255,107,0,0.08);
    }
    .hero-logo {
        width: 160px;
        margin-bottom: 0.25rem;
    }
    .hero-title {
        font-size: 1.6rem;
        font-weight: 700;
        color: #1a1a2e;
        margin: 0.25rem 0 0.15rem 0;
        letter-spacing: -0.5px;
    }
    .hero-subtitle {
        font-size: 0.95rem;
        color: #6B7280;
        margin: 0;
        font-weight: 400;
        line-height: 1.5;
    }
    .hero-badge {
        display: inline-block;
        background: linear-gradient(135deg, #FF6B00, #F05A28);
        color: white;
        padding: 4px 14px;
        border-radius: 20px;
        font-size: 0.75rem;
        font-weight: 600;
        letter-spacing: 0.5px;
        margin-top: 0.5rem;
    }

    /* ── Source Cards ────────────────────────────────────── */
    .source-card {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 14px;
        padding: 1.5rem;
        box-shadow: 0 2px 12px rgba(0,0,0,0.04);
        transition: box-shadow 0.2s ease;
    }
    .source-card:hover {
        box-shadow: 0 4px 20px rgba(0,0,0,0.08);
    }
    .source-card-title {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1a1a2e;
        margin-bottom: 0.25rem;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .source-card-desc {
        font-size: 0.82rem;
        color: #9CA3AF;
        margin-bottom: 1rem;
    }

    /* ── Metric Cards ────────────────────────────────────── */
    div[data-testid="stMetric"] {
        background: #FFFFFF;
        border: 1px solid #E5E7EB;
        border-radius: 12px;
        padding: 1rem 1.25rem;
        box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    }
    div[data-testid="stMetric"] label {
        color: #6B7280 !important;
        font-weight: 500 !important;
        font-size: 0.8rem !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    div[data-testid="stMetric"] div[data-testid="stMetricValue"] {
        font-size: 2rem !important;
        font-weight: 800 !important;
        color: #1a1a2e !important;
    }

    /* ── Buttons ─────────────────────────────────────────── */
    .stButton > button[kind="primary"],
    .stButton > button[data-testid="stBaseButton-primary"] {
        background: linear-gradient(135deg, #FF6B00 0%, #F05A28 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.65rem 2.5rem !important;
        font-weight: 700 !important;
        font-size: 1rem !important;
        letter-spacing: 0.3px;
        box-shadow: 0 4px 14px rgba(240,90,40,0.3) !important;
        transition: all 0.2s ease !important;
    }
    .stButton > button[kind="primary"]:hover,
    .stButton > button[data-testid="stBaseButton-primary"]:hover {
        box-shadow: 0 6px 20px rgba(240,90,40,0.4) !important;
        transform: translateY(-1px);
    }

    .stDownloadButton > button {
        background: linear-gradient(135deg, #FF6B00 0%, #F05A28 100%) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        padding: 0.6rem 2rem !important;
        font-weight: 600 !important;
        box-shadow: 0 4px 14px rgba(240,90,40,0.25) !important;
    }

    /* ── Tabs ────────────────────────────────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background: #F9FAFB;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        padding: 8px 16px;
        font-weight: 500;
        font-size: 0.85rem;
    }
    .stTabs [aria-selected="true"] {
        background: #FF6B00 !important;
        color: white !important;
        border-radius: 8px;
    }

    /* ── Expander ────────────────────────────────────────── */
    .streamlit-expanderHeader {
        font-weight: 600;
        color: #374151;
        font-size: 0.95rem;
    }

    /* ── Section Headers ─────────────────────────────────── */
    .section-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin: 1.5rem 0 1rem 0;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #FFE0C2;
    }
    .section-header h3 {
        margin: 0;
        font-size: 1.15rem;
        font-weight: 700;
        color: #1a1a2e;
    }

    /* ── Divider ─────────────────────────────────────────── */
    .orange-divider {
        height: 3px;
        background: linear-gradient(90deg, #FF6B00, #FFB347, transparent);
        border: none;
        border-radius: 2px;
        margin: 1.5rem 0;
    }

    /* ── Dataframe ───────────────────────────────────────── */
    .stDataFrame {
        border-radius: 10px;
        overflow: hidden;
    }

    /* ── Success/Error alerts ────────────────────────────── */
    .stAlert {
        border-radius: 10px !important;
    }

    /* ── File uploader ───────────────────────────────────── */
    [data-testid="stFileUploader"] {
        border-radius: 10px;
    }

    /* ── Selectbox ────────────────────────────────────────── */
    [data-testid="stSelectbox"] > div > div {
        border-radius: 8px !important;
    }
    </style>
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
                    missing items, price errors & more. Get instant PDF reports.
                </p>
                <span class="hero-badge">✨ AI-POWERED</span>
            </div>
            <div style="text-align:center; opacity:0.15; font-size:5rem; line-height:1;">
                🍔🍕🥗
            </div>
        </div>
    </div>
    """, unsafe_allow_html=True)


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
        initial_sidebar_state="collapsed",
    )

    inject_custom_css()
    render_header()

    # ── Source Inputs ────────────────────────────────────────
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
        with st.spinner("🔄 Analyzing menus..."):
            try:
                our_raw = load_menu(our_payload)
                reference_raw = load_menu(reference_payload)
                our_normalized = normalize_menu(our_raw)
                reference_normalized = normalize_menu(reference_raw)
                report = compare_menus(our_normalized, reference_normalized)
                pdf_bytes = build_pdf_bytes(report)
            except Exception as exc:  # pragma: no cover
                st.error(f"⚠️ {exc}")
                return

        # ── Divider ──────────────────────────────────────────
        st.markdown('<div class="orange-divider"></div>', unsafe_allow_html=True)

        # ── Summary Metrics ──────────────────────────────────
        st.markdown("""
        <div class="section-header">
            <h3>📊 Comparison Summary</h3>
        </div>
        """, unsafe_allow_html=True)

        metrics = report["summary"]
        metric_keys = ["missing_items", "extra_items", "price_mismatches",
                       "description_mismatches", "spelling_errors"]
        metric_cols = st.columns(5, gap="medium")
        for col, key in zip(metric_cols, metric_keys):
            icon = METRIC_ICONS.get(key, "")
            label = f"{icon} {key.replace('_', ' ').title()}"
            col.metric(label, metrics[key])

        # ── Total issues banner ──────────────────────────────
        total = sum(metrics.get(k, 0) for k in metric_keys)
        if total == 0:
            st.success("🎉 **Perfect match!** No issues found between the menus.")
        else:
            st.warning(f"⚠️ **{total} issue(s)** detected across all categories. Review details below.")

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

        dl_col1, dl_col2, dl_col3 = st.columns([1, 1, 1])
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
    <div style="text-align:center; padding:2rem 0 1rem 0; color:#9CA3AF; font-size:0.8rem;">
        Built with ❤️ by <strong style="color:#FF6B00;">Boons</strong> · AI-Powered Menu Verification
    </div>
    """, unsafe_allow_html=True)


if __name__ == "__main__":
    main()
