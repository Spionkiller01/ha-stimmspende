"""Konstanten der Stimmspende."""

DOMAIN = "stimmspende"
VERSION = "0.2.2"

UPLOAD_URL = "https://stimmspende.spionkiller01.workers.dev/spende"

CONF_SATELLIT = "satellit"
CONF_ANZAHL = "anzahl"
CONF_OKAY = "okay_sagen"
CONF_EIGENE_STIMME = "eigene_stimme"
CONF_VOLLJAEHRIG = "volljaehrig"
CONF_CC0 = "cc0"
CONF_GERAET = "geraet"
CONF_RAUM = "raum"
CONF_ABSTAND = "abstand"
CONF_HINTERGRUND = "hintergrund"
CONF_DIALEKT = "dialekt"
CONF_RAUMGROESSE = "raumgroesse"
CONF_RAUMKLANG = "raumklang"
CONF_SPRECHER = "sprecher"

RAEUME = ["wohnzimmer", "kueche", "schlafzimmer", "arbeitszimmer", "bad", "flur", "anderer"]
ABSTAENDE = ["unter_1m", "1_3m", "3_5m", "ueber_5m", "gemischt"]
HINTERGRUENDE = ["ruhig", "etwas", "deutlich", "gemischt"]
RAUMGROESSEN = ["klein", "mittel", "gross"]
RAUMKLAENGE = ["gedaempft", "normal", "hallig"]
