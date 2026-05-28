"""Climate platform for Go-On UTOR-RKY20-N7-1 Aircon IR."""

from __future__ import annotations

from homeassistant.components.climate import (
    ATTR_TEMPERATURE,
    ClimateEntity,
    ClimateEntityFeature,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import ATTR_ENTITY_ID, CONF_NAME, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.restore_state import RestoreEntity

from .const import (
    CONF_DEFAULT_FAN_MODE,
    CONF_DEFAULT_TEMPERATURE,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_REMOTE_ENTITY_ID,
    CONF_REPEATS,
    DEFAULT_FAN_MODE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_REPEATS,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    FAN_MODES,
)
from .ir import COMMAND_POWER_OFF, COMMAND_SET, encode_broadlink_base64


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Go-On UTOR-RKY20-N7-1 Aircon IR climate entities."""
    async_add_entities([AirconIrClimate(hass, entry)])


class AirconIrClimate(ClimateEntity, RestoreEntity):
    """Climate entity that emits generated Broadlink IR commands."""

    _attr_assumed_state = True
    _attr_hvac_modes = [HVACMode.COOL, HVACMode.OFF]
    _attr_should_poll = False
    _attr_supported_features = (
        ClimateEntityFeature.TARGET_TEMPERATURE | ClimateEntityFeature.FAN_MODE
    )
    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the climate entity."""
        self.hass = hass
        self._entry = entry
        self._attr_unique_id = f"{entry.data[CONF_REMOTE_ENTITY_ID]}_climate"
        self._attr_name = entry.data[CONF_NAME]
        self._attr_fan_modes = FAN_MODES
        self._attr_min_temp = int(entry.data.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
        self._attr_max_temp = int(entry.data.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))
        self._remote_entity_id = entry.data[CONF_REMOTE_ENTITY_ID]
        self._repeats = int(entry.data.get(CONF_REPEATS, DEFAULT_REPEATS))
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = int(
            entry.data.get(CONF_DEFAULT_TEMPERATURE, DEFAULT_TEMPERATURE)
        )
        self._attr_fan_mode = entry.data.get(CONF_DEFAULT_FAN_MODE, DEFAULT_FAN_MODE)

    @property
    def device_info(self):
        """Return device information."""
        return {
            "identifiers": {(DOMAIN, self._entry.entry_id)},
            "name": self._entry.data[CONF_NAME],
            "manufacturer": "Go-On",
            "model": "UTOR-RKY20-N7-1",
        }

    async def async_added_to_hass(self) -> None:
        """Restore previous state after Home Assistant restarts."""
        await super().async_added_to_hass()
        last_state = await self.async_get_last_state()
        if last_state is None:
            return

        if last_state.state in [mode.value for mode in self._attr_hvac_modes]:
            self._attr_hvac_mode = HVACMode(last_state.state)

        if last_state.attributes.get(ATTR_TEMPERATURE) is not None:
            self._attr_target_temperature = int(
                float(last_state.attributes[ATTR_TEMPERATURE])
            )

        restored_fan_mode = last_state.attributes.get("fan_mode")
        if restored_fan_mode in FAN_MODES:
            self._attr_fan_mode = restored_fan_mode

    async def async_set_temperature(self, **kwargs) -> None:
        """Set target temperature and send a cool command when active."""
        if ATTR_TEMPERATURE not in kwargs:
            return

        self._attr_target_temperature = int(kwargs[ATTR_TEMPERATURE])
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def async_set_fan_mode(self, fan_mode: str) -> None:
        """Set low/high power mode and send a cool command when active."""
        if fan_mode not in FAN_MODES:
            raise ValueError(f"Unsupported fan mode: {fan_mode}")

        self._attr_fan_mode = fan_mode
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.COOL:
            self._attr_hvac_mode = HVACMode.COOL
            await self._async_send(COMMAND_SET)
        elif hvac_mode == HVACMode.OFF:
            await self._async_send(COMMAND_POWER_OFF)
            self._attr_hvac_mode = HVACMode.OFF
        else:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")

        self.async_write_ha_state()

    async def _async_send(self, command: str) -> None:
        """Send the generated command through the configured remote entity."""
        command_payload = encode_broadlink_base64(
            command,
            int(self._attr_target_temperature),
            str(self._attr_fan_mode),
        )

        service_data = {
            ATTR_ENTITY_ID: self._remote_entity_id,
            "command": command_payload,
        }
        if self._repeats > 1:
            service_data["num_repeats"] = self._repeats

        await self.hass.services.async_call(
            "remote",
            "send_command",
            service_data,
            blocking=True,
        )
