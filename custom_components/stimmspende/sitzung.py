"""Eine Lesesitzung: Sätze vorlesen, Aufnahmen einsammeln, verpacken, hochladen.

Aufnahme ohne YAML: Home Assistant liest `debug_recording_dir` bei jedem Pipeline-Lauf neu aus
hass.data[DATA_CONFIG] (assist_pipeline/run.py, _start_debug_recording_thread). Die Sitzung setzt
den Wert nur für ihre Dauer auf einen eigenen Ordner und stellt danach den alten Zustand wieder
her. Das ist kein offizielles API – fehlt der Eintrag, bricht die Sitzung mit einer Meldung ab.

Vorlesen und Zuhören über assist_satellite.ask_question: Dabei läuft nur die Spracherkennung,
kein Gesprächsagent und keine Satz-Trigger, es wird also nichts geschaltet.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timezone
import io
import json
import logging
from pathlib import Path
import random
import shutil
import uuid
import zipfile

import aiohttp

from homeassistant.components import persistent_notification
from homeassistant.const import __version__ as HA_VERSION
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    CONF_ABSTAND,
    CONF_ANZAHL,
    CONF_CC0,
    CONF_DIALEKT,
    CONF_EIGENE_STIMME,
    CONF_GERAET,
    CONF_HINTERGRUND,
    CONF_OKAY,
    CONF_RAUM,
    CONF_SATELLIT,
    CONF_VOLLJAEHRIG,
    DOMAIN,
    UPLOAD_URL,
    VERSION,
)

_LOGGER = logging.getLogger(__name__)
HINWEISE = {
    0.3: "Dreh dich für die nächsten Sätze bitte vom Gerät weg.",
    0.55: "Geh jetzt ein paar Schritte durch den Raum, du darfst auch beim Sprechen laufen.",
    0.8: "Jetzt bitte an die Stelle im Raum, die am weitesten vom Gerät weg ist.",
}
LEER = 1600  # Bytes: unter 0,05 s Audio gilt als keine Aufnahme


class Sitzung:
    def __init__(self, hass: HomeAssistant, cfg: dict) -> None:
        self.hass = hass
        self.cfg = cfg
        self.sat: str = cfg[CONF_SATELLIT]
        self.id = f"{datetime.now(timezone.utc):%Y%m%d-%H%M%S}-{uuid.uuid4().hex[:6]}"
        self.ordner = Path(hass.config.path(DOMAIN, self.id))

    # --- kleine Helfer -------------------------------------------------------------------
    def _melden(self, titel: str, text: str) -> None:
        persistent_notification.async_create(self.hass, text, title=titel, notification_id=f"{DOMAIN}_{self.id}")

    async def _sagen(self, text: str) -> None:
        await self.hass.services.async_call(
            "assist_satellite", "announce", {"message": text, "preannounce": False},
            target={"entity_id": self.sat}, blocking=True,
        )

    async def _fragen(self, text: str) -> str:
        antwort = await asyncio.wait_for(
            self.hass.services.async_call(
                "assist_satellite", "ask_question",
                {"entity_id": self.sat, "question": text, "preannounce": False},
                blocking=True, return_response=True,
            ),
            timeout=90,
        )
        if isinstance(antwort, dict) and self.sat in antwort:  # falls als Entitäts-Dienst registriert
            antwort = antwort[self.sat]
        return (antwort or {}).get("sentence") or ""

    def _aufnahmen(self) -> set[Path]:
        return set(self.ordner.glob("aufnahme/**/*.wav")) if self.ordner.exists() else set()

    async def _neue_aufnahme(self, vorher: set[Path]) -> Path | None:
        # Der Aufnahme-Thread schreibt bis zum Ende des Laufs; kurz warten, bis die Datei geschlossen ist.
        for _ in range(20):
            neu = [p for p in self._aufnahmen() - vorher if self._geraet_pfad(p)]
            if neu:
                await asyncio.sleep(0.6)
                beste = max(neu, key=lambda p: p.stat().st_size)
                return beste if beste.stat().st_size > 44 + LEER else None
            await asyncio.sleep(0.25)
        return None

    def _geraet_pfad(self, p: Path) -> bool:
        """Nur Aufnahmen des gewählten Satelliten (andere Geräte im Haus können parallel aufnehmen)."""
        return self.device_id is None or self.device_id in p.parts

    # --- Ablauf --------------------------------------------------------------------------
    async def ablauf(self) -> None:
        try:
            from homeassistant.components.assist_pipeline.const import (  # noqa: PLC0415
                CONF_DEBUG_RECORDING_DIR,
                DATA_CONFIG,
            )
        except ImportError:
            self._melden("Stimmspende", "Diese Home-Assistant-Version wird nicht unterstützt (Aufnahme nicht möglich).")
            return
        pipeline_cfg = self.hass.data.get(DATA_CONFIG)
        if not isinstance(pipeline_cfg, dict):
            self._melden("Stimmspende", "Aufnahme nicht möglich: assist_pipeline ist nicht geladen.")
            return

        eintrag = er.async_get(self.hass).async_get(self.sat)
        self.device_id = eintrag.device_id if eintrag else None
        plattform = eintrag.platform if eintrag else "unbekannt"
        pool = await self.hass.async_add_executor_job(
            lambda: [s.strip() for s in (Path(__file__).parent / "saetze.txt").read_text("utf-8").splitlines() if s.strip()]
        )
        anzahl = int(self.cfg.get(CONF_ANZAHL, 20))
        auswahl = random.sample(pool, min(anzahl, len(pool)))
        hinweise = {int(anzahl * f): t for f, t in HINWEISE.items()}

        alt = pipeline_cfg.get(CONF_DEBUG_RECORDING_DIR, None)
        hatte_alt = CONF_DEBUG_RECORDING_DIR in pipeline_cfg
        await self.hass.async_add_executor_job(lambda: (self.ordner / "aufnahme").mkdir(parents=True, exist_ok=True))
        pipeline_cfg[CONF_DEBUG_RECORDING_DIR] = str(self.ordner / "aufnahme")
        saetze: list[dict] = []
        try:
            self._melden("Stimmspende läuft", f"{anzahl} Sätze auf {self.sat}. Sprich jeden Satz nach dem Vorlesen nach.")
            await self._sagen(
                f"Danke fürs Mitmachen! Ich lese dir gleich {anzahl} Sätze vor. Sprich jeden Satz nach dem "
                "Vorlesen ganz normal nach, so wie du sonst mit deinem Sprachassistenten redest. "
                "Ein Weckwort brauchst du nicht. Los geht's."
            )
            for i, satz in enumerate(auswahl):
                if i in hinweise and i > 0:
                    await self._sagen(hinweise[i])
                datei = None
                erkannt = ""
                for versuch, frage in enumerate((satz, f"Ich habe nichts gehört. Nochmal: {satz}")):
                    vorher = await self.hass.async_add_executor_job(self._aufnahmen)
                    try:
                        erkannt = await self._fragen(frage)
                    except Exception as err:  # noqa: BLE001
                        _LOGGER.warning("Satz %d: Frage fehlgeschlagen: %s", i + 1, err)
                    datei = await self._neue_aufnahme(vorher)
                    if datei is not None:
                        break
                if datei is not None:
                    name = f"{len(saetze) + 1:03d}.wav"
                    await self.hass.async_add_executor_job(shutil.copyfile, datei, self.ordner / name)
                    saetze.append({"datei": name, "satz": satz, "erkannt": erkannt, "versuch": versuch + 1})
                if self.cfg.get(CONF_OKAY, True):
                    await self._sagen("Okay.")
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Stimmspende abgebrochen")
        finally:
            if hatte_alt:
                pipeline_cfg[CONF_DEBUG_RECORDING_DIR] = alt
            else:
                pipeline_cfg.pop(CONF_DEBUG_RECORDING_DIR, None)

        if not saetze:
            self._melden("Stimmspende", "Es wurden keine Aufnahmen gespeichert. Unterstützt dein Gerät „Gespräch starten“?")
            await self.hass.async_add_executor_job(shutil.rmtree, self.ordner, True)
            return

        manifest = {
            "format": 1,
            "integration": VERSION,
            "homeassistant": HA_VERSION,
            "zeit": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "satellit_plattform": plattform,
            "geraet": self.cfg.get(CONF_GERAET, ""),
            "raum": self.cfg.get(CONF_RAUM),
            "abstand": self.cfg.get(CONF_ABSTAND),
            "hintergrund": self.cfg.get(CONF_HINTERGRUND),
            "dialekt": self.cfg.get(CONF_DIALEKT, ""),
            "einwilligung": {k: bool(self.cfg.get(k)) for k in (CONF_EIGENE_STIMME, CONF_VOLLJAEHRIG, CONF_CC0)},
            "saetze": saetze,
        }
        daten = await self.hass.async_add_executor_job(self._packen, manifest)
        await self._sagen("Fertig, vielen Dank! Ich lade die Aufnahmen jetzt hoch.")
        ok, info = await self._hochladen(daten)
        if ok:
            await self.hass.async_add_executor_job(shutil.rmtree, self.ordner, True)
            self._melden("Stimmspende hochgeladen – danke!",
                         f"{len(saetze)} Aufnahmen übertragen (Spende {info}). Du kannst jederzeit eine weitere Runde machen.")
        else:
            ziel = self.ordner.parent / f"{self.id}.zip"
            await self.hass.async_add_executor_job(ziel.write_bytes, daten)
            await self.hass.async_add_executor_job(shutil.rmtree, self.ordner, True)
            self._melden("Stimmspende: Hochladen fehlgeschlagen",
                         f"{info}\n\nDie Aufnahmen liegen als `{ziel}`. Du kannst die Datei auch über "
                         "https://github.com/Spionkiller01/ha-stimmspende/issues/new?template=spende.yml hochladen.")

    def _packen(self, manifest: dict) -> bytes:
        puffer = io.BytesIO()
        with zipfile.ZipFile(puffer, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("manifest.json", json.dumps(manifest, ensure_ascii=False, indent=1))
            for s in manifest["saetze"]:
                z.write(self.ordner / s["datei"], s["datei"])
        return puffer.getvalue()

    async def _hochladen(self, daten: bytes) -> tuple[bool, str]:
        try:
            async with async_get_clientsession(self.hass).post(
                UPLOAD_URL, data=daten, headers={"Content-Type": "application/zip"},
                timeout=aiohttp.ClientTimeout(total=120),
            ) as r:
                text = await r.text()
                if r.status == 200:
                    return True, json.loads(text).get("id", "?")
                return False, f"Server antwortet {r.status}: {text[:200]}"
        except Exception as err:  # noqa: BLE001
            return False, f"Keine Verbindung zum Server: {err}"
