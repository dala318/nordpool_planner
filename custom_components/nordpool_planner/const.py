"""Common constants for integration."""

from enum import Enum

DOMAIN = "nordpool_planner"


class PlannerStates(Enum):
    """Standard numeric identifiers for planner states."""

    Ok = 0
    Idle = 1
    Warning = 2
    Error = 3
    Unknown = 4


CONF_TYPE = "type"
CONF_TYPE_MOVING = "moving"
CONF_TYPE_STATIC = "static"
CONF_TYPE_LIST = [CONF_TYPE_MOVING, CONF_TYPE_STATIC]
CONF_PRICES_ENTITY = "prices_entity"
CONF_LOW_COST_ENTITY = "low_cost_entity"
CONF_HEALTH_ENTITY = "health_entity"
CONF_HIGH_COST_ENTITY = "high_cost_entity"
CONF_STARTS_AT_ENTITY = "starts_at_entity"
CONF_DURATION_ENTITY = "duration_entity"
CONF_ACCEPT_COST_ENTITY = "accept_cost_entity"
CONF_ACCEPT_RATE_ENTITY = "accept_rate_entity"
CONF_SEARCH_LENGTH_ENTITY = "search_length_entity"
CONF_END_TIME_ENTITY = "end_time_entity"
CONF_USED_TIME_RESET_ENTITY = "used_time_reset_entity"
CONF_START_TIME_ENTITY = "start_time_entity"
CONF_USED_HOURS_LOW_ENTITY = "used_hours_low_entity"

NAME_FILE_READER = "file_reader"

PATH_FILE_READER = "config/config_entry-nordpool_planner.json"
