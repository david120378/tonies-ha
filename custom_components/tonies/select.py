"""Select entities: max volume, headphone volume, LED, tap direction."""

from __future__ import annotations

from dataclasses import dataclass

from homeassistant.components.select import SelectEntity, SelectEntityDescription
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import LED_OPTIONS, TAP_OPTIONS, VOLUME_OPTIONS
from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity


@dataclass(frozen=True, kw_only=True)
class ToniesSelectDescription(SelectEntityDescription):
    api_field: str
    numeric: bool = False
    show_picture: bool = False


SELECTS: tuple[ToniesSelectDescription, ...] = (
    ToniesSelectDescription(
        key="max_volume",
        api_field="maxVolume",
        options=VOLUME_OPTIONS,
        numeric=True,
        icon="mdi:volume-high",
        show_picture=True,
    ),
    ToniesSelectDescription(
        key="max_headphone_volume",
        api_field="maxHeadphoneVolume",
        options=VOLUME_OPTIONS,
        numeric=True,
        icon="mdi:headphones",
    ),
    ToniesSelectDescription(
        key="led_level",
        api_field="ledLevel",
        options=LED_OPTIONS,
        icon="mdi:led-on",
        entity_category=EntityCategory.CONFIG,
    ),
    ToniesSelectDescription(
        key="tap_direction",
        api_field="tapDirection",
        options=TAP_OPTIONS,
        icon="mdi:gesture-tap",
        entity_category=EntityCategory.CONFIG,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant, entry: ToniesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    entities: list[SelectEntity] = [
        ToniesSelect(coordinator, box_id, desc) for box_id in coordinator.data.boxes for desc in SELECTS
    ]
    entities += [
        ToniesScheduleVolumeSelect(coordinator, box_id, key, field)
        for box_id in coordinator.data.boxes
        for key, field in (("night_volume", "night_volume"), ("day_volume", "day_volume"))
    ]
    async_add_entities(entities)


class ToniesSelect(ToniesBoxEntity, SelectEntity):
    entity_description: ToniesSelectDescription

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, desc: ToniesSelectDescription) -> None:
        super().__init__(coordinator, box_id, desc.key)
        self.entity_description = desc

    @property
    def entity_picture(self) -> str | None:
        return self.box_picture if self.entity_description.show_picture else None

    @property
    def current_option(self) -> str | None:
        value = self.box.get(self.entity_description.api_field)
        if value is None:
            return None
        return str(value)

    async def async_select_option(self, option: str) -> None:
        value: int | str = int(option) if self.entity_description.numeric else option
        await self.coordinator.async_set_box(self.box_id, **{self.entity_description.api_field: value})


class ToniesScheduleVolumeSelect(ToniesBoxEntity, SelectEntity):
    """Volume used by the schedule at night / during the day."""

    _attr_entity_category = EntityCategory.CONFIG
    _attr_options = VOLUME_OPTIONS

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, key: str, field: str) -> None:
        super().__init__(coordinator, box_id, key)
        self._field = field
        self._attr_icon = "mdi:volume-low" if field == "night_volume" else "mdi:volume-high"

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        assert self.coordinator.schedules
        self.async_on_remove(self.coordinator.schedules.async_add_listener(self.async_write_ha_state))

    @property
    def current_option(self) -> str | None:
        assert self.coordinator.schedules
        return str(getattr(self.coordinator.schedules.get(self.box_id), self._field))

    async def async_select_option(self, option: str) -> None:
        assert self.coordinator.schedules
        await self.coordinator.schedules.async_update(self.box_id, **{self._field: int(option)})
