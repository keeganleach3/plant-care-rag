"""The .env reader: a quoted value is taken whole ('#' included); an unquoted one ends at a ' #' comment."""
from rag import config


def test_env_values_keep_hash_signs_unless_a_comment_starts(tmp_path):
    env = tmp_path / ".env"
    env.write_text('A="abc#def"   # comment\nB=abc#def\nC=cc            # cc = default\nD=\'x y\'\nE=\n# F=skipped\n'
                   'G=        # only a comment, as in .env.example\n', encoding="utf-8")
    assert config._parse_env(env) == {"A": "abc#def", "B": "abc#def", "C": "cc", "D": "x y", "E": "", "G": ""}
