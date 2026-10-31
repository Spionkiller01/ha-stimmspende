# Stimmspende – Sprachaufnahmen für eine bessere deutsche Spracherkennung

Lokale Spracherkennung (Whisper, Parakeet, Cohere Transcribe …) versteht deutsche Sprachbefehle
oft schlecht, sobald man **nicht direkt ins Mikrofon** spricht: Hall, Abstand, weggedreht,
Fernseher im Hintergrund. Die großen Anbieter trainieren genau auf solchen Aufnahmen – offen
verfügbar gibt es sie für Deutsch praktisch nicht.

Dieses Projekt sammelt sie: **echte Sprachbefehle, aufgenommen mit echten Home-Assistant-Satelliten
in echten Räumen**, und veröffentlicht sie als freien Datensatz (CC0). Daraus soll ein
nachtrainiertes, frei verfügbares Modell für deutschsprachige Home-Assistant-Nutzer entstehen.

Ein erster Versuch mit eigenen Aufnahmen (ein Sprecher, ca. 230 Sätze) hat die Fehlerquote von
Cohere Transcribe auf Raum-Aufnahmen von **14,8 % auf 7,2 %** gesenkt. Wichtig: Das ist auf
*derselben* Stimme gemessen, mit der trainiert wurde – es zeigt, wie gut die Anpassung an eine
Person klappt, nicht, wie gut ein allgemeines Modell für andere wird. Genau dafür braucht es
viele Sprecher. Nahbesprochene Fremddaten
(Speech-MASSIVE) brachten dagegen nichts – es braucht Aufnahmen aus dem Raum.

## So machst du mit (ca. 10 Minuten)

