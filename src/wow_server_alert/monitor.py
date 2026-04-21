"""Realm status polling loop."""

import asyncio
import logging
import time

from wow_server_alert import store
from wow_server_alert.blizzard import BlizzardClient
from wow_server_alert.telegram import TelegramClient

log = logging.getLogger(__name__)


def _fmt_duration(seconds: float) -> str:
    seconds = int(seconds)
    h, m = divmod(seconds // 60, 60)
    s = seconds % 60
    if h:
        return f"{h}h {m}m"
    if m:
        return f"{m}m {s}s"
    return f"{s}s"


async def watch(
    blizzard: BlizzardClient,
    telegram: TelegramClient,
    db_path: str,
    realm_id: int,
    interval: int,
) -> None:
    """Poll realm status indefinitely. Sends Telegram alerts on UP/DOWN transitions."""
    log.info("Monitoring realm %d — polling every %ds", realm_id, interval)

    while True:
        try:
            realm = await blizzard.get_realm_status(realm_id)
            status: str = realm["status"]
            name: str = realm["name"]
            has_queue: bool = realm["has_queue"]

            row = store.get_realm(db_path, realm_id)

            if row is None:
                store.upsert_realm(db_path, realm_id, name, status)
                log.info("Realm %s: %s (initial state)", name, status)
            elif row["last_status"] != status:
                now = time.time()

                if status == "UP" and row["last_status"] == "DOWN":
                    down_for = _fmt_duration(now - row["last_changed"])
                    queue_note = " (queue active)" if has_queue else ""
                    msg = f"WoW servers are UP{queue_note}\nRealm: {name}\nDown for: {down_for}"
                    await telegram.send(msg)
                    store.upsert_realm(db_path, realm_id, name, status, notified_at=now)
                    log.info("Alert sent: %s is UP (was down %s)", name, down_for)

                elif status == "DOWN" and row["last_status"] == "UP":
                    msg = f"WoW servers are DOWN\nRealm: {name}\nMaintenance in progress."
                    await telegram.send(msg)
                    store.upsert_realm(db_path, realm_id, name, status, notified_at=now)
                    log.info("Alert sent: %s is DOWN", name)

                else:
                    store.upsert_realm(db_path, realm_id, name, status)
                    log.info("Realm %s status changed: %s -> %s", name, row["last_status"], status)
            else:
                log.debug("Realm %s: %s (no change)", name, status)

        except Exception as exc:
            log.error("Poll error: %s", exc)

        await asyncio.sleep(interval)
