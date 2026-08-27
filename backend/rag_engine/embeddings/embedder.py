"""
embedder.py
Generates vector embeddings for text chunks using a local sentence-transformers
model (free, no external API needed for embeddings — Groq is used for
generation only, not embeddings).
"""

import logging
from typing import List

import numpy as np
from sentence_transformers import SentenceTransformer

logger = logging.getLogger(__name__)

DEFAULT_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder:
    """Wraps a sentence-transformers model to produce embeddings for text chunks."""

    def __init__(self, model_name: str = DEFAULT_MODEL_NAME, device: str = "cpu"):
        logger.info("Loading embedding model: %s", model_name)
        self.model_name = model_name
        self.model = SentenceTransformer(model_name, device=device)
        self.embedding_dim = self.model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: List[str], batch_size: int = 32) -> np.ndarray:
        """Embed a list of raw text strings. Returns a (N, embedding_dim) float32 array."""
        if not texts:
            return np.empty((0, self.embedding_dim), dtype="float32")

        embeddings = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=False,
            normalize_embeddings=True,  # cosine similarity via dot product
            convert_to_numpy=True,
        )
        return embeddings.astype("float32")

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single search query. Returns a (embedding_dim,) float32 vector."""
        embedding = self.model.encode(
            [query],
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return embedding[0].astype("float32")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    embedder = Embedder()
    vectors = embedder.embed_texts(
        ["Retrieval-augmented generation grounds LLMs in external documents."]
    )
    print(f"Embedding shape: {vectors.shape}, dim={embedder.embedding_dim}")