### Voraussetzungen
- Home Assistant **2025.7 oder neuer** und [HACS](https://hacs.xyz)
- Ein Sprach-Satellit mit Mikrofon (Home Assistant Voice PE, ReSpeaker, ESPHome-Satellit,
  View Assist, Wyoming-Satellit …), der „Gespräch starten" unterstützt
- Eine Assist-Pipeline auf **Deutsch** mit beliebiger Spracherkennung

### 1. Installieren
[![In HACS öffnen](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=Spionkiller01&repository=ha-stimmspende&category=integration)

Oder von Hand: HACS → ⋮ → **Benutzerdefinierte Repositories** →
`https://github.com/Spionkiller01/ha-stimmspende`, Typ **Integration** → „Stimmspende" herunterladen.
Danach Home Assistant **einmal neu starten**.

### 2. Einrichten
[![Integration hinzufügen](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=stimmspende)

Satelliten auswählen, die drei Einwilligungen bestätigen, freiwillig Gerät, Raum, Raumgröße,
Raumklang, Abstand und Dialekt angeben. Sprechen mehrere Personen im Haushalt, trägt jede bei „Wer
spricht?" ihr Kürzel ein (Optionen der Integration) – das Kürzel bleibt lokal, gesendet wird nur
eine anonyme Kennung (siehe unten).

### 3. Aufnehmen
Beim Gerät „Stimmspende" auf **Stimmspende starten** drücken. Dein Satellit liest dir 20 zufällige
Sätze vor, du sprichst jeden nach – **ohne Weckwort**. Nach jedem Satz sagt er „Okay".
Am Ende werden die Aufnahmen **automatisch hochgeladen**, du bekommst eine Benachrichtigung. Fertig.

Es wird dabei **nichts geschaltet**: Vorgelesen und zugehört wird über
`assist_satellite.ask_question`, dabei läuft nur die Spracherkennung, kein Gesprächsagent, keine KI,
keine Automationen. Aufgenommen wird **nur während der Sitzung**; danach ist alles wie vorher.

**Bitte so natürlich wie möglich** – genau die schwierigen Fälle sind wertvoll:
- Sprich so, wie du sonst mit deinem Sprachassistenten redest. Nicht extra deutlich.
- Das Gerät sagt dir zwischendurch: wegdrehen, durch den Raum gehen, an die entfernteste Stelle.
- Normale Hintergrundgeräusche (Spülmaschine, leise Musik) sind ausdrücklich erwünscht.
- **Andere Personen sollten nicht zu verstehen sein** (deren Stimmen dürfen ohne Einwilligung
  nicht veröffentlicht werden). Fernseher/Radio im Hintergrund ist in Ordnung.
- Versprochen? Einfach weitermachen, das wird beim Auswerten aussortiert.

Mehrere Runden, mehrere Räume oder mehrere Geräte sind herzlich willkommen – einfach nochmal drücken
bzw. die Integration für ein weiteres Gerät hinzufügen.

<details>
<summary>Ohne HACS: Weg mit Blueprint (mehr Handarbeit)</summary>

1. In die `configuration.yaml` eintragen und HA neu starten:
   ```yaml
   assist_pipeline:
     debug_recording_dir: /share/stimmspende
   ```
   (Container-/Core-Installation: z. B. `/config/stimmspende`)
2. [![Blueprint importieren](https://my.home-assistant.io/badges/blueprint_import.svg)](https://my.home-assistant.io/redirect/blueprint_import/?blueprint_url=https%3A%2F%2Fgithub.com%2FSpionkiller01%2Fha-stimmspende%2Fblob%2Fmain%2Fblueprints%2Fscript%2Fstimmspende.yaml)
   → Skript erstellen, Satelliten wählen, starten.
3. Ordner `/share/stimmspende` herunterladen (Samba oder Studio Code Server), als ZIP über
   [das Spendenformular](https://github.com/Spionkiller01/ha-stimmspende/issues/new?template=spende.yml)
   hochladen (GitHub-Konto nötig, **Anhänge sind dort sofort öffentlich**), Satzliste aus der
   Benachrichtigung mit hineinkopieren.
4. Die Zeilen wieder aus der `configuration.yaml` nehmen, neu starten, Ordner leeren.
</details>

## Datenschutz und Einwilligung

- Deine Stimme ist ein personenbezogenes Datum. Mit dem Hochladen **willigst du ein**, dass deine
  Aufnahmen **öffentlich und dauerhaft** unter **CC0 1.0** (gemeinfrei) veröffentlicht werden:
  Jeder darf sie für jeden Zweck nutzen, auch kommerziell, auch zum Trainieren von KI-Modellen.
- **Weg der Daten (Integration):** Die ZIP geht verschlüsselt an einen kleinen Empfangsdienst bei
  Cloudflare (`stimmspende.spionkiller01.workers.dev`, Quellcode im Ordner `worker/`) und liegt dort
  **nicht öffentlich**, bis sie geprüft ist. IP-Adressen werden nicht gespeichert (nur ein gekürzter
  Prüfwert gegen Spam, der nach einer Stunde verfällt).
- **Weg der Daten (Blueprint/GitHub):** Issue-Anhänge sind **sofort öffentlich**, schon vor der Prüfung.
- Lade nur Aufnahmen **deiner eigenen Stimme** hoch, du musst **mindestens 18 Jahre** alt sein.
- Hochgeladen werden nur die Aufnahmen der Lesesitzung vom gewählten Gerät, keine anderen
  Sprachbefehle. Beim Blueprint-Weg bitte selbst prüfen, dass der Ordner nichts anderes enthält.
- Es werden **keine Namen, Konten oder Geräte-IDs** in den Datensatz übernommen, nur die Audios,
  der Satztext und freiwillige Angaben aus dem Formular (Gerät, Raumgröße, Abstand).
- Widerruf: Ein Issue mit der Spenden-Nummer aus deiner Benachrichtigung genügt, dann werden die Aufnahmen aus dem
  Datensatz entfernt. Bereits heruntergeladene Kopien Dritter lassen sich nicht zurückholen.
- Das ist ein privates Hobbyprojekt ohne Gewinnabsicht, ohne Gewähr.

## Lizenz

- **Aufnahmen und Satzliste:** [CC0 1.0](LICENSE-DATEN) – gemeinfrei
- **Blueprint und Werkzeuge:** [MIT](LICENSE)

## Was pro Aufnahme gespeichert wird

- der vorgelesene Satz und was eure eigene Spracherkennung daraus gemacht hat
- die **Phase** der Aufnahme: `zugewandt`, `abgewandt`, `gehend` oder `weit` (das Skript sagt die
  Wechsel selbst an), damit sich getrennt messen lässt, ob ein Modell z. B. nur bei Fernfeld oder
  nur in halligen Räumen besser wird
- pro Spende: Gerätetyp, Raum, Raumgröße, Raumklang, Abstand, Hintergrund, freiwillig Dialekt
- eine **anonyme Sprecher-Kennung**: ein Hash aus der zufälligen Installations-ID eures Home
  Assistant und dem lokalen Kürzel. Daraus lässt sich niemand ermitteln, aber mehrere Runden
  derselben Person gehören zusammen. Das ist nötig, damit beim Auswerten **keine Stimme gleichzeitig
  im Training und im Test** landet – sonst misst man nur, wie gut das Modell bekannte Stimmen kann.

## Was mit den Daten passiert

Spenden werden geprüft (Satz passt zur Aufnahme, nur eine Stimme, keine privaten Inhalte),
in den Datensatz übernommen und regelmäßig gesammelt veröffentlicht. Für Messungen wird nach
Sprechern getrennt: Testsprecher kommen nie ins Training. Damit wird ein freies
deutsches Spracherkennungsmodell nachtrainiert und ebenfalls veröffentlicht, samt Messwerten
vorher/nachher.

## Technische Details

- `custom_components/stimmspende/` – die Integration (Aufnahme nur während der Sitzung, Zuordnung
  Aufnahme ↔ Satz direkt, ZIP + Upload). Sie schaltet dafür kurzzeitig HAs eingebaute
  Debug-Aufnahme (`debug_recording_dir`) auf einen eigenen Ordner und stellt danach den alten Zustand
  wieder her. Das ist kein offizielles API; sollte ein HA-Update das ändern, meldet die Integration
  einen Fehler statt still nichts aufzunehmen.
- `worker/` – Empfangsdienst (Cloudflare Worker): prüft Aufbau und Einwilligung, begrenzt die Menge
- `blueprints/script/stimmspende.yaml` – das Skript-Blueprint für den Weg ohne HACS (Satzpool von ~390 Sätzen ist
  eingebettet, je Durchlauf zufällige Auswahl)
- `saetze.txt` – der Satzpool
- `werkzeuge/` – Auswertung: Aufnahmen über den Inhalt den Sätzen zuordnen (nicht über
  Zeitstempel), Blueprint aus der Satzliste bauen
