from __future__ import annotations
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import Config, HomeAssistant
from homeassistant.helpers.entity import Entity
from homeassistant.util import dt

DOMAIN = "nordpool_planner"
PLATFORMS = ["binary_sensor"]

_LOGGER = logging.getLogger(__name__)


async def async_setup(hass: HomeAssistant, config: Config) -> bool:
    hass.data.setdefault(DOMAIN, {})
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    entry_data = dict(entry.data)
    hass.data[DOMAIN][entry.entry_id] = entry_data
    hass.config_entries.async_setup_platforms(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)
    return unload_ok


class NordpoolPlannerEntity(Entity):
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

        # BinarySensor state
        self._attr_is_on = STATE_UNKNOWN

        # Sensor state
        self._attr_native_value = STATE_UNKNOWN

        # Attributes
        self._starts_at = STATE_UNKNOWN
        self._cost_at = STATE_UNKNOWN
        self._now_cost_rate = STATE_UNKNOWN

    # @property
    # def _attr_is_on(self) -> bool | None:

    # @property
    # def _attr_native_value(self) -> StateType | date | datetime | Decimal:

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
                if len([[x for x in prince_range if x is not None]]) * 2 > len(
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
