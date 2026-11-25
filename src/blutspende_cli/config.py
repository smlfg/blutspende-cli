"""Config- und Zustandspfade (XDG), Rechte 0600."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .errors import BlutspendeError, UsageError

APP = "blutspende-cli"


def _xdg(name: str, fallback: str) -> Path:
    value = os.environ.get(name)
    if value:
        return Path(value).expanduser()
    return Path.home() / fallback


def config_dir() -> Path:
    return _xdg("XDG_CONFIG_HOME", ".config") / APP


def state_dir() -> Path:
    return _xdg("XDG_STATE_HOME", ".local/state") / APP


def cache_dir() -> Path:
    return _xdg("XDG_CACHE_HOME", ".cache") / APP


def data_dir() -> Path:
    return _xdg("XDG_DATA_HOME", ".local/share") / APP


def config_path() -> Path:
    return config_dir() / "config.json"


def watch_path() -> Path:
    return state_dir() / "watch.json"


def _ensure_dir(path: Path, mode: int = 0o700) -> None:
    path.mkdir(parents=True, exist_ok=True)
    try:
        os.chmod(path, mode)
    except OSError:
        pass


def ensure_cache_dir() -> Path:
    path = cache_dir()
    _ensure_dir(path, 0o700)
    return path


def _atomic_write(path: Path, text: str, mode: int) -> None:
    _ensure_dir(path.parent)
    handle, raw = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-")
    tmp = Path(raw)
    try:
        with os.fdopen(handle, "w", encoding="utf-8") as stream:
            stream.write(text)
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        try:
            tmp.unlink()
        except OSError:
            pass
        raise


def _read_json(path: Path) -> dict[str, Any]:
    try:
        raw = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return {}
    except OSError as exc:
        raise BlutspendeError(
            f"Datei {path} nicht lesbar – Rechte prüfen oder Datei löschen."
        ) from exc
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise BlutspendeError(
            f"Datei {path} ist kein gültiges JSON – `blutspende config loeschen` ausführen."
        ) from exc
    if not isinstance(data, dict):
        raise BlutspendeError(
            f"Datei {path} hat ein unerwartetes Format – `blutspende config loeschen` ausführen."
        )
    return data


def load_config() -> dict[str, Any]:
    data = _read_json(config_path())
    ort = data.get("ort")
    umkreis = data.get("umkreis_km")
    result: dict[str, Any] = {}
    if isinstance(ort, str) and ort.strip():
        result["ort"] = ort.strip()
    if isinstance(umkreis, int) and not isinstance(umkreis, bool) and 1 <= umkreis <= 100:
        result["umkreis_km"] = umkreis
    return result


def save_config(data: dict[str, Any]) -> Path:
    path = config_path()
    _atomic_write(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n", 0o600)
    return path


def delete_config() -> bool:
    path = config_path()
    try:
        path.unlink()
        return True
    except FileNotFoundError:
        return False
    except OSError as exc:
        raise BlutspendeError(f"Config {path} nicht löschbar – Rechte prüfen.") from exc


def load_watch() -> dict[str, Any]:
    return _read_json(watch_path())


def save_watch(data: dict[str, Any]) -> None:
    _atomic_write(
        watch_path(), json.dumps(data, ensure_ascii=False, indent=2) + "\n", 0o600
    )


def validate_umkreis(value: int) -> int:
    if not 1 <= value <= 100:
        raise UsageError("Umkreis muss zwischen 1 und 100 km liegen.")
    return value
