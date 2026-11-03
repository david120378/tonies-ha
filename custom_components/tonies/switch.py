"""Switch entities: accelerometer (Spulen & Klapsen)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ToniesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(ToniesAccelerometerSwitch(coordinator, box_id) for box_id in coordinator.data)


class ToniesAccelerometerSwitch(ToniesBoxEntity, SwitchEntity):
    _attr_entity_category = EntityCategory.CONFIG
    _attr_icon = "mdi:axis-arrow"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id, "accelerometer")

    @property
    def is_on(self) -> bool | None:
        return self.box.get("accelerometerEnabled")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_box(self.box_id, accelerometerEnabled=True)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self.coordinator.async_set_box(self.box_id, accelerometerEnabled=False)
