# UX-Spec: blutspende

`blutspende` findet DRK-Blutspendetermine im Terminal: per PLZ/Ort und Umkreis
oder Landkreis, mit Zeitraumfilter, Detailansicht, Kalendereintrag (.ics),
Reservierungslink und Watch fuer neue Termine. Alle Aktionen sind lesend
(GET); es gibt keinen Login und keine schreibende Web-Aktion.

## Meta

```ux-meta
{"tool": "blutspende",
 "install": "pipx install git+https://github.com/smlfg/blutspende-cli",
 "base_url_env": "BLUTSPENDE_BASE_URL",
 "env": {}}
```

## Sitzungen

### Installation und Termine suchen

Der erste Befehl nach der Installation sucht Termine um eine PLZ. Ohne
weitere Optionen gilt ein Umkreis von 10 km. Die Ausgabe zeigt Datum,
Uhrzeit, PLZ/Ort und Lokal, damit ein Mensch direkt sieht, ob der Termin
passt.

```ux-session
$ pipx install git+https://github.com/smlfg/blutspende-cli
$ blutspende suche 74072
< 3 Termine im Umkreis von 10 km um 74072
< 1) 02.12.2026, 14:00-19:00 Uhr: 74235 Erlenbach, Sulmtalhalle, Kultursaal
< 2) 03.12.2026, 14:30-19:30 Uhr: 74388 Talheim, Schloßberghalle
< 3) 23.12.2026, 14:00-19:00 Uhr: 74078 Heilbronn-Kirchhausen, Deutschordenhalle
! exit 0
```

### Nächsten Termin finden

`naechster` beantwortet die Frage „wann kann ich in der Nähe Blut spenden?“
mit genau einem Termin: dem frühesten Treffer.

```ux-session
$ blutspende naechster Heilbronn
< Nächster Termin:
< 23.12.2026, 14:00-19:00 Uhr: 74078 Heilbronn-Kirchhausen, Deutschordenhalle
! exit 0
```

### Termin anzeigen

`zeige` nimmt einen Ortsnamen positional. Bei mehreren Treffern folgt eine
nummerierte Auswahl im Terminal. Die Detailansicht nennt Datum, Lokal,
Straße, Uhrzeit, die Reservierungspflicht und den Reservierungslink. Der
Link wird nur angezeigt, nie automatisch geöffnet oder reserviert.

```ux-session
$ blutspende zeige Erlenbach
< Mehrere Termine gefunden:
< 1) 25.11.2026, 15:30-19:45 Uhr: 61352 Bad Homburg / Ober-Erlenbach
< 2) 02.12.2026, 14:00-19:00 Uhr: 74235 Erlenbach
< 3) 28.12.2026, 16:30-20:00 Uhr: 97714 OERLENBACH
< Welchen Termin anzeigen? [1-3]
> 2
< Blutspende in Erlenbach
< 02.12.2026
< Sulmtalhalle, Kultursaal
< Talstraße 21
< 14:00 - 19:00 Uhr
< Nur mit Terminreservierung!
< Termin reservieren: https://terminreservierung.blutspende.de/oeffentliche-spendeorte/7423511/termine?reservation_context=eyJkb25hdGlvbl90eXBlIjoiYmQiLCJkYXRlIjoiMjAyNi0xMi0wMiJ9
! exit 0
```

### Kalendereintrag speichern

`kalender` holt die .ics-Datei zu einer Termin-ID und speichert sie im
Datenverzeichnis des Nutzers (`$XDG_DATA_HOME/blutspende-cli/termine`).
Mit `--datei PFAD` lässt sich ein anderer Speicherort wählen.

```ux-session
$ blutspende kalender 436804
< Kalendereintrag gespeichert:
! exit 0
```

### Neue Termine beobachten

`watch` merkt sich die zuletzt gesehenen Termin-IDs unter
`$XDG_STATE_HOME/blutspende-cli` und meldet beim nächsten Aufruf nur neue
Termine. Der erste Aufruf meldet alle Treffer.

```ux-session
$ blutspende watch 74072
< 3 neue Termine seit dem letzten Aufruf
< 02.12.2026 74235 Erlenbach
< 03.12.2026 74388 Talheim
< 23.12.2026 74078 Heilbronn-Kirchhausen
! exit 0
```

### Suche im Landkreis

Statt PLZ/Ort kann ein Landkreis per Name angegeben werden. Der Name wird
über die Landkreisliste der Suchseite zur `county_id` aufgelöst (tippfehler-
tolerant, z. B. „Zwickau“ → 14524).

```ux-session
$ blutspende suche --landkreis Zwickau
< Landkreis Zwickau (14524)
< 3 Termine im Landkreis Zwickau
< 1) 24.11.2026, 11:00-13:00 Uhr: 08056 Zwickau, Plasmaspendezentrum Zwickau
< 2) 25.11.2026, 15:00-18:30 Uhr: 08412 Werdau, Werdau, Stadthalle
< 3) 26.11.2026, 11:00-13:00 Uhr: 08056 Zwickau, Plasmaspendezentrum Zwickau
! exit 0
```

## Lesende Routen

Alle Sitzungen kommen mit GET aus. Die RSS-Suche ist die Hauptquelle; die
HTML-Suche liefert die Landkreisliste, die Detailseite die Adresse und den
Reservierungslink, der Kalender-Endpunkt die .ics-Datei. Antworten sind
gekürzte Live-Antworten vom 24.11.2026 ohne Personendaten.

```ux-routes
[{"method": "GET", "path": "/blutspendetermine/termine.rss", "query_contains": "term=74072", "response": "tests/fixtures/ux/rss_74072.xml", "status": 200, "content_type": "application/rss+xml; charset=utf-8"},
 {"method": "GET", "path": "/blutspendetermine/termine.rss", "query_contains": "term=Heilbronn", "response": "tests/fixtures/ux/rss_heilbronn.xml", "status": 200, "content_type": "application/rss+xml; charset=utf-8"},
 {"method": "GET", "path": "/blutspendetermine/termine.rss", "query_contains": "term=Erlenbach", "response": "tests/fixtures/ux/rss_erlenbach.xml", "status": 200, "content_type": "application/rss+xml; charset=utf-8"},
 {"method": "GET", "path": "/blutspendetermine/termine.rss", "query_contains": "county_id=14524", "response": "tests/fixtures/ux/rss_zwickau.xml", "status": 200, "content_type": "application/rss+xml; charset=utf-8"},
 {"method": "GET", "path": "/blutspendetermine/termine", "query_contains": "term=Zwickau", "response": "tests/fixtures/ux/landkreise.html", "status": 200, "content_type": "text/html; charset=utf-8"},
 {"method": "GET", "path": "/blutspendetermine/termine/436804", "response": "tests/fixtures/ux/detail_436804.html", "status": 200, "content_type": "text/html; charset=utf-8"},
 {"method": "GET", "path": "/blutspendetermine/termine/436804/ical.ics", "response": "tests/fixtures/ux/termin_436804.ics", "status": 200, "content_type": "text/calendar"}]
```

## Schreibende Aktion

Keine. Das Tool reserviert nicht und sendet keine Formulare; der
Reservierungslink wird nur angezeigt. Deshalb gibt es keine `ux-formsteps`,
keine `credential_env` und keinen `login`-Befehl. `UX09` darf im vollen Gate
als SKIP (read-only) enden.
