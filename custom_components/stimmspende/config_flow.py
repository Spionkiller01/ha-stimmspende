"""Einrichtung: Gerät wählen, Einwilligung bestätigen, freiwillige Angaben."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector

from .const import (
    ABSTAENDE,
    CONF_ABSTAND,
    CONF_ANZAHL,
    CONF_CC0,
    CONF_DIALEKT,
    CONF_EIGENE_STIMME,
    CONF_GERAET,
    CONF_HINTERGRUND,
    CONF_OKAY,
    CONF_RAUM,
    CONF_RAUMGROESSE,
    CONF_RAUMKLANG,
    CONF_SPRECHER,
    CONF_SATELLIT,
    CONF_VOLLJAEHRIG,
    DOMAIN,
    HINTERGRUENDE,
    RAEUME,
    RAUMGROESSEN,
    RAUMKLAENGE,
)


def _schema(werte: dict[str, Any], mit_einwilligung: bool) -> vol.Schema:
    felder: dict[Any, Any] = {
        vol.Required(CONF_SATELLIT, default=werte.get(CONF_SATELLIT, vol.UNDEFINED)): selector.EntitySelector(
            selector.EntitySelectorConfig(domain="assist_satellite")
        ),
        vol.Required(CONF_ANZAHL, default=werte.get(CONF_ANZAHL, 20)): selector.NumberSelector(
            selector.NumberSelectorConfig(min=5, max=60, step=1, mode=selector.NumberSelectorMode.SLIDER)
        ),
        vol.Required(CONF_OKAY, default=werte.get(CONF_OKAY, True)): selector.BooleanSelector(),
        vol.Optional(CONF_GERAET, default=werte.get(CONF_GERAET, "")): selector.TextSelector(),
        vol.Optional(CONF_RAUM, default=werte.get(CONF_RAUM, "wohnzimmer")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=RAEUME, translation_key="raum")
        ),
        vol.Optional(CONF_RAUMGROESSE, default=werte.get(CONF_RAUMGROESSE, "mittel")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=RAUMGROESSEN, translation_key="raumgroesse")
        ),
        vol.Optional(CONF_RAUMKLANG, default=werte.get(CONF_RAUMKLANG, "normal")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=RAUMKLAENGE, translation_key="raumklang")
        ),
        vol.Optional(CONF_ABSTAND, default=werte.get(CONF_ABSTAND, "gemischt")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=ABSTAENDE, translation_key="abstand")
        ),
        vol.Optional(CONF_HINTERGRUND, default=werte.get(CONF_HINTERGRUND, "gemischt")): selector.SelectSelector(
            selector.SelectSelectorConfig(options=HINTERGRUENDE, translation_key="hintergrund")
        ),
        vol.Optional(CONF_DIALEKT, default=werte.get(CONF_DIALEKT, "")): selector.TextSelector(),
        vol.Optional(CONF_SPRECHER, default=werte.get(CONF_SPRECHER, "")): selector.TextSelector(),
    }
    if mit_einwilligung:
        for k in (CONF_EIGENE_STIMME, CONF_VOLLJAEHRIG, CONF_CC0):
            felder[vol.Required(k, default=False)] = selector.BooleanSelector()
    return vol.Schema(felder)


class StimmspendeConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung der Stimmspende."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        fehler: dict[str, str] = {}
        if user_input is not None:
            if not all(user_input.get(k) for k in (CONF_EIGENE_STIMME, CONF_VOLLJAEHRIG, CONF_CC0)):
                fehler["base"] = "einwilligung"
            else:
                await self.async_set_unique_id(user_input[CONF_SATELLIT])
                self._abort_if_unique_id_configured()
                name = self.hass.states.get(user_input[CONF_SATELLIT])
                titel = name.name if name else user_input[CONF_SATELLIT]
                return self.async_create_entry(title=f"Stimmspende {titel}", data=user_input)
        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input or {}, mit_einwilligung=True), errors=fehler
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        return StimmspendeOptionsFlow()


class StimmspendeOptionsFlow(OptionsFlow):
    """Angaben später ändern (Einwilligung bleibt aus der Einrichtung bestehen)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data=user_input)
        werte = {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(step_id="init", data_schema=_schema(werte, mit_einwilligung=False))
