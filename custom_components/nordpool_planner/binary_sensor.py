from __future__ import annotations

import logging
from typing import Any
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.binary_sensor import PLATFORM_SCHEMA, BinarySensorEntity
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt

_LOGGER = logging.getLogger(__name__)

NORDPOOL_ENTITY = "nordpool_entity"
ENTITY_ID = "entity_id"
PLANNER_TYPE = "planner_type"
MOVING = "moving"
STATIC = "static"
SEARCH_LENGTH = "search_length"
VAR_SEARCH_LENGTH_ENTITY = "var_search_length_entity"
DURATION = "duration"
VAR_DURATION_ENTITY = "var_duration_entity"
END_HOUR = "end_hour"
VAR_END_HOUR_ENTITY = "var_end_hour_entity"
SPLIT_HOURS = "split_hours"
ACCEPT_COST = "accept_cost"
ACCEPT_RATE = "accept_rate"
TYPE_GROUP = "type"
TYPE_DUPLICATE_MSG = f'One entity can only be one of "{MOVING}" and "{STATIC}", please remove either or split in two entities.'
TYPE_MISSING_MSG = f'One of "{MOVING}" and "{STATIC}" must be spcified'


def optional_entity_id(value: Any) -> str:
    """Validate Entity ID if not Empty"""
    if not value:
        return ""
    return cv.entity_id(value)


# https://developers.home-assistant.io/docs/development_validation/
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/config_validation.py
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(NORDPOOL_ENTITY): cv.entity_id,
        vol.Required(ENTITY_ID): vol.All(vol.Coerce(str)),
        vol.Optional(DURATION, default=2): vol.All(
            vol.Coerce(int),
            vol.Range(min=1, max=5),
        ),
        vol.Optional(VAR_DURATION_ENTITY, default=""): optional_entity_id,
        vol.Optional(ACCEPT_COST, default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=10000.0)
        ),
        vol.Optional(ACCEPT_RATE, default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=10000.0)
        ),
        # Moving planner exclusives
        vol.Exclusive(MOVING, TYPE_GROUP, msg=TYPE_DUPLICATE_MSG): {
            vol.Required(SEARCH_LENGTH): vol.All(
                vol.Coerce(int), vol.Range(min=2, max=24)
            ),
            vol.Optional(VAR_SEARCH_LENGTH_ENTITY, default=""): optional_entity_id,
        },
        # Static planner exclusive
        vol.Exclusive(STATIC, TYPE_GROUP, msg=TYPE_DUPLICATE_MSG): {
            vol.Required(END_HOUR): vol.All(vol.Coerce(int), vol.Range(min=0, max=23)),
            vol.Optional(VAR_END_HOUR_ENTITY, default=""): optional_entity_id,
            vol.Optional(SPLIT_HOURS, default=False): vol.Coerce(bool),
        },
        # Check either is configured
        # vol.Required(
        #     vol.Any(MOVING, STATIC),
        #     msg=TYPE_MISSING_MSG,
        # ): object,
    },
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    nordpool_entity = config[NORDPOOL_ENTITY]
    entity_id = config[ENTITY_ID]
    duration = config[DURATION]
    var_duration_entity = config[VAR_DURATION_ENTITY]
    accept_cost = config[ACCEPT_COST]
    accept_rate = config[ACCEPT_RATE]
    if MOVING in config.keys():
        search_length = config[MOVING][SEARCH_LENGTH]
        var_search_length_entity = config[MOVING][VAR_SEARCH_LENGTH_ENTITY]
        add_entities(
            [
                NordpoolMovingPlannerSensor(
                    search_length=search_length,
                    var_search_length_entity=var_search_length_entity,
                    nordpool_entity=nordpool_entity,
                    entity_id=entity_id,
                    duration=duration,
                    var_duration_entity=var_duration_entity,
                    accept_cost=accept_cost,
                    accept_rate=accept_rate,
                )
            ]
        )
    if STATIC in config.keys():
        end_hour = config[STATIC][END_HOUR]
        var_end_hour_entity = config[STATIC][VAR_END_HOUR_ENTITY]
        split_hours = config[STATIC][SPLIT_HOURS]
        add_entities(
            [
                NordpoolStaticPlannerSensor(
                    end_hour=end_hour,
                    var_end_hour_entity=var_end_hour_entity,
                    nordpool_entity=nordpool_entity,
                    entity_id=entity_id,
                    duration=duration,
                    var_duration_entity=var_duration_entity,
                    split_hours=split_hours,
                    accept_cost=accept_cost,
                    accept_rate=accept_rate,
                )
            ]
        )


