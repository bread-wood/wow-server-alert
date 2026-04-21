"""CLI entry points."""

import asyncio
import logging
import sys

import click

from wow_server_alert import store
from wow_server_alert.blizzard import BlizzardClient
from wow_server_alert.config import db_path, load_config
from wow_server_alert.monitor import watch
from wow_server_alert.telegram import TelegramClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)


def _blizzard(cfg: dict) -> BlizzardClient:
    b = cfg["blizzard"]
    if not b["client_id"] or not b["client_secret"]:
        click.echo("Error: Blizzard client_id and client_secret are required.", err=True)
        sys.exit(1)
    return BlizzardClient(b["client_id"], b["client_secret"], b["region"], b["locale"])


def _telegram(cfg: dict) -> TelegramClient:
    t = cfg["telegram"]
    if not t["bot_token"] or not t["chat_id"]:
        click.echo("Error: Telegram bot_token and chat_id are required.", err=True)
        sys.exit(1)
    return TelegramClient(t["bot_token"], t["chat_id"])


@click.group()
@click.option("--config", default="config.yaml", show_default=True, help="Path to config.yaml")
@click.pass_context
def main(ctx: click.Context, config: str) -> None:
    ctx.ensure_object(dict)
    ctx.obj["cfg"] = load_config(config)


@main.command()
@click.option("--realm-id", type=int, default=None, help="Override realm ID from config")
@click.option("--interval", type=int, default=None, help="Override poll interval (seconds)")
@click.pass_context
def watch_cmd(ctx: click.Context, realm_id: int | None, interval: int | None) -> None:
    """Start polling WoW realm status and send Telegram alerts on transitions."""
    cfg = ctx.obj["cfg"]
    rid = realm_id or cfg["monitor"]["realm_id"]
    ivl = interval or cfg["monitor"]["poll_interval_seconds"]

    if not rid:
        click.echo("Error: realm_id is required. Use --realm-id or set monitor.realm_id in config.", err=True)
        sys.exit(1)

    blizzard = _blizzard(cfg)
    telegram = _telegram(cfg)
    dp = db_path(cfg)
    store.init_db(dp)

    asyncio.run(watch(blizzard, telegram, dp, rid, ivl))


@main.command()
@click.option("--realm-id", type=int, default=None, help="Override realm ID from config")
@click.pass_context
def status(ctx: click.Context, realm_id: int | None) -> None:
    """Check current status of a realm."""
    cfg = ctx.obj["cfg"]
    rid = realm_id or cfg["monitor"]["realm_id"]

    if not rid:
        click.echo("Error: realm_id is required.", err=True)
        sys.exit(1)

    blizzard = _blizzard(cfg)

    async def _run() -> None:
        realm = await blizzard.get_realm_status(rid)
        queue = " (queue active)" if realm["has_queue"] else ""
        click.echo(f"{realm['name']}: {realm['status']}{queue}")

    asyncio.run(_run())


@main.command()
@click.argument("query")
@click.pass_context
def realms(ctx: click.Context, query: str) -> None:
    """Search realm names to find connected realm IDs."""
    cfg = ctx.obj["cfg"]
    blizzard = _blizzard(cfg)

    async def _run() -> None:
        results = await blizzard.search_realms(query)
        if not results:
            click.echo(f"No realms found matching '{query}'")
            return
        click.echo(f"{'Name':<30} {'Slug':<30} {'Connected Realm ID'}")
        click.echo("-" * 70)
        for r in results:
            click.echo(f"{r['name']:<30} {r['slug']:<30} {r['connected_realm_id']}")

    asyncio.run(_run())


# Register the watch command under its natural name
main.add_command(watch_cmd, name="watch")
