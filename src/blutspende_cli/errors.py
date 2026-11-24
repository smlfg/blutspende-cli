"""Fehlerklassen mit klarer Zuordnung zu Exit-Codes."""

from __future__ import annotations


class BlutspendeError(Exception):
    """Basis für erwartbare Fehler; ``art`` landet im JSON-Fehlerobjekt."""

    code = 1
    art = "fehler"

    def __init__(self, nachricht: str, *, code: int | None = None) -> None:
        super().__init__(nachricht)
        self.nachricht = nachricht
        if code is not None:
            self.code = code


class UsageError(BlutspendeError):
    code = 2
    art = "nutzung"


class NotFoundError(BlutspendeError):
    code = 1
    art = "nicht_gefunden"


class SourceError(BlutspendeError):
    code = 3
    art = "netz"

    def __init__(self, nachricht: str, *, status: int | None = None) -> None:
        super().__init__(nachricht)
        self.status = status
