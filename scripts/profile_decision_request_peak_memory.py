from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import json
import queue
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = REPO_ROOT / "backend"
PYTHON = BACKEND_DIR / "venv" / "Scripts" / "python.exe"


class PROCESS_MEMORY_COUNTERS_EX(ctypes.Structure):
    _fields_ = [
        ("cb", wt.DWORD),
        ("PageFaultCount", wt.DWORD),
        ("PeakWorkingSetSize", ctypes.c_size_t),
        ("WorkingSetSize", ctypes.c_size_t),
        ("QuotaPeakPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPagedPoolUsage", ctypes.c_size_t),
        ("QuotaPeakNonPagedPoolUsage", ctypes.c_size_t),
        ("QuotaNonPagedPoolUsage", ctypes.c_size_t),
        ("PagefileUsage", ctypes.c_size_t),
        ("PeakPagefileUsage", ctypes.c_size_t),
        ("PrivateUsage", ctypes.c_size_t),
    ]


_KERNEL32 = ctypes.WinDLL("kernel32", use_last_error=True)
_PSAPI = ctypes.WinDLL("psapi", use_last_error=True)
_OPEN_PROCESS = _KERNEL32.OpenProcess
_OPEN_PROCESS.argtypes = [wt.DWORD, wt.BOOL, wt.DWORD]
_OPEN_PROCESS.restype = wt.HANDLE
_CLOSE_HANDLE = _KERNEL32.CloseHandle
_CLOSE_HANDLE.argtypes = [wt.HANDLE]
_GET_PROCESS_MEMORY_INFO = _PSAPI.GetProcessMemoryInfo
_GET_PROCESS_MEMORY_INFO.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESS_MEMORY_COUNTERS_EX), wt.DWORD]
_GET_PROCESS_MEMORY_INFO.restype = wt.BOOL

PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010


def _rss_mb(pid: int) -> Optional[float]:
    handle = _OPEN_PROCESS(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid)
    if not handle:
        return None
    try:
        counters = PROCESS_MEMORY_COUNTERS_EX()
        counters.cb = ctypes.sizeof(PROCESS_MEMORY_COUNTERS_EX)
        ok = _GET_PROCESS_MEMORY_INFO(handle, ctypes.byref(counters), counters.cb)
        if not ok:
            return None
        return round(counters.WorkingSetSize / 1024 / 1024, 2)
    finally:
        _CLOSE_HANDLE(handle)


def _http_get(url: str, timeout: int) -> Tuple[int, Dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return int(response.status), parsed


def _http_post(url: str, payload: Dict[str, Any], timeout: int) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return int(response.status), parsed


def run_profile(port: int, wait_seconds: int) -> Dict[str, Any]:
    command = [
        str(PYTHON),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "127.0.0.1",
        "--port",
        str(port),
    ]
    process = subprocess.Popen(
        command,
        cwd=str(BACKEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
    )

    output_queue: queue.Queue[str] = queue.Queue()
    output_lines = []

    def _reader() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output_queue.put(line.rstrip("\n"))

    threading.Thread(target=_reader, daemon=True).start()

    uvicorn_pid: Optional[int] = None
    startup_seen = False
    startup_rss: Optional[float] = None
    before_reco_rss: Optional[float] = None
    after_reco_rss: Optional[float] = None
    peak_rss = 0.0
    started_at = time.time()

    payload = {
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

    health_status: Optional[int] = None
    reco_status: Optional[int] = None
    needs_status: Optional[int] = None
    compare_status: Optional[int] = None
    reco_result_count: Optional[int] = None
    reco_total_candidates: Optional[int] = None
    reco_duration_seconds: Optional[float] = None

    phase = "startup"
    wait_started = 0.0

    while True:
        if process.poll() is not None:
            break

        while True:
            try:
                line = output_queue.get_nowait()
            except queue.Empty:
                break
            output_lines.append(line)

            pid_match = re.search(r"Started server process \[(\d+)\]", line)
            if pid_match and uvicorn_pid is None:
                uvicorn_pid = int(pid_match.group(1))

            if "Application startup complete." in line and not startup_seen:
                startup_seen = True
                if uvicorn_pid is not None:
                    startup_rss = _rss_mb(uvicorn_pid)

        if uvicorn_pid is not None:
            current_rss = _rss_mb(uvicorn_pid)
            if current_rss is not None and current_rss > peak_rss:
                peak_rss = current_rss

        if startup_seen and phase == "startup":
            health_status, _ = _http_get(f"http://127.0.0.1:{port}/health", timeout=20)
            before_reco_rss = _rss_mb(uvicorn_pid) if uvicorn_pid is not None else None
            phase = "recommendations"

        if phase == "recommendations":
            reco_started = time.time()
            reco_status, reco_payload = _http_post(
                f"http://127.0.0.1:{port}/decision-engine/recommendations",
                payload,
                timeout=240,
            )
            reco_duration_seconds = round(time.time() - reco_started, 2)
            reco_result_count = int(reco_payload.get("result_count") or 0)
            reco_total_candidates = int(reco_payload.get("total_candidates_scored") or 0)
            after_reco_rss = _rss_mb(uvicorn_pid) if uvicorn_pid is not None else None
            phase = "other_routes"

        if phase == "other_routes":
            needs_status, needs_payload = _http_post(
                f"http://127.0.0.1:{port}/decision-engine/patient-needs-profile",
                payload,
                timeout=180,
            )
            compare_payload = {
                "canonical_facility_ids": ["CMS-105005", "CMS-105511"],
                "patient_needs_profile": needs_payload.get("patient_needs_profile") or {},
            }
            compare_status, _ = _http_post(
                f"http://127.0.0.1:{port}/decision-engine/comparison-context",
                compare_payload,
                timeout=240,
            )
            phase = "wait"
            wait_started = time.time()

        if phase == "wait" and (time.time() - wait_started) >= wait_seconds:
            break

        if (time.time() - started_at) > 360:
            break

        time.sleep(0.2)

    result = {
        "startup_memory_mb": startup_rss,
        "before_recommendations_memory_mb": before_reco_rss,
        "after_recommendations_memory_mb": after_reco_rss,
        "peak_memory_mb": round(peak_rss, 2),
        "headroom_under_512_mb": round(512.0 - peak_rss, 2),
        "health_status": health_status,
        "recommendations_status": reco_status,
        "recommendations_result_count": reco_result_count,
        "recommendations_total_candidates": reco_total_candidates,
        "recommendations_duration_seconds": reco_duration_seconds,
        "patient_needs_profile_status": needs_status,
        "comparison_context_status": compare_status,
        "process_return_code": process.returncode,
        "uvicorn_pid": uvicorn_pid,
        "startup_seen": startup_seen,
        "log_tail": output_lines[-40:],
    }

    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile request-time memory for decision-engine routes.")
    parser.add_argument("--port", type=int, default=8014)
    parser.add_argument("--wait-seconds", type=int, default=90)
    args = parser.parse_args()
    result = run_profile(port=args.port, wait_seconds=args.wait_seconds)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
