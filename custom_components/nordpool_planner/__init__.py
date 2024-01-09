from __future__ import annotations
import logging

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nordpool_planner"
PLATFORMS = [Platform.BINARY_SENSOR]

CONF_TYPE = "type"
CONF_TYPE_LIST = ["moving", "static"]
CONF_ENTITY = "entity"


class NordpoolPlanner:
    def __init__(self, hass, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        # super().__init__(
        #     hass,
        #     _LOGGER,
        #     name="Nordpool Planner",
        #     # update_interval=timedelta(seconds=30),
        #     # update_method=self._async_update_data,
        # )
        self._hass = hass
        self._config = config_entry
        type = config_entry.data[CONF_TYPE]
        np_entity_id = config_entry.data[CONF_ENTITY]
        if np_entity_id is not None:
            # self.async_on_remove(
            #     async_track_state_change_event(
            #         self._hass,
            #         [np_entity_id],
            #         self._async_input_changed,
            #     )
            # )
            async_track_state_change_event(
                self._hass,
                [np_entity_id],
                self._async_input_changed,
            )

        # @property
        # def _nordpool_entity(self):
        #     return config_entry

        # # Input configs
        # self._nordpool_entity = nordpool_entity
        # self._duration = duration
        # self._var_duration_entity = var_duration_entity
        # self._accept_cost = accept_cost
        # self._accept_rate = accept_rate

        # # Entity identification
        # entity_id = entity_id.replace(" ", "_")
        # self._attr_name = f"nordpool_planner_{entity_id}"
        # self._attr_unique_id = entity_id

        # # Internal state
        # self._np = None

        # # Output states
        # self._attr_is_on = STATE_UNKNOWN
        # self._starts_at = STATE_UNKNOWN
        # self._cost_at = STATE_UNKNOWN
        # self._now_cost_rate = STATE_UNKNOWN

    async def _async_input_changed(self, event):
        new_state = event.data.get("new_state")
        _LOGGER.info("Sensor change: %s", new_state)

    async def _async_sensor_changed(self, event):
        """Handle temperature changes."""
        new_state = event.data.get("new_state")
        _LOGGER.info("Sensor change: %s", new_state)
        if new_state is None or new_state.state in (STATE_UNAVAILABLE, STATE_UNKNOWN):
            return
        # self._async_update_temp(new_state)
        # await self._async_control_climate()
        # self.async_write_ha_state()

    # async def _async_update_data(self):
    #     """Fetch data from API endpoint."""
    #     try:
    #         async with async_timeout.timeout(10):
    #             return await self.api.request()
    #     # except ApiAuthError as err:
    #     # except GraphQLErroras as err:
    #     except TransportQueryError as err:
    #         # Raising ConfigEntryAuthFailed will cancel future updates
    #         # and start a config flow with SOURCE_REAUTH (async_step_reauth)
    #         raise ConfigEntryAuthFailed from err
    #     except Exception as err:
    #         raise UpdateFailed(f"Unknown error communicating with API: {err}") from err


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if config_entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][config_entry.entry_id] = planner = NordpoolPlanner(
            hass, config_entry
        )
    else:
        planner = hass.data[DOMAIN][config_entry.entry_id]
    # await planner.async_config_entry_first_refresh()

    if config_entry is not None:
        if config_entry.source == SOURCE_IMPORT:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
            return False

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading a config_flow entry"""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the HACS config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)


# async def async_setup(hass: HomeAssistant, config: Config) -> bool:
#     hass.data.setdefault(DOMAIN, {})
#     return True


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     entry_data = dict(entry.data)
#     hass.data[DOMAIN][entry.entry_id] = entry_data
#     await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
#     return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
#     if unload_ok:
#         hass.data[DOMAIN].pop(entry.entry_id)
#     return unload_ok
