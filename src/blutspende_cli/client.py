"""HTTP-Client für die DRK-Quelle (nur GET, Cache, Rate-Limit)."""

from __future__ import annotations

import hashlib
import json
import os
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlencode, urlsplit

import httpx

from . import __version__
from .config import cache_dir
from .errors import NotFoundError, SourceError, UsageError
from .parsers import (
    Termin,
    finde_landkreis,
    parse_detail,
    parse_landkreise,
    parse_rss,
)

DEFAULT_BASE_URL = "https://www.drk-blutspende.de"
USER_AGENT = f"blutspende-cli/{__version__} (+https://github.com/smlfg/blutspende-cli)"
CACHE_TTL = 600
MIN_INTERVAL = 1.0
TIMEOUT = 15.0


def basis_url() -> str:
    raw = os.environ.get("BLUTSPENDE_BASE_URL", DEFAULT_BASE_URL).strip()
    if not raw:
        raw = DEFAULT_BASE_URL
    parts = urlsplit(raw)
    if parts.scheme not in {"http", "https"} or not parts.netloc:
        raise SourceError(
            "BLUTSPENDE_BASE_URL ist keine gültige http(s)-URL – Wert prüfen."
        )
    return raw.rstrip("/")


class Client:
    """Ein Client je Prozess; Cache und Rate-Limit gelten prozessweit."""

    def __init__(self, base_url: str | None = None) -> None:
        self.base_url = (base_url or basis_url()).rstrip("/")
        self._last_request = 0.0
        self._http = httpx.Client(
            headers={"User-Agent": USER_AGENT, "Accept": "*/*"},
            timeout=TIMEOUT,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._http.close()

    def __enter__(self) -> "Client":
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def _cache_file(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return cache_dir() / "antworten" / f"{digest}.json"

    def _cache_read(self, url: str) -> str | None:
        path = self._cache_file(url)
        try:
            stat = path.stat()
        except OSError:
            return None
        if time.time() - stat.st_mtime > CACHE_TTL:
            return None
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None
        if data.get("url") != url or not isinstance(data.get("text"), str):
            return None
        return data["text"]

    def _cache_write(self, url: str, text: str) -> None:
        path = self._cache_file(url)
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            os.chmod(path.parent, 0o700)
            tmp = path.with_suffix(".tmp")
            tmp.write_text(
                json.dumps({"url": url, "text": text}, ensure_ascii=False),
                encoding="utf-8",
            )
            os.chmod(tmp, 0o600)
            os.replace(tmp, path)
        except OSError:
            return

    def _rate_limit(self) -> None:
        now = time.monotonic()
        wartezeit = MIN_INTERVAL - (now - self._last_request)
        if wartezeit > 0:
            time.sleep(wartezeit)
        self._last_request = time.monotonic()

    def get(self, path: str, params: dict[str, Any] | None = None) -> str:
        query = {
            key: value
            for key, value in (params or {}).items()
            if value is not None and value != ""
        }
        url = f"{self.base_url}{path}"
        if query:
            url = f"{url}?{urlencode(query)}"
        cached = self._cache_read(url)
        if cached is not None:
            return cached
        self._rate_limit()
        try:
            response = self._http.get(url)
        except httpx.TimeoutException as exc:
            raise SourceError(
                "Quelle antwortet nicht – Internet prüfen oder später erneut versuchen."
            ) from exc
        except httpx.RequestError as exc:
            raise SourceError(
                "Quelle nicht erreichbar – Internet prüfen oder später erneut versuchen."
            ) from exc
        if response.status_code >= 400:
            raise SourceError(
                f"Quelle antwortet mit HTTP {response.status_code} – "
                "später erneut versuchen.",
                status=response.status_code,
            )
        encoding = response.encoding or "utf-8"
        text = response.content.decode(encoding, "replace")
        self._cache_write(url, text)
        return text

    def suche_rss(
        self,
        *,
        term: str | None,
        county_id: str | None,
        radius: int,
        von: date,
        bis: date | None,
    ) -> list[Termin]:
        params: dict[str, Any] = {
            "term": term,
            "radius": radius if term else None,
            "date_from": von.isoformat(),
            "date_to": bis.isoformat() if bis else None,
            "county_id": county_id,
        }
        text = self.get("/blutspendetermine/termine.rss", params)
        return parse_rss(text, self.base_url)

    def landkreise(self, term: str, radius: int = 10) -> list[tuple[str, str]]:
        text = self.get(
            "/blutspendetermine/termine", {"term": term, "radius": radius}
        )
        return parse_landkreise(text)

    def loese_landkreis(self, name: str) -> tuple[str, str]:
        landkreise = self.landkreise(name)
        treffer = finde_landkreis(landkreise, name)
        if treffer is None:
            raise UsageError(
                f"Landkreis {name!r} nicht gefunden – Namen prüfen oder PLZ/Ort angeben."
            )
        return treffer

    def detail(self, termin_id: int) -> dict:
        try:
            text = self.get(f"/blutspendetermine/termine/{termin_id}")
        except SourceError as exc:
            if exc.status == 404:
                raise NotFoundError(
                    f"Termin {termin_id} nicht gefunden – ID prüfen."
                ) from exc
            raise
        return parse_detail(text, termin_id, self.base_url)

    def ical(self, termin_id: int) -> str:
        try:
            return self.get(f"/blutspendetermine/termine/{termin_id}/ical.ics")
        except SourceError as exc:
            if exc.status == 404:
                raise NotFoundError(
                    f"Termin {termin_id} nicht gefunden – ID prüfen."
                ) from exc
            raise
