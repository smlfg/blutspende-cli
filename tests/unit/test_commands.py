from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path

import pytest

from blutspende_cli import commands
from blutspende_cli.commands import Ausgabe
from blutspende_cli.parsers import parse_detail, parse_rss

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ux"
BASE = "https://www.drk-blutspende.de"


class StubClient:
    def __init__(self) -> None:
        self.rss = (FIXTURES / "rss_74072.xml").read_text(encoding="utf-8")
        self.landkreis_rss = (FIXTURES / "rss_zwickau.xml").read_text(encoding="utf-8")
        self.erlenbach_rss = (FIXTURES / "rss_erlenbach.xml").read_text(encoding="utf-8")
        self.heilbronn_rss = (FIXTURES / "rss_heilbronn.xml").read_text(encoding="utf-8")
        self.detail_html = (FIXTURES / "detail_436804.html").read_text(encoding="utf-8")
        self.ics = (FIXTURES / "termin_436804.ics").read_text(encoding="utf-8")
        self.aufrufe = []

    def close(self) -> None:
        pass

    def suche_rss(self, *, term, county_id, radius, von, bis):
        self.aufrufe.append(("rss", term, county_id, radius, von, bis))
        if county_id:
            return parse_rss(self.landkreis_rss, BASE)
        if term == "Erlenbach":
            return parse_rss(self.erlenbach_rss, BASE)
        if term == "Heilbronn":
            return parse_rss(self.heilbronn_rss, BASE)
        return parse_rss(self.rss, BASE)

    def loese_landkreis(self, name):
        return "14524", "Zwickau"

    def detail(self, termin_id):
        return parse_detail(self.detail_html, termin_id, BASE)

    def ical(self, termin_id):
        return self.ics


@pytest.fixture
def umgebung(tmp_path, monkeypatch):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    monkeypatch.setenv("XDG_STATE_HOME", str(tmp_path / "state"))
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "cache"))
    monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / "data"))
    monkeypatch.setenv("BLUTSPENDE_HEUTE", "2026-11-24")
    monkeypatch.setattr(commands, "Client", lambda: StubClient())
    return tmp_path


def _suche_args(**overrides):
    werte = {
        "suchbegriff": "74072",
        "umkreis": None,
        "landkreis": None,
        "von": None,
        "bis": None,
        "limit": 20,
    }
    werte.update(overrides)
    return argparse.Namespace(**werte)


def test_suche_text(umgebung, capsys):
    code = commands.cmd_suche(_suche_args(), Ausgabe(False))
    aus = capsys.readouterr().out
    assert code == 0
    assert "3 Termine im Umkreis von 10 km um 74072" in aus
    assert "02.12.2026, 14:00-19:00 Uhr: 74235 Erlenbach" in aus
    assert "(ID 436804)" in aus


def test_suche_json_und_limit(umgebung, capsys):
    code = commands.cmd_suche(_suche_args(limit=2), Ausgabe(True))
    daten = json.loads(capsys.readouterr().out)
    assert code == 0
    assert daten["ok"] is True
    assert daten["anzahl"] == 2
    assert daten["abfrage"]["von"] == "2026-11-24"
    assert [t["id"] for t in daten["termine"]] == [436804, 436838]


def test_landkreis_suche(umgebung, capsys):
    args = _suche_args(suchbegriff=None, landkreis="Zwickau")
    code = commands.cmd_suche(args, Ausgabe(False))
    aus = capsys.readouterr().out
    assert code == 0
    assert "Landkreis Zwickau (14524)" in aus
    assert "3 Termine im Landkreis Zwickau" in aus


def test_suche_ohne_ort_und_config_ist_nutzungsfehler(umgebung):
    from blutspende_cli.errors import UsageError

    with pytest.raises(UsageError):
        commands.cmd_suche(
            _suche_args(suchbegriff=None), Ausgabe(True)
        )


def test_naechster(umgebung, capsys):
    args = _suche_args(suchbegriff="Heilbronn")
    code = commands.cmd_naechster(args, Ausgabe(False))
    aus = capsys.readouterr().out
    assert code == 0
    assert aus.startswith("Nächster Termin:")


