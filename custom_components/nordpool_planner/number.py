from __future__ import annotations

import logging
from homeassistant.components.number import NumberEntityDescription, RestoreNumber
from homeassistant.components.number.const import NumberDeviceClass
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, UnitOfTime
from homeassistant.core import HomeAssistant

from .const import (
    DOMAIN,
)

from . import (
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_DURATION_ENTITY,
    CONF_END_TIME_ENTITY,
    CONF_SEARCH_LENGTH_ENTITY,
    NordpoolPlanner,
    NordpoolPlannerEntity,
)

_LOGGER = logging.getLogger(__name__)

DURATION_ENTITY_DESCRIPTION = NumberEntityDescription(
    key=CONF_DURATION_ENTITY,
    device_class=NumberDeviceClass.DURATION,
    native_min_value=1,
    native_max_value=8,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.HOURS,
)
ACCEPT_COST_ENTITY_DESCRIPTION = NumberEntityDescription(
    key=CONF_ACCEPT_COST_ENTITY,
    device_class=NumberDeviceClass.MONETARY,
    native_min_value=-20.0,
    native_max_value=20.0,
    native_step=0.01,
)
ACCEPT_RATE_ENTITY_DESCRIPTION = NumberEntityDescription(
    key=CONF_ACCEPT_RATE_ENTITY,
    device_class=NumberDeviceClass.DATA_RATE,
    native_min_value=-1.0,
    native_max_value=1.0,
    native_step=0.1,
)
SEARCH_LENGTH_ENTITY_DESCRIPTION = NumberEntityDescription(
    key=CONF_SEARCH_LENGTH_ENTITY,
    device_class=NumberDeviceClass.DURATION,
    native_min_value=3,
    native_max_value=12,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.HOURS,
)
END_TIME_ENTITY_DESCRIPTION = NumberEntityDescription(
    key=CONF_END_TIME_ENTITY,
    device_class=NumberDeviceClass.DURATION,
    native_min_value=0,
    native_max_value=23,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.HOURS,
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Setup sensor platform for the ui"""
    planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    if (CONF_DURATION_ENTITY in config_entry.options.keys() and
        config_entry.options[CONF_DURATION_ENTITY]
    ):
        entities.append(NordpoolPlannerNumber(
            planner, callback=planner.input_changed, start_val=3,
            entity_description=DURATION_ENTITY_DESCRIPTION))

    if (CONF_ACCEPT_COST_ENTITY in config_entry.options.keys() and
        config_entry.options[CONF_ACCEPT_COST_ENTITY]
    ):
        entities.append(NordpoolPlannerNumber(
            planner, callback=planner.input_changed, start_val=0.0,
            entity_description=ACCEPT_COST_ENTITY_DESCRIPTION))

    if (CONF_ACCEPT_RATE_ENTITY in config_entry.options.keys() and
        config_entry.options[CONF_ACCEPT_RATE_ENTITY]
    ):
        entities.append(NordpoolPlannerNumber(
            planner, callback=planner.input_changed, start_val=0.1,
            entity_description=ACCEPT_RATE_ENTITY_DESCRIPTION))

    if (CONF_SEARCH_LENGTH_ENTITY in config_entry.options.keys() and
        config_entry.options[CONF_SEARCH_LENGTH_ENTITY]
    ):
        entities.append(NordpoolPlannerNumber(
            planner, callback=planner.input_changed, start_val=10,
            entity_description=SEARCH_LENGTH_ENTITY_DESCRIPTION))

    if (CONF_END_TIME_ENTITY in config_entry.options.keys() and
        config_entry.options[CONF_END_TIME_ENTITY]
    ):
        entities.append(NordpoolPlannerNumber(
            planner, callback=planner.input_changed, start_val=7,
            entity_description=END_TIME_ENTITY_DESCRIPTION))

    async_add_entities(entities)
    return True

class NordpoolPlannerNumber(NordpoolPlannerEntity, RestoreNumber):

    def __init__(
        self,
        planner,
        callback,
        start_val,
        entity_description: NumberEntityDescription,
    ) -> None:
        super().__init__(planner)
        self.entity_description = entity_description
        self._callback = callback
        self._attr_name = self._planner.name  + " " + entity_description.key.replace("_", " ")
        self._attr_unique_id = ("nordpool_planner_" + self._attr_name).lower().replace(".", "").replace(" ", "_")
        self._attr_native_value = start_val

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

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and (
            last_number_data := await self.async_get_last_number_data()
        ):
            if last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                self._attr_native_value = last_number_data.native_value
        self._planner.register_number_entity(self.entity_id, self.entity_description.key)

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        _LOGGER.debug(
            "Got new async value %s for %s",
            value,
            self.name,
        )
        self._callback(value)
        self.async_schedule_update_ha_state()
