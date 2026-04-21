import asyncio
import time
import pytest
from unittest.mock import AsyncMock, MagicMock

from wow_server_alert import store
from wow_server_alert.monitor import watch, _fmt_duration


# --- _fmt_duration ---

def test_fmt_duration_seconds():
    assert _fmt_duration(45) == "45s"


def test_fmt_duration_minutes():
    assert _fmt_duration(125) == "2m 5s"


def test_fmt_duration_hours():
    assert _fmt_duration(7500) == "2h 5m"


# --- watch loop ---

def _make_blizzard(status: str, name: str = "Stormrage") -> MagicMock:
    b = AsyncMock()
    b.get_realm_status.return_value = {"status": status, "name": name, "has_queue": False}
    return b


def _make_telegram() -> MagicMock:
    t = AsyncMock()
    return t


async def _run_one_tick(blizzard, telegram, db_path):
    """Run the watch loop for exactly one iteration then cancel."""
    task = asyncio.create_task(watch(blizzard, telegram, db_path, realm_id=96, interval=0))
    await asyncio.sleep(0.05)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass


async def test_initial_state_no_alert(tmp_db):
    blizzard = _make_blizzard("UP")
    telegram = _make_telegram()

    await _run_one_tick(blizzard, telegram, tmp_db)

    telegram.send.assert_not_called()
    row = store.get_realm(tmp_db, 96)
    assert row["last_status"] == "UP"


async def test_down_to_up_sends_alert(tmp_db):
    store.upsert_realm(tmp_db, 96, "Stormrage", "DOWN")
    # Backdate last_changed so duration is non-zero
    import sqlite3
    conn = sqlite3.connect(tmp_db)
    conn.execute("UPDATE realm_watch SET last_changed = ? WHERE realm_id = 96", (time.time() - 3600,))
    conn.commit()
    conn.close()

    blizzard = _make_blizzard("UP")
    telegram = _make_telegram()

    await _run_one_tick(blizzard, telegram, tmp_db)

    telegram.send.assert_called_once()
    msg = telegram.send.call_args[0][0]
    assert "UP" in msg
    assert "Stormrage" in msg


async def test_up_to_down_sends_alert(tmp_db):
    store.upsert_realm(tmp_db, 96, "Stormrage", "UP")

    blizzard = _make_blizzard("DOWN")
    telegram = _make_telegram()

    await _run_one_tick(blizzard, telegram, tmp_db)

    telegram.send.assert_called_once()
    msg = telegram.send.call_args[0][0]
    assert "DOWN" in msg


async def test_no_change_no_alert(tmp_db):
    store.upsert_realm(tmp_db, 96, "Stormrage", "UP")

    blizzard = _make_blizzard("UP")
    telegram = _make_telegram()

    await _run_one_tick(blizzard, telegram, tmp_db)

    telegram.send.assert_not_called()


async def test_poll_error_does_not_crash(tmp_db):
    blizzard = AsyncMock()
    blizzard.get_realm_status.side_effect = Exception("network error")
    telegram = _make_telegram()

    # Should complete without raising
    await _run_one_tick(blizzard, telegram, tmp_db)
    telegram.send.assert_not_called()
