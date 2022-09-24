from __future__ import annotations
from http.client import ACCEPTED

import logging
from sre_parse import State
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
SEARCH_LENGTH = "search_length"
VAR_SEARCH_LENGTH = "var_search_length"
DURATION = "duration"
ACCEPT_COST = "accept_cost"
ACCEPT_RATE = "accept_rate"


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
        vol.Optional(SEARCH_LENGTH, default=10): vol.All(
            vol.Coerce(int), vol.Range(min=2, max=24)
        ),
        vol.Optional(VAR_SEARCH_LENGTH, default=""): optional_entity_id,
        vol.Optional(DURATION, default=2): vol.All(
            vol.Coerce(int), vol.Range(min=1, max=5)
        ),
        vol.Optional(ACCEPT_COST, default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=10000.0)
        ),
        vol.Optional(ACCEPT_RATE, default=0.0): vol.All(
            vol.Coerce(float), vol.Range(min=0.0, max=10000.0)
        ),
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    nordpool_entity_id = config[NORDPOOL_ENTITY]
    search_length = config[SEARCH_LENGTH]
    var_search_length = config[VAR_SEARCH_LENGTH]
    duration = config[DURATION]
    accept_cost = config[ACCEPT_COST]
    accept_rate = config[ACCEPT_RATE]

    add_entities(
        [
            NordpoolPlannerSensor(
                nordpool_entity_id,
                search_length,
                var_search_length,
                duration,
                accept_cost,
                accept_rate,
            )
        ]
    )


class NordpoolPlannerSensor(BinarySensorEntity):
    _attr_icon = "mdi:flash"

    def __init__(
        self,
        nordpool_entity_id,
        search_length,
        var_search_length,
        duration,
        accept_cost,
        accept_rate,
    ):
        self._nordpool_entity_id = nordpool_entity_id
        self._search_length = search_length
        self._var_search_length = var_search_length
        self._duration = duration
        self._accept_cost = accept_cost
        self._accept_rate = accept_rate
        self._attr_name = (
            f"nordpool_planner_{duration}_{search_length}_{accept_cost}_{accept_rate}"
        )
        # https://developers.home-assistant.io/docs/entity_registry_index/ : Entities should not include the domain in
        # their Unique ID as the system already accounts for these identifiers:
        self._attr_unique_id = f"{duration}_{search_length}_{accept_cost}_{accept_rate}"
        self._state = STATE_UNKNOWN
        self._starts_at = STATE_UNKNOWN
        self._cost_at = STATE_UNKNOWN
        self._now_cost_rate = STATE_UNKNOWN

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        # TODO could also add self._nordpool_entity_id etc. useful properties here.
        return {
            "starts_at": self._starts_at,
            "cost_at": self._cost_at,
            "now_cost_rate": self._now_cost_rate,
        }

    def _get_search_length(self) -> int:
        search_length = self._search_length
        if self._var_search_length:
            input_search_length = self.hass.states.get(self._var_search_length)
            if not input_search_length or not input_search_length.state[0].isdigit():
                return search_length
            try:
                input_search_length = int(input_search_length.state.split(".")[0])
                if input_search_length is not None:
                    search_length = min(search_length, input_search_length)
            except TypeError:
                _LOGGER.debug(
                    'Could not convert value "%s" of entity %s to int',
                    input_search_length.state,
                    self._var_search_length,
                )
        return search_length

    def update(self):
        np = self.hass.states.get(self._nordpool_entity_id)
        if np is None:
            _LOGGER.warning(
                "Got empty data from Norpool entity %s ", self._nordpool_entity_id
            )
            return
        if "today" not in np.attributes.keys():
            _LOGGER.warning(
                "No values for today in Norpool entity %s ", self._nordpool_entity_id
            )
            return
        prices = np.attributes["today"]
        if np.attributes["tomorrow_valid"]:
            prices += np.attributes["tomorrow"]
        np_average = np.attributes["average"]

        now = dt.now()
        min_average = np.attributes["current_price"]
        min_start_hour = now.hour
        # Only search if current is above acceptable rates
        if (
            min_average > self._accept_cost
            and (min_average / np_average) > self._accept_rate
        ):
            search_length = self._get_search_length()
            for i in range(
                now.hour,
                min(now.hour + search_length, len(prices) - self._duration),
            ):
                prince_range = prices[i : i + self._duration]
                # Nordpool sometimes returns null prices, https://github.com/custom-components/nordpool/issues/125
                # If 50% or more non-Null in range accept and use
                if len([[x for x in prince_range if x is not None]]) * 2 > len(
                    prince_range
                ):
                    _LOGGER.debug("Skipping range at %s as to many empty", i)
                    continue
                prince_range = [x for x in prince_range if x is not None]
                average = sum(prince_range) / self._duration
                if average < min_average:
                    min_average = average
                    min_start_hour = i
                    _LOGGER.debug("New min value at %s", i)
                if (
                    average < self._accept_cost
                    or (average / np_average) < self._accept_rate
                ):
                    min_average = average
                    min_start_hour = i
                    _LOGGER.debug("Found range under accept level at %s", i)
                    break

        if now.hour >= min_start_hour:
            self._state = True
        else:
            self._state = False

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
        self._now_cost_rate = np.attributes["current_price"] / min_average
