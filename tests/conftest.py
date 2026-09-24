"""Integration tests run in an isolated test database (same container), never the dev DB.
TEST_DB names it (default plantcare_test) so parallel sessions never share tables. Every db/init/*.sql is applied
each session (the files are idempotent), and every test starts from empty tables."""
import os
import re

import psycopg
import pytest
from psycopg import sql
from psycopg.conninfo import conninfo_to_dict, make_conninfo

from rag import db
from rag.config import ROOT, settings

MIGRATIONS = sorted((ROOT / "db" / "init").glob("*.sql"))
NAME = os.environ.get("TEST_DB", "plantcare_test")


def _test_conninfo(url: str, name: str = NAME) -> str:
    """The dev URL with only the database swapped (never string surgery on the URL: a '/' in its query string would
    leave the dev database in place), refused unless it lands on a plantcare_test* database."""
    assert re.fullmatch(r"plantcare_test\w*", name), name
    info = make_conninfo(url, dbname=name)
    assert conninfo_to_dict(info)["dbname"] == name != conninfo_to_dict(url).get("dbname"), (url, name)
    return info


@pytest.fixture(scope="session")
def test_db_url():
    url = _test_conninfo(settings()["DATABASE_URL"])
    try:
        admin = psycopg.connect(settings()["DATABASE_URL"], autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("database not reachable")
    if not admin.execute("SELECT 1 FROM pg_database WHERE datname = %s", (NAME,)).fetchone():
        admin.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(NAME)))
    admin.close()
    with psycopg.connect(url, autocommit=True) as c:
        for m in MIGRATIONS:
            c.execute(m.read_text(encoding="utf-8"))
    return url


@pytest.fixture
def conn(test_db_url):
    c = psycopg.connect(test_db_url, autocommit=True)
    db.register(c)
    c.execute("TRUNCATE documents, chunks RESTART IDENTITY CASCADE")
    yield c
    c.close()
