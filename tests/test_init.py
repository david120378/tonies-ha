from unittest.mock import AsyncMock, patch

from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.tonies.const import DOMAIN

BOX = {
    "id": "4QN986SP", "householdId": "H1", "macAddress": "909A771554EC", "name": "Hauke's rote Toniebox",
    "accelerometerEnabled": True, "tapDirection": "left", "maxVolume": 25, "maxHeadphoneVolume": 25,
    "ledLevel": "on", "firmwareVersion": "1779199517", "onlineState": "unsupported", "settingsApplied": False,
    "generation": "classic", "householdName": "Mein Haushalt",
}

TONIES = {
    "households": [{
        "id": "H1", "name": "Mein Haushalt",
        "contentTonies": [
            {"id": "T1", "title": "Asterix, der Gallier", "lock": False, "imageUrl": "x", "series": {"name": "Asterix", "group": None}, "tune": None},
            {"id": "T2", "title": "Dumbo", "lock": False, "imageUrl": "x", "series": {"name": "Dumbo", "group": None}, "tune": None},
        ],
        "creativeTonies": [
            {"id": "C1", "name": "Red", "live": True, "private": False, "imageUrl": "x", "secondsRemaining": 4218.0, "secondsPresent": 1181.0, "tune": None},
        ],
    }]
}


async def test_setup_and_select(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"username": "u", "password": "p"}, unique_id="uid")
    entry.add_to_hass(hass)

    patched = dict(BOX, maxVolume=50, settingsApplied=False)
    with patch("custom_components.tonies.ToniesClient") as cls:
        client = cls.return_value
        client.async_login = AsyncMock()
        client.async_get_all_tonieboxes = AsyncMock(return_value={BOX["id"]: dict(BOX)})
        client.async_get_tonies = AsyncMock(return_value=TONIES)
        client.async_patch_toniebox = AsyncMock(return_value=patched)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        sel = hass.states.get("select.hauke_s_rote_toniebox_max_volume")
        assert sel is not None and sel.state == "25", hass.states.async_entity_ids()
        assert hass.states.get("binary_sensor.hauke_s_rote_toniebox_settings_applied").state == "off"
        assert hass.states.get("switch.hauke_s_rote_toniebox_tap_tilt").state == "on"

        await hass.services.async_call(
            "select", "select_option", {"entity_id": sel.entity_id, "option": "50"}, blocking=True
        )
        client.async_patch_toniebox.assert_awaited_once_with("H1", "4QN986SP", maxVolume=50)
        assert hass.states.get(sel.entity_id).state == "50"


async def test_config_flow(hass: HomeAssistant) -> None:
    with patch("custom_components.tonies.config_flow.ToniesClient") as cls:
        client = cls.return_value
        client.async_login = AsyncMock()
        client.async_get_me = AsyncMock(return_value={"uuid": "abc"})
        result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": "user"})
        assert result["type"] == "form"
        with patch("custom_components.tonies.async_setup_entry", return_value=True):
            result = await hass.config_entries.flow.async_configure(
                result["flow_id"], {"username": "u@x.de", "password": "p"}
            )
    assert result["type"] == "create_entry"
    assert result["result"].unique_id == "abc"


async def test_tonies_sensors(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"username": "u", "password": "p"}, unique_id="uid2")
    entry.add_to_hass(hass)
    with patch("custom_components.tonies.ToniesClient") as cls:
        client = cls.return_value
        client.async_login = AsyncMock()
        client.async_get_all_tonieboxes = AsyncMock(return_value={BOX["id"]: dict(BOX)})
        client.async_get_tonies = AsyncMock(return_value=TONIES)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    ids = hass.states.async_entity_ids("sensor")
    content = hass.states.get("sensor.tonies_mein_haushalt_content_tonies")
    assert content is not None, ids
    assert content.state == "2"
    assert content.attributes["tonies"][0]["title"] == "Asterix, der Gallier"
    assert hass.states.get("sensor.tonies_mein_haushalt_creative_tonies").state == "1"
    rem = hass.states.get("sensor.kreativ_tonie_red_remaining_time")
    assert rem is not None, ids
    assert rem.state == "70.3"


async def test_options_flow(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"username": "u", "password": "p"}, unique_id="uid3")
    entry.add_to_hass(hass)
    with patch("custom_components.tonies.async_setup_entry", return_value=True):
        result = await hass.config_entries.options.async_init(entry.entry_id)
        assert result["type"] == "form"
        result = await hass.config_entries.options.async_configure(result["flow_id"], {"scan_interval": 30})
    assert result["type"] == "create_entry"
    assert entry.options["scan_interval"] == 30


