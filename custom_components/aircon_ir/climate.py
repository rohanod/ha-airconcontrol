"""Climate entity for the Go-On UTOR-RKY20-N7-1 Aircon IR (infrared only)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import ClimateEntity, ClimateEntityFeature, HVACMode
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_TEMPERATURE, CONF_NAME
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity import DeviceInfo
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_DEFAULT_FAN_MODE,
    CONF_DEFAULT_SWING_MODE,
    CONF_DEFAULT_TEMPERATURE,
    CONF_INFRARED_ENTITY_ID,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_REPEATS,
    DEFAULT_FAN_MODE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_REPEATS,
    DEFAULT_SWING_MODE,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    FAN_MODES,
    SWING_MODES,
)
from .ir import COMMAND_POWER_OFF, COMMAND_SET, make_utor_command


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: Any,
) -> None:
    """Set up the climate entity from a config entry."""
    async_add_entities([AirconIrClimate(hass, entry)], True)


class AirconIrClimate(ClimateEntity, RestoreEntity):
    """Climate entity that sends generated IR via Home Assistant infrared entity."""

    _attr_has_entity_name = False
    _attr_temperature_unit = "°C"
    _attr_hvac_modes = [HVACMode.OFF, HVACMode.COOL]
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_precision = 1.0

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        self.hass = hass
        self._entry = entry
        cfg = {**entry.data, **entry.options}
        self._attr_unique_id = f"{entry.entry_id}_climate"
        self._attr_name = cfg[CONF_NAME]
        self._attr_fan_modes = FAN_MODES
        self._attr_min_temp = int(cfg.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
        self._attr_max_temp = int(cfg.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))
        self._infrared_entity_id = cfg[CONF_INFRARED_ENTITY_ID]
        self._repeats = int(cfg.get(CONF_REPEATS, DEFAULT_REPEATS))
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = int(cfg.get(CONF_DEFAULT_TEMPERATURE, DEFAULT_TEMPERATURE))
        self._attr_fan_mode = cfg.get(CONF_DEFAULT_FAN_MODE, DEFAULT_FAN_MODE)
        self._attr_swing_modes = SWING_MODES
        self._attr_swing_mode = cfg.get(CONF_DEFAULT_SWING_MODE, DEFAULT_SWING_MODE)

    @property
    def device_info(self) -> DeviceInfo:
        return DeviceInfo(
            identifiers={(DOMAIN, self._entry.entry_id)},
            name=self._entry.data[CONF_NAME],
            manufacturer="Go-On",
            model="UTOR-RKY20-N7-1 (Aircon IR — infrared)",
        )

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return
        hvac_mode = last_state.state
        if hvac_mode in (HVACMode.OFF, HVACMode.COOL):
            self._attr_hvac_mode = HVACMode(hvac_mode)
        target_temperature = last_state.attributes.get("temperature")
        if target_temperature is not None:
            try:
                self._attr_target_temperature = int(target_temperature)
            except (TypeError, ValueError):
                pass
        restored_fan_mode = last_state.attributes.get("fan_mode")
        if restored_fan_mode in FAN_MODES:
            self._attr_fan_mode = restored_fan_mode
        restored_swing = last_state.attributes.get("swing_mode")
        if restored_swing in SWING_MODES:
            self._attr_swing_mode = restored_swing

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode not in self._attr_hvac_modes:
            raise ValueError(f"Unsupported hvac mode: {hvac_mode}")
        if hvac_mode == HVACMode.OFF:
            await self._async_send(COMMAND_POWER_OFF)
            self._attr_hvac_mode = HVACMode.OFF
        else:
            self._attr_hvac_mode = HVACMode.COOL
            await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def async_set_temperature(self, **kwargs: Any) -> None:
        temperature = kwargs.get(ATTR_TEMPERATURE)
        if temperature is None:
            return
        self._attr_target_temperature = int(temperature)
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        if fan_mode not in FAN_MODES:
            raise ValueError(f"Unsupported fan mode: {fan_mode}")
        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        if swing_mode not in SWING_MODES:
            raise ValueError(f"Unsupported swing mode: {swing_mode}")
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def _async_send(self, command: str) -> None:
        from homeassistant.components import infrared

        cmd = make_utor_command(
            command,
            int(self._attr_target_temperature),
            str(self._attr_fan_mode),
            str(self._attr_swing_mode),
        )
        cmd.repeat_count = max(0, self._repeats - 1)
        await infrared.async_send_command(self.hass, self._infrared_entity_id, cmd)
