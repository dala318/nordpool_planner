"""Config flow for PoolLab integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import ATTR_NAME, ATTR_UNIT_OF_MEASUREMENT
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector, template

from .const import (
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_DURATION_ENTITY,
    CONF_END_TIME_ENTITY,
    CONF_HEALTH_ENTITY,
    CONF_HIGH_COST_ENTITY,
    CONF_LOW_COST_ENTITY,
    CONF_PRICES_ENTITY,
    CONF_SEARCH_LENGTH_ENTITY,
    CONF_START_TIME_ENTITY,
    CONF_STARTS_AT_ENTITY,
    CONF_TYPE,
    CONF_TYPE_LIST,
    CONF_TYPE_MOVING,
    CONF_TYPE_STATIC,
    CONF_USED_HOURS_LOW_ENTITY,
    DOMAIN,
    NAME_FILE_READER,
    PATH_FILE_READER,
)
from .helpers import get_np_from_file

_LOGGER = logging.getLogger(__name__)

ENTOSOE_DOMAIN = None
try:
    from ..entsoe.const import DOMAIN as ENTOSOE_DOMAIN
except ImportError:
    _LOGGER.warning("Could not import ENTSO-e integration")

NORDPOOL_DOMAIN = None
try:
    from ..nordpool import DOMAIN as NORDPOOL_DOMAIN
except ImportError:
    _LOGGER.warning("Could not import Nord Pool integration")


class NordpoolPlannerConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Nordpool Planner config flow."""

    VERSION = 2
    MINOR_VERSION = 2
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
                self.data[CONF_START_TIME_ENTITY] = True
                self.data[CONF_END_TIME_ENTITY] = True
                self.data[CONF_USED_HOURS_LOW_ENTITY] = True

            self.options = {}
            if self.data[CONF_PRICES_ENTITY] == NAME_FILE_READER:
                np_entity = get_np_from_file(PATH_FILE_READER)
            else:
                np_entity = self.hass.states.get(self.data[CONF_PRICES_ENTITY])

            try:
                self.options[ATTR_UNIT_OF_MEASUREMENT] = np_entity.attributes.get(
                    ATTR_UNIT_OF_MEASUREMENT
                )
            except (IndexError, KeyError):
                _LOGGER.warning("Could not extract currency from Nordpool entity")

            await self.async_set_unique_id(
                self.data[ATTR_NAME]
                + "_"
                + self.data[CONF_PRICES_ENTITY]
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
                title=self.data[ATTR_NAME], data=self.data, options=self.options
            )

        selected_entities = []
        if NORDPOOL_DOMAIN:
            selected_entities.extend(
                template.integration_entities(self.hass, NORDPOOL_DOMAIN)
            )
        if ENTOSOE_DOMAIN:
            ent = template.integration_entities(self.hass, ENTOSOE_DOMAIN)
            selected_entities.extend([s for s in ent if "average" in s])
        selected_entities.append(NAME_FILE_READER)

        schema = vol.Schema(
            {
                vol.Required(ATTR_NAME): str,
                vol.Required(CONF_TYPE): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=CONF_TYPE_LIST),
                ),
                vol.Required(CONF_PRICES_ENTITY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=selected_entities),
                ),
                vol.Required(CONF_ACCEPT_COST_ENTITY, default=False): bool,
                vol.Required(CONF_ACCEPT_RATE_ENTITY, default=False): bool,
                vol.Required(CONF_HIGH_COST_ENTITY, default=False): bool,
                vol.Required(CONF_STARTS_AT_ENTITY, default=False): bool,
                vol.Required(CONF_HEALTH_ENTITY, default=True): bool,
            }
        )

        placeholders = {
            CONF_TYPE: CONF_TYPE_LIST,
            CONF_PRICES_ENTITY: selected_entities,
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
