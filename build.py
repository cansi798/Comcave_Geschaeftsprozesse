#!/usr/bin/env python3
"""Baut die Lernseite Geschaeftsprozesse 2026 fuer GitHub Pages.

Das Material liegt verschluesselt in tresor/ und wird je Tag zur eingestellten Uhrzeit
freigegeben (oder sofort, wenn in zeitplan.json "alles_sofort": true steht).
Die Seite selbst ist mit dem Zugangscode aus zeitplan.json geschuetzt.
Testlauf mit fester Uhrzeit:  JETZT="2026-11-12 12:30" python3 build.py
(c) 2026 Waybuild
"""
import os, json, shutil, subprocess, datetime, hashlib, glob, re, base64
from zoneinfo import ZoneInfo

TZ = ZoneInfo("Europe/Berlin")
ROOT = os.path.dirname(os.path.abspath(__file__))
SITE = os.path.join(ROOT, "_site")
KEY = os.environ.get("MATERIAL_KEY", "")
VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v")


def jetzt():
    j = os.environ.get("JETZT")
    if j:
        return datetime.datetime.strptime(j, "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
    return datetime.datetime.now(TZ)


def zeitpunkt(datum, uhr):
    return datetime.datetime.strptime(f"{datum} {uhr}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)


def openssl_dec(datei, out=None):
    cmd = ["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:MATERIAL_KEY", "-in", datei]
    if out:
        cmd += ["-out", out]
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise SystemExit(f"Entschluesseln fehlgeschlagen ({os.path.basename(datei)}). Ist das Secret MATERIAL_KEY richtig gesetzt?")
    return r.stdout


def entpacken(datei, ziel):
    os.makedirs(ziel, exist_ok=True)
    subprocess.run(["tar", "xzf", "-", "-C", ziel], input=openssl_dec(datei), check=True)


def quizdaten(html_datei):
    s = open(html_datei, encoding="utf-8").read()
    m = re.search(r'<script[^>]*id="(?:qd|pool)"[^>]*>(.*?)</script>', s, re.S)
    if not m:
        raise SystemExit(f"Keine Quizdaten in {html_datei}")
    return json.loads(m.group(1))


def schreibe_json(daten, pfad):
    os.makedirs(os.path.dirname(pfad), exist_ok=True)
    with open(pfad, "w", encoding="utf-8") as f:
        json.dump(daten, f, ensure_ascii=False, separators=(",", ":"))


def video_fuer(tag, videos, P, MAT, stand):
    link = (videos.get(tag) or "").strip()
    if link:
        yt = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?v=|embed/|shorts/))([\w-]{6,})", link)
        stand.append(f"{tag}video:{link}")
        if yt:
            return {"typ": "youtube", "id": yt.group(1)}
        if link.lower().split("?")[0].endswith(VIDEO_EXT):
            return {"typ": "datei", "src": link}
        return {"typ": "link", "src": link}
    os.makedirs(os.path.join(MAT, "videos"), exist_ok=True)
    for p in sorted(glob.glob(os.path.join(ROOT, "tresor", "videos", f"Tag{tag}*.enc"))):
        name = os.path.basename(p)[:-4]
        openssl_dec(p, os.path.join(MAT, "videos", name))
        stand.append(f"{tag}video:{os.path.getsize(p)}")
        return {"typ": "datei", "src": f"{P}/videos/{name}"}
    for p in sorted(glob.glob(os.path.join(ROOT, "videos", f"Tag{tag}*"))):
        if p.lower().endswith(VIDEO_EXT):
            shutil.copy2(p, os.path.join(MAT, "videos", os.path.basename(p)))
            stand.append(f"{tag}video:{os.path.getsize(p)}")
            return {"typ": "datei", "src": f"{P}/videos/{os.path.basename(p)}"}
    return None


