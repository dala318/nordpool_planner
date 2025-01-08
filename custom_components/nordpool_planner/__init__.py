"""Main package for planner."""

from __future__ import annotations

import datetime as dt
import logging

from homeassistant.config_entries import SOURCE_IMPORT, ConfigEntry
from homeassistant.const import (
    ATTR_UNIT_OF_MEASUREMENT,
    STATE_UNAVAILABLE,
    STATE_UNKNOWN,
    Platform,
)
from homeassistant.core import HomeAssistant, HomeAssistantError
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.event import (
    async_track_state_change_event,
    async_track_time_change,
)
from homeassistant.util import dt as dt_util

from .config_flow import NordpoolPlannerConfigFlow
from .const import (
    CONF_ACCEPT_COST_ENTITY,
    CONF_ACCEPT_RATE_ENTITY,
    CONF_DURATION_ENTITY,
    CONF_END_TIME_ENTITY,
    CONF_HEALTH_ENTITY,
    CONF_PRICES_ENTITY,
    CONF_SEARCH_LENGTH_ENTITY,
    CONF_START_TIME_ENTITY,
    CONF_TYPE,
    CONF_TYPE_MOVING,
    CONF_TYPE_STATIC,
    CONF_USED_HOURS_LOW_ENTITY,
    DOMAIN,
    NAME_FILE_READER,
    PATH_FILE_READER,
    PlannerStates,
)
from .helpers import get_np_from_file

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [Platform.BINARY_SENSOR, Platform.BUTTON, Platform.NUMBER, Platform.SENSOR]


