"""Time entities: start of night / day for the volume schedule."""

from __future__ import annotations

from datetime import time

from homeassistant.components.time import TimeEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ToniesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ToniesScheduleTime(coordinator, box_id, key, field)
        for box_id in coordinator.data.boxes
        for key, field in (("night_start", "night_start"), ("day_start", "day_start"))
    )


class ToniesScheduleTime(ToniesBoxEntity, TimeEntity):
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, key: str, field: str) -> None:
        super().__init__(coordinator, box_id, key)
        self._field = field
        self._attr_icon = "mdi:weather-night" if field == "night_start" else "mdi:weather-sunny"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        assert self.coordinator.schedules
        self.async_on_remove(self.coordinator.schedules.async_add_listener(self.async_write_ha_state))

    @property
    def native_value(self) -> time | None:
        assert self.coordinator.schedules
        return time.fromisoformat(getattr(self.coordinator.schedules.get(self.box_id), self._field))

    async def async_set_value(self, value: time) -> None:
        assert self.coordinator.schedules
        await self.coordinator.schedules.async_update(self.box_id, **{self._field: value.replace(second=0).isoformat()})
