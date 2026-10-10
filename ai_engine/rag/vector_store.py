"""
FAISS vector store with metadata persistence.

Stores embeddings in a FAISS index and metadata in JSON.
Supports incremental add, full rebuild, and search with metadata filtering.
"""
import json
import logging
import threading
from pathlib import Path
from typing import List, Optional, Tuple

import numpy as np
import faiss

from django.conf import settings

from .embeddings import embed_text, EMBED_DIM

logger = logging.getLogger(__name__)

_lock = threading.Lock()


class VectorStore:
    """Singleton per-directory FAISS store."""

    def __init__(self, store_dir: Path = None):
        self.store_dir = Path(store_dir or self._default_dir())
        self.store_dir.mkdir(parents=True, exist_ok=True)

        self.index_path = self.store_dir / 'index.faiss'
        self.metadata_path = self.store_dir / 'metadata.json'

        self._index: Optional[faiss.Index] = None
        self._metadata: List[dict] = []

    @staticmethod
    def _default_dir() -> Path:
        base = getattr(settings, 'BASE_DIR', Path.cwd())
        return Path(base) / 'ai_engine' / 'vector_store_data' / 'faiss'

    # ================================================================
    # Persistence
    # ================================================================
    def load(self):
        """Load index + metadata from disk. Idempotent."""
        with _lock:
            if self._index is not None:
                return

            if self.index_path.exists() and self.metadata_path.exists():
                try:
                    self._index = faiss.read_index(str(self.index_path))

                    with open(
                        self.metadata_path,
                        'r',
                        encoding='utf-8',
                    ) as f:
                        self._metadata = json.load(f)

                    logger.info(
                        f'Loaded FAISS index: {self._index.ntotal} vectors'
                    )

                except Exception as e:
                    logger.exception(
                        f'Failed to load FAISS index: {e}'
                    )
                    self._index = None
                    self._metadata = []

            if self._index is None:
                self._index = faiss.IndexFlatIP(EMBED_DIM)
                self._metadata = []

    def save(self):
        """Persist to disk."""
        with _lock:
            if self._index is None:
                return

            faiss.write_index(
                self._index,
                str(self.index_path),
            )

            with open(
                self.metadata_path,
                'w',
                encoding='utf-8',
            ) as f:
                json.dump(
                    self._metadata,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            logger.info(
                f'Saved FAISS index: {self._index.ntotal} vectors'
            )

    def clear(self):
        """Wipe the store."""
        with _lock:
            self._index = faiss.IndexFlatIP(EMBED_DIM)
            self._metadata = []

            if self.index_path.exists():
                self.index_path.unlink()

            if self.metadata_path.exists():
                self.metadata_path.unlink()

    # ================================================================
    # Add / search
    # ================================================================
    def add(
        self,
        chunks: List,
        embeddings: List[Tuple[List[float], str]],
    ):
        """
        Add chunks + embeddings. chunks are splitter.Chunk instances.
        """
        self.load()

        if not chunks:
            return

        vectors = []

        for i, (emb, _) in enumerate(embeddings):
            v = np.array(
                emb,
                dtype='float32',
            )

            norm = np.linalg.norm(v)

            if norm > 0:
                v = v / norm

            vectors.append(v)

        mat = np.vstack(vectors)

        with _lock:
            self._index.add(mat)

            for c in chunks:
                self._metadata.append({
                    'text': c.text,
                    'metadata': c.metadata,
                })

    def search(
        self,
        query: str,
        top_k: int = 20,
    ) -> List[dict]:
        """Search the store. Returns list of {text, metadata, score}."""
        self.load()

        if self._index is None or self._index.ntotal == 0:
            return []

        q_emb, _ = embed_text(query)

        q = np.array(
            [q_emb],
            dtype='float32',
        )

        norm = np.linalg.norm(q)

        if norm > 0:
            q = q / norm

        scores, indices = self._index.search(
            q,
            min(top_k, self._index.ntotal),
        )

        results = []

        for score, idx in zip(
            scores[0],
            indices[0],
        ):
            if idx < 0 or idx >= len(self._metadata):
                continue

            item = self._metadata[idx]

            results.append({
                'text': item['text'],
                'metadata': item.get('metadata', {}),
                'score': float(score),
            })

        return results

    def __len__(self):
        self.load()
        return self._index.ntotal if self._index else 0


# =====================================================================
# Module-level singleton
# =====================================================================
_store: Optional[VectorStore] = None


def get_vector_store() -> VectorStore:
    global _store

    if _store is None:
        _store = VectorStore()

    return _store