"""Telegram Bot API — send text messages."""

import logging

import httpx

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org/bot{token}/sendMessage"


class TelegramClient:
    def __init__(self, token: str, chat_id: str):
        self.token = token
        self.chat_id = chat_id

    async def send(self, text: str) -> None:
        """Send a plain-text message. Raises on HTTP or Telegram API error."""
        url = TELEGRAM_API.format(token=self.token)
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                url,
                json={"chat_id": self.chat_id, "text": text},
                timeout=10,
            )
        resp.raise_for_status()
        body = resp.json()
        if not body.get("ok"):
            raise RuntimeError(f"Telegram error: {body.get('description')}")
        log.debug("Telegram message sent to %s", self.chat_id)
