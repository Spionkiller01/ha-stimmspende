"""Spenden aus den GitHub-Issues holen und den Sätzen zuordnen.

    python3 werkzeuge/spenden_holen.py [--stt http://localhost:9296/stt]

Für jedes offene Issue mit Label „spende": ZIP-Anhänge laden, WAVs auspacken, jede Aufnahme
einzeln erkennen lassen und über den Inhalt dem ähnlichsten Satz aus saetze.txt zuordnen
(nie über Zeitstempel – die Uhren von HA und Server laufen auseinander). Ergebnis je Spende in
spenden/<issue>/zuordnung.json, unsichere Fälle (Ähnlichkeit < 0,6) zum Gegenhören markiert.
Braucht `gh` (angemeldet) und einen STT-Dienst mit der Schnittstelle POST rohes PCM -> {"text"}.
"""
import argparse
import difflib
import io
import json
import os
import re
import subprocess
import urllib.request
import zipfile

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = "Spionkiller01/ha-stimmspende"


def norm(s: str) -> str:
    return " ".join(re.findall(r"[\wäöüß]+", s.lower()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stt", default="http://localhost:9296/stt")
    args = ap.parse_args()
    pool = [s.strip() for s in open(os.path.join(HIER, "saetze.txt")) if s.strip()]
    issues = json.loads(subprocess.check_output(
        ["gh", "issue", "list", "-R", REPO, "--label", "spende", "--state", "open", "--json", "number,body"]))
    for iss in issues:
        ziel = os.path.join(HIER, "spenden", str(iss["number"]))
        if os.path.exists(os.path.join(ziel, "zuordnung.json")):
            continue
        links = re.findall(r"https://github\.com/user-attachments/files/\S+?\.zip", iss["body"])
        if not links:
            print(f"#{iss['number']}: kein ZIP gefunden")
            continue
        os.makedirs(ziel, exist_ok=True)
        wavs = []
        for url in links:
            daten = urllib.request.urlopen(url, timeout=60).read()
            with zipfile.ZipFile(io.BytesIO(daten)) as z:
                for name in sorted(z.namelist()):
                    if name.endswith(".wav"):
                        pfad = os.path.join(ziel, "wav", f"{len(wavs):03d}.wav")
                        os.makedirs(os.path.dirname(pfad), exist_ok=True)
                        open(pfad, "wb").write(z.read(name))
                        wavs.append((name, pfad))
        zuordnung = []
        for name, pfad in wavs:
            pcm = open(pfad, "rb").read()[44:]
            if len(pcm) < 3200:
                continue  # leer oder kürzer als 0,1 s
            text = json.load(urllib.request.urlopen(urllib.request.Request(args.stt, pcm), timeout=30))["text"]
            satz, aehnl = max(((s, difflib.SequenceMatcher(None, norm(s), norm(text)).ratio()) for s in pool),
                              key=lambda x: x[1])
            zuordnung.append(dict(datei=os.path.relpath(pfad, ziel), original=name, erkannt=text,
                                  satz=satz, aehnlichkeit=round(aehnl, 2), pruefen=aehnl < 0.6))
        json.dump(zuordnung, open(os.path.join(ziel, "zuordnung.json"), "w"), ensure_ascii=False, indent=1)
        unsicher = sum(z["pruefen"] for z in zuordnung)
        print(f"#{iss['number']}: {len(zuordnung)} Aufnahmen, {unsicher} zum Gegenhören")


if __name__ == "__main__":
    main()
