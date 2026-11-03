"""Sensors: box diagnostics, content tonies per household, creative tonies."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription, SensorStateClass
from homeassistant.const import EntityCategory, UnitOfTime
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity


@dataclass(frozen=True, kw_only=True)
class ToniesSensorDescription(SensorEntityDescription):
    api_field: str


BOX_SENSORS: tuple[ToniesSensorDescription, ...] = (
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
    entities: list[SensorEntity] = [
        ToniesBoxSensor(coordinator, box_id, desc) for box_id in coordinator.data.boxes for desc in BOX_SENSORS
    ]
    for hid in coordinator.data.households:
        entities.append(ToniesContentToniesSensor(coordinator, hid))
        entities.append(ToniesCreativeToniesCountSensor(coordinator, hid))
    for tonie_id in coordinator.data.creative_tonies:
        entities.append(CreativeTonieRemainingSensor(coordinator, tonie_id))
        entities.append(CreativeTonieUsedSensor(coordinator, tonie_id))
    async_add_entities(entities)


# --------------------------------------------------------------------- boxes
class ToniesBoxSensor(ToniesBoxEntity, SensorEntity):
    entity_description: ToniesSensorDescription

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, desc: ToniesSensorDescription) -> None:
        super().__init__(coordinator, box_id, desc.key)
        self.entity_description = desc

    @property
    def native_value(self) -> str | None:
        value = self.box.get(self.entity_description.api_field)
        return None if value is None else str(value)


# ---------------------------------------------------------------- households
class ToniesHouseholdEntity(CoordinatorEntity[ToniesCoordinator]):
    """Entity bound to a household (one device per household)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ToniesCoordinator, household_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.household_id = household_id
        self._attr_unique_id = f"household_{household_id}_{key}"
        self._attr_translation_key = key
        name = coordinator.data.households[household_id].get("name") or "Haushalt"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"household_{household_id}")},
            name=f"tonies {name}",
            manufacturer="tonies GmbH",
            model="Haushalt",
            entry_type=None,
        )

    def _tonies(self, source: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
        return [t for t in source.values() if t.get("householdId") == self.household_id]


class ToniesContentToniesSensor(ToniesHouseholdEntity, SensorEntity):
    """Number of content tonies, list as attribute."""

    _attr_icon = "mdi:account-group"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ToniesCoordinator, household_id: str) -> None:
        super().__init__(coordinator, household_id, "content_tonies")

    @property
    def native_value(self) -> int:
        return len(self._tonies(self.coordinator.data.content_tonies))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        tonies = sorted(self._tonies(self.coordinator.data.content_tonies), key=lambda t: t.get("title") or "")
        return {
            "tonies": [
                {
                    "id": t["id"],
                    "title": t.get("title"),
                    "series": (t.get("series") or {}).get("name"),
                    "locked": t.get("lock"),
                    "image": t.get("imageUrl"),
                }
                for t in tonies
            ]
        }


class ToniesCreativeToniesCountSensor(ToniesHouseholdEntity, SensorEntity):
    _attr_icon = "mdi:account-edit"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ToniesCoordinator, household_id: str) -> None:
        super().__init__(coordinator, household_id, "creative_tonies")

    @property
    def native_value(self) -> int:
        return len(self._tonies(self.coordinator.data.creative_tonies))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        return {
            "tonies": [
                {"id": t["id"], "name": t.get("name"), "live": t.get("live")}
                for t in self._tonies(self.coordinator.data.creative_tonies)
            ]
        }


# ------------------------------------------------------------ creative tonies
class CreativeTonieEntity(CoordinatorEntity[ToniesCoordinator]):
    """Entity bound to one creative tonie (one device per tonie)."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ToniesCoordinator, tonie_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.tonie_id = tonie_id
        self._attr_unique_id = f"creative_{tonie_id}_{key}"
        self._attr_translation_key = key
        tonie = self.tonie
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, f"creative_{tonie_id}")},
            name=f"Kreativ-Tonie {tonie.get('name') or tonie_id}",
            manufacturer="tonies GmbH",
            model="Kreativ-Tonie",
            serial_number=tonie_id,
            via_device=(DOMAIN, f"household_{tonie['householdId']}"),
        )

    @property
    def tonie(self) -> dict[str, Any]:
        return self.coordinator.data.creative_tonies[self.tonie_id]

    @property
    def available(self) -> bool:
        return super().available and self.tonie_id in self.coordinator.data.creative_tonies


class CreativeTonieRemainingSensor(CreativeTonieEntity, SensorEntity):
    _attr_icon = "mdi:timer-sand"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ToniesCoordinator, tonie_id: str) -> None:
        super().__init__(coordinator, tonie_id, "remaining")

    @property
    def native_value(self) -> float | None:
        secs = self.tonie.get("secondsRemaining")
        return None if secs is None else round(secs / 60, 1)

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        t = self.tonie
        return {"live": t.get("live"), "private": t.get("private"), "image": t.get("imageUrl")}


class CreativeTonieUsedSensor(CreativeTonieEntity, SensorEntity):
    _attr_icon = "mdi:music-box-multiple"
    _attr_native_unit_of_measurement = UnitOfTime.MINUTES
    _attr_suggested_display_precision = 0
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ToniesCoordinator, tonie_id: str) -> None:
        super().__init__(coordinator, tonie_id, "used")

    @property
    def native_value(self) -> float | None:
        secs = self.tonie.get("secondsPresent")
        return None if secs is None else round(secs / 60, 1)
