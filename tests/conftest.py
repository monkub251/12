"""Shared fixtures. The fake registry must be installed before core imports."""

from __future__ import annotations

import sys
import tempfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from tests import fakereg  # noqa: E402

WINREG = fakereg.install()


@pytest.fixture(autouse=True)
def clean_registry():
    fakereg.reset()
    yield
    fakereg.reset()


@pytest.fixture(autouse=True)
def isolated_programdata(monkeypatch):
    """Snapshots land in a throwaway dir, never in a real %PROGRAMDATA%."""
    tmp = tempfile.mkdtemp()
    monkeypatch.setenv("PROGRAMDATA", tmp)
    import importlib

    import core.backup as backup

    importlib.reload(backup)
    yield Path(tmp)


@pytest.fixture
def engine(monkeypatch):
    """core.engine with every shell-out neutralised — only registry is real."""
    import core.engine as E

    monkeypatch.setattr(E, "run", lambda *a, **k: (1, ""))
    monkeypatch.setattr(E, "ps", lambda *a, **k: (1, ""))
    return E
