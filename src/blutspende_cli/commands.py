"""Unterkommandos: suche, naechster, zeige, kalender, watch, config."""

from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

from .client import Client
from .config import (
    data_dir,
    delete_config,
    load_config,
    load_watch,
    save_config,
    save_watch,
    validate_umkreis,
)
from .errors import BlutspendeError, NotFoundError, UsageError
from .parsers import Termin

MITTEILUNG_LEER = "Keine Termine gefunden – Umkreis oder Zeitraum vergrößern."
HINWEIS_KAPPUNG = (
    "Hinweis: Die Quelle liefert maximal 100 Termine – "
    "Zeitraum, Umkreis oder Landkreis eingrenzen."
)


class Ausgabe:
    def __init__(self, json_mode: bool) -> None:
        self.json_mode = json_mode

    def text(self, zeilen: list[str]) -> None:
        if not self.json_mode:
            print("\n".join(zeilen))

    def json(self, obj: dict) -> None:
        print(json.dumps(obj, ensure_ascii=False))

    def ergebnis(self, obj: dict, zeilen: list[str]) -> None:
        if self.json_mode:
            self.json(obj)
        else:
            self.text(zeilen)


def _heute() -> date:
    raw = os.environ.get("BLUTSPENDE_HEUTE", "").strip()
    if not raw:
        return date.today()
    try:
        return date.fromisoformat(raw)
    except ValueError as exc:
        raise UsageError(
            "BLUTSPENDE_HEUTE ist kein gültiges Datum (JJJJ-MM-TT) – Wert prüfen."
        ) from exc


def _datum(wert: str, label: str) -> date:
    for fmt in ("%d.%m.%Y", "%Y-%m-%d"):
        try:
            from datetime import datetime

            return datetime.strptime(wert.strip(), fmt).date()
        except ValueError:
            continue
    raise UsageError(
        f"{label}: ungültiges Datum {wert!r} – TT.MM.JJJJ oder JJJJ-MM-TT angeben."
    )


def _von_bis(args: Any) -> tuple[date, date | None]:
    heute = _heute()
    roh_von = getattr(args, "von", None)
    von = heute if roh_von in (None, "") else _datum(roh_von, "--von")
    roh_bis = getattr(args, "bis", None)
    bis = _datum(roh_bis, "--bis") if roh_bis else None
    if bis is not None and bis < von:
        raise UsageError("--bis muss am oder nach --von liegen.")
    return von, bis


@dataclass
class SuchErgebnis:
    termine: list[Termin]
    term: str | None
    umkreis: int
    landkreis_name: str | None
    landkreis_id: str | None
    von: date
    bis: date | None
    gekappt: bool

    def abfrage_json(self) -> dict:
        return {
            "ort": self.term,
            "umkreis_km": self.umkreis,
            "landkreis": self.landkreis_name,
            "landkreis_id": self.landkreis_id,
            "von": self.von.isoformat(),
            "bis": self.bis.isoformat() if self.bis else None,
        }


def _termine_aus_args(
    args: Any, *, standard_umkreis: int, standard_limit: int
) -> tuple[Client, SuchErgebnis]:
    landkreis_name = getattr(args, "landkreis", None)
    suchbegriff = getattr(args, "suchbegriff", None)
    if landkreis_name and suchbegriff:
        raise UsageError("PLZ/Ort und --landkreis schließen sich aus – nur eines angeben.")
    config = load_config()
    if not landkreis_name and not suchbegriff:
        suchbegriff = config.get("ort")
        if not suchbegriff:
            raise UsageError(
                "Kein Suchort angegeben – PLZ/Ort nennen oder "
                "`blutspende config ort <PLZ>` ausführen."
            )
    umkreis = getattr(args, "umkreis", None)
    if umkreis is None:
        umkreis = config.get("umkreis_km", standard_umkreis)
    umkreis = validate_umkreis(int(umkreis))
    von, bis = _von_bis(args)
    limit = getattr(args, "limit", standard_limit)
    if limit is None:
        limit = standard_limit
    limit = int(limit)
    if limit < 0:
        raise UsageError("--limit muss 0 oder größer sein.")

    client = Client()
    landkreis_id: str | None = None
    kanonisch: str | None = None
    try:
        if landkreis_name:
            landkreis_id, kanonisch = client.loese_landkreis(landkreis_name)
        roh = client.suche_rss(
            term=None if landkreis_name else suchbegriff,
            county_id=landkreis_id,
            radius=umkreis,
            von=von,
            bis=bis,
        )
    except BaseException:
        client.close()
        raise

    termine = [t for t in roh if t.datum >= von and (bis is None or t.datum <= bis)]
    termine.sort(key=lambda t: (t.datum, t.von, t.id))
    gekappt = len(roh) >= 100
    if limit > 0:
        termine = termine[:limit]
    ergebnis = SuchErgebnis(
        termine=termine,
        term=suchbegriff,
        umkreis=umkreis,
        landkreis_name=kanonisch,
        landkreis_id=landkreis_id,
        von=von,
        bis=bis,
        gekappt=gekappt,
    )
    return client, ergebnis


