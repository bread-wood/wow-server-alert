import time
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from wow_server_alert.blizzard import BlizzardClient


@pytest.fixture
def client():
    return BlizzardClient("id", "secret", "us", "en_US")


async def test_authenticate_fetches_token(client):
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"access_token": "tok123", "expires_in": 86400}
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value = mock_http
        mock_http.__aexit__.return_value = False
        mock_http.post = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        await client.authenticate()

    assert client._token == "tok123"
    assert client._token_expires > time.time()


async def test_authenticate_skips_if_valid(client):
    client._token = "existing"
    client._token_expires = time.time() + 9999

    with patch("httpx.AsyncClient") as mock_cls:
        await client.authenticate()
        mock_cls.assert_not_called()


async def test_get_realm_status(client):
    client._token = "tok"
    client._token_expires = time.time() + 9999

    api_response = {
        "status": {"type": "UP", "name": {"en_US": "Up"}},
        "has_queue": False,
        "realms": [{"name": "Stormrage", "slug": "stormrage"}],
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = api_response
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value = mock_http
        mock_http.__aexit__.return_value = False
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        result = await client.get_realm_status(96)

    assert result["status"] == "UP"
    assert result["name"] == "Stormrage"
    assert result["has_queue"] is False


async def test_search_realms_filters_by_query(client):
    client._token = "tok"
    client._token_expires = time.time() + 9999

    index_response = {
        "realms": [
            {
                "name": "Stormrage",
                "slug": "stormrage",
                "connected_realm": {"href": "https://us.api.blizzard.com/data/wow/connected-realm/96?namespace=dynamic-us"},
            },
            {
                "name": "Illidan",
                "slug": "illidan",
                "connected_realm": {"href": "https://us.api.blizzard.com/data/wow/connected-realm/11?namespace=dynamic-us"},
            },
        ]
    }
    mock_resp = MagicMock()
    mock_resp.json.return_value = index_response
    mock_resp.raise_for_status = MagicMock()

    with patch("httpx.AsyncClient") as mock_cls:
        mock_http = AsyncMock()
        mock_http.__aenter__.return_value = mock_http
        mock_http.__aexit__.return_value = False
        mock_http.get = AsyncMock(return_value=mock_resp)
        mock_cls.return_value = mock_http

        results = await client.search_realms("storm")

    assert len(results) == 1
    assert results[0]["name"] == "Stormrage"
    assert results[0]["connected_realm_id"] == 96