def test_zeige_per_id(umgebung, capsys):
    args = argparse.Namespace(ziel="436804", umkreis=None, erster=False)
    code = commands.cmd_zeige(args, Ausgabe(False))
    aus = capsys.readouterr().out
    assert code == 0
    assert "Blutspende in Erlenbach" in aus
    assert "14:00 - 19:00 Uhr" in aus
    assert "Nur mit Terminreservierung!" in aus
    assert "Termin reservieren: https://terminreservierung.blutspende.de" in aus


def test_zeige_mehrdeutig_ohne_tty(umgebung, capsys, monkeypatch):
    from blutspende_cli.errors import UsageError

    monkeypatch.setattr("sys.stdin.isatty", lambda: False)
    args = argparse.Namespace(ziel="Erlenbach", umkreis=None, erster=False)
    with pytest.raises(UsageError):
        commands.cmd_zeige(args, Ausgabe(False))
    aus = capsys.readouterr().out
    assert "Mehrere Termine gefunden:" in aus


def test_kalender_speichert_datei(umgebung, capsys):
    args = argparse.Namespace(termin_id="436804", datei=None)
    code = commands.cmd_kalender(args, Ausgabe(False))
    aus = capsys.readouterr().out
    datei = umgebung / "data" / "blutspende-cli" / "termine" / "436804.ics"
    assert code == 0
    assert "Kalendereintrag gespeichert:" in aus
    assert datei.is_file()
    assert "UID:436804" in datei.read_text(encoding="utf-8")


def test_kalender_unbekannte_id_schreibt_keine_datei(umgebung, monkeypatch):
    from blutspende_cli.errors import NotFoundError

    class Fehlt:
        def close(self):
            pass

        def ical(self, termin_id):
            raise NotFoundError(f"Termin {termin_id} nicht gefunden – ID prüfen.")

    monkeypatch.setattr(commands, "Client", lambda: Fehlt())
    ziel = umgebung / "bad_123456789.ics"
    with pytest.raises(NotFoundError):
        commands.cmd_kalender(
            argparse.Namespace(termin_id="123456789", datei=str(ziel)), Ausgabe(True)
        )
    assert not ziel.exists()


def test_watch_meldet_nur_neue(umgebung, capsys):
    args = _suche_args()
    commands.cmd_watch(args, Ausgabe(False))
    aus1 = capsys.readouterr().out
    commands.cmd_watch(args, Ausgabe(False))
    aus2 = capsys.readouterr().out
    assert "3 neue Termine seit dem letzten Aufruf" in aus1
    assert "0 neue Termine seit dem letzten Aufruf" in aus2
    state = umgebung / "state" / "blutspende-cli" / "watch.json"
    assert state.is_file()
    assert oct(state.stat().st_mode & 0o777) == oct(0o600)


def test_watch_ueber_tageswechsel_meldet_keine_alten(umgebung, capsys, monkeypatch):
    args = _suche_args()
    commands.cmd_watch(args, Ausgabe(True))
    capsys.readouterr()
    monkeypatch.setenv("BLUTSPENDE_HEUTE", "2026-11-25")
    code = commands.cmd_watch(args, Ausgabe(True))
    daten = json.loads(capsys.readouterr().out)
    assert code == 0
    assert daten["anzahl_neu"] == 0
    assert daten["termine"] == []


def test_config_ort_zeigen_loeschen(umgebung, capsys):
    ort = argparse.Namespace(wert="74072", umkreis=20)
    commands.cmd_config_ort(ort, Ausgabe(False))
    config_datei = umgebung / "config" / "blutspende-cli" / "config.json"
    assert config_datei.is_file()
    assert oct(config_datei.stat().st_mode & 0o777) == oct(0o600)
    daten = json.loads(config_datei.read_text(encoding="utf-8"))
    assert daten == {"ort": "74072", "umkreis_km": 20}

    commands.cmd_config_zeigen(argparse.Namespace(), Ausgabe(False))
    aus = capsys.readouterr().out
    assert "Ort: 74072" in aus
    assert "Umkreis: 20 km" in aus

    assert commands.cmd_config_loeschen(argparse.Namespace(), Ausgabe(False)) == 0
    assert not config_datei.exists()
    assert commands.cmd_config_loeschen(argparse.Namespace(), Ausgabe(False)) == 0
