from extractor.docx_reader import read_docx_menu
from extractor.image_ocr import read_image_menu
from extractor.json_reader import read_json_menu
from extractor.pdf_reader import read_pdf_menu
from extractor.web_scraper import read_website_menu


def extract_menu_from_source(source_type, file_bytes=None, text=None, url=None):
    source_type = source_type.lower()
    if source_type in {"json text", "json file", "api response text", "api response"}:
        return read_json_menu(file_bytes=file_bytes, text=text)
    if source_type in {"website url", "url", "website"}:
        if not url:
            raise ValueError("A website URL is required.")
        return read_website_menu(url)
    if source_type == "pdf":
        return read_pdf_menu(file_bytes)
    if source_type == "image":
        return read_image_menu(file_bytes)
    if source_type in {"word document", "docx"}:
        return read_docx_menu(file_bytes)
    raise ValueError(f"Unsupported source type: {source_type}")

