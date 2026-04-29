from io import BytesIO
import html as _html


def _e(text, max_len=120):
    """Escape HTML entities and truncate."""
    t = _html.escape(str(text or ""))
    return t[:max_len] + ("..." if len(t) > max_len else "")


def _badge(is_same):
    """Return a colored SAME / DIFFERENT badge as HTML."""
    if is_same:
        return '<span class="badge badge-same">SAME</span>'
    return '<span class="badge badge-diff">DIFFERENT</span>'


def _build_html(report):
    """Build the full HTML document that mirrors the Standard Report UI."""
    summary = report.get("summary", {})
    mk = ["missing_items", "extra_items", "price_mismatches",
          "description_mismatches", "spelling_errors", "category_mismatches"]
    total_issues = sum(summary.get(k, 0) for k in mk)
    matched = summary.get("matched_total", 0)
    perfect = summary.get("perfect_matches", 0)
    with_diffs = summary.get("items_with_differences", 0)
    status = "PASS" if total_issues == 0 else "REVIEW"
    status_color = "#10B981" if total_issues == 0 else "#EF4444"

    parts = [_CSS, f'''<body>
<h1 class="title">MENU VERIFICATION REPORT</h1>
<div class="stats-banner">
  <div class="stat"><div class="stat-val">{summary.get("our_total",0)}</div><div class="stat-lbl">Our Total</div></div>
  <div class="stat"><div class="stat-val">{summary.get("reference_total",0)}</div><div class="stat-lbl">Ref Total</div></div>
  <div class="stat"><div class="stat-val">{matched}</div><div class="stat-lbl">Matched</div></div>
  <div class="stat"><div class="stat-val">{perfect}</div><div class="stat-lbl">Perfect</div></div>
  <div class="stat"><div class="stat-val">{with_diffs}</div><div class="stat-lbl">With Diffs</div></div>
  <div class="stat"><div class="stat-val">{summary.get("missing_items",0)}</div><div class="stat-lbl">Missing</div></div>
  <div class="stat"><div class="stat-val">{summary.get("extra_items",0)}</div><div class="stat-lbl">Extra</div></div>
  <div class="stat"><div class="stat-val">{total_issues}</div><div class="stat-lbl">Total Issues</div></div>
  <div class="stat"><div class="stat-val" style="color:{status_color}">{status}</div><div class="stat-lbl">Status</div></div>
</div>''']

    if total_issues == 0:
        parts.append('<div class="result-pass">Perfect Match! All items matched with no differences.</div>')
    else:
        parts.append(f'<div class="result-fail">{total_issues} issue(s) detected across {with_diffs} items</div>')

    # ── Matched Items ──────────────────────────────────────
    matched_items = report.get("matched_items", [])
    parts.append(f'<h2 class="section-title">Matched Items ({len(matched_items)})</h2>')

    if not matched_items:
        parts.append('<p class="ok-msg">No items matched.</p>')
    else:
        perf_count = sum(1 for m in matched_items if m.get("is_perfect_match"))
        diff_count = len(matched_items) - perf_count
        parts.append(f'<p><strong>{len(matched_items)}</strong> matched items &mdash; '
                     f'<strong>{perf_count}</strong> perfect, <strong>{diff_count}</strong> with differences</p>')

        for m in matched_items:
            parts.append(_matched_card_html(m))

    # ── Missing Items ──────────────────────────────────────
    parts.append(_issue_table_html(
        "Missing Items", report.get("missing_items", []),
        ["Item", "Category"],
        lambda it: [_e(it.get("item", "")), _e(it.get("category", ""))],
        hdr_bg="#991B1B", row_bg="#FEF2F2", border="#FECACA"))

    # ── Extra Items ────────────────────────────────────────
    parts.append(_issue_table_html(
        "Extra Items", report.get("extra_items", []),
        ["Item", "Category"],
        lambda it: [_e(it.get("item", "")), _e(it.get("category", ""))],
        hdr_bg="#1E40AF", row_bg="#EFF6FF", border="#DBEAFE"))

    # ── Price Mismatches ───────────────────────────────────
    parts.append(_issue_table_html(
        "Price Mismatches", report.get("price_mismatches", []),
        ["Item", "Our Price", "Ref Price", "Reason"],
        lambda it: [_e(it.get("our_item", it.get("item", ""))),
                    f"${it.get('our_price','')}", f"${it.get('reference_price','')}",
                    _e(it.get("reason", ""), 80)],
        hdr_bg="#92400E", row_bg="#FFFBEB", border="#FEF3C7"))

    # ── Category Mismatches ────────────────────────────────
    parts.append(_issue_table_html(
        "Category Mismatches", report.get("category_mismatches", []),
        ["Item", "Our Category", "Ref Category"],
        lambda it: [_e(it.get("our_item", it.get("item", ""))),
                    _e(it.get("our_category", "")), _e(it.get("reference_category", ""))],
        hdr_bg="#6B21A8", row_bg="#FAF5FF", border="#F3E8FF"))

    # ── Description Mismatches ─────────────────────────────
    parts.append(_issue_table_html(
        "Description Mismatches", report.get("description_mismatches", []),
        ["Item", "Our Description", "Ref Description"],
        lambda it: [_e(it.get("our_item", it.get("item", ""))),
                    _e(it.get("our_description", ""), 80), _e(it.get("reference_description", ""), 80)],
        hdr_bg="#3730A3", row_bg="#EEF2FF", border="#E0E7FF"))

    # ── Spelling Errors ────────────────────────────────────
    parts.append(_issue_table_html(
        "Spelling Errors", report.get("spelling_errors", []),
        ["Item", "Field", "Our Text", "Ref Text"],
        lambda it: [_e(it.get("our_item", it.get("item", ""))),
                    _e(it.get("field", "")), _e(it.get("our", ""), 60),
                    _e(it.get("reference", ""), 60)],
        hdr_bg="#065F46", row_bg="#ECFDF5", border="#CCFBF1"))

    # ── Missing Images ─────────────────────────────────────
    images = report.get("missing_images", [])
    parts.append(f'<h2 class="section-title">Missing Images ({len(images)})</h2>')
    if not images:
        parts.append('<p class="ok-msg">No missing images.</p>')
    else:
        for it in images:
            parts.append(f'<p>&bull; {_e(it.get("item",""))} ({_e(it.get("category",""))})</p>')

    parts.append('</body></html>')
    return "\n".join(parts)