def _anzahl_text(anzahl: int) -> str:
    return "1 Termin" if anzahl == 1 else f"{anzahl} Termine"


def _termin_zeile(termin: Termin, nummer: int | None = None) -> str:
    prefix = f"{nummer}) " if nummer is not None else ""
    lokal = f", {termin.lokal}" if termin.lokal else ""
    return (
        f"{prefix}{termin.datum_text}, {termin.von}-{termin.bis} Uhr: "
        f"{termin.plz} {termin.ort}{lokal} (ID {termin.id})"
    )


def _kandidat_zeile(termin: Termin, nummer: int) -> str:
    return (
        f"{nummer}) {termin.datum_text}, {termin.von}-{termin.bis} Uhr: "
        f"{termin.plz} {termin.ort}"
    )


def _suche_zeilen(ergebnis: SuchErgebnis) -> list[str]:
    zeilen: list[str] = []
    if ergebnis.landkreis_name:
        zeilen.append(
            f"Landkreis {ergebnis.landkreis_name} ({ergebnis.landkreis_id})"
        )
    if not ergebnis.termine:
        zeilen.append(MITTEILUNG_LEER)
        return zeilen
    if ergebnis.landkreis_name:
        zeilen.append(
            f"{_anzahl_text(len(ergebnis.termine))} im Landkreis "
            f"{ergebnis.landkreis_name}"
        )
    else:
        zeilen.append(
            f"{_anzahl_text(len(ergebnis.termine))} im Umkreis von "
            f"{ergebnis.umkreis} km um {ergebnis.term}"
        )
    for nummer, termin in enumerate(ergebnis.termine, start=1):
        zeilen.append(_termin_zeile(termin, nummer))
    if ergebnis.gekappt:
        zeilen.append(HINWEIS_KAPPUNG)
    return zeilen


def cmd_suche(args: Any, ausgabe: Ausgabe) -> int:
    client, ergebnis = _termine_aus_args(
        args, standard_umkreis=10, standard_limit=20
    )
    client.close()
    obj = {
        "ok": True,
        "abfrage": ergebnis.abfrage_json(),
        "anzahl": len(ergebnis.termine),
        "gekappt": ergebnis.gekappt,
        "termine": [termin.als_json() for termin in ergebnis.termine],
    }
    ausgabe.ergebnis(obj, _suche_zeilen(ergebnis))
    return 0


def cmd_naechster(args: Any, ausgabe: Ausgabe) -> int:
    client, ergebnis = _termine_aus_args(
        args, standard_umkreis=10, standard_limit=1
    )
    client.close()
    if not ergebnis.termine:
        ausgabe.ergebnis(
            {"ok": True, "abfrage": ergebnis.abfrage_json(), "termin": None},
            [MITTEILUNG_LEER],
        )
        return 0
    termin = ergebnis.termine[0]
    ausgabe.ergebnis(
        {"ok": True, "abfrage": ergebnis.abfrage_json(), "termin": termin.als_json()},
        ["Nächster Termin:", _termin_zeile(termin)],
    )
    return 0


def _detail_obj(detail: dict) -> dict:
    datum = detail.get("datum")
    return {
        "id": detail.get("id"),
        "datum": datum.isoformat() if isinstance(datum, date) else None,
        "wochentag": detail.get("wochentag", ""),
        "von": detail.get("von", ""),
        "bis": detail.get("bis", ""),
        "plz": detail.get("plz", ""),
        "ort": detail.get("ort", ""),
        "lokal": detail.get("lokal", ""),
        "strasse": detail.get("strasse", ""),
        "reservierung_pflicht": bool(detail.get("reservierung_pflicht")),
        "reservierung_url": detail.get("reservierung_url"),
        "detail_url": detail.get("detail_url", ""),
        "ical_url": detail.get("ical_url", ""),
    }


