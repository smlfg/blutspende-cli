from __future__ import annotations

from pathlib import Path

from blutspende_cli.parsers import (
    finde_landkreis,
    parse_detail,
    parse_landkreise,
    parse_rss,
)

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ux"
BASE = "https://www.drk-blutspende.de"


def _text(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def test_rss_74072_parst_drei_termine():
    termine = parse_rss(_text("rss_74072.xml"), BASE)
    assert len(termine) == 3
    erster = termine[0]
    assert erster.id == 436804
    assert erster.datum.isoformat() == "2026-12-02"
    assert erster.wochentag == "Mi"
    assert (erster.von, erster.bis) == ("14:00", "19:00")
    assert (erster.plz, erster.ort) == ("74235", "Erlenbach")
    assert erster.strasse == "Talstraße 21"
    assert erster.lokal == "Sulmtalhalle, Kultursaal"
    assert erster.detail_url.endswith("/blutspendetermine/termine/436804")
    assert erster.ical_url.endswith("/blutspendetermine/termine/436804/ical.ics")


def test_rss_erlenbach_mehrdeutig():
    termine = parse_rss(_text("rss_erlenbach.xml"), BASE)
    assert [t.ort for t in termine] == [
        "Bad Homburg / Ober-Erlenbach",
        "Erlenbach",
        "OERLENBACH",
    ]


def test_rss_zwickau_mit_klammer_strasse():
    termine = parse_rss(_text("rss_zwickau.xml"), BASE)
    assert termine[0].strasse == "Äußere Schneeberger Straße 100 (Glück-Auf-Center)"
    assert termine[0].lokal == "Plasmaspendezentrum Zwickau"


def test_landkreise_und_tippfehler():
    landkreise = parse_landkreise(_text("landkreise.html"))
    assert ("14524", "Zwickau") in landkreise
    assert finde_landkreis(landkreise, "Zwickau") == ("14524", "Zwickau")
    assert finde_landkreis(landkreise, "zwickua") == ("14524", "Zwickau")
    assert finde_landkreis(landkreise, "gibtsnicht") is None


def test_detail_parst_adresse_reservierung_und_hinweis():
    detail = parse_detail(_text("detail_436804.html"), 436804, BASE)
    assert detail["titel"] == "Blutspende in Erlenbach"
    assert detail["datum"].isoformat() == "2026-12-02"
    assert detail["datum_text"] == "02.12.2026"
    assert detail["plz"] == "74235"
    assert detail["ort"] == "Erlenbach"
    assert detail["lokal"] == "Sulmtalhalle, Kultursaal"
    assert detail["strasse"] == "Talstraße 21"
    assert (detail["von"], detail["bis"]) == ("14:00", "19:00")
    assert detail["reservierung_pflicht"] is True
    assert detail["reservierung_url"].startswith(
        "https://terminreservierung.blutspende.de/"
    )
    assert detail["ical_url"].endswith("/blutspendetermine/termine/436804/ical.ics")
