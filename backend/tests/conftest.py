import os
import tempfile
from pathlib import Path
import pytest

_test_dir = tempfile.TemporaryDirectory(prefix="quantlab-tests-")
os.environ["DATABASE_URL"] = "sqlite:///" + str(Path(_test_dir.name) / "test.db")
os.environ["HELIUS_API_KEY"] = ""
os.environ["BIRDEYE_API_KEY"] = ""
os.environ["API_TOKEN"] = ""


@pytest.fixture(scope="session")
def migrated_database():
    from alembic.config import Config
    from alembic import command
    command.upgrade(Config("alembic.ini"), "head")


@pytest.fixture
def client(migrated_database):
    from fastapi.testclient import TestClient
    from app.main import app
    with TestClient(app) as c:
        yield c
