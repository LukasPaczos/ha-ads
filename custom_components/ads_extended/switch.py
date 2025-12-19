"""Support for ADS switch platform."""

from __future__ import annotations

from typing import Any

from custom_components.ads_extended.hub import AdsHub
import pyads
import voluptuous as vol

from homeassistant.components.switch import (
    PLATFORM_SCHEMA as SWITCH_PLATFORM_SCHEMA,
    SwitchEntity,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_ADS_VAR, DATA_ADS, STATE_KEY_STATE
from .entity import AdsEntity

CONF_ADS_VAR_TURN_ON = "adsvar_turn_on"
CONF_ADS_VAR_TURN_OFF = "adsvar_turn_off"

DEFAULT_NAME = "ADS Switch"

PLATFORM_SCHEMA = SWITCH_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ADS_VAR): cv.string,
        vol.Optional(CONF_ADS_VAR_TURN_ON): cv.string,
        vol.Optional(CONF_ADS_VAR_TURN_OFF): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)


def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up switch platform for ADS."""
    ads_hub = hass.data[DATA_ADS]

    name: str = config[CONF_NAME]
    ads_var_is_on: str = config[CONF_ADS_VAR]
    ads_var_turn_on: str | None = config.get(CONF_ADS_VAR_TURN_ON)
    ads_var_turn_off: str | None = config.get(CONF_ADS_VAR_TURN_OFF)

    add_entities([AdsSwitch(ads_hub, ads_var_is_on, ads_var_turn_on, ads_var_turn_off, name)])


class AdsSwitch(AdsEntity, SwitchEntity):
    """Representation of an ADS switch device."""

    def __init__(
        self,
        ads_hub: AdsHub,
        ads_var_is_on: str,
        ads_var_turn_on: str | None,
        ads_var_turn_off: str | None,
        name: str,
    ) -> None:
        """Initialize ADS switch."""
        super().__init__(ads_hub, name, ads_var_is_on)
        self._ads_var_turn_on = ads_var_turn_on
        self._ads_var_turn_off = ads_var_turn_off

    async def async_added_to_hass(self) -> None:
        """Register device notification."""
        await self.async_initialize_device(self._ads_var, pyads.PLCTYPE_BOOL)

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self._state_dict[STATE_KEY_STATE]

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the switch on."""
        if self._ads_var_turn_on is not None:
            self._ads_hub.write_by_name(self._ads_var_turn_on, True, pyads.PLCTYPE_BOOL)
        else:
            self._ads_hub.write_by_name(self._ads_var, True, pyads.PLCTYPE_BOOL)

    def turn_off(self, **kwargs: Any) -> None:
        """Turn the switch off."""
        if self._ads_var_turn_off is not None:
            self._ads_hub.write_by_name(self._ads_var_turn_off, True, pyads.PLCTYPE_BOOL)
        else:
            self._ads_hub.write_by_name(self._ads_var, False, pyads.PLCTYPE_BOOL)