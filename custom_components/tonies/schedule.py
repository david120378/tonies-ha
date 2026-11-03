"""Per-box volume schedule (night / day), handled by the integration itself."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import time
import logging
from typing import TYPE_CHECKING, Any

from homeassistant.core import CALLBACK_TYPE, HomeAssistant, callback
from homeassistant.helpers.event import async_track_time_change
from homeassistant.helpers.storage import Store
from homeassistant.util import dt as dt_util

from .const import DOMAIN

if TYPE_CHECKING:
    from .coordinator import ToniesCoordinator

_LOGGER = logging.getLogger(__name__)

STORAGE_VERSION = 1


@dataclass
class BoxSchedule:
    """Schedule settings of one box."""

    enabled: bool = False
    night_start: str = "19:00:00"
    day_start: str = "07:00:00"
    night_volume: int = 25
    day_volume: int = 50
    headphones_too: bool = False

    @property
    def night_time(self) -> time:
        return time.fromisoformat(self.night_start)

    @property
    def day_time(self) -> time:
        return time.fromisoformat(self.day_start)

    def is_night(self, now: time) -> bool:
        """True if `now` falls into the night window (handles windows crossing midnight)."""
        n, d = self.night_time, self.day_time
        if n == d:
            return False
        if n < d:
            return n <= now < d
        return now >= n or now < d

    def expected_volume(self, now: time) -> int:
        return self.night_volume if self.is_night(now) else self.day_volume


class ScheduleManager:
    """Keeps schedules per box, persists them and fires the volume changes."""

    def __init__(self, hass: HomeAssistant, coordinator: ToniesCoordinator, entry_id: str) -> None:
        self.hass = hass
        self.coordinator = coordinator
        self._store: Store[dict[str, dict[str, Any]]] = Store(hass, STORAGE_VERSION, f"{DOMAIN}.{entry_id}.schedules")
        self.schedules: dict[str, BoxSchedule] = {}
        self._unsubs: dict[str, list[CALLBACK_TYPE]] = {}
        self._listeners: list[CALLBACK_TYPE] = []

    async def async_load(self) -> None:
        data = await self._store.async_load() or {}
        for box_id in self.coordinator.data.boxes:
            raw = data.get(box_id, {})
            self.schedules[box_id] = BoxSchedule(**{k: v for k, v in raw.items() if k in BoxSchedule.__dataclass_fields__})
            self._register_timers(box_id)

    @callback
    def async_add_listener(self, cb: CALLBACK_TYPE) -> CALLBACK_TYPE:
        self._listeners.append(cb)

        def _remove() -> None:
            self._listeners.remove(cb)

        return _remove

    @callback
    def async_unload(self) -> None:
        for unsubs in self._unsubs.values():
            for unsub in unsubs:
                unsub()
        self._unsubs.clear()

    def get(self, box_id: str) -> BoxSchedule:
        return self.schedules.setdefault(box_id, BoxSchedule())

    async def async_update(self, box_id: str, **changes: Any) -> None:
        """Change schedule fields, persist, re-register timers and apply the expected volume right away."""
        schedule = self.get(box_id)
        for key, value in changes.items():
            setattr(schedule, key, value)
        await self._store.async_save({bid: asdict(s) for bid, s in self.schedules.items()})
        self._register_timers(box_id)
        for cb in self._listeners:
            cb()
        if schedule.enabled:
            await self._apply(box_id, reason="settings changed")

    @callback
    def _register_timers(self, box_id: str) -> None:
        for unsub in self._unsubs.pop(box_id, []):
            unsub()
        schedule = self.get(box_id)
        if not schedule.enabled:
            return
        async def _fire(_now: Any) -> None:
            await self._apply(box_id, reason="scheduled")

        self._unsubs[box_id] = [
            async_track_time_change(self.hass, _fire, hour=t.hour, minute=t.minute, second=0)
            for t in (schedule.night_time, schedule.day_time)
        ]

    async def async_apply_all(self) -> None:
        """Apply expected volumes for all enabled schedules (e.g. after HA start)."""
        for box_id, schedule in self.schedules.items():
            if schedule.enabled:
                await self._apply(box_id, reason="startup")

    async def _apply(self, box_id: str, reason: str) -> None:
        schedule = self.get(box_id)
        box = self.coordinator.data.boxes.get(box_id)
        if box is None:
            return
        expected = schedule.expected_volume(dt_util.now().time())
        fields: dict[str, Any] = {}
        if box.get("maxVolume") != expected:
            fields["maxVolume"] = expected
        if schedule.headphones_too and box.get("maxHeadphoneVolume") != expected:
            fields["maxHeadphoneVolume"] = expected
        if not fields:
            return
        _LOGGER.info("Toniebox %s: setting %s (%s)", box.get("name"), fields, reason)
        try:
            await self.coordinator.async_set_box(box_id, **fields)
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Toniebox %s: could not apply schedule", box.get("name"))
