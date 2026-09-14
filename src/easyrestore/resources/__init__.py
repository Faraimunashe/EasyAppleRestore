"""Bundled static assets (logo, etc.)."""

from __future__ import annotations

from importlib import resources
from pathlib import Path


def resource_path(name: str) -> Path:
    """Return a filesystem path to a packaged resource file."""
    root = resources.files("easyrestore.resources")
    return Path(str(root.joinpath(name)))