def _detail_zeilen(detail: dict) -> list[str]:
    titel = detail.get("titel") or f"Blutspende in {detail.get('ort') or 'Termin'}"
    zeilen = [titel]
    if detail.get("datum_text"):
        zeilen.append(detail["datum_text"])
    if detail.get("lokal"):
        zeilen.append(detail["lokal"])
    if detail.get("strasse"):
        zeilen.append(detail["strasse"])
    if detail.get("von") and detail.get("bis"):
        zeilen.append(f"{detail['von']} - {detail['bis']} Uhr")
    if detail.get("reservierung_pflicht"):
        zeilen.append("Nur mit Terminreservierung!")
    if detail.get("reservierung_url"):
        zeilen.append(f"Termin reservieren: {detail['reservierung_url']}")
    return zeilen


def _kandidaten_auswahl(kandidaten: list[Termin]) -> Termin:
    if not sys.stdin.isatty():
        print("Mehrere Termine gefunden:")
        for nummer, termin in enumerate(kandidaten, start=1):
            print(_kandidat_zeile(termin, nummer))
        raise UsageError(
            "Mehrere Termine gefunden – ID angeben oder --erster verwenden."
        )
    print("Mehrere Termine gefunden:")
    for nummer, termin in enumerate(kandidaten, start=1):
        print(_kandidat_zeile(termin, nummer))
    while True:
        try:
            antwort = input(f"Welchen Termin anzeigen? [1-{len(kandidaten)}] ")
        except EOFError as exc:
            raise UsageError(
                "Eingabe abgebrochen – ID angeben oder --erster verwenden."
            ) from exc
        antwort = antwort.strip()
        if not antwort:
            continue
        if not antwort.isdigit():
            print(f"Bitte eine Zahl von 1 bis {len(kandidaten)} eingeben.")
            continue
        auswahl = int(antwort)
        if 1 <= auswahl <= len(kandidaten):
            return kandidaten[auswahl - 1]
        print(f"Bitte eine Zahl von 1 bis {len(kandidaten)} eingeben.")


def _finde_termin(
    ziel: str, args: Any, ausgabe: Ausgabe
) -> tuple[Client, Termin | dict]:
    if ziel.isdigit():
        client = Client()
        return client, client.detail(int(ziel))

    umkreis = getattr(args, "umkreis", None)
    if umkreis is None:
        umkreis = 25
    umkreis = validate_umkreis(int(umkreis))
    von = _heute()
    client = Client()
    try:
        roh = client.suche_rss(
            term=ziel, county_id=None, radius=umkreis, von=von, bis=None
        )
    except BaseException:
        client.close()
        raise
    kandidaten = [t for t in roh if t.datum >= von]
    kandidaten.sort(key=lambda t: (t.datum, t.von, t.id))
    if not kandidaten:
        client.close()
        raise NotFoundError(
            f"Keine Termine zu {ziel!r} gefunden – anderen Ort oder ID versuchen."
        )
    if len(kandidaten) == 1:
        return client, client.detail(kandidaten[0].id)
    if getattr(args, "erster", False):
        return client, client.detail(kandidaten[0].id)
    if ausgabe.json_mode:
        raise UsageError(
            "Mehrere Termine gefunden – ID angeben oder --erster verwenden."
        )
    auswahl = _kandidaten_auswahl(kandidaten)
    return client, client.detail(auswahl.id)


def cmd_zeige(args: Any, ausgabe: Ausgabe) -> int:
    client, detail = _finde_termin(args.ziel, args, ausgabe)
    client.close()
    ausgabe.ergebnis(
        {"ok": True, "termin": _detail_obj(detail)}, _detail_zeilen(detail)
    )
    return 0


