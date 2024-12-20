"""Number definitions."""

from __future__ import annotations

import logging

from homeassistant.components.number import (
    NumberDeviceClass,
    NumberEntityDescription,
    RestoreNumber,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    UnitOfTime,
)
from homeassistant.core import HomeAssistant

from . import NordpoolPlanner, NordpoolPlannerEntity
from .const import (
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_DURATION_ENTITY,
    CONF_END_TIME_ENTITY,
    CONF_SEARCH_LENGTH_ENTITY,
    CONF_START_TIME_ENTITY,
    DOMAIN,
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
    native_min_value=0.1,
    native_max_value=1.0,
    native_step=0.1,
)
SEARCH_LENGTH_ENTITY_DESCRIPTION = NumberEntityDescription(
    key=CONF_SEARCH_LENGTH_ENTITY,
    device_class=NumberDeviceClass.DURATION,
    native_min_value=3,
    native_max_value=23,  # Let's keep it below 24h to not risk wrapping a day.
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
START_TIME_ENTITY_DESCRIPTION = NumberEntityDescription(
    key=CONF_START_TIME_ENTITY,
    device_class=NumberDeviceClass.DURATION,
    native_min_value=0,
    native_max_value=23,
    native_step=1,
    native_unit_of_measurement=UnitOfTime.HOURS,
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Create configuration number entities for platform."""

    planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    if config_entry.data.get(CONF_DURATION_ENTITY):
        entities.append(
            NordpoolPlannerNumber(
                planner,
                start_val=3,
                entity_description=DURATION_ENTITY_DESCRIPTION,
            )
        )

    if config_entry.data.get(CONF_ACCEPT_COST_ENTITY):
        entity_description = ACCEPT_COST_ENTITY_DESCRIPTION
        # Override if currency option is set
        if unit_of_measurement := config_entry.options.get(ATTR_UNIT_OF_MEASUREMENT):
            entity_description = NumberEntityDescription(
                key=ACCEPT_COST_ENTITY_DESCRIPTION.key,
                device_class=ACCEPT_COST_ENTITY_DESCRIPTION.device_class,
                native_min_value=ACCEPT_COST_ENTITY_DESCRIPTION.native_min_value,
                native_max_value=ACCEPT_COST_ENTITY_DESCRIPTION.native_max_value,
                native_step=ACCEPT_COST_ENTITY_DESCRIPTION.native_step,
                native_unit_of_measurement=unit_of_measurement,
            )
        entities.append(
            NordpoolPlannerNumber(
                planner,
                start_val=0.0,
                entity_description=entity_description,
            )
        )

    if config_entry.data.get(CONF_ACCEPT_RATE_ENTITY):
        entities.append(
            NordpoolPlannerNumber(
                planner,
                start_val=0.1,
                entity_description=ACCEPT_RATE_ENTITY_DESCRIPTION,
            )
        )

    if config_entry.data.get(CONF_SEARCH_LENGTH_ENTITY):
        entities.append(
            NordpoolPlannerNumber(
                planner,
                start_val=10,
                entity_description=SEARCH_LENGTH_ENTITY_DESCRIPTION,
            )
        )

    if config_entry.data.get(CONF_END_TIME_ENTITY):
        entities.append(
            NordpoolPlannerNumber(
                planner,
                start_val=7,
                entity_description=END_TIME_ENTITY_DESCRIPTION,
            )
        )

    if config_entry.data.get(CONF_START_TIME_ENTITY):
        entities.append(
            NordpoolPlannerNumber(
                planner,
                start_val=18,
                entity_description=START_TIME_ENTITY_DESCRIPTION,
            )
        )

    async_add_entities(entities)
    return True


class NordpoolPlannerNumber(NordpoolPlannerEntity, RestoreNumber):
    """Number config entity."""

    def __init__(
        self,
        planner,
        start_val,
        entity_description: NumberEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(planner)
        self.entity_description = entity_description
        self._default_value = start_val
        self._attr_name = (
            self._planner.name
            + " "
            + entity_description.key.replace("_entity", "").replace("_", " ")
        )
        self._attr_unique_id = (
            ("nordpool_planner_" + self._attr_name)
            .lower()
            .replace(".", "")
            .replace(" ", "_")
        )

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        if (last_state := await self.async_get_last_state()) and (
            last_number_data := await self.async_get_last_number_data()
        ):
            if last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
                self._attr_native_value = last_number_data.native_value
        else:
            self._attr_native_value = self._default_value
        self._planner.register_input_entity_id(
            self.entity_id, self.entity_description.key
        )

    async def async_set_native_value(self, value: float) -> None:
        """Update the current value."""
        self._attr_native_value = value
        _LOGGER.debug(
            "Got new async value %s for %s",
            value,
            self.name,
        )
        self.async_schedule_update_ha_state()
