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
    CONF_DEFAULT_SWING_MODE,
    CONF_DEFAULT_TEMPERATURE,
    CONF_INFRARED_ENTITY_ID,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_REMOTE_ENTITY_ID,
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
from .ir import COMMAND_POWER_OFF, COMMAND_SET, encode_broadlink_base64, make_utor_command


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
        ClimateEntityFeature.TARGET_TEMPERATURE
        | ClimateEntityFeature.FAN_MODE
        | ClimateEntityFeature.SWING_MODE
        | ClimateEntityFeature.TURN_ON
        | ClimateEntityFeature.TURN_OFF
    )
    _attr_target_temperature_step = 1
    _attr_temperature_unit = UnitOfTemperature.CELSIUS

    def __init__(self, hass: HomeAssistant, entry: ConfigEntry) -> None:
        """Initialize the climate entity."""
        self.hass = hass
        self._entry = entry
        unique_src = entry.data.get(CONF_INFRARED_ENTITY_ID) or entry.data.get(
            CONF_REMOTE_ENTITY_ID
        )
        self._attr_unique_id = f"{unique_src}_climate" if unique_src else entry.entry_id
        self._attr_name = entry.data[CONF_NAME]
        self._attr_fan_modes = FAN_MODES
        self._attr_min_temp = int(entry.data.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP))
        self._attr_max_temp = int(entry.data.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP))
        self._remote_entity_id = entry.data.get(CONF_REMOTE_ENTITY_ID)
        self._infrared_entity_id = entry.data.get(CONF_INFRARED_ENTITY_ID)
        self._repeats = int(entry.data.get(CONF_REPEATS, DEFAULT_REPEATS))
        self._attr_hvac_mode = HVACMode.OFF
        self._attr_target_temperature = int(
            entry.data.get(CONF_DEFAULT_TEMPERATURE, DEFAULT_TEMPERATURE)
        )
        self._attr_fan_mode = entry.data.get(CONF_DEFAULT_FAN_MODE, DEFAULT_FAN_MODE)
        # dashboard swing control per https://developers.home-assistant.io/docs/core/entity/climate/#swing-modes
        self._attr_swing_modes = SWING_MODES
        self._attr_swing_mode = entry.data.get(
            CONF_DEFAULT_SWING_MODE, DEFAULT_SWING_MODE
        )

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

        restored_swing = last_state.attributes.get("swing_mode")
        if restored_swing in SWING_MODES:
            self._attr_swing_mode = restored_swing

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

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        """Set swing on/off and send a cool command when active."""
        if swing_mode not in SWING_MODES:
            raise ValueError(f"Unsupported swing mode: {swing_mode}")
        self._attr_swing_mode = swing_mode
        if self._attr_hvac_mode == HVACMode.COOL:
            await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        """Set HVAC mode."""
        if hvac_mode == HVACMode.COOL:
            await self.async_turn_on()
        elif hvac_mode == HVACMode.OFF:
            await self.async_turn_off()
        else:
            raise ValueError(f"Unsupported HVAC mode: {hvac_mode}")

    async def async_turn_on(self) -> None:
        """Turn on the air conditioner in cool mode."""
        self._attr_hvac_mode = HVACMode.COOL
        await self._async_send(COMMAND_SET)
        self.async_write_ha_state()

    async def async_turn_off(self) -> None:
        """Turn off the air conditioner."""
        await self._async_send(COMMAND_POWER_OFF)
        self._attr_hvac_mode = HVACMode.OFF
        self.async_write_ha_state()

    async def _async_send(self, command: str) -> None:
        """Send via infrared emitter (official) or legacy remote (fallback).

        Uses ``infrared`` when ``infrared_entity_id`` is configured, otherwise
        ``remote.send_command``. When both are configured, sends via infrared
        (and also via remote for transition — remove remote later).
        """
        # Infrared path (official HA 2026.4+)
        if self._infrared_entity_id:
            try:
                from homeassistant.components import infrared

                cmd = make_utor_command(
                    command,
                    int(self._attr_target_temperature),
                    str(self._attr_fan_mode),
                    str(self._attr_swing_mode),
                )
                # infrared-protocols repeat_count: 0 = single shot
                cmd.repeat_count = max(0, self._repeats - 1)
                await infrared.async_send_command(
                    self.hass, self._infrared_entity_id, cmd
                )
                # dual-send during transition: also via remote if configured
                if not self._remote_entity_id:
                    return
            except Exception as err:  # noqa: BLE001
                if not self._remote_entity_id:
                    raise
                # fall through to legacy remote on infrared failure

        if self._remote_entity_id:
            command_payload = encode_broadlink_base64(
                command,
                int(self._attr_target_temperature),
                str(self._attr_fan_mode),
                str(self._attr_swing_mode),
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
            return

        raise ValueError("No infrared or remote entity configured")
