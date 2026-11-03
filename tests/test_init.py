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


async def test_setup_and_select(hass: HomeAssistant) -> None:
    entry = MockConfigEntry(domain=DOMAIN, data={"username": "u", "password": "p"}, unique_id="uid")
    entry.add_to_hass(hass)

    patched = dict(BOX, maxVolume=50, settingsApplied=False)
    with patch("custom_components.tonies.ToniesClient") as cls:
        client = cls.return_value
        client.async_login = AsyncMock()
        client.async_get_all_tonieboxes = AsyncMock(return_value={BOX["id"]: dict(BOX)})
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
