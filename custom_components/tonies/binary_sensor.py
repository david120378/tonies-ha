"""Binary sensor: settings applied by the box."""

from __future__ import annotations

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ToniesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(ToniesSettingsAppliedSensor(coordinator, box_id) for box_id in coordinator.data.boxes)


class ToniesSettingsAppliedSensor(ToniesBoxEntity, BinarySensorEntity):
    _attr_icon = "mdi:sync"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id, "settings_applied")

    @property
    def is_on(self) -> bool | None:
        return self.box.get("settingsApplied")

    @property
    def icon(self) -> str:
        return "mdi:sync" if self.is_on else "mdi:sync-alert"
