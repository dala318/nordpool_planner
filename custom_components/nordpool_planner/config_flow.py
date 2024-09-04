"""Config flow for PoolLab integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector

from .const import (
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_CURENCY,
    CONF_DURATION_ENTITY,
    CONF_END_TIME_ENTITY,
    CONF_HIGH_COST_ENTITY,
    CONF_LOW_COST_ENTITY,
    CONF_NAME,
    CONF_NP_ENTITY,
    CONF_SEARCH_LENGTH_ENTITY,
    CONF_TYPE,
    CONF_TYPE_LIST,
    CONF_TYPE_MOVING,
    CONF_TYPE_STATIC,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)


class NordpoolPlannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Nordpool Planner config flow."""

    VERSION = 1
    data = None
    options = None
    _reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle initial user step."""
        errors: dict[str, str] = {}

        if user_input is not None:
            self.data = user_input
            # Add those that are not optional
            self.data[CONF_LOW_COST_ENTITY] = True
            self.data[CONF_DURATION_ENTITY] = True
            if self.data[CONF_TYPE] == CONF_TYPE_MOVING:
                self.data[CONF_SEARCH_LENGTH_ENTITY] = True
            elif self.data[CONF_TYPE] == CONF_TYPE_STATIC:
                self.data[CONF_END_TIME_ENTITY] = True

            self.options = {}
            np_entity = self.hass.states.get(self.data[CONF_NP_ENTITY])
            try:
                self.options[CONF_CURENCY] = np_entity.attributes.get(CONF_CURENCY)
            except (IndexError, KeyError):
                _LOGGER.warning("Could not extract currency from Nordpool entity")

            await self.async_set_unique_id(
                self.data[CONF_NAME]
                + "_"
                + self.data[CONF_NP_ENTITY]
                + "_"
                + self.data[CONF_TYPE]
            )
            self._abort_if_unique_id_configured()

            _LOGGER.debug(
                'Creating entry "%s" with data "%s"',
                self.unique_id,
                self.data,
            )
            return self.async_create_entry(
                title=self.data[CONF_NAME], data=self.data, options=self.options
            )

        sensor_entities = self.hass.states.async_entity_ids(domain_filter="sensor")
        selected_entities = [s for s in sensor_entities if "nordpool" in s]
        # TODO: Enable usage for e-ENTSO prices integration
        # selected_entities += [
        #     s for s in sensor_entities if "current_electricity_market_price" in s
        # ]

        if len(selected_entities) == 0:
            errors["base"] = "No Nordpool entity found"

        schema = vol.Schema(
            {
                vol.Required(CONF_NAME): str,
                vol.Required(CONF_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=CONF_TYPE_LIST),
                ),
                vol.Required(CONF_NP_ENTITY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=selected_entities),
                ),
                vol.Required(CONF_ACCEPT_COST_ENTITY, default=False): bool,
                vol.Required(CONF_ACCEPT_RATE_ENTITY, default=False): bool,
                vol.Required(CONF_HIGH_COST_ENTITY, default=False): bool,
            }
        )

        placeholders = {
            CONF_TYPE: CONF_TYPE_LIST,
            CONF_NP_ENTITY: selected_entities,
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
