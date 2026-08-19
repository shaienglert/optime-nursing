from __future__ import annotations

"""Service package import governance.

There are historically two filesystem entries named ``patient_decision_engine``:
``patient_decision_engine.py`` (legacy core) and ``patient_decision_engine/``
(the governed production facade). Different Python import environments can
resolve that collision differently. Production must always import the governed
package while the facade itself may still load the legacy core explicitly by
file path.

This finder is deliberately scoped to that single fully-qualified module name;
all other ``app.services`` imports use Python's normal resolution.
"""

import importlib.abc
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional


_GOVERNED_FULLNAME = f"{__name__}.patient_decision_engine"
_GOVERNED_DIR = Path(__file__).resolve().parent / "patient_decision_engine"
_GOVERNED_INIT = _GOVERNED_DIR / "__init__.py"


class _GovernedDecisionEngineFinder(importlib.abc.MetaPathFinder):
    """Resolve the production decision-engine name to the governed package."""

    def find_spec(
        self,
        fullname: str,
        path: Optional[list[str]] = None,
        target: Optional[ModuleType] = None,
    ):
        if fullname != _GOVERNED_FULLNAME:
            return None
        return importlib.util.spec_from_file_location(
            fullname,
            _GOVERNED_INIT,
            submodule_search_locations=[str(_GOVERNED_DIR)],
        )


if not any(isinstance(finder, _GovernedDecisionEngineFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _GovernedDecisionEngineFinder())
