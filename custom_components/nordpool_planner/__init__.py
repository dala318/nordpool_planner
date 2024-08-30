from __future__ import annotations
import logging
from config.custom_components import nordpool
from homeassistant.components.binary_sensor import BinarySensorEntity

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import STATE_UNKNOWN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_track_state_change_event,
)
from homeassistant.util import dt

from .const import (
    DOMAIN,
    CONF_ACCEPT_COST,
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_DURATION,
    CONF_DURATION_ENTITY,
    CONF_END_TIME,
    CONF_END_TIME_ENTITY,
    CONF_NAME,
    CONF_NP_ENTITY,
    CONF_SEARCH_LENGTH,
    CONF_SEARCH_LENGTH_ENTITY,
    CONF_TYPE,
    CONF_TYPE_MOVING,
    CONF_TYPE_STATIC,
    CONF_TYPE_LIST,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.NUMBER]


class NordpoolPlanner:
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

        # Output states
        self.state = NordpoolPlannerState()

    @property
    def name(self) -> str:
        return self._config.data["name"]

    @property
    def _duration(self) -> int:
        if self._duration_number_entity:
            try:
                entity = self._hass.states.get(self._duration_number_entity)
                state = entity.state
                value = int(float(state))
                # if value is not None:
                #     return value
                return value
            except (TypeError, ValueError):
                _LOGGER.warning(
                    'Could not convert value "%s" of entity %s to int',
                    state,
                    self._duration_number_entity,
                )
            except Exception as e:
                _LOGGER.error(
                    'Unknown error wen reading "%s": %s',
                    self._accept_cost_number_entity,
                    e,
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
                state = self._hass.states.get(self._accept_cost_number_entity).state
                value = float(state)
                # if value is not None:
                #     return value
                return value
            except (TypeError, ValueError):
                _LOGGER.warning(
                    'Could not convert value "%s" of entity %s to int',
                    state,
                    self._accept_cost_number_entity,
                )
            except Exception as e:
                _LOGGER.error(
                    'Unknown error wen reading "%s": %s',
                    self._accept_cost_number_entity,
                    e,
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
                state = self._hass.states.get(self._accept_rate_number_entity).state
                value = float(state)
                # if value is not None:
                #     return value
                return value
            except (TypeError, ValueError):
                _LOGGER.warning(
                    'Could not convert value "%s" of entity %s to int',
                    state,
                    self._accept_rate_number_entity,
                )
            except Exception as e:
                _LOGGER.error(
                    'Unknown error wen reading "%s": %s',
                    self._accept_cost_number_entity,
                    e,
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
    def _end_time(self) -> int:
        if (
            CONF_END_TIME in self._config.options.keys()
            and self._config.options[CONF_END_TIME]
        ):
            return self._config.options[CONF_END_TIME]
        return 6

    def register_number_entity(self, entity_id, conf_key) -> None:
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
                conf_key
            )
        # TODO: Dont seem to work as expected!
        async_track_state_change_event(
            self._hass,
            [entity_id],
            self._async_input_changed,
        )

    # def register_duration_number_entity(self, entity_id) -> None:
    #     self._duration_number_entity = entity_id
    #     async_track_state_change_event(
    #         self._hass,
    #         [entity_id],
    #         self._async_input_changed,
    #     )
    #     # TODO: Dont seem to work as expected!

    # def register_accept_cost_number_entity(self, entity_id) -> None:
    #     self._accept_cost_number_entity = entity_id
    #     async_track_state_change_event(
    #         self._hass,
    #         [entity_id],
    #         self._async_input_changed,
    #     )
    #     # TODO: Dont seem to work as expected!

    # def register_accept_rate_number_entity(self, entity_id) -> None:
    #     self._accept_rate_number_entity = entity_id
    #     async_track_state_change_event(
    #         self._hass,
    #         [entity_id],
    #         self._async_input_changed,
    #     )
    #     # TODO: Dont seem to work as expected!

    # def register_search_length_number_entity(self, entity_id) -> None:
    #     self._search_length_number_entity = entity_id
    #     async_track_state_change_event(
    #         self._hass,
    #         [entity_id],
    #         self._async_input_changed,
    #     )
    #     # TODO: Dont seem to work as expected!

    # def register_end_time_number_entity(self, entity_id) -> None:
    #     self._end_time_number_entity = entity_id
    #     async_track_state_change_event(
    #         self._hass,
    #         [entity_id],
    #         self._async_input_changed,
    #     )
    #     # TODO: Dont seem to work as expected!

    def get_device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._config.data[CONF_TYPE])},
            name=self.name,
            manufacturer="Nordpool",
            entry_type=DeviceEntryType.SERVICE,
            via_device=(nordpool.DOMAIN, self._np_entity.unique_id)
        )

    # def get_binary_sensor_entities(self):
    #     # return [NordpoolPlannerBinaeySensor(self)]
    #     pass

    # def get_number_entities(self) -> list[NordpoolPlannerNumber]:
    #     number_entities = []
    #     if self._duration_number_entity:
    #         number_entities.append(self._duration_number_entity)
    #     if self._accept_cost_number_entity:
    #         number_entities.append(self._accept_cost_number_entity)
    #     if self._accept_rate_number_entity:
    #         number_entities.append(self._accept_rate_number_entity)
    #     if self._search_length_number_entity:
    #         number_entities.append(self._search_length_number_entity)
    #     if self._end_time_number_entity:
    #         number_entities.append(self._end_time_number_entity)
    #     return number_entities
    #     # return [self._duration_number_entity]

    def input_changed(self, value):
        _LOGGER.debug("Sensor change event from callback: %s", value)
        self.update()

    async def _async_input_changed(self, event):
        new_state = event.data.get("new_state")
        _LOGGER.debug("Sensor change event from HASS: %s", new_state)
        self.update()

    def update(self):
        # if self._config.data[CONF_TYPE] == CONF_TYPE_MOVING:
        self._update(dt.now().hour, self._search_length)

    def _update(self, start_hour, search_length: int):
        # TODO: Remove, only for debugging
        d = self._duration
        c = self._accept_cost
        r = self._accept_rate
        l = self._search_length
        e = self._end_time

        self._np_entity.update(self._hass)
        if not self._np_entity.valid:
            _LOGGER.warning(
                "Aborting update since no valid Nordpool data"
            )
            return

        # Evaluate data
        now = dt.now()
        min_average = self._np_entity.current_price
        min_start_hour = now.hour
        # Only search if current is above acceptable rates and in range
        if (
            now.hour >= start_hour
            and not (self._accept_cost is not None and min_average <= self._accept_cost)
            and not (self._accept_rate is not None and (min_average / self._np_entity.average) <= self._accept_rate)
        ):
            duration = self._duration
            if duration is None:
                _LOGGER.warning(
                    "Aborting update since no valid Duration"
                )
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
                    (self._accept_cost is not None and min_average <= self._accept_cost) or
                    (self._accept_rate is not None and (min_average / self._np_entity.average) <= self._accept_rate)
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
        self.state.now_cost_rate = self._np_entity.current_price / min_average


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


