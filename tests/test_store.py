import time

from wow_server_alert import store


def test_get_realm_missing(tmp_db):
    assert store.get_realm(tmp_db, 999) is None


def test_upsert_and_get(tmp_db):
    store.upsert_realm(tmp_db, 1, "Stormrage", "UP")
    row = store.get_realm(tmp_db, 1)
    assert row["realm_name"] == "Stormrage"
    assert row["last_status"] == "UP"
    assert row["notified_at"] is None


def test_upsert_status_change_updates_last_changed(tmp_db):
    store.upsert_realm(tmp_db, 1, "Stormrage", "UP")
    row_before = store.get_realm(tmp_db, 1)

    time.sleep(0.01)
    store.upsert_realm(tmp_db, 1, "Stormrage", "DOWN")
    row_after = store.get_realm(tmp_db, 1)

    assert row_after["last_status"] == "DOWN"
    assert row_after["last_changed"] > row_before["last_changed"]


def test_upsert_same_status_preserves_last_changed(tmp_db):
    store.upsert_realm(tmp_db, 1, "Stormrage", "UP")
    row_before = store.get_realm(tmp_db, 1)

    time.sleep(0.01)
    store.upsert_realm(tmp_db, 1, "Stormrage", "UP")
    row_after = store.get_realm(tmp_db, 1)

    assert row_after["last_changed"] == row_before["last_changed"]


def test_upsert_notified_at(tmp_db):
    now = time.time()
    store.upsert_realm(tmp_db, 1, "Stormrage", "UP", notified_at=now)
    row = store.get_realm(tmp_db, 1)
    assert abs(row["notified_at"] - now) < 0.01
