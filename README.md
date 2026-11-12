# Geschäftsprozesse 2026 · Lernseite (GitHub Pages)

Seite: https://cansi798.github.io/Comcave_Geschaeftsprozesse/

## So funktioniert die Freischaltung
Jeder Unterrichtstag hat zwei Stufen.

| Stufe | Inhalt | Uhrzeit (Standard) |
|---|---|---|
| Vormittag | Präsentation als PDF, Skript, Quiz, Video des Tages | 12:00 Uhr |
| Nachmittag, freiwillig | Übungsquiz 1 und 2, Aufgabenheft 1 und 2 mit Lösungen | 12:45 Uhr |

Quiz-Trainer und Gesamtskript sind sofort sichtbar (Ordner `kurs`).

Das Tagesmaterial liegt bis zur Freigabe verschlüsselt im Ordner `tresor`. Der Workflow `.github/workflows/freigabe.yml` läuft montags bis freitags alle 15 Minuten zwischen 07:00 und 19:00 Uhr, entschlüsselt alles Fällige mit dem Secret `MATERIAL_KEY` und veröffentlicht die Seite neu. GitHub startet geplante Läufe manchmal 5 bis 20 Minuten später.

## Einmalige Einrichtung
1. Settings, Secrets and variables, Actions, New repository secret. Name `MATERIAL_KEY`, Wert aus der lokalen Datei `_Schluessel_Website.txt`.
2. Settings, Pages, Build and deployment, Source auf **GitHub Actions** stellen.
3. Actions, „Lernseite freischalten und veroeffentlichen“, Run workflow.

## Uhrzeiten ändern
In `zeitplan.json` die Werte `uhrzeit_vormittag` und `uhrzeit_nachmittag` ändern. Für einen einzelnen Tag beim Tag z. B. `"vormittag": "11:30"` oder `"nachmittag": "14:00"` ergänzen.

## Video ergänzen
Siehe `videos/LIESMICH.md`.

© 2026 Waybuild Akademie, Waybuild UG (haftungsbeschränkt). Alle Rechte vorbehalten. · www.waybuild.de
