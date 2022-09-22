from __future__ import annotations
from http.client import ACCEPTED

import logging
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA, SensorEntity
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


class NordpoolPlannerSensor(SensorEntity):
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
        self._state = self._starts_in = STATE_UNKNOWN
        self._cost_buffer = {}

    @property
    def state(self):
        return self._state

    @property
    def extra_state_attributes(self):
        # TODO could also add self._nordpool_entity_id etc. useful properties here.
        return {"starts_in": self._starts_in}

    def update(self):
        np = self.hass.states.get(self._nordpool_entity_id)
        if np is None:
            _LOGGER.warning("Got empty data from Norpool entity %s ", self._nordpool_entity_id)
            return
        prices = np.attributes["today"]
        if np.attributes["tomorrow_valid"]:
            prices += np.attributes["tomorrow"]

        now_hour = dt.now().hour
        min_average = 1000000000
        min_start_hour = now_hour
        for i in range(
            max(now_hour - self._duration, 0), len(prices) - self._search_length
        ):
            prince_range = prices[i : i + self._duration]
            # Nordpool sometimes returns null prices, https://github.com/custom-components/nordpool/issues/125
            # If 50% or more non-Null in range accept and use
            if len([[x for x in prince_range if x is not None]]) * 2 < len(prince_range):
                _LOGGER.debug("Skipping range at %s as to many empty", i)
                continue
            prices = [x for x in prices if x is not None]
            average = sum(prince_range) / self._duration
            if average < min_average:
                min_average = average
                min_start_hour = i
                _LOGGER.debug("New min value at %s", i)
            if average < self._accept_rate:
                min_start_hour = i
                _LOGGER.debug("Found range under accept level at %s", i)
                break

        if now_hour > min_start_hour:
            self._state = True
            self._starts_in = 0
        else:
            self._state = False
            now = dt.now()
            begin = now
            begin.second = 0
            begin.minute = 0
            # Check if next day
            if begin.hour < now.hour:
                begin.day += 1
                min_start_hour -= 24
            begin.hour = min_start_hour
            self._starts_in = begin - now
