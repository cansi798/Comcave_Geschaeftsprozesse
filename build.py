#!/usr/bin/env python3
"""Baut die Lernseite. Schaltet Material je Tag zur eingestellten Uhrzeit frei.
Freigabe: Stufe Vormittag (Praesentation PDF, Skript, Quiz, Video) und Stufe Nachmittag
(Uebungsquizze, Aufgabenhefte). Noch nicht freigegebenes Material liegt verschluesselt in tresor/.
Testlauf mit fester Uhrzeit:  JETZT="2026-11-12 12:30" python3 build.py
(c) 2026 Waybuild"""
import os, json, shutil, subprocess, datetime, html, hashlib, glob, re, base64
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

def entschluesseln(datei, ziel):
    os.makedirs(ziel, exist_ok=True)
    dec = subprocess.run(["openssl", "enc", "-d", "-aes-256-cbc", "-pbkdf2", "-iter", "200000",
                          "-pass", "env:MATERIAL_KEY", "-in", datei], capture_output=True)
    if dec.returncode != 0:
        raise SystemExit(f"Entschluesseln fehlgeschlagen ({os.path.basename(datei)}). Ist das Secret MATERIAL_KEY richtig gesetzt?")
    subprocess.run(["tar", "xzf", "-", "-C", ziel], input=dec.stdout, check=True)

def video_fuer(tag, videos):
    link = (videos.get(tag) or "").strip()
    if link:
        return link, False
    for p in sorted(glob.glob(os.path.join(ROOT, "videos", f"Tag{tag}*"))):
        if p.lower().endswith(VIDEO_EXT):
            return "videos/" + os.path.basename(p), True
    return None, False

def a(href, text):
    return f'<a href="{html.escape(href)}" target="_blank" rel="noopener">{html.escape(text)}</a>'

