# Restaurant Menu Verification System

An AI-assisted Python application that compares an internal menu against a reference menu, detects mismatches, and produces a PDF verification report.

## Features
- Extracts menus from JSON/API payloads, PDFs, images, Word documents, and websites
- Normalizes all extracted content into a shared JSON schema
- Uses fuzzy matching to align similar menu items
- Detects missing items, extra items, price mismatches, description mismatches, spelling issues, missing images, and category mismatches
- Exposes a Streamlit UI and PDF report download

## Project Structure
- `app.py`
- `extractor/`
- `processing/`
- `comparator/`
- `reports/`
- `examples/`
- `tests/`

## Install
Use pip to install the required libraries:
`pip install streamlit rapidfuzz pdfplumber pytesseract beautifulsoup4 reportlab python-docx pillow requests`

If you want OCR support, install Tesseract on your machine and ensure it is available on PATH.

## Run
Start the Streamlit app:
`streamlit run app.py`

Run the unit test suite:
`python -m unittest discover -s tests -v`

## Example Data
- `examples/our_menu.json`
- `examples/reference_menu.json`

You can paste JSON into the UI or upload the example files to test the workflow.

