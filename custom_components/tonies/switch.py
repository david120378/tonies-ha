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
    entities: list[SwitchEntity] = []
    for box_id in coordinator.data.boxes:
        entities.append(ToniesAccelerometerSwitch(coordinator, box_id))
        entities.append(ToniesScheduleSwitch(coordinator, box_id, "schedule", "enabled", "mdi:calendar-clock"))
        entities.append(
            ToniesScheduleSwitch(coordinator, box_id, "schedule_headphones", "headphones_too", "mdi:headphones-settings")
        )
    async_add_entities(entities)


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


class ToniesScheduleSwitch(ToniesBoxEntity, SwitchEntity):
    """Enable the volume schedule / include headphones."""

    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, key: str, field: str, icon: str) -> None:
        super().__init__(coordinator, box_id, key)
        self._field = field
        self._attr_icon = icon

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        assert self.coordinator.schedules
        self.async_on_remove(self.coordinator.schedules.async_add_listener(self.async_write_ha_state))

    @property
    def is_on(self) -> bool:
        assert self.coordinator.schedules
        return bool(getattr(self.coordinator.schedules.get(self.box_id), self._field))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        assert self.coordinator.schedules
        sched = self.coordinator.schedules.get(self.box_id)
        from homeassistant.util import dt as dt_util  # noqa: PLC0415

        return {
            "night_start": sched.night_start,
            "day_start": sched.day_start,
            "night_volume": sched.night_volume,
            "day_volume": sched.day_volume,
            "currently": "night" if sched.is_night(dt_util.now().time()) else "day",
        }

    async def async_turn_on(self, **kwargs: Any) -> None:
        assert self.coordinator.schedules
        await self.coordinator.schedules.async_update(self.box_id, **{self._field: True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        assert self.coordinator.schedules
        await self.coordinator.schedules.async_update(self.box_id, **{self._field: False})
