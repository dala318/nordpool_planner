"""Diagnostics support for Nordpool Planner."""

from __future__ import annotations

# import json
import logging
from typing import Any

# from homeassistant.components.diagnostics import async_redact_data
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import NordpoolPlanner
from .const import DOMAIN

_LOGGER = logging.getLogger(__name__)

# TO_REDACT = []


async def async_get_config_entry_diagnostics(
    hass: HomeAssistant, config_entry: ConfigEntry
) -> dict[str, Any]:
    """Return diagnostics for a config entry."""
    diag_data = {
        # "config_entry": async_redact_data(config_entry, TO_REDACT),
        # "planner": async_redact_data(hass.data[DOMAIN][config_entry.entry_id], TO_REDACT),
        "config_entry": config_entry,
        "planner": hass.data[DOMAIN][config_entry.entry_id],
    }
    # planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    # if planner is not None:
    #     # diag_data["planner"] = planner.__dict__
    #     # diag_data["prices"] = planner._prices_entity.__dict__
    # else:
    #     _LOGGER.warning("NordpoolPlanner is not available")

    return diag_data
