from __future__ import annotations

import json
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path


REQUEST_PAYLOAD = {
    "questionnaire_state": {
        "relationship": "Dad",
        "ageGroup": "80-84",
        "assistanceLevel": "24/7 support required",
        "memoryStatus": "No",
        "budget": 7000,
        "distanceFromFamily": "Balanced location",
        "humanIntelligenceV2": {
            "transitionRiskProfile": {
                "postHospitalRehabNeed": "Yes",
            }
        },
    },
    "natural_language_query": "Father age 82 Miami stroke limited mobility 24/7 support PT OT speech medication transfer",
    "limit": 50,
}
def _http_get(url: str, timeout: int = 20) -> tuple[int, dict]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return int(response.status), json.loads(body) if body else {}


def _http_post(url: str, payload: dict, timeout: int = 120) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        return int(response.status), json.loads(body) if body else {}


def test_decision_routes_end_to_end() -> None:
    backend_dir = Path(__file__).resolve().parents[1]
    python_exe = backend_dir / "venv" / "Scripts" / "python.exe"
    command = [
        str(python_exe),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        "8016",
    ]

    process = subprocess.Popen(
        command,
        cwd=str(backend_dir),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_lines: list[str] = []

    def _reader() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output_lines.append(line.rstrip("\n"))

    thread = threading.Thread(target=_reader, daemon=True)
    thread.start()

    try:
        started = False
        started_at = time.time()
        while time.time() - started_at < 180:
            if any("Application startup complete." in line for line in output_lines):
                started = True
                break
            if process.poll() is not None:
                break
            time.sleep(0.2)

        assert started, "uvicorn did not complete startup"

        health_status, _ = _http_get("http://127.0.0.1:8016/health")
        assert health_status == 200

        recommendations_status, recommendations_payload = _http_post(
            "http://127.0.0.1:8016/decision-engine/recommendations", REQUEST_PAYLOAD, timeout=240
        )
        assert recommendations_status == 200
        assert int(recommendations_payload.get("result_count") or 0) > 0
        assert int(recommendations_payload.get("total_candidates_scored") or 0) >= int(
            recommendations_payload.get("result_count") or 0
        )

        needs_status, needs_payload = _http_post(
            "http://127.0.0.1:8016/decision-engine/patient-needs-profile", REQUEST_PAYLOAD, timeout=180
        )
        assert needs_status == 200
        assert isinstance(needs_payload, dict)
        assert isinstance(needs_payload.get("needs"), list)

        comparison_payload = {
            "canonical_facility_ids": ["CMS-105005", "CMS-105511"],
            "patient_needs_profile": needs_payload,
        }
        comparison_status, comparison_body = _http_post(
            "http://127.0.0.1:8016/decision-engine/comparison-context", comparison_payload, timeout=240
        )
        assert comparison_status == 200
        assert isinstance(comparison_body.get("facilities"), list)

        combined_logs = "\n".join(output_lines)
        assert re.search(r"POST /decision-engine/recommendations", combined_logs)
        assert re.search(r"POST /decision-engine/patient-needs-profile", combined_logs)
        assert re.search(r"POST /decision-engine/comparison-context", combined_logs)
    finally:
        try:
            process.terminate()
            process.wait(timeout=10)
        except Exception:
            try:
                process.kill()
            except Exception:
                pass
