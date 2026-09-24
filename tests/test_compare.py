"""Blind pairwise comparison summary (pure)."""
from eval import compare as C


def rows(wins_a, wins_b):
    return [{"id": f"q{i}", "winner": "a"} for i in range(wins_a)] + [{"id": f"r{i}", "winner": "b"} for i in range(wins_b)]


def test_sign_test_is_exact_and_two_sided():
    assert round(C.sign_test(12, 14), 4) == 0.0129
    assert C.sign_test(7, 14) == 1.0


def test_summary_counts_wins_and_ties():
    s = C.summary(rows(12, 2) + [{"id": "t", "winner": "tie"}], "a", "b")
    assert (s["a"], s["b"], s["tie"], s["p"]) == (12, 2, 1, round(C.sign_test(12, 14), 4))
