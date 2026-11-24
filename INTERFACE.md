# Interface: blutspende

Kommando: `blutspende` (Console-Script), Python-Modul: `blutspende_cli`
(Python ≥ 3.10). Das Werkzeug ist lesend, es gibt keinen Login.

```
blutspende [--json] <unterkommando> [argumente] [optionen]
blutspende --version
blutspende --help
```

## Globale Optionen

| Option | Bedeutung |
|---|---|
| `--json` | Ausgabe als genau ein JSON-Objekt auf stdout (auch im Terminal) |
| `--version` | Version ausgeben, Exit 0 |
| `--help` | Hilfe ausgeben, Exit 0; gilt auch für jedes Unterkommando |

Ohne `--json` ist die Ausgabe im Terminal (stdout ist ein TTY) lesbarer Text.
Ist stdout **kein** TTY (Pipe, Datei, Agent), wird automatisch JSON
ausgegeben. Prompts erscheinen nie im JSON-Modus.

## Umgebungsvariablen

| Variable | Bedeutung |
|---|---|
| `BLUTSPENDE_BASE_URL` | Basis-URL der Quelle; Default `https://www.drk-blutspende.de` (für Fake-Server) |
| `BLUTSPENDE_HEUTE` | Heutiges Datum als `JJJJ-MM-TT`; nur für deterministische Tests und Läufe, Default: Systemdatum |
| `XDG_CONFIG_HOME` | Basis für die Config (Default `~/.config`) |
| `XDG_STATE_HOME` | Basis für den Watch-Zustand (Default `~/.local/state`) |
| `XDG_CACHE_HOME` | Basis für den Cache (Default `~/.cache`) |
| `XDG_DATA_HOME` | Basis für gespeicherte Kalenderdateien (Default `~/.local/share`) |

## Config- und Zustandspfade

| Inhalt | Pfad | Rechte |
|---|---|---|
| Config | `$XDG_CONFIG_HOME/blutspende-cli/config.json` | 0600 |
| Watch-Zustand | `$XDG_STATE_HOME/blutspende-cli/watch.json` | 0600 |
| Cache (10 min) | `$XDG_CACHE_HOME/blutspende-cli/` | Verzeichnis 0700 |
| Kalenderdatei | `$XDG_DATA_HOME/blutspende-cli/termine/<ID>.ics` | Datei 0644 |

Fehlende Verzeichnisse werden angelegt. Die Config ist optional; sie liefert
nur den Standardort und den Standardumkreis.

## Datumsformate

- Eingabe: `TT.MM.JJJJ` (deutsch) oder `JJJJ-MM-TT` (ISO).
- Ausgabe im Terminal: `TT.MM.JJJJ`.
- Anfrage an die Quelle: ISO `JJJJ-MM-TT` (`date_from`, `date_to`).
- `--von` ohne Wert ist heute (`BLUTSPENDE_HEUTE` oder Systemdatum).
- `--bis` muss ≥ `--von` sein, sonst Exit 2.

## Unterkommandos

### `blutspende suche [PLZ|ORT]`

Sucht Termine. Ohne Argument wird der in `config ort` gespeicherte Ort
verwendet; ist keiner gesetzt, Exit 2 mit Hinweis auf
`blutspende config ort <PLZ>`.

| Argument/Option | Bedeutung |
|---|---|
| `PLZ\|ORT` (positional, optional) | Suchbegriff, z. B. `74072` oder `Heilbronn` |
| `--umkreis KM` | Umkreis in km, Default `10`; ganzzahlig, 1–100 |
| `--landkreis NAME` | Landkreisname statt PLZ/Ort; löst den Namen über die Suchseite zur `county_id` auf (tippfehlertolerant) |
| `--von DATUM` | frühester Termin, Default heute |
| `--bis DATUM` | spätester Termin, optional |
| `--limit N` | höchstens N Treffer, Default `20`, `0` = alle (Quelle kappt bei 100) |

`PLZ|ORT` und `--landkreis` schließen sich aus (Exit 2).

Textausgabe:

```
3 Termine im Umkreis von 10 km um 74072
1) 02.12.2026, 14:00-19:00 Uhr: 74235 Erlenbach, Sulmtalhalle, Kultursaal (ID 436804)
2) 03.12.2026, 14:30-19:30 Uhr: 74388 Talheim, Schloßberghalle (ID 436838)
3) 23.12.2026, 14:00-19:00 Uhr: 74078 Heilbronn-Kirchhausen, Deutschordenhalle (ID 436026)
```

Bei `--landkreis` steht zusätzlich die erste Zeile
`Landkreis Zwickau (14524)`. Keine Treffer: `Keine Termine gefunden – Umkreis
oder Zeitraum vergrößern.` (Exit 0). Bei der 100er-Kappung der Quelle folgt
ein Hinweis, den Zeitraum oder Landkreis einzugrenzen.

### `blutspende naechster [PLZ|ORT]`

Gibt genau den frühesten Treffer aus. Akzeptiert dieselben Suchoptionen wie
`suche` (ohne `--limit`).

```
Nächster Termin:
23.12.2026, 14:00-19:00 Uhr: 74078 Heilbronn-Kirchhausen, Deutschordenhalle (ID 436026)
```

Keine Treffer: `Keine Termine gefunden – Umkreis oder Zeitraum vergrößern.`
(Exit 0).

### `blutspende zeige ID|ORT`

Zeigt die Detailansicht. Eine rein numerische Eingabe wird als Termin-ID
verwendet. Sonst wird per RSS nach dem Ort gesucht (Default-Umkreis 25 km).

| Argument/Option | Bedeutung |
|---|---|
| `ID\|ORT` (positional, Pflicht) | Termin-ID oder Ortsname |
| `--erster` | bei mehreren Treffern den ersten ohne Rückfrage nehmen |
| `--umkreis KM` | Umkreis für die Namenssuche, Default `25` |