def cmd_kalender(args: Any, ausgabe: Ausgabe) -> int:
    wert = str(args.termin_id).strip()
    if not wert.isdigit():
        raise UsageError("Termin-ID muss eine Zahl sein – z. B. `blutspende kalender 436804`.")
    termin_id = int(wert)
    ziel = Path(args.datei).expanduser() if args.datei else None
    if ziel is not None and ziel.is_dir():
        ziel = ziel / f"{termin_id}.ics"
    if ziel is None:
        ziel = data_dir() / "termine" / f"{termin_id}.ics"
    client = Client()
    try:
        inhalt = client.ical(termin_id)
    finally:
        client.close()
    try:
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
        os.chmod(ziel, 0o644)
    except OSError as exc:
        raise BlutspendeError(
            f"Datei {ziel} nicht schreibbar – anderen Pfad mit --datei wählen."
        ) from exc
    ausgabe.ergebnis(
        {"ok": True, "datei": str(ziel), "termin_id": termin_id},
        ["Kalendereintrag gespeichert:", str(ziel)],
    )
    return 0


def _watch_key(ergebnis: SuchErgebnis) -> str:
    return json.dumps(
        {
            "term": ergebnis.term,
            "landkreis_id": ergebnis.landkreis_id,
            "umkreis": ergebnis.umkreis,
            "von": ergebnis.von.isoformat(),
            "bis": ergebnis.bis.isoformat() if ergebnis.bis else None,
        },
        sort_keys=True,
        ensure_ascii=False,
    )


def cmd_watch(args: Any, ausgabe: Ausgabe) -> int:
    client, ergebnis = _termine_aus_args(
        args, standard_umkreis=10, standard_limit=20
    )
    client.close()
    key = _watch_key(ergebnis)
    zustand = load_watch()
    abfragen = zustand.get("abfragen")
    if not isinstance(abfragen, dict):
        abfragen = {}
    eintrag = abfragen.get(key)
    gesehen: set[int] = set()
    if isinstance(eintrag, dict):
        for wert in eintrag.get("ids", []):
            if isinstance(wert, int) and not isinstance(wert, bool):
                gesehen.add(wert)
    neu = [termin for termin in ergebnis.termine if termin.id not in gesehen]
    alle = gesehen | {termin.id for termin in ergebnis.termine}
    abfragen[key] = {
        "ids": sorted(alle),
        "aktualisiert": _heute().isoformat(),
    }
    save_watch({"abfragen": abfragen})

    if neu:
        zeilen = [f"{len(neu)} neue Termine seit dem letzten Aufruf"]
        for termin in neu:
            zeilen.append(
                f"{termin.datum_text} {termin.plz} {termin.ort}"
            )
    else:
        zeilen = ["0 neue Termine seit dem letzten Aufruf"]
    ausgabe.ergebnis(
        {
            "ok": True,
            "anzahl_neu": len(neu),
            "termine": [
                {
                    "id": termin.id,
                    "datum": termin.datum.isoformat(),
                    "plz": termin.plz,
                    "ort": termin.ort,
                }
                for termin in neu
            ],
        },
        zeilen,
    )
    return 0


def cmd_config_ort(args: Any, ausgabe: Ausgabe) -> int:
    ort = str(args.wert).strip()
    if not ort:
        raise UsageError("PLZ/Ort darf nicht leer sein – z. B. `blutspende config ort 74072`.")
    config = load_config()
    config["ort"] = ort
    umkreis = getattr(args, "umkreis", None)
    if umkreis is not None:
        config["umkreis_km"] = validate_umkreis(int(umkreis))
    save_config(config)
    zeilen = [f"Standardort gespeichert: {config['ort']}"]
    if "umkreis_km" in config:
        zeilen.append(f"Umkreis: {config['umkreis_km']} km")
    ausgabe.ergebnis({"ok": True, "config": config}, zeilen)
    return 0


def cmd_config_zeigen(args: Any, ausgabe: Ausgabe) -> int:
    config = load_config()
    if config:
        zeilen = []
        if "ort" in config:
            zeilen.append(f"Ort: {config['ort']}")
        if "umkreis_km" in config:
            zeilen.append(f"Umkreis: {config['umkreis_km']} km")
    else:
        zeilen = ["Kein Standardort gesetzt – `blutspende config ort <PLZ>` ausführen."]
    ausgabe.ergebnis({"ok": True, "config": config}, zeilen)
    return 0


def cmd_config_loeschen(args: Any, ausgabe: Ausgabe) -> int:
    entfernt = delete_config()
    text = (
        "Config gelöscht."
        if entfernt
        else "Keine Config vorhanden – nichts zu löschen."
    )
    ausgabe.ergebnis({"ok": True, "geloescht": entfernt}, [text])
    return 0
