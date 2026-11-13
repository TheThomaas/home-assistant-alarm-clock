"""Chargement de la logique pure, sans Home Assistant.

`custom_components/reveil/schedule.py` est importé par chemin de fichier :
importer `custom_components.reveil` exécuterait `__init__.py`, qui dépend de
Home Assistant. La suite doit donc tourner sans HA installé — c'est ce qui
garantit que `schedule.py` reste sans dépendance au framework.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import pytest

MODULE_PATH = (
    Path(__file__).resolve().parent.parent
    / "custom_components"
    / "reveil"
    / "schedule.py"
)


@pytest.fixture(scope="session")
def schedule() -> ModuleType:
    """Le module `schedule.py` de l'intégration, chargé hors package."""
    spec = importlib.util.spec_from_file_location("reveil_schedule", MODULE_PATH)
    assert spec is not None and spec.loader is not None, MODULE_PATH
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module
