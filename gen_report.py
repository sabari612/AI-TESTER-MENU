"""Generate comprehensive PDF report for the Menu Verification System.  Run: python gen_report.py"""
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
                                PageBreak, ListFlowable, ListItem, HRFlowable)
from reportlab.graphics.shapes import Drawing, Rect, String, Line, Group
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY

OUTPUT = "Project_Report_Menu_Verification_System.pdf"
styles = getSampleStyleSheet()
styles.add(ParagraphStyle("CT", fontSize=28, leading=34, alignment=TA_CENTER, spaceAfter=20,
                          textColor=colors.HexColor("#1a237e"), fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("CS", fontSize=14, leading=18, alignment=TA_CENTER, spaceAfter=8,
                          textColor=colors.HexColor("#424242")))
styles.add(ParagraphStyle("Sec", fontSize=18, leading=22, spaceBefore=18, spaceAfter=10,
                          textColor=colors.HexColor("#0d47a1"), fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("Sub", fontSize=13, leading=16, spaceBefore=12, spaceAfter=6,
                          textColor=colors.HexColor("#1565c0"), fontName="Helvetica-Bold"))
styles.add(ParagraphStyle("B", fontSize=10, leading=14, alignment=TA_JUSTIFY, spaceAfter=6))
HR = HRFlowable(width="100%", thickness=1, color=colors.HexColor("#bbdefb"), spaceAfter=10, spaceBefore=6)
BW, BH, GAP = 150, 30, 14


def _box(d, x, y, label, fill="#e3f2fd", brd="#1565c0"):
    g = Group()
    g.add(Rect(x, y, BW, BH, fillColor=colors.HexColor(fill),
               strokeColor=colors.HexColor(brd), strokeWidth=1, rx=6, ry=6))
    g.add(String(x + BW / 2, y + 10, label, fontSize=8, fontName="Helvetica-Bold",
                 fillColor=colors.HexColor("#0d47a1"), textAnchor="middle"))
    d.add(g)


def _arrow(d, x1, y1, x2, y2):
    d.add(Line(x1, y1, x2, y2, strokeColor=colors.HexColor("#1565c0"), strokeWidth=1.2))
    d.add(Line(x2, y2, x2 - 4, y2 + 6, strokeColor=colors.HexColor("#1565c0"), strokeWidth=1.2))
    d.add(Line(x2, y2, x2 + 4, y2 + 6, strokeColor=colors.HexColor("#1565c0"), strokeWidth=1.2))


def _vflow(labels, clrs=None):
    dh = len(labels) * (BH + GAP) + 20
    d = Drawing(400, dh)
    cx = (400 - BW) / 2
    top = dh - BH - 10
    for i, lb in enumerate(labels):
        y = top - i * (BH + GAP)
        f, b = clrs[i] if clrs else ("#e3f2fd", "#1565c0")
        _box(d, cx, y, lb, f, b)
        if i > 0:
            _arrow(d, cx + BW / 2, y + BH, cx + BW / 2, y + BH + GAP)
    return d


def _tbl(data, cw):
    t = Table(data, colWidths=cw)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1565c0")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#bbdefb")),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.HexColor("#f5f5f5"), colors.white]),
        ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    return t


def _bl(items):
    return ListFlowable(
        [ListItem(Paragraph(i, styles["B"])) for i in items],
        bulletType="bullet", start="\u2022")


