"""Akzeptanztests aus docs/UX.md gegen den Fake-Server.

Jede UX-Sitzung hat mindestens einen Test. Das Werkzeug läuft als
Subprozess (``python -m blutspende_cli`` bzw. Console-Script) in einer
PTY-Sitzung, damit die für Menschen gedachte Textausgabe geprüft wird.
Die Tests dürfen vor dem Bau (Schritt 4) rot sein.
"""

from __future__ import annotations

import os
import re
import shutil
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
HARNESS = REPO / "tests" / "harness"
sys.path.insert(0, str(HARNESS))

from fake_server import FakeServer  # noqa: E402
from ux_session import PtySession, strip_ansi  # noqa: E402
from ux_spec import parse  # noqa: E402

PACKAGE = "blutspende_cli"
TOOL = "blutspende"
TODAY = "2026-11-24"
TIMEOUT = 30.0


@pytest.fixture(scope="module")
def ux_spec():
    spec = parse(REPO / "docs" / "UX.md")
    assert not spec.errors, spec.errors
    return spec


def _tool_command() -> list[str]:
    """Bevorzugt das Paket aus ``src/``, sonst ein installiertes Console-Script."""
    if (REPO / "src" / PACKAGE / "__main__.py").is_file():
        return [sys.executable, "-m", PACKAGE]
    exe = shutil.which(TOOL)
    if exe:
        return [exe]
    return [sys.executable, "-m", PACKAGE]


def _env(server: FakeServer, home: Path) -> dict[str, str]:
    home.mkdir(parents=True, exist_ok=True)
    env = dict(os.environ)
    env.update(
        {
            "HOME": str(home),
            "XDG_CONFIG_HOME": str(home / "config"),
            "XDG_STATE_HOME": str(home / "state"),
            "XDG_CACHE_HOME": str(home / "cache"),
            "XDG_DATA_HOME": str(home / "data"),
            "BLUTSPENDE_BASE_URL": server.base_url,
            "BLUTSPENDE_HEUTE": TODAY,
            "PYTHONUNBUFFERED": "1",
            "TERM": "xterm",
            "NO_COLOR": "1",
            "LANG": "C.UTF-8",
            "ACCEPTANCE_SANDBOX": "1",
            "ACCEPTANCE_NET_LOG": str(home / "net.log"),
        }
    )
    parts = [str(REPO / "src"), str(HARNESS)]
    existing = env.get("PYTHONPATH")
    if existing:
        parts.append(existing)
    env["PYTHONPATH"] = os.pathsep.join(parts)
    return env


def _run(args: list[str], env: dict[str, str], answers=()) -> tuple[int, str]:
    """Startet das Werkzeug im PTY und beantwortet optionale Prompts."""
    session = PtySession(_tool_command() + args, env=env, cwd=str(REPO))
    transcript = ""
    try:
        for prompt, answer in answers:
            if not session.expect(prompt, timeout=TIMEOUT):
                session.kill()
                break
            session.send_line(answer)
        code = session.wait_exit(TIMEOUT)
        transcript = strip_ansi(session.transcript)
    finally:
        session.close()
    return code, transcript


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _expect_text(output: str, expected: str) -> None:
    assert _flat(expected) in _flat(output), (
        f"erwartet: {expected!r}\n\nAusgabe:\n{output}"
    )


def test_suche_74072(ux_spec, tmp_path):
    with FakeServer(ux_spec, REPO) as server:
        code, out = _run(["suche", "74072"], _env(server, tmp_path))
        assert server.requests, "kein Request am Fake-Server (base_url_env?)"
    assert code == 0, out
    _expect_text(out, "3 Termine im Umkreis von 10 km um 74072")
    _expect_text(
        out,
        "02.12.2026, 14:00-19:00 Uhr: 74235 Erlenbach, Sulmtalhalle, Kultursaal",
    )
    _expect_text(out, "03.12.2026, 14:30-19:30 Uhr: 74388 Talheim, Schloßberghalle")
    _expect_text(
        out,
        "23.12.2026, 14:00-19:00 Uhr: 74078 Heilbronn-Kirchhausen, "
        "Deutschordenhalle",
    )


