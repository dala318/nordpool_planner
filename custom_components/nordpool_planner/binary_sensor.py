from __future__ import annotations
from http.client import ACCEPTED

import logging
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
DURATION = "duration"
ACCEPT_RATE = "accept_rate"

# https://developers.home-assistant.io/docs/development_validation/
# https://github.com/home-assistant/core/blob/dev/homeassistant/helpers/config_validation.py
PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend({
    vol.Required(NORDPOOL_ENTITY): cv.entity_id,
    vol.Optional(SEARCH_LENGTH, default=10): vol.All(vol.Coerce(int), vol.Range(min=2, max=24)),
    vol.Optional(DURATION, default=2): vol.All(vol.Coerce(int), vol.Range(min=1, max=5)),
    vol.Optional(ACCEPT_RATE, default=0.0): vol.All(vol.Coerce(float), vol.Range(min=0.0, max=10000.0)),
})


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    nordpool_entity_id = config[NORDPOOL_ENTITY]
    search_length = config[SEARCH_LENGTH]
    duration = config[DURATION]
    accept_rate = config[ACCEPT_RATE]

    add_entities(
        [
            NordpoolPlannerSensor(
                nordpool_entity_id, search_length, duration, accept_rate
            )
        ]
    )


class NordpoolPlannerSensor(BinarySensorEntity):
    _attr_icon = "mdi:flash"

    def __init__(self, nordpool_entity_id, search_length, duration, accept_rate):
        self._nordpool_entity_id = nordpool_entity_id
        self._search_length = search_length
        self._duration = duration
        self._accept_rate = accept_rate
        self._attr_name = f"nordpool_planner_{duration}_{search_length}"
        # https://developers.home-assistant.io/docs/entity_registry_index/ : Entities should not include the domain in
        # their Unique ID as the system already accounts for these identifiers:
        self._attr_unique_id = f"{duration}_{search_length}"
        self._state = STATE_UNKNOWN
        self._starts_at = STATE_UNKNOWN
        self._cost_buffer = {}

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        # TODO could also add self._nordpool_entity_id etc. useful properties here.
        return {"starts_at": self._starts_at}  # self._starts_at

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

        now = dt.now()
        min_average = 1000000000
        min_start_hour = now.hour
        first_hour = max(now.hour - (self._duration - 1), 0)
        last_hour = min(len(prices) - self._duration, now.hour + self._search_length)
        for i in range(first_hour, last_hour):
            prince_range = prices[i : i + self._duration]
            # Nordpool sometimes returns null prices, https://github.com/custom-components/nordpool/issues/125
            # If 50% or more non-Null in range accept and use
            if len([[x for x in prince_range if x is not None]]) * 2 < len(prince_range):
                _LOGGER.debug("Skipping range at %s as to many empty", i)
                continue
            prince_range = [x for x in prince_range if x is not None]
            average = sum(prince_range) / self._duration
            if average < min_average:
                min_average = average
                min_start_hour = i
                _LOGGER.debug("New min value at %s", i)
            if average < self._accept_rate:
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
