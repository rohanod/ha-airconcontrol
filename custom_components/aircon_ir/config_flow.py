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
    VERSION = 2

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        errors: dict[str, str] = {}

        if user_input is not None:
            min_temp = user_input[CONF_MIN_TEMP]
            max_temp = user_input[CONF_MAX_TEMP]
            default_temperature = user_input[CONF_DEFAULT_TEMPERATURE]
            if min_temp >= max_temp:
                errors["base"] = "invalid_temperature_range"
            elif not min_temp <= default_temperature <= max_temp:
                errors[CONF_DEFAULT_TEMPERATURE] = "default_temperature_out_of_range"
            else:
                await self.async_set_unique_id(user_input[CONF_INFRARED_ENTITY_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=user_input[CONF_NAME], data=user_input)

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
            vol.Required(CONF_INFRARED_ENTITY_ID): selector.EntitySelector(
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
        return AirconIrOptionsFlowHandler()


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
            if min_temp >= max_temp:
                errors["base"] = "invalid_temperature_range"
            elif not min_temp <= default_temperature <= max_temp:
                errors[CONF_DEFAULT_TEMPERATURE] = "default_temperature_out_of_range"
            else:
                new_data = {**entry.data, **user_input}
                self.hass.config_entries.async_update_entry(entry, data=new_data)
                return self.async_create_entry(title="", data={})

        schema_dict: dict[Any, Any] = {
            vol.Required(CONF_NAME, default=current.get(CONF_NAME, DEFAULT_NAME)): str,
            vol.Required(CONF_INFRARED_ENTITY_ID, default=current.get(CONF_INFRARED_ENTITY_ID)): selector.EntitySelector(
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
