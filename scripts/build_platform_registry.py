from __future__ import annotations

import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.platform_registry_service import write_platform_registry_artifacts


def main() -> int:
    payload = write_platform_registry_artifacts()
    print(
        json.dumps(
            {
                "generated_at_utc": payload.get("generated_at_utc"),
                "summary": payload.get("summary"),
                "current_blocking_capability": payload.get("current_blocking_capability"),
                "objective_stack": payload.get("objective_stack"),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