async def test_active_sensor_via_option(hass: HomeAssistant) -> None:
    hass.states.async_set("device_tracker.toniebox", "not_home")
    entry = MockConfigEntry(
        domain=DOMAIN, data={"username": "u", "password": "p"}, unique_id="uid4",
        options={"tracker_4QN986SP": "device_tracker.toniebox"},
    )
    entry.add_to_hass(hass)
    with patch("custom_components.tonies.ToniesClient") as cls:
        client = cls.return_value
        client.async_login = AsyncMock()
        client.async_get_all_tonieboxes = AsyncMock(return_value={BOX["id"]: dict(BOX)})
        client.async_get_tonies = AsyncMock(return_value=TONIES)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    active = hass.states.get("binary_sensor.hauke_s_rote_toniebox_active")
    assert active is not None, hass.states.async_entity_ids("binary_sensor")
    assert active.state == "off"
    hass.states.async_set("device_tracker.toniebox", "home")
    await hass.async_block_till_done()
    active = hass.states.get("binary_sensor.hauke_s_rote_toniebox_active")
    assert active.state == "on"
    assert active.attributes["last_active"] is not None


async def test_active_sensor_via_mac(hass: HomeAssistant) -> None:
    from homeassistant.helpers import device_registry as dr, entity_registry as er

    other = MockConfigEntry(domain="fritz", data={}, unique_id="fritz")
    other.add_to_hass(hass)
    dev = dr.async_get(hass).async_get_or_create(
        config_entry_id=other.entry_id, connections={(dr.CONNECTION_NETWORK_MAC, "90:9a:77:15:54:ec")}
    )
    er.async_get(hass).async_get_or_create(
        "device_tracker", "fritz", "909A771554EC", device_id=dev.id, suggested_object_id="toniebox_54ec"
    )
    hass.states.async_set("device_tracker.toniebox_54ec", "home")

    entry = MockConfigEntry(domain=DOMAIN, data={"username": "u", "password": "p"}, unique_id="uid5")
    entry.add_to_hass(hass)
    with patch("custom_components.tonies.ToniesClient") as cls:
        client = cls.return_value
        client.async_login = AsyncMock()
        client.async_get_all_tonieboxes = AsyncMock(return_value={BOX["id"]: dict(BOX)})
        client.async_get_tonies = AsyncMock(return_value=TONIES)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

    active = hass.states.get("binary_sensor.hauke_s_rote_toniebox_active")
    assert active is not None, hass.states.async_entity_ids("binary_sensor")
    assert active.state == "on"
    assert active.attributes["tracker_entity"] == "device_tracker.toniebox_54ec"


async def test_schedule(hass: HomeAssistant, freezer) -> None:
    from datetime import timedelta
    from pytest_homeassistant_custom_component.common import async_fire_time_changed
    from homeassistant.util import dt as dt_util

    await hass.config.async_set_time_zone("Europe/Berlin")
    freezer.move_to("2026-11-03 18:00:00+01:00")
    entry = MockConfigEntry(domain=DOMAIN, data={"username": "u", "password": "p"}, unique_id="uid6")
    entry.add_to_hass(hass)
    with patch("custom_components.tonies.ToniesClient") as cls:
        client = cls.return_value
        client.async_login = AsyncMock()
        client.async_get_all_tonieboxes = AsyncMock(return_value={BOX["id"]: dict(BOX, maxVolume=50)})
        client.async_get_tonies = AsyncMock(return_value=TONIES)

        def _patch(hid, bid, **fields):
            return dict(BOX, **fields)

        client.async_patch_toniebox = AsyncMock(side_effect=_patch)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()

        prefix = "hauke_s_rote_toniebox"
        assert hass.states.get(f"switch.{prefix}_volume_schedule").state == "off"
        assert hass.states.get(f"time.{prefix}_night_from").state == "19:00:00"
        assert hass.states.get(f"select.{prefix}_night_volume").state == "25"

        # enabling at 18:00 (day) with box at 50 -> nothing to do
        await hass.services.async_call(
            "switch", "turn_on", {"entity_id": f"switch.{prefix}_volume_schedule"}, blocking=True
        )
        await hass.async_block_till_done()
        client.async_patch_toniebox.assert_not_awaited()

        # 19:00 -> night volume 25
        freezer.move_to("2026-11-03 19:00:00+01:00")
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        client.async_patch_toniebox.assert_awaited_once_with("H1", "4QN986SP", maxVolume=25)
        assert hass.states.get(f"select.{prefix}_max_volume").state == "25"

        # change day volume to 75 while it's night -> no immediate change
        client.async_patch_toniebox.reset_mock()
        await hass.services.async_call(
            "select", "select_option", {"entity_id": f"select.{prefix}_day_volume", "option": "75"}, blocking=True
        )
        await hass.async_block_till_done()
        client.async_patch_toniebox.assert_not_awaited()

        # 07:00 next day -> 75
        freezer.move_to("2026-11-04 07:00:00+01:00")
        async_fire_time_changed(hass, dt_util.utcnow())
        await hass.async_block_till_done()
        client.async_patch_toniebox.assert_awaited_once_with("H1", "4QN986SP", maxVolume=75)

        # storage persisted
        assert hass.states.get(f"switch.{prefix}_volume_schedule").attributes["day_volume"] == 75
