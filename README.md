# Stimmspende – Sprachaufnahmen für eine bessere deutsche Spracherkennung

Lokale Spracherkennung (Whisper, Parakeet, Cohere Transcribe …) versteht deutsche Sprachbefehle
oft schlecht, sobald man **nicht direkt ins Mikrofon** spricht: Hall, Abstand, weggedreht,
Fernseher im Hintergrund. Die großen Anbieter trainieren genau auf solchen Aufnahmen – offen
verfügbar gibt es sie für Deutsch praktisch nicht.

Dieses Projekt sammelt sie: **echte Sprachbefehle, aufgenommen mit echten Home-Assistant-Satelliten
in echten Räumen**, und veröffentlicht sie als freien Datensatz (CC0). Daraus soll ein
nachtrainiertes, frei verfügbares Modell für deutschsprachige Home-Assistant-Nutzer entstehen.

Ein erster Versuch mit eigenen Aufnahmen (ein Sprecher, ca. 230 Sätze) hat die Fehlerquote von
Cohere Transcribe auf Raum-Aufnahmen von **14,8 % auf 7,2 %** gesenkt. Nahbesprochene Fremddaten
(Speech-MASSIVE) brachten dagegen nichts – es braucht Aufnahmen aus dem Raum.

## So machst du mit (ca. 10 Minuten)

### Voraussetzungen
- Home Assistant **2025.7 oder neuer**
- Ein Sprach-Satellit mit Mikrofon (Home Assistant Voice PE, ReSpeaker, ESPHome-Satellit,
  View Assist, Wyoming-Satellit …), der „Gespräch starten" unterstützt
- Eine Assist-Pipeline auf **Deutsch** mit beliebiger Spracherkennung
- Ein GitHub-Konto zum Hochladen

### 1. Aufnahmen einschalten
In die `configuration.yaml` (z. B. mit dem File-Editor-Add-on):

```yaml
assist_pipeline:
  debug_recording_dir: /share/stimmspende
```

Home Assistant neu starten. Ab jetzt speichert HA jede Spracheingabe als WAV-Datei in diesem Ordner.
(Home Assistant OS/Supervised: `/share/…` wie oben. Container- oder Core-Installation: einen Pfad im
Config-Ordner nehmen, z. B. `/config/stimmspende`.)

### 2. Blueprint importieren

[![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FSpionkiller01%2Fha-stimmspende%2Fblob%2Fmain%2Fblueprints%2Fscript%2Fstimmspende.yaml)

Dann **Einstellungen → Automationen & Szenen → Blueprints → Stimmspende → Skript erstellen**,
deinen Satelliten auswählen, speichern.

### 3. Aufnehmen
Skript starten. Das Gerät liest dir 20 zufällige Sätze vor, du sprichst jeden nach – **ohne
Weckwort**. Es wird dabei **nichts geschaltet**: Das Skript nutzt `assist_satellite.ask_question`,
dabei läuft nur die Spracherkennung, kein Gesprächsagent, keine KI, keine Automationen.

**Bitte so natürlich wie möglich** – genau die schwierigen Fälle sind wertvoll:
- Sprich so, wie du sonst mit deinem Sprachassistenten redest. Nicht extra deutlich.
- Das Skript sagt dir zwischendurch: wegdrehen, durch den Raum gehen, an die entfernteste Stelle.
- Normale Hintergrundgeräusche (Spülmaschine, leise Musik) sind ausdrücklich erwünscht.
- **Andere Personen sollten nicht zu verstehen sein** (deren Stimmen dürfen ohne Einwilligung
  nicht veröffentlicht werden). Fernseher/Radio im Hintergrund ist in Ordnung.
- Versprochen? Einfach weitermachen, das wird beim Auswerten aussortiert.

### 4. Hochladen
1. Den Ordner `/share/stimmspende` herunterladen (Samba-Add-on, oder Studio Code Server:
   Rechtsklick → Download) und als ZIP packen.
2. **[Neue Spende anlegen](https://github.com/Spionkiller01/ha-stimmspende/issues/new?template=spende.yml)**,
   Formular ausfüllen, ZIP anhängen, Einwilligung bestätigen.
3. **Aufräumen:** die zwei Zeilen wieder aus der `configuration.yaml` nehmen, neu starten und den
   Ordner leeren – sonst werden alle weiteren Sprachbefehle weiter mitgeschnitten.

Mehrere Runden, mehrere Räume oder mehrere Geräte sind herzlich willkommen – jeweils als eigene Spende.

## Datenschutz und Einwilligung

- Deine Stimme ist ein personenbezogenes Datum. Mit dem Hochladen **willigst du ein**, dass deine
  Aufnahmen **öffentlich und dauerhaft** unter **CC0 1.0** (gemeinfrei) veröffentlicht werden:
  Jeder darf sie für jeden Zweck nutzen, auch kommerziell, auch zum Trainieren von KI-Modellen.
- **Issue-Anhänge auf GitHub sind sofort öffentlich**, schon bevor sie geprüft werden.
- Lade nur Aufnahmen **deiner eigenen Stimme** hoch, du musst **mindestens 18 Jahre** alt sein.
- Prüfe vor dem Hochladen, dass der Ordner nur die Lesesitzung enthält (keine anderen
  Sprachbefehle, keine anderen Personen).
- Es werden **keine Namen, Konten oder Geräte-IDs** in den Datensatz übernommen, nur die Audios,
  der Satztext und freiwillige Angaben aus dem Formular (Gerät, Raumgröße, Abstand).
- Widerruf: Ein Issue mit der Nummer deiner Spende genügt, dann werden die Aufnahmen aus dem
  Datensatz entfernt. Bereits heruntergeladene Kopien Dritter lassen sich nicht zurückholen.
- Das ist ein privates Hobbyprojekt ohne Gewinnabsicht, ohne Gewähr.

## Lizenz

- **Aufnahmen und Satzliste:** [CC0 1.0](LICENSE-DATEN) – gemeinfrei
- **Blueprint und Werkzeuge:** [MIT](LICENSE)

## Was mit den Daten passiert

Spenden werden geprüft (Satz passt zur Aufnahme, nur eine Stimme, keine privaten Inhalte),
in den Datensatz übernommen und regelmäßig gesammelt veröffentlicht. Damit wird ein freies
deutsches Spracherkennungsmodell nachtrainiert und ebenfalls veröffentlicht, samt Messwerten
vorher/nachher.

## Technische Details

- `blueprints/script/stimmspende.yaml` – das Skript-Blueprint (Satzpool von ~290 Sätzen ist
  eingebettet, je Durchlauf zufällige Auswahl)
- `saetze.txt` – der Satzpool
- `werkzeuge/` – Auswertung: Aufnahmen über den Inhalt den Sätzen zuordnen (nicht über
  Zeitstempel), Blueprint aus der Satzliste bauen
