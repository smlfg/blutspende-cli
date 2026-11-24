# Anforderungen: blutspende

## Zweck

`blutspende` bringt die Blutspendetermine des Deutschen Roten Kreuzes (DRK)
ins Terminal. Menschen und Agenten beantworten damit die Frage „Wann kann ich
in meiner Nähe Blut spenden?“ ohne Browser, ohne Konto und ohne App.

Das Werkzeug ist ein reines Lesewerkzeug. Es reserviert keinen Termin, sendet
keine Formulare und meldet sich nirgends an. Der Reservierungslink wird nur
angezeigt.

## Nutzer und Aufgaben

| Nutzer | Aufgabe |
|---|---|
| Blutspender | Termine in der Nähe der eigenen PLZ oder des eigenen Ortes finden |
| Pendler und Studierende | den frühesten passenden Termin im Umkreis sehen |
| Menschen mit Zeitfenster | Termine nach Zeitraum (`--von`, `--bis`) filtern |
| Menschen mit Landkreisbezug | alle Termine eines Landkreises nach Namen suchen |
| Kalendernutzer | einen Termin als `.ics`-Datei speichern |
| Wiederkehrer | per `watch` nur neue Termine seit dem letzten Aufruf sehen |
| Agenten und Skripte | dieselben Daten stabil als JSON erhalten |

Kernaufgaben in der Reihenfolge der UX-Spezifikation (`docs/UX.md`):

1. Installation und Terminsuche per PLZ bzw. Ort.
2. Frühesten Termin ausgeben (`naechster`).
3. Termin anzeigen, bei mehreren Treffern auswählen (`zeige`).
4. Kalendereintrag speichern (`kalender`).
5. Neue Termine seit dem letzten Aufruf melden (`watch`).
6. Suche nach Landkreisnamen (`suche --landkreis`).

## Nachfrage

Stand: 24.11.2026 (Demand-Gate).

- GitHub, Glama, mcp.so, Smithery, PyPI und npm lieferten für „blutspende“
  keine bestehende CLI oder keinen MCP-Server.
- Eigenbauten belegen den Bedarf:
  - `Bouni/drkblutspende` (★8, Home-Assistant/HACS) nutzt
    `spenderservice.net/termine.rss`; der Feed war am 24.11.2026 nicht mehr
    erreichbar (404). Ein vergleichbares Werkzeug ist damit kaputt.
  - `Betelgeitze/blutspender` (Telegram-Bot, Push-Meldungen, August 2026).
  - `RSS-Bridge/DRKBlutspendeBridge` (RSS-Brücke, November 2024).
  - `t-huyeng/drk-blutspendetermine-api` (inoffizielle OpenAPI-Beschreibung).
- Im DRK-Spenderforum wurden Push- und Erinnerungswünsche geäußert
  (17.09.2026 und 03.10.2026).
- Reddit `r/Ratschlag`: Diskussion mit 35 Upvotes und 228 Kommentaren.
- Eine offizielle DRK-API ist nicht bekannt.

## Datenquelle

Basis-URL: `https://www.drk-blutspende.de` (per `BLUTSPENDE_BASE_URL`
überschreibbar, z. B. für den Fake-Server der Tests).

| Zweck | Request | Antwort |
|---|---|---|
| Terminsuche (Hauptquelle) | `GET /blutspendetermine/termine.rss?term=…&radius=…&date_from=…&date_to=…&county_id=…` | RSS 2.0 mit Termin-Items |
| Landkreis auflösen | `GET /blutspendetermine/termine?term=…&radius=…` | HTML-Suchseite mit Landkreis-`<select>` |
| Detailansicht | `GET /blutspendetermine/termine/<id>` | HTML mit Datum, Adresse, Lokal, Uhrzeit, Hinweis, Reservierungslink |
| Kalendereintrag | `GET /blutspendetermine/termine/<id>/ical.ics` | `text/calendar` |

RSS-Item-Format (live erkundet am 24.11.2026):

- `title`: `74235 Erlenbach am 02.12.2026, 14:00 Uhr bis 19:00 Uhr`
- `description`: `- Talstraße 21 - Sulmtalhalle, Kultursaal` (Straße, Lokal)
- `link`/`guid`: `https://www.drk-blutspende.de/blutspendetermine/termine/436804`

Die Landkreise stehen als `<option value="14524">Zwickau</option>` in der
Suchseite. Der Name wird im Werkzeug aufgelöst, nicht vom Nutzer als ID
erwartet.

## Grenzen

- **Inoffiziell:** Es gibt keine zugesicherte DRK-API. RSS, HTML und
  Kalender-Endpunkt können sich jederzeit ändern.
- **Nur lesend live getestet:** Am 24.11.2026 wurden ausschließlich GET-
  Requests auf öffentliche Seiten ausgeführt. Das Werkzeug reserviert nicht,
  sendet keine Formulare und nutzt keinen Login.
- **Keine Garantie auf Vollständigkeit:** Die RSS-Suche liefert höchstens
  100 Treffer (Kappung). Für vollständige Listen müssen Zeitraum, Umkreis
  oder Landkreis eingegrenzt werden.
- **Keine Geokodierung:** Der Umkreis bezieht sich auf die DRK-Suche. Eine
  eigene Koordinaten- oder Routenberechnung findet nicht statt.
- **Höflichkeit:** maximal ein Request pro Sekunde, Cache für 10 Minuten,
  aussagekräftiger User-Agent mit Repository-URL.
- **Datenschutz:** Keine Konten, keine Cookies, keine Personendaten. Der
  Watch-Zustand enthält nur Termin-IDs und liegt lokal mit Rechten 0600.

## Nicht-Ziele

- Automatische Reservierung oder Anmeldung zu einem Termin.
- E-Mail-/SMS-Erinnerungen über die DRK-Formulare.
- Push-Benachrichtigungen oder ein dauerhaft laufender Hintergrunddienst.
- Eigene Karten, Navigation oder Entfernungsberechnung.
