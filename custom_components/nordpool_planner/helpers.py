"""Helper functions package."""

import contextlib
import datetime as dt
import json
import pathlib

from homeassistant.core import State
from homeassistant.util import dt as dt_util


def get_np_from_file(data_file: str, set_today: bool = True) -> State | None:
    """Fake NP entity from file."""
    diag_data = {}
    file_path = pathlib.Path(data_file)
    if file_path.is_file():
        with contextlib.suppress(ValueError):
            diag_data = json.loads(file_path.read_text(encoding="utf-8"))

    if data := diag_data.get("data"):
        if planner := data.get("planner"):
            if prices_entity := planner.get("_prices_entity"):
                if np := prices_entity.get("_np"):
                    attr = np.get("attributes")
                    now = dt_util.now()
                    if "raw_today" in attr:
                        for item in attr["raw_today"]:
                            for key, value in item.items():
                                if key in ["start", "end"] and isinstance(value, str):
                                    item[key] = dt_util.parse_datetime(value)
                                    if set_today:
                                        item[key] = item[key].replace(
                                            year=now.year, month=now.month, day=now.day
                                        )
                    if "raw_tomorrow" in attr:
                        for item in attr["raw_tomorrow"]:
                            for key, value in item.items():
                                if key in ["start", "end"] and isinstance(value, str):
                                    item[key] = dt_util.parse_datetime(value)
                                    if set_today:
                                        item[key] = item[key].replace(
                                            year=now.year, month=now.month, day=now.day
                                        )
                                        item[key] += dt.timedelta(days=1)
                    if "prices" in attr and set_today:
                        first_time = None
                        original_tz = None
                        for item in attr["prices"]:
                            for key, value in item.items():
                                if key in ["time"] and isinstance(value, str):
                                    fixed_time = dt_util.parse_datetime(value)
                                    if not original_tz:
                                        original_tz = fixed_time.tzinfo
                                    fixed_time = fixed_time.astimezone(now.tzinfo)
                                    if not first_time:
                                        first_time = fixed_time
                                    if fixed_time.day == first_time.day:
                                        fixed_time = fixed_time.replace(
                                            year=now.year, month=now.month, day=now.day
                                        )
                                    else:
                                        fixed_time = fixed_time.replace(
                                            year=now.year, month=now.month, day=now.day
                                        )
                                        fixed_time += dt.timedelta(days=1)
                                    item[key] = fixed_time.astimezone(
                                        original_tz
                                    ).strftime("%Y-%m-%d %H:%M:%S%z")
                    return State(
                        entity_id=np.get("entity_id"),
                        state=np.get("state"),
                        attributes=attr,
                        # last_changed: datetime.datetime | None = None,
                        # last_reported: datetime.datetime | None = None,
                        # last_updated: datetime.datetime | None = None,
                        # context: Context | None = None,
                        # validate_entity_id: bool | None = True,
                        # state_info: StateInfo | None = None,
                        # last_updated_timestamp: float | None = None,
                    )

    return None
