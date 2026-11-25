"""argparse-Einstieg mit Fehlervertrag und JSON-Ausgabe."""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

from . import __version__
from .commands import (
    Ausgabe,
    cmd_config_loeschen,
    cmd_config_ort,
    cmd_config_zeigen,
    cmd_kalender,
    cmd_naechster,
    cmd_suche,
    cmd_watch,
    cmd_zeige,
)
from .errors import BlutspendeError, NotFoundError, SourceError, UsageError


class Parser(argparse.ArgumentParser):
    def error(self, message: str):  # noqa: D401 - argparse-Vertrag
        raise UsageError(message)


def _umkreis(wert: str) -> int:
    try:
        zahl = int(wert)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("Umkreis muss eine ganze Zahl sein") from exc
    if not 1 <= zahl <= 100:
        raise argparse.ArgumentTypeError("Umkreis muss zwischen 1 und 100 km liegen")
    return zahl


def _limit(wert: str) -> int:
    try:
        zahl = int(wert)
    except (TypeError, ValueError) as exc:
        raise argparse.ArgumentTypeError("Limit muss eine ganze Zahl sein") from exc
    if zahl < 0:
        raise argparse.ArgumentTypeError("Limit muss 0 oder größer sein")
    return zahl


def _suchoptionen(parser: argparse.ArgumentParser, *, mit_limit: bool) -> None:
    parser.add_argument(
        "suchbegriff",
        nargs="?",
        metavar="PLZ|ORT",
        help="PLZ oder Ortsname (ohne Angabe gilt der gespeicherte Standardort)",
    )
    parser.add_argument(
        "--umkreis",
        type=_umkreis,
        metavar="KM",
        help="Umkreis in km (1-100, Standard 10)",
    )
    parser.add_argument(
        "--landkreis",
        metavar="NAME",
        help="Landkreisname statt PLZ/Ort; wird zur county_id aufgelöst",
    )
    parser.add_argument(
        "--von",
        nargs="?",
        const="",
        metavar="DATUM",
        help="frühester Termin (TT.MM.JJJJ oder JJJJ-MM-TT; ohne Wert heute)",
    )
    parser.add_argument(
        "--bis",
        metavar="DATUM",
        help="spätester Termin (TT.MM.JJJJ oder JJJJ-MM-TT)",
    )
    if mit_limit:
        parser.add_argument(
            "--limit",
            type=_limit,
            default=20,
            metavar="N",
            help="höchstens N Treffer (Standard 20, 0 = alle)",
        )