def _matched_card_html(m):
    """Render a single matched-item card as HTML — same as the Streamlit UI."""
    diffs = m.get("differences", [])
    is_perfect = m.get("is_perfect_match", False)
    score = m.get("score", 0)

    border_color = "#10B981" if is_perfect else "#F59E0B"
    header_bg = "#D1FAE5" if is_perfect else "#FEF3C7"
    header_fg = "#065F46" if is_perfect else "#92400E"
    status_text = "Perfect Match" if is_perfect else f"{len(diffs)} difference(s): {', '.join(diffs)}"
    icon = "&#10004;" if is_perfect else "&#9888;"

    price_same = str(m.get("our_price","")).strip() == str(m.get("reference_price","")).strip()
    cat_same = str(m.get("our_category","")).strip().lower() == str(m.get("reference_category","")).strip().lower()
    desc_same = str(m.get("our_description","")).strip().lower() == str(m.get("reference_description","")).strip().lower()
    name_same = str(m.get("our_item","")).strip().lower() == str(m.get("reference_item","")).strip().lower()

    our_price = f"${m.get('our_price','')}" if m.get("our_price") else "&mdash;"
    ref_price = f"${m.get('reference_price','')}" if m.get("reference_price") else "&mdash;"

    def _row(label, our, ref, same, bg_diff=""):
        bg = f'background:{bg_diff};' if not same and bg_diff else ''
        fw = 'font-weight:700;' if not same else ''
        return f'''<tr style="border-bottom:1px solid #E5E7EB;{bg}">
            <td style="padding:6px 12px;font-weight:600;">{label}</td>
            <td style="padding:6px 12px;{fw}">{our}</td>
            <td style="padding:6px 12px;{fw}">{ref}</td>
            <td style="padding:6px 12px;text-align:center;">{_badge(same)}</td>
        </tr>'''

    return f'''
    <div class="card" style="border-color:{border_color};">
        <div class="card-header" style="background:{header_bg};color:{header_fg};">
            {_e(m.get("our_item",""))} &harr; {_e(m.get("reference_item",""))}
            &nbsp;&nbsp;<span style="font-size:8px;font-weight:400;">Match: {score:.0f}%</span>
            &nbsp;&nbsp;{icon} {status_text}
        </div>
        <table class="card-table">
            <thead><tr style="background:#F3F4F6;">
                <th style="width:15%;">Field</th><th style="width:35%;">Our Menu</th>
                <th style="width:35%;">Reference Menu</th><th style="width:15%;text-align:center;">Status</th>
            </tr></thead>
            <tbody>
                {_row("Name", _e(m.get("our_item","")), _e(m.get("reference_item","")), name_same)}
                {_row("Price", our_price, ref_price, price_same, "#FEF3C7")}
                {_row("Category", _e(m.get("our_category","")), _e(m.get("reference_category","")), cat_same, "#F3E8FF")}
                {_row("Description", _e(m.get("our_description","") or "&mdash;", 120),
                      _e(m.get("reference_description","") or "&mdash;", 120), desc_same, "#E0E7FF")}
            </tbody>
        </table>
    </div>'''