def test_naechster_heilbronn(ux_spec, tmp_path):
    with FakeServer(ux_spec, REPO) as server:
        code, out = _run(["naechster", "Heilbronn"], _env(server, tmp_path))
        assert server.requests, "kein Request am Fake-Server (base_url_env?)"
    assert code == 0, out
    _expect_text(out, "Nächster Termin:")
    _expect_text(
        out,
        "23.12.2026, 14:00-19:00 Uhr: 74078 Heilbronn-Kirchhausen, "
        "Deutschordenhalle",
    )


def test_zeige_erlenbach_waehlt_zweiten(ux_spec, tmp_path):
    with FakeServer(ux_spec, REPO) as server:
        code, out = _run(
            ["zeige", "Erlenbach"],
            _env(server, tmp_path),
            answers=[("Welchen Termin anzeigen? [1-3]", "2")],
        )
        assert server.requests, "kein Request am Fake-Server (base_url_env?)"
    assert code == 0, out
    _expect_text(out, "Mehrere Termine gefunden:")
    _expect_text(out, "1) 25.11.2026, 15:30-19:45 Uhr: 61352 Bad Homburg / Ober-Erlenbach")
    _expect_text(out, "2) 02.12.2026, 14:00-19:00 Uhr: 74235 Erlenbach")
    _expect_text(out, "3) 28.12.2026, 16:30-20:00 Uhr: 97714 OERLENBACH")
    _expect_text(out, "Blutspende in Erlenbach")
    _expect_text(out, "02.12.2026")
    _expect_text(out, "Sulmtalhalle, Kultursaal")
    _expect_text(out, "Talstraße 21")
    _expect_text(out, "14:00 - 19:00 Uhr")
    _expect_text(out, "Nur mit Terminreservierung!")
    _expect_text(out, "Termin reservieren: https://terminreservierung.blutspende.de")


def test_kalender_436804(ux_spec, tmp_path):
    with FakeServer(ux_spec, REPO) as server:
        code, out = _run(["kalender", "436804"], _env(server, tmp_path))
        assert server.requests, "kein Request am Fake-Server (base_url_env?)"
    assert code == 0, out
    _expect_text(out, "Kalendereintrag gespeichert:")
    files = sorted((tmp_path / "data").rglob("*.ics"))
    assert files, f"keine .ics-Datei unter {tmp_path / 'data'}\n\n{out}"
    content = files[0].read_text(encoding="utf-8")
    assert "BEGIN:VCALENDAR" in content
    assert "UID:436804" in content


def test_watch_74072_meldet_nur_neue(ux_spec, tmp_path):
    home = tmp_path
    with FakeServer(ux_spec, REPO) as server:
        env = _env(server, home)
        code1, out1 = _run(["watch", "74072"], env)
        code2, out2 = _run(["watch", "74072"], env)
        assert server.requests, "kein Request am Fake-Server (base_url_env?)"
    assert code1 == 0, out1
    _expect_text(out1, "3 neue Termine seit dem letzten Aufruf")
    _expect_text(out1, "02.12.2026 74235 Erlenbach")
    _expect_text(out1, "03.12.2026 74388 Talheim")
    _expect_text(out1, "23.12.2026 74078 Heilbronn-Kirchhausen")
    assert code2 == 0, out2
    _expect_text(out2, "0 neue Termine seit dem letzten Aufruf")


def test_suche_landkreis_zwickau(ux_spec, tmp_path):
    with FakeServer(ux_spec, REPO) as server:
        code, out = _run(
            ["suche", "--landkreis", "Zwickau"], _env(server, tmp_path)
        )
        assert server.requests, "kein Request am Fake-Server (base_url_env?)"
    assert code == 0, out
    _expect_text(out, "Landkreis Zwickau (14524)")
    _expect_text(out, "3 Termine im Landkreis Zwickau")
    _expect_text(
        out,
        "24.11.2026, 11:00-13:00 Uhr: 08056 Zwickau, "
        "Plasmaspendezentrum Zwickau",
    )
    _expect_text(
        out,
        "25.11.2026, 15:00-18:30 Uhr: 08412 Werdau, Werdau, Stadthalle",
    )
    _expect_text(
        out,
        "26.11.2026, 11:00-13:00 Uhr: 08056 Zwickau, "
        "Plasmaspendezentrum Zwickau",
    )