def build_parser() -> Parser:
    parser = Parser(
        prog="blutspende",
        description=(
            "DRK-Blutspendetermine im Terminal finden: Termine, Details, "
            "Kalendereintrag, Watch. Nur lesend, kein Login."
        ),
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"blutspende {__version__}",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Ausgabe als genau ein JSON-Objekt (auch im Terminal)",
    )
    unter = parser.add_subparsers(
        dest="kommando",
        metavar="{suche,naechster,zeige,kalender,watch,config}",
        required=True,
    )

    p_suche = unter.add_parser(
        "suche", help="Termine in der Nähe oder im Landkreis suchen"
    )
    _suchoptionen(p_suche, mit_limit=True)
    p_suche.set_defaults(func=cmd_suche)

    p_naechster = unter.add_parser(
        "naechster", help="den frühesten passenden Termin anzeigen"
    )
    _suchoptionen(p_naechster, mit_limit=False)
    p_naechster.set_defaults(func=cmd_naechster)

    p_zeige = unter.add_parser(
        "zeige", help="Details zu einer Termin-ID oder einem Ort anzeigen"
    )
    p_zeige.add_argument(
        "ziel",
        metavar="ID|ORT",
        help="Termin-ID (Zahl) oder Ortsname",
    )
    p_zeige.add_argument(
        "--erster",
        action="store_true",
        help="bei mehreren Treffern den ersten ohne Rückfrage nehmen",
    )
    p_zeige.add_argument(
        "--umkreis",
        type=_umkreis,
        metavar="KM",
        help="Umkreis für die Namenssuche (Standard 25)",
    )
    p_zeige.set_defaults(func=cmd_zeige)

    p_kalender = unter.add_parser(
        "kalender", help="Kalendereintrag (.ics) zu einer Termin-ID speichern"
    )
    p_kalender.add_argument("termin_id", metavar="ID", help="numerische Termin-ID")
    p_kalender.add_argument(
        "--datei",
        metavar="PFAD",
        help="Zielpfad oder vorhandenes Verzeichnis",
    )
    p_kalender.set_defaults(func=cmd_kalender)

    p_watch = unter.add_parser(
        "watch", help="nur neue Termine seit dem letzten Aufruf melden"
    )
    _suchoptionen(p_watch, mit_limit=True)
    p_watch.set_defaults(func=cmd_watch)

    p_config = unter.add_parser(
        "config", help="Standardort und Standardumkreis verwalten"
    )
    config_unter = p_config.add_subparsers(
        dest="aktion",
        metavar="{ort,zeigen,loeschen}",
        required=True,
    )
    p_config_ort = config_unter.add_parser("ort", help="Standardort speichern")
    p_config_ort.add_argument("wert", metavar="PLZ", help="PLZ oder Ortsname")
    p_config_ort.add_argument(
        "--umkreis",
        type=_umkreis,
        metavar="KM",
        help="Standardumkreis in km (1-100)",
    )
    p_config_ort.set_defaults(func=cmd_config_ort)
    p_config_zeigen = config_unter.add_parser("zeigen", help="aktuelle Config ausgeben")
    p_config_zeigen.set_defaults(func=cmd_config_zeigen)
    p_config_loeschen = config_unter.add_parser(
        "loeschen", help="Config löschen (idempotent)"
    )
    p_config_loeschen.set_defaults(func=cmd_config_loeschen)

    return parser


def _fehler(exc: BlutspendeError, json_mode: bool) -> int:
    if json_mode:
        fehler: dict[str, Any] = {
            "code": exc.code,
            "art": exc.art,
            "nachricht": exc.nachricht,
        }
        if exc.kandidaten is not None:
            fehler["kandidaten"] = exc.kandidaten
        print(json.dumps({"ok": False, "fehler": fehler}, ensure_ascii=False))
    else:
        print(f"Fehler: {exc.nachricht}", file=sys.stderr)
    return exc.code


def main(argv: list[str] | None = None) -> int:
    argumente = list(sys.argv[1:] if argv is None else argv)
    frueh_json = "--json" in argumente
    try:
        args = build_parser().parse_args(argumente)
    except UsageError as exc:
        return _fehler(exc, frueh_json or not sys.stdout.isatty())
    json_mode = bool(getattr(args, "json", False) or not sys.stdout.isatty())
    ausgabe = Ausgabe(json_mode)
    try:
        return int(args.func(args, ausgabe))
    except UsageError as exc:
        return _fehler(exc, json_mode)
    except NotFoundError as exc:
        return _fehler(exc, json_mode)
    except SourceError as exc:
        return _fehler(exc, json_mode)
    except BlutspendeError as exc:
        return _fehler(exc, json_mode)
    except KeyboardInterrupt:
        try:
            print("\nAbgebrochen.", file=sys.stderr)
        except OSError:
            pass
        return 130
    except EOFError:
        return _fehler(
            UsageError("Eingabe abgebrochen – Argumente angeben oder --help lesen."),
            json_mode,
        )
    except BrokenPipeError:
        try:
            sys.stdout.close()
        except OSError:
            pass
        return 0
    except Exception as exc:  # noqa: BLE001 - nie Tracebacks nach außen
        nachricht = (
            f"Unerwarteter Fehler ({type(exc).__name__}) – "
            "Aufruf mit `blutspende --help` prüfen oder später erneut versuchen."
        )
        return _fehler(BlutspendeError(nachricht), json_mode)


if __name__ == "__main__":
    raise SystemExit(main())
