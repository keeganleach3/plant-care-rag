"""Corpus markdown → chunks. One H2 = one chunk (split at blank lines if over CAP). Pure; no DB, no model."""
import re
from dataclasses import dataclass
from pathlib import Path

from rag.config import GENERA, TOPICS

CAP = 1800  # chars (~400 tokens); contract: H2 body cap 2,000 chars after split
_REQUIRED = ("title", "genus", "topic", "verified")


class DocError(Exception):
    pass


@dataclass
class Section:
    heading: str
    body: str


@dataclass
class Doc:
    slug: str
    title: str
    genus: str
    topic: str
    source_path: str
    sections: list[Section]


@dataclass
class Chunk:
    chunk_id: str
    doc_slug: str
    genus: str
    topic: str
    heading: str
    content: str


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def _frontmatter(path: Path, block: str) -> dict:
    """Flat `key: value` lines only (titles may contain colons; values are never quoted or nested)."""
    meta = {}
    for line in block.splitlines():
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        key, sep, value = line.partition(":")
        if not sep or not key.strip():
            raise DocError(f"{path.name}: malformed frontmatter line {line!r}")
        meta[key.strip()] = value.split("  #")[0].strip()
    return meta


def parse(path: Path) -> Doc:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"^---\n(.*?)\n---\n", text, re.S)
    if not m:
        raise DocError(f"{path.name}: missing frontmatter")
    meta = _frontmatter(path, m.group(1))
    for key in _REQUIRED:
        if key not in meta:
            raise DocError(f"{path.name}: frontmatter missing {key}")
    if meta["verified"] != "true":
        raise DocError(f"{path.name}: not verified")
    if meta["genus"] not in GENERA:
        raise DocError(f"{path.name}: unknown genus {meta['genus']!r}")
    if meta["topic"] not in TOPICS:
        raise DocError(f"{path.name}: unknown topic {meta['topic']!r}")
    body = text[m.end():]
    if "[CONFIRM]" in body:
        raise DocError(f"{path.name}: unresolved [CONFIRM] marker")
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)
    sections = []
    for part in re.split(r"^## ", body, flags=re.M)[1:]:
        heading, _, rest = part.partition("\n")
        rest = rest.strip()
        if rest:
            sections.append(Section(heading.strip(), rest))
    return Doc(slugify(path.stem), str(meta["title"]), meta["genus"], meta["topic"], str(path), sections)


def _split(body: str) -> list[str]:
    parts, cur = [], ""
    for para in re.split(r"\n\s*\n", body):
        cand = f"{cur}\n\n{para}" if cur else para
        if cur and len(cand) > CAP:
            parts.append(cur)
            cur = para
        else:
            cur = cand
    parts.append(cur)
    return parts


def chunk(doc: Doc) -> list[Chunk]:
    out = []
    for s in doc.sections:
        base = f"{doc.slug}#{slugify(s.heading)}"
        for i, content in enumerate(_split(s.body), 1):
            cid = base if i == 1 else f"{base}-{i}"
            out.append(Chunk(cid, doc.slug, doc.genus, doc.topic, s.heading, content))
    return out
