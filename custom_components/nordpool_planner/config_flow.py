"""Config flow for PoolLab integration."""
from __future__ import annotations
import logging
import voluptuous as vol
from typing import Any, Dict, Optional

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    DOMAIN,
    CONF_NAME,
    CONF_NP_ENTITY,
    CONF_TYPE,
    CONF_TYPE_MOVING,
    CONF_TYPE_STATIC,
    CONF_TYPE_LIST,
    CONF_LOW_COST_ENTITY,
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_DURATION_ENTITY,
    CONF_END_TIME_ENTITY,
    CONF_SEARCH_LENGTH_ENTITY,
)


_LOGGER = logging.getLogger(__name__)


# def optional_value(value: Any):
#     """Validate Entity ID if not Empty"""
#     if value is None:
#         return None
#     return vol.All(vol.Coerce(int), vol.Range(min=0, max=8))


class NordpoolPlannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Nordpool Planner config flow."""

    VERSION = 1
    _reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: Optional[Dict[str, Any]] | None = None
    ) -> FlowResult:
        """Handle initial user step."""
        errors: Dict[str, str] = {}

        if user_input is not None:
            self.data = user_input
            # Add those that are not optional
            self.data[CONF_LOW_COST_ENTITY] = True
            self.data[CONF_DURATION_ENTITY] = True
            self.data[CONF_SEARCH_LENGTH_ENTITY] = True
            self.data[CONF_END_TIME_ENTITY] = True
            self.data[CONF_LOW_COST_ENTITY] = True

            await self.async_set_unique_id(
                self.data[CONF_NAME] + "_" +
                self.data[CONF_NP_ENTITY] + "_" +
                self.data[CONF_TYPE])
            self._abort_if_unique_id_configured()

            return self.async_create_entry(title=self.data[CONF_NAME], data=self.data)

        sensor_entities = self.hass.states.async_entity_ids(domain_filter="sensor")
        sensor_entities = [s for s in sensor_entities if "nordpool" in s]
        if len(sensor_entities) == 0:
            errors["base"] = "No Nordpool entity found"

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=CONF_TYPE_LIST),
                ),
                vol.Required(CONF_NP_ENTITY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=sensor_entities),
                ),
                vol.Required(CONF_ACCEPT_COST_ENTITY, default=False):
                    bool
                ,
                vol.Required(CONF_ACCEPT_RATE_ENTITY, default=False):
                    bool
                ,
            }
        )

        placeholders = {
            CONF_TYPE: CONF_TYPE_LIST,
            CONF_NP_ENTITY: sensor_entities,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=schema,
            description_placeholders=placeholders,
            errors=errors,
        )

    # async def async_step_import(
    #     self, user_input: Optional[Dict[str, Any]] | None = None
    # ) -> FlowResult:
    #     """Import nordpool planner config from configuration.yaml."""
    #     return await self.async_step_user(import_data)

    # async def async_step_reconfigure(
    #     self, user_input: Optional[Dict[str, Any]] | None = None
    # ) -> FlowResult:
    #     if user_input is not None:
    #         pass  # TODO: process user input
    #     return self.async_show_form(
    #         step_id="reconfigure",
    #         data_schema=vol.Schema({vol.Required("input_parameter"): str}),
    #     )