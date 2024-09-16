"""planner tests."""

from unittest import mock

from custom_components.nordpool_planner import NordpoolPlanner
import pytest

# from pytest_homeassistant_custom_component.async_mock import patch
# from pytest_homeassistant_custom_component.common import (
#     MockModule,
#     MockPlatform,
#     mock_integration,
#     mock_platform,
# )

from custom_components.nordpool_planner.const import *
from homeassistant import config_entries

# from homeassistant.components import sensor
# from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

NAME = "My planner 1"
TYPE = "moving"
DURATION_ENT = "duration_ent"
SEARCH_LENGTH_ENT = "search_len"
NP_ENT = "sensor.np_ent"
CURRENCY = "EUR"

CONF_ENTRY = config_entries.ConfigEntry(
    data={
        CONF_NAME: NAME,
        CONF_TYPE: TYPE,
        CONF_NP_ENTITY: NP_ENT,
        CONF_DURATION_ENTITY: DURATION_ENT,
        CONF_SEARCH_LENGTH_ENTITY: SEARCH_LENGTH_ENT,
    },
    options={CONF_CURENCY: CURRENCY},
    domain=DOMAIN,
    version=1,
    minor_version=2,
    source="user",
    title="Nordpool Planner",
    unique_id="123456",
)


@pytest.mark.asyncio
async def test_planner_init(hass):
    """Test the planner initialization."""

    # async def async_setup_entry_init(
    #     hass: HomeAssistant, config_entry: config_entries.ConfigEntry
    # ) -> bool:
    #     """Set up test config entry."""
    #     await hass.config_entries.async_forward_entry_setups(
    #         config_entry, [sensor.DOMAIN]
    #     )
    #     return True

    # mock_integration(
    #     hass,
    #     MockModule(
    #         "nordpool",
    #         async_setup_entry=async_setup_entry_init,
    #     ),
    # )

    # # Fake nordpool sensor
    # np_sensor = sensor.SensorEntity()
    # np_sensor.entity_id = NP_ENT
    # np_sensor._attr_device_class = sensor.SensorDeviceClass.MONETARY

    # async def async_setup_entry_platform(
    #     hass: HomeAssistant,
    #     config_entry: config_entries.ConfigEntry,
    #     async_add_entities: AddEntitiesCallback,
    # ) -> None:
    #     """Set up test sensor platform via config entry."""
    #     async_add_entities([np_sensor])

    # mock_platform(
    #     hass,
    #     f"{"nordpool"}.{sensor.DOMAIN}",
    #     MockPlatform(async_setup_entry=async_setup_entry_platform),
    # )

    planner = NordpoolPlanner(hass, CONF_ENTRY)

    assert planner.name == NAME
    assert planner._is_static == False
    assert planner._is_moving == True
