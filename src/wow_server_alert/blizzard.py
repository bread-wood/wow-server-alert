"""
Blizzard Battle.net API client — realm status only.

Endpoints:
  POST https://oauth.battle.net/token
  GET  https://{region}.api.blizzard.com/data/wow/connected-realm/{id}
  GET  https://{region}.api.blizzard.com/data/wow/realm/index
"""

import re
import time
import logging

import httpx

log = logging.getLogger(__name__)

BNET_AUTH_URL = "https://oauth.battle.net/token"
BNET_API_BASE = "https://{region}.api.blizzard.com"


class BlizzardClient:
    def __init__(self, client_id: str, client_secret: str, region: str = "us", locale: str = "en_US"):
        self.client_id = client_id
        self.client_secret = client_secret
        self.region = region.lower()
        self.locale = locale
        self._token: str | None = None
        self._token_expires: float = 0

    @property
    def _api_base(self) -> str:
        return BNET_API_BASE.format(region=self.region)

    async def authenticate(self) -> None:
        """Fetch or refresh OAuth2 client-credentials token."""
        if self._token and time.time() < self._token_expires - 60:
            return
        async with httpx.AsyncClient() as client:
            resp = await client.post(
                BNET_AUTH_URL,
                data={"grant_type": "client_credentials"},
                auth=(self.client_id, self.client_secret),
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
        self._token = data["access_token"]
        self._token_expires = time.time() + data["expires_in"]
        log.debug("Blizzard token refreshed, expires in %ds", data["expires_in"])

    async def _get(self, path: str, params: dict | None = None) -> dict:
        await self.authenticate()
        async with httpx.AsyncClient() as client:
            resp = await client.get(
                f"{self._api_base}{path}",
                headers={"Authorization": f"Bearer {self._token}"},
                params=params or {},
                timeout=15,
            )
        resp.raise_for_status()
        return resp.json()

    async def get_realm_status(self, realm_id: int) -> dict:
        """
        Returns {"status": "UP"|"DOWN", "name": str, "has_queue": bool}.
        Raises httpx.HTTPStatusError on API failure.
        """
        namespace = f"dynamic-{self.region}"
        data = await self._get(
            f"/data/wow/connected-realm/{realm_id}",
            params={"namespace": namespace, "locale": self.locale},
        )
        realms = data.get("realms", [])
        name = realms[0]["name"] if realms else str(realm_id)
        return {
            "status": data.get("status", {}).get("type", "UNKNOWN"),
            "name": name,
            "has_queue": data.get("has_queue", False),
        }

    async def search_realms(self, query: str) -> list[dict]:
        """
        Search realm names. Returns list of {"name": str, "slug": str, "connected_realm_id": int}.
        Uses the realm index — filters client-side by query.
        """
        namespace = f"dynamic-{self.region}"
        data = await self._get(
            "/data/wow/realm/index",
            params={"namespace": namespace, "locale": self.locale},
        )
        realms = data.get("realms", [])
        query_lower = query.lower()
        results = []
        for r in realms:
            name = r.get("name", "")
            slug = r.get("slug", "")
            if query_lower not in name.lower() and query_lower not in slug.lower():
                continue
            # Extract connected realm ID from href: .../connected-realm/96?...
            href = r.get("connected_realm", {}).get("href", "")
            m = re.search(r"/connected-realm/(\d+)", href)
            if not m:
                continue
            results.append({
                "name": name,
                "slug": slug,
                "connected_realm_id": int(m.group(1)),
            })
        return results
