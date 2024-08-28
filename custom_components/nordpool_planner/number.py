from __future__ import annotations

import logging
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import DOMAIN, NordpoolPlannerNumber

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Setup sensor platform for the ui"""
    # config = config_entry.data
    # planner = hass.data[DOMAIN][config_entry.entry_id]
    # async_add_entities([NordpoolPlannerNumber(planner)])
    async_add_entities(hass.data[DOMAIN][config_entry.entry_id].get_number_entities())

    # _dry_setup(hass, config, async_add_devices)
    return True

