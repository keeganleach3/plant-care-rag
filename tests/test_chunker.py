import pytest

from rag.chunker import CAP, DocError, chunk, parse

HEAD = "---\ntitle: Monstera humidity step-down\ngenus: monstera\ntopic: humidity\nverified: true\n---\n"


def write(tmp_path, body, name="monstera-humidity.md", head=HEAD):
    p = tmp_path / name
    p.write_text(head + body, encoding="utf-8")
    return p


def test_parse_reads_frontmatter_and_h2_sections(tmp_path):
    doc = parse(write(tmp_path, "\n## Starting humidity\n\nHold 95%.\n\n## Week two\n\nDrop to 80%.\n"))
    assert doc.slug == "monstera-humidity"
    assert doc.genus == "monstera" and doc.topic == "humidity" and doc.title == "Monstera humidity step-down"
    assert [s.heading for s in doc.sections] == ["Starting humidity", "Week two"]
    assert doc.sections[1].body == "Drop to 80%."


def test_chunk_ids_are_stable_slugs(tmp_path):
    p = write(tmp_path, "\n## Starting humidity (day 0-7)\n\nHold 95%.\n")
    a = chunk(parse(p))
    b = chunk(parse(p))
    assert [c.chunk_id for c in a] == ["monstera-humidity#starting-humidity-day-0-7"]
    assert [c.chunk_id for c in a] == [c.chunk_id for c in b]
    assert a[0].genus == "monstera" and a[0].topic == "humidity" and a[0].heading == "Starting humidity (day 0-7)"


def test_long_section_splits_at_paragraphs_under_cap(tmp_path):
    paras = [f"Paragraph {i}. " + ("x" * 500) for i in range(6)]  # ~3,100 chars, 6 paragraphs
    chunks = chunk(parse(write(tmp_path, "\n## Big section\n\n" + "\n\n".join(paras) + "\n")))
    assert [c.chunk_id for c in chunks] == ["monstera-humidity#big-section", "monstera-humidity#big-section-2"]
    assert all(len(c.content) <= CAP for c in chunks)
    assert all(c.content.startswith("Paragraph") for c in chunks)  # split only on blank lines
    assert "".join(c.content for c in chunks).count("Paragraph") == 6


def test_unverified_doc_is_rejected(tmp_path):
    p = write(tmp_path, "\n## A\n\nB.\n", head=HEAD.replace("verified: true", "verified: false"))
    with pytest.raises(DocError, match="verified"):
        parse(p)


def test_confirm_marker_is_rejected(tmp_path):
    with pytest.raises(DocError, match="CONFIRM"):
        parse(write(tmp_path, "\n## A\n\nDip for 10 min [CONFIRM].\n"))


def test_unknown_genus_is_rejected(tmp_path):
    p = write(tmp_path, "\n## A\n\nB.\n", head=HEAD.replace("genus: monstera", "genus: hoya"))
    with pytest.raises(DocError, match="genus"):
        parse(p)


def test_text_before_first_h2_is_ignored_and_empty_sections_dropped(tmp_path):
    doc = parse(write(tmp_path, "\nIntro text.\n\n## Real\n\nContent.\n\n## Empty\n\n"))
    assert [s.heading for s in doc.sections] == ["Real"]


def test_title_with_colon_parses(tmp_path):
    head = HEAD.replace("title: Monstera humidity step-down", "title: Alocasia from TC: slower step-down, leaf drop")
    doc = parse(write(tmp_path, "\n## A\n\nB.\n", head=head))
    assert doc.title == "Alocasia from TC: slower step-down, leaf drop"


def test_malformed_frontmatter_is_a_docerror_not_a_crash(tmp_path):
    with pytest.raises(DocError):
        parse(write(tmp_path, "\n## A\n\nB.\n", head="---\ntitle\ngenus: monstera\ntopic: humidity\nverified: true\n---\n"))
