"""Main package for planner."""

from __future__ import annotations

import datetime as dt
import logging

from config.custom_components import nordpool
from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import async_track_state_change_event
from homeassistant.util import dt as dt_util

from .const import (
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_DURATION_ENTITY,
    CONF_END_TIME_ENTITY,
    CONF_LOW_COST_ENTITY,
    CONF_NP_ENTITY,
    CONF_SEARCH_LENGTH_ENTITY,
    CONF_TYPE,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER]


# async def async_setup(hass: HomeAssistant, config: Config) -> bool:
#     hass.data.setdefault(DOMAIN, {})
#     return True


# async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     entry_data = dict(entry.data)
#     hass.data[DOMAIN][entry.entry_id] = entry_data
#     await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
#     return True
async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if config_entry.entry_id not in hass.data[DOMAIN]:
        hass.data[DOMAIN][config_entry.entry_id] = NordpoolPlanner(hass, config_entry)
    # else:
    #     planner = hass.data[DOMAIN][config_entry.entry_id]
    # await planner.async_config_entry_first_refresh()

    if config_entry is not None:
        if config_entry.source == SOURCE_IMPORT:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
            return False

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


# async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
#     unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
#     if unload_ok:
#         hass.data[DOMAIN].pop(entry.entry_id)
#     return unload_ok
async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading a config_flow entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)


