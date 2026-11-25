# Pflicht-QA: blutspende

- Datum: 25.11.2026
- Version: `blutspende 0.1.0`
- Commit: `c1612f5` (HEAD, identisch mit dem per `pipx` installierten Commit)
- Installation: `scratch/pipx` (Python 3.14.7), Protokoll `scratch/qa/pipx-install.log`
- Live-Quelle: `https://www.drk-blutspende.de`, nur lesende GETs
- Fake-Server: `tests/harness/fake_server.py` mit den `ux-routes` aus `docs/UX.md`
- Terminal: `script -qec`, Ausgabe nach `scratch/qa/logs/*.log`
- Zusätzlich: `scratch/venv/bin/pytest -q` -> `62 passed`

## Ergebnis

**51 OK / 57 Prüfungen; 6 FAIL** (offene FAILs siehe unten).

## Prüfungen

| Prüfung | Befehl | Erwartet | Ergebnis | Beleg (gekürzt) |
|---|---|---|---|---|
| Frische Installation | `pipx install git+https://github.com/smlfg/blutspende-cli` (Orchestrator-Log) | Paket + App installiert | OK | `installed package blutspende-cli 0.1.0`; `- blutspende` |
| Installierter Commit | `direct_url.json` | HEAD `c1612f5` | OK | `"commit_id": "c1612f5f00aaaabe216191d8f45991a66dbeabd6"` |
| Befehl über PATH | `PATH=$PWD/scratch/pipx/bin:$PATH which blutspende` | `scratch/pipx/bin/blutspende` | OK | `/home/box/cli-daily/blutspende-cli/scratch/pipx/bin/blutspende` |
| Version | `blutspende --version` | `blutspende 0.1.0`, Exit 0 | OK | `blutspende 0.1.0` |
| Installierter Code = Repo | `diff -rq src/... scratch/pipx/.../site-packages/...` | keine Code-Unterschiede | OK | nur `__pycache__`-Dateien unterschiedlich |
| Hilfe | `blutspende --help` | alle Unterkommandos, Exit 0 | OK | `{suche,naechster,zeige,kalender,watch,config}` |
| Unterkommando-Hilfe | `blutspende suche --help` | Optionen, Exit 0 | OK | `--umkreis`, `--landkreis`, `--von`, `--bis`, `--limit` |
| Schnellstart 1 (Fake) | `blutspende suche 74072` | 3 Termine als Text | OK | `3 Termine im Umkreis von 10 km um 74072` |
| Schnellstart 2 (Fake) | `blutspende naechster Heilbronn` | frühester Termin | OK | `23.12.2026 ... Heilbronn-Kirchhausen` |
| Schnellstart 3 (Fake) | `blutspende zeige Erlenbach`, Antwort `2` | nummerierte Auswahl, Details | OK | `Welchen Termin anzeigen? [1-3]` -> `Blutspende in Erlenbach` |
| Schnellstart 4 (Fake) | `blutspende kalender 436804` | `.ics` gespeichert | OK | `Kalendereintrag gespeichert: .../436804.ics` |
| Schnellstart 5 (Fake) | `blutspende watch 74072` zweimal | 3 neu, dann 0 neu | OK | `3 neue Termine` / `0 neue Termine` |
| Schnellstart 6 (Fake) | `blutspende suche --landkreis Zwickau` | Landkreiszeile + Treffer | OK | `Landkreis Zwickau (14524)` |
| Live-Suche | `blutspende suche 74072` | 3 plausible Treffer | OK | IDs `436804`, `436838`, `436026`; PLZ `74235`, `74388`, `74078` |
| Live-Nächster | `blutspende naechster Heilbronn` | frühester Treffer | OK | `23.12.2026 ... (ID 436026)` |
| Live-Detail | `blutspende zeige 436804` | Ort, Datum, Lokal, Straße, Zeit, Reservierung | OK | `02.12.2026`, `Sulmtalhalle, Kultursaal`, `Talstraße 21`, `Nur mit Terminreservierung!` |
| Live-Detail per Ort | `blutspende zeige Erlenbach`, Antwort `2` | Auswahl und Detail | OK | 3 Kandidaten, Auswahl `2` -> `Blutspende in Erlenbach` |
| Live-Kalender | `blutspende kalender 436804 --datei .../live_pty.ics` | gültige `.ics` | OK | `BEGIN:VCALENDAR` ... `END:VCALENDAR` |
| Live-Watch | `blutspende watch 74072` zweimal | 3 neu, dann 0 neu | OK | `3 neue Termine` / `0 neue Termine` |
| Live-Landkreis | `blutspende suche --landkreis Zwickau` | Landkreiszeile + Treffer | OK | `Landkreis Zwickau (14524)`, 20 Treffer (Default-Limit) |
| Landkreis-Tippfehler | `blutspende suche --landkreis ZwickkAU` | `Zwickau` / `14524` | OK | `"landkreis": "Zwickau", "landkreis_id": "14524"` |
| Landkreis-Umlaut | `blutspende suche --landkreis Markisch-Oderland` | `Märkisch-Oderland` / `12064` | OK | `"landkreis": "Märkisch-Oderland"` |
| Leere Suche | `blutspende suche 99999` | 0 Treffer, Exit 0 | OK | `"anzahl": 0`, Exit 0 |
| Datumsfilter von/bis | `blutspende suche 74072 --von 01.12.2026 --bis 05.12.2026` | alle Treffer im Zeitraum | OK | 2 Treffer, `2026-12-02`, `2026-12-03` |
| Datumsfilter von (ISO) | `blutspende suche 74072 --von 2026-12-04` | alle Treffer >= 04.12. | OK | 1 Treffer, `2026-12-23` |
| Datumsfilter bis | `blutspende suche 74072 --bis 05.12.2026` | alle Treffer <= 05.12. | OK | 2 Treffer, alle <= `2026-12-05` |
| `--von` ohne Wert | `blutspende suche 74072 --von` | heute (`2026-11-25`) | OK | `"von": "2026-11-25"`, alle Treffer >= heute |
| Limit | `blutspende suche 74072 --limit 1` | genau 1 Treffer | OK | `"anzahl": 1` |
| Limit 0 | `blutspende suche 74072 --limit 0` | alle Treffer | OK | `"anzahl": 3` |
| Umkreis | `blutspende suche 74072 --umkreis 25` | mehr Treffer, 10-km-Treffer enthalten | OK | 20 Treffer; IDs aus 10 km sind Teilmenge |
| Config speichern | `blutspende config ort 74072 --umkreis 20` | Config 0600 | OK | `600 .../config.json`, `"umkreis_km": 20` |
| Config nutzen | `blutspende suche` ohne Ort | gespeicherter Ort/Umkreis | OK | `"ort": "74072"`, `"umkreis_km": 20` |
| Config löschen | `blutspende config loeschen` zweimal | idempotent | OK | `"geloescht": true`, dann `false` |
| Fehler: Datum | `blutspende suche 74072 --von 32.13.2026` | Exit 2, nächster Schritt | OK | `ungültiges Datum ... TT.MM.JJJJ oder JJJJ-MM-TT angeben.` |
| Fehler: Ort + Landkreis | `blutspende suche 74072 --landkreis Zwickau` | Exit 2 | OK | `PLZ/Ort und --landkreis schließen sich aus` |
| Fehler: Umkreis | `blutspende suche 74072 --umkreis 0` | Exit 2 | OK | `Umkreis muss zwischen 1 und 100 km liegen` |
| Fehler: Limit | `blutspende suche 74072 --limit -1` | Exit 2 | OK | `Limit muss 0 oder größer sein` |
| Fehler: Bis vor Von | `blutspende suche 74072 --von 05.12.2026 --bis 01.12.2026` | Exit 2 | OK | `--bis muss am oder nach --von liegen.` |
| Fehler: Config-Umkreis | `blutspende config ort 74072 --umkreis 0` | Exit 2 | OK | `Umkreis muss zwischen 1 und 100 km liegen` |
| Fehler: Kalender-ID | `blutspende kalender abc` | Exit 2, Beispiel | OK | `Termin-ID muss eine Zahl sein – z. B. ... 436804` |
| Fehler: Datei nicht schreibbar | `blutspende kalender 436804 --datei .../436804.ics/sub.ics` | Exit 1, nächster Schritt | OK | `nicht schreibbar – anderen Pfad mit --datei wählen.` |
| Fehler: Netz | `BLUTSPENDE_BASE_URL=http://127.0.0.1:1 blutspende suche 74072` | Exit 3, kein Traceback | OK | `Quelle nicht erreichbar – Internet prüfen oder später erneut versuchen.` |
| Fehler: Basis-URL | `BLUTSPENDE_BASE_URL=nonsense blutspende suche 74072` | Exit 3, kein Traceback | OK | `BLUTSPENDE_BASE_URL ist keine gültige http(s)-URL – Wert prüfen.` |
| Fehler: `BLUTSPENDE_HEUTE` | `BLUTSPENDE_HEUTE=2026-13-01 blutspende suche 74072` | Exit 2 | OK | `BLUTSPENDE_HEUTE ist kein gültiges Datum ...` |
| Fehler: unbekannter Landkreis | `blutspende suche --landkreis Xyzabc` | Exit 2, nächster Schritt | OK | `Landkreis 'Xyzabc' nicht gefunden – Namen prüfen oder PLZ/Ort angeben.` |
| Fehler: keine Config | `blutspende suche` ohne Config | Exit 2, Hinweis | OK | `Kein Suchort angegeben – ... blutspende config ort <PLZ> ausführen.` |
| Fehler: kaputte Config | Config mit `{broken`, `blutspende config zeigen` | Exit 1, nächster Schritt | OK | `... ist kein gültiges JSON – blutspende config loeschen ausführen.` |
| JSON im TTY | `blutspende --json suche 74072` | genau ein JSON-Objekt | OK | valides JSON, Exit 0 |
| JSON-Fehler im TTY | `blutspende --json zeige Erlenbach` | genau ein JSON-Objekt | OK | valides JSON, Exit 2 |
| Strg+C | `blutspende suche 74072` + `SIGINT` | Exit 130, kein Traceback | OK | `Abgebrochen.`, Exit 130 |
| EOF am Prompt | `blutspende zeige Erlenbach`, Eingabe `x` + EOF | Exit 2, kein Traceback | OK | `Eingabe abgebrochen – ID angeben oder --erster verwenden.` |
| Watch über Tageswechsel | `BLUTSPENDE_HEUTE=2026-11-24 blutspende watch 74072`, dann `2026-11-25` | zweiter Tag: 0 neu | FAIL | zweiter Tag meldet erneut `3 neue Termine` (State-Key enthält `von`) |
| `zeige` unbekannte ID | `blutspende --json zeige 123456789` | Exit 1, Termin nicht gefunden | FAIL | `{"ok": true, "termin": {"datum": null, ...}}`, Exit 0 |
| `kalender` unbekannte ID | `blutspende --json kalender 123456789 --datei .../bad_123456789.ics` | Exit 1/3, keine Datei | FAIL | `{"ok": true, "datei": ...}`, Exit 0; Datei beginnt mit `<!DOCTYPE html>` |
| `zeige` mehrdeutig ohne TTY | `blutspende --json zeige Erlenbach` | Exit 2 mit Kandidatenliste im JSON-Fehlerobjekt | FAIL | Fehlerobjekt nur mit `code`/`art`/`nachricht`, keine Kandidaten |
| Detail ohne Hausnummer | `blutspende zeige 436838` | Straße `In den Hofwiesen` | FAIL | Ausgabe: `Schloßberghalle`, dann direkt Uhrzeit; Straße fehlt |
| Cache-Verzeichnisrechte | `stat -c '%a' $XDG_CACHE_HOME/blutspende-cli` | `700` | FAIL | `755` (nur Unterordner `antworten` ist `700`) |

