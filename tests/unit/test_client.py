from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest

from blutspende_cli.client import DEFAULT_BASE_URL, Client, basis_url
from blutspende_cli.errors import SourceError

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
