# UX-Gate-Bericht

- Datum: 25.11.2026
- Tool: `blutspende`
- Repo: `smlfg/blutspende-cli`

## Ergebnisse

| Gate | Befehl | Exit-Code | Ergebnis |
|---|---|---|---|
| UX-Check | `python3 tests/harness/ux_check.py . --report scratch/ux_check.md` | 0 | PASS |
| UX-Session | `python3 tests/harness/ux_session.py . --report scratch/ux_session.md` | 0 | PASS |

## UX-Check

| ID | Ergebnis | Befund |
|---|---|---|
| UX00 | PASS | 7 Request(s) am Fake-Server, keine Fremdverbindung |
| UX01 | PASS | docs/UX.md: 6 Sitzungen, 0 formsteps |
| UX02 | PASS | keine Credential-Env-Variablen gefunden |
| UX03 | PASS | --help, --version und 6 Unterkommandos mit Exit 0 |
| UX04 | PASS | 6 Unterkommandos ohne Pflicht-Option statt positional |
| UX05 | PASS | 6 Sitzungen ohne JSON/Traceback im TTY |
| UX06 | PASS | Schnellstart: 6 Tool-Befehle, Installation passt |
| UX07 | PASS | keine ux-formsteps, keine schreibende Aktion |
| UX08 | PASS | keine ux-formsteps, keine schreibende Aktion |
| UX09 | SKIP | keine schreibende Sitzung |

## UX-Session

| Sitzung | Lauf | Ergebnis | Befund |
|---|---|---|---|
| Installation und Termine suchen | 1 | PASS | OK |
| Nächsten Termin finden | 1 | PASS | OK |
| Termin anzeigen | 1 | PASS | OK |
| Kalendereintrag speichern | 1 | PASS | OK |
| Neue Termine beobachten | 1 | PASS | OK |
| Suche im Landkreis | 1 | PASS | OK |