## Offene FAILs

1. **`watch` über Tageswechsel**: Der Zustandsschlüssel enthält das implizite
   `von` (heute). Dadurch meldet `watch` am nächsten Tag alle bereits gesehenen
   Termine erneut als neu. Beleg: gleicher Befehl mit `BLUTSPENDE_HEUTE`
   24.11. und 25.11. liefert beide Male `3 neue Termine`; die State-Datei
   enthält zwei Schlüssel mit demselben Termin-IDs-Satz.
2. **`zeige` unbekannte ID**: Die Detailseite antwortet mit 302 auf die Suche,
   der Client folgt dem Redirect und liefert ein leeres Erfolgsobjekt mit
   Exit 0 statt „Termin nicht gefunden“ (Exit 1). Beleg:
   `blutspende --json zeige 123456789` -> `"ok": true`, `"datum": null`.
3. **`kalender` unbekannte ID**: Der iCal-Endpunkt antwortet ebenfalls mit
   einem Redirect auf die Suchseite; der Client speichert die HTML-Seite als
   `.ics` und meldet Erfolg. Beleg: `bad_123456789.ics` beginnt mit
   `<!DOCTYPE html>`, Exit 0.
4. **`zeige` mehrdeutig ohne TTY**: `INTERFACE.md` verlangt bei mehreren
   Treffern ohne TTY eine Kandidatenliste im JSON-Fehlerobjekt. Die Ausgabe
   enthält nur `code`, `art`, `nachricht`; die Kandidaten fehlen.
5. **Detailseite ohne Hausnummer**: Bei Adressen ohne Ziffer in der Straße
   (`In den Hofwiesen`) wird die Straße nicht erkannt und in der Detailansicht
   weggelassen. Beleg: `blutspende zeige 436838` zeigt `Schloßberghalle` und
   direkt die Uhrzeit.
6. **Cache-Verzeichnisrechte**: `INTERFACE.md` fordert für
   `$XDG_CACHE_HOME/blutspende-cli/` das Recht `0700`. Angelegt wird `0755`;
   nur der Unterordner `antworten` ist `0700`.

## Nicht als FAIL gewertet

- `--json` wird als globale Option nur vor dem Unterkommando akzeptiert
  (`blutspende --json suche ...`). Die Schnittstelle dokumentiert diese
  Reihenfolge; `blutspende suche ... --json` endet mit Exit 2.
- `blutspende` ohne Argument und `blutspende unbekannt` nennen die gültigen
  Unterkommandos, aber keinen expliziten nächsten Befehl. Das ist für einen
  Nutzungsfehler ausreichend.
- `--landkreis ""` wird wie „nicht gesetzt“ behandelt und fällt auf den
  gespeicherten Standardort zurück. Kein dokumentierter Anwendungsfall.
