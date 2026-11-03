"""Data update coordinator for tonies."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import timedelta
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import ToniesApiError, ToniesAuthError, ToniesClient
from .const import CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES, DOMAIN

if TYPE_CHECKING:
    from .schedule import ScheduleManager

_LOGGER = logging.getLogger(__name__)

type ToniesConfigEntry = ConfigEntry[ToniesCoordinator]


@dataclass
class ToniesData:
    """All data of the account."""

    boxes: dict[str, dict[str, Any]] = field(default_factory=dict)
    households: dict[str, dict[str, Any]] = field(default_factory=dict)
    content_tonies: dict[str, dict[str, Any]] = field(default_factory=dict)
    creative_tonies: dict[str, dict[str, Any]] = field(default_factory=dict)


class ToniesCoordinator(DataUpdateCoordinator[ToniesData]):
    """Fetch boxes and tonies of the account."""

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry, client: ToniesClient) -> None:
        minutes = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL_MINUTES)
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(minutes=minutes),
            config_entry=entry,
        )
        self.client = client
        self.schedules: ScheduleManager | None = None

    async def _async_update_data(self) -> ToniesData:
        try:
            boxes = await self.client.async_get_all_tonieboxes()
            tonies = await self.client.async_get_tonies()
        except ToniesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ToniesApiError as err:
            raise UpdateFailed(str(err)) from err

        data = ToniesData(boxes=boxes)
        for household in tonies.get("households", []):
            hid = household["id"]
            data.households[hid] = {"id": hid, "name": household.get("name")}
            for tonie in household.get("contentTonies") or []:
                tonie["householdId"] = hid
                tonie["householdName"] = household.get("name")
                data.content_tonies[tonie["id"]] = tonie
            for tonie in household.get("creativeTonies") or []:
                tonie["householdId"] = hid
                tonie["householdName"] = household.get("name")
                data.creative_tonies[tonie["id"]] = tonie
        return data

    async def async_set_box(self, box_id: str, **fields: Any) -> None:
        """Patch a box and update local data immediately."""
        box = self.data.boxes[box_id]
        try:
            updated = await self.client.async_patch_toniebox(box["householdId"], box_id, **fields)
        except ToniesAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ToniesApiError as err:
            raise UpdateFailed(str(err)) from err
        updated["householdName"] = box.get("householdName")
        self.data.boxes[box_id] = updated
        self.async_update_listeners()
