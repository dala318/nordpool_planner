"""Config flow for PoolLab integration."""
from __future__ import annotations
import logging
import selectors
from types import NoneType
import voluptuous as vol
from collections.abc import Mapping
from typing import Any, Dict, Optional

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry as er, selector
from homeassistant import config_entries

# from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult

from . import (
    DOMAIN,
    CONF_ACCEPT_COST,
    CONF_ACCEPT_RATE,
    CONF_DURATION,
    CONF_END_TIME,
    CONF_NAME,
    CONF_NP_ENTITY,
    CONF_TYPE,
    CONF_TYPE_LIST,
    CONF_SEARCH_LENGTH,
)

# from .lib import poollab

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

            await self.async_set_unique_id(
                self.data[CONF_NAME] + "_" +
                self.data[CONF_NP_ENTITY] + "_" +
                self.data[CONF_TYPE])
            self._abort_if_unique_id_configured()

            # Set not defined values to none (to create config entity)
            if CONF_DURATION not in self.data.keys():
                self.data[CONF_DURATION] = None
            if CONF_ACCEPT_COST not in self.data.keys():
                self.data[CONF_ACCEPT_COST] = None
            if CONF_ACCEPT_RATE not in self.data.keys():
                self.data[CONF_ACCEPT_RATE] = None

            if self.data[CONF_TYPE] == 'moving':
                return await self.async_step_user_moving()
            elif self.data[CONF_TYPE] == 'static':
                return await self.async_step_user_static()
            else:
                errors["base"] = "No valid type given"

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
                vol.Optional(CONF_DURATION): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=8)
                ),
                vol.Optional(CONF_ACCEPT_RATE): vol.All(
                    vol.Coerce(float), vol.Range(min=-10.0, max=10.0)
                ),
                vol.Optional(CONF_ACCEPT_COST): vol.All(
                    vol.Coerce(float), vol.Range(min=-100.0, max=100.0)
                ),
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

    async def async_step_user_moving(
        self, user_input: Optional[Dict[str, Any]] | None = None
    ) -> FlowResult:
        """Second step in config flow to set options for moving planner."""
        # errors = {}
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Validate the settings.
            # try:
            #     pass
            # except ValueError:
            #     errors["base"] = "Some error occured"

            if not errors:
                self.data['moving'] = user_input
                # Set not defined values to none (to create config entity)
                if CONF_DURATION not in self.data["moving"].keys():
                    self.data["moving"][CONF_DURATION] = None
                return self.async_create_entry(title="Nordpool Planner", data=self.data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_SEARCH_LENGTH): vol.All(
                    vol.Coerce(int), vol.Range(min=2, max=24)
                ),
            }
        )

        placeholders = {
            # CONF_SEARCH_LENGTH: CONF_TYPE_LIST,
            # CONF_NP_ENTITY: sensor_entities,
        }

        return self.async_show_form(
            step_id="user_moving",
            data_schema=schema,
            # description_placeholders=placeholders,
            errors=errors,
        )

    async def async_step_user_static(
        self, user_input: Optional[Dict[str, Any]] | None = None
    ) -> FlowResult:
        """Second step in config flow to set options for static planner."""
        # errors = {}
        errors: Dict[str, str] = {}
        if user_input is not None:
            # Validate the settings.
            # try:
            #     pass
            # except ValueError:
            #     errors["base"] = "Some error occured"

            if not errors:
                self.data['static'] = user_input
                # Set not defined values to none (to create config entity)
                if CONF_DURATION not in self.data["static"].keys():
                    self.data["static"][CONF_DURATION] = None
                return self.async_create_entry(title="Nordpool Planner", data=self.data)

        schema = vol.Schema(
            {
                vol.Optional(CONF_END_TIME): vol.All(
                    vol.Coerce(int), vol.Range(min=0, max=23)
                ),
            }
        )

        placeholders = {
            # CONF_SEARCH_LENGTH: CONF_TYPE_LIST,
            # CONF_NP_ENTITY: sensor_entities,
        }

        return self.async_show_form(
            step_id="user_static",
            data_schema=schema,
            # description_placeholders=placeholders,
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