def main():
    cfg = json.load(open(os.path.join(ROOT, "zeitplan.json"), encoding="utf-8"))
    inhalt = json.load(open(os.path.join(ROOT, "tresor", "inhalt.json"), encoding="utf-8"))
    videos = json.load(open(os.path.join(ROOT, "videos.json"), encoding="utf-8"))
    now = jetzt()
    shutil.rmtree(SITE, ignore_errors=True)
    os.makedirs(SITE)
    shutil.copytree(os.path.join(ROOT, "assets"), os.path.join(SITE, "assets"))
    open(os.path.join(SITE, ".nojekyll"), "w").close()

    stand = []
    # Alle Dateien liegen in einem Unterordner, dessen Name sich aus dem Secret ableitet.
    # Ohne Zugangscode kennt man die Adressen nicht.
    P = ("m" + hashlib.sha256(("pfad|" + KEY).encode()).hexdigest()[:24]) if KEY else "m-ohne-schluessel"
    MAT = os.path.join(SITE, P)
    os.makedirs(MAT)
    if cfg.get("kursdateien_sofort", True) and KEY:
        entschluesseln(os.path.join(ROOT, "tresor", "Kursdateien.tar.gz.enc"), os.path.join(MAT, "kurs"))
        stand.append("kurs")

    def kachel(href, titel, text, cls=""):
        if href:
            ziel = '' if href.startswith("#") else ' target="_blank" rel="noopener"'
            return (f'<a class="kachel {cls}" href="{html.escape(href)}"{ziel}><span class="kt">{html.escape(titel)}</span>'
                    f'<span class="kx">{html.escape(text)}</span></a>')
        return (f'<div class="kachel zu {cls}"><span class="kt">{html.escape(titel)}</span>'
                f'<span class="kx">{html.escape(text)}</span></div>')

    sektionen, uebersicht, ansichten = [], {}, []
    for t in cfg["tage"]:
        n, o = t["tag"], t["ordner"]
        z1 = zeitpunkt(t["datum"], t.get("vormittag") or cfg["uhrzeit_vormittag"])
        z2 = zeitpunkt(t["datum"], t.get("nachmittag") or cfg["uhrzeit_nachmittag"])
        frei1 = now >= z1 and bool(KEY)
        frei2 = now >= z2 and bool(KEY)
        dateien = inhalt[o]
        if frei1:
            entschluesseln(os.path.join(ROOT, "tresor", f"Tag{n}_1_Vormittag.tar.gz.enc"), os.path.join(MAT, o))
            stand.append(f"{n}v")
        if frei2:
            entschluesseln(os.path.join(ROOT, "tresor", f"Tag{n}_2_Nachmittag.tar.gz.enc"), os.path.join(MAT, o))
            stand.append(f"{n}n")
        heute = now.date().isoformat() == t["datum"]
        datum_de = datetime.date.fromisoformat(t["datum"]).strftime("%d.%m.%Y")
        ab1 = f"ab {z1:%H:%M} Uhr" if heute else f"ab {datum_de}, {z1:%H:%M} Uhr"
        ab2 = f"ab {z2:%H:%M} Uhr" if heute else f"ab {datum_de}, {z2:%H:%M} Uhr"

        # Uebersichtskachel
        status = "Heute" if heute else ("Freigegeben" if frei1 else ab1)
        cls = "tag" + ("" if frei1 else " off") + (" heute" if heute else "")
        uebersicht.setdefault(t["teil"], [])
        if t["teil"] not in sektionen:
            sektionen.append(t["teil"])
        uebersicht[t["teil"]].append(
            f'<a class="{cls}" href="#tag{n}"><span class="dh"><span class="nr">Tag {n}</span><span class="st">{html.escape(status)}</span></span>'
            f'<span class="dt">{t["wochentag"]}, {datum_de}</span><span class="ti">{html.escape(t["titel"])}</span></a>')

        # Vormittag
        v = dateien["vormittag"]
        vid, datei = (video_fuer(n, videos) if frei1 else (None, False))
        if vid:
            if datei:
                src = os.path.join(ROOT, vid)
                os.makedirs(os.path.join(MAT, "videos"), exist_ok=True)
                shutil.copy2(src, os.path.join(MAT, vid))
                vid = f"{P}/{vid}"
                stand.append(f"{n}video:{os.path.getsize(src)}")
            else:
                stand.append(f"{n}video:{vid}")
        if frei1:
            vm = [kachel(f"{P}/{o}/{v[0]}", "Präsentation", "Folien des Tages als PDF", "k1"),
                  kachel(f"{P}/{o}/{v[1]}", "Skript", "Hauptskript zum Nachlesen", "k2"),
                  kachel(f"{P}/{o}/{v[2]}", "Quiz", "Tagesquiz online", "k3"),
                  kachel(vid, "Video", "Video zum Tag ansehen", "k4") if vid else kachel(None, "Video", "Video folgt", "k4 folgt")]
        else:
            vm = [kachel(None, x, ab1, c) for x, c in (("Präsentation", "k1"), ("Skript", "k2"), ("Quiz", "k3"), ("Video", "k4"))]
        nm_kachel = (kachel(f"#tag{n}-nachmittag", "Nachmittag", "Freiwillige Übungsquizze und Aufgabenhefte", "k5 gross") if frei2
                     else kachel(None, "Nachmittag", f"Freiwillige Übungsquizze und Aufgabenhefte {ab2}", "k5 gross"))
        kopf = (f'<p class="zur"><a href="#">Alle Tage</a></p><h2 class="tk">Tag {n} · {html.escape(t["titel"])}</h2>'
                f'<p class="tu">{t["wochentag"]}, {datum_de} · {html.escape(t["teil"])}</p>')
        ansichten.append(f'<div class="ansicht" id="v-tag{n}">{kopf}<h3>Vormittag</h3><div class="kacheln">{"".join(vm)}</div>'
                         f'<div class="kacheln eins">{nm_kachel}</div></div>')

        # Nachmittag
        if frei2:
            nm = []
            for f in dateien["nachmittag"]:
                b = os.path.basename(f)
                m = re.search(r"Uebungsquiz_(\d)_(\w+?)_ONLINE", b)
                if m:
                    nm.append(kachel(f"{P}/{o}/{f}", f"Übungsquiz {m.group(1)}", "Grundlagen, 60 Fragen" if m.group(2) == "Grundlagen" else "Anwendung, 60 Fragen", "k3"))
                    continue
                m = re.search(r"Aufgabenheft_(\d)_([A-Za-z]+?)(_Loesung)?\.pdf", b)
                thema = {"Begriffe": "Begriffe und Verständnis", "Faelle": "Fälle"}.get(m.group(2), m.group(2))
                if m.group(3):
                    nm.append(kachel(f"{P}/{o}/{f}", f"Lösung {m.group(1)}", f"Musterlösung zu Aufgabenheft {m.group(1)}", "k6"))
                else:
                    nm.append(kachel(f"{P}/{o}/{f}", f"Aufgabenheft {m.group(1)}", thema, "k5"))
            ansichten.append(f'<div class="ansicht" id="v-tag{n}-nachmittag"><p class="zur"><a href="#tag{n}">Zurück zu Tag {n}</a> · <a href="#">Alle Tage</a></p>'
                             f'<h2 class="tk">Tag {n} · Nachmittag, freiwillig</h2><p class="tu">{html.escape(t["titel"])}</p>'
                             f'<div class="kacheln">{"".join(nm)}</div></div>')

    kurs = ""
    if cfg.get("kursdateien_sofort", True) and KEY:
        kurs = ('<h3>Kursdateien</h3><div class="kacheln">'
                + kachel(f"{P}/kurs/03_Quiz-Trainer_alle_Fragen_und_Probeklausur.html", "Quiz-Trainer", "Alle Fragen und Probeklausur", "k3")
                + kachel(f"{P}/kurs/04_Gesamtskript_alle_Tage.pdf", "Gesamtskript", "Skripte aller Tage", "k2") + "</div>")
    start = ('<div class="ansicht" id="v-start"><div class="kurs">Tag anklicken, um Präsentation, Skript, Quiz und Video zu öffnen. '
             'Nachmittags kommen die freiwilligen Übungsquizze und Aufgabenhefte dazu.</div>' + kurs
             + "".join(f'<section><h2>{html.escape(s)}</h2><div class="grid">{"".join(uebersicht[s])}</div></section>' for s in sektionen)
             + "</div>")
    inhalt_html = "<!--gp2026-->" + start + "".join(ansichten)
    code = str(cfg.get("zugangscode", "KBM")).strip()
    enc = subprocess.run(["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "100000", "-md", "sha256", "-salt",
                          "-pass", "env:ZUGANGSCODE"], input=inhalt_html.encode("utf-8"), capture_output=True, check=True,
                         env=dict(os.environ, ZUGANGSCODE=code.upper())).stdout
    seite = TEMPLATE.format(titel=html.escape(cfg["kurs"]["titel"]), untertitel=html.escape(cfg["kurs"]["untertitel"]),
                            daten=base64.b64encode(enc).decode(), stand=f"{now:%d.%m.%Y, %H:%M}")
    open(os.path.join(SITE, "index.html"), "w", encoding="utf-8").write(seite)
    fingerprint = hashlib.sha256((inhalt_html + code + P + "|".join(stand)).encode()).hexdigest()
    open(os.path.join(SITE, "stand.txt"), "w").write(fingerprint + "\n")
    print("Freigegeben:", ", ".join(stand) or "nichts", "| Fingerprint", fingerprint[:12])
    if not KEY:
        print("WARNUNG: Secret MATERIAL_KEY fehlt, es wird kein Tagesmaterial freigeschaltet.")

