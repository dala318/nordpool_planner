from __future__ import annotations

from typing import Any
import voluptuous as vol
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import (
    PLATFORM_SCHEMA,
    SensorEntity,
    SensorDeviceClass,
)
from homeassistant.const import STATE_UNKNOWN
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType
from homeassistant.util import dt

from . import NordpoolPlannerEntity

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
        # Check not both variants in same
        vol.Required(
            vol.Any(MOVING, STATIC),
            msg=TYPE_MISSING_MSG,
        ): object,
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
    # if MOVING in config.keys():
    #     search_length = config[MOVING][SEARCH_LENGTH]
    #     var_search_length_entity = config[MOVING][VAR_SEARCH_LENGTH_ENTITY]
    #     add_entities(
    #         [
    #             NordpoolPlannerMovingSensor(
    #                 search_length=search_length,
    #                 var_search_length_entity=var_search_length_entity,
    #                 nordpool_entity=nordpool_entity,
    #                 entity_id=entity_id,
    #                 duration=duration,
    #                 var_duration_entity=var_duration_entity,
    #                 accept_cost=accept_cost,
    #                 accept_rate=accept_rate,
    #             )
    #         ]
    #     )
    if STATIC in config.keys():
        end_hour = config[STATIC][END_HOUR]
        var_end_hour_entity = config[STATIC][VAR_END_HOUR_ENTITY]
        split_hours = config[STATIC][SPLIT_HOURS]
        add_entities(
            [
                NordpoolPlannerStaticSensor(
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


# class NordpoolPlannerMovingSensor(NordpoolPlannerEntity, SensorEntity):
#     """Nordpool planner with moving search length"""

#     def __init__(self, search_length, var_search_length_entity, **kwds):
#         super().__init__(**kwds)
#         self._search_length = search_length
#         self._var_search_length_entity = var_search_length_entity

#     def update(self):
#         """Called from Home Assistant to update entity value"""
#         self._update_np_prices()
#         if self._np is not None:
#             search_length = min(
#                 self._get_input_entity_or_default(
#                     self._var_search_length_entity, self._search_length
#                 ),
#                 self._search_length,
#             )
#             self._update(dt.now().hour, search_length)


class NordpoolPlannerStaticSensor(NordpoolPlannerEntity, SensorEntity):
    """Nordpool planner with fixed search length end time"""

    def __init__(self, end_hour, var_end_hour_entity, split_hours, **kwds):
        super().__init__(**kwds)
        self._end_hour = end_hour
        self._var_end_hour_entity = var_end_hour_entity
        self._split_hours = split_hours

        # self.native_unit_of_measurement = STATE_UNKNOWN
        # self.unit_of_measurement = STATE_UNKNOWN
        self.device_class = SensorDeviceClass.DATE

        # TODO: Need to add logic to handle counting used hours
        # self._now_hour = dt.now().hour
        self._produced_hours = 0
        self._remaining = 0

    def update(self):
        """Called from Home Assistant to update entity value"""
        self._update_np_prices()
        now = dt.now()
        # if self._now_hour == now.hour + 1:
        #     self._now_hour = now.hour
        if self._np is not None:
            end_hour = self._get_input_entity_or_default(
                self._var_end_hour_entity, self._end_hour
            )
            if end_hour < now.hour:
                end_hour += 24
            self._update(now.hour, end_hour - now.hour)
