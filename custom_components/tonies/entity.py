"""Base entity for tonies."""

from __future__ import annotations

from typing import Any

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ToniesCoordinator


class ToniesBoxEntity(CoordinatorEntity[ToniesCoordinator]):
    """Entity bound to one Toniebox."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ToniesCoordinator, box_id: str, key: str) -> None:
        super().__init__(coordinator)
        self.box_id = box_id
        self._attr_unique_id = f"{box_id}_{key}"
        self._attr_translation_key = key
        box = self.box
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, box_id)},
            name=box.get("name") or f"Toniebox {box_id}",
            manufacturer="tonies GmbH",
            model=f"Toniebox ({box.get('generation', 'unknown')})",
            serial_number=box_id,
            sw_version=str(box.get("firmwareVersion") or ""),
            connections={("mac", format_mac(box["macAddress"]))} if box.get("macAddress") else set(),
        )

    @property
    def box(self) -> dict[str, Any]:
        return self.coordinator.data.boxes[self.box_id]

    @property
    def box_picture(self) -> str | None:
        """Product photo of this box from the cloud (matches the box colour)."""
        return self.box.get("frontImageUrl") or self.box.get("imageUrl")

    @property
    def available(self) -> bool:
        return super().available and self.box_id in self.coordinator.data.boxes


def format_mac(raw: str) -> str:
    raw = raw.replace(":", "").lower()
    return ":".join(raw[i : i + 2] for i in range(0, len(raw), 2))
