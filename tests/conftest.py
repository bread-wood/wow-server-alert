import pytest
import tempfile
import os

from wow_server_alert import store


@pytest.fixture
def tmp_db(tmp_path):
    db = str(tmp_path / "test.db")
    store.init_db(db)
    return db


@pytest.fixture(autouse=True)
def no_env_vars(monkeypatch):
    """Clear credential env vars so tests don't accidentally use real keys."""
    for var in ("BLIZZARD_CLIENT_ID", "BLIZZARD_CLIENT_SECRET", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID"):
        monkeypatch.delenv(var, raising=False)
