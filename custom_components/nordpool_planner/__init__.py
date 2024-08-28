from __future__ import annotations
import logging
from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.components.number import NumberEntity, NumberEntityDescription

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN, Platform
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_interval,
)
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt

_LOGGER = logging.getLogger(__name__)

DOMAIN = "nordpool_planner"
PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER]

CONF_NAME = "name"
CONF_TYPE = "type"
CONF_TYPE_MOVING = "moving"
CONF_TYPE_STATIC = "static"
CONF_TYPE_LIST = [CONF_TYPE_MOVING, CONF_TYPE_STATIC]
CONF_NP_ENTITY = "np_entity"
CONF_DURATION = "duration"
CONF_DURATION_ENTITY = "duration_entity"
CONF_ACCEPT_COST = "accept_cost"
CONF_ACCEPT_COST_ENTITY = "accept_cost_entity"
CONF_ACCEPT_RATE = "accept_rate"
CONF_ACCEPT_RATE_ENTITY = "accept_rate_entity"
CONF_SEARCH_LENGTH = "search_length"
CONF_SEARCH_LENGTH_ENTITY = "search_length_entity"
CONF_END_TIME = "end_time"
CONF_END_TIME_ENTITY = "end_time_entity"

class NordpoolPlanner:
    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        self._hass = hass
        self._config = config_entry

        self._type = config_entry.data[CONF_TYPE]

        # if self._nordpool_entity is not None:
        #     self.async_on_remove(
        #         async_track_state_change_event(
        #             self._hass,
        #             [self._nordpool_entity],
        #             self._async_input_changed,
        #         )
        #     )

        # Internal state
        self._np = None

        self._duration_number_entity = None
        if self._config.options[CONF_DURATION_ENTITY]:
            self._duration_number_entity = NordpoolPlannerNumber(
                self, callback=None, type="duration"
            )
            # n = self._duration_number_entity.name
        self._accept_cost_number_entity = None
        self._accept_rate_number_entity = None
        self._search_length_number_entity = None
        self._end_time_number_entity = None

        async_track_state_change_event(
            self._hass,
            [self._nordpool_entity],
            self._async_input_changed,
        )

        # Output states
        self.state = NordpoolPlannerState()

    def get_binary_sensor_entities(self):
        # return [NordpoolPlannerBinaeySensor(self)]
        pass

    def get_number_entities(self) -> list[NordpoolPlannerNumber]:
        number_entities = []
        for k, v in self._config.options.items():
            if v is None:
                number_entities.append(k)
        number_entities = []
        if self._duration_number_entity:
            number_entities.append(self._duration_number_entity)
        # return number_entities  # ToDo: Create specific entities
        return [self._duration_number_entity]

    # def duration_changed(self, value):
    #     self._duration_value = value

    async def _async_input_changed(self, event):
        new_state = event.data.get("new_state")
        _LOGGER.info("Sensor change: %s", new_state)
        self.update()

    @property
    def name(self) -> str:
        return self._config.data["name"]

    @property
    def _nordpool_entity(self) -> str:
        return self._config.data[CONF_NP_ENTITY]

    @property
    def _duration(self) -> int:
        if self._duration_number_entity:
            try:
                entity = self._hass.states.get(self._duration_number_entity.entity_id)
                state = entity.state
                value = int(state)
                # if value is not None:
                #     return value
                return value
            except TypeError:
                _LOGGER.warning(
                    'Could not convert value "%s" of entity %s to int',
                    state,
                    self._duration_number_entity.name,
                )
        elif (
            CONF_DURATION in self._config.options.keys()
            and self._config.options[CONF_DURATION]
        ):
            return self._config.options[CONF_DURATION]
        else:
            _LOGGER.error("No duration value or entity defined")
        return None

    @property
    def _accept_cost(self) -> float:
        if self._accept_cost_number_entity:
            try:
                state = self._hass.states.get(self._accept_cost_number_entity.entity_id).state
                value = float(state)
                # if value is not None:
                #     return value
                return value
            except TypeError:
                _LOGGER.warning(
                    'Could not convert value "%s" of entity %s to int',
                    state,
                    self._accept_cost_number_entity.name,
                )
        elif (
            CONF_ACCEPT_COST in self._config.options.keys()
            and self._config.options[CONF_ACCEPT_COST]
        ):
            return self._config.options[CONF_ACCEPT_COST]
        else:
            _LOGGER.debug("No accept cost value or entity defined")
        return None

    @property
    def _accept_rate(self) -> float:
        if self._accept_rate_number_entity:
            try:
                state = self._hass.states.get(self._accept_rate_number_entity.entity_id).state
                value = float(state)
                # if value is not None:
                #     return value
                return value
            except TypeError:
                _LOGGER.warning(
                    'Could not convert value "%s" of entity %s to int',
                    state,
                    self._accept_rate_number_entity.name,
                )
        elif (
            CONF_ACCEPT_RATE in self._config.options.keys()
            and self._config.options[CONF_ACCEPT_RATE]
        ):
            return self._config.options[CONF_ACCEPT_RATE]
        else:
            _LOGGER.debug("No accept rate value or entity defined")
        return None


    @property
    def _search_length(self) -> int:
        if (
            CONF_SEARCH_LENGTH in self._config.options.keys()
            and self._config.options[CONF_SEARCH_LENGTH]
        ):
            return self._config.options[CONF_SEARCH_LENGTH]
        return 12

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

    def update(self):
        # if self._type == "moving":
        self._update(dt.now().hour, self._search_length)

    def _update(self, start_hour, search_length: int):
        # Update nordpool prices
        np = self._hass.states.get(self._nordpool_entity)
        if np is None:
            _LOGGER.warning(
                "Got empty data from Norpool entity %s ", self._nordpool_entity
            )
            # return
        elif "today" not in np.attributes.keys():
            _LOGGER.warning(
                "No values for today in Norpool entity %s ", self._nordpool_entity
            )
            # return
        else:
            self._np = np

        if self._np is None:
            # ToDo: Set UNAVAILABLE?
            return

        # Evaluate data
        now = dt.now()
        min_average = self._np_current
        min_start_hour = now.hour
        # Only search if current is above acceptable rates and in range
        if (
            now.hour >= start_hour
            and not (self._accept_cost is not None and min_average <= self._accept_cost)
            and not (self._accept_rate is not None and (min_average / self._np_average) <= self._accept_rate)
        ):
            duration = self._duration
            if duration is None:
                return

            for i in range(
                start_hour,
                min(now.hour + search_length, len(self._np_prices) - duration),
            ):
                price_range = self._np_prices[i : i + duration]
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
                    (self._accept_cost is not None and min_average <= self._accept_cost) or
                    (self._accept_rate is not None and (min_average / self._np_average) <= self._accept_rate)
                ):
                    min_average = average
                    min_start_hour = i
                    _LOGGER.debug("Found range under accept level at %s", i)
                    break

        # Write result to entity
        if now.hour >= min_start_hour:
            # self._attr_is_on = True
            self.state.is_on = True
        else:
            # self._attr_is_on = False
            self.state.is_on = False

        start = dt.parse_datetime(
            "%s-%s-%s %s:%s" % (now.year, now.month, now.day, 0, 0)
        )
        # Check if next day
        if min_start_hour >= 24:
            start += dt.parse_duration("1 day")
            min_start_hour -= 24
        self.state.starts_at = "%04d-%02d-%02d %02d:%02d" % (
            start.year,
            start.month,
            start.day,
            min_start_hour,
            0,
        )
        self.state.cost_at = min_average
        self.state.now_cost_rate = self._np_current / min_average


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


