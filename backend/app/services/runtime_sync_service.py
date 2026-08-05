from __future__ import annotations

import json
import logging
import os
import shutil
import subprocess
import tempfile
import threading
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from app.services.canonical_universe import configured_canonical_market, resolve_canonical_universe_path
from app.services.facility_parameter_service import get_runtime_cache_status, get_runtime_metadata, refresh_runtime_cache


logger = logging.getLogger("optime.runtime_sync")

REPO_ROOT = Path(__file__).resolve().parents[3]
DATABASE_DIR = REPO_ROOT / "database"
SCRIPTS_DIR = REPO_ROOT / "scripts"

ARTIFACT_REGISTRY = DATABASE_DIR / "optime_parameter_registry.json"
ARTIFACT_EVIDENCE = DATABASE_DIR / "florida_facility_parameter_evidence.json"


def _artifact_canonical() -> Path:
    return resolve_canonical_universe_path(require_exists=False)

SOURCE_CMS_INVENTORY = DATABASE_DIR / "florida_senior_living_inventory.json"
SOURCE_LEGACY_EVIDENCE = DATABASE_DIR / "florida_parameter_evidence.json"
SOURCE_NPPES_TAXONOMY = DATABASE_DIR / "florida_nppes_taxonomy_evidence.json"

INGEST_SCRIPT = SCRIPTS_DIR / "ingest_nppes_florida_universe.py"
BUILD_SCRIPT = SCRIPTS_DIR / "build_optime_parameter_matrix.py"

_MONITOR_LOCK = threading.RLock()
_MONITOR_THREAD: Optional[threading.Thread] = None
_STOP_EVENT = threading.Event()

