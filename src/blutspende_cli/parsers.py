"""Parser für RSS-Suche, Landkreisliste und Detailseite."""

from __future__ import annotations

import re
import unicodedata
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import date
from difflib import SequenceMatcher

from bs4 import BeautifulSoup, Tag

from .errors import SourceError

WOCHENTAGE = ["Mo", "Di", "Mi", "Do", "Fr", "Sa", "So"]
RSS_TITLE_RE = re.compile(
    r"^(?P<plz>\d{5})\s+(?P<ort>.+?)\s+am\s+"
    r"(?P<datum>\d{1,2}\.\d{1,2}\.\d{4}),\s*"
    r"(?P<von>\d{1,2}:\d{2})\s*Uhr\s+bis\s+"
    r"(?P<bis>\d{1,2}:\d{2})\s*Uhr\.?$"
)
TIME_RE = re.compile(r"(?P<von>\d{1,2}:\d{2})\s*[-–]\s*(?P<bis>\d{1,2}:\d{2})\s*Uhr")
PLZ_ORT_RE = re.compile(r"^(?P<ort>.+?)\s+(?P<plz>\d{5})$")


@dataclass
class Termin:
    id: int
    datum: date
    von: str
    bis: str
    plz: str
    ort: str
    lokal: str = ""
    strasse: str = ""
    reservierung_pflicht: bool = False
    reservierung_url: str | None = None
    detail_url: str = ""
    ical_url: str = ""

    @property
    def wochentag(self) -> str:
        return WOCHENTAGE[self.datum.weekday()]

    @property
    def datum_text(self) -> str:
        return self.datum.strftime("%d.%m.%Y")

    @property
    def zeit_text(self) -> str:
        return f"{self.von}-{self.bis} Uhr"

    def als_json(self) -> dict:
        return {
            "id": self.id,
            "datum": self.datum.isoformat(),
            "wochentag": self.wochentag,
            "von": self.von,
            "bis": self.bis,
            "plz": self.plz,
            "ort": self.ort,
            "lokal": self.lokal,
            "strasse": self.strasse,
            "reservierung_pflicht": self.reservierung_pflicht,
            "reservierung_url": self.reservierung_url,
            "detail_url": self.detail_url,
            "ical_url": self.ical_url,
        }


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


def _datum(iso: str) -> date:
    return date.fromisoformat(iso)


def _id_aus_link(link: str) -> int | None:
    match = re.search(r"/termine/(\d+)", link)
    if match:
        return int(match.group(1))
    match = re.fullmatch(r"\s*(\d+)\s*", link or "")
    if match:
        return int(match.group(1))
    return None


def parse_rss(text: str, base_url: str) -> list[Termin]:
    """Wandelt einen RSS-Feed in Termine um; unbrauchbare Items werden übersprungen."""
    try:
        root = ET.fromstring(text)
    except ET.ParseError as exc:
        raise SourceError(
            "Antwort der Quelle ist kein gültiges RSS – später erneut versuchen."
        ) from exc
    termine: list[Termin] = []
    for item in root.iter("item"):
        title = _clean(item.findtext("title") or "")
        link = _clean(item.findtext("link") or item.findtext("guid") or "")
        description = _clean(item.findtext("description") or "")
        match = RSS_TITLE_RE.match(title)
        termin_id = _id_aus_link(link)
        if not match or termin_id is None:
            continue
        try:
            tag = date(
                int(match.group("datum")[6:10]),
                int(match.group("datum")[3:5]),
                int(match.group("datum")[0:2]),
            )
        except ValueError:
            continue
        strasse = ""
        lokal = ""
        if description.startswith("-"):
            description = description.lstrip("-").strip()
        parts = [part.strip() for part in description.split(" - ") if part.strip()]
        if parts:
            strasse = parts[0]
        if len(parts) > 1:
            lokal = ", ".join(parts[1:])
        termin = Termin(
            id=termin_id,
            datum=tag,
            von=match.group("von"),
            bis=match.group("bis"),
            plz=match.group("plz"),
            ort=match.group("ort").strip(),
            lokal=lokal,
            strasse=strasse,
            detail_url=f"{base_url}/blutspendetermine/termine/{termin_id}",
            ical_url=f"{base_url}/blutspendetermine/termine/{termin_id}/ical.ics",
        )
        termine.append(termin)
    return termine


