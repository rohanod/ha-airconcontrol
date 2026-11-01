"""Config flow for Go-On UTOR-RKY20-N7-1 Aircon IR — infrared only."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    CONF_DEFAULT_FAN_MODE,
    CONF_DEFAULT_SWING_MODE,
    CONF_DEFAULT_TEMPERATURE,
    CONF_INFRARED_ENTITY_ID,
    CONF_MAX_TEMP,
    CONF_MIN_TEMP,
    CONF_REPEATS,
    CONF_ZIGBEE2MQTT_TOPIC,
    DEFAULT_FAN_MODE,
    DEFAULT_MAX_TEMP,
    DEFAULT_MIN_TEMP,
    DEFAULT_NAME,
    DEFAULT_REPEATS,
    DEFAULT_SWING_MODE,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    FAN_MODES,
    SWING_MODES,
)


class AirconIrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    VERSION = 3

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            min_temp = user_input[CONF_MIN_TEMP]
            max_temp = user_input[CONF_MAX_TEMP]
            default_temperature = user_input[CONF_DEFAULT_TEMPERATURE]
            # A cleared optional selector is omitted by Home Assistant.
            # Store an explicit empty value so options override entry.data.
            user_input[CONF_INFRARED_ENTITY_ID] = (
                user_input.get(CONF_INFRARED_ENTITY_ID) or ""
            )
            user_input[CONF_ZIGBEE2MQTT_TOPIC] = (
                user_input.get(CONF_ZIGBEE2MQTT_TOPIC) or ""
            ).strip()
            if not (
                user_input[CONF_INFRARED_ENTITY_ID]
                or user_input[CONF_ZIGBEE2MQTT_TOPIC]
            ):
                errors["base"] = "transmitter_required"
            elif min_temp >= max_temp:
                errors["base"] = "invalid_temperature_range"
            elif not min_temp <= default_temperature <= max_temp:
                errors[CONF_DEFAULT_TEMPERATURE] = "default_temperature_out_of_range"
            else:
                await self.async_set_unique_id(
                    user_input[CONF_INFRARED_ENTITY_ID]
                    or f"mqtt:{user_input[CONF_ZIGBEE2MQTT_TOPIC]}"
                )
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Optional(CONF_ZIGBEE2MQTT_TOPIC): str,
            vol.Optional(CONF_INFRARED_ENTITY_ID): selector.EntitySelector(
                selector.EntitySelectorConfig(domain="infrared")
            ),
            vol.Required(CONF_DEFAULT_TEMPERATURE, default=DEFAULT_TEMPERATURE): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=DEFAULT_MIN_TEMP,
                    max=DEFAULT_MAX_TEMP,
                    step=1,
                    mode=selector.NumberSelectorMode.BOX,
                )
            ),
            vol.Required(CONF_DEFAULT_FAN_MODE, default=DEFAULT_FAN_MODE): vol.In(FAN_MODES),
            vol.Required(CONF_DEFAULT_SWING_MODE, default=DEFAULT_SWING_MODE): vol.In(SWING_MODES),
            vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(int),
            vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(int),
            vol.Required(CONF_REPEATS, default=DEFAULT_REPEATS): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=5)
            ),
        }
        return self.async_show_form(step_id="user", data_schema=vol.Schema(schema_dict), errors=errors)

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: config_entries.ConfigEntry) -> config_entries.OptionsFlow:
        return AirconIrOptionsFlowHandler(config_entry)


try:
    _BaseOptionsFlow = config_entries.OptionsFlowWithConfigEntry  # type: ignore[attr-defined]
except AttributeError:
    _BaseOptionsFlow = config_entries.OptionsFlow  # type: ignore[assignment]


class AirconIrOptionsFlowHandler(_BaseOptionsFlow):  # type: ignore[misc]
    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}
        entry = self.config_entry if hasattr(self, "config_entry") else self._config_entry  # type: ignore[attr-defined]
        current: dict[str, Any] = {**entry.data, **entry.options}

        if user_input is not None:
            min_temp = user_input[CONF_MIN_TEMP]
            max_temp = user_input[CONF_MAX_TEMP]
            default_temperature = user_input[CONF_DEFAULT_TEMPERATURE]
            # A cleared optional selector is omitted by Home Assistant.
            # Store an explicit empty value so options override entry.data.
            user_input[CONF_INFRARED_ENTITY_ID] = (
                user_input.get(CONF_INFRARED_ENTITY_ID) or ""
            )
            user_input[CONF_ZIGBEE2MQTT_TOPIC] = (
                user_input.get(CONF_ZIGBEE2MQTT_TOPIC) or ""
            ).strip()
            current.update(user_input)
            if not (
                user_input[CONF_INFRARED_ENTITY_ID]
                or user_input[CONF_ZIGBEE2MQTT_TOPIC]
            ):
                errors["base"] = "transmitter_required"
            elif min_temp >= max_temp:
                errors["base"] = "invalid_temperature_range"
            elif not min_temp <= default_temperature <= max_temp:
                errors[CONF_DEFAULT_TEMPERATURE] = "default_temperature_out_of_range"
            else:
                return self.async_create_entry(title="", data=user_input)

        # Suggested values prepopulate the form without making an optional
        # field reappear after the user has cleared it.
        emitter_value = current.get(CONF_INFRARED_ENTITY_ID) or ""
        mqtt_value = current.get(CONF_ZIGBEE2MQTT_TOPIC) or ""
        emitter_marker = (
            vol.Optional(
                CONF_INFRARED_ENTITY_ID,
                description={"suggested_value": emitter_value},
            )
            if emitter_value
            else vol.Optional(CONF_INFRARED_ENTITY_ID)
        )
        mqtt_marker = (
            vol.Optional(
                CONF_ZIGBEE2MQTT_TOPIC,
                description={"suggested_value": mqtt_value},
            )
            if mqtt_value
            else vol.Optional(CONF_ZIGBEE2MQTT_TOPIC)
        )

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=current.get(CONF_NAME, DEFAULT_NAME)): str,
            mqtt_marker: str,
            emitter_marker: selector.EntitySelector(
                selector.EntitySelectorConfig(domain="infrared")
            ),
            vol.Required(CONF_DEFAULT_TEMPERATURE, default=current.get(CONF_DEFAULT_TEMPERATURE, DEFAULT_TEMPERATURE)): selector.NumberSelector(
                selector.NumberSelectorConfig(
                    min=DEFAULT_MIN_TEMP, max=DEFAULT_MAX_TEMP, step=1, mode=selector.NumberSelectorMode.BOX
                )
            ),
            vol.Required(CONF_DEFAULT_FAN_MODE, default=current.get(CONF_DEFAULT_FAN_MODE, DEFAULT_FAN_MODE)): vol.In(FAN_MODES),
            vol.Required(CONF_DEFAULT_SWING_MODE, default=current.get(CONF_DEFAULT_SWING_MODE, DEFAULT_SWING_MODE)): vol.In(SWING_MODES),
            vol.Required(CONF_MIN_TEMP, default=current.get(CONF_MIN_TEMP, DEFAULT_MIN_TEMP)): vol.Coerce(int),
            vol.Required(CONF_MAX_TEMP, default=current.get(CONF_MAX_TEMP, DEFAULT_MAX_TEMP)): vol.Coerce(int),
            vol.Required(CONF_REPEATS, default=current.get(CONF_REPEATS, DEFAULT_REPEATS)): vol.All(
                vol.Coerce(int), vol.Range(min=1, max=5)
            ),
        }
        return self.async_show_form(step_id="init", data_schema=vol.Schema(schema_dict), errors=errors)
