"""Knopf „Stimmspende starten"."""

from __future__ import annotations

import asyncio

from homeassistant.components.button import ButtonEntity
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .sitzung import Sitzung


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry, add: AddEntitiesCallback) -> None:
    add([StartKnopf(entry)])


class StartKnopf(ButtonEntity):
    """Startet eine Lesesitzung; ein zweiter Druck während einer laufenden Sitzung wird ignoriert."""

    _attr_has_entity_name = True
    _attr_translation_key = "starten"
    _attr_icon = "mdi:microphone-message"

    def __init__(self, entry: ConfigEntry) -> None:
        self._entry = entry
        self._attr_unique_id = f"{entry.entry_id}_starten"
        self._aufgabe: asyncio.Task | None = None
        self._attr_device_info = {
            "identifiers": {(DOMAIN, entry.entry_id)},
            "name": entry.title,
            "entry_type": "service",
        }

    async def async_press(self) -> None:
        if self._aufgabe and not self._aufgabe.done():
            return
        sitzung = Sitzung(self.hass, {**self._entry.data, **self._entry.options})
        self._aufgabe = self._entry.async_create_background_task(self.hass, sitzung.ablauf(), "stimmspende_sitzung")
