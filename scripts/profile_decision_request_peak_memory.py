from __future__ import annotations

import argparse
import ctypes
import ctypes.wintypes as wt
import gc
import json
import queue
import re
import subprocess
import threading
import time
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple


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


class PROCESSENTRY32W(ctypes.Structure):
    _fields_ = [
        ("dwSize", wt.DWORD),
        ("cntUsage", wt.DWORD),
        ("th32ProcessID", wt.DWORD),
        ("th32DefaultHeapID", ctypes.c_size_t),
        ("th32ModuleID", wt.DWORD),
        ("cntThreads", wt.DWORD),
        ("th32ParentProcessID", wt.DWORD),
        ("pcPriClassBase", ctypes.c_long),
        ("dwFlags", wt.DWORD),
        ("szExeFile", ctypes.c_wchar * 260),
    ]


class IO_COUNTERS(ctypes.Structure):
    _fields_ = [
        ("ReadOperationCount", ctypes.c_ulonglong),
        ("WriteOperationCount", ctypes.c_ulonglong),
        ("OtherOperationCount", ctypes.c_ulonglong),
        ("ReadTransferCount", ctypes.c_ulonglong),
        ("WriteTransferCount", ctypes.c_ulonglong),
        ("OtherTransferCount", ctypes.c_ulonglong),
    ]


class JOBOBJECT_BASIC_LIMIT_INFORMATION(ctypes.Structure):
    _fields_ = [
        ("PerProcessUserTimeLimit", ctypes.c_longlong),
        ("PerJobUserTimeLimit", ctypes.c_longlong),
        ("LimitFlags", wt.DWORD),
        ("MinimumWorkingSetSize", ctypes.c_size_t),
        ("MaximumWorkingSetSize", ctypes.c_size_t),
        ("ActiveProcessLimit", wt.DWORD),
        ("Affinity", ctypes.c_size_t),
        ("PriorityClass", wt.DWORD),
        ("SchedulingClass", wt.DWORD),
    ]


class JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT(ctypes.Structure):
    _fields_ = [
        ("BasicLimitInformation", JOBOBJECT_BASIC_LIMIT_INFORMATION),
        ("IoInfo", IO_COUNTERS),
        ("ProcessMemoryLimit", ctypes.c_size_t),
        ("JobMemoryLimit", ctypes.c_size_t),
        ("PeakProcessMemoryUsed", ctypes.c_size_t),
        ("PeakJobMemoryUsed", ctypes.c_size_t),
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

_CREATE_TOOLHELP32_SNAPSHOT = _KERNEL32.CreateToolhelp32Snapshot
_CREATE_TOOLHELP32_SNAPSHOT.argtypes = [wt.DWORD, wt.DWORD]
_CREATE_TOOLHELP32_SNAPSHOT.restype = wt.HANDLE

_PROCESS32_FIRST = _KERNEL32.Process32FirstW
_PROCESS32_FIRST.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_PROCESS32_FIRST.restype = wt.BOOL

_PROCESS32_NEXT = _KERNEL32.Process32NextW
_PROCESS32_NEXT.argtypes = [wt.HANDLE, ctypes.POINTER(PROCESSENTRY32W)]
_PROCESS32_NEXT.restype = wt.BOOL

_CREATE_JOB_OBJECT = _KERNEL32.CreateJobObjectW
_CREATE_JOB_OBJECT.argtypes = [ctypes.c_void_p, wt.LPCWSTR]
_CREATE_JOB_OBJECT.restype = wt.HANDLE

_SET_INFORMATION_JOB_OBJECT = _KERNEL32.SetInformationJobObject
_SET_INFORMATION_JOB_OBJECT.argtypes = [wt.HANDLE, wt.INT, ctypes.c_void_p, wt.DWORD]
_SET_INFORMATION_JOB_OBJECT.restype = wt.BOOL

_ASSIGN_PROCESS_TO_JOB_OBJECT = _KERNEL32.AssignProcessToJobObject
_ASSIGN_PROCESS_TO_JOB_OBJECT.argtypes = [wt.HANDLE, wt.HANDLE]
_ASSIGN_PROCESS_TO_JOB_OBJECT.restype = wt.BOOL


PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
PROCESS_SET_QUOTA = 0x0100
PROCESS_TERMINATE = 0x0001

TH32CS_SNAPPROCESS = 0x00000002

JOB_OBJECT_LIMIT_PROCESS_MEMORY = 0x00000100
JOB_OBJECT_EXTENDED_LIMIT_INFORMATION = 9


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


def _child_pids(root_pid: int) -> List[int]:
    snapshot = _CREATE_TOOLHELP32_SNAPSHOT(TH32CS_SNAPPROCESS, 0)
    if not snapshot:
        return []
    try:
        parent_map: Dict[int, List[int]] = {}
        entry = PROCESSENTRY32W()
        entry.dwSize = ctypes.sizeof(PROCESSENTRY32W)
        ok = _PROCESS32_FIRST(snapshot, ctypes.byref(entry))
        while ok:
            pid = int(entry.th32ProcessID)
            ppid = int(entry.th32ParentProcessID)
            parent_map.setdefault(ppid, []).append(pid)
            ok = _PROCESS32_NEXT(snapshot, ctypes.byref(entry))

        out: List[int] = []
        stack = [root_pid]
        seen: Set[int] = set()
        while stack:
            current = stack.pop()
            for child in parent_map.get(current, []):
                if child in seen:
                    continue
                seen.add(child)
                out.append(child)
                stack.append(child)
        return out
    finally:
        _CLOSE_HANDLE(snapshot)


def _process_tree_rss_mb(root_pid: int) -> float:
    total = 0.0
    root_rss = _rss_mb(root_pid)
    if root_rss is not None:
        total += root_rss
    for child_pid in _child_pids(root_pid):
        child_rss = _rss_mb(child_pid)
        if child_rss is not None:
            total += child_rss
    return round(total, 2)


def _apply_process_memory_limit(process_pid: int, limit_mib: int) -> Optional[int]:
    job = _CREATE_JOB_OBJECT(None, "optime-decision-memory-cap")
    if not job:
        return None

    limits = JOBOBJECT_EXTENDED_LIMIT_INFORMATION_STRUCT()
    limits.BasicLimitInformation.LimitFlags = JOB_OBJECT_LIMIT_PROCESS_MEMORY
    limits.ProcessMemoryLimit = int(limit_mib) * 1024 * 1024
    ok = _SET_INFORMATION_JOB_OBJECT(
        job,
        JOB_OBJECT_EXTENDED_LIMIT_INFORMATION,
        ctypes.byref(limits),
        ctypes.sizeof(limits),
    )
    if not ok:
        _CLOSE_HANDLE(job)
        return None

    process_handle = _OPEN_PROCESS(PROCESS_SET_QUOTA | PROCESS_TERMINATE | PROCESS_QUERY_INFORMATION, False, process_pid)
    if not process_handle:
        _CLOSE_HANDLE(job)
        return None

    try:
        assigned = _ASSIGN_PROCESS_TO_JOB_OBJECT(job, process_handle)
        if not assigned:
            _CLOSE_HANDLE(job)
            return None
    finally:
        _CLOSE_HANDLE(process_handle)

    return int(job)


def _http_get(url: str, timeout: int = 20) -> Tuple[int, Dict[str, Any]]:
    with urllib.request.urlopen(url, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return int(response.status), parsed


def _http_post(url: str, payload: Dict[str, Any], timeout: int = 240) -> Tuple[int, Dict[str, Any]]:
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = response.read().decode("utf-8")
        parsed = json.loads(body) if body else {}
        return int(response.status), parsed


def run_profile(port: int, duration_seconds: int, hard_limit_mib: Optional[int]) -> Dict[str, Any]:
    command = [
        str(PYTHON),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        "0.0.0.0",
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
    output_lines: List[str] = []

    def _reader() -> None:
        assert process.stdout is not None
        for line in process.stdout:
            output_queue.put(line.rstrip("\n"))

    threading.Thread(target=_reader, daemon=True).start()

    job_handle: Optional[int] = None
    if hard_limit_mib is not None:
        job_handle = _apply_process_memory_limit(process.pid, hard_limit_mib)

    uvicorn_pid: Optional[int] = None
    startup_seen = False
    startup_rss: Optional[float] = None
    startup_tree_rss: Optional[float] = None
    peak_rss = 0.0
    peak_tree_rss = 0.0

    sequence_status: Dict[str, Any] = {
        "root": None,
        "health": None,
        "openapi": None,
        "facilities": None,
        "facilities_limit_100": None,
        "governance_runtime_context": None,
        "patient_needs_profile": None,
        "comparison_context": None,
        "recommendations": [],
    }

    recommendation_payload = {
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

    memory_samples: List[Dict[str, Any]] = []
    recommendation_memory_after: List[float] = []
    first_reco_after: Optional[float] = None
    final_reco_after: Optional[float] = None
    recommendations_count = 0
    recommendations_total_candidates: Optional[int] = None

    started_at = time.time()
    next_cycle_at = 0.0
    cycle_interval_seconds = 35

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
                    startup_tree_rss = _process_tree_rss_mb(uvicorn_pid)

        if uvicorn_pid is not None:
            current_rss = _rss_mb(uvicorn_pid)
            if current_rss is not None and current_rss > peak_rss:
                peak_rss = current_rss
            current_tree_rss = _process_tree_rss_mb(uvicorn_pid)
            if current_tree_rss > peak_tree_rss:
                peak_tree_rss = current_tree_rss

        now = time.time()
        elapsed = now - started_at

        if startup_seen and uvicorn_pid is not None and now >= next_cycle_at:
            sample: Dict[str, Any] = {"elapsed_sec": round(elapsed, 2)}

            sequence_status["root"], _ = _http_get(f"http://127.0.0.1:{port}/")
            sequence_status["health"], _ = _http_get(f"http://127.0.0.1:{port}/health")
            sequence_status["openapi"], _ = _http_get(f"http://127.0.0.1:{port}/openapi.json", timeout=40)
            sequence_status["facilities"], _ = _http_get(f"http://127.0.0.1:{port}/facilities", timeout=90)
            sequence_status["facilities_limit_100"], _ = _http_get(f"http://127.0.0.1:{port}/facilities?limit=100", timeout=90)
            sequence_status["governance_runtime_context"], _ = _http_get(
                f"http://127.0.0.1:{port}/governance/runtime-context", timeout=120
            )

            sequence_status["patient_needs_profile"], needs_payload = _http_post(
                f"http://127.0.0.1:{port}/decision-engine/patient-needs-profile",
                recommendation_payload,
                timeout=180,
            )
            comparison_payload = {
                "canonical_facility_ids": ["CMS-105005", "CMS-105511"],
                "patient_needs_profile": needs_payload,
            }
            sequence_status["comparison_context"], _ = _http_post(
                f"http://127.0.0.1:{port}/decision-engine/comparison-context",
                comparison_payload,
                timeout=240,
            )

            reco_start = time.time()
            reco_status, reco_payload = _http_post(
                f"http://127.0.0.1:{port}/decision-engine/recommendations",
                recommendation_payload,
                timeout=240,
            )
            reco_seconds = round(time.time() - reco_start, 2)
            sequence_status["recommendations"].append({"status": reco_status, "seconds": reco_seconds})
            recommendations_count += 1
            recommendations_total_candidates = int(reco_payload.get("total_candidates_scored") or 0)

            after_reco = _rss_mb(uvicorn_pid)
            tree_after_reco = _process_tree_rss_mb(uvicorn_pid)
            sample["rss_after_recommendations_mb"] = after_reco
            sample["tree_rss_after_recommendations_mb"] = tree_after_reco
            if after_reco is not None:
                recommendation_memory_after.append(after_reco)
                if first_reco_after is None:
                    first_reco_after = after_reco
                final_reco_after = after_reco

            time.sleep(1.5)
            gc.collect()
            sample["rss_after_gc_mb"] = _rss_mb(uvicorn_pid)
            sample["tree_rss_after_gc_mb"] = _process_tree_rss_mb(uvicorn_pid)

            for wait_mark in (30, 60, 120):
                if time.time() - started_at + wait_mark > duration_seconds:
                    continue
                time.sleep(wait_mark)
                gc.collect()
                sample[f"rss_after_{wait_mark}s_mb"] = _rss_mb(uvicorn_pid)
                sample[f"tree_rss_after_{wait_mark}s_mb"] = _process_tree_rss_mb(uvicorn_pid)
                if process.poll() is not None:
                    break

            memory_samples.append(sample)
            next_cycle_at = time.time() + cycle_interval_seconds

        if elapsed > duration_seconds:
            break

        time.sleep(0.2)

    result = {
        "startup_memory_mb": startup_rss,
        "startup_process_tree_memory_mb": startup_tree_rss,
        "first_recommendation_after_memory_mb": first_reco_after,
        "final_recommendation_after_memory_mb": final_reco_after,
        "peak_memory_mb": round(peak_rss, 2),
        "peak_process_tree_memory_mb": round(peak_tree_rss, 2),
        "headroom_under_512_mb": round(512.0 - peak_tree_rss, 2),
        "hard_limit_mib": hard_limit_mib,
        "job_limit_applied": job_handle is not None,
        "endpoint_status": sequence_status,
        "recommendation_request_count": recommendations_count,
        "recommendations_total_candidates": recommendations_total_candidates,
        "recommendation_memory_samples_mb": recommendation_memory_after,
        "memory_samples": memory_samples,
        "process_return_code": process.returncode,
        "uvicorn_pid": uvicorn_pid,
        "startup_seen": startup_seen,
        "log_tail": output_lines[-60:],
    }

    try:
        process.terminate()
        process.wait(timeout=8)
    except Exception:
        try:
            process.kill()
        except Exception:
            pass

    if job_handle is not None:
        try:
            _CLOSE_HANDLE(job_handle)
        except Exception:
            pass

    return result


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile production-like decision-route memory behavior over time.")
    parser.add_argument("--port", type=int, default=8014)
    parser.add_argument("--duration-seconds", type=int, default=330)
    parser.add_argument("--hard-limit-mib", type=int, default=512)
    args = parser.parse_args()

    result = run_profile(
        port=args.port,
        duration_seconds=args.duration_seconds,
        hard_limit_mib=args.hard_limit_mib,
    )
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
