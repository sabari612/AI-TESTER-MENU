from io import BytesIO


def _issue_lines(report):
    return {
        "Missing Items": [item.get("item", "") for item in report["missing_items"]],
        "Extra Items": [item.get("item", "") for item in report["extra_items"]],
        "Price Differences": [
            f"{item['item']}: Our ${item['our_price']} | Reference ${item['reference_price']}"
            for item in report["price_mismatches"]
        ],
        "Description Mismatches": [item["item"] for item in report["description_mismatches"]],
        "Spelling Errors": [
            f"{item['item']} ({item['field']}): {item['our']} -> {item['reference']}"
            for item in report["spelling_errors"]
        ],
        "Missing Images": [item["item"] for item in report["missing_images"]],
        "Category Mismatches": [
            f"{item['item']}: {item['our_category']} -> {item['reference_category']}"
            for item in report["category_mismatches"]
        ],
    }


def build_pdf_bytes(report):
    try:
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("reportlab is required to build PDF reports.") from exc

    buffer = BytesIO()
    document = SimpleDocTemplate(buffer)
    styles = getSampleStyleSheet()
    story = [Paragraph("MENU VERIFICATION REPORT", styles["Title"]), Spacer(1, 12)]

    summary_lines = [f"{key.replace('_', ' ').title()}: {value}" for key, value in report["summary"].items()]
    story.append(Paragraph("<br/>".join(summary_lines), styles["BodyText"]))
    story.append(Spacer(1, 12))

    for title, lines in _issue_lines(report).items():
        story.append(Paragraph(title, styles["Heading2"]))
        if lines:
            for line in lines:
                story.append(Paragraph(f"• {line}", styles["BodyText"]))
        else:
            story.append(Paragraph("No issues found.", styles["BodyText"]))
        story.append(Spacer(1, 8))

    document.build(story)
    return buffer.getvalue()


def save_pdf_report(report, output_path):
    pdf_bytes = build_pdf_bytes(report)
    with open(output_path, "wb") as file_obj:
        file_obj.write(pdf_bytes)
    return output_path

