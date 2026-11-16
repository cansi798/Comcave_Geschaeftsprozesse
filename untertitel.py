#!/usr/bin/env python3
"""Erzeugt deutsche Untertitel (WebVTT) fuer alle Kursvideos, die noch keine haben.

Laeuft automatisch in GitHub Actions (Workflow "Untertitel"), sobald ein Video
hochgeladen wird. Die Untertitel werden wie die Videos verschluesselt im Ordner
tresor/videos abgelegt (TagNN_Untertitel.vtt.enc) und von build.py eingebunden.

Aufruf
  python3 untertitel.py --liste          zeigt nur, wie viele Videos offen sind
  python3 untertitel.py                  erzeugt alle fehlenden Untertitel
  python3 untertitel.py --neu 01,02      erzeugt die Untertitel fuer Tag 01 und 02 neu
  python3 untertitel.py --neu alle       erzeugt alle Untertitel neu
"""
import glob
import math
import os
import re
import subprocess
import sys
import tempfile
import textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
TRESOR = os.path.join(ROOT, "tresor", "videos")
VIDEO_EXT = (".mp4", ".webm", ".mov", ".m4v")
MODELL = os.environ.get("WHISPER_MODEL", "large-v3-turbo")
HINWEIS = ("Geschäftsprozesse für Kaufleute für Büromanagement. Hanse Bürowelt GmbH, BüroERP, "
           "DocuSafe, Microsoft 365, Teams, IHK, comcave, Waybuild, DSGVO, E-Rechnung, Skonto.")


def ssl(args):
    cmd = ["openssl", "enc", "-aes-256-cbc", "-pbkdf2", "-iter", "200000", "-pass", "env:MATERIAL_KEY"] + args
    r = subprocess.run(cmd, capture_output=True)
    if r.returncode != 0:
        raise SystemExit("openssl fehlgeschlagen. Ist MATERIAL_KEY gesetzt?")


def videos():
    """Liefert {tag: (pfad, verschluesselt)} fuer alle Videodateien."""
    v = {}
    for p in sorted(glob.glob(os.path.join(TRESOR, "Tag*.enc"))):
        name = os.path.basename(p)[:-4]
        m = re.match(r"Tag(\d\d)", name)
        if m and name.lower().endswith(VIDEO_EXT):
            v.setdefault(m.group(1), (p, True))
    for p in sorted(glob.glob(os.path.join(ROOT, "videos", "Tag*"))):
        m = re.match(r"Tag(\d\d)", os.path.basename(p))
        if m and p.lower().endswith(VIDEO_EXT):
            v.setdefault(m.group(1), (p, False))
    return v


def ziel(tag, verschluesselt):
    if verschluesselt:
        return os.path.join(TRESOR, f"Tag{tag}_Untertitel.vtt.enc")
    return os.path.join(ROOT, "videos", f"Tag{tag}_Untertitel.vtt")


def offen(neu):
    out = []
    for tag, (p, enc) in sorted(videos().items()):
        if neu == "alle" or tag in neu or not os.path.exists(ziel(tag, enc)):
            out.append((tag, p, enc))
    return out


def zeit(s):
    s = max(0.0, s)
    h, r = divmod(s, 3600)
    m, r = divmod(r, 60)
    return f"{int(h):02d}:{int(m):02d}:{r:06.3f}"


def umbruch(text):
    if len(text) <= 42:
        return text
    breite = max(42, math.ceil(len(text) / 2) + 4)
    return "\n".join(textwrap.wrap(text, breite)[:3])


def bloecke(segmente):
    """Teilt die Woerter in gut lesbare Untertitel (hoechstens etwa 2 Zeilen, 6 Sekunden)."""
    woerter = [w for s in segmente for w in (s.words or [])]
    bl, akt = [], []
    for i, w in enumerate(woerter):
        akt.append(w)
        text = "".join(x.word for x in akt).strip()
        dauer = akt[-1].end - akt[0].start
        satzende = w.word.strip().endswith((".", "?", "!"))
        pause = i + 1 < len(woerter) and woerter[i + 1].start - w.end > 0.8
        if len(text) >= 80 or dauer >= 6 or ((satzende or pause) and len(text) >= 20):
            bl.append(akt)
            akt = []
    if akt:
        bl.append(akt)
    cues = []
    for i, b in enumerate(bl):
        start, ende = b[0].start, b[-1].end
        naechster = bl[i + 1][0].start if i + 1 < len(bl) else ende + 2
        ende = min(max(ende + 0.3, start + 1.2), naechster - 0.05)
        cues.append((start, max(ende, start + 0.5), umbruch("".join(x.word for x in b).strip())))
    return cues


def transkribieren(modell, datei):
    segmente, info = modell.transcribe(
        datei, language="de", vad_filter=True, word_timestamps=True,
        beam_size=5, condition_on_previous_text=False, initial_prompt=HINWEIS)
    segmente = list(segmente)
    print(f"  Dauer {info.duration:.0f} s, {len(segmente)} Abschnitte", flush=True)
    vtt = ["WEBVTT", "Kind: captions", "Language: de", ""]
    for n, (a, e, t) in enumerate(bloecke(segmente), 1):
        vtt += [str(n), f"{zeit(a)} --> {zeit(e)}", t, ""]
    return "\n".join(vtt)


def main():
    neu = set()
    if "--neu" in sys.argv:
        wert = sys.argv[sys.argv.index("--neu") + 1].strip() if len(sys.argv) > sys.argv.index("--neu") + 1 else ""
        neu = "alle" if wert == "alle" else {x.strip().zfill(2) for x in wert.split(",") if x.strip()}
    liste = offen(neu)
    if "--liste" in sys.argv:
        print(f"anzahl={len(liste)}")
        print("tage=" + ",".join(t for t, _, _ in liste))
        return
    if not liste:
        print("Alle Videos haben Untertitel.")
        return
    from faster_whisper import WhisperModel
    modell = WhisperModel(MODELL, device="cpu", compute_type="int8")
    for tag, p, enc in liste:
        print(f"Tag {tag}: {os.path.basename(p)}", flush=True)
        with tempfile.TemporaryDirectory() as tmp:
            datei = p
            if enc:
                datei = os.path.join(tmp, "video" + os.path.splitext(p[:-4])[1])
                ssl(["-d", "-in", p, "-out", datei])
            text = transkribieren(modell, datei)
            if enc:
                klar = os.path.join(tmp, "ut.vtt")
                open(klar, "w", encoding="utf-8").write(text)
                ssl(["-salt", "-in", klar, "-out", ziel(tag, True)])
            else:
                open(ziel(tag, False), "w", encoding="utf-8").write(text)
        print(f"  gespeichert {os.path.relpath(ziel(tag, enc), ROOT)}", flush=True)


if __name__ == "__main__":
    main()
