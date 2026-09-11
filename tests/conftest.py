"""Integration tests run in an isolated `plantcare_test` database (same container), never the dev DB.
Created on first use from db/init/001_schema.sql; every test starts from empty tables."""
import psycopg
import pytest

from rag import db
from rag.config import ROOT, settings

SCHEMA = (ROOT / "db" / "init" / "001_schema.sql").read_text(encoding="utf-8")


def _test_url() -> str:
    url = settings()["DATABASE_URL"]
    assert not url.endswith("_test")
    return url.rsplit("/", 1)[0] + "/plantcare_test"


@pytest.fixture(scope="session")
def test_db_url():
    try:
        admin = psycopg.connect(settings()["DATABASE_URL"], autocommit=True)
    except psycopg.OperationalError:
        pytest.skip("database not reachable")
    if not admin.execute("SELECT 1 FROM pg_database WHERE datname='plantcare_test'").fetchone():
        admin.execute("CREATE DATABASE plantcare_test")
        with psycopg.connect(_test_url(), autocommit=True) as c:
            c.execute(SCHEMA)
    admin.close()
    return _test_url()


@pytest.fixture
def conn(test_db_url):
    c = psycopg.connect(test_db_url, autocommit=True)
    db.register(c)
    c.execute("TRUNCATE documents, chunks RESTART IDENTITY CASCADE")
    yield c
    c.close()