class NordpoolPlannerState:
    def __init__(self) -> None:
        self.is_on = STATE_UNKNOWN
        self.starts_at = STATE_UNKNOWN
        self.cost_at = STATE_UNKNOWN
        self.now_cost_rate = STATE_UNKNOWN


class NordpoolPlannerEntity(Entity):
    def __init__(
        self,
        planner,
    ) -> None:
        # Input configs
        self._planner = planner

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    @property
    def unique_id(self):
        name = "nordpool_planner_%s" % (self._planner.name,)
        name = name.lower().replace(".", "")
        return name


class NordpoolPlannerBinarySensor(NordpoolPlannerEntity, BinarySensorEntity):
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        planner,
    ) -> None:
        super().__init__(planner=planner)
        # Input configs
        # self._planner = planner

        # # Output states
        # self._attr_is_on = STATE_UNKNOWN
        # self._starts_at = STATE_UNKNOWN
        # self._cost_at = STATE_UNKNOWN
        # self._now_cost_rate = STATE_UNKNOWN

    @property
    def name(self):
        return self._planner.name  + " binary"

    # @property
    # def _attr_is_on(self):
    #     return self._planner.state.is_on

    @property
    def extra_state_attributes(self):
        """Provide attributes for the entity"""
        return {
            "starts_at": self._planner.state.starts_at,
            "cost_at": self._planner.state.cost_at,
            "now_cost_rate": self._planner.state.now_cost_rate,
        }

    def update(self):
        """Called from Home Assistant to update entity value"""
        self._planner.update()
        # self._update_np_prices()
        # if self._np is not None:
        #     search_length = min(
        #         self._get_input_entity_or_default(
        #             self._var_search_length_entity, self._search_length
        #         ),
        #         self._search_length,
        #     )
        #     self._update(dt.now().hour, search_length)


class NordpoolPlannerNumber(NordpoolPlannerEntity, NumberEntity):
    # _attr_icon = "mdi:flash"

    def __init__(
        self,
        planner,
        callback,
        type,
    ) -> None:
        super().__init__(planner)
        # Input configs
        self._callback = callback
        self._type = type
        self._value = 2
        # self._planner = planner
        # self.entity_description.min_value = 1
        # self.entity_description.max_value = 6
        # self.entity_description.step = 1

    @property
    def name(self):
        return self._planner.name  + " number " + self._type

    @property
    def native_value(self):
        return self._value

    # @property
    # def unit(self) -> str:
    #     """Unit"""
    #     return self._price_type

    # @property
    # def unit_of_measurement(self) -> str:  # FIXME
    #     """Return the unit of measurement this sensor expresses itself in."""
    #     _currency = self._currency
    #     if self._use_cents is True:
    #         # Convert unit of measurement to cents based on chosen currency
    #         _currency = _CURRENTY_TO_CENTS[_currency]
    #     return "%s/%s" % (_currency, self._price_type)

    def set_native_value(self, value: float) -> None:
        """Update the current value."""
        # self._callback(value)
        self._value = value

    # async def async_set_native_value(self, value: float) -> None:
    #     """Update the current value."""
    #     pass
