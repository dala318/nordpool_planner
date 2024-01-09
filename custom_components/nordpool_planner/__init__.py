from __future__ import annotations
import logging

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nordpool_planner"
PLATFORMS = ["binary_sensor"]


class NordpoolPlannerCoordinator(DataUpdateCoordinator):
    def __init__(self, hass, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name="Nordpool Planner",
            # update_interval=timedelta(seconds=30),
            # update_method=self._async_update_data,
        )
        self._config = config_entry

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
        hass.data[DOMAIN][config_entry.entry_id] = planner = NordpoolPlannerCoordinator(
            hass, config_entry
        )
    else:
        planner = hass.data[DOMAIN][config_entry.entry_id]
    await planner.async_config_entry_first_refresh()

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
