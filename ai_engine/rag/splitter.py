"""
Recursive text splitter.

Splits text at natural boundaries (paragraphs → sentences → words)
with overlap. Preserves semantic units better than fixed-size chunking.
"""
import logging
import re
from dataclasses import dataclass
from typing import List

logger = logging.getLogger(__name__)


@dataclass
class Chunk:
    text: str
    metadata: dict


def split_text(
    text: str,
    chunk_size: int = 800,
    chunk_overlap: int = 150,
    metadata: dict = None,
) -> List[Chunk]:
    """
    Split text recursively.

    Separators in priority order:
      1. Double newline (paragraphs)
      2. Single newline
      3. Sentence boundaries (. ! ?)
      4. Spaces
      5. Character-level (fallback)

    Overlap: adjacent chunks share `chunk_overlap` characters.
    """
    metadata = metadata or {}
    text = (text or '').strip()
    if not text:
        return []

    # Split at paragraph level first
    paragraphs = re.split(r'\n\s*\n', text)
    pieces = []

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue
        if len(para) <= chunk_size:
            pieces.append(para)
        else:
            # Split long paragraphs by sentence
            pieces.extend(_split_long_paragraph(para, chunk_size))

    # Merge small pieces up to chunk_size
    chunks = _merge_pieces(pieces, chunk_size)

    # Apply overlap
    if chunk_overlap > 0 and len(chunks) > 1:
        chunks = _apply_overlap(chunks, chunk_overlap)

    return [Chunk(text=c, metadata={**metadata, 'char_count': len(c)}) for c in chunks]


def _split_long_paragraph(text, chunk_size):
    """Break a long paragraph at sentence boundaries."""
    sentences = re.split(r'(?<=[.!?])\s+', text)
    result = []
    current = ''

    for s in sentences:
        if len(current) + len(s) + 1 <= chunk_size:
            current = f'{current} {s}'.strip()
        else:
            if current:
                result.append(current)
            # Sentence itself too long → split by words
            if len(s) > chunk_size:
                result.extend(_split_by_words(s, chunk_size))
                current = ''
            else:
                current = s

    if current:
        result.append(current)
    return result


def _split_by_words(text, chunk_size):
    words = text.split()
    result = []
    current = ''
    for w in words:
        if len(current) + len(w) + 1 <= chunk_size:
            current = f'{current} {w}'.strip()
        else:
            if current:
                result.append(current)
            current = w
    if current:
        result.append(current)
    return result


def _merge_pieces(pieces, chunk_size):
    """Merge adjacent small pieces up to chunk_size."""
    result = []
    current = ''
    for p in pieces:
        if len(current) + len(p) + 2 <= chunk_size:
            current = f'{current}\n\n{p}'.strip()
        else:
            if current:
                result.append(current)
            current = p
    if current:
        result.append(current)
    return result


def _apply_overlap(chunks, overlap):
    """Prepend the tail of each previous chunk to the next."""
    result = [chunks[0]]
    for i in range(1, len(chunks)):
        prev_tail = chunks[i - 1][-overlap:]
        # Try to start at a word boundary
        space_idx = prev_tail.find(' ')
        if space_idx > 0:
            prev_tail = prev_tail[space_idx + 1:]
        result.append(f'{prev_tail} {chunks[i]}'.strip())
    return result