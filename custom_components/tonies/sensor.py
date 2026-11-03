"""Diagnostic sensors."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity


@dataclass(frozen=True, kw_only=True)
class ToniesSensorDescription(SensorEntityDescription):
    api_field: str


SENSORS: tuple[ToniesSensorDescription, ...] = (
    ToniesSensorDescription(
        key="firmware_version",
        api_field="firmwareVersion",
        icon="mdi:chip",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ToniesSensorDescription(
        key="online_state",
        api_field="onlineState",
        icon="mdi:wifi",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
    ToniesSensorDescription(
        key="household",
        api_field="householdName",
        icon="mdi:home-group",
        entity_category=EntityCategory.DIAGNOSTIC,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ToniesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        ToniesSensor(coordinator, box_id, desc) for box_id in coordinator.data for desc in SENSORS
    )


class ToniesSensor(ToniesBoxEntity, SensorEntity):
    entity_description: ToniesSensorDescription

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, desc: ToniesSensorDescription) -> None:
        super().__init__(coordinator, box_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> str | None:
        value = self.box.get(self.entity_description.api_field)
        return None if value is None else str(value)
