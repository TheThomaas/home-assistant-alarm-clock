"""Config flow et options flow de l'intégration Réveil."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlow,
)
from homeassistant.const import CONF_NAME
from homeassistant.core import callback
from homeassistant.helpers.selector import (
    NumberSelector,
    NumberSelectorConfig,
    NumberSelectorMode,
    TextSelector,
    TimeSelector,
)
from homeassistant.util import slugify

from .const import (
    CONF_DEFAULT_TIME,
    CONF_LEAD_MINUTES,
    DEFAULT_LEAD_MINUTES,
    DEFAULT_TIME,
    DOMAIN,
)

_LEAD_SELECTOR = NumberSelector(
    NumberSelectorConfig(
        min=0,
        max=120,
        step=1,
        mode=NumberSelectorMode.BOX,
        unit_of_measurement="min",
    )
)


class ReveilConfigFlow(ConfigFlow, domain=DOMAIN):
    """Ajout d'un réveil (on peut en ajouter autant que voulu)."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ReveilOptionsFlow:
        return ReveilOptionsFlow()

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            name = user_input[CONF_NAME].strip() or "Réveil"
            await self.async_set_unique_id(slugify(name))
            self._abort_if_unique_id_configured()
            return self.async_create_entry(
                title=name,
                data={CONF_DEFAULT_TIME: user_input[CONF_DEFAULT_TIME]},
                options={CONF_LEAD_MINUTES: int(user_input[CONF_LEAD_MINUTES])},
            )

        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema(
                {
                    vol.Required(CONF_NAME, default="Réveil"): TextSelector(),
                    vol.Required(CONF_DEFAULT_TIME, default=DEFAULT_TIME): TimeSelector(),
                    vol.Required(
                        CONF_LEAD_MINUTES, default=DEFAULT_LEAD_MINUTES
                    ): _LEAD_SELECTOR,
                }
            ),
        )


class ReveilOptionsFlow(OptionsFlow):
    """Options d'un réveil : durée de la phase progressive."""

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(
                data={CONF_LEAD_MINUTES: int(user_input[CONF_LEAD_MINUTES])}
            )

        return self.async_show_form(
            step_id="init",
            data_schema=self.add_suggested_values_to_schema(
                vol.Schema({vol.Required(CONF_LEAD_MINUTES): _LEAD_SELECTOR}),
                self.config_entry.options,
            ),
        )
