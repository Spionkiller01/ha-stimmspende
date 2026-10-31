"""Neue Spenden aus dem Cloudflare-Speicher holen, auspacken und zum Gegenhören vorbereiten.

    python3 werkzeuge/spenden_holen.py [--stt http://localhost:9296/stt] [--behalten]

Zugangsdaten aus ~/.config/stimmspende.env (CLOUDFLARE_API_TOKEN, CLOUDFLARE_ACCOUNT_ID,
CLOUDFLARE_KV_ID). Jede Spende landet in spenden/<id>/ (WAVs + manifest.json); die Zuordnung
Aufnahme -> Satz steht schon im Manifest. Zusätzlich wird jede Aufnahme mit dem lokalen STT-Dienst
erkannt und mit dem Satz verglichen: pruefung.tsv listet alle, auffällige (Ähnlichkeit < 0,6)
zuerst. Nach erfolgreicher lokaler Sicherung wird die Spende aus dem Cloudflare-Speicher gelöscht
(außer mit --behalten).
"""
import argparse
import difflib
import io
import json
import os
import re
import urllib.parse
import urllib.request
import zipfile

HIER = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def env() -> dict:
    werte = {}
    for zeile in open(os.path.expanduser("~/.config/stimmspende.env")):
        if "=" in zeile:
            k, v = zeile.strip().split("=", 1)
            werte[k] = v
    return werte


def cf(e: dict, pfad: str, methode: str = "GET") -> bytes:
    url = f"https://api.cloudflare.com/client/v4/accounts/{e['CLOUDFLARE_ACCOUNT_ID']}/storage/kv/namespaces/{e['CLOUDFLARE_KV_ID']}{pfad}"
    req = urllib.request.Request(url, method=methode, headers={"Authorization": f"Bearer {e['CLOUDFLARE_API_TOKEN']}"})
    return urllib.request.urlopen(req, timeout=120).read()


def norm(s: str) -> str:
    return " ".join(re.findall(r"[\wäöüß]+", s.lower()))


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--stt", default="http://localhost:9296/stt")
    ap.add_argument("--behalten", action="store_true", help="Spenden nicht aus dem Cloudflare-Speicher löschen")
    args = ap.parse_args()
    e = env()
    schluessel = [k["name"] for k in json.loads(cf(e, "/keys?prefix=spende/"))["result"]]
    if not schluessel:
        print("Keine neuen Spenden.")
        return
    for k in schluessel:
        sid = k.split("/", 1)[1]
        ziel = os.path.join(HIER, "spenden", sid)
        daten = cf(e, "/values/" + urllib.parse.quote(k, safe=""))
        os.makedirs(ziel, exist_ok=True)
        open(ziel + ".zip", "wb").write(daten)
        with zipfile.ZipFile(io.BytesIO(daten)) as z:
            z.extractall(ziel)
        m = json.load(open(os.path.join(ziel, "manifest.json")))
        zeilen = []
        for s in m["saetze"]:
            pcm = open(os.path.join(ziel, s["datei"]), "rb").read()[44:]
            text = json.load(urllib.request.urlopen(urllib.request.Request(args.stt, pcm), timeout=30))["text"]
            aehnl = difflib.SequenceMatcher(None, norm(s["satz"]), norm(text)).ratio()
            zeilen.append((aehnl, s["datei"], s["satz"], text, s.get("erkannt", "")))
        zeilen.sort()
        with open(os.path.join(ziel, "pruefung.tsv"), "w") as f:
            f.write("Ähnlichkeit\tDatei\tVorlage\tLokal erkannt\tErkannt beim Spender\n")
            for z in zeilen:
                f.write(f"{z[0]:.2f}\t" + "\t".join(z[1:]) + "\n")
        auffaellig = sum(z[0] < 0.6 for z in zeilen)
        print(f"{sid}: {len(zeilen)} Aufnahmen, {auffaellig} auffällig, Gerät {m.get('satellit_plattform')}/{m.get('geraet') or '-'}, Raum {m.get('raum')}")
        if not args.behalten:
            cf(e, "/values/" + urllib.parse.quote(k, safe=""), methode="DELETE")


if __name__ == "__main__":
    main()
