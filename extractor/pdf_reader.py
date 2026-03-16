from io import BytesIO

from processing.normalize_menu import parse_menu_text


def read_pdf_menu(file_bytes):
    try:
        import pdfplumber
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("pdfplumber is required for PDF extraction.") from exc

    with pdfplumber.open(BytesIO(file_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)
    return parse_menu_text(text)

