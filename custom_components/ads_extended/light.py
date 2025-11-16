"""Support for ADS light sources."""

from __future__ import annotations

from typing import Any
import logging

import pyads
from pyads.constants import PLCTYPE_ARR_UINT
import voluptuous as vol

from homeassistant.components.light import (
    ATTR_BRIGHTNESS,
    ATTR_RGBW_COLOR,
    PLATFORM_SCHEMA as LIGHT_PLATFORM_SCHEMA,
    ColorMode,
    LightEntity,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.typing import ConfigType, DiscoveryInfoType

from .const import CONF_ADS_VAR, DATA_ADS, STATE_KEY_STATE
from .entity import AdsEntity
from .hub import AdsHub

CONF_ADS_VAR_BRIGHTNESS = "adsvar_brightness"
CONF_ADS_VAR_RGBW_COLOR = "adsvar_rgbw_color"
STATE_KEY_BRIGHTNESS = "brightness"
STATE_KEY_RGBW_COLOR = "rgbw_color"

DEFAULT_NAME = "ADS Light"
PLATFORM_SCHEMA = LIGHT_PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_ADS_VAR): cv.string,
        vol.Optional(CONF_ADS_VAR_BRIGHTNESS): cv.string,
        vol.Optional(CONF_ADS_VAR_RGBW_COLOR): cv.string,
        vol.Optional(CONF_NAME, default=DEFAULT_NAME): cv.string,
    }
)

_LOGGER = logging.getLogger(__name__)

def setup_platform(
    hass: HomeAssistant,
    config: ConfigType,
    add_entities: AddEntitiesCallback,
    discovery_info: DiscoveryInfoType | None = None,
) -> None:
    """Set up the light platform for ADS."""
    ads_hub = hass.data[DATA_ADS]

    ads_var_enable: str = config[CONF_ADS_VAR]
    ads_var_brightness: str | None = config.get(CONF_ADS_VAR_BRIGHTNESS)
    ads_var_rgbw_color: str | None = config.get(CONF_ADS_VAR_RGBW_COLOR)
    name: str = config[CONF_NAME]

    add_entities([AdsLight(ads_hub, ads_var_enable, ads_var_brightness, ads_var_rgbw_color, name)])

class AdsLight(AdsEntity, LightEntity):
    """Representation of ADS light."""

    def __init__(
        self,
        ads_hub: AdsHub,
        ads_var_enable: str,
        ads_var_brightness: str | None,
        ads_var_rgbw_color: str | None,
        name: str,
    ) -> None:
        """Initialize AdsLight entity."""
        super().__init__(ads_hub, name, ads_var_enable)
        self._state_dict[STATE_KEY_BRIGHTNESS] = None
        self._state_dict[STATE_KEY_RGBW_COLOR] = None
        self._ads_var_brightness = ads_var_brightness
        self._ads_var_rgbw_color = ads_var_rgbw_color
        if ads_var_rgbw_color is not None:
            self._attr_color_mode = ColorMode.RGBW
            self._attr_supported_color_modes = {ColorMode.RGBW}
        elif ads_var_brightness is not None:
            self._attr_color_mode = ColorMode.BRIGHTNESS
            self._attr_supported_color_modes = {ColorMode.BRIGHTNESS}
        else:
            self._attr_color_mode = ColorMode.ONOFF
            self._attr_supported_color_modes = {ColorMode.ONOFF}

    async def async_added_to_hass(self) -> None:
        """Register device notification."""
        await self.async_initialize_device(self._ads_var, pyads.PLCTYPE_BOOL)

        if self._ads_var_brightness is not None:
            await self.async_initialize_device(
                self._ads_var_brightness,
                pyads.PLCTYPE_UINT,
                STATE_KEY_BRIGHTNESS,
            )

        if self._ads_var_rgbw_color is not None:
            await self.async_initialize_device(
                self._ads_var_rgbw_color,
                PLCTYPE_ARR_UINT(4),
                STATE_KEY_RGBW_COLOR,
            )


    @property
    def brightness(self) -> int | None:
        """Return the brightness of the light (0..255)."""
        return self._state_dict[STATE_KEY_BRIGHTNESS]

    @property
    def rgbw_color(self) -> tuple[int, int, int, int] | None:
        """Return (R, G, B, W)."""
        rgbw = self._state_dict[STATE_KEY_RGBW_COLOR]
        if rgbw is None:
            return None

        # Expect a list/tuple of four 0..255 integers from hub; warn otherwise
        if isinstance(rgbw, (tuple, list)) and len(rgbw) == 4:
            try:
                r, g, b, w = (int(rgbw[0]), int(rgbw[1]), int(rgbw[2]), int(rgbw[3]))
            except (ValueError, TypeError):
                _LOGGER.warning("rgbw_color has non-integer values: %s", rgbw)
                return None

            # Clamp to 0..255 to satisfy HA expectations
            if not all(0 <= v <= 255 for v in [r, g, b, w]):
                _LOGGER.warning(
                    "rgbw_color values out of range 0-255: R=%d, G=%d, B=%d, W=%d",
                    r, g, b, w
                )
            def clamp(v: int) -> int:
                return max(0, min(255, v))

            return (clamp(r), clamp(g), clamp(b), clamp(w))

        _LOGGER.warning(
            "Unexpected rgbw_color value (expected tuple/list of 4): %s", type(rgbw)
        )
        return None

    @property
    def is_on(self) -> bool:
        """Return True if the entity is on."""
        return self._state_dict[STATE_KEY_STATE]

    def turn_on(self, **kwargs: Any) -> None:
        """Turn the light on and set a specific dimmer or color value."""
        self._ads_hub.write_by_name(self._ads_var, True, pyads.PLCTYPE_BOOL)

        brightness = kwargs.get(ATTR_BRIGHTNESS)
        if self._ads_var_brightness is not None and brightness is not None:
            self._ads_hub.write_by_name(
                self._ads_var_brightness, brightness, pyads.PLCTYPE_UINT
            )

        rgbw_color = kwargs.get(ATTR_RGBW_COLOR)
        if self._ads_var_rgbw_color is not None and rgbw_color is not None:
            if len(rgbw_color) == 4:
                # Create c_uint16 array of length 4
                arr_type = PLCTYPE_ARR_UINT(4)
                arr = arr_type(*rgbw_color)

                # Write to PLC
                self._ads_hub.write_by_name(
                    self._ads_var_rgbw_color, arr, arr_type
                )


    def turn_off(self, **kwargs: Any) -> None:
        """Turn the light off."""
        self._ads_hub.write_by_name(self._ads_var, False, pyads.PLCTYPE_BOOL)
