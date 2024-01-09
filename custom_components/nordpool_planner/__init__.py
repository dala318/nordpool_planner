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
from homeassistant.util import dt

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nordpool_planner"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER]

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

        if self._nordpool_entity is not None:
            # self.async_on_remove(
            #     async_track_state_change_event(
            #         self._hass,
            #         [self._nordpool_entity],
            #         self._async_input_changed,
            #     )
            # )
            async_track_state_change_event(
                self._hass,
                [self._nordpool_entity],
                self._async_input_changed,
            )

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

    @property
    def _nordpool_entity(self) -> str:
        return self._config.data[CONF_ENTITY]

    def _update_np_prices(self):
        np = self._hass.states.get(self._nordpool_entity)
        if np is None:
            _LOGGER.warning(
                "Got empty data from Norpool entity %s ", self._nordpool_entity
            )
            return
        if "today" not in np.attributes.keys():
            _LOGGER.warning(
                "No values for today in Norpool entity %s ", self._nordpool_entity
            )
            return
        self._np = np

    @property
    def _np_prices(self):
        np_prices = self._np.attributes["today"]
        if self._np.attributes["tomorrow_valid"]:
            np_prices += self._np.attributes["tomorrow"]
        return np_prices

    @property
    def _np_average(self):
        return self._np.attributes["average"]

    @property
    def _np_current(self):
        return self._np.attributes["current_price"]

    def _get_input_entity_or_default(self, entity_id, default):
        if entity_id:
            input_value = self._hass.states.get(entity_id)
            if not input_value or not input_value.state[0].isdigit():
                return default
            try:
                input_value = int(input_value.state.split(".")[0])
                if input_value is not None:
                    return input_value
            except TypeError:
                _LOGGER.debug(
                    'Could not convert value "%s" of entity %s to int',
                    input_value.state,
                    entity_id,
                )
        return default

    def _update(self, start_hour, search_length: int):
        # Evaluate data
        now = dt.now()
        min_average = self._np_current
        min_start_hour = now.hour
        # Only search if current is above acceptable rates and in range
        if (
            now.hour >= start_hour
            and min_average > self._accept_cost
            and (min_average / self._np_average) > self._accept_rate
        ):
            duration = self._get_input_entity_or_default(
                self._var_duration_entity, self._duration
            )
            for i in range(
                start_hour,
                min(now.hour + search_length, len(self._np_prices) - duration),
            ):
                prince_range = self._np_prices[i : i + duration]
                # Nordpool sometimes returns null prices, https://github.com/custom-components/nordpool/issues/125
                # If more than 50% is Null in selected range skip.
                if len([x for x in prince_range if x is None]) * 2 > len(prince_range):
                    _LOGGER.debug("Skipping range at %s as to many empty", i)
                    continue
                prince_range = [x for x in prince_range if x is not None]
                average = sum(prince_range) / duration
                if average < min_average:
                    min_average = average
                    min_start_hour = i
                    _LOGGER.debug("New min value at %s", i)
                if (
                    average < self._accept_cost
                    or (average / self._np_average) < self._accept_rate
                ):
                    min_average = average
                    min_start_hour = i
                    _LOGGER.debug("Found range under accept level at %s", i)
                    break

        # Write result to entity
        if now.hour >= min_start_hour:
            self._attr_is_on = True
        else:
            self._attr_is_on = False

        start = dt.parse_datetime(
            "%s-%s-%s %s:%s" % (now.year, now.month, now.day, 0, 0)
        )
        # Check if next day
        if min_start_hour >= 24:
            start += dt.parse_duration("1 day")
            min_start_hour -= 24
        self._starts_at = "%04d-%02d-%02d %02d:%02d" % (
            start.year,
            start.month,
            start.day,
            min_start_hour,
            0,
        )
        self._cost_at = min_average
        self._now_cost_rate = self._np_current / min_average


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
