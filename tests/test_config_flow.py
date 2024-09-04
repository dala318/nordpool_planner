"""config_flow tests."""

from unittest import mock

import pytest
from pytest_homeassistant_custom_component.async_mock import patch

from custom_components.nordpool_planner import config_flow
from homeassistant import config_entries


async def test_flow_init(hass):
    """Test the initial flow."""
    result = await hass.config_entries.flow.async_init(
        config_flow.DOMAIN, context={"source": "user"}
    )

    expected = {
        "data_schema": config_flow.DATA_SCHEMA,
        "description_placeholders": None,
        "errors": {},
        "flow_id": mock.ANY,
        "handler": "steam_wishlist",
        "step_id": "user",
        "type": "form",
    }
    assert expected == result
