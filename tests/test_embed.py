import threading
import time

from rag.config import ROOT, EMBED_MODELS
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


class SlowFakeModel:
    """Records overlapping encode() calls so a missing lock shows up as max_active > 1."""

    def __init__(self):
        self.active = 0
        self.max_active = 0
        self._guard = threading.Lock()

    def encode(self, texts, **kw):
        with self._guard:
            self.active += 1
            self.max_active = max(self.max_active, self.active)
        time.sleep(0.05)
        with self._guard:
            self.active -= 1
        return [[0.0] * 768 for _ in texts]


def test_encode_serializes_across_threads():
    fake = SlowFakeModel()
    e = Embedder("BAAI/bge-base-en-v1.5", model=fake)
    threads = [threading.Thread(target=e.embed_query, args=(f"q{i}",)) for i in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert fake.max_active == 1


def test_embedder_passes_pinned_revision(monkeypatch):
    calls = []

    class FakeCtor:
        def __init__(self, name, **kw):
            calls.append((name, kw))

        def encode(self, texts, **kw):
            return [[0.0] * 768 for _ in texts]

    monkeypatch.setattr("sentence_transformers.SentenceTransformer", FakeCtor)
    Embedder("BAAI/bge-base-en-v1.5")
    assert calls == [(
        "BAAI/bge-base-en-v1.5",
        {"device": "cpu", "trust_remote_code": False, "revision": EMBED_MODELS["BAAI/bge-base-en-v1.5"]["revision"]},
    )]


def test_dockerfile_pins_bge_revision():
    dockerfile = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    revision = EMBED_MODELS["BAAI/bge-base-en-v1.5"]["revision"]
    assert revision in dockerfile
