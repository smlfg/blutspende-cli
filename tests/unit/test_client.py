from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from blutspende_cli.client import DEFAULT_BASE_URL, Antwort, Client, basis_url
from blutspende_cli.errors import NotFoundError, SourceError

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "ux"
BASE = "https://www.drk-blutspende.de"


def test_basis_url_default(monkeypatch):
    monkeypatch.delenv("BLUTSPENDE_BASE_URL", raising=False)
    assert basis_url() == DEFAULT_BASE_URL


def test_basis_url_ueberschreibbar(monkeypatch):
    monkeypatch.setenv("BLUTSPENDE_BASE_URL", "http://127.0.0.1:9999/")
    assert basis_url() == "http://127.0.0.1:9999"


@pytest.mark.parametrize("wert", ["keine-url", "ftp://example.invalid"])
def test_basis_url_ungueltig(monkeypatch, wert):
    monkeypatch.setenv("BLUTSPENDE_BASE_URL", wert)
    with pytest.raises(SourceError):
        basis_url()


def test_basis_url_leer_ist_default(monkeypatch):
    monkeypatch.setenv("BLUTSPENDE_BASE_URL", "")
    assert basis_url() == DEFAULT_BASE_URL


def test_suche_rss_baut_parameter_und_parst_fixture(monkeypatch):
    aufrufe = []
    rss = (FIXTURES / "rss_74072.xml").read_text(encoding="utf-8")

    def fake_get(self, path, params=None):
        aufrufe.append((path, params))
        return rss

    monkeypatch.setattr(Client, "get", fake_get)
    client = Client(base_url=BASE)
    termine = client.suche_rss(
        term="74072",
        county_id=None,
        radius=10,
        von=date(2026, 11, 24),
        bis=date(2026, 12, 31),
    )
    client.close()
    assert len(termine) == 3
    pfad, params = aufrufe[0]
    assert pfad == "/blutspendetermine/termine.rss"
    assert params == {
        "term": "74072",
        "radius": 10,
        "date_from": "2026-11-24",
        "date_to": "2026-12-31",
        "county_id": None,
    }


def test_suche_rss_landkreis_ohne_term(monkeypatch):
    aufrufe = []
    rss = (FIXTURES / "rss_zwickau.xml").read_text(encoding="utf-8")

    def fake_get(self, path, params=None):
        aufrufe.append(params)
        return rss

    monkeypatch.setattr(Client, "get", fake_get)
    client = Client(base_url=BASE)
    termine = client.suche_rss(
        term=None,
        county_id="14524",
        radius=10,
        von=date(2026, 11, 24),
        bis=None,
    )
    client.close()
    assert len(termine) == 3
    assert aufrufe[0]["county_id"] == "14524"
    assert aufrufe[0]["term"] is None
    assert aufrufe[0]["radius"] is None


def test_detail_erkennt_redirect_auf_suche_als_nicht_gefunden(monkeypatch):
    def fake_antwort(self, path, params=None):
        return Antwort(
            text="<html><body>Suche</body></html>",
            final_url=f"{BASE}/blutspendetermine/termine/suche",
            content_type="text/html; charset=utf-8",
        )

    monkeypatch.setattr(Client, "get_antwort", fake_antwort)
    client = Client(base_url=BASE)
    with pytest.raises(NotFoundError):
        client.detail(123456789)
    client.close()


def test_detail_parst_gueltige_seite(monkeypatch):
    html = (FIXTURES / "detail_436804.html").read_text(encoding="utf-8")

    def fake_antwort(self, path, params=None):
        return Antwort(
            text=html,
            final_url=f"{BASE}/blutspendetermine/termine/436804",
            content_type="text/html; charset=utf-8",
        )

    monkeypatch.setattr(Client, "get_antwort", fake_antwort)
    client = Client(base_url=BASE)
    detail = client.detail(436804)
    client.close()
    assert detail["id"] == 436804
    assert detail["ort"] == "Erlenbach"


def test_ical_erkennt_html_redirect_als_nicht_gefunden(monkeypatch):
    def fake_antwort(self, path, params=None):
        return Antwort(
            text="<!DOCTYPE html><html><body>Suche</body></html>",
            final_url=f"{BASE}/blutspendetermine/termine/suche",
            content_type="text/html; charset=utf-8",
        )

    monkeypatch.setattr(Client, "get_antwort", fake_antwort)
    client = Client(base_url=BASE)
    with pytest.raises(NotFoundError):
        client.ical(123456789)
    client.close()


def test_ical_liefert_nur_kalenderdaten(monkeypatch):
    ics = (FIXTURES / "termin_436804.ics").read_text(encoding="utf-8")

    def fake_antwort(self, path, params=None):
        return Antwort(
            text=ics,
            final_url=f"{BASE}/blutspendetermine/termine/436804/ical.ics",
            content_type="text/calendar",
        )

    monkeypatch.setattr(Client, "get_antwort", fake_antwort)
    client = Client(base_url=BASE)
    inhalt = client.ical(436804)
    client.close()
    assert inhalt.startswith("BEGIN:VCALENDAR")
