"""Data update coordinator for tonies."""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ToniesApiError, ToniesAuthError, ToniesClient
from .const import DEFAULT_SCAN_INTERVAL, DOMAIN

_LOGGER = logging.getLogger(__name__)

type ToniesConfigEntry = ConfigEntry[ToniesCoordinator]


class ToniesCoordinator(DataUpdateCoordinator[dict[str, dict[str, Any]]]):
    """Fetch all tonieboxes of the account."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ToniesClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=DEFAULT_SCAN_INTERVAL,
            config_entry=entry,
        )
        self.client = client

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        try:
            return await self.client.async_get_all_tonieboxes()
        except ToniesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ToniesApiError as err:
            raise UpdateFailed(str(err)) from err

    async def async_set_box(self, box_id: str, **fields: Any) -> None:
        """Patch a box and update local data immediately."""
        box = self.data[box_id]
        try:
            updated = await self.client.async_patch_toniebox(box["householdId"], box_id, **fields)
        except ToniesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ToniesApiError as err:
            raise UpdateFailed(str(err)) from err
        updated["householdName"] = box.get("householdName")
        self.data[box_id] = updated
        self.async_update_listeners()
