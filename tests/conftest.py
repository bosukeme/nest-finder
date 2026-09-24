import os

os.environ["DATABASE_URL"] = os.environ.get(
    "TEST_DATABASE_URL",
    "postgresql+psycopg://nestfinder:nestfinder@db:5432/nestfinder_test",
)

import pytest
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

from alembic import command
from app.db.session import engine
from app.main import app


def _ensure_test_db() -> None:
    url = make_url(os.environ["DATABASE_URL"])
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as conn:
        exists = conn.scalar(text("SELECT 1 FROM pg_database WHERE datname = :n"), {"n": url.database})
        if not exists:
            conn.execute(text(f'CREATE DATABASE "{url.database}"'))
    admin.dispose()


@pytest.fixture(scope="session", autouse=True)
def _migrate():
    _ensure_test_db()
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture(autouse=True)
def _clean_tables():
    with engine.begin() as conn:
        conn.execute(text("TRUNCATE listings RESTART IDENTITY"))


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def payload():
    return {
        "title": "2-bed apartment, GRA",
        "price": "1500000.00",
        "type": "rent",
        "bedrooms": 2,
        "location": {"lat": 4.8156, "lng": 7.0498},
        "agent_id": 1,
    }
