"""Baut blueprints/script/stimmspende.yaml aus saetze.txt (Satzpool direkt im Blueprint, damit nichts nachgeladen werden muss)."""
import json
import os

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
pool = [s.strip() for s in open(os.path.join(HIER, "saetze.txt")) if s.strip()]
pool_yaml = "\n".join(f"    - {json.dumps(s, ensure_ascii=False)}" for s in pool)

BP = f'''blueprint:
  name: "Stimmspende – Sprachaufnahmen für eine bessere deutsche Spracherkennung"
  description: >-
    Liest dir zufällige deutsche Sätze (Sprachbefehle, Fragen, kurze Antworten) über deinen
    Sprach-Satelliten vor. Du sprichst jeden Satz nach, ohne Weckwort. Es wird **nichts geschaltet**:
    Das Skript nutzt `assist_satellite.ask_question`, dabei läuft nur die Spracherkennung,
    kein Gesprächsagent, keine KI, keine Automationen.


    **Damit die Aufnahmen gespeichert werden**, muss vorher in der `configuration.yaml` stehen:

    ```

    assist_pipeline:
      debug_recording_dir: /share/stimmspende

    ```

    (danach Home Assistant neu starten). Anleitung, Datenschutz und Hochladen:
    https://github.com/Spionkiller01/ha-stimmspende
  domain: script
  author: Spionkiller01
  source_url: https://github.com/Spionkiller01/ha-stimmspende/blob/main/blueprints/script/stimmspende.yaml
  homeassistant:
    min_version: "2025.7.0"
  input:
    satellit:
      name: Sprach-Satellit
      description: >-
        Das Gerät, das vorliest und aufnimmt (Voice PE, ReSpeaker, ESPHome-Satellit, View Assist, …).
        Es muss „Gespräch starten" unterstützen und auf eine deutsche Assist-Pipeline eingestellt sein.
      selector:
        entity:
          filter:
            - domain: assist_satellite
    anzahl:
      name: Anzahl Sätze
      description: Wie viele Sätze vorgelesen werden. 20 dauern etwa 5 Minuten.
      default: 20
      selector:
        number:
          min: 5
          max: 60
          step: 1
          mode: slider
    okay_sagen:
      name: Nach jedem Satz „Okay" sagen
      description: Kurze Bestätigung, dass der Satz angekommen ist. Fest eingebaut, ohne KI.
      default: true
      selector:
        boolean: {{}}

mode: single
icon: mdi:microphone-message

variables:
  satellit: !input satellit
  anzahl: !input anzahl
  okay_sagen: !input okay_sagen
  pool:
{pool_yaml}
  auswahl: "{{{{ (pool | shuffle)[:anzahl | int] }}}}"
  hinweise:
    weg: "{{{{ (anzahl * 0.3) | round(0, 'floor') | int }}}}"
    gehen: "{{{{ (anzahl * 0.55) | round(0, 'floor') | int }}}}"
    weit: "{{{{ (anzahl * 0.8) | round(0, 'floor') | int }}}}"

sequence:
  - action: assist_satellite.announce
    target:
      entity_id: "{{{{ satellit }}}}"
    data:
      preannounce: false
      message: >-
        Danke fürs Mitmachen! Ich lese dir gleich {{{{ anzahl }}}} Sätze vor. Sprich jeden Satz nach
        dem Vorlesen ganz normal nach, so wie du sonst mit deinem Sprachassistenten redest.
        Ein Weckwort brauchst du nicht. Los geht's.
  - action: logbook.log
    data:
      name: Stimmspende
      message: "Start: {{{{ anzahl }}}} Sätze auf {{{{ satellit }}}}"
  - repeat:
      for_each: "{{{{ auswahl }}}}"
      sequence:
        - variables:
            nr: "{{{{ repeat.index }}}}"
            satz: "{{{{ repeat.item }}}}"
            antwort: {{}}
        - choose:
            - conditions: "{{{{ nr == hinweise.weg + 1 }}}}"
              sequence:
                - action: assist_satellite.announce
                  target: {{entity_id: "{{{{ satellit }}}}"}}
                  data: {{preannounce: false, message: "Dreh dich für die nächsten Sätze bitte vom Gerät weg."}}
            - conditions: "{{{{ nr == hinweise.gehen + 1 }}}}"
              sequence:
                - action: assist_satellite.announce
                  target: {{entity_id: "{{{{ satellit }}}}"}}
                  data: {{preannounce: false, message: "Geh jetzt ein paar Schritte durch den Raum, du darfst auch beim Sprechen laufen."}}
            - conditions: "{{{{ nr == hinweise.weit + 1 }}}}"
              sequence:
                - action: assist_satellite.announce
                  target: {{entity_id: "{{{{ satellit }}}}"}}
                  data: {{preannounce: false, message: "Jetzt bitte an die Stelle im Raum, die am weitesten vom Gerät weg ist."}}
        - action: assist_satellite.ask_question
          note: Liest den Satz vor und hört zu. Nur Spracherkennung, kein Gesprächsagent, nichts wird geschaltet.
          data:
            entity_id: "{{{{ satellit }}}}"
            question: "{{{{ satz }}}}"
            preannounce: false
          response_variable: antwort
          continue_on_error: true
        - if:
            - condition: template
              value_template: "{{{{ antwort is not defined or not antwort.sentence }}}}"
          then:
            - action: assist_satellite.ask_question
              data:
                entity_id: "{{{{ satellit }}}}"
                question: "Ich habe nichts gehört. Nochmal: {{{{ satz }}}}"
                preannounce: false
              response_variable: antwort
              continue_on_error: true
        - action: logbook.log
          data:
            name: Stimmspende
            message: "{{{{ nr }}}}/{{{{ anzahl }}}} | {{{{ satz }}}} | erkannt: {{{{ antwort.sentence if antwort is defined and antwort.sentence else '–' }}}}"
        - if:
            - condition: template
              value_template: "{{{{ okay_sagen }}}}"
          then:
            - action: assist_satellite.announce
              target: {{entity_id: "{{{{ satellit }}}}"}}
              data: {{preannounce: false, message: "Okay."}}
              continue_on_error: true
  - action: assist_satellite.announce
    target:
      entity_id: "{{{{ satellit }}}}"
    data:
      preannounce: false
      message: Fertig, vielen Dank! Die Anleitung zum Hochladen findest du in deinen Benachrichtigungen.
  - action: persistent_notification.create
    data:
      notification_id: stimmspende
      title: "Stimmspende fertig – {{{{ anzahl }}}} Sätze"
      message: >-
        Danke! So geht's weiter:


        1. Lade den Ordner **/share/stimmspende** herunter (z. B. über das Samba-Add-on oder
        Studio Code Server: Rechtsklick → Download) und packe ihn als ZIP.

        2. Öffne https://github.com/Spionkiller01/ha-stimmspende/issues/new?template=spende.yml
        und hänge die ZIP an. Kopiere die Satzliste unten mit hinein.

        3. Danach die zwei Zeilen `debug_recording_dir` wieder aus der configuration.yaml nehmen
        und den Ordner leeren, sonst werden alle weiteren Sprachbefehle mitgeschnitten.


        **Gesprochene Sätze** (Gerät {{{{ satellit }}}}, {{{{ now().strftime('%d.%m.%Y %H:%M') }}}}):

        {{% for s in auswahl %}}{{{{ loop.index }}}}. {{{{ s }}}}

        {{% endfor %}}
'''
os.makedirs(os.path.join(HIER, "blueprints", "script"), exist_ok=True)
open(os.path.join(HIER, "blueprints", "script", "stimmspende.yaml"), "w").write(BP)
print(len(pool), "Sätze im Pool")
