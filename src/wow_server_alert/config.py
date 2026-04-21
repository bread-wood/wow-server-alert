"""Config loading — YAML file with env var overrides."""

import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

load_dotenv()

_DEFAULTS: dict = {
    "blizzard": {
        "client_id": "",
        "client_secret": "",
        "region": "us",
        "locale": "en_US",
    },
    "monitor": {
        "realm_id": 0,
        "poll_interval_seconds": 60,
    },
    "telegram": {
        "bot_token": "",
        "chat_id": "",
    },
    "data_dir": "~/.wow-server-alert",
}


_WOW_AUCTION_CONFIG = Path(__file__).parents[4] / "wow-auction" / "config.yaml"


def _load_wow_auction_blizzard() -> dict:
    """Pull blizzard credentials from sibling wow-auction repo if available."""
    if not _WOW_AUCTION_CONFIG.exists():
        return {}
    with open(_WOW_AUCTION_CONFIG) as f:
        data = yaml.safe_load(f) or {}
    b = data.get("blizzard", {})
    return {k: b[k] for k in ("client_id", "client_secret", "region") if b.get(k)}


def load_config(path: str = "config.yaml") -> dict:
    """
    Load config from YAML, then apply env var overrides.
    Blizzard credentials fall back to ../wow-auction/config.yaml if not set locally.
    Env vars: BLIZZARD_CLIENT_ID, BLIZZARD_CLIENT_SECRET,
              TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
    """
    cfg = _deep_merge(_DEFAULTS, {})

    # Pull blizzard credentials from wow-auction first; local config can override
    cfg = _deep_merge(cfg, {"blizzard": _load_wow_auction_blizzard()})

    if Path(path).exists():
        with open(path) as f:
            file_cfg = yaml.safe_load(f) or {}
        cfg = _deep_merge(cfg, file_cfg)

    # Env overrides
    if v := os.getenv("BLIZZARD_CLIENT_ID"):
        cfg["blizzard"]["client_id"] = v
    if v := os.getenv("BLIZZARD_CLIENT_SECRET"):
        cfg["blizzard"]["client_secret"] = v
    if v := os.getenv("TELEGRAM_BOT_TOKEN"):
        cfg["telegram"]["bot_token"] = v
    if v := os.getenv("TELEGRAM_CHAT_ID"):
        cfg["telegram"]["chat_id"] = v

    cfg["data_dir"] = str(Path(cfg["data_dir"]).expanduser())
    return cfg


def db_path(cfg: dict) -> str:
    return str(Path(cfg["data_dir"]) / "monitor.db")


def _deep_merge(base: dict, override: dict) -> dict:
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = _deep_merge(result[k], v)
        else:
            result[k] = v
    return result
