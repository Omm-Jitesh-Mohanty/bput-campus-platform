"""
Load PDFs and extract text.
"""
import logging
from pathlib import Path

import pdfplumber

logger = logging.getLogger(__name__)


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF file. Returns str."""
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        logger.warning(f'PDF not found: {pdf_path}')
        return ''

    try:
        parts = []
        with pdfplumber.open(str(pdf_path)) as pdf:
            for i, page in enumerate(pdf.pages):
                text = page.extract_text() or ''
                if text.strip():
                    parts.append(f'--- Page {i + 1} ---\n{text}')
        return '\n\n'.join(parts)
    except Exception as e:
        logger.exception(f'PDF extraction failed for {pdf_path}: {e}')
        return ''


def load_all_pdfs(folder):
    """Return list of {path, name, text}."""
    folder = Path(folder)
    if not folder.exists():
        return []

    docs = []
    for pdf_path in sorted(folder.glob('*.pdf')):
        text = extract_text_from_pdf(pdf_path)
        if text.strip():
            docs.append({
                'path': str(pdf_path),
                'name': pdf_path.stem,
                'title': pdf_path.stem.replace('_', ' ').title(),
                'text': text,
            })
    logger.info(f'Loaded {len(docs)} PDFs from {folder}')
    return docs