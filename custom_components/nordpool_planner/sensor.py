"""Binary sensor definitions."""

from __future__ import annotations

import logging

from homeassistant.components.sensor import SensorEntity, SensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant

from . import NordpoolPlanner, NordpoolPlannerEntity
from .const import (
    CONF_HIGH_COST_ENTITY,
    CONF_LOW_COST_ENTITY,
    CONF_STARTS_AT_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_LOW_COST_STARTS_AT_ENTITY = (
    CONF_LOW_COST_ENTITY.replace("_entity", "") + "_" + CONF_STARTS_AT_ENTITY
)
CONF_HIGH_COST_STARTS_AT_ENTITY = (
    CONF_HIGH_COST_ENTITY.replace("_entity", "") + "_" + CONF_STARTS_AT_ENTITY
)

LOW_COST_START_AT_ENTITY_DESCRIPTION = SensorEntityDescription(
    key=CONF_LOW_COST_STARTS_AT_ENTITY,
    # device_class=SensorDeviceClass.???,
)

HIGH_COST_START_AT_ENTITY_DESCRIPTION = SensorEntityDescription(
    key=CONF_HIGH_COST_STARTS_AT_ENTITY,
    # device_class=SensorDeviceClass.???,
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Create state sensor entities for platform."""

    planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    if config_entry.data.get(CONF_STARTS_AT_ENTITY):
        if config_entry.data.get(CONF_LOW_COST_ENTITY):
            entities.append(
                NordpoolPlannerSensor(
                    planner,
                    entity_description=LOW_COST_START_AT_ENTITY_DESCRIPTION,
                )
            )

        if config_entry.data.get(CONF_HIGH_COST_ENTITY):
            entities.append(
                NordpoolPlannerSensor(
                    planner,
                    entity_description=HIGH_COST_START_AT_ENTITY_DESCRIPTION,
                )
            )

    async_add_entities(entities)
    return True


class NordpoolPlannerSensor(NordpoolPlannerEntity, SensorEntity):
    """State sensor."""

    _attr_icon = "mdi:flash"

    def __init__(
        self,
        planner,
        entity_description: SensorEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(planner)
        self.entity_description = entity_description
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

    @property
    def native_value(self):
        """Output state."""
        state = STATE_UNKNOWN
        # TODO: This can be made nicer to get value from states in dictionary in planner
        if self.entity_description.key == CONF_LOW_COST_STARTS_AT_ENTITY:
            if self._planner.low_cost_state.starts_at not in [
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ]:
                state = self._planner.low_cost_state.starts_at
        if self.entity_description.key == CONF_HIGH_COST_STARTS_AT_ENTITY:
            if self._planner.high_cost_state.starts_at not in [
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ]:
                state = self._planner.high_cost_state.starts_at
        _LOGGER.debug(
            'Returning state "%s" of sensor "%s"',
            state,
            self.unique_id,
        )
        return state

    # @property
    # def extra_state_attributes(self):
    #     """Extra state attributes."""
    #     state_attributes = {
    #         "cost_at": STATE_UNKNOWN,
    #         "now_cost_rate": STATE_UNKNOWN,
    #     }
    #     # TODO: This can be made nicer to get value from states in dictionary in planner
    #     if self.entity_description.key == CONF_LOW_COST_STARTS_AT_ENTITY:
    #         state_attributes = {
    #             "cost_at": self._planner.low_cost_state.cost_at,
    #             "now_cost_rate": self._planner.low_cost_state.now_cost_rate,
    #         }
    #     _LOGGER.debug(
    #         'Returning extra state attributes "%s" of sensor "%s"',
    #         state_attributes,
    #         self.unique_id,
    #     )
    #     return state_attributes

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        self._planner.register_output_listener_entity(self, self.entity_description.key)

    def update_callback(self) -> None:
        """Call from planner that new data available."""
        self.schedule_update_ha_state()

    # async def async_update(self):
    #     """Called from Home Assistant to update entity value"""
    #     self._planner.update()
