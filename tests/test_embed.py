from rag.embed import Embedder


class FakeModel:
    def __init__(self):
        self.seen = []

    def encode(self, texts, **kw):
        """Bag-of-characters vector: similar text → similar direction, so ordering tests are meaningful."""
        self.seen.extend(texts)
        out = []
        for t in texts:
            v = [0.0] * 768
            for ch in t.lower():
                v[ord(ch) % 768] += 1.0
            n = sum(x * x for x in v) ** 0.5 or 1.0
            out.append([x / n for x in v])
        return out


def test_query_and_doc_prefixes_come_from_model_config():
    fake = FakeModel()
    e = Embedder("nomic-ai/nomic-embed-text-v1.5", model=fake)
    e.embed_query("how humid")
    e.embed_docs(["hold 95%", "drop to 80%"])
    assert fake.seen == ["search_query: how humid", "search_document: hold 95%", "search_document: drop to 80%"]


def test_bge_query_prefix_only():
    fake = FakeModel()
    e = Embedder("BAAI/bge-base-en-v1.5", model=fake)
    e.embed_query("q")
    e.embed_docs(["d"])
    assert fake.seen == ["Represent this sentence for searching relevant passages: q", "d"]


def test_returns_768_dim_vectors():
    e = Embedder("BAAI/bge-base-en-v1.5", model=FakeModel())
    assert len(e.embed_query("q")) == 768
    assert [len(v) for v in e.embed_docs(["a", "bb"])] == [768, 768]
