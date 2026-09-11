"""Embedding wrapper. Loads the sentence-transformers model once; prefixes come from EMBED_MODELS so a
model swap cannot silently drop the query/document asymmetry."""
from rag.config import EMBED_MODELS


class Embedder:
    def __init__(self, name: str, model=None):
        self.name = name
        self.cfg = EMBED_MODELS[name]
        if model is None:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer(name, device="cpu", trust_remote_code=self.cfg["trust_remote_code"])
        self.model = model

    def _encode(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self.model.encode(texts, normalize_embeddings=True, batch_size=32)]

    def embed_query(self, text: str) -> list[float]:
        return self._encode([self.cfg["query_prefix"] + text])[0]

    def embed_docs(self, texts: list[str]) -> list[list[float]]:
        return self._encode([self.cfg["doc_prefix"] + t for t in texts])
