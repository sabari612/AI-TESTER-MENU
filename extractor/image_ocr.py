from io import BytesIO

from processing.normalize_menu import parse_menu_text


def read_image_menu(file_bytes):
    try:
        from PIL import Image
        import pytesseract
    except ImportError as exc:  # pragma: no cover
        raise RuntimeError("Pillow and pytesseract are required for image extraction.") from exc

    image = Image.open(BytesIO(file_bytes))
    text = pytesseract.image_to_string(image)
    return parse_menu_text(text)

