"""Button definitions."""

from __future__ import annotations

import logging

from homeassistant.components.button import (
    ButtonDeviceClass,
    ButtonEntityDescription,
    ButtonEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    EntityCategory,
)
from homeassistant.core import HomeAssistant

from . import NordpoolPlanner, NordpoolPlannerEntity
from .const import (
    CONF_END_TIME_ENTITY,
    CONF_USED_TIME_RESET_ENTITY,
    DOMAIN,
)

_LOGGER = logging.getLogger(__name__)

CONF_USED_TIME_RESET_ENTITY_DESCRIPTION = ButtonEntityDescription(
    key=CONF_USED_TIME_RESET_ENTITY,
    device_class=ButtonDeviceClass.RESTART,
    entity_category=EntityCategory.DIAGNOSTIC
)


async def async_setup_entry(
    hass: HomeAssistant, config_entry: ConfigEntry, async_add_entities
):
    """Create action button entities for platform."""

    planner: NordpoolPlanner = hass.data[DOMAIN][config_entry.entry_id]
    entities = []

    if config_entry.data.get(CONF_END_TIME_ENTITY):
        entities.append(
            NordpoolPlannerButton(
                planner,
                entity_description=CONF_USED_TIME_RESET_ENTITY_DESCRIPTION,
            )
        )

    async_add_entities(entities)
    return True


class NordpoolPlannerButton(NordpoolPlannerEntity, ButtonEntity):
    """Button config entity."""

    def __init__(
        self,
        planner,
        entity_description: ButtonEntityDescription,
    ) -> None:
        """Initialize the entity."""
        super().__init__(planner)
        self.entity_description = entity_description
        self._attr_name = (
            self._planner.name
            + " "
            + entity_description.key.replace("_entity", "").replace("_", " ")
        )
        self._attr_unique_id = (
            ("nordpool_planner_" + self._attr_name)
            .lower()
            .replace(".", "")
            .replace(" ", "_")
        )

    async def async_added_to_hass(self) -> None:
        """Load the last known state when added to hass."""
        await super().async_added_to_hass()
        self._planner.register_input_entity_id(
            self.entity_id, self.entity_description.key
        )

    def press(self) -> None:
        """Press the button."""
        self._planner.low_hours = 0