_STATE: Dict[str, Any] = {
    "monitor_enabled": False,
    "monitor_interval_seconds": 120,
    "last_check_at": None,
    "last_dirty": None,
    "dirty_reasons": [],
    "last_rebuild_attempt_at": None,
    "last_rebuild_success_at": None,
    "last_rebuild_duration_ms": None,
    "last_error": None,
    "retry_count": 0,
    "next_retry_at": None,
    "last_artifact_signature": None,
    "runtime_version_history": [],
    "recent_events": [],
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _record_event(level: str, message: str, **details: Any) -> None:
    event = {
        "timestamp": _utc_now_iso(),
        "level": level,
        "message": message,
        "details": details,
    }
    with _MONITOR_LOCK:
        events = list(_STATE.get("recent_events") or [])
        events.append(event)
        _STATE["recent_events"] = events[-100:]


def _parse_env_int(name: str, default: int, minimum: int, maximum: int) -> int:
    raw = os.getenv(name)
    if raw is None:
        return default
    try:
        value = int(raw)
    except ValueError:
        logger.warning("runtime_sync_invalid_env name=%s raw=%s default=%s", name, raw, default)
        return default
    return max(minimum, min(maximum, value))


def _resolve_python_executable() -> Path:
    override = str(os.getenv("OPTIME_PYTHON") or "").strip()
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = REPO_ROOT / candidate
        if candidate.exists():
            return candidate

    canonical = REPO_ROOT / "backend" / "venv" / "Scripts" / "python.exe"
    if canonical.exists():
        return canonical

    fallback = REPO_ROOT / ".venv" / "Scripts" / "python.exe"
    if fallback.exists():
        return fallback

    raise FileNotFoundError("No canonical OPTIME Python interpreter found in backend/venv or .venv")


def _file_signature(path: Path) -> Dict[str, Any]:
    if not path.exists():
        return {"path": str(path), "exists": False, "mtime": None, "size": None}
    stat = path.stat()
    return {
        "path": str(path),
        "exists": True,
        "mtime": stat.st_mtime,
        "size": stat.st_size,
    }


def _artifact_signature() -> Dict[str, Any]:
    return {
        "registry": _file_signature(ARTIFACT_REGISTRY),
        "evidence": _file_signature(ARTIFACT_EVIDENCE),
        "canonical": _file_signature(_artifact_canonical()),
    }


def _latest_mtime(paths: List[Path]) -> Optional[float]:
    values = [path.stat().st_mtime for path in paths if path.exists()]
    return max(values) if values else None


def detect_runtime_dirty() -> Dict[str, Any]:
    reasons: List[str] = []

    artifacts = [ARTIFACT_REGISTRY, ARTIFACT_EVIDENCE, _artifact_canonical()]
    missing = [str(path) for path in artifacts if not path.exists()]
    if missing:
        reasons.append(f"missing_artifacts:{','.join(missing)}")

    latest_source = _latest_mtime([SOURCE_CMS_INVENTORY, SOURCE_LEGACY_EVIDENCE, SOURCE_NPPES_TAXONOMY])
    oldest_artifact = None
    if all(path.exists() for path in artifacts):
        oldest_artifact = min(path.stat().st_mtime for path in artifacts)
    if latest_source is not None and oldest_artifact is not None and latest_source > oldest_artifact:
        reasons.append("source_newer_than_runtime_artifacts")

    current_signature = _artifact_signature()
    with _MONITOR_LOCK:
        previous_signature = _STATE.get("last_artifact_signature")
    if previous_signature and previous_signature != current_signature:
        reasons.append("artifact_signature_changed")

    return {
        "dirty": len(reasons) > 0,
        "reasons": reasons,
        "artifact_signature": current_signature,
        "latest_source_mtime": latest_source,
        "oldest_artifact_mtime": oldest_artifact,
    }


def _run_script(script: Path, timeout_seconds: int) -> Tuple[bool, str]:
    python_executable = _resolve_python_executable()
    command = [str(python_executable), str(script)]
    logger.info("runtime_sync_script_start script=%s", script)
    _record_event("INFO", "script_start", script=str(script))
    try:
        completed = subprocess.run(
            command,
            cwd=str(REPO_ROOT),
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        message = f"script_timeout script={script} timeout_seconds={timeout_seconds}"
        logger.error(message)
        _record_event("ERROR", "script_timeout", script=str(script), timeout_seconds=timeout_seconds)
        return False, message
    except Exception as exc:  # defensive guard for production stability
        message = f"script_execution_error script={script} error={exc}"
        logger.exception(message)
        _record_event("ERROR", "script_execution_error", script=str(script), error=str(exc))
        return False, message

    output = (completed.stdout or "") + (completed.stderr or "")
    if completed.returncode != 0:
        message = f"script_failed script={script} returncode={completed.returncode}"
        logger.error("%s output=%s", message, output[-4000:])
        _record_event("ERROR", "script_failed", script=str(script), returncode=completed.returncode)
        return False, f"{message} output_tail={output[-1200:]}"

    logger.info("runtime_sync_script_success script=%s", script)
    _record_event("INFO", "script_success", script=str(script))
    return True, output[-1200:]


def _validate_runtime_artifacts() -> Tuple[bool, List[str]]:
    messages: List[str] = []
    canonical_artifact = _artifact_canonical()
    required = [ARTIFACT_REGISTRY, ARTIFACT_EVIDENCE, canonical_artifact]
    for path in required:
        if not path.exists():
            messages.append(f"missing:{path}")
    if messages:
        return False, messages

    checks = [
        (ARTIFACT_REGISTRY, ["generated_at_utc", "record_count", "records"]),
        (ARTIFACT_EVIDENCE, ["generated_at_utc", "record_count", "records"]),
        (canonical_artifact, ["generated_at_utc", "record_count", "records"]),
    ]
    for path, keys in checks:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:
            messages.append(f"invalid_json:{path}:{exc}")
            continue

        for key in keys:
            if key not in payload:
                messages.append(f"missing_key:{path}:{key}")
        if not isinstance(payload.get("records"), list):
            messages.append(f"invalid_records_type:{path}")

    return len(messages) == 0, messages


def _snapshot_runtime_artifacts() -> Tuple[Dict[str, Optional[Path]], Path]:
    snapshot: Dict[str, Optional[Path]] = {
        "registry": None,
        "evidence": None,
        "canonical": None,
    }
    tmp_dir = Path(tempfile.mkdtemp(prefix="runtime-sync-", dir=str(REPO_ROOT / "backend")))

    for key, source in {
        "registry": ARTIFACT_REGISTRY,
        "evidence": ARTIFACT_EVIDENCE,
        "canonical": _artifact_canonical(),
    }.items():
        if not source.exists():
            continue
        destination = tmp_dir / f"{key}.json"
        shutil.copyfile(source, destination)
        snapshot[key] = destination
    return snapshot, tmp_dir


def _restore_runtime_artifacts(snapshot: Dict[str, Optional[Path]]) -> None:
    mapping = {
        "registry": ARTIFACT_REGISTRY,
        "evidence": ARTIFACT_EVIDENCE,
        "canonical": _artifact_canonical(),
    }
    for key, destination in mapping.items():
        source = snapshot.get(key)
        if source is None or not source.exists():
            continue
        shutil.copyfile(source, destination)


def _rebuild_runtime_artifacts(trigger: str) -> Dict[str, Any]:
    start = time.perf_counter()
    messages: List[str] = []
    if configured_canonical_market() != "florida":
        return {
            "ok": False,
            "error": "automatic_rebuild_unsupported_for_configured_market",
            "messages": ["Florida-only runtime rebuild scripts cannot rebuild a non-Florida canonical universe."],
            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        }
    snapshot, backup_dir = _snapshot_runtime_artifacts()

    if not _artifact_canonical().exists() and INGEST_SCRIPT.exists():
        ok, message = _run_script(INGEST_SCRIPT, timeout_seconds=900)
        messages.append(message)
        if not ok:
            shutil.rmtree(backup_dir, ignore_errors=True)
            return {
                "ok": False,
                "error": "canonical_ingest_failed",
                "messages": messages,
                "duration_ms": round((time.perf_counter() - start) * 1000, 2),
            }

    ok, message = _run_script(BUILD_SCRIPT, timeout_seconds=1800)
    messages.append(message)
    if not ok:
        _restore_runtime_artifacts(snapshot)
        _record_event("WARNING", "runtime_restore_after_build_failure", trigger=trigger)
        shutil.rmtree(backup_dir, ignore_errors=True)
        return {
            "ok": False,
            "error": "build_runtime_failed",
            "messages": messages,
            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    artifacts_valid, validation_errors = _validate_runtime_artifacts()
    if not artifacts_valid:
        _restore_runtime_artifacts(snapshot)
        _record_event("ERROR", "runtime_validation_failed_restore", trigger=trigger, errors=validation_errors)
        shutil.rmtree(backup_dir, ignore_errors=True)
        return {
            "ok": False,
            "error": "runtime_artifact_validation_failed",
            "messages": messages + validation_errors,
            "duration_ms": round((time.perf_counter() - start) * 1000, 2),
        }

    refresh_runtime_cache(reason=f"runtime_sync:{trigger}")
    shutil.rmtree(backup_dir, ignore_errors=True)
    _record_event("INFO", "runtime_rebuild_success", trigger=trigger)
    return {
        "ok": True,
        "messages": messages,
        "duration_ms": round((time.perf_counter() - start) * 1000, 2),
    }


def run_runtime_sync(*, force: bool = False, trigger: str = "manual") -> Dict[str, Any]:
    with _MONITOR_LOCK:
        _STATE["last_check_at"] = _utc_now_iso()
        _STATE["last_rebuild_attempt_at"] = _utc_now_iso()

    dirty_result = detect_runtime_dirty()
    should_rebuild = force or bool(dirty_result["dirty"])

    with _MONITOR_LOCK:
        _STATE["last_dirty"] = bool(dirty_result["dirty"])
        _STATE["dirty_reasons"] = list(dirty_result["reasons"])
        _STATE["last_artifact_signature"] = dirty_result["artifact_signature"]

    if not should_rebuild:
        _record_event("INFO", "runtime_noop_clean", trigger=trigger)
        runtime_meta = get_runtime_metadata()
        return {
            "ok": True,
            "action": "noop",
            "reason": "runtime_clean",
            "dirty": False,
            "dirty_reasons": dirty_result["reasons"],
            "runtime_version": runtime_meta.get("runtime_version"),
            "runtime_timestamp": runtime_meta.get("runtime_timestamp"),
        }

    rebuild_result = _rebuild_runtime_artifacts(trigger=trigger)
    if rebuild_result["ok"]:
        with _MONITOR_LOCK:
            _STATE["last_rebuild_success_at"] = _utc_now_iso()
            _STATE["last_rebuild_duration_ms"] = rebuild_result["duration_ms"]
            _STATE["last_error"] = None
            _STATE["retry_count"] = 0
            _STATE["next_retry_at"] = None
            _STATE["last_artifact_signature"] = _artifact_signature()
        runtime_meta = get_runtime_metadata()
        with _MONITOR_LOCK:
            history = list(_STATE.get("runtime_version_history") or [])
            version_value = str(runtime_meta.get("runtime_version") or "")
            if version_value:
                history.append(
                    {
                        "runtime_version": version_value,
                        "runtime_timestamp": runtime_meta.get("runtime_timestamp"),
                        "activated_at": _utc_now_iso(),
                        "trigger": trigger,
                    }
                )
                _STATE["runtime_version_history"] = history[-20:]
            _record_event("INFO", "runtime_sync_success", trigger=trigger, duration_ms=rebuild_result["duration_ms"])
        return {
            "ok": True,
            "action": "rebuild",
            "dirty": bool(dirty_result["dirty"]),
            "dirty_reasons": dirty_result["reasons"],
            "duration_ms": rebuild_result["duration_ms"],
            "runtime_version": runtime_meta.get("runtime_version"),
            "runtime_timestamp": runtime_meta.get("runtime_timestamp"),
            "messages": rebuild_result["messages"],
        }

    with _MONITOR_LOCK:
        _STATE["last_error"] = rebuild_result["error"]
        _STATE["retry_count"] = int(_STATE.get("retry_count") or 0) + 1
        backoff = min(900, 30 * (2 ** min(_STATE["retry_count"], 5)))
        _STATE["next_retry_at"] = datetime.fromtimestamp(time.time() + backoff, tz=timezone.utc).isoformat()
    _record_event("ERROR", "runtime_sync_failed", trigger=trigger, error=rebuild_result["error"])

    return {
        "ok": False,
        "action": "rebuild_failed",
        "dirty": bool(dirty_result["dirty"]),
        "dirty_reasons": dirty_result["reasons"],
        "error": rebuild_result["error"],
        "messages": rebuild_result["messages"],
    }


def _monitor_loop() -> None:
    logger.info("runtime_sync_monitor_started")
    while not _STOP_EVENT.is_set():
        interval = _parse_env_int("OPTIME_RUNTIME_SYNC_INTERVAL_SECONDS", 120, 15, 3600)
        with _MONITOR_LOCK:
            _STATE["monitor_interval_seconds"] = interval

        try:
            next_retry = None
            with _MONITOR_LOCK:
                next_retry = _STATE.get("next_retry_at")
            if next_retry:
                retry_time = datetime.fromisoformat(str(next_retry).replace("Z", "+00:00"))
                if datetime.now(timezone.utc) < retry_time:
                    _record_event("INFO", "runtime_retry_waiting", next_retry_at=next_retry)
                    _STOP_EVENT.wait(interval)
                    continue

            result = run_runtime_sync(force=False, trigger="monitor")
            if not result.get("ok"):
                logger.warning("runtime_sync_monitor_iteration_failed error=%s", result.get("error"))
        except Exception as exc:
            logger.exception("runtime_sync_monitor_unhandled_error error=%s", exc)
            with _MONITOR_LOCK:
                _STATE["last_error"] = f"monitor_unhandled:{exc}"

        _STOP_EVENT.wait(interval)

    logger.info("runtime_sync_monitor_stopped")


def start_runtime_sync_monitor() -> Dict[str, Any]:
    enabled = os.getenv("OPTIME_RUNTIME_SYNC_ENABLED", "1") == "1"
    with _MONITOR_LOCK:
        _STATE["monitor_enabled"] = enabled
    if not enabled:
        logger.info("runtime_sync_monitor_disabled")
        _record_event("INFO", "runtime_monitor_disabled")
        return get_runtime_sync_status()

    global _MONITOR_THREAD
    with _MONITOR_LOCK:
        if _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive():
            return get_runtime_sync_status()

        _STOP_EVENT.clear()
        _MONITOR_THREAD = threading.Thread(target=_monitor_loop, name="optime-runtime-sync", daemon=True)
        _MONITOR_THREAD.start()
        _record_event("INFO", "runtime_monitor_started")

    return get_runtime_sync_status()


def stop_runtime_sync_monitor() -> None:
    _STOP_EVENT.set()


def get_runtime_sync_status() -> Dict[str, Any]:
    dirty_result = detect_runtime_dirty()
    runtime_meta = get_runtime_metadata()
    cache_status = get_runtime_cache_status()
    with _MONITOR_LOCK:
        thread_running = _MONITOR_THREAD is not None and _MONITOR_THREAD.is_alive()
        status = {
            "monitor_enabled": bool(_STATE.get("monitor_enabled")),
            "monitor_running": bool(thread_running),
            "monitor_interval_seconds": int(_STATE.get("monitor_interval_seconds") or 120),
            "last_check_at": _STATE.get("last_check_at"),
            "last_dirty": _STATE.get("last_dirty"),
            "dirty_reasons": list(_STATE.get("dirty_reasons") or []),
            "last_rebuild_attempt_at": _STATE.get("last_rebuild_attempt_at"),
            "last_rebuild_success_at": _STATE.get("last_rebuild_success_at"),
            "last_rebuild_duration_ms": _STATE.get("last_rebuild_duration_ms"),
            "last_error": _STATE.get("last_error"),
            "retry_count": int(_STATE.get("retry_count") or 0),
            "next_retry_at": _STATE.get("next_retry_at"),
            "runtime_version_history": list(_STATE.get("runtime_version_history") or []),
            "recent_events": list(_STATE.get("recent_events") or []),
        }

    status.update(
        {
            "dirty": bool(dirty_result["dirty"]),
            "dirty_reasons_current": dirty_result["reasons"],
            "artifact_signature": dirty_result["artifact_signature"],
            "runtime_version": runtime_meta.get("runtime_version"),
            "runtime_timestamp": runtime_meta.get("runtime_timestamp"),
            "runtime_cache": cache_status,
        }
    )
    return status
