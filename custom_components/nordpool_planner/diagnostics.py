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
        # "config_entry": config_entry,  # Already included in the planner
        "planner": hass.data[DOMAIN][config_entry.entry_id],
    }

    return diag_data
