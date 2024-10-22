"""Binary sensor definitions."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.util import dt as dt_util

from . import NordpoolPlanner, NordpoolPlannerEntity
from .const import CONF_HIGH_COST_ENTITY, CONF_LOW_COST_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)

# LOW_COST_ENTITY_DESCRIPTION = BinarySensorEntityDescription(
#     key=CONF_LOW_COST_ENTITY,
#     # device_class=BinarySensorDeviceClass.???,
# )


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Create state binary sensor entities for platform."""

    planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    if config_entry.data.get(CONF_LOW_COST_ENTITY):
        entities.append(
            NordpoolPlannerBinarySensor(
                planner,
                entity_description=BinarySensorEntityDescription(
                    key=CONF_LOW_COST_ENTITY,
                    # device_class=BinarySensorDeviceClass.???,
                ),
            )
        )

    if config_entry.data.get(CONF_HIGH_COST_ENTITY):
        entities.append(
            NordpoolPlannerBinarySensor(
                planner,
                entity_description=BinarySensorEntityDescription(
                    key=CONF_HIGH_COST_ENTITY,
                    # device_class=BinarySensorDeviceClass.???,
                ),
            )
        )

    async_add_entities(entities)
    return True


class NordpoolPlannerBinarySensor(NordpoolPlannerEntity, BinarySensorEntity):
    """Binary state sensor."""

    _attr_icon = "mdi:flash"

    def __init__(
        self,
        planner,
        entity_description: BinarySensorEntityDescription,
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
    def is_on(self):
        """Output state."""
        state = None
        # TODO: This can be made nicer to get value from states in dictionary in planner
        if self.entity_description.key == CONF_LOW_COST_ENTITY:
            if self._planner.low_cost_state.starts_at not in [
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ]:
                state = self._planner.low_cost_state.starts_at < dt_util.now()
        if self.entity_description.key == CONF_HIGH_COST_ENTITY:
            if self._planner.high_cost_state.starts_at not in [
                STATE_UNKNOWN,
                STATE_UNAVAILABLE,
            ]:
                state = self._planner.high_cost_state.starts_at < dt_util.now()
        _LOGGER.debug(
            'Returning state "%s" of binary sensor "%s"',
            state,
            self.unique_id,
        )
        return state

    @property
    def extra_state_attributes(self):
        """Extra state attributes."""
        state_attributes = {
            "starts_at": STATE_UNKNOWN,
            "cost_at": STATE_UNKNOWN,
            "current_cost": self._planner.price_now,
            "current_cost_rate": STATE_UNKNOWN,
            "price_sensor": self._planner.price_sensor_id,
        }
        # TODO: This can be made nicer to get value from states in dictionary in planner
        if self.entity_description.key == CONF_LOW_COST_ENTITY:
            state_attributes = {
                "starts_at": self._planner.low_cost_state.starts_at,
                "cost_at": self._planner.low_cost_state.cost_at,
                "current_cost": self._planner.price_now,
                "current_cost_rate": self._planner.low_cost_state.now_cost_rate,
                "price_sensor": self._planner.price_sensor_id,
            }
        elif self.entity_description.key == CONF_HIGH_COST_ENTITY:
            state_attributes = {
                "starts_at": self._planner.high_cost_state.starts_at,
                "cost_at": self._planner.high_cost_state.cost_at,
                "current_cost": self._planner.price_now,
                "current_cost_rate": self._planner.high_cost_state.now_cost_rate,
                "price_sensor": self._planner.price_sensor_id,
            }
        _LOGGER.debug(
            'Returning extra state attributes "%s" of binary sensor "%s"',
            state_attributes,
            self.unique_id,
        )
        return state_attributes

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