def build_story():
    S = []
    # Cover Page
    S += [Spacer(1, 2 * inch),
          Paragraph("Restaurant Menu Verification System", styles["CT"]),
          Paragraph("Comprehensive Project Report", styles["CS"]),
          Spacer(1, .3 * inch),
          Paragraph("Version 1.0  \u2022  March 2026", styles["CS"]),
          Paragraph("AI-Assisted Menu Comparison &amp; QA Platform", styles["CS"]),
          Spacer(1, 1.5 * inch),
          Paragraph("Prepared by: Development Team", styles["CS"]),
          Paragraph("Date: 15 March 2026", styles["CS"]),
          PageBreak()]
    # Table of Contents
    S += [Paragraph("Table of Contents", styles["Sec"]), HR]
    for t in ["1. Executive Summary", "2. Project Overview", "3. System Architecture",
              "4. Module Details", "5. Application Flow", "6. Extraction Pipeline",
              "7. Comparison Engine", "8. Technology Stack", "9. Current Features",
              "10. Known Limitations", "11. Future Roadmap", "12. File Inventory"]:
        S.append(Paragraph(t, styles["B"]))
    S.append(PageBreak())
    _sections(S)
    return S


def _sections(S):
    """All numbered report sections."""
    # 1 — Executive Summary
    S += [Paragraph("1. Executive Summary", styles["Sec"]), HR,
          Paragraph(
              "The <b>Restaurant Menu Verification System</b> automates menu quality assurance by "
              "extracting menus from multiple formats (JSON, PDF, images, DOCX, live websites), "
              "normalising data into a shared schema, performing fuzzy matching, and detecting "
              "<b>missing items, extra items, price mismatches, description differences, spelling "
              "errors, missing images, and category mismatches</b>. A Streamlit web interface "
              "displays results and offers downloadable PDF reports.", styles["B"]),
          Spacer(1, .15 * inch)]

    # 2 — Project Overview
    S += [Paragraph("2. Project Overview &amp; Objectives", styles["Sec"]), HR,
          _bl(["Automate menu QA across restaurants and ordering platforms.",
               "Support diverse inputs: JSON APIs, PDFs, scanned images (OCR), DOCX, websites.",
               "Detect all categories of menu discrepancies in a single comparison run.",
               "Provide clear, downloadable PDF reports for restaurant managers and QA teams.",
               "Handle bot-protected websites via multi-strategy scraping (requests, cloudscraper, cache proxies)."]),
          Spacer(1, .15 * inch)]

    # 3 — Architecture
    S += [Paragraph("3. System Architecture", styles["Sec"]), HR,
          Paragraph("The system follows a <b>layered pipeline architecture</b>:", styles["B"]),
          _tbl([["Layer", "Package", "Responsibility"],
                ["Presentation", "app.py (Streamlit)", "UI, user input collection, result display, PDF download"],
                ["Extraction", "extractor/", "Read menus from JSON, PDF, Image, DOCX, Website sources"],
                ["Processing", "processing/", "Normalize and clean all menu data into a unified schema"],
                ["Comparison", "comparator/", "Fuzzy-match items and detect all mismatch types"],
                ["Reporting", "reports/", "Build downloadable PDF verification reports"]],
               [1.2 * inch, 1.7 * inch, 3.3 * inch]),
          Spacer(1, .2 * inch), PageBreak()]

    # 4 — Module Details
    S += [Paragraph("4. Module Details", styles["Sec"]), HR]
    modules = [
        ["Module", "File", "Key Functions / Classes"],
        ["Extractor Factory", "extractor/factory.py", "extract_menu_from_source() - routes to correct reader"],
        ["JSON Reader", "extractor/json_reader.py", "read_json_menu() - parse JSON text or file bytes"],
        ["PDF Reader", "extractor/pdf_reader.py", "read_pdf_menu() - extract text via pdfplumber"],
        ["Image OCR", "extractor/image_ocr.py", "read_image_menu() - Tesseract OCR on uploaded images"],
        ["DOCX Reader", "extractor/docx_reader.py", "read_docx_menu() - extract from Word documents"],
        ["Web Scraper", "extractor/web_scraper.py", "read_website_menu() - LD+JSON, HTML tables, text fallback"],
        ["Normalizer", "processing/normalize_menu.py", "normalize_menu(), parse_menu_text(), coerce_price()"],
        ["Item Matcher", "comparator/item_matcher.py", "best_item_match(), similarity() - fuzzy matching"],
        ["Price Checker", "comparator/price_checker.py", "price_difference() - detect price mismatches"],
        ["Desc Checker", "comparator/description_checker.py", "descriptions_differ(), detect_spelling_errors()"],
        ["Image Checker", "comparator/image_checker.py", "missing_image_issue() - flag missing images"],
        ["Menu Comparator", "comparator/menu_comparator.py", "compare_menus() - orchestrates all checks"],
        ["PDF Report", "reports/pdf_report.py", "build_pdf_bytes() - generate downloadable PDF"],
    ]
    S += [_tbl(modules, [1.2 * inch, 1.8 * inch, 3.2 * inch]), Spacer(1, .2 * inch), PageBreak()]

    # 5 — Application Flow
    main_flow_clrs = [("#e8f5e9", "#2e7d32"), ("#e3f2fd", "#1565c0"), ("#e3f2fd", "#1565c0"),
                      ("#e3f2fd", "#1565c0"), ("#fff3e0", "#e65100"), ("#fce4ec", "#c62828"),
                      ("#e8f5e9", "#2e7d32")]
    S += [Paragraph("5. Application Flow (Flowchart)", styles["Sec"]), HR,
          Paragraph("Main application pipeline from user interaction to report download:", styles["B"]),
          _vflow(["User Opens Streamlit UI", "Select Source Types & Input",
                  "Extract Menu (Extractor)", "Normalize Menu Data",
                  "Compare Menus (Comparator)", "Generate PDF Report",
                  "Display Results & Download"], main_flow_clrs),
          Spacer(1, .2 * inch), PageBreak()]

    # 6 — Extraction Pipeline
    S += [Paragraph("6. Extraction Pipeline Flow", styles["Sec"]), HR,
          Paragraph("The Extractor Factory routes input to the appropriate reader:", styles["B"]),
          _tbl([["Source Type", "Reader Module", "Strategy"],
                ["JSON Text / File", "json_reader.py", "json.loads() on text or decoded file bytes"],
                ["PDF Upload", "pdf_reader.py", "pdfplumber page-by-page text extraction"],
                ["Image Upload", "image_ocr.py", "Tesseract OCR via pytesseract"],
                ["Word Document", "docx_reader.py", "python-docx paragraph + table extraction"],
                ["Website URL", "web_scraper.py", "LD+JSON > HTML tables > plain text (3 strategies)"]],
               [1.3 * inch, 1.5 * inch, 3.4 * inch]),
          Spacer(1, .15 * inch),
          Paragraph("<b>Web Scraper Multi-Strategy Approach:</b>", styles["B"]),
          _vflow(["1. Plain requests (fast)", "2. Cloudscraper (Cloudflare bypass)",
                  "3. Google Cache Proxy (last resort)", "Parse: LD+JSON > Tables > Text"],
                 [("#e8f5e9", "#2e7d32"), ("#fff3e0", "#e65100"),
                  ("#fce4ec", "#c62828"), ("#e3f2fd", "#1565c0")]),
          Spacer(1, .2 * inch), PageBreak()]

    # 7 — Comparison Engine
    S += [Paragraph("7. Comparison Engine Flow", styles["Sec"]), HR,
          Paragraph("The comparator aligns items via fuzzy matching, then runs all check modules:", styles["B"]),
          _vflow(["Normalize Both Menus", "Fuzzy-Match Items (rapidfuzz)",
                  "Identify Missing & Extra Items", "Price Checker",
                  "Description Checker", "Spelling Error Detector",
                  "Image Checker", "Category Mismatch Checker",
                  "Build Summary Report"],
                 [("#e3f2fd", "#1565c0"), ("#fff3e0", "#e65100"), ("#fce4ec", "#c62828"),
                  ("#e8f5e9", "#2e7d32"), ("#e8f5e9", "#2e7d32"), ("#e8f5e9", "#2e7d32"),
                  ("#e8f5e9", "#2e7d32"), ("#e8f5e9", "#2e7d32"), ("#e3f2fd", "#1565c0")]),
          Spacer(1, .15 * inch),
          Paragraph("<b>Mismatch Types Detected:</b>", styles["B"]),
          _tbl([["Check", "Module", "Logic"],
                ["Missing Items", "item_matcher", "Reference items not found in our menu (score &lt; 84)"],
                ["Extra Items", "item_matcher", "Our items not matched to any reference item"],
                ["Price Mismatch", "price_checker", "Absolute difference &gt; $0.01 tolerance"],
                ["Description Diff", "description_checker", "SequenceMatcher ratio &lt; 0.88 or word count gap"],
                ["Spelling Errors", "description_checker", "Token-level fuzzy match ratio 0.82-0.99"],
                ["Missing Images", "image_checker", "Our item has no image URL when reference does"],
                ["Category Mismatch", "menu_comparator", "Category name differs between matched items"]],
               [1.2 * inch, 1.5 * inch, 3.5 * inch]),
          Spacer(1, .2 * inch), PageBreak()]

    _sections_part2(S)