Bei mehreren Treffern im TTY: nummerierte Liste und
`Welchen Termin anzeigen? [1-N]`. Ohne TTY und ohne `--erster`: Liste und
Exit 2 mit Hinweis auf eine ID oder `--erster`. Bei `--json` wird nie
interaktiv gefragt; mehrere Treffer führen zu Exit 2 mit Kandidatenliste im
JSON-Fehlerobjekt.

Detailausgabe:

```
Blutspende in Erlenbach
02.12.2026
Sulmtalhalle, Kultursaal
Talstraße 21
14:00 - 19:00 Uhr
Nur mit Terminreservierung!
Termin reservieren: https://terminreservierung.blutspende.de/oeffentliche-spendeorte/7423511/termine?…
```

Der Reservierungslink wird nur angezeigt, nie geöffnet oder aufgerufen. Fehlt
der Hinweis auf der Quelle, entfällt die Zeile `Nur mit Terminreservierung!`.

### `blutspende kalender ID`

Lädt `GET /blutspendetermine/termine/<ID>/ical.ics` und speichert die Datei.
Vorhandene Dateien werden überschrieben (idempotent).

| Option | Bedeutung |
|---|---|
| `--datei PFAD` | Zielpfad oder vorhandenes Verzeichnis; Default `$XDG_DATA_HOME/blutspende-cli/termine/<ID>.ics` |

```
Kalendereintrag gespeichert:
/home/nutzer/.local/share/blutspende-cli/termine/436804.ics
```

### `blutspende watch [PLZ|ORT]`

Sucht wie `suche` und meldet nur Termin-IDs, die im Zustand für dieselbe
Abfrage noch nicht gespeichert sind. Der erste Aufruf meldet alle Treffer.
Der Zustand wird nach jedem erfolgreichen Aufruf aktualisiert.

Akzeptiert `--umkreis` (Default `10`), `--landkreis`, `--von`, `--bis`,
`--limit`.

```
3 neue Termine seit dem letzten Aufruf
02.12.2026 74235 Erlenbach
03.12.2026 74388 Talheim
23.12.2026 74078 Heilbronn-Kirchhausen
```

Ohne neue Termine: `0 neue Termine seit dem letzten Aufruf` (Exit 0).

### `blutspende config`

| Aufruf | Bedeutung |
|---|---|
| `blutspende config ort PLZ [--umkreis KM]` | Standardort und optional Standardumkreis speichern (0600) |
| `blutspende config zeigen` | aktuelle Config ausgeben |
| `blutspende config loeschen` | Config löschen; idempotent |

`config ort` validiert die PLZ nicht gegen die Quelle, speichert sie aber nur
als Zeichenkette. `--umkreis` wird wie bei `suche` validiert.

## Ausgabeformat JSON

Mit `--json` (oder wenn stdout kein TTY ist) steht auf stdout genau ein
JSON-Objekt, auch bei Fehlern. Prompts und Warnungen gehen dann auf stderr.
Gemeinsames Fehlerobjekt:

```json
{"ok": false, "fehler": {"code": 3, "art": "netz", "nachricht": "Quelle nicht erreichbar – Internet prüfen oder später erneut versuchen."}}
```

Erfolgsobjekte (gekürzt):

```json
{"ok": true, "abfrage": {"ort": "74072", "umkreis_km": 10, "landkreis": null, "von": "2026-11-24", "bis": null}, "anzahl": 3, "gekappt": false, "termine": [{"id": 436804, "datum": "2026-12-02", "wochentag": "Mi", "von": "14:00", "bis": "19:00", "plz": "74235", "ort": "Erlenbach", "lokal": "Sulmtalhalle, Kultursaal", "strasse": "Talstraße 21", "reservierung_pflicht": true, "reservierung_url": "https://…", "detail_url": "https://…", "ical_url": "https://…"}]}
{"ok": true, "termin": {"id": 436804, "…": "…"}}
{"ok": true, "anzahl_neu": 3, "termine": [{"id": 436804, "datum": "2026-12-02", "plz": "74235", "ort": "Erlenbach"}]}
{"ok": true, "datei": "/pfad/436804.ics", "termin_id": 436804}
{"ok": true, "config": {"ort": "74072", "umkreis_km": 10}}
```

## Exit-Codes

| Code | Bedeutung |
|---|---|
| `0` | Erfolg, auch bei null Treffern (mit Hinweis) |
| `1` | allgemeiner Fehler (z. B. Termin nicht gefunden, Datei nicht schreibbar, ungültige Config) |
| `2` | Nutzungsfehler (unbekanntes Kommando/Flag, fehlendes Argument, ungültige Zahl/Datum, mehrdeutig ohne TTY) |
| `3` | Netz- oder Quellenfehler (DNS, Timeout, HTTP ≥ 400, unlesbare Antwort) |
| `4` | Login erforderlich (reserviert; wird derzeit nie zurückgegeben, da es keinen Login gibt) |
| `130` | Abbruch durch Strg+C (kein Traceback) |

Fehler nennen den nächsten Schritt, z. B.
`Mehrere Termine gefunden – ID angeben oder --erster verwenden.` oder
`Quelle nicht erreichbar – Internet prüfen oder später erneut versuchen.`

## Verhalten gegenüber der Quelle

- User-Agent: `blutspende-cli/<version> (+https://github.com/smlfg/blutspende-cli)`
- Maximal ein Request pro Sekunde.
- Antworten werden 10 Minuten unter `$XDG_CACHE_HOME/blutspende-cli/`
  zwischengespeichert.
- Nur GET; keine Cookies, keine Formulare, keine Reservierung.
