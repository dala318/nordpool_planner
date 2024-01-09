from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol
from homeassistant.config_entries import ConfigEntry
import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity
from homeassistant.components.number import NumberEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import dt

from . import DOMAIN

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Setup sensor platform for the ui"""
    # config = config_entry.data
    planner = hass.data[DOMAIN][config_entry.entry_id]
    async_add_entities([NordpoolPlannerNumber(planner)])

    # _dry_setup(hass, config, async_add_devices)
    return True


class NordpoolPlannerNumber(NumberEntity):
    # _attr_icon = "mdi:flash"

    def __init__(
        self,
        planner,
    ) -> None:
        # Input configs
        self._planner = planner

        # # Output states
        # self._attr_is_on = STATE_UNKNOWN
        # self._starts_at = STATE_UNKNOWN
        # self._cost_at = STATE_UNKNOWN
        # self._now_cost_rate = STATE_UNKNOWN

    # @property
    # def extra_state_attributes(self):
    #     """Provide attributes for the entity"""
    #     return {
    #         "starts_at": self._starts_at,
    #         "cost_at": self._cost_at,
    #         "now_cost_rate": self._now_cost_rate,
    #     }

    # @callback
    # def _handle_coordinator_update(self) -> None:
    #     """Handle updated data from the coordinator."""
    #     try:
    #         self._latest_measurement = self.coordinator.data.get_measurement(
    #             self._account.id, self._latest_measurement.parameter
    #         )
    #         self.async_write_ha_state()
    #     except StopIteration:
    #         _LOGGER.error(
    #             "Could not find a measurement matching id:%s and parameter:%s",
    #             self._account.id,
    #             self._latest_measurement.parameter,
    #         )

    @property
    def name(self) -> str:
        return "Planner Number"

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    # @property
    # def unit(self) -> str:
    #     """Unit"""
    #     return self._price_type

    # @property
    # def unit_of_measurement(self) -> str:  # FIXME
    #     """Return the unit of measurement this sensor expresses itself in."""
    #     _currency = self._currency
    #     if self._use_cents is True:
    #         # Convert unit of measurement to cents based on chosen currency
    #         _currency = _CURRENTY_TO_CENTS[_currency]
    #     return "%s/%s" % (_currency, self._price_type)

    @property
    def unique_id(self):
        name = "nordpool_planner_%s" % (self.name,)
        name = name.lower().replace(".", "")
        return name
