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


SELECTS: tuple[ToniesSelectDescription, ...] = (
    ToniesSelectDescription(
        key="max_volume",
        api_field="maxVolume",
        options=VOLUME_OPTIONS,
        numeric=True,
        icon="mdi:volume-high",
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
    async_add_entities(
        ToniesSelect(coordinator, box_id, desc) for box_id in coordinator.data for desc in SELECTS
    )


class ToniesSelect(ToniesBoxEntity, SelectEntity):
    entity_description: ToniesSelectDescription

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, desc: ToniesSelectDescription) -> None:
        super().__init__(coordinator, box_id, desc.key)
        self.entity_description = desc

    @property
    def current_option(self) -> str | None:
        value = self.box.get(self.entity_description.api_field)
        if value is None:
            return None
        return str(value)

    async def async_select_option(self, option: str) -> None:
        value: int | str = int(option) if self.entity_description.numeric else option
        await self.coordinator.async_set_box(self.box_id, **{self.entity_description.api_field: value})
