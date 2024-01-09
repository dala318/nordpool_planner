"""Config flow for PoolLab integration."""
from __future__ import annotations
import logging
import selectors
import voluptuous as vol
from collections.abc import Mapping
from typing import Any

import homeassistant.helpers.config_validation as cv
from homeassistant.helpers import entity_registry as er, selector
from homeassistant import config_entries

# from homeassistant.const import CONF_API_KEY
from homeassistant.data_entry_flow import FlowResult

from . import DOMAIN

# from .lib import poollab

_LOGGER = logging.getLogger(__name__)

CONF_TYPE = "type"
CONF_TYPE_LIST = ["moving", "static"]
CONF_ENTITY = "entity"


class NordpoolPlannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """PoolLab config flow."""

    VERSION = 1
    _reauth_entry: config_entries.ConfigEntry | None = None

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle user step."""
        errors = {}
        # defaults = {
        #     CONF_API_KEY: "",
        # }

        if user_input is not None:
            return self.async_create_entry(title="Nordpool Planner", data=user_input)
            # await self.async_set_unique_id(user_input[CONF_API_KEY])

        #     if not self._reauth_entry:
        #         self._abort_if_unique_id_configured()

        #     # try:
        #     #     await self.is_valid(user_input)
        #     # except InvalidAuth:
        #     #     errors["base"] = "invalid_auth"
        #     # except Exception:  # pylint: disable=broad-except
        #     #     _LOGGER.exception("Unhandled exception in user step")
        #     #     errors["base"] = "unknown"
        #     if not errors:
        #         if self._reauth_entry:
        #             self.hass.config_entries.async_update_entry(
        #                 self._reauth_entry, data=self._reauth_entry.data | user_input
        #             )
        #             await self.hass.config_entries.async_reload(
        #                 self._reauth_entry.entry_id
        #             )
        #             return self.async_abort(reason="reauth_successful")

        #         return self.async_create_entry(title="PoolLab", data=user_input)
        # # elif self._reauth_entry:
        # #     for key in defaults:
        # #         defaults[key] = self._reauth_entry.data.get(key)

        senssor_entities = self.hass.states.async_entity_ids(domain_filter="sensor")
        senssor_entities = [s for s in senssor_entities if "nordpool" in s]
        if len(senssor_entities) == 0:
            errors["base"] = "no_entities"

        user_schema = vol.Schema(
            {
                vol.Required(CONF_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=CONF_TYPE_LIST),
                ),
                vol.Required(CONF_ENTITY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=senssor_entities),
                ),
            }
        )

        placeholders = {
            CONF_TYPE: CONF_TYPE_LIST,
            CONF_ENTITY: senssor_entities,
        }

        return self.async_show_form(
            step_id="user",
            data_schema=user_schema,
            description_placeholders=placeholders,
            errors=errors,
        )

    # async def async_step_import(self, import_data) -> FlowResult:
    #     """Import poollab config from configuration.yaml."""
    #     return await self.async_step_user(import_data)

    async def is_valid(self, user_input):
        """Check for user input errors."""
        # poollab_api = poollab.PoolLabApi(user_input[CONF_API_KEY])
        # if not await poollab_api.test():
        #     raise InvalidAuth
        pass