class NordpoolPlannerSensor(BinarySensorEntity):
    """Base class for nordpool planner"""

    _attr_icon = "mdi:flash"

    def __init__(
        self,
        nordpool_entity,
        entity_id,
        duration,
        var_duration_entity,
        accept_cost,
        accept_rate,
    ):
        # Input configs
        self._nordpool_entity = nordpool_entity
        self._duration = duration
        self._var_duration_entity = var_duration_entity
        self._accept_cost = accept_cost
        self._accept_rate = accept_rate

        # Entity identification
        entity_id = entity_id.replace(" ", "_")
        self._attr_name = f"nordpool_planner_{entity_id}"
        self._attr_unique_id = entity_id

        # Internal state
        self._np = None

        # Output states
        self._attr_is_on = STATE_UNKNOWN
        self._starts_at = STATE_UNKNOWN
        self._cost_at = STATE_UNKNOWN
        self._now_cost_rate = STATE_UNKNOWN

    @property
    def extra_state_attributes(self):
        """Provide attributes for the entity"""
        return {
            "starts_at": self._starts_at,
            "cost_at": self._cost_at,
            "now_cost_rate": self._now_cost_rate,
        }

    def _update_np_prices(self):
        np = self.hass.states.get(self._nordpool_entity)
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
            input_value = self.hass.states.get(entity_id)
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
                # If 50% or more non-Null in range accept and use
                if len([x for x in prince_range if x is not None]) * 2 <= len(
                    prince_range
                ):
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


class NordpoolMovingPlannerSensor(NordpoolPlannerSensor):
    """Nordpool planner with moving search length"""

    def __init__(self, search_length, var_search_length_entity, **kwds):
        super().__init__(**kwds)
        self._search_length = search_length
        self._var_search_length_entity = var_search_length_entity

    def update(self):
        """Called from Home Assistant to update entity value"""
        self._update_np_prices()
        if self._np is not None:
            search_length = min(
                self._get_input_entity_or_default(
                    self._var_search_length_entity, self._search_length
                ),
                self._search_length,
            )
            self._update(dt.now().hour, search_length)


class NordpoolStaticPlannerSensor(NordpoolPlannerSensor):
    """Nordpool planner with fixed search length end time"""

    def __init__(self, end_hour, var_end_hour_entity, split_hours, **kwds):
        super().__init__(**kwds)
        self._end_hour = end_hour
        self._var_end_hour_entity = var_end_hour_entity
        self._split_hours = split_hours

        self._now_hour = dt.now().hour
        self._remaining = self._get_input_entity_or_default(
            self._var_duration_entity, self._duration
        )

    def update(self):
        """Called from Home Assistant to update entity value"""
        self._update_np_prices()
        now = dt.now()
        end_hour = self._get_input_entity_or_default(
            self._var_end_hour_entity, self._end_hour
        )

        # Start by checking if hour has changed
        if self._now_hour != now.hour:
            # Reset needed hours as end has been reached
            if now.hour == end_hour:
                self._remaining = self._get_input_entity_or_default(
                    self._var_duration_entity, self._duration
                )
            # Else-if since don't want to risk to remove one directly
            elif self._attr_is_on:
                self._remaining -= 1
        self._now_hour = now.hour

        if self._remaining == 0:
            self._attr_is_on = False
            self._starts_at = None
            self._cost_at = None
            self._now_cost_rate = None
        else:
            if self._np is not None:
                if end_hour < now.hour:
                    end_hour += 24
                self._update(now.hour, end_hour - now.hour)
