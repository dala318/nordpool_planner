from __future__ import annotations

import logging
from homeassistant.components.binary_sensor import BinarySensorDeviceClass, BinarySensorEntity, BinarySensorEntityDescription
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import(
    CONF_LOW_COST_ENTITY,
    DOMAIN,
)

from . import (
    NordpoolPlanner,
    NordpoolPlannerEntity
)

_LOGGER = logging.getLogger(__name__)

LOW_COST_ENTITY_DESCRIPTION = BinarySensorEntityDescription(
    key=CONF_LOW_COST_ENTITY,
    # device_class=BinarySensorDeviceClass.???,
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Setup sensor platform for the ui"""
    planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    entities.append(NordpoolPlannerBinarySensor(
        planner,
        entity_description=LOW_COST_ENTITY_DESCRIPTION))

    # TODO: Add for other non-standard binary sensor
    # if (CONF_DURATION_ENTITY in config_entry.options.keys() and
    #     config_entry.options[CONF_DURATION_ENTITY]
    # ):
    #     entities.append(NordpoolPlannerNumber(
    #         planner, callback=planner.input_changed, start_val=3,
    #         entity_description=DURATION_ENTITY_DESCRIPTION))

    async_add_entities(entities)
    return True


class NordpoolPlannerBinarySensor(NordpoolPlannerEntity, BinarySensorEntity):
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        planner,
        entity_description: BinarySensorEntityDescription,
    ) -> None:
        super().__init__(planner)
        self.entity_description = entity_description
        self._attr_name = self._planner.name  + " " + entity_description.key.replace("_", " ")
        self._attr_unique_id = ("nordpool_planner_" + self._attr_name).lower().replace(".", "").replace(" ", "_")

        # # Output states
        # self._attr_is_on = STATE_UNKNOWN
        # self._starts_at = STATE_UNKNOWN
        # self._cost_at = STATE_UNKNOWN
        # self._now_cost_rate = STATE_UNKNOWN


    @property
    def is_on(self):
        return self._planner.state.is_on

    @property
    def extra_state_attributes(self):
        """Provide attributes for the entity"""
        return {
            "starts_at": self._planner.state.starts_at,
            "cost_at": self._planner.state.cost_at,
            "now_cost_rate": self._planner.state.now_cost_rate,
        }

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        # if (last_state := await self.async_get_last_state()) and (
        #     last_number_data := await self.async_get_last_number_data()
        # ):
        #     if last_state.state not in (STATE_UNKNOWN, STATE_UNAVAILABLE):
        #         self._attr_native_value = last_number_data.native_value
        self._planner.register_output_listner_entity(self, self.entity_description.key)


    def update_callback(self) -> None:
        self.schedule_update_ha_state()

    def update(self):
        """Called from Home Assistant to update entity value"""

        # self._planner.update()

        # self._update_np_prices()
        # if self._np is not None:
        #     search_length = min(
        #         self._get_input_entity_or_default(
        #             self._var_search_length_entity, self._search_length
        #         ),
        #         self._search_length,
        #     )
        #     self._update(dt.now().hour, search_length)