def main():
    cfg = json.load(open(os.path.join(ROOT, "zeitplan.json"), encoding="utf-8"))
    inhalt = json.load(open(os.path.join(ROOT, "tresor", "inhalt.json"), encoding="utf-8"))
    videos = json.load(open(os.path.join(ROOT, "videos.json"), encoding="utf-8"))
    now = jetzt()
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(SITE)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(SITE, "assets"))
    open(os.path.join(SITE, ".nojekyll"), "w").close()

    # Alle Dateien liegen in einem Unterordner, dessen Name sich aus dem Secret ableitet.
    P = ("m" + hashlib.sha256(("pfad|" + KEY).encode()).hexdigest()[:24]) if KEY else "m-ohne-schluessel"
    MAT = os.path.join(SITE, P)
    os.makedirs(MAT)
    stand, tage, reihenfolge, teile, frei = [], {}, [], [], {}

    for t in cfg["tage"]:
        n, o = t["tag"], t["ordner"]
        z1 = zeitpunkt(t["datum"], t.get("vormittag") or cfg["uhrzeit_vormittag"])
        z2 = zeitpunkt(t["datum"], t.get("nachmittag") or cfg["uhrzeit_nachmittag"])
        frei1 = now >= z1 and bool(KEY)
        frei2 = now >= z2 and bool(KEY)
        if cfg.get("alles_sofort"):
            frei1 = frei2 = bool(KEY)
        frei[n] = (frei1, frei2)
        datum_de = datetime.date.fromisoformat(t["datum"]).strftime("%d.%m.%Y")
        teilkurz, _, teillang = t["teil"].partition(" · ")
        d = {"datum": t["datum"], "datum_de": datum_de, "wochentag": t["wochentag"], "titel": t["titel"],
             "teilkurz": teilkurz, "frei1": frei1, "frei2": frei2,
             "ab1": f"ab {datum_de}, {z1:%H:%M} Uhr", "ab2": f"ab {datum_de}, {z2:%H:%M} Uhr"}
        dateien = inhalt[o]
        ziel = os.path.join(MAT, o)
        if frei1:
            entpacken(os.path.join(ROOT, "tresor", f"Tag{n}_1_Vormittag.tar.gz.enc"), ziel)
            v = dateien["vormittag"]
            d["praes"] = f"{P}/{o}/{v[0]}"
            d["skript"] = f"{P}/{o}/{v[1]}"
            q = quizdaten(os.path.join(ziel, v[2]))
            schreibe_json(q, os.path.join(ziel, "quiz", "tagesquiz.json"))
            d["quiz"] = f"{P}/{o}/quiz/tagesquiz.json"
            d["quiz_n"] = len(q)
            d["video"] = video_fuer(n, videos, P, MAT, stand)
            stand.append(f"{n}v")
        if frei2:
            entpacken(os.path.join(ROOT, "tresor", f"Tag{n}_2_Nachmittag.tar.gz.enc"), ziel)
            uebungen, hefte = [], {}
            for f in dateien["nachmittag"]:
                b = os.path.basename(f)
                m = re.search(r"Uebungsquiz_(\d)_([A-Za-z]+)_ONLINE", b)
                if m:
                    q = quizdaten(os.path.join(ziel, f))
                    schreibe_json(q, os.path.join(ziel, "quiz", f"uebung{m.group(1)}.json"))
                    uebungen.append({"nr": m.group(1), "info": m.group(2), "anzahl": len(q),
                                     "src": f"{P}/{o}/quiz/uebung{m.group(1)}.json"})
                    continue
                m = re.search(r"Aufgabenheft_(\d)_([A-Za-z]+?)(_Loesung)?\.pdf", b)
                if m:
                    h = hefte.setdefault(m.group(1), {"nr": m.group(1),
                                                     "thema": {"Begriffe": "Begriffe und Verständnis", "Faelle": "Fälle aus der Praxis"}.get(m.group(2), m.group(2))})
                    h["loesung" if m.group(3) else "aufgabe"] = f"{P}/{o}/{f}"
            d["uebungen"] = sorted(uebungen, key=lambda u: u["nr"])
            d["hefte"] = [hefte[k] for k in sorted(hefte)]
            stand.append(f"{n}n")
        tage[n] = d
        reihenfolge.append(n)
        if not teile or teile[-1]["kurz"] != teilkurz:
            teile.append({"kurz": teilkurz, "lang": teillang, "tage": []})
        teile[-1]["tage"].append(n)

    kurs = None
    if cfg.get("kursdateien_sofort", True) and KEY:
        entpacken(os.path.join(ROOT, "tresor", "Kursdateien.tar.gz.enc"), os.path.join(MAT, "kurs"))
        pool = quizdaten(os.path.join(MAT, "kurs", "03_Quiz-Trainer_alle_Fragen_und_Probeklausur.html"))
        pool = [q for q in pool if q.get("tag") in frei and frei[q["tag"]][0 if q.get("src") == "Tagesquiz" else 1]]
        schreibe_json(pool, os.path.join(MAT, "kurs", "pool.json"))
        kurs = {"pool": f"{P}/kurs/pool.json", "gesamtskript": f"{P}/kurs/04_Gesamtskript_alle_Tage.pdf", "anzahl": len(pool)}
        stand.append(f"kurs:{len(pool)}")

    daten = {"marker": "gp2026", "titel": cfg["kurs"]["titel"], "untertitel": cfg["kurs"]["untertitel"],
             "teile": teile, "reihenfolge": reihenfolge, "tage": tage, "kurs": kurs}
    code = str(cfg.get("zugangscode", "KBM")).strip().upper()
    fingerprint = hashlib.sha256((json.dumps(daten, sort_keys=True, ensure_ascii=False) + code + P + "|".join(stand)
                                  + open(os.path.join(ROOT, "vorlage.html"), encoding="utf-8").read()).encode()).hexdigest()
    daten["stand"] = f"{now:%d.%m.%Y, %H:%M}"
    enc = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-md", "sha256", "-salt",
                          "-pass", "env:ZUGANGSCODE"], input=json.dumps(daten, ensure_ascii=False).encode("utf-8"),
                         capture_output=True, check=True, env=dict(os.environ, ZUGANGSCODE=code)).stdout
    seite = open(os.path.join(ROOT, "vorlage.html"), encoding="utf-8").read().replace("__DATEN__", base64.b64encode(enc).decode())
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(seite)
    open(os.path.join(SITE, "stand.txt"), "w").write(fingerprint + "\n")
    print("Freigegeben:", ", ".join(stand) or "nichts", "| Fingerprint", fingerprint[:12])
    if not KEY:
        print("WARNUNG: Secret MATERIAL_KEY fehlt, es wird kein Material freigeschaltet.")


if __name__ == "__main__":
    main()