class NordpoolEntity:
    def __init__(self, unique_id: str) -> None:
        self._unique_id = unique_id
        self._np = None

    @property
    def unique_id(self) -> str:
        return self._unique_id

    @property
    def valid(self) -> bool:
        # TODO: Add more checks, make function of those in update()
        return self._np is not None

    @property
    def prices(self):
        np_prices = self._np.attributes["today"]
        if self._np.attributes["tomorrow_valid"]:
            np_prices += self._np.attributes["tomorrow"]
        return np_prices

    @property
    def average(self):
        return self._np.attributes["average"]

    @property
    def current_price(self):
        return self._np.attributes["current_price"]

    def update(self, hass: HomeAssistant) -> None:
        np = hass.states.get(self._unique_id)
        if np is None:
            _LOGGER.warning(
                "Got empty data from Norpool entity %s ", self._unique_id
            )
        elif "today" not in np.attributes.keys():
            _LOGGER.warning(
                "No values for today in Norpool entity %s ", self._unique_id
            )
        else:
            _LOGGER.debug(
                "Nordpool sensor %s was updated sucsessfully",
                self._unique_id
            )
            if self._np is None:
                pass
                # TODO: Set unit_of_measuremetn of applicable number entities
            self._np = np

        if self._np is None:
            # TODO: Set UNAVAILABLE?
            return


class NordpoolPlannerState:
    def __init__(self) -> None:
        self.is_on = STATE_UNKNOWN
        self.starts_at = STATE_UNKNOWN
        self.cost_at = STATE_UNKNOWN
        self.now_cost_rate = STATE_UNKNOWN


class NordpoolPlannerEntity(Entity):
    def __init__(
        self,
        planner: NordpoolPlanner,
    ) -> None:
        # Input configs
        self._planner = planner
        self._attr_device_info = planner.get_device_info()

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

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
    def unique_id(self):
        name = "nordpool_planner_%s_%s" % (self._planner.name, "low")
        name = name.lower().replace(".", "")
        return name

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


