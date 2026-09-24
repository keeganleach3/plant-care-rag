"""Answer synthesis from retrieved chunks. Citations are validated against the retrieved set; a bad one rejects the answer.

  uv run python -m rag.generate --sanity      # empty context → refused; seeded context → cited (needs claude -p or api key)
"""
import argparse
import json
import re
from dataclasses import dataclass

from rag import llm
from rag.config import PROMPTS
from rag.retrieve import Hit

REFUSAL = "I don't have information on that in my notes."
MAX_QUESTION = 500
MODEL, EFFORT = "claude-sonnet-5", "low"
_INLINE_CITATION = re.compile(r"\[([a-z0-9-]+#[a-z0-9-]+)\]")
SYSTEM = (PROMPTS / "answer.md").read_text(encoding="utf-8")
SCHEMA = json.loads((PROMPTS / "answer.schema.json").read_text(encoding="utf-8"))


class GenerationError(Exception):
    def __init__(self, kind: str, detail: str):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


@dataclass
class Answer:
    answer: str
    citations: list[str]
    refused: bool
    usage: dict
    model: str
    cost_usd: float


def build_user(question: str, hits: list[Hit]) -> str:
    passages = "\n\n".join(f'<passage chunk_id="{h.chunk_id}" genus="{h.genus}" topic="{h.topic}">\n{h.content}\n</passage>' for h in hits)
    return f"<passages>\n{passages}\n</passages>\n\n<question>{question}</question>"


def answer(question: str, hits: list[Hit], *, call=llm.call, model=MODEL, effort=EFFORT) -> Answer:
    if len(question) > MAX_QUESTION:
        raise ValueError(f"question exceeds {MAX_QUESTION} characters")
    result = call(SYSTEM, build_user(question, hits), SCHEMA, model=model, effort=effort)
    p = result.parsed
    citations = [c for c in p["citations"] if isinstance(c, str)]
    if p["refused"]:
        return Answer(REFUSAL, [], True, result.usage, result.model, result.cost_usd)
    allowed = {h.chunk_id for h in hits}
    # inline [chunk_id] markers too: a UI renders them, so a forged one would show as a source
    bad = [c for c in citations + _INLINE_CITATION.findall(p["answer"]) if c not in allowed]
    if bad:
        raise GenerationError("citation_invalid", f"cited chunk(s) not in retrieved set: {bad}")
    return Answer(p["answer"], citations, False, result.usage, result.model, result.cost_usd)


def _sanity():
    seeded = [Hit("general-acclimation#humidity-hold-100-percent-for-the-first-week",
                  "Starting humidity is always 100 percent. Hold 100 percent for at least a week, then open vents slowly.",
                  "Humidity", "general", "acclimation", 0.9)]
    a = answer("How humid should it be when I first pot up TC plantlets?", seeded)
    print("seeded  →", {"refused": a.refused, "citations": a.citations, "answer": a.answer[:120]})
    b = answer("How do I pollinate a Monstera flower?", seeded)
    print("offtopic→", {"refused": b.refused, "citations": b.citations, "answer": b.answer[:120]})
    c = answer("How humid should it be when I first pot up TC plantlets?", [])
    print("empty   →", {"refused": c.refused, "citations": c.citations, "answer": c.answer[:120]})


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--sanity", action="store_true")
    if ap.parse_args().sanity:
        _sanity()
