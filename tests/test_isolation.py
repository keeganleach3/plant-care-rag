"""The test fixtures must land on a *_test database, whatever the dev URL looks like (they TRUNCATE what they reach)."""
import pytest

from tests.conftest import _test_conninfo

URL = "postgresql://127.0.0.1:5432/plantcare?options=-c%20search_path%3Da/b"  # a '/' inside the query string


def test_only_the_database_name_is_swapped_even_with_a_slash_in_the_query():
    info = _test_conninfo(URL, "plantcare_test")
    assert "dbname=plantcare_test" in info and "search_path=a/b" in info and "dbname=plantcare " not in info


@pytest.mark.parametrize("name", ["plantcare", "evil", "plantcare_test; DROP"])
def test_a_name_that_is_not_a_test_database_is_refused(name):
    with pytest.raises(AssertionError):
        _test_conninfo(URL, name)
