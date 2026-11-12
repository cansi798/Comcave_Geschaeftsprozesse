# Geschäftsprozesse 2026 · Lernseite (GitHub Pages)

Seite: https://cansi798.github.io/Comcave_Geschaeftsprozesse/

## So funktioniert die Freischaltung
Aktuell ist in `zeitplan.json` `"alles_sofort": true` gesetzt, damit ist alles sofort sichtbar. Mit `false` gilt der Zeitplan unten.

Jeder Unterrichtstag hat zwei Stufen.

| Stufe | Inhalt | Uhrzeit (Standard) |
|---|---|---|
| Vormittag | Präsentation als PDF, Skript, Quiz, Video des Tages | 12:00 Uhr |
| Nachmittag, freiwillig | Übungsquiz 1 und 2, Aufgabenheft 1 und 2 mit Lösungen | 12:45 Uhr |

Quiz-Trainer und Gesamtskript sind sofort sichtbar.

Die Seite fragt zuerst nach dem **Zugangscode** (Standard `KBM`, änderbar in `zeitplan.json` unter `zugangscode`). Ohne Code sieht man nur die Eingabemaske. Die Dateien liegen in einem Unterordner, dessen Name sich aus dem Secret ableitet.

Das gesamte Material liegt bis zur Freigabe verschlüsselt im Ordner `tresor`. Der Workflow `.github/workflows/freigabe.yml` läuft montags bis freitags alle 15 Minuten zwischen 07:00 und 19:00 Uhr, entschlüsselt alles Fällige mit dem Secret `MATERIAL_KEY` und veröffentlicht die Seite neu. GitHub startet geplante Läufe manchmal 5 bis 20 Minuten später.

## Aufbau der Seite
Übersicht mit dem heutigen Tag, Quiz-Trainer, Probeklausur, Gesamtskript und allen Tagen als Kacheln. Am Desktop gibt es eine Seitenleiste, am Handy eine Leiste oben mit Zurück-Knopf und eine Leiste unten (Übersicht, Heute, Trainer, Alle Tage).
Jeder Tag hat die Kacheln Präsentation, Skript, Quiz und Video sowie die Kachel Nachmittag mit Übungsquizzen und Aufgabenheften.
Alle Quizze laufen direkt in der Seite. Alle Fragen stehen untereinander, wahlweise mit Sofort-Feedback je Frage oder mit Auswertung am Ende, jeweils mit Erklärung und Note nach IHK-Schlüssel.

## Einmalige Einrichtung
1. Settings, Secrets and variables, Actions, New repository secret. Name `MATERIAL_KEY`, Wert aus der lokalen Datei `_Schluessel_Website.txt`.
2. Settings, Pages, Build and deployment, Source auf **GitHub Actions** stellen.
3. Actions, „Lernseite freischalten und veroeffentlichen“, Run workflow.

## Uhrzeiten ändern
In `zeitplan.json` die Werte `uhrzeit_vormittag` und `uhrzeit_nachmittag` ändern. Für einen einzelnen Tag beim Tag z. B. `"vormittag": "11:30"` oder `"nachmittag": "14:00"` ergänzen.

## Video ergänzen
Siehe `videos/LIESMICH.md`. Videos aus dem lokalen Kursordner (z. B. `Tag01_8_Video.mp4`) werden verschlüsselt unter `tresor/videos/` abgelegt.

© 2026 Waybuild · www.waybuild.de
