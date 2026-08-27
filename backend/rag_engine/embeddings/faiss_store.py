"""
faiss_store.py
Wraps a FAISS index for storing chunk embeddings and performing
context-aware semantic similarity search. Persists the index and
an id->metadata sidecar map to disk so it survives restarts.
"""

import os
import json
import logging
import pickle
from dataclasses import dataclass
from typing import List, Dict, Any, Optional

import faiss
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    metadata: Dict[str, Any]


class FAISSStore:
    """
    Flat inner-product FAISS index (cosine similarity, since embeddings are
    L2-normalized upstream). Swap IndexFlatIP for IndexIVFFlat/HNSW if the
    corpus grows beyond a few hundred thousand chunks.
    """

    def __init__(self, embedding_dim: int, index_path: str = "data/faiss_index"):
        self.embedding_dim = embedding_dim
        self.index_path = index_path
        self.index = faiss.IndexFlatIP(embedding_dim)

        # FAISS only stores vectors by integer position — keep our own
        # mapping from that position to chunk_id/text/metadata.
        self._id_map: Dict[int, Dict[str, Any]] = {}
        self._next_pos = 0

        os.makedirs(os.path.dirname(self.index_path) or ".", exist_ok=True)

    def add(self, chunk_ids: List[str], embeddings: np.ndarray, texts: List[str],
            metadatas: List[Dict[str, Any]]) -> None:
        """Add a batch of embeddings + their associated text/metadata to the index."""
        if len(chunk_ids) != embeddings.shape[0] or len(chunk_ids) != len(texts):
            raise ValueError("chunk_ids, embeddings, and texts must be the same length")

        self.index.add(embeddings)

        for i, chunk_id in enumerate(chunk_ids):
            self._id_map[self._next_pos] = {
                "chunk_id": chunk_id,
                "text": texts[i],
                "metadata": metadatas[i] if metadatas else {},
            }
            self._next_pos += 1

        logger.info("Added %d vectors to FAISS index (total=%d)", len(chunk_ids), self.index.ntotal)

    def search(self, query_embedding: np.ndarray, top_k: int = 5,
               filter_source_id: Optional[str] = None) -> List[SearchResult]:
        """
        Run a similarity search for a single query embedding.
        If filter_source_id is set, over-fetch and filter to results from that paper only.
        """
        if self.index.ntotal == 0:
            logger.warning("Search called on empty FAISS index")
            return []

        fetch_k = top_k * 4 if filter_source_id else top_k
        query_vec = query_embedding.reshape(1, -1)
        scores, positions = self.index.search(query_vec, min(fetch_k, self.index.ntotal))

        results = []
        for score, pos in zip(scores[0], positions[0]):
            if pos == -1:
                continue
            entry = self._id_map.get(int(pos))
            if entry is None:
                continue
            if filter_source_id and entry["metadata"].get("source_id") != filter_source_id:
                continue

            results.append(
                SearchResult(
                    chunk_id=entry["chunk_id"],
                    text=entry["text"],
                    score=float(score),
                    metadata=entry["metadata"],
                )
            )
            if len(results) >= top_k:
                break

        return results

    def save(self) -> None:
        """Persist the FAISS index and the id->metadata sidecar map to disk."""
        faiss.write_index(self.index, f"{self.index_path}.faiss")
        with open(f"{self.index_path}.meta.pkl", "wb") as f:
            pickle.dump({"id_map": self._id_map, "next_pos": self._next_pos}, f)
        logger.info("Saved FAISS index to %s.faiss", self.index_path)

    def load(self) -> bool:
        """Load a previously saved index. Returns True if a saved index was found."""
        faiss_file = f"{self.index_path}.faiss"
        meta_file = f"{self.index_path}.meta.pkl"

        if not (os.path.exists(faiss_file) and os.path.exists(meta_file)):
            logger.info("No existing FAISS index found at %s", self.index_path)
            return False

        self.index = faiss.read_index(faiss_file)
        with open(meta_file, "rb") as f:
            saved = pickle.load(f)
            self._id_map = saved["id_map"]
            self._next_pos = saved["next_pos"]

        logger.info("Loaded FAISS index with %d vectors", self.index.ntotal)
        return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    dim = 384
    store = FAISSStore(embedding_dim=dim, index_path="data/test_index")

    dummy_embeddings = np.random.rand(3, dim).astype("float32")
    faiss.normalize_L2(dummy_embeddings)

    store.add(
        chunk_ids=["c1", "c2", "c3"],
        embeddings=dummy_embeddings,
        texts=["chunk one text", "chunk two text", "chunk three text"],
        metadatas=[{"source_id": "paper-1"}] * 3,
    )
    results = store.search(dummy_embeddings[0], top_k=2)
    for r in results:
        print(r.chunk_id, r.score)