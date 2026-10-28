"""Load project configuration (config/*.yaml) with paths resolved against the repo root."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]


def repo_path(relative: str | Path) -> Path:
    """Resolve a repo-relative path from config to an absolute path."""
    p = Path(relative)
    return p if p.is_absolute() else REPO_ROOT / p


@lru_cache(maxsize=1)
def load_settings() -> dict[str, Any]:
    """Return config/settings.yaml as a dict."""
    return yaml.safe_load((REPO_ROOT / "config" / "settings.yaml").read_text())


@lru_cache(maxsize=1)
def load_parameter_groups() -> dict[str, dict[str, Any]]:
    """Return the ordered parameter groups from config/parameter_groups.yaml."""
    return yaml.safe_load((REPO_ROOT / "config" / "parameter_groups.yaml").read_text())["groups"]