def _normalisiere(text: str) -> str:
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(char for char in text if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def parse_landkreise(html: str) -> list[tuple[str, str]]:
    """Liefert (county_id, Name) aus dem Select der Suchseite."""
    soup = BeautifulSoup(html, "html.parser")
    select = soup.find("select", attrs={"name": "county_id"})
    if not isinstance(select, Tag):
        return []
    result: list[tuple[str, str]] = []
    for option in select.find_all("option"):
        value = (option.get("value") or "").strip()
        name = _clean(option.get_text(" ", strip=True))
        if value and name:
            result.append((value, name))
    return result


def finde_landkreis(landkreise: list[tuple[str, str]], name: str) -> tuple[str, str] | None:
    """Tippfehlertolerante Auflösung eines Landkreisnamens."""
    gesucht = _normalisiere(name)
    if not gesucht:
        return None
    for county_id, kandidat in landkreise:
        if _normalisiere(kandidat) == gesucht:
            return county_id, kandidat
    for county_id, kandidat in landkreise:
        if gesucht in _normalisiere(kandidat):
            return county_id, kandidat
    best: tuple[float, str, str] | None = None
    for county_id, kandidat in landkreise:
        score = SequenceMatcher(None, gesucht, _normalisiere(kandidat)).ratio()
        if best is None or score > best[0]:
            best = (score, county_id, kandidat)
    if best is not None and best[0] >= 0.72:
        return best[1], best[2]
    return None


def parse_detail(html: str, termin_id: int, base_url: str) -> dict:
    """Liest die Detailseite; fehlende Felder bleiben leer."""
    soup = BeautifulSoup(html, "html.parser")
    h1 = soup.find("h1")
    titel = _clean(h1.get_text(" ", strip=True)) if isinstance(h1, Tag) else ""

    datum_text = ""
    datum_node = soup.select_one("div.datum p")
    if isinstance(datum_node, Tag):
        datum_text = _clean(datum_node.get_text(" ", strip=True))

    adresse_node = soup.select_one("div.adresse")
    zeilen: list[str] = []
    if isinstance(adresse_node, Tag):
        for zeile in adresse_node.get_text("\n", strip=True).splitlines():
            zeile = _clean(zeile)
            if zeile and not zeile.startswith("Nur mit Terminreservierung"):
                zeilen.append(zeile)

    plz = ""
    ort = ""
    strasse = ""
    lokal = ""
    von = ""
    bis = ""
    rest: list[str] = []
    for zeile in zeilen:
        plz_match = PLZ_ORT_RE.match(zeile)
        if plz_match and not plz:
            ort = plz_match.group("ort").strip()
            plz = plz_match.group("plz")
            continue
        zeit_match = TIME_RE.search(zeile)
        if zeit_match and not von:
            von = zeit_match.group("von")
            bis = zeit_match.group("bis")
            continue
        rest.append(zeile)
    for index, zeile in enumerate(rest):
        if re.search(r"\d", zeile):
            strasse = rest.pop(index)
            break
    if rest:
        lokal = rest[0]

    reservierung = soup.select_one("#make_reservation a.reservation")
    if not isinstance(reservierung, Tag):
        reservierung = soup.select_one("a.reservation")
    reservierung_url: str | None = None
    if isinstance(reservierung, Tag):
        href = (reservierung.get("href") or "").strip()
        if href:
            reservierung_url = href

    text = soup.get_text(" ", strip=True)
    pflicht = "Nur mit Terminreservierung" in text

    if not datum_text:
        og = soup.find("meta", attrs={"property": "og:description"})
        if isinstance(og, Tag):
            match = re.search(r"(\d{1,2}\.\d{1,2}\.\d{4})", og.get("content") or "")
            if match:
                datum_text = match.group(1)
    try:
        tag = date(
            int(datum_text[6:10]), int(datum_text[3:5]), int(datum_text[0:2])
        )
    except (ValueError, IndexError):
        tag = None

    return {
        "id": termin_id,
        "titel": titel,
        "datum": tag,
        "datum_text": datum_text,
        "wochentag": WOCHENTAGE[tag.weekday()] if tag else "",
        "plz": plz,
        "ort": ort,
        "lokal": lokal,
        "strasse": strasse,
        "von": von,
        "bis": bis,
        "reservierung_pflicht": pflicht,
        "reservierung_url": reservierung_url,
        "detail_url": f"{base_url}/blutspendetermine/termine/{termin_id}",
        "ical_url": f"{base_url}/blutspendetermine/termine/{termin_id}/ical.ics",
    }