def _sections_part2(S):
    """Sections 8-12."""
    # 8 — Technology Stack
    S += [Paragraph("8. Technology Stack", styles["Sec"]), HR,
          _tbl([["Technology", "Purpose", "Version / Notes"],
                ["Python 3.10+", "Core language", "3.10 - 3.13 tested"],
                ["Streamlit", "Web UI framework", "Interactive dashboard with widgets"],
                ["reportlab", "PDF generation", "v4.4 - vector PDF reports"],
                ["rapidfuzz", "Fuzzy string matching", "Token sort ratio for item alignment"],
                ["pdfplumber", "PDF text extraction", "Page-by-page text extraction"],
                ["pytesseract", "OCR for images", "Requires Tesseract engine on PATH"],
                ["python-docx", "Word document parsing", "Paragraph + table extraction"],
                ["BeautifulSoup4", "HTML parsing", "LD+JSON, tables, text from websites"],
                ["requests", "HTTP client", "Primary web fetching strategy"],
                ["cloudscraper", "Anti-bot bypass", "Cloudflare JS challenge handling"],
                ["Pillow", "Image processing", "Image loading for OCR pipeline"]],
               [1.3 * inch, 1.7 * inch, 3.2 * inch]),
          Spacer(1, .2 * inch), PageBreak()]

    # 9 — Current Features
    S += [Paragraph("9. Current Features", styles["Sec"]), HR,
          _bl(["<b>Multi-source extraction:</b> JSON, PDF, Image (OCR), DOCX, Website URL",
               "<b>Smart web scraping:</b> 3-strategy fallback (requests > cloudscraper > cache proxy)",
               "<b>LD+JSON extraction:</b> Parses structured restaurant data from Schema.org markup",
               "<b>Unified normalization:</b> All sources normalized to {category, item, price, description, image}",
               "<b>Fuzzy item matching:</b> rapidfuzz token_sort_ratio with 84% threshold + category bonus",
               "<b>7 mismatch types:</b> Missing, Extra, Price, Description, Spelling, Image, Category",
               "<b>Interactive UI:</b> Streamlit with tabs, metrics, expanders, and dataframe views",
               "<b>PDF report download:</b> Professional verification report via reportlab",
               "<b>JSON report export:</b> Full structured report displayed in-app",
               "<b>Unit test suite:</b> Tests for comparator logic and web scraper"]),
          Spacer(1, .2 * inch)]

    # 10 — Known Limitations
    S += [Paragraph("10. Known Limitations", styles["Sec"]), HR,
          _bl(["Bot-protected sites may still block scraping (Cloudflare Enterprise, reCAPTCHA)",
               "OCR accuracy depends on image quality and Tesseract configuration",
               "Fuzzy matching threshold (84%) may need tuning for different cuisines",
               "No persistent storage - results are session-only",
               "No user authentication or multi-tenant support",
               "PDF report is basic text-only (no charts or visual analytics)",
               "No CI/CD pipeline or automated deployment configured"]),
          Spacer(1, .2 * inch), PageBreak()]

    # 11 — Future Roadmap
    S += [Paragraph("11. Future Roadmap &amp; Next Steps", styles["Sec"]), HR,
          Paragraph("<b>Phase 1 - Short Term (Next 2-4 weeks):</b>", styles["Sub"]),
          _bl(["Add Selenium/Playwright browser automation for JavaScript-rendered restaurant sites",
               "Integrate OpenAI/Gemini API for intelligent menu item categorization",
               "Add batch comparison mode - compare multiple restaurant locations at once",
               "Enhance PDF report with charts, color-coded severity, and visual dashboards",
               "Add CSV/Excel export alongside PDF"]),
          Spacer(1, .1 * inch),
          Paragraph("<b>Phase 2 - Medium Term (1-2 months):</b>", styles["Sub"]),
          _bl(["Build a database layer (PostgreSQL/SQLite) for historical comparison tracking",
               "Add scheduled automated comparisons with email/Slack notifications",
               "Create a REST API endpoint for programmatic access (FastAPI)",
               "Implement role-based access control and user management",
               "Add image comparison using perceptual hashing (imagehash)",
               "Support menu translations and multi-language comparison"]),
          Spacer(1, .1 * inch),
          Paragraph("<b>Phase 3 - Long Term (3-6 months):</b>", styles["Sub"]),
          _bl(["ML-based menu categorization model trained on restaurant menu datasets",
               "Real-time menu monitoring dashboard with change detection alerts",
               "Integration with POS systems (Square, Toast, Clover) for live menu sync",
               "Mobile-friendly PWA version of the verification interface",
               "Containerized deployment (Docker) with CI/CD pipeline (GitHub Actions)",
               "Multi-restaurant chain management with centralized reporting",
               "Compliance checking against food labeling regulations"]),
          Spacer(1, .2 * inch), PageBreak()]

    # 12 — File Inventory
    S += [Paragraph("12. File Inventory", styles["Sec"]), HR,
          _tbl([["File", "Lines", "Purpose"],
                ["app.py", "124", "Streamlit UI - main entry point"],
                ["extractor/__init__.py", "2", "Package init, re-exports factory"],
                ["extractor/factory.py", "23", "Routes source type to correct reader"],
                ["extractor/json_reader.py", "11", "JSON text/file parsing"],
                ["extractor/pdf_reader.py", "15", "PDF text extraction via pdfplumber"],
                ["extractor/image_ocr.py", "16", "Image OCR via pytesseract"],
                ["extractor/docx_reader.py", "20", "Word document extraction"],
                ["extractor/web_scraper.py", "~160", "Multi-strategy website menu scraping"],
                ["processing/normalize_menu.py", "117", "Menu normalization and text parsing"],
                ["comparator/menu_comparator.py", "85", "Orchestrates all comparison checks"],
                ["comparator/item_matcher.py", "45", "Fuzzy item matching with rapidfuzz"],
                ["comparator/price_checker.py", "14", "Price difference detection"],
                ["comparator/description_checker.py", "47", "Description diff and spelling checks"],
                ["comparator/image_checker.py", "8", "Missing image detection"],
                ["reports/pdf_report.py", "60", "PDF report builder with reportlab"],
                ["tests/test_menu_comparator.py", "69", "Unit tests for comparison engine"],
                ["tests/test_web_scraper.py", "~50", "Unit tests for web scraper"]],
               [2.2 * inch, 0.6 * inch, 3.4 * inch]),
          Spacer(1, .3 * inch),
          Paragraph("--- End of Report ---", styles["CS"])]


def main():
    doc = SimpleDocTemplate(OUTPUT, pagesize=A4, topMargin=0.7 * inch, bottomMargin=0.7 * inch)
    doc.build(build_story())
    print(f"Report saved to {OUTPUT}")


if __name__ == "__main__":
    main()