async def async_setup_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Set up this integration using UI."""
    config_entry.async_on_unload(config_entry.add_update_listener(async_reload_entry))

    if DOMAIN not in hass.data:
        hass.data[DOMAIN] = {}

    if config_entry.entry_id not in hass.data[DOMAIN]:
        planner = NordpoolPlanner(hass, config_entry)
        await planner.async_setup()
        hass.data[DOMAIN][config_entry.entry_id] = planner

    if config_entry is not None:
        if config_entry.source == SOURCE_IMPORT:
            hass.async_create_task(
                hass.config_entries.async_remove(config_entry.entry_id)
            )
            return False

    await hass.config_entries.async_forward_entry_setups(config_entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unloading a config_flow entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        planner = hass.data[DOMAIN].pop(entry.entry_id)
        planner.cleanup()
    return unload_ok


async def async_reload_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> None:
    """Reload the config entry."""
    await async_unload_entry(hass, config_entry)
    await async_setup_entry(hass, config_entry)


async def async_migrate_entry(hass: HomeAssistant, config_entry: ConfigEntry) -> bool:
    """Migrate old entry."""
    _LOGGER.debug(
        "Attempting migrating configuration from version %s.%s",
        config_entry.version,
        config_entry.minor_version,
    )

    class MigrateError(HomeAssistantError):
        """Error to indicate there is was an error in version migration."""

    installed_version = NordpoolPlannerConfigFlow.VERSION
    installed_minor_version = NordpoolPlannerConfigFlow.MINOR_VERSION

    new_data = {**config_entry.data}
    new_options = {**config_entry.options}

    if config_entry.version > installed_version:
        _LOGGER.warning(
            "Downgrading major version from %s to %s is not allowed",
            config_entry.version,
            installed_version,
        )
        return False

    if (
        config_entry.version == installed_version
        and config_entry.minor_version > installed_minor_version
    ):
        _LOGGER.warning(
            "Downgrading minor version from %s.%s to %s.%s is not allowed",
            config_entry.version,
            config_entry.minor_version,
            installed_version,
            installed_minor_version,
        )
        return False

    def options_1x_to_20(options: dict, data: dict, hass: HomeAssistant):
        try:
            np_entity = hass.states.get(data[CONF_PRICES_ENTITY])
            uom = np_entity.attributes.get(ATTR_UNIT_OF_MEASUREMENT)
            options.pop("currency")
            options[ATTR_UNIT_OF_MEASUREMENT] = uom
        except (IndexError, KeyError) as err:
            _LOGGER.warning("Could not extract currency from Prices entity")
            raise MigrateError from err
        return options

    def data_20_to_21(data: dict):
        if entity_id := data.pop("np_entity"):
            data[CONF_PRICES_ENTITY] = entity_id
            return data
        _LOGGER.warning('Could not find "np_entity" in config_entry')
        raise MigrateError('Could not find "np_entity" in config_entry')

    def data_21_to_22(data: dict):
        if data[CONF_TYPE] == CONF_TYPE_STATIC:
            data[CONF_USED_HOURS_LOW_ENTITY] = True
            data[CONF_START_TIME_ENTITY] = True
        if CONF_HEALTH_ENTITY not in data:
            data[CONF_HEALTH_ENTITY] = True
        return data

    if config_entry.version == 1:
        try:
            # Version 1.x to 2.0
            new_options = options_1x_to_20(new_options, new_data, hass)
            # Version 2.0 to 2.1
            new_data = data_20_to_21(new_data)
            # Version 2.1 to 2.2
            new_data = data_21_to_22(new_data)
        except MigrateError:
            _LOGGER.warning("Error while upgrading from version 1.x to 2.1")
            return False

    if config_entry.version == 2 and config_entry.minor_version == 0:
        try:
            # Version 2.0 to 2.1
            new_data = data_20_to_21(new_data)
            # Version 2.1 to 2.2
            new_data = data_21_to_22(new_data)
        except MigrateError:
            _LOGGER.warning("Error while upgrading from version 2.0 to 2.1")
            return False

    if config_entry.version == 2 and config_entry.minor_version == 1:
        try:
            # Version 2.1 to 2.2
            new_data = data_21_to_22(new_data)
        except MigrateError:
            _LOGGER.warning("Error while upgrading from version 2.1 to 2.2")
            return False

    hass.config_entries.async_update_entry(
        config_entry,
        data=new_data,
        options=new_options,
        version=installed_version,
        minor_version=installed_minor_version,
    )
    _LOGGER.info(
        "Migration configuration from version %s.%s to %s.%s successful",
        config_entry.version,
        config_entry.minor_version,
        installed_version,
        installed_minor_version,
    )
    return True


class NordpoolPlanner:
    """Planner base class."""

    _hourly_update = None

    def __init__(self, hass: HomeAssistant, config_entry: ConfigEntry) -> None:
        """Initialize my coordinator."""
        self._hass = hass
        self._config = config_entry
        self._state_change_listeners = []

        # Input entities
        self._prices_entity = PricesEntity(self._config.data[CONF_PRICES_ENTITY])
        # TODO: Remove, likely not needed anymore as async_track_time_change in async_setup() will ensure update every hour
        # self._state_change_listeners.append(
        #     async_track_state_change_event(
        #         self._hass,
        #         [self._prices_entity.unique_id],
        #         self._async_input_changed,
        #     )
        # )

        # Configuration entities
        self._duration_number_entity = ""
        self._accept_cost_number_entity = ""
        self._accept_rate_number_entity = ""
        self._search_length_number_entity = ""
        self._start_time_number_entity = ""
        self._end_time_number_entity = ""
        # TODO: Make dictionary?

        # Output entities
        self._output_listeners: dict[str, NordpoolPlannerEntity] = {}

        # Local state variables
        self._last_update = None
        self.low_hours = None
        self._planner_status = NordpoolPlannerStatus()

        # Output states
        self.low_cost_state = NordpoolPlannerState()
        self.high_cost_state = NordpoolPlannerState()

    def as_dict(self):
        """For diagnostics serialization."""
        res = self.__dict__.copy()
        for k, i in res.copy().items():
            if "_number_entity" in k:
                res[k] = {"id": i, "value": self.get_number_entity_value(i)}
        return res

    async def async_setup(self):
        """Post initialization setup."""
        # Ensure an update is done on every hour
        self._hourly_update = async_track_time_change(
            self._hass, self.scheduled_update, minute=0, second=0
        )

    @property
    def name(self) -> str:
        """Name of planner."""
        return self._config.data["name"]

    @property
    def price_sensor_id(self) -> str:
        """Entity id of source sensor."""
        return self._prices_entity.unique_id

    @property
    def price_now(self) -> str:
        """Current price from source sensor."""
        return self._prices_entity.current_price_attr

    @property
    def planner_status(self) -> NordpoolPlannerStatus:
        """Current planner status."""
        return self._planner_status

    @property
    def _duration(self) -> int:
        """Get duration parameter."""
        return self.get_number_entity_value(self._duration_number_entity, integer=True)

    @property
    def _is_moving(self) -> bool:
        """Get if planner is of type Moving."""
        return self._config.data[CONF_TYPE] == CONF_TYPE_MOVING

    @property
    def _is_static(self) -> bool:
        """Get if planner is of type Static."""
        return self._config.data[CONF_TYPE] == CONF_TYPE_STATIC

    @property
    def _search_length(self) -> int:
        """Get search length parameter."""
        return self.get_number_entity_value(
            self._search_length_number_entity, integer=True
        )

    @property
    def _start_time(self) -> int:
        """Get start time parameter."""
        return self.get_number_entity_value(
            self._start_time_number_entity, integer=True
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

    def cleanup(self):
        """Cleanup by removing event listeners."""
        for lister in self._state_change_listeners:
            lister()

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
        elif conf_key == CONF_START_TIME_ENTITY:
            self._start_time_number_entity = entity_id
        elif conf_key == CONF_END_TIME_ENTITY:
            self._end_time_number_entity = entity_id
        else:
            _LOGGER.warning(
                'An entity "%s" was registered for callback but no match for key "%s"',
                entity_id,
                conf_key,
            )
        self._state_change_listeners.append(
            async_track_state_change_event(
                self._hass,
                [entity_id],
                self._async_input_changed,
            )
        )

    def register_output_listener_entity(
        self, entity: NordpoolPlannerEntity, conf_key=""
    ) -> None:
        """Register output entity."""
        if conf_key in self._output_listeners:
            _LOGGER.warning(
                'An output listener with key "%s" and unique id "%s" is overriding previous entity "%s"',
                conf_key,
                self._output_listeners.get(conf_key).entity_id,
                entity.entity_id,
            )
        self._output_listeners[conf_key] = entity

    def get_device_info(self) -> DeviceInfo:
        """Get device info to group entities."""
        return DeviceInfo(
            identifiers={(DOMAIN, self._config.entry_id)},
            name=self.name,
            manufacturer="Nordpool",
            entry_type=DeviceEntryType.SERVICE,
            model="Forecast",
        )

    def scheduled_update(self, _):
        """Scheduled updates callback."""
        _LOGGER.debug("Scheduled callback")
        self.update()

    def input_changed(self, value):
        """Input entity callback to initiate a planner update."""
        _LOGGER.debug("Sensor change event from callback: %s", value)
        self.update()

    async def _async_input_changed(self, event):
        """Input entity change callback from state change event."""
        new_state = event.data.get("new_state")
        _LOGGER.debug("Sensor change event from HASS: %s", new_state)
        self.update()

    def update(self):
        """Planner update call function."""
        _LOGGER.debug("Updating planner")

        # Update inputs
        if not self._prices_entity.update(self._hass) and not self._prices_entity.valid:
            self.set_unavailable()
            self._planner_status.status = PlannerStates.Error
            self._planner_status.running_text = "No valid Price data"
            return

        if not self._duration:
            _LOGGER.warning("Aborting update since no valid Duration")
            self._planner_status.status = PlannerStates.Error
            self._planner_status.running_text = "No valid Duration data"
            return

        if self._is_moving and not self._search_length:
            _LOGGER.warning("Aborting update since no valid Search length")
            self._planner_status.status = PlannerStates.Error
            self._planner_status.running_text = "No valid Search-Length data"
            return

        if self._is_static and not (self._start_time and self._end_time):
            _LOGGER.warning("Aborting update since no valid Start or end time")
            self._planner_status.status = PlannerStates.Error
            self._planner_status.running_text = "No valid Start-Time or End-Time"
            return

        # If come this far no running error texts relevant (for now...)
        self._planner_status.status = PlannerStates.Ok
        self._planner_status.running_text = "ok"
        self._planner_status.config_text = "ok"

        if self._is_moving and self._search_length < self._duration:
            self._planner_status.status = PlannerStates.Warning
            self._planner_status.config_text = "Duration is Lager than Search-Length"

        # if self._is_static and (self._end_time - self._start_time) < self._duration:
        #     self._planner_status.status = PlannerStates.Warning
        #     self._planner_status.config_text = "Duration is Lager than Search-Window"

        # initialize local variables
        now = dt_util.now()

        if self._is_static and self.low_hours is not None:
            if self.low_hours >= self._duration:
                _LOGGER.debug("No need to update, quota of hours fulfilled")
                self.set_done_for_now()
                self._planner_status.status = PlannerStates.Idle
                self._planner_status.running_text = "Quota of hours fulfilled"
                return
            duration = dt.timedelta(hours=max(0, self._duration - self.low_hours) - 1)
            # TODO: Need to fix this so that the duration amount of hours are found in range for static
            # duration = dt.timedelta(hours=1)
        else:
            duration = dt.timedelta(hours=self._duration - 1)

        # Initiate states and variables for Moving planner
        if self._is_moving:
            start_time = now
            end_time = now + dt.timedelta(hours=self._search_length)

        # Initiate states and variables for Static planner
        elif self._is_static:
            start_time = now.replace(
                hour=self._start_time, minute=0, second=0, microsecond=0
            )
            end_time = now.replace(
                hour=self._end_time, minute=0, second=0, microsecond=0
            )
            # First ensure end is after start (spans over midnight)
            if end_time < start_time:
                # Have not started range yet
                if end_time < now:
                    end_time += dt.timedelta(days=1)
                # Started range "yesterday"
                else:
                    start_time -= dt.timedelta(days=1)
            # In active range
            if start_time < now and end_time > now:
                # Bump up start to now so that prices in the past is not used
                start_time = now

        # Invalid planner type
        else:
            _LOGGER.warning("Aborting update since unknown planner type")
            self._planner_status.status = PlannerStates.Error
            self._planner_status.config_text = "Bad planner type"
            return

        prices_groups: list[NordpoolPricesGroup] = []
        offset = 0
        while True:
            start_offset = dt.timedelta(hours=offset)
            first_time = start_time + start_offset
            last_time = first_time + duration
            if offset != 0 and last_time > end_time:
                break
            offset += 1
            prices_group = self._prices_entity.get_prices_group(first_time, last_time)
            if not prices_group.valid:
                continue
                # TODO: Should not end up here, why?
            prices_groups.append(prices_group)

        if len(prices_groups) == 0:
            _LOGGER.warning(
                "Aborting update since no prices fetched in range %s to %s with duration %s",
                start_time,
                end_time,
                duration,
            )
            self._planner_status.status = PlannerStates.Warning
            self._planner_status.running_text = "No prices in active range"
            return

        _LOGGER.debug(
            "Processing %s prices_groups found in range %s to %s",
            len(prices_groups),
            start_time,
            end_time,
        )

        accept_cost = self._accept_cost
        accept_rate = self._accept_rate
        lowest_cost_group: NordpoolPricesGroup = prices_groups[0]
        for p in prices_groups:
            if accept_cost and p.average < accept_cost:
                _LOGGER.debug("Accept cost fulfilled")
                self.set_lowest_cost_state(p)
                break
            if accept_rate:
                if self._prices_entity.average_attr <= 0:
                    if p.average <= 0:
                        _LOGGER.debug(
                            "Accept rate indirectly fulfilled (NP average & range average <= 0)"
                        )
                        self.set_lowest_cost_state(p)
                        break
                elif (p.average / self._prices_entity.average_attr) <= accept_rate:
                    _LOGGER.debug("Accept rate fulfilled")
                    self.set_lowest_cost_state(p)
                    break
            if p.average < lowest_cost_group.average:
                lowest_cost_group = p
        else:
            self.set_lowest_cost_state(lowest_cost_group)

        highest_cost_group: NordpoolPricesGroup = prices_groups[0]
        for p in prices_groups:
            if p.average > highest_cost_group.average:
                highest_cost_group = p
        self.set_highest_cost_state(highest_cost_group)

        if not self._last_update:
            pass
        elif self._last_update.hour != now.hour:
            _LOGGER.debug(
                "Swapping hour on change from %s to %s", self._last_update, now
            )
            if self._is_static:
                if self.low_cost_state.on_at(now):
                    if self.low_hours is None:
                        self.low_hours = 1
                    else:
                        self.low_hours += 1
                if end_time.hour == now.hour:
                    self.low_hours = 0
        self._last_update = now
        for listener in self._output_listeners.values():
            listener.update_callback()

    def set_lowest_cost_state(self, prices_group: NordpoolPricesGroup) -> None:
        """Set the state to output variable."""
        self.low_cost_state.starts_at = prices_group.start_time
        self.low_cost_state.cost_at = prices_group.average
        if prices_group.average != 0:
            self.low_cost_state.now_cost_rate = (
                self._prices_entity.current_price_attr / prices_group.average
            )
        else:
            self.low_cost_state.now_cost_rate = STATE_UNAVAILABLE
        _LOGGER.debug("Wrote lowest cost state: %s", self.low_cost_state)

    def set_highest_cost_state(self, prices_group: NordpoolPricesGroup) -> None:
        """Set the state to output variable."""
        self.high_cost_state.starts_at = prices_group.start_time
        self.high_cost_state.cost_at = prices_group.average
        if prices_group.average != 0:
            self.high_cost_state.now_cost_rate = (
                self._prices_entity.current_price_attr / prices_group.average
            )
        else:
            self.high_cost_state.now_cost_rate = STATE_UNAVAILABLE
        _LOGGER.debug("Wrote highest cost state: %s", self.high_cost_state)

    def set_done_for_now(self) -> None:
        """Set output state to off."""
        now_hour = dt_util.now().replace(minute=0, second=0, microsecond=0)
        start_hour = now_hour.replace(hour=self._start_time)
        if start_hour < now_hour:
            start_hour += dt.timedelta(days=1)
        self.low_cost_state.starts_at = start_hour
        self.low_cost_state.cost_at = STATE_UNAVAILABLE
        self.low_cost_state.now_cost_rate = STATE_UNAVAILABLE
        self.high_cost_state.starts_at = start_hour
        self.high_cost_state.cost_at = STATE_UNAVAILABLE
        self.high_cost_state.now_cost_rate = STATE_UNAVAILABLE
        _LOGGER.debug("Setting output states to unavailable")
        for listener in self._output_listeners.values():
            listener.update_callback()

    def set_unavailable(self) -> None:
        """Set output state to unavailable."""
        self.low_cost_state.starts_at = STATE_UNAVAILABLE
        self.low_cost_state.cost_at = STATE_UNAVAILABLE
        self.low_cost_state.now_cost_rate = STATE_UNAVAILABLE
        self.high_cost_state.starts_at = STATE_UNAVAILABLE
        self.high_cost_state.cost_at = STATE_UNAVAILABLE
        self.high_cost_state.now_cost_rate = STATE_UNAVAILABLE
        _LOGGER.debug("Setting output states to unavailable")
        for listener in self._output_listeners.values():
            listener.update_callback()


class PricesEntity:
    """Representation for Nordpool state."""

    def __init__(self, unique_id: str) -> None:
        """Initialize state tracker."""
        self._unique_id = unique_id
        self._np = None

    def as_dict(self):
        """For diagnostics serialization."""
        return self.__dict__

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
    def _all_prices(self):
        if np_prices := self._np.attributes.get("raw_today"):
            # For Nordpool format
            if self._np.attributes["tomorrow_valid"]:
                np_prices += self._np.attributes["raw_tomorrow"]
            return np_prices
        elif e_prices := self._np.attributes.get("prices"):  # noqa: RET505
            # For ENTSO-e format
            e_prices = [
                {"start": dt_util.parse_datetime(ep["time"]), "value": ep["price"]}
                for ep in e_prices
            ]
            return e_prices  # noqa: RET504
        return []

    @property
    def average_attr(self):
        """Get the average price attribute."""
        if self._np is not None:
            if "average_electricity_price" in self._np.entity_id:
                # For ENTSO-e average
                try:
                    return float(self._np.state)
                except ValueError:
                    _LOGGER.warning(
                        'Could not convert "%s" to float for average sensor "%s"',
                        self._np.state,
                        self._np.entity_id,
                    )
            else:
                # For Nordpool format
                return self._np.attributes["average"]
        return None

    @property
    def current_price_attr(self):
        """Get the current price attribute."""
        if self._np is not None:
            if current := self._np.attributes.get("current_price"):
                # For Nordpool format
                return current
            else:  # noqa: RET505
                # For general, find in list
                now = dt_util.now()
                for price in self._all_prices:
                    if (
                        price["start"] < now
                        and price["start"] + dt.timedelta(hours=1) > now
                    ):
                        return price["value"]
        return None

    def update(self, hass: HomeAssistant) -> bool:
        """Update price in storage."""
        if self._unique_id == NAME_FILE_READER:
            np = get_np_from_file(PATH_FILE_READER)
        else:
            np = hass.states.get(self._unique_id)

        if np is None:
            _LOGGER.warning("Got empty data from Nordpool entity %s ", self._unique_id)
        elif "today" not in np.attributes and "prices_today" not in np.attributes:
            _LOGGER.warning(
                "No values for today in Nordpool entity %s ", self._unique_id
            )
        else:
            _LOGGER.debug(
                "Nordpool sensor %s was updated successfully", self._unique_id
            )
            if self._np is None:
                pass
            self._np = np

        if self._np is None:
            return False
        return True

    def get_prices_group(
        self, start: dt.datetime, end: dt.datetime
    ) -> NordpoolPricesGroup:
        """Get a range of prices from NP given the start and end datetimes.

        Ex. If start is 7:05 and end 10:05, a list of 4 prices will be returned,
        7, 8, 9 & 10.
        """
        started = False
        selected = []
        for p in self._all_prices:
            if p["start"] > start - dt.timedelta(hours=1):
                started = True
            if p["start"] > end:
                break
            if started:
                selected.append(p)
        return NordpoolPricesGroup(selected)


class NordpoolPricesGroup:
    """A slice if Nordpool prices with helper functions."""

    def __init__(self, prices) -> None:
        """Initialize price group."""
        self._prices = prices

    def __str__(self) -> str:
        """Get string representation of class."""
        return f"start_time={self.start_time.strftime("%Y-%m-%d %H:%M")} average={self.average} len(_prices)={len(self._prices)}"

    def __repr__(self) -> str:
        """Get string representation for debugging."""
        return type(self).__name__ + f" ({self.__str__()})"

    @property
    def valid(self) -> bool:
        """Is the price group valid."""
        if len(self._prices) == 0:
            # _LOGGER.debug("None-valid price range group, len=%s", len(self._prices))
            return False
        return True

    @property
    def average(self) -> float:
        """The average price of the price group."""
        # if not self.valid:
        #     _LOGGER.warning(
        #         "Average set to 1 for invalid price group, should not happen"
        #     )
        #     return 1
        return sum([p["value"] for p in self._prices]) / len(self._prices)

    @property
    def start_time(self) -> dt.datetime:
        """The start time of first price in group."""
        # if not self.valid:
        #     _LOGGER.warning(
        #         "Start time set to None for invalid price group, should not happen"
        #     )
        #     return None
        return self._prices[0]["start"]


class NordpoolPlannerState:
    """State attribute representation."""

    def __init__(self) -> None:
        """Initiate states."""
        self.starts_at = STATE_UNKNOWN
        self.cost_at = STATE_UNKNOWN
        self.now_cost_rate = STATE_UNKNOWN

    def __str__(self) -> str:
        """Get string representation of class."""
        return f"start_at={self.starts_at} cost_at={self.cost_at:.2} now_cost_rate={self.now_cost_rate:.2}"

    def as_dict(self):
        """For diagnostics serialization."""
        return self.__dict__

    def on_at(self, time: dt.datetime) -> bool:
        """Get boolean state if start is before given timestamp."""
        if self.starts_at not in [
            STATE_UNKNOWN,
            STATE_UNAVAILABLE,
        ]:
            return self.starts_at < time
        return False


class NordpoolPlannerStatus:
    """Status for the overall planner."""

    def __init__(self) -> None:
        """Initiate status."""
        self.status = PlannerStates.Unknown
        self.running_text = ""
        self.config_text = ""


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

    def as_dict(self):
        """For diagnostics serialization."""
        return {
            k: v
            for k, v in self.__dict__.items()
            if not (
                k.startswith("_")
                or k in ["hass", "platform", "registry_entry", "device_entry"]
            )
        }

    @property
    def should_poll(self):
        """No need to poll. Coordinator notifies entity of updates."""
        return False

    def update_callback(self) -> None:
        """Call from planner that new data available."""
        self.schedule_update_ha_state()