class NordpoolPlanner:
    """Planner base class."""

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        self._hass = hass
        self._config = config_entry

        # if self._np_entity.unique_id is not None:
        #     self.async_on_remove(
        #         async_track_state_change_event(
        #             self._hass,
        #             [self._np_entity.unique_id],
        #             self._async_input_changed,
        #         )
        #     )

        # Internal states
        self._np_entity = NordpoolEntity(self._config.data[CONF_NP_ENTITY])
        async_track_state_change_event(
            self._hass,
            [self._np_entity.unique_id],
            self._async_input_changed,
        )
        # TODO: Dont seem to work as expected!

        # Configuration entities
        self._duration_number_entity = ""
        self._accept_cost_number_entity = ""
        self._accept_rate_number_entity = ""
        self._search_length_number_entity = ""
        self._end_time_number_entity = ""
        # TODO: Make dictionary?

        # Output entities
        self._low_cost_binary_sensor_entity = None
        # TODO: Make list?

        # Output states
        self.low_cost_state = NordpoolPlannerState()

    @property
    def name(self) -> str:
        """Name of planner."""
        return self._config.data["name"]

    @property
    def _duration(self) -> int:
        """Get duration parameter."""
        return self.get_number_entity_value(self._duration_number_entity, integer=True)

    @property
    def _search_length(self) -> int:
        """Get search length parameter."""
        return self.get_number_entity_value(
            self._search_length_number_entity, integer=True
        )

    @property
    def _end_time(self) -> int:
        """Get end time parameter."""
        return self.get_number_entity_value(self._end_time_number_entity, integer=True)

    @property
    def _accept_cost(self) -> float:
        """Get accept cost parameter."""
        return self.get_number_entity_value(self._accept_cost_number_entity)

    @property
    def _accept_rate(self) -> float:
        """Get accept rate parameter."""
        return self.get_number_entity_value(self._accept_rate_number_entity)

    def get_number_entity_value(
        self, entity_id: str, integer: bool = False
    ) -> float | int | None:
        """Get value of generic entity parameter."""
        if entity_id:
            try:
                entity = self._hass.states.get(entity_id)
                state = entity.state
                value = float(state)
                if integer:
                    return int(value)
                return value  # noqa: TRY300
            except (TypeError, ValueError):
                _LOGGER.warning(
                    'Could not convert value "%s" of entity %s to expected format',
                    state,
                    entity_id,
                )
            except Exception as e:  # noqa: BLE001
                _LOGGER.error(
                    'Unknown error wen reading and converting "%s": %s',
                    entity_id,
                    e,
                )
        else:
            _LOGGER.debug("No entity defined")
        return None

    def register_input_entity_id(self, entity_id, conf_key) -> None:
        """Register input entity id."""
        # Input numbers
        if conf_key == CONF_DURATION_ENTITY:
            self._duration_number_entity = entity_id
        elif conf_key == CONF_ACCEPT_COST_ENTITY:
            self._accept_cost_number_entity = entity_id
        elif conf_key == CONF_ACCEPT_RATE_ENTITY:
            self._accept_rate_number_entity = entity_id
        elif conf_key == CONF_SEARCH_LENGTH_ENTITY:
            self._search_length_number_entity = entity_id
        elif conf_key == CONF_END_TIME_ENTITY:
            self._end_time_number_entity = entity_id
        else:
            _LOGGER.warning(
                'An entity "%s" was registred for callback but no match for key "%s"',
                entity_id,
                conf_key,
            )
        # TODO: Dont seem to work as expected!
        async_track_state_change_event(
            self._hass,
            [entity_id],
            self._async_input_changed,
        )

    def register_output_listner_entity(self, entity, conf_key="") -> None:
        """Register output entity."""
        # Output binary sensors
        if conf_key == CONF_LOW_COST_ENTITY:
            self._low_cost_binary_sensor_entity = entity
        else:
            _LOGGER.warning(
                'An entity "%s" was registred for update but no match for key "%s"',
                entity.entity_id,
                conf_key,
            )

    def get_device_info(self) -> DeviceInfo:
        """Get device info to group entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config.data[CONF_TYPE])},
            name=self.name,
            manufacturer="Nordpool",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(nordpool.DOMAIN, self._np_entity.unique_id),
        )

    def input_changed(self, value):
        """Input entitiy callback to initiate a planner update."""
        _LOGGER.debug("Sensor change event from callback: %s", value)
        self.update()

    async def _async_input_changed(self, event):
        """Input entity change callback from state change event."""
        new_state = event.data.get("new_state")
        _LOGGER.debug("Sensor change event from HASS: %s", new_state)
        self.update()

    def update(self):
        """Public planner update call function."""
        # if self._config.data[CONF_TYPE] == CONF_TYPE_MOVING:
        self._update_legacy(dt_util.now().hour, self._search_length)
        self._update()

    def _update(self) -> None:
        """Planner update call function."""
        _LOGGER.debug("Updating planner")

        # Update inputs
        self._np_entity.update(self._hass)
        if not self._np_entity.valid:
            _LOGGER.warning("Aborting update since no valid Nordpool data")
            return

        if not self._duration:
            _LOGGER.warning("Aborting update since no valid Duration")
            return

        # initialize local variables
        now = dt_util.now()
        min_start_hour = now.hour
        min_average = self._np_entity.current_price

        # np_raw = self._np_entity.prices_raw
        duration = dt.timedelta(hours=self._duration)
        np_range = self._np_entity.get_prices_range(now, now + duration)
        pass

    def _update_legacy(self, start_hour, search_length: int) -> None:
        """Planner update call function."""
        _LOGGER.debug("Updating legacy planner")

        self._np_entity.update(self._hass)
        if not self._np_entity.valid:
            _LOGGER.warning("Aborting update since no valid Nordpool data")
            return

        # Evaluate data
        now = dt_util.now()
        min_average = self._np_entity.current_price
        min_start_hour = now.hour
        # Only search if current is above acceptable rates and in range
        if (
            now.hour >= start_hour
            and not (self._accept_cost is not None and min_average <= self._accept_cost)
            and not (
                self._accept_rate is not None
                and (min_average / self._np_entity.average) <= self._accept_rate
            )
        ):
            duration = self._duration
            if duration is None:
                _LOGGER.warning("Aborting update since no valid Duration")
                return

            for i in range(
                start_hour,
                min(now.hour + search_length, len(self._np_entity.prices) - duration),
            ):
                price_range = self._np_entity.prices[i : i + duration]
                # Nordpool sometimes returns null prices, https://github.com/custom-components/nordpool/issues/125
                # If more than 50% is Null in selected range skip.
                if len([x for x in price_range if x is None]) * 2 > len(price_range):
                    _LOGGER.debug("Skipping range at %s as to many empty", i)
                    continue
                price_range = [x for x in price_range if x is not None]
                average = sum(price_range) / duration
                if average < min_average:
                    min_average = average
                    min_start_hour = i
                    _LOGGER.debug("New min value at %s", i)
                if (
                    self._accept_cost is not None and min_average <= self._accept_cost
                ) or (
                    self._accept_rate is not None
                    and (min_average / self._np_entity.average) <= self._accept_rate
                ):
                    min_average = average
                    min_start_hour = i
                    _LOGGER.debug("Found range under accept level at %s", i)
                    break

        # Write result to entity
        if now.hour >= min_start_hour:
            # self._attr_is_on = True
            self.low_cost_state.is_on = True
        else:
            # self._attr_is_on = False
            self.low_cost_state.is_on = False

        start = dt_util.parse_datetime(f"{now.year}-{now.month}-{now.day} {0}:{0}")
        # Check if next day
        if min_start_hour >= 24:
            start += dt_util.parse_duration("1 day")
            min_start_hour -= 24
        self.low_cost_state.starts_at = "%04d-%02d-%02d %02d:%02d" % (
            start.year,
            start.month,
            start.day,
            min_start_hour,
            0,
        )
        self.low_cost_state.cost_at = min_average
        self.low_cost_state.now_cost_rate = self._np_entity.current_price / min_average

        if self._low_cost_binary_sensor_entity:
            self._low_cost_binary_sensor_entity.update_callback()


class NordpoolEntity:
    """Represenatation for Nordpool state."""

    def __init__(self, unique_id: str) -> None:
        """Initialize state tracker."""
        self._unique_id = unique_id
        self._np = None

    @property
    def unique_id(self) -> str:
        """Get the unique id."""
        return self._unique_id

    @property
    def valid(self) -> bool:
        """Get if data is valid."""
        # TODO: Add more checks, make function of those in update()
        return self._np is not None

    @property
    def prices(self):
        """Get the prices."""
        np_prices = self._np.attributes["today"]
        if self._np.attributes["tomorrow_valid"]:
            np_prices += self._np.attributes["tomorrow"]
        return np_prices

    @property
    def _prices_raw(self):
        np_prices = self._np.attributes["raw_today"]
        if self._np.attributes["tomorrow_valid"]:
            np_prices += self._np.attributes["raw_tomorrow"]
        return np_prices

    @property
    def average(self):
        """Get the average price."""
        return self._np.attributes["average"]

    @property
    def current_price(self):
        """Get the curent price."""
        return self._np.attributes["current_price"]

    def update(self, hass: HomeAssistant) -> None:
        """Update price in storage."""
        np = hass.states.get(self._unique_id)
        if np is None:
            _LOGGER.warning("Got empty data from Norpool entity %s ", self._unique_id)
        elif "today" not in np.attributes:
            _LOGGER.warning(
                "No values for today in Norpool entity %s ", self._unique_id
            )
        else:
            _LOGGER.debug(
                "Nordpool sensor %s was updated sucsessfully", self._unique_id
            )
            if self._np is None:
                pass
                # TODO: Set unit_of_measuremetn of applicable number entities
            self._np = np

        if self._np is None:
            # TODO: Set UNAVAILABLE?
            return

    def get_prices_range(self, start: dt.datetime, end: dt.datetime):
        """Get a range of prices from NP given the start and end datatimes."""
        started = False
        selected = []
        for p in self._prices_raw:
            if p["start"] < start:
                started = True
            if p["start"] > end:  # dt.timedelta(hours=1)
                break
            if started:
                selected.append(p)
        return selected


class NordpoolPlannerState:
    """State attribute representation."""

    def __init__(self) -> None:
        """Initiate states."""
        self.is_on = STATE_UNKNOWN
        self.starts_at = STATE_UNKNOWN
        self.cost_at = STATE_UNKNOWN
        self.now_cost_rate = STATE_UNKNOWN


class NordpoolPlannerEntity(Entity):
    """Base class for nordpool planner entities."""

    def __init__(
        self,
        planner: NordpoolPlanner,
    ) -> None:
        """Initialize entity."""
        # Input configs
        self._planner = planner
        self._attr_device_info = planner.get_device_info()

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False
