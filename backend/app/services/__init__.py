from __future__ import annotations

"""Service package import governance.

There are historically multiple decision-engine implementations in the repo:
``patient_decision_engine.py`` (legacy core), ``patient_decision_engine/``
(governed care/regulatory facade), and the integrated production runtime that
adds evidence-governed Human Intelligence. Production must always resolve the
public ``app.services.patient_decision_engine`` name to the integrated runtime.

The integrated runtime explicitly loads the governed facade, which in turn may
load the legacy scorer by file path. This finder is deliberately scoped to one
fully-qualified module name; all other ``app.services`` imports use normal
Python resolution.
"""

import importlib.abc
import importlib.util
import sys
from pathlib import Path
from types import ModuleType
from typing import Optional


_GOVERNED_FULLNAME = f"{__name__}.patient_decision_engine"
_RUNTIME_DIR = Path(__file__).resolve().parent / "patient_decision_engine_runtime"
_RUNTIME_INIT = _RUNTIME_DIR / "__init__.py"


class _GovernedDecisionEngineFinder(importlib.abc.MetaPathFinder):
    """Resolve the public production decision-engine name to the integrated runtime."""

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
            _RUNTIME_INIT,
            submodule_search_locations=[str(_RUNTIME_DIR)],
        )


if not any(isinstance(finder, _GovernedDecisionEngineFinder) for finder in sys.meta_path):
    sys.meta_path.insert(0, _GovernedDecisionEngineFinder())