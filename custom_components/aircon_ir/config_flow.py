"""Config flow for Aircon IR."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.const import CONF_NAME
from homeassistant.helpers import selector

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
    DEFAULT_NAME,
    DEFAULT_REPEATS,
    DEFAULT_TEMPERATURE,
    DOMAIN,
    FAN_MODES,
)


class AirconIrConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle an Aircon IR config flow."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> config_entries.ConfigFlowResult:
        """Handle the initial step."""
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
                await self.async_set_unique_id(user_input[CONF_REMOTE_ENTITY_ID])
                self._abort_if_unique_id_configured()
                return self.async_create_entry(
                    title=user_input[CONF_NAME],
                    data=user_input,
                )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default=DEFAULT_NAME): str,
                    vol.Required(CONF_REMOTE_ENTITY_ID): selector.EntitySelector(
                        selector.EntitySelectorConfig(domain="remote")
                    ),
                    vol.Required(
                        CONF_DEFAULT_TEMPERATURE, default=DEFAULT_TEMPERATURE
                    ): selector.NumberSelector(
                        selector.NumberSelectorConfig(
                            min=DEFAULT_MIN_TEMP,
                            max=DEFAULT_MAX_TEMP,
                            step=1,
                            mode=selector.NumberSelectorMode.BOX,
                        )
                    ),
                    vol.Required(CONF_DEFAULT_FAN_MODE, default=DEFAULT_FAN_MODE): vol.In(
                        FAN_MODES
                    ),
                    vol.Required(CONF_MIN_TEMP, default=DEFAULT_MIN_TEMP): vol.Coerce(
                        int
                    ),
                    vol.Required(CONF_MAX_TEMP, default=DEFAULT_MAX_TEMP): vol.Coerce(
                        int
                    ),
                    vol.Required(CONF_REPEATS, default=DEFAULT_REPEATS): vol.All(
                        vol.Coerce(int), vol.Range(min=1, max=5)
                    ),
                }
            ),
            errors=errors,
        )
