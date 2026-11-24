from __future__ import annotations

import json

import pytest

from blutspende_cli import __version__
from blutspende_cli.cli import main


def test_version_exit_0(capsys):
    with pytest.raises(SystemExit) as info:
        main(["--version"])
    assert info.value.code == 0
    assert __version__ in capsys.readouterr().out


def test_help_exit_0(capsys):
    with pytest.raises(SystemExit) as info:
        main(["--help"])
    assert info.value.code == 0
    aus = capsys.readouterr().out
    for befehl in ["suche", "naechster", "zeige", "kalender", "watch", "config"]:
        assert befehl in aus


def test_unbekanntes_kommando_ist_nutzungsfehler(capsys):
    code = main(["--json", "gibtsnicht"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 2
    assert daten["ok"] is False
    assert daten["fehler"]["code"] == 2
    assert daten["fehler"]["art"] == "nutzung"


def test_ungueltiger_umkreis_ist_nutzungsfehler(capsys):
    code = main(["--json", "suche", "74072", "--umkreis", "999"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 2
    assert "Umkreis" in daten["fehler"]["nachricht"]


def test_help_der_unterkommandos_exit_0():
    for befehl in ["suche", "naechster", "zeige", "kalender", "watch", "config"]:
        with pytest.raises(SystemExit) as info:
            main([befehl, "--help"])
        assert info.value.code == 0


def test_config_ort_ohne_netz(tmp_path, monkeypatch, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    code = main(["--json", "config", "ort", "74072", "--umkreis", "20"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 0
    assert daten["config"] == {"ort": "74072", "umkreis_km": 20}


def test_netzfehler_liefert_json_exit_3(monkeypatch, capsys):
    from blutspende_cli import commands
    from blutspende_cli.errors import SourceError

    class Kaputt:
        def close(self):
            pass

        def suche_rss(self, **kwargs):
            raise SourceError("Quelle nicht erreichbar – später erneut versuchen.")

    monkeypatch.setattr(commands, "Client", lambda: Kaputt())
    code = main(["--json", "suche", "74072"])
    daten = json.loads(capsys.readouterr().out)
    assert code == 3
    assert daten["fehler"]["art"] == "netz"
    assert "Quelle nicht erreichbar" in daten["fehler"]["nachricht"]


def test_strg_c_ohne_traceback(monkeypatch, capsys):
    from blutspende_cli import commands

    def abbrechen():
        raise KeyboardInterrupt

    monkeypatch.setattr(commands, "load_config", abbrechen)
    code = main(["--json", "config", "zeigen"])
    assert code == 130
    assert "Traceback" not in capsys.readouterr().err
