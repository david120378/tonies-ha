"""Minimal client for the (unofficial) tonies cloud API used by my.tonies.com."""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

import aiohttp

from .const import API_BASE, CLIENT_ID, TOKEN_URL

_LOGGER = logging.getLogger(__name__)


class ToniesAuthError(Exception):
    """Invalid credentials."""


class ToniesApiError(Exception):
    """Generic API error."""


class ToniesClient:
    """Async client for the tonies cloud."""

    def __init__(self, session: aiohttp.ClientSession, username: str, password: str) -> None:
        self._session = session
        self._username = username
        self._password = password
        self._access_token: str | None = None
        self._refresh_token: str | None = None
        self._expires_at: float = 0
        self._lock = asyncio.Lock()

    # ------------------------------------------------------------------ auth
    async def _token_request(self, data: dict[str, str]) -> None:
        data = {"client_id": CLIENT_ID, "scope": "openid", **data}
        try:
            async with self._session.post(TOKEN_URL, data=data, timeout=aiohttp.ClientTimeout(total=20)) as resp:
                body = await resp.json(content_type=None)
                if resp.status == 401 or body.get("error") == "invalid_grant":
                    raise ToniesAuthError(body.get("error_description", "invalid credentials"))
                if resp.status != 200:
                    raise ToniesApiError(f"token request failed: {resp.status} {body}")
        except aiohttp.ClientError as err:
            raise ToniesApiError(f"token request failed: {err}") from err

        self._access_token = body["access_token"]
        self._refresh_token = body.get("refresh_token")
        # refresh a little early
        self._expires_at = time.monotonic() + int(body.get("expires_in", 300)) - 30

    async def async_login(self) -> None:
        """Log in with username/password."""
        await self._token_request(
            {"grant_type": "password", "username": self._username, "password": self._password}
        )

    async def _ensure_token(self) -> str:
        async with self._lock:
            if self._access_token and time.monotonic() < self._expires_at:
                return self._access_token
            if self._refresh_token:
                try:
                    await self._token_request(
                        {"grant_type": "refresh_token", "refresh_token": self._refresh_token}
                    )
                    return self._access_token  # type: ignore[return-value]
                except (ToniesAuthError, ToniesApiError) as err:
                    _LOGGER.debug("Refresh failed (%s), logging in again", err)
            await self.async_login()
            return self._access_token  # type: ignore[return-value]

    # ------------------------------------------------------------------ http
    async def _request(self, method: str, path: str, json: Any | None = None, _retry: bool = True) -> Any:
        token = await self._ensure_token()
        headers = {"Authorization": f"Bearer {token}", "Accept": "application/json"}
        try:
            async with self._session.request(
                method,
                f"{API_BASE}{path}",
                headers=headers,
                json=json,
                timeout=aiohttp.ClientTimeout(total=20),
            ) as resp:
                if resp.status == 401 and _retry:
                    self._access_token = None
                    return await self._request(method, path, json, _retry=False)
                if resp.status >= 400:
                    text = await resp.text()
                    raise ToniesApiError(f"{method} {path} -> {resp.status}: {text[:200]}")
                if resp.status == 204:
                    return None
                return await resp.json(content_type=None)
        except aiohttp.ClientError as err:
            raise ToniesApiError(f"{method} {path} failed: {err}") from err

    # ------------------------------------------------------------------ api
    async def async_get_me(self) -> dict[str, Any]:
        return await self._request("GET", "/me")

    async def async_get_households(self) -> list[dict[str, Any]]:
        return await self._request("GET", "/households")

    async def async_get_tonieboxes(self, household_id: str) -> list[dict[str, Any]]:
        return await self._request("GET", f"/households/{household_id}/tonieboxes")

    async def async_get_all_tonieboxes(self) -> dict[str, dict[str, Any]]:
        """Return all boxes of all households, keyed by box id."""
        boxes: dict[str, dict[str, Any]] = {}
        for household in await self.async_get_households():
            for box in await self.async_get_tonieboxes(household["id"]):
                box["householdName"] = household.get("name")
                boxes[box["id"]] = box
        return boxes

    async def async_patch_toniebox(self, household_id: str, box_id: str, **fields: Any) -> dict[str, Any]:
        """Change box settings, e.g. maxVolume=25. Returns the updated box."""
        return await self._request("PATCH", f"/households/{household_id}/tonieboxes/{box_id}", json=fields)
