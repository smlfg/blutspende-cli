# blutspende-cli

DRK-Blutspendetermine im Terminal: Termine in der Nähe per PLZ/Ort und
Umkreis oder Landkreis finden, Zeitraum filtern, Details anzeigen,
Kalendereintrag (.ics) speichern und neue Termine beobachten.

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
| `blutspende zeige ID\|ORT` | Details anzeigen, bei mehreren Treffern Auswahl (`--erster`) |
| `blutspende kalender ID` | .ics-Datei speichern (`--datei PFAD`) |
| `blutspende watch [PLZ\|ORT]` | nur neue Termine seit dem letzten Aufruf |

Die Ausgabe ist im Terminal lesbar. Mit `--json` (oder wenn stdout keine
TTY ist) kommt genau ein JSON-Objekt. `--version` und `--help` funktionieren.

## Konfiguration

- `BLUTSPENDE_BASE_URL` überschreibt die Basis-URL (für Tests/Fake-Server).
- Watch-Zustand liegt unter `$XDG_STATE_HOME/blutspende-cli` (0600).
- Cache liegt unter `$XDG_CACHE_HOME/blutspende-cli` (10 Minuten).
- Kein Login, keine Cookies, keine schreibenden Aktionen. Reserviert wird
  nur über den angezeigten Link auf der DRK-Seite.

## Entwicklung

Die UX-Spec steht in [docs/UX.md](docs/UX.md), Fixtures unter
`tests/fixtures/ux/`. Gate:

```bash
python3 tests/harness/ux_check.py . --spec-only
```
