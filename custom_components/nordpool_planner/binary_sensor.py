"""Binary sensor definitions."""

from __future__ import annotations

import logging

from homeassistant.components.binary_sensor import (
    BinarySensorEntity,
    BinarySensorEntityDescription,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from . import NordpoolPlanner, NordpoolPlannerEntity
from .const import CONF_LOW_COST_ENTITY, DOMAIN

_LOGGER = logging.getLogger(__name__)

LOW_COST_ENTITY_DESCRIPTION = BinarySensorEntityDescription(
    key=CONF_LOW_COST_ENTITY,
    # device_class=BinarySensorDeviceClass.???,
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Create state binary sensor entities for platform."""

    planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    if config_entry.data.get(CONF_LOW_COST_ENTITY):
        entities.append(
            NordpoolPlannerBinarySensor(
                planner, entity_description=LOW_COST_ENTITY_DESCRIPTION
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
        _LOGGER.debug(
            'Reading state "%s" of binary sensor "%s"',
            self._planner.low_cost_state.is_on,
            self.unique_id,
        )
        return self._planner.low_cost_state.is_on

    @property
    def extra_state_attributes(self):
        """Extra state attributes."""
        return {
            "starts_at": self._planner.low_cost_state.starts_at,
            "cost_at": self._planner.low_cost_state.cost_at,
            "now_cost_rate": self._planner.low_cost_state.now_cost_rate,
        }

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        self._planner.register_output_listner_entity(self, self.entity_description.key)

    def update_callback(self) -> None:
        """Call from planner that new data avaialble."""
        self.schedule_update_ha_state()

    # async def async_update(self):
    #     """Called from Home Assistant to update entity value"""

    #     self._planner.update()

    # self._update_np_prices()
    # if self._np is not None:
    #     search_length = min(
    #         self._get_input_entity_or_default(
    #             self._var_search_length_entity, self._search_length
    #         ),
    #         self._search_length,
    #     )
    #     self._update(dt.now().hour, search_length)