def _issue_table_html(title, items, columns, row_fn,
                      hdr_bg="#333", row_bg="#f9f9f9", border="#ddd"):
    """Render a section with header + table for an issue type."""
    html = f'<h2 class="section-title">{title} ({len(items)})</h2>'
    if not items:
        html += f'<p class="ok-msg">No {title.lower()} found.</p>'
        return html

    html += f'<table class="issue-table" style="border:1px solid {border};">'
    html += f'<thead><tr style="background:{hdr_bg};color:white;">'
    for col in columns:
        html += f'<th>{col}</th>'
    html += '</tr></thead><tbody>'
    for i, it in enumerate(items):
        bg = row_bg if i % 2 == 0 else "#ffffff"
        html += f'<tr style="background:{bg};">'
        for val in row_fn(it):
            html += f'<td>{val}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html


_CSS = '''<!DOCTYPE html><html><head><meta charset="utf-8">
<style>
@page { size: A4; margin: 1.5cm; }
body { font-family: Helvetica, Arial, sans-serif; font-size: 10px; color: #1a1a2e; margin: 0; padding: 0; }
.title { text-align: center; font-size: 20px; color: #1a237e; margin-bottom: 10px; border-bottom: 2px solid #bbdefb; padding-bottom: 8px; }
.stats-banner { display: flex; justify-content: space-between; background: #f8f9fa; border: 1px solid #e0e0e0;
    border-radius: 8px; padding: 8px 4px; margin-bottom: 12px; }
.stat { text-align: center; flex: 1; }
.stat-val { font-size: 16px; font-weight: 700; color: #1a237e; }
.stat-lbl { font-size: 8px; color: #666; text-transform: uppercase; }
.result-pass { background: #D1FAE5; color: #065F46; padding: 8px 14px; border-radius: 6px; font-weight: 700; margin-bottom: 14px; text-align: center; }
.result-fail { background: #FEE2E2; color: #991B1B; padding: 8px 14px; border-radius: 6px; font-weight: 700; margin-bottom: 14px; text-align: center; }
.section-title { font-size: 14px; color: #1a237e; border-bottom: 2px solid #bbdefb; padding-bottom: 4px; margin-top: 18px; }
.ok-msg { color: #065F46; font-style: italic; }

.card { border: 2px solid #ccc; border-radius: 8px; margin-bottom: 10px; overflow: hidden; }
.card-header { padding: 6px 12px; font-weight: 700; font-size: 10px; }
.card-table { width: 100%; border-collapse: collapse; font-size: 9px; }
.card-table th { padding: 5px 10px; text-align: left; font-size: 9px; }
.card-table td { padding: 5px 10px; }

.badge { padding: 2px 6px; border-radius: 3px; font-size: 7px; font-weight: 700; }
.badge-same { background: #D1FAE5; color: #065F46; }
.badge-diff { background: #FEE2E2; color: #991B1B; }

.issue-table { width: 100%; border-collapse: collapse; margin-bottom: 10px; font-size: 9px; }
.issue-table th { padding: 5px 8px; text-align: left; font-size: 9px; font-weight: 700; }
.issue-table td { padding: 4px 8px; border-bottom: 1px solid #eee; }
</style></head>'''


def build_pdf_bytes(report):
    """Generate a PDF from HTML that mirrors the Standard Report UI."""
    try:
        from xhtml2pdf import pisa
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("xhtml2pdf is required to build PDF reports.") from exc

    html_content = _build_html(report)
    buffer = BytesIO()
    pisa_status = pisa.CreatePDF(html_content, dest=buffer)
    if pisa_status.err:
        raise RuntimeError(f"PDF generation failed with {pisa_status.err} error(s)")
    return buffer.getvalue()


def save_pdf_report(report, output_path):
    pdf_bytes = build_pdf_bytes(report)
    with open(output_path, "wb") as file_obj:
        file_obj.write(pdf_bytes)
    return output_path