TEMPLATE = """<!DOCTYPE html><html lang="de"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Geschäftsprozesse 2026 · Waybuild Akademie</title><style>
body{{font-family:Inter,Arial,sans-serif;margin:0;background:#f4f7f9;color:#1d2b3a}}
header{{background:#fff;border-bottom:3px solid #0077A6;padding:16px 26px;display:flex;gap:22px;align-items:center;flex-wrap:wrap}}
header img{{height:52px}}header h1{{margin:0;color:#003366;font-size:26px}}header p{{margin:4px 0 0;color:#555}}
main{{max-width:1200px;margin:0 auto;padding:16px}}
.kurs{{background:#fff;border:1px solid #d5e1e9;border-radius:12px;padding:12px 18px;margin:10px 0;line-height:1.7}}
h2{{color:#003366;font-size:20px;margin:22px 0 8px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(260px,1fr));gap:12px}}
.tag{{display:block;text-decoration:none;color:inherit;background:#fff;border:1px solid #d5e1e9;border-left:6px solid #0077A6;border-radius:10px;padding:10px 14px;transition:box-shadow .15s,transform .15s}}
.tag:hover{{box-shadow:0 4px 14px #00336622;transform:translateY(-1px)}}
.tag.off{{border-left-color:#bbb;color:#777;background:#fafbfc}}.tag.heute{{border-left-color:#E8833A;box-shadow:0 0 0 2px #E8833A55}}
.dh{{display:flex;justify-content:space-between;align-items:center}}.nr{{font-weight:700;color:#0077A6}}.heute .nr{{color:#E8833A}}
.st{{font-size:12px;padding:2px 8px;border-radius:10px;background:#e6f2f7;color:#0077A6}}.off .st{{background:#eee;color:#888}}.heute .st{{background:#E8833A;color:#fff}}
.dt{{display:block;color:#555;font-size:13.5px;margin-top:2px}}.ti{{display:block;font-weight:600;margin-top:4px}}
.ansicht{{display:none}}.ansicht.aktiv{{display:block}}
.zur{{margin:8px 0 0;font-size:14px}}.tk{{margin:8px 0 2px;font-size:23px}}.tu{{margin:0 0 6px;color:#555}}
h3{{color:#003366;font-size:17px;margin:18px 0 8px}}
.kacheln{{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:14px}}.kacheln.eins{{margin-top:14px;grid-template-columns:1fr}}
.kachel{{display:flex;flex-direction:column;gap:6px;min-height:96px;justify-content:center;text-decoration:none;color:#1d2b3a;background:#fff;border:1px solid #d5e1e9;border-top:6px solid #0077A6;border-radius:12px;padding:16px 18px;transition:box-shadow .15s,transform .15s}}
a.kachel:hover{{box-shadow:0 6px 18px #00336626;transform:translateY(-2px)}}
.kachel .kt{{font-size:19px;font-weight:700;color:#003366}}.kachel .kx{{font-size:14px;color:#555}}
.k2{{border-top-color:#2E8B57}}.k3{{border-top-color:#7A4FB5}}.k4{{border-top-color:#C0392B}}.k5{{border-top-color:#E8833A}}.k6{{border-top-color:#8A9BA8}}
.k5.gross{{background:#fff8f2;min-height:80px}}
.kachel.zu{{background:#f3f5f7;border-top-color:#c4ccd3;color:#888}}.kachel.zu .kt{{color:#8a96a0}}.kachel.zu .kx::before{{content:"Gesperrt · "}}.kachel.folgt .kx::before{{content:""}}
.tor p{{margin:4px 0 10px;color:#555}}.tor input{{font-size:17px;padding:8px 10px;border:1px solid #9fb6c6;border-radius:8px;width:200px;text-transform:uppercase}}.tor button{{font-size:16px;padding:8px 16px;border:0;border-radius:8px;background:#0077A6;color:#fff;cursor:pointer}}#err{{color:#b3261e;margin-top:8px;font-size:14px}}
a{{color:#0077A6}}footer{{max-width:1200px;margin:20px auto;padding:12px 16px;font-size:12.5px;color:#555;border-top:1px solid #d5e1e9}}
</style></head><body>
<header><img src="assets/logo.png" alt="Waybuild Akademie"><div><h1>{titel}</h1><p>{untertitel}</p></div></header>
<main><div id="tor" class="kurs tor"><b>Zugangscode</b><p>Bitte den Zugangscode aus dem Unterricht eingeben.</p>
<form id="f"><input id="c" autocomplete="off" autocapitalize="characters" placeholder="Zugangscode" aria-label="Zugangscode"> <button>Öffnen</button></form><div id="err"></div></div>
<div id="inhalt"></div></main>
<footer>Dozent Can Siebert · Waybuild · <a href="https://www.waybuild.de">www.waybuild.de</a><br>© 2026 Waybuild. Alle Rechte vorbehalten.<!--stand--> · Stand {stand} Uhr</footer>
<script>
const DATEN="{daten}";
async function oeffnen(code){{
  const raw=Uint8Array.from(atob(DATEN),c=>c.charCodeAt(0));
  const salt=raw.slice(8,16),ct=raw.slice(16);
  const base=await crypto.subtle.importKey("raw",new TextEncoder().encode(code),"PBKDF2",false,["deriveBits"]);
  const bits=new Uint8Array(await crypto.subtle.deriveBits({{name:"PBKDF2",salt:salt,iterations:100000,hash:"SHA-256"}},base,384));
  const key=await crypto.subtle.importKey("raw",bits.slice(0,32),"AES-CBC",false,["decrypt"]);
  const pt=await crypto.subtle.decrypt({{name:"AES-CBC",iv:bits.slice(32,48)}},key,ct);
  const html=new TextDecoder("utf-8",{{fatal:true}}).decode(pt);
  if(html.indexOf('<!--gp2026-->')!==0) throw new Error("falsch");
  document.getElementById("inhalt").innerHTML=html;
  document.getElementById("tor").style.display="none";
  try{{localStorage.setItem("gp2026code",code)}}catch(e){{}}
  zeigen();
}}
function zeigen(){{
  const id=(location.hash||"").replace("#","");
  const ziel=document.getElementById(id?"v-"+id:"v-start")||document.getElementById("v-start");
  if(!ziel) return;
  document.querySelectorAll(".ansicht").forEach(v=>v.classList.toggle("aktiv",v===ziel));
  if(ziel.id==="v-start"){{const h=document.querySelector(".tag.heute"); if(h&&!id) h.scrollIntoView({{block:"center"}}); else window.scrollTo(0,0);}}
  else window.scrollTo(0,0);
}}
window.addEventListener("hashchange",zeigen);
document.getElementById("f").addEventListener("submit",async e=>{{
  e.preventDefault(); const code=document.getElementById("c").value.trim().toUpperCase();
  try{{await oeffnen(code); document.getElementById("err").textContent=""}}catch(x){{document.getElementById("err").textContent="Der Zugangscode stimmt nicht."}}
}});
(async()=>{{let c=null;try{{c=localStorage.getItem("gp2026code")}}catch(e){{}} if(c){{try{{await oeffnen(c)}}catch(e){{try{{localStorage.removeItem("gp2026code")}}catch(_){{}}}}}}}})();
</script>
</body></html>"""

if __name__ == "__main__":
    main()
