"""planner tests."""

from unittest import mock

from custom_components.nordpool_planner import NordpoolPlanner
import pytest

# from pytest_homeassistant_custom_component.async_mock import patch
import voluptuous as vol

from custom_components.nordpool_planner.const import *
from homeassistant import config_entries
from homeassistant.helpers import selector


@pytest.mark.asyncio
async def test_planner_init(hass):
    """Test the planner initialization."""

    NAME = "planner name"
    TYPE = "moving"
    DURATION_ENT = "duration_ent"
    SEARCH_LENGTH_ENT = "search_len"
    NP_ENT = "sensor.np_ent"
    CURRENCY = "EUR"

    config_entry = config_entries.ConfigEntry(
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

    planner = NordpoolPlanner(hass, config_entry)

    assert planner.name == NAME
    assert planner._is_static == False
    assert planner._is_moving == True


# @pytest.mark.asyncio
# async def test_flow_init(hass):
#     """Test the initial flow."""
#     result = await hass.config_entries.flow.async_init(
#         config_flow.DOMAIN, context={"source": "user"}
#     )

#     expected = {
#         "data_schema": SCHEMA_COPY,
#         # "data_schema": config_flow.DATA_SCHEMA,
#         "description_placeholders": None,
#         "errors": {},
#         "flow_id": mock.ANY,
#         "handler": "nordpool_planner",
#         "step_id": "user",
#         "type": "form",
#     }
#     assert expected == result
