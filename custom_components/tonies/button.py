"""Button: refresh data from the cloud."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .coordinator import ToniesConfigEntry, ToniesCoordinator
from .entity import ToniesBoxEntity


async def async_setup_entry(
    hass: HomeAssistant, entry: ToniesConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(ToniesRefreshButton(coordinator, box_id) for box_id in coordinator.data.boxes)


class ToniesRefreshButton(ToniesBoxEntity, ButtonEntity):
    _attr_entity_category = EntityCategory.DIAGNOSTIC
    _attr_icon = "mdi:cloud-refresh"

    def __init__(self, coordinator: ToniesCoordinator, box_id: str) -> None:
        super().__init__(coordinator, box_id, "refresh")

    async def async_press(self) -> None:
        await self.coordinator.async_request_refresh()
