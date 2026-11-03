"""Binary sensors: settings applied (cloud) and box active (WLAN presence)."""

from __future__ import annotations

from datetime import datetime
import logging
from typing import Any

from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity
from homeassistant.const import STATE_HOME
from homeassistant.core import Event, EventStateChangedData, HomeAssistant, callback
from homeassistant.helpers import device_registry as dr, entity_registry as er
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.helpers.restore_state import RestoreEntity
from homeassistant.util import dt as dt_util

from .const import CONF_TRACKER_PREFIX
from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity, format_mac

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, entry: ToniesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[BinarySensorEntity] = []
    for box_id, box in coordinator.data.boxes.items():
        entities.append(ToniesSettingsAppliedSensor(coordinator, box_id))
        tracker = find_tracker_entity(hass, entry, box_id, box.get("macAddress"))
        if tracker:
            entities.append(ToniesBoxActiveSensor(coordinator, box_id, tracker))
        else:
            _LOGGER.info(
                "No device_tracker found for Toniebox %s (MAC %s); "
                "select one in the integration options to get the 'active' sensor",
                box.get("name"),
                box.get("macAddress"),
            )
    async_add_entities(entities)


def find_tracker_entity(hass: HomeAssistant, entry: ToniesConfigEntry, box_id: str, mac: str | None) -> str | None:
    """Return a device_tracker entity for the box: options first, then by MAC via the registries."""
    configured = entry.options.get(f"{CONF_TRACKER_PREFIX}{box_id}")
    if configured:
        return configured
    if not mac:
        return None
    dev_reg = dr.async_get(hass)
    device = dev_reg.async_get_device(connections={(dr.CONNECTION_NETWORK_MAC, format_mac(mac))})
    if device is None:
        return None
    ent_reg = er.async_get(hass)
    for ent in er.async_entries_for_device(ent_reg, device.id, include_disabled_entities=False):
        if ent.domain == "device_tracker":
            return ent.entity_id
    return None


class ToniesSettingsAppliedSensor(ToniesBoxEntity, BinarySensorEntity):
    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id, "settings_applied")

    @property
    def is_on(self) -> bool | None:
        return self.box.get("settingsApplied")

    @property
    def icon(self) -> str:
        return "mdi:sync" if self.is_on else "mdi:sync-alert"

    @property
    def entity_picture(self) -> str | None:
        return self.box_picture


class ToniesBoxActiveSensor(ToniesBoxEntity, BinarySensorEntity, RestoreEntity):
    """On while the box is awake (its WLAN device_tracker reports 'home')."""

    _attr_device_class = BinarySensorDeviceClass.RUNNING
    _attr_icon = "mdi:speaker-wireless"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, tracker_entity_id: str) -> None:
        super().__init__(coordinator, box_id, "active")
        self._tracker = tracker_entity_id
        self._is_on: bool | None = None
        self._last_active: datetime | None = None

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        if (last := await self.async_get_last_state()) and (ts := last.attributes.get("last_active")):
            self._last_active = dt_util.parse_datetime(ts)
        self._update_from_tracker(self.hass.states.get(self._tracker))
        self.async_on_remove(
            async_track_state_change_event(self.hass, [self._tracker], self._handle_tracker_event)
        )

    @callback
    def _handle_tracker_event(self, event: Event[EventStateChangedData]) -> None:
        self._update_from_tracker(event.data["new_state"])
        self.async_write_ha_state()

    @callback
    def _update_from_tracker(self, state: Any) -> None:
        if state is None or state.state in ("unknown", "unavailable"):
            self._is_on = None
            return
        now_on = state.state == STATE_HOME
        if now_on and not self._is_on:
            self._last_active = dt_util.utcnow()
        self._is_on = now_on

    @property
    def available(self) -> bool:
        return self._is_on is not None

    @property
    def entity_picture(self) -> str | None:
        return self.box_picture

    @property
    def is_on(self) -> bool | None:
        return self._is_on

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "tracker_entity": self._tracker,
            "last_active": self._last_active.isoformat() if self._last_active else None,
        }
