# blutspende-cli

DRK-Blutspendetermine im Terminal: Termine in der Nähe per PLZ/Ort und
Umkreis oder Landkreis finden, Zeitraum filtern, Details anzeigen,
Kalendereintrag (.ics) speichern, Reservierungslink anzeigen und per `watch`
neue Termine beobachten. Kein Login, keine schreibenden Aktionen.

## Schnellstart

```bash
pipx install git+https://github.com/smlfg/blutspende-cli
blutspende suche 74072
blutspende naechster Heilbronn
blutspende zeige Erlenbach
blutspende kalender 436804
blutspende watch 74072
blutspende suche --landkreis Zwickau
```

## Befehle

| Befehl | Zweck |
|---|---|
| `blutspende suche [PLZ\|ORT]` | Termine suchen (`--umkreis`, `--landkreis`, `--von`, `--bis`, `--limit`) |
| `blutspende naechster [PLZ\|ORT]` | frühesten Termin anzeigen |
| `blutspende zeige ID\|ORT` | Details anzeigen, bei mehreren Treffern auswählen (`--erster` für Agenten) |
| `blutspende kalender ID` | .ics-Datei speichern (`--datei PFAD`) |
| `blutspende watch [PLZ\|ORT]` | nur neue Termine seit dem letzten Aufruf melden |
| `blutspende config ort PLZ` | Standardort und Standardumkreis speichern |

## Beispiele

Termine im Umkreis von 20 km um eine PLZ, nur im Dezember:

```bash
blutspende suche 74072 --umkreis 20 --von 01.12.2026 --bis 31.12.2026
```

Alle Termine eines Landkreises (Name statt ID):

```bash
blutspende suche --landkreis Zwickau
```

Frühesten Termin für einen Ort finden:

```bash
blutspende naechster Heilbronn
```

Details zu einem Termin anzeigen; bei mehreren Orts-Treffern fragt das
Terminal nach der Nummer:

```bash
blutspende zeige Erlenbach
```

Kalendereintrag an einen eigenen Ort speichern:

```bash
blutspende kalender 436804 --datei ./blutspende.ics
```

## Konfiguration

- `BLUTSPENDE_BASE_URL` überschreibt die Basis-URL (für Tests/Fake-Server).
- `BLUTSPENDE_HEUTE` setzt das heutige Datum (`JJJJ-MM-TT`) für
  deterministische Läufe; im Normalbetrieb gilt das Systemdatum.
- `blutspende config ort 74072 --umkreis 20` speichert einen Standardort in
  `$XDG_CONFIG_HOME/blutspende-cli/config.json` (0600).
- Watch-Zustand: `$XDG_STATE_HOME/blutspende-cli/watch.json` (0600).
- Cache: `$XDG_CACHE_HOME/blutspende-cli/` (10 Minuten).
- Kalenderdateien: `$XDG_DATA_HOME/blutspende-cli/termine/<ID>.ics`.
- Kein Login, keine Cookies, keine schreibenden Aktionen. Reserviert wird
  ausschließlich über den angezeigten Link auf der DRK-Seite.

## Ausgabe und Exit-Codes

Im Terminal erscheint lesbarer Text. Mit `--json` (oder wenn stdout keine
TTY ist) kommt genau ein JSON-Objekt. `--version` und `--help` funktionieren.

| Code | Bedeutung |
|---|---|
| `0` | Erfolg, auch bei null Treffern (mit Hinweis) |
| `1` | allgemeiner Fehler (z. B. Termin nicht gefunden, Datei nicht schreibbar) |
| `2` | Nutzungsfehler (Argumente, ungültiges Datum, mehrdeutig ohne TTY) |
| `3` | Netz- oder Quellenfehler |
| `4` | Login erforderlich (reserviert, derzeit nicht verwendet) |
| `130` | Abbruch mit Strg+C |

Details stehen in [INTERFACE.md](INTERFACE.md), die Anforderungen in
[ANFORDERUNGEN.md](ANFORDERUNGEN.md).

## Hinweis

Dieses Werkzeug ist **inoffiziell** und gehört nicht zum Deutschen Roten
Kreuz. Es nutzt die öffentlich erreichbare RSS-Suche, die HTML-Suchseite,
die Detailseiten und den Kalender-Endpunkt von `drk-blutspende.de`. Eine
offizielle API gibt es nicht; Änderungen an der Website können das Werkzeug
brechen. Es wird ausschließlich lesend zugegriffen, höflich mit maximal
einem Request pro Sekunde und einem aussagekräftigen User-Agent.

## Entwicklung

Die UX-Spec steht in [docs/UX.md](docs/UX.md), Fixtures unter
`tests/fixtures/ux/`, Akzeptanztests unter `tests/acceptance/`. Gate:

```bash
python3 tests/harness/ux_check.py . --spec-only
```

## Lizenz

MIT, siehe [LICENSE](LICENSE). Copyright (c) 2026 smlfg.
