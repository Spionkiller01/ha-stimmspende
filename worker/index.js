// Stimmspende-Empfang (Cloudflare Worker): POST /spende mit einer ZIP aus der HA-Integration.
// Prueft Groesse, Aufbau (manifest.json + 001.wav ...) und Einwilligung, begrenzt die Menge je
// Absender und legt die ZIP im KV-Speicher SPENDEN ab. Bruno holt sie von dort ab (werkzeuge/
// spenden_holen.py), prueft sie und veroeffentlicht erst danach. IP-Adressen werden nicht gespeichert.

const MAX_ZIP = 24 * 1024 * 1024; // KV-Werte duerfen hoechstens 25 MiB gross sein
const MAX_WAVS = 100;
const PRO_STUNDE = 6;
const PRO_TAG = 250;

const antwort = (code, daten) =>
  new Response(JSON.stringify(daten), { status: code, headers: { "content-type": "application/json" } });

function eintraege(buf) {
  // Zentralverzeichnis einer ZIP lesen: [{name, methode, groesse, offset}]
  const v = new DataView(buf);
  let eocd = -1;
  for (let i = buf.byteLength - 22; i >= Math.max(0, buf.byteLength - 66000); i--) {
    if (v.getUint32(i, true) === 0x06054b50) { eocd = i; break; }
  }
  if (eocd < 0) throw new Error("Keine gueltige ZIP-Datei.");
  const anzahl = v.getUint16(eocd + 10, true);
  let p = v.getUint32(eocd + 16, true);
  const liste = [];
  const dec = new TextDecoder();
  for (let k = 0; k < anzahl; k++) {
    if (v.getUint32(p, true) !== 0x02014b50) throw new Error("ZIP-Verzeichnis beschaedigt.");
    const methode = v.getUint16(p + 10, true);
    const komprimiert = v.getUint32(p + 20, true);
    const groesse = v.getUint32(p + 24, true);
    const nl = v.getUint16(p + 28, true), el = v.getUint16(p + 30, true), cl = v.getUint16(p + 32, true);
    const offset = v.getUint32(p + 42, true);
    liste.push({ name: dec.decode(new Uint8Array(buf, p + 46, nl)), methode, komprimiert, groesse, offset });
    p += 46 + nl + el + cl;
  }
  return liste;
}

async function lesen(buf, e) {
  const v = new DataView(buf);
  const start = e.offset + 30 + v.getUint16(e.offset + 26, true) + v.getUint16(e.offset + 28, true);
  const roh = new Uint8Array(buf, start, e.komprimiert);
  if (e.methode === 0) return roh;
  if (e.methode !== 8) throw new Error("Unbekannte Kompression.");
  const strom = new Blob([roh]).stream().pipeThrough(new DecompressionStream("deflate-raw"));
  return new Uint8Array(await new Response(strom).arrayBuffer());
}

async function zaehlen(env, schluessel, grenze, ttl) {
  const n = parseInt((await env.SPENDEN.get(schluessel)) || "0", 10);
  if (n >= grenze) return false;
  await env.SPENDEN.put(schluessel, String(n + 1), { expirationTtl: ttl });
  return true;
}

async function hash(text) {
  const d = await crypto.subtle.digest("SHA-256", new TextEncoder().encode(text));
  return [...new Uint8Array(d)].slice(0, 8).map((b) => b.toString(16).padStart(2, "0")).join("");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (request.method === "GET") {
      return new Response("Stimmspende-Empfang. Infos: https://github.com/Spionkiller01/ha-stimmspende\n");
    }
    if (request.method !== "POST" || url.pathname !== "/spende") return antwort(404, { fehler: "unbekannt" });
    if (parseInt(request.headers.get("content-length") || "0", 10) > MAX_ZIP) {
      return antwort(413, { fehler: "ZIP zu gross (max. 24 MB)." });
    }
    const buf = await request.arrayBuffer();
    if (buf.byteLength > MAX_ZIP || buf.byteLength < 100) return antwort(413, { fehler: "Ungueltige Groesse." });

    let manifest;
    try {
      const liste = eintraege(buf);
      const wavs = liste.filter((e) => /^\d{3}\.wav$/.test(e.name));
      const man = liste.find((e) => e.name === "manifest.json");
      if (!man || wavs.length + 1 !== liste.length) throw new Error("Erwartet: manifest.json und 001.wav, 002.wav, ...");
      if (wavs.length < 1 || wavs.length > MAX_WAVS) throw new Error("Zu viele oder keine Aufnahmen.");
      if (liste.reduce((s, e) => s + e.groesse, 0) > 80 * 1024 * 1024) throw new Error("Inhalt zu gross.");
      if (man.groesse > 512 * 1024) throw new Error("manifest.json zu gross.");
      manifest = JSON.parse(new TextDecoder().decode(await lesen(buf, man)));
      const e = manifest.einwilligung || {};
      if (!(e.eigene_stimme && e.volljaehrig && e.cc0)) throw new Error("Einwilligung fehlt.");
      const namen = new Set((manifest.saetze || []).map((s) => s && s.datei));
      for (const w of wavs) if (!namen.has(w.name)) throw new Error(`Kein Satz zu ${w.name}.`);
    } catch (err) {
      return antwort(400, { fehler: String(err.message || err) });
    }

    const absender = await hash((request.headers.get("cf-connecting-ip") || "?") + env.SALZ);
    const stunde = Math.floor(Date.now() / 3600000), tag = Math.floor(Date.now() / 86400000);
    if (!(await zaehlen(env, `drossel/tag/${tag}`, PRO_TAG, 90000))) return antwort(429, { fehler: "Tageslimit erreicht, bitte morgen nochmal." });
    if (!(await zaehlen(env, `drossel/${absender}/${stunde}`, PRO_STUNDE, 4000))) return antwort(429, { fehler: "Zu viele Spenden in kurzer Zeit, bitte spaeter nochmal." });

    const jetzt = new Date();
    const id = `${jetzt.toISOString().slice(0, 19).replace(/[-:T]/g, "")}-${crypto.randomUUID().slice(0, 8)}`;
    await env.SPENDEN.put(`spende/${id}`, buf, {
      metadata: { saetze: manifest.saetze.length, bytes: buf.byteLength, zeit: jetzt.toISOString() },
    });
    return antwort(200, { ok: true, id, saetze: manifest.saetze.length });
  },
};
