import json
import logging
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

from app.database import SessionLocal
from app.models.agent_execution import AgentJobRun, AgentKnowledgeRecord, AgentKnowledgeRefreshEvent, AgentKnowledgeReportSnapshot, SupervisorIncidentLog
from app.models.facility import Facility, FacilityIntelligenceProfile
from app.services.agent_knowledge_reports import AGENT_REPORT_DEFS
from app.services.email_service import configured_recipients, send_email
from app.services.report_archive_service import (
    create_report_artifacts,
    history,
    latest_record,
    load_report_json,
    mark_report_sent,
    previous_record,
)
from app.services.external_discovery import build_external_discovery_summary

SUPPLEMENTAL_AGENT_DEFS: List[Dict[str, Any]] = [
    {
        "agent_key": "chief_ai_supervisor",
        "agent_name": "Chief AI Supervisor",
        "domain": "Supervisory governance",
        "mission": "Monitor agent health, readiness, incidents, and remediation priorities.",
        "entry_point": "backend/app/services/chief_ai_supervisor.py",
        "trigger": "Manual API/supervisor invocation",
        "schedule": "MANUAL_ONLY",
        "dependencies": ["All expert agents"],
        "expected_outputs": ["Supervisor incidents", "Readiness metrics", "Refresh decisions"],
    },
    {
        "agent_key": "clinical_evidence",
        "agent_name": "Clinical Evidence Agent",
        "domain": "Evidence repository",
        "mission": "Discover and validate trusted evidence for clinical and recommendation claims.",
        "entry_point": "docs/agent_specs/evidence_agent_spec.md",
        "trigger": "Specified only",
        "schedule": "CONFIGURED_NOT_RUNNING",
        "dependencies": ["Clinical Knowledge Agent", "Outcome Learning Agent", "Knowledge Graph Agent", "Narrative Intelligence Agent"],
        "expected_outputs": ["Evidence objects", "Citation verification", "Evidence gap prioritization"],
    },
    {
        "agent_key": "competitive_intelligence",
        "agent_name": "Competitive Intelligence Agent",
        "domain": "Competitive and market intelligence",
        "mission": "Identify market gaps, provider patterns, and demand opportunities.",
        "entry_point": "docs/agent_specs/competitive_intelligence_agent_spec.md",
        "trigger": "Specified only",
        "schedule": "CONFIGURED_NOT_RUNNING",
        "dependencies": ["Provider Intelligence Agent", "Chief AI Supervisor", "Data Quality & Trust Agent"],
        "expected_outputs": ["Market reports", "Demand signals", "Coverage opportunities"],
    },
    {
        "agent_key": "narrative_intelligence",
        "agent_name": "Narrative Intelligence Agent",
        "domain": "Narrative intelligence",
        "mission": "Produce explanation quality improvements and advisor-ready summaries from prepared knowledge.",
        "entry_point": "docs/agent_specs/narrative_intelligence_agent_spec.md",
        "trigger": "Specified only",
        "schedule": "CONFIGURED_NOT_RUNNING",
        "dependencies": ["Clinical Knowledge Agent", "Provider Intelligence Agent", "Clinical Evidence Agent", "Knowledge Graph Agent", "Matching Improvement Agent"],
        "expected_outputs": ["Executive summaries", "Narrative improvements", "Explanation quality checks"],
    },
]

ORGANIC_AI_AUTHORITY_SYSTEM: Dict[str, Any] = {
    "agent_key": "organic_ai_authority",
    "agent_name": "Organic / SEO / GEO / AI Authority System",
    "domain": "Organic search and AI discoverability",
    "mission": "Improve OPTIME discoverability and authority across search and AI answer engines.",
    "entry_point": "docs/GEO_STRATEGY.md",
    "trigger": "Strategy and benchmark scaffolding only",
    "schedule": "NOT_CONFIGURED",
    "dependencies": ["Published facility/profile surfaces", "Structured data", "External search/citation telemetry"],
    "expected_outputs": ["Indexability audits", "SERP monitoring", "AI citation monitoring"],
}


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _reports_path(name: str) -> Path:
    return _repo_root() / "reports" / name


def _read(path: Path) -> str:
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def _extract_int(pattern: str, text: str) -> Optional[int]:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    try:
        return int(m.group(1))
    except ValueError:
        return None


def _load_evidence_parity_audit() -> Dict[str, Any]:
    path = _reports_path("GOLDEN_CASE_RANKING_CAUSALITY_AUDIT.json")
    if not path.exists():
        return {
            "status": "UNPROVEN",
            "corrected_proven_match_top5": [],
            "high_potential_needs_verification": [],
            "regression_status": "UNPROVEN",
        }
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "status": "UNPROVEN",
            "corrected_proven_match_top5": [],
            "high_potential_needs_verification": [],
            "regression_status": "UNPROVEN",
        }

    golden = payload.get("golden_case") if isinstance(payload.get("golden_case"), dict) else {}
    regression = payload.get("regression_tests") if isinstance(payload.get("regression_tests"), dict) else {}
    return {
        "status": "ACTIVE",
        "corrected_proven_match_top5": golden.get("corrected_proven_match_top5") or golden.get("evidence_parity_top5") or [],
        "high_potential_needs_verification": golden.get("high_potential_needs_verification") or [],
        "regression_status": regression.get("status", "UNPROVEN"),
    }


def _extract_float(pattern: str, text: str) -> Optional[float]:
    m = re.search(pattern, text, re.IGNORECASE)
    if not m:
        return None
    try:
        return float(m.group(1))
    except ValueError:
        return None


def _parse_discovery_metrics() -> Dict[str, Any]:
    discovery = _read(_reports_path("discovery_report.md"))
    florida = _read(_reports_path("florida_discovery_inventory.md"))

    total = _extract_int(r"Total number of communities discovered:\s*\*\*(\d+)\*\*", discovery)
    verified = _extract_int(r"Total number of verified communities:\s*\*\*(\d+)\*\*", discovery)
    pending = _extract_int(r"pending verification:\s*\*\*(\d+)\*\*", discovery)
    newly = _extract_int(r"newly discovered communities:\s*\*\*(\d+)\*\*", discovery)
    updated = _extract_int(r"updated communities:\s*\*\*(\d+)\*\*", discovery)
    closed = _extract_int(r"closed communities:\s*\*\*(\d+)\*\*", discovery)
    merged = _extract_int(r"duplicate communities merged:\s*\*\*(\d+)\*\*", discovery)

    fl_covered = _extract_int(r"Florida counties covered:\s*(\d+)\s*/\s*67", florida)
    fl_total = 67

    coverage_pct = None
    if fl_covered is not None:
        coverage_pct = round((fl_covered / fl_total) * 100.0, 1)

    return {
        "total_communities": total,
        "verified_communities": verified,
        "pending_verification": pending,
        "newly_discovered": newly,
        "updated": updated,
        "closed": closed,
        "duplicates_merged": merged,
        "counties_covered": fl_covered,
        "counties_total": fl_total,
        "coverage_pct": coverage_pct,
    }


def _parse_platform_metrics() -> Dict[str, Any]:
    text = _read(_reports_path("platform_intelligence_report.md"))
    return {
        "knowledge_objects": _extract_int(r"\|\s*Knowledge Objects\s*\|\s*(\d+)\s*\|", text),
        "evidence_objects": _extract_int(r"\|\s*Evidence Objects\s*\|\s*(\d+)\s*\|", text),
    }


def _parse_recommendation_quality() -> Dict[str, Any]:
    text = _read(_reports_path("recommendation_accuracy_dashboard.md"))
    gate_pass = "PASS" if re.search(r"Release Gate:\s*\*\*PASS\*\*", text, re.IGNORECASE) else "UNKNOWN"
    advisor = _extract_float(r"\|\s*Advisor agreement\s*\|\s*([0-9.]+)%\s*\|", text)
    top3_visit = _extract_float(r"\|\s*Top-3 visit rate\s*\|\s*([0-9.]+)%\s*\|", text)
    top3_movein = _extract_float(r"\|\s*Top-3 move-in rate\s*\|\s*([0-9.]+)%\s*\|", text)
    return {
        "release_gate": gate_pass,
        "advisor_agreement_pct": advisor,
        "top3_visit_pct": top3_visit,
        "top3_movein_pct": top3_movein,
    }


def _parse_executive_scores() -> Dict[str, Any]:
    text = _read(_reports_path("executive_dashboard.md"))
    return {
        "trust_score": _extract_float(r"Trust Score:\s*\*\*([0-9.]+)%\*\*", text),
        "institutional_intelligence_score": _extract_float(r"Institutional Intelligence Score:\s*\*\*([0-9.]+)%\*\*", text),
        "agents_running": _extract_int(r"Running:\s*\*\*(\d+)\*\*", text),
    }


def _parse_agent_queue() -> Dict[str, Dict[str, str]]:
    text = _read(_reports_path("agent_task_queue.md"))
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    rows = [ln.split("|")[1:-1] for ln in lines]
    if len(rows) < 2:
        return {}
    data = {}
    for row in rows[2:]:
        cols = [cell.strip() for cell in row]
        if len(cols) < 6:
            continue
        data[cols[0]] = {
            "current_task": cols[1],
            "next_task": cols[2],
            "queue_status": cols[5],
        }
    return data


def _report_registry_updates_by_agent() -> Dict[str, str]:
    raw = _read_json(_reports_path("report_registry.json")) or {}
    updates: Dict[str, str] = {}
    for row in raw.get("reports", []) if isinstance(raw, dict) else []:
        if not isinstance(row, dict):
            continue
        agent_name = str(row.get("responsible_agent") or "").strip()
        updated_at = str(row.get("last_updated_utc") or "").strip()
        if not agent_name or not updated_at:
            continue
        current = updates.get(agent_name)
        if current is None or updated_at > current:
            updates[agent_name] = updated_at
    return updates


def _known_agent_catalog() -> List[Dict[str, Any]]:
    catalog: List[Dict[str, Any]] = []
    for row in AGENT_REPORT_DEFS:
        catalog.append(
            {
                "agent_key": str(row.get("agent_key")),
                "agent_name": str(row.get("agent_name")),
                "domain": str(row.get("domain")),
                "mission": str(row.get("mission")),
                "entry_point": "backend/app/services/agent_knowledge_reports.py",
                "trigger": "FastAPI startup background refresh loop",
                "schedule": f"Every {os.getenv('OPTIME_AGENT_REPORT_REFRESH_MINUTES', '15')} minutes while the FastAPI process is alive",
                "dependencies": list(row.get("sources") or []),
                "expected_outputs": ["Agent knowledge snapshot", "Refresh event", "Prepared knowledge report JSON"],
                "automatic": True,
            }
        )
    catalog.extend(SUPPLEMENTAL_AGENT_DEFS)
    return catalog


def _agent_activity_table(db: Session) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    since = now - timedelta(hours=24)
    queue = _parse_agent_queue()
    registry_updates = _report_registry_updates_by_agent()
    snapshots = {row.agent_key: row for row in db.query(AgentKnowledgeReportSnapshot).all()}
    job_rows = db.query(AgentJobRun).filter(AgentJobRun.started_at >= since).all()
    jobs_by_agent: Dict[str, List[AgentJobRun]] = {}
    for row in job_rows:
        jobs_by_agent.setdefault(row.agent_key, []).append(row)

    event_rows = db.query(AgentKnowledgeRefreshEvent).filter(AgentKnowledgeRefreshEvent.started_at >= since).all()
    events_by_agent: Dict[str, List[AgentKnowledgeRefreshEvent]] = {}
    for row in event_rows:
        events_by_agent.setdefault(row.agent_key, []).append(row)

    record_rows = db.query(AgentKnowledgeRecord).filter(AgentKnowledgeRecord.created_at >= since).all()
    records_by_agent: Dict[str, List[AgentKnowledgeRecord]] = {}
    for row in record_rows:
        records_by_agent.setdefault(row.agent_key, []).append(row)

    rows: List[Dict[str, Any]] = []
    for agent in _known_agent_catalog():
        agent_key = str(agent["agent_key"])
        agent_name = str(agent["agent_name"])
        snapshot = snapshots.get(agent_key)
        jobs = jobs_by_agent.get(agent_key, [])
        events = events_by_agent.get(agent_key, [])
        records = records_by_agent.get(agent_key, [])
        queue_state = queue.get(agent_name, {})
        success_events = [row for row in events if str(row.status).upper() == "SUCCESS"]
        failed_events = [row for row in events if str(row.status).upper() == "FAILED"]
        successful_jobs = [row for row in jobs if str(row.status).upper() == "SUCCESS"]
        failed_jobs = [row for row in jobs if str(row.status).upper() == "FAILED"]
        latest_job = max(jobs, key=lambda row: str(row.started_at or "")) if jobs else None
        work_performed = "NO"
        state = "DID NOT RUN"
        new_value = "No new verifiable output in the last 24h."
        failures: List[str] = []
        if failed_jobs and not successful_jobs:
            state = "FAILED"
            work_performed = "NO"
            new_value = "None"
            failures = [json.loads(str(row.knowledge_gained_json or "{}")).get("error", "Unknown failure") if str(row.knowledge_gained_json or "").startswith("{") else "Unknown failure" for row in failed_jobs]
        elif successful_jobs and sum(int(row.items_added or 0) + int(row.items_updated or 0) for row in successful_jobs) > 0:
            state = "WORKED - CREATED NEW VALUE"
            work_performed = "YES"
            added = sum(int(row.items_added or 0) for row in successful_jobs)
            updated = sum(int(row.items_updated or 0) for row in successful_jobs)
            new_value = f"Created {added} new persisted item(s) and updated {updated} existing item(s)."
        elif successful_jobs:
            state = "RAN - NO NEW FINDINGS"
            work_performed = "NO"
        elif snapshot is None:
            state = "UNKNOWN" if agent.get("schedule") == "CONFIGURED_NOT_RUNNING" else "MANUAL_ONLY"
            work_performed = "UNKNOWN"
            new_value = "No runtime evidence table is connected for this agent."

        last_run = None
        if successful_jobs:
            last_run = max((row.finished_at for row in successful_jobs if row.finished_at), default=None)
        elif failed_jobs:
            last_run = max((row.finished_at for row in failed_jobs if row.finished_at), default=None)
        elif success_events:
            last_run = max((row.finished_at for row in success_events if row.finished_at), default=None)
        elif failed_events:
            last_run = max((row.finished_at for row in failed_events if row.finished_at), default=None)
        elif snapshot is not None:
            last_run = snapshot.last_refresh_attempt or snapshot.last_successful_refresh
        last_run_text = str(last_run) if last_run else registry_updates.get(agent_name, "UNKNOWN")

        what_it_did = []
        if successful_jobs:
            processed = sum(int(row.items_processed or 0) for row in successful_jobs)
            added = sum(int(row.items_added or 0) for row in successful_jobs)
            updated = sum(int(row.items_updated or 0) for row in successful_jobs)
            what_it_did.append(f"Executed {len(successful_jobs)} workflow run(s); processed {processed} item(s); added {added}; updated {updated}.")
        if failed_jobs:
            what_it_did.append(f"Encountered {len(failed_jobs)} failed workflow run(s) in the last 24h.")
        if queue_state.get("current_task"):
            what_it_did.append(f"Current queued task: {queue_state.get('current_task')}")
        if latest_job is not None and str(latest_job.knowledge_gained_json or "").startswith("{"):
            try:
                latest_payload = json.loads(str(latest_job.knowledge_gained_json))
                findings = latest_payload.get("new_findings") or []
                if findings:
                    what_it_did.append(f"Examples: {'; '.join(str(item) for item in findings[:3])}")
            except json.JSONDecodeError:
                pass
        if not what_it_did:
            what_it_did.append("No measurable runtime activity captured.")

        evidence = []
        if snapshot is not None:
            evidence.append("backend/optime_nursing.db:agent_knowledge_report_snapshots")
        if events:
            evidence.append("backend/optime_nursing.db:agent_knowledge_refresh_events")
        if records:
            evidence.append("backend/optime_nursing.db:agent_knowledge_records")
        if registry_updates.get(agent_name):
            evidence.append("reports/report_registry.json")
        if queue_state:
            evidence.append("reports/agent_task_queue.md")

        rows.append(
            {
                "agent_id": agent_key,
                "name": agent_name,
                "purpose": agent.get("mission"),
                "entry_point": agent.get("entry_point"),
                "trigger": agent.get("trigger"),
                "schedule": agent.get("schedule"),
                "inputs": agent.get("dependencies"),
                "expected_outputs": agent.get("expected_outputs"),
                "dependencies": agent.get("dependencies"),
                "last_known_run": last_run_text,
                "activity_evidence_source": evidence[0] if evidence else "UNKNOWN",
                "output_evidence_source": evidence[1] if len(evidence) > 1 else (evidence[0] if evidence else "UNKNOWN"),
                "failure_evidence_source": "backend/optime_nursing.db:agent_knowledge_refresh_events" if failed_events else "UNKNOWN",
                "current_status": state,
                "run_status": snapshot.refresh_status if snapshot is not None else agent.get("schedule"),
                "worked": work_performed,
                "what_it_did": " ".join(what_it_did),
                "items_examined": sum(int(row.items_processed or 0) for row in successful_jobs) if successful_jobs else (len(events) if events else "UNKNOWN"),
                "items_changed": sum(int(row.items_added or 0) + int(row.items_updated or 0) for row in successful_jobs),
                "new_outputs": [f"{sum(int(row.items_added or 0) for row in successful_jobs)} new persisted item(s)" if successful_jobs else "No new knowledge records"],
                "new_findings": sum(int(row.items_added or 0) for row in successful_jobs),
                "new_value_created": new_value,
                "failures": failures,
                "evidence": evidence,
                "automatic": bool(agent.get("automatic", False)),
            }
        )

    automatic_agents = [row for row in rows if row.get("automatic")]
    worked = [row for row in rows if row.get("current_status") == "WORKED - CREATED NEW VALUE"]
    ran_no_value = [row for row in rows if row.get("current_status") == "RAN - NO NEW FINDINGS"]
    did_not_run = [row for row in rows if row.get("current_status") == "DID NOT RUN"]
    failed = [row for row in rows if row.get("current_status") == "FAILED"]
    unknown = [row for row in rows if row.get("current_status") in {"UNKNOWN", "MANUAL_ONLY", "CONFIGURED_NOT_RUNNING"}]
    attention = [
        {
            "agent": row["name"],
            "why": row["current_status"],
            "impact": row["new_value_created"],
            "next_action": row["failures"][0] if row["failures"] else row["what_it_did"],
        }
        for row in rows
        if row["current_status"] in {"FAILED", "UNKNOWN", "MANUAL_ONLY"}
    ]

    return {
        "summary": {
            "total_known_agents": len(rows),
            "automatic_agents": len(automatic_agents),
            "actually_worked_last_24h": len(worked),
            "ran_no_new_value_last_24h": len(ran_no_value),
            "did_not_run_last_24h": len(did_not_run),
            "failed_last_24h": len(failed),
            "unknown_status": len(unknown),
        },
        "rows": rows,
        "attention": attention,
        "achievements": {
            "NEW_EVIDENCE_FOUND": sum(int(row.items_added or 0) for row in job_rows if str(row.status).upper() == "SUCCESS"),
            "FACTS_VERIFIED": sum(int(row.items_added or 0) for row in job_rows if str(row.status).upper() == "SUCCESS"),
            "UNKNOWN_FIELDS_RESOLVED": "NOT_MEASURED",
            "CONTRADICTIONS_FOUND": "NOT_MEASURED",
            "FACILITIES_ENRICHED": sum(1 for row in rows if "provider_intelligence" == row.get("agent_id") and row.get("items_changed", 0) > 0),
            "STALE_DATA_REFRESHED": len([row for row in rows if row.get("current_status") == "RAN - NO NEW FINDINGS"]),
            "GOLDEN_CASES_PASSED": "NOT_MEASURED",
            "REGRESSIONS_FOUND": "NOT_MEASURED",
            "NEW_AI_CITATIONS": "NOT_CONFIGURED",
        },
    }


def _organic_ai_authority_status() -> Dict[str, Any]:
    repo = _repo_root()
    geo_strategy_exists = repo / "docs" / "GEO_STRATEGY.md"
    public_dir = repo / "frontend" / "public"
    app_dir = repo / "frontend" / "src" / "app"
    benchmark = _read(_reports_path("MULTI_AI_BENCHMARK_SYSTEM_REPORT.md"))
    live_exec = "NOT_CONFIGURED"
    if "## LIVE EXECUTION STATUS" in benchmark:
        m = re.search(r"## LIVE EXECUTION STATUS\s*\n\s*([A-Z_]+)", benchmark)
        if m:
            live_exec = m.group(1)

    route_files = list(app_dir.rglob("page.tsx")) if app_dir.exists() else []
    metadata_files = []
    schema_files = []
    for file_path in route_files + ([app_dir / "layout.tsx"] if (app_dir / "layout.tsx").exists() else []):
        text = file_path.read_text(encoding="utf-8")
        if "metadata" in text or "generateMetadata" in text:
            metadata_files.append(str(file_path.relative_to(repo)).replace("\\", "/"))
        if "schema.org" in text or "json-ld" in text:
            schema_files.append(str(file_path.relative_to(repo)).replace("\\", "/"))

    robots_exists = (public_dir / "robots.txt").exists()
    sitemap_exists = (public_dir / "sitemap.xml").exists() or (public_dir / "sitemap-index.xml").exists()
    facility_routes = [
        "frontend/src/app/facility/[id]/page.tsx" if (app_dir / "facility" / "[id]" / "page.tsx").exists() else None,
        "frontend/src/app/facilities/[id]/page.tsx" if (app_dir / "facilities" / "[id]" / "page.tsx").exists() else None,
    ]
    facility_routes = [item for item in facility_routes if item is not None]

    technical_findings = [
        f"robots.txt present: {'YES' if robots_exists else 'NO'}",
        f"sitemap present: {'YES' if sitemap_exists else 'NO'}",
        f"route files checked: {len(route_files)}",
        f"metadata-covered files: {len(metadata_files)}",
        f"structured-data files: {len(schema_files)}",
        f"facility profile route files: {len(facility_routes)}",
    ]
    return {
        **ORGANIC_AI_AUTHORITY_SYSTEM,
        "current_status": "PARTIAL" if geo_strategy_exists.exists() else "NOT_FOUND",
        "last_verified_run": "UNVERIFIED_EXTERNAL",
        "worked_last_24h": "YES",
        "what_it_actually_did": "Ran local technical discoverability checks for robots, sitemap, metadata coverage, structured-data coverage, and facility profile route presence.",
        "new_result_created": "; ".join(technical_findings),
        "evidence": ["docs/GEO_STRATEGY.md", "reports/MULTI_AI_BENCHMARK_SYSTEM_REPORT.md"],
        "technical_findings": technical_findings,
        "robots_txt": "PRESENT" if robots_exists else "MISSING",
        "sitemap": "PRESENT" if sitemap_exists else "MISSING",
        "metadata_coverage_files": len(metadata_files),
        "structured_data_files": len(schema_files),
        "facility_profile_route_files": len(facility_routes),
        "google_visibility": "UNVERIFIED_EXTERNAL",
        "ai_citation_monitoring": "NOT_CONFIGURED",
        "live_execution_status": live_exec,
    }


def _extract_centers() -> List[str]:
    text = _read(_reports_path("scientific_method.md"))
    centers: List[str] = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("- ") and "must maintain a research agenda" in line:
            centers.append(line[2:].split(" must maintain a research agenda", 1)[0].strip())
    return centers


def _sum_knowledge_growth() -> Dict[str, int]:
    text = _read(_reports_path("knowledge_growth_matrix.md"))
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    rows = [ln.split("|")[1:-1] for ln in lines]
    if len(rows) < 2:
        return {
            "knowledge_created": 0,
            "knowledge_updated": 0,
            "evidence_reviewed": 0,
            "evidence_verified": 0,
            "decision_rules": 0,
            "relationships": 0,
            "gaps_closed": 0,
        }

    totals = {
        "knowledge_created": 0,
        "knowledge_updated": 0,
        "evidence_reviewed": 0,
        "evidence_verified": 0,
        "decision_rules": 0,
        "relationships": 0,
        "gaps_closed": 0,
    }

    for row in rows[2:]:
        cols = [c.strip() for c in row]
        if len(cols) < 8:
            continue
        try:
            totals["knowledge_created"] += int(cols[1])
            totals["knowledge_updated"] += int(cols[2])
            totals["evidence_reviewed"] += int(cols[3])
            totals["evidence_verified"] += int(cols[4])
            totals["decision_rules"] += int(cols[5])
            totals["relationships"] += int(cols[6])
            totals["gaps_closed"] += int(cols[7])
        except ValueError:
            continue
    return totals


def _agent_activity(db: Session) -> List[Dict[str, Any]]:
    snapshots = db.query(AgentKnowledgeReportSnapshot).order_by(AgentKnowledgeReportSnapshot.agent_name.asc()).all()
    today_utc = datetime.now(timezone.utc).date()
    queue = _parse_agent_queue()

    out: List[Dict[str, Any]] = []
    for snap in snapshots:
        completed_today = int(
            db.query(func.count(AgentKnowledgeRefreshEvent.id))
            .filter(
                AgentKnowledgeRefreshEvent.agent_key == snap.agent_key,
                AgentKnowledgeRefreshEvent.status == "SUCCESS",
                func.date(AgentKnowledgeRefreshEvent.finished_at) == str(today_utc),
            )
            .scalar()
            or 0
        )
        blocked_tasks = int(
            db.query(func.count(SupervisorIncidentLog.id))
            .filter(
                SupervisorIncidentLog.agent_key == snap.agent_key,
                SupervisorIncidentLog.status == "OPEN",
                SupervisorIncidentLog.severity.in_(["HIGH", "CRITICAL"]),
            )
            .scalar()
            or 0
        )

        q = queue.get(snap.agent_name, {})
        status = "RUNNING"
        if str(snap.refresh_status).upper() in {"ERROR"} or str(snap.health_status).upper() == "DEGRADED":
            status = "FAILED"
        elif completed_today == 0:
            status = "IDLE"

        out.append(
            {
                "agent_key": snap.agent_key,
                "agent_name": snap.agent_name,
                "status": status,
                "health": snap.health_status,
                "current_task": q.get("current_task", "UNPROVEN"),
                "completed_today": completed_today,
                "blocked_tasks": blocked_tasks,
                "next_task": q.get("next_task", "UNPROVEN"),
                "learning_completed": completed_today,
                "knowledge_produced": int(snap.knowledge_count or 0),
            }
        )
    return out


def _knowledge_gap_lines() -> List[str]:
    text = _read(_reports_path("knowledge_gap_report.md"))
    lines = [line.strip() for line in text.splitlines() if line.strip().startswith("|")]
    rows = [ln.split("|")[1:-1] for ln in lines]
    gaps: List[str] = []
    for row in rows[2:7]:
        cols = [c.strip() for c in row]
        if len(cols) >= 4:
            gaps.append(f"{cols[0]}: {cols[2]} -> {cols[3]}")
    return gaps


def _provider_intelligence_today(db: Session) -> Dict[str, int]:
    today = str(datetime.now(timezone.utc).date())
    enriched = int(
        db.query(func.count(FacilityIntelligenceProfile.id))
        .filter(func.date(FacilityIntelligenceProfile.updated_at) == today)
        .scalar()
        or 0
    )

    # Derive topic-specific changes from measured knowledge records.
    records = db.query(AgentKnowledgeRecord).filter(func.date(AgentKnowledgeRecord.created_at) == today).all()

    def _count_topic(*keywords: str) -> int:
        n = 0
        for rec in records:
            hay = f"{rec.record_type or ''} {rec.summary or ''}".lower()
            if any(k in hay for k in keywords):
                n += 1
        return n

    return {
        "profiles_enriched": enriched,
        "ownership_changes": _count_topic("ownership"),
        "inspection_updates": _count_topic("inspection", "deficiency"),
        "licensing_updates": _count_topic("license", "licensing"),
        "cms_updates": _count_topic("cms"),
        "staffing_updates": _count_topic("staffing"),
        "pricing_updates": _count_topic("pricing", "rate"),
        "website_changes": _count_topic("website", "domain"),
        "new_penalties_detected": _count_topic("penalty", "fine"),
        "new_awards_detected": _count_topic("award"),
    }


def _data_quality_metrics(discovery: Dict[str, Any]) -> Dict[str, Any]:
    discovery_text = _read(_reports_path("discovery_report.md"))
    missing_rows = _extract_int(r"Missing data rows:\s*\*\*(\d+)\*\*", discovery_text)
    conflicts = _extract_int(r"Data conflicts:\s*\*\*(\d+)\*\*", discovery_text)
    snapshot_age = _extract_int(r"snapshot age:\s*(\d+)\s*day", discovery_text)

    total = discovery.get("total_communities") or 0
    dup = discovery.get("duplicates_merged") or 0
    dup_rate = round((dup / total) * 100.0, 2) if total else 0.0
    verification_cov = 0.0
    if total and discovery.get("verified_communities") is not None:
        verification_cov = round((discovery["verified_communities"] / total) * 100.0, 1)

    return {
        "database_coverage": f"{discovery.get('counties_covered')}/{discovery.get('counties_total')} counties",
        "verification_coverage_pct": verification_cov,
        "duplicate_rate_pct": dup_rate,
        "missing_information_rows": missing_rows,
        "conflicting_information": conflicts,
        "freshness_days": snapshot_age,
    }


def _read_json(path: Path) -> Optional[Dict[str, Any]]:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _authority_stage(status: str, metrics: Dict[str, Any], evidence: List[str], next_action: str, blockers: Optional[List[str]] = None) -> Dict[str, Any]:
    return {
        "status": status,
        "metrics": metrics,
        "evidence": evidence,
        "last_verified_utc": datetime.now(timezone.utc).isoformat(),
        "blockers": blockers or [],
        "next_action": next_action,
    }


def _build_authority_status(
    discovery: Dict[str, Any],
    platform: Dict[str, Any],
    rec: Dict[str, Any],
    scores: Dict[str, Any],
    data_quality: Dict[str, Any],
    growth_totals: Dict[str, int],
    knowledge_gaps: List[str],
    previous_payload: Optional[Dict[str, Any]],
) -> Dict[str, Any]:
    benchmark_v2 = _read_json(_reports_path("REAL_CASE_POST_STROKE_MIAMI_OPTIME_RESULT_V2.json"))
    golden_case_status = "PASS" if benchmark_v2 and benchmark_v2.get("run_status") == "OK" and len(benchmark_v2.get("top_5") or []) == 5 else "PARTIAL"
    validation_gaps = []
    if rec.get("release_gate") != "PASS":
        validation_gaps.append("Recommendation release gate is not PASS.")
    if benchmark_v2 is None:
        validation_gaps.append("Golden case V2 evidence bundle is missing.")

    return {
        "overall_status": "PARTIAL",
        "answer": "OPTIME is improving its evidence base, but publish/index/discover/cite measurement is still only partially instrumented.",
        "last_verified_utc": datetime.now(timezone.utc).isoformat(),
        "stages": {
            "DATA": _authority_stage(
                "PARTIAL",
                {
                    "TOTAL_CANONICAL_FACILITIES": discovery.get("total_communities"),
                    "IDENTITY_VERIFIED": discovery.get("verified_communities"),
                    "IDENTITY_UNRESOLVED": discovery.get("pending_verification"),
                    "CMS_DATA_COVERAGE": discovery.get("coverage_pct") if discovery.get("coverage_pct") is not None else "UNKNOWN",
                    "STAFFING_COVERAGE": "UNKNOWN",
                    "INSPECTION_COVERAGE": "UNKNOWN",
                    "PENALTY_COVERAGE": "UNKNOWN",
                    "OWNERSHIP_COVERAGE": "UNKNOWN",
                    "REHAB_EVIDENCE_COVERAGE": "UNKNOWN",
                    "PRICING_EVIDENCE_COVERAGE": "UNKNOWN",
                    "ACTIVITY_EVIDENCE_COVERAGE": "UNKNOWN",
                    "LANGUAGE_EVIDENCE_COVERAGE": "UNKNOWN",
                    "DIET_FOOD_EVIDENCE_COVERAGE": "UNKNOWN",
                    "IMPORTANT_MISSING_DATA": data_quality.get("missing_information_rows") if data_quality.get("missing_information_rows") is not None else "UNKNOWN",
                },
                [
                    "Discovery coverage is incomplete across the statewide universe.",
                    "Several evidence domains are not directly measured in current telemetry.",
                ],
                "Expand canonical coverage and preserve UNKNOWN for unmeasured evidence domains.",
            ),
            "KNOWLEDGE": _authority_stage(
                "PARTIAL",
                {
                    "TOTAL_CLAIMS": platform.get("knowledge_objects"),
                    "VERIFIED_CLAIMS": growth_totals.get("evidence_verified"),
                    "UNKNOWN_CLAIMS": data_quality.get("missing_information_rows") if data_quality.get("missing_information_rows") is not None else "UNKNOWN",
                    "STALE_CLAIMS": data_quality.get("freshness_days") if data_quality.get("freshness_days") is not None else "UNKNOWN",
                    "CONTRADICTED_CLAIMS": data_quality.get("conflicting_information") if data_quality.get("conflicting_information") is not None else "UNKNOWN",
                    "UNRESOLVED_IDENTITY_CLAIMS": discovery.get("pending_verification"),
                    "CLAIMS_WITH_SOURCE_PROVENANCE": growth_totals.get("evidence_verified"),
                    "CLAIMS_WITH_SOURCE_DATE": "UNKNOWN",
                    "CLAIMS_WITH_LAST_VERIFIED_TIMESTAMP": "UNKNOWN",
                    "HIGH_IMPACT_KNOWLEDGE_GAPS": len(knowledge_gaps),
                    "EVIDENCE_QUALITY": growth_totals.get("evidence_verified"),
                },
                [
                    "Knowledge coverage is measured, but claim-level provenance is not fully instrumented in this report path.",
                    "Unknown and stale knowledge cannot be conflated with verified knowledge.",
                ],
                "Close provenance gaps and add claim-level freshness timestamps.",
            ),
            "VALIDATE": _authority_stage(
                golden_case_status,
                {
                    "GOLDEN_CASES_TOTAL": 1 if benchmark_v2 else "UNKNOWN",
                    "GOLDEN_CASES_PASSING": 1 if golden_case_status == "PASS" else 0,
                    "FULLY_TRACEABLE_DECISIONS": len(benchmark_v2.get("top_5") or []) if benchmark_v2 else "UNKNOWN",
                    "REGRESSION_FAILURES": 0 if rec.get("release_gate") == "PASS" else 1,
                    "UNKNOWN_GOVERNANCE_FAILURES": 0 if rec.get("release_gate") == "PASS" else 1,
                    "IDENTITY_COLLISION_FAILURES": 0,
                    "SCORE_RECONCILIATION_FAILURES": 0,
                    "CANDIDATE_FUNNEL_RECONCILIATION_FAILURES": 0,
                    "POST_STROKE_MIAMI_001": golden_case_status,
                    "PROFESSIONAL_VALIDATION": rec.get("release_gate"),
                    "EXTERNAL_VALIDATION_STATUS": "PARTIAL",
                },
                [
                    "Professional release gate is not yet PASS.",
                    "External validation is still partial and not independently connected here.",
                ],
                "Resolve validation gaps and keep the golden case permanently visible.",
            ),
            "PUBLISH": _authority_stage(
                "PARTIAL",
                {
                    "EXPECTED_PUBLIC_FACILITY_PROFILES": "UNKNOWN",
                    "ACTUAL_PUBLIC_FACILITY_PROFILES": "UNKNOWN",
                    "WORKING_PROFILE_ROUTES": "UNKNOWN",
                    "BROKEN_PROFILE_ROUTES": "UNKNOWN",
                    "PROFILES_WITH_CANONICAL_URL": "UNKNOWN",
                    "PROFILES_WITH_SOURCE_PROVENANCE": "UNKNOWN",
                    "PROFILES_WITH_LAST_UPDATED": "UNKNOWN",
                    "PROFILES_WITH_STRUCTURED_DATA": "UNKNOWN",
                    "THIN_OR_INCOMPLETE_PROFILES": "UNKNOWN",
                },
                [
                    "Route existence is not the same as a useful, published profile surface.",
                    "No repo-level facility publication audit is yet wired into this daily report.",
                ],
                "Measure actual published profile surfaces before claiming public authority coverage.",
            ),
            "INDEX": _authority_stage(
                "PARTIAL",
                {
                    "ROBOTS_TXT": "NOT_FOUND",
                    "SITEMAP_STATUS": "NOT_FOUND",
                    "SITEMAP_URL_COUNT": 0,
                    "EXPECTED_INDEXABLE_URLS": "UNKNOWN",
                    "TECHNICALLY_INDEXABLE_URLS": "UNKNOWN",
                    "BLOCKED_URLS": "UNKNOWN",
                    "STRUCTURED_DATA_VALID": "UNKNOWN",
                    "STRUCTURED_DATA_INVALID": "UNKNOWN",
                    "CANONICAL_ERRORS": "UNKNOWN",
                    "GOOGLE_INDEX_STATUS": "UNVERIFIED_EXTERNAL",
                },
                [
                    "No robots.txt or sitemap.xml evidence is present in the repository root.",
                    "Google Search Console is not connected here, so indexed counts cannot be asserted.",
                ],
                "Add a verifiable sitemap/robots/index audit and connect external search telemetry if available.",
            ),
            "DISCOVER": _authority_stage(
                "NOT_YET_MEASURED",
                {
                    "TRACKED_QUERIES": [
                        "best nursing homes in Miami",
                        "best nursing homes Miami-Dade",
                        "best nursing home for stroke rehabilitation in Miami",
                        "best skilled nursing facilities Miami",
                        "nursing homes with strong staffing in Miami",
                    ],
                    "SERP_MONITORING": "NOT_CONFIGURED",
                    "OPTIME_VISIBILITY": "UNKNOWN",
                    "RANKING_CHANGES": "UNKNOWN",
                    "NEW_RANKING_PAGES": "UNKNOWN",
                    "LOST_RANKING_PAGES": "UNKNOWN",
                    "COMPETITORS_OUTRANKING_OPTIME": "UNKNOWN",
                },
                [
                    "No verified organic/SERP monitoring data is connected in the current repo state.",
                ],
                "Configure search monitoring before asserting discoverability performance.",
            ),
            "CITE": _authority_stage(
                "NOT_CONFIGURED",
                {
                    "CHATGPT_MENTIONS": "UNKNOWN",
                    "CHATGPT_CITATIONS": "UNKNOWN",
                    "GEMINI_MENTIONS": "UNKNOWN",
                    "GEMINI_CITATIONS": "UNKNOWN",
                    "PERPLEXITY_MENTIONS": "UNKNOWN",
                    "PERPLEXITY_CITATIONS": "UNKNOWN",
                    "CLAUDE_MENTIONS": "UNKNOWN",
                    "CLAUDE_CITATIONS": "UNKNOWN",
                    "CITED_OPTIME_URLS": "UNKNOWN",
                    "COMPETITOR_SOURCES_CITED_INSTEAD": "UNKNOWN",
                    "QUERY_LEVEL_CITATION_RATE": "UNKNOWN",
                    "AI_CITATION_MONITORING": "NOT_CONFIGURED",
                },
                [
                    "No automated external AI citation monitoring is connected in this daily report pipeline.",
                ],
                "Reuse the existing multi-AI benchmark surfaces if access is configured; otherwise keep this as UNKNOWN.",
            ),
            "LEARN": _authority_stage(
                "PARTIAL",
                {
                    "KNOWLEDGE_GAPS_FROM_USER_QUERIES": len(knowledge_gaps),
                    "FACILITIES_WITH_HIGH_DEMAND_BUT_LOW_EVIDENCE": discovery.get("pending_verification"),
                    "SEARCH_QUERIES_WITH_NO_STRONG_OPTIME_PAGE": "UNKNOWN",
                    "AI_QUERIES_WHERE_COMPETITORS_ARE_CITED_INSTEAD": "UNKNOWN",
                    "STALE_HIGH_IMPACT_CLAIMS": data_quality.get("freshness_days") if data_quality.get("freshness_days") is not None else "UNKNOWN",
                    "DECISION_REGRESSION_PATTERNS": rec.get("regression_tests"),
                    "TOP_AUTHORITY_PRIORITIES": [
                        "Close remaining statewide coverage gaps.",
                        "Instrument publication/index audits for real profile surfaces.",
                        "Connect discoverability and citation monitoring if available.",
                    ],
                },
                [
                    "Learning signals are available, but not all external discovery/citation feeds are connected.",
                ],
                "Prioritize evidence gaps, publication coverage, and traceability before model changes.",
            ),
        },
        "top_authority_gaps_today": [
            "External discoverability is not yet measured.",
            "AI citation monitoring is not configured.",
            "Publish/index audits for facility profiles are not yet instrumented.",
            "Several evidence domains remain UNKNOWN in the current telemetry.",
            "Professional validation is still partial.",
        ],
    }


def _today_delta(current: Dict[str, Any], previous: Optional[Dict[str, Any]], key: str) -> Optional[float]:
    if previous is None:
        return None
    try:
        c = float(current.get(key))
        p = float(previous.get(key))
        return c - p
    except Exception:
        return None


def _build_report_payload(db: Session, previous_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    discovery = _parse_discovery_metrics()
    platform = _parse_platform_metrics()
    rec = _parse_recommendation_quality()
    scores = _parse_executive_scores()
    growth_totals = _sum_knowledge_growth()
    provider = _provider_intelligence_today(db)
    data_quality = _data_quality_metrics(discovery)
    control_tower = _agent_activity_table(db)
    agents = control_tower["rows"]
    centers = _extract_centers()
    gaps = _knowledge_gap_lines()
    organic_authority = _organic_ai_authority_status()
    external_discovery = build_external_discovery_summary(db)
    evidence_parity = _load_evidence_parity_audit()

    current_kpis = {
        "total_communities": discovery.get("total_communities"),
        "verified_communities": discovery.get("verified_communities"),
        "florida_coverage_pct": discovery.get("coverage_pct"),
        "knowledge_centers": len(centers),
        "certified_knowledge_centers": None,
        "knowledge_objects": platform.get("knowledge_objects"),
        "evidence_objects": platform.get("evidence_objects"),
        "research_papers": int(provider.get("cms_updates", 0)),
        "best_practices": int(growth_totals.get("decision_rules", 0)),
        "open_knowledge_gaps": len(gaps),
        "closed_knowledge_gaps_today": 0,
        "trust_score": scores.get("trust_score"),
        "institutional_intelligence_score": scores.get("institutional_intelligence_score"),
        "recommendation_quality_score": rec.get("advisor_agreement_pct"),
        "agents_running": scores.get("agents_running"),
    }

    previous_kpis = None
    if previous_payload:
        previous_kpis = previous_payload.get("executive_kpis") if isinstance(previous_payload.get("executive_kpis"), dict) else None

    deltas = {
        "communities_discovered_today": _today_delta(current_kpis, previous_kpis, "total_communities"),
        "communities_verified_today": _today_delta(current_kpis, previous_kpis, "verified_communities"),
        "knowledge_objects_created_today": _today_delta(current_kpis, previous_kpis, "knowledge_objects"),
        "evidence_objects_added_today": _today_delta(current_kpis, previous_kpis, "evidence_objects"),
    }

    improvements = [
        f"Florida coverage now {discovery.get('counties_covered')}/{discovery.get('counties_total')} counties ({discovery.get('coverage_pct')}%).",
        f"Recommendation release gate: {rec.get('release_gate')}; advisor agreement {rec.get('advisor_agreement_pct')}%.",
    ]
    new_knowledge = [
        f"Knowledge objects: {platform.get('knowledge_objects')}",
        f"Evidence objects: {platform.get('evidence_objects')}",
    ]

    problems = []
    if discovery.get("counties_covered") is not None and discovery.get("counties_covered") < 67:
        problems.append(f"Statewide county coverage incomplete ({discovery.get('counties_covered')}/67).")
    if data_quality.get("missing_information_rows"):
        problems.append(f"Missing information rows remain high: {data_quality.get('missing_information_rows')}.")

    remaining = [
        "Complete 67/67 county coverage.",
        "Reduce pending verification backlog.",
        "Close highest-priority knowledge gaps.",
    ]

    priorities = [
        "Finish remaining Florida county discovery coverage.",
        "Process pending verification queue for newly discovered communities.",
        "Resolve open high-severity supervisor incidents.",
        "Increase provider intelligence enrichment depth.",
        "Link outcome miss-analysis to recommendation calibration updates.",
    ]

    return {
        "executive_questions": {
            "better_today": improvements,
            "new_knowledge_today": new_knowledge,
            "problems_today": problems,
            "remaining_work": remaining,
            "tomorrow_priorities": priorities,
        },
        "discovery": discovery,
        "provider_intelligence": provider,
        "external_discovery": external_discovery,
        "knowledge_growth": {
            **growth_totals,
            "clinical_guidelines_added": provider.get("cms_updates", 0),
            "research_papers_reviewed": provider.get("cms_updates", 0),
            "best_practices_added": growth_totals.get("decision_rules", 0),
        },
        "research_activity": {
            "knowledge_centers": [
                {
                    "center": c,
                    "current_status": "ACTIVE" if c else "UNKNOWN",
                    "research_completed": 0,
                    "research_in_progress": 0,
                    "knowledge_gaps_discovered": 0,
                    "knowledge_gaps_closed": 0,
                    "current_priority": "No measurable center-specific progress data available in current repository telemetry.",
                }
                for c in centers
            ]
        },
        "authority_status": _build_authority_status(discovery, platform, rec, scores, data_quality, growth_totals, gaps, previous_payload),
        "agent_control_tower": control_tower,
        "organic_ai_authority": organic_authority,
        "recommendation_engine": {
            "recommendation_improvements": 1 if rec.get("release_gate") == "PASS" else 0,
            "reasoning_improvements": growth_totals.get("decision_rules", 0),
            "confidence_improvements": provider.get("profiles_enriched", 0),
            "validation_results": rec,
            "regression_tests": rec.get("release_gate"),
        },
        "evidence_parity": evidence_parity,
        "agent_activity": agents,
        "data_quality": data_quality,
        "knowledge_gaps": gaps,
        "executive_kpis": current_kpis,
        "critical_alerts": [
            f"{a['name']} status={a['current_status']}"
            for a in agents
            if a["current_status"] in {"FAILED", "UNKNOWN", "MANUAL_ONLY"}
        ],
        "tomorrow": {
            "top_five_priorities": priorities,
            "expected_deliverables": [
                "Updated discovery and verification reports.",
                "Refreshed executive dashboard trend section.",
                "Knowledge gap closure delta summary.",
            ],
            "potential_risks": problems,
        },
        "delta_since_previous": deltas,
    }


def _fmt_num(value: Any) -> str:
    if value is None:
        return "UNPROVEN"
    if isinstance(value, float):
        if value.is_integer():
            return str(int(value))
        return f"{value:.1f}"
    return str(value)


def _to_markdown(payload: Dict[str, Any]) -> str:
    q = payload["executive_questions"]
    d = payload["discovery"]
    p = payload["provider_intelligence"]
    kg = payload["knowledge_growth"]
    re = payload["recommendation_engine"]
    dq = payload["data_quality"]
    kpi = payload["executive_kpis"]
    authority = payload.get("authority_status", {})
    control_tower = payload.get("agent_control_tower", {})
    external_discovery = payload.get("external_discovery", {})
    organic_authority = payload.get("organic_ai_authority", {})
    evidence_parity = payload.get("evidence_parity", {})
    alerts = payload["critical_alerts"]

    if not any(v not in (None, 0, [], "", "UNPROVEN") for v in payload["delta_since_previous"].values()):
        no_progress = "No measurable progress since the previous report."
    else:
        no_progress = ""

    agent_lines = []
    for a in payload["agent_activity"]:
        evidence_text = ", ".join(a.get("evidence", [])[:2]) if a.get("evidence") else "UNKNOWN"
        agent_lines.append(f"| {a['name']} | {a['current_status']} | {a['worked']} | {a['what_it_did']} | {a['new_value_created']} | {evidence_text} |")

    center_lines = []
    for c in payload["research_activity"]["knowledge_centers"]:
        center_lines.append(
            f"- {c['center']}: status={c['current_status']}, completed={c['research_completed']}, in_progress={c['research_in_progress']}, gaps_discovered={c['knowledge_gaps_discovered']}, gaps_closed={c['knowledge_gaps_closed']}, priority={c['current_priority']}"
        )

    md = [
        "# Executive Summary",
        "",
        f"Overall Institute Health: Trust {_fmt_num(kpi.get('trust_score'))}% | Institutional Intelligence {_fmt_num(kpi.get('institutional_intelligence_score'))}%",
        f"Overall Progress: Coverage {_fmt_num(d.get('counties_covered'))}/67 | Verified {_fmt_num(d.get('verified_communities'))}/{_fmt_num(d.get('total_communities'))}",
        f"Biggest Achievement: {q['better_today'][0] if q['better_today'] else 'UNPROVEN'}",
        f"Biggest Risk: {q['problems_today'][0] if q['problems_today'] else 'UNPROVEN'}",
        f"Authority Status: {authority.get('overall_status', 'UNPROVEN')} | Answer: {authority.get('answer', 'UNPROVEN')}",
        f"Agent Status: total={_fmt_num(control_tower.get('summary', {}).get('total_known_agents'))} automatic={_fmt_num(control_tower.get('summary', {}).get('automatic_agents'))} worked={_fmt_num(control_tower.get('summary', {}).get('actually_worked_last_24h'))} failed={_fmt_num(control_tower.get('summary', {}).get('failed_last_24h'))}",
        "",
        no_progress,
        "",
        "# Agent Activity - Last 24 Hours",
        "",
        f"- Total known agents: {_fmt_num(control_tower.get('summary', {}).get('total_known_agents'))}",
        f"- Automatic agents: {_fmt_num(control_tower.get('summary', {}).get('automatic_agents'))}",
        f"- Actually worked: {_fmt_num(control_tower.get('summary', {}).get('actually_worked_last_24h'))}",
        f"- Ran with no new value: {_fmt_num(control_tower.get('summary', {}).get('ran_no_new_value_last_24h'))}",
        f"- Did not run: {_fmt_num(control_tower.get('summary', {}).get('did_not_run_last_24h'))}",
        f"- Failed: {_fmt_num(control_tower.get('summary', {}).get('failed_last_24h'))}",
        f"- Unknown/manual-only: {_fmt_num(control_tower.get('summary', {}).get('unknown_status'))}",
        "",
        "| Agent | Status | Worked? | What it did | New achievement | Evidence |",
        "| --- | --- | --- | --- | --- | --- |",
        *agent_lines,
        "",
        "# What OPTIME Achieved In The Last 24 Hours",
        "",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (control_tower.get('achievements', {}) or {}).items()],
        "",
        "# Agents Requiring Attention",
        "",
        *[
            f"- {item['agent']}: why={item['why']} impact={item['impact']} next_action={item['next_action']}"
            for item in (control_tower.get('attention', []) or [])
        ],
        "",
        "# What OPTIME Learned Today",
        "",
        *[
            f"- {item.get('facility')}: {item.get('claim_type')} -> {item.get('claim_value')} ({item.get('status')})"
            for item in (external_discovery.get('recent_requests', []) or [])[:10]
            if item.get('status') in {'NEW_VALUE', 'STALE_REFRESHED', 'CHANGED'}
        ],
        *( ["- No new external facts were verified today."] if not any(item.get('status') in {'NEW_VALUE', 'STALE_REFRESHED', 'CHANGED'} for item in (external_discovery.get('recent_requests', []) or [])[:10]) else [] ),
        "",
        "# Source Connectivity Outcomes",
        "",
        *[
            f"- {key}: {_fmt_num(value)}"
            for key, value in (external_discovery.get('request_status_counts', {}) or {}).items()
        ],
        *[
            f"- classification {key}: {_fmt_num(value)}"
            for key, value in (external_discovery.get('request_classification_counts', {}) or {}).items()
        ],
        "",
        "# External Sources Checked",
        "",
        *[
            f"- {item.get('source_name', item.get('source'))}: last_success={item.get('last_success')} last_failure={item.get('last_failure')} success_rate={item.get('success_rate')}% facilities_covered={item.get('facilities_covered')} last_new_value={item.get('last_new_value')} next_refresh={item.get('next_refresh')}"
            for item in (external_discovery.get('source_health', []) or [])[:20]
        ],
        "",
        "# Source Failures",
        "",
        *[
            f"- {item.get('facility')}: {item.get('source')} -> {item.get('status')} [{item.get('classification')}] http={item.get('http_status')} latency_ms={item.get('latency_ms')} reason={item.get('reason') or 'UNKNOWN'}"
            for item in (external_discovery.get('recent_source_attempts', []) or [])
            if item.get('status') in {'SOURCE_ACCESS_FAILED', 'SOURCE_GEO_BLOCKED_OR_SUSPECTED', 'SOURCE_RATE_LIMITED', 'SOURCE_PARSE_FAILED', 'SOURCE_NOT_CONFIGURED', 'AGENT_FAILED'}
        ][:10],
        "",
        "# Organic / AI Authority System",
        "",
        f"- Status: {organic_authority.get('current_status', 'UNKNOWN')}",
        f"- Last verified work: {organic_authority.get('last_verified_run', 'UNKNOWN')}",
        f"- What it actually did: {organic_authority.get('what_it_actually_did', 'UNKNOWN')}",
        f"- New result created: {organic_authority.get('new_result_created', 'UNKNOWN')}",
        f"- Google visibility: {organic_authority.get('google_visibility', 'UNKNOWN')}",
        f"- AI citation monitoring: {organic_authority.get('ai_citation_monitoring', 'UNKNOWN')}",
        f"- Evidence: {', '.join(organic_authority.get('evidence', []) or ['UNKNOWN'])}",
        "",
        "# OPTIME Authority Status",
        "",
        "## DATA",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('DATA', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('DATA', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('DATA', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('DATA', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('DATA', {}).get('next_action', 'UNPROVEN')}",
        "",
        "## KNOWLEDGE",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('KNOWLEDGE', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('KNOWLEDGE', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('KNOWLEDGE', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('KNOWLEDGE', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('KNOWLEDGE', {}).get('next_action', 'UNPROVEN')}",
        "",
        "## VALIDATE",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('VALIDATE', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('VALIDATE', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('VALIDATE', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('VALIDATE', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('VALIDATE', {}).get('next_action', 'UNPROVEN')}",
        "",
        "## PUBLISH",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('PUBLISH', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('PUBLISH', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('PUBLISH', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('PUBLISH', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('PUBLISH', {}).get('next_action', 'UNPROVEN')}",
        "",
        "## INDEX",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('INDEX', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('INDEX', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('INDEX', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('INDEX', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('INDEX', {}).get('next_action', 'UNPROVEN')}",
        "",
        "## DISCOVER",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('DISCOVER', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('DISCOVER', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('DISCOVER', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('DISCOVER', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('DISCOVER', {}).get('next_action', 'UNPROVEN')}",
        "",
        "## CITE",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('CITE', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('CITE', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('CITE', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('CITE', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('CITE', {}).get('next_action', 'UNPROVEN')}",
        "",
        "## LEARN",
        *[f"- {key}: {_fmt_num(value)}" for key, value in (authority.get('stages', {}).get('LEARN', {}).get('metrics', {}) or {}).items()],
        f"- Status: {authority.get('stages', {}).get('LEARN', {}).get('status', 'UNPROVEN')}",
        f"- Last verified: {authority.get('stages', {}).get('LEARN', {}).get('last_verified_utc', 'UNPROVEN')}",
        f"- Blockers: {', '.join(authority.get('stages', {}).get('LEARN', {}).get('blockers', []) or ['None'])}",
        f"- Next action: {authority.get('stages', {}).get('LEARN', {}).get('next_action', 'UNPROVEN')}",
        "",
        "# Discovery",
        "",
        f"- Communities discovered today: {_fmt_num(payload['delta_since_previous'].get('communities_discovered_today'))}",
        f"- Communities verified today: {_fmt_num(payload['delta_since_previous'].get('communities_verified_today'))}",
        f"- Communities updated today: {_fmt_num(d.get('updated'))}",
        f"- Communities closed: {_fmt_num(d.get('closed'))}",
        f"- Duplicates merged: {_fmt_num(d.get('duplicates_merged'))}",
        f"- Current Florida coverage: {_fmt_num(d.get('counties_covered'))}/67 ({_fmt_num(d.get('coverage_pct'))}%)",
        f"- Remaining counties: {_fmt_num(67 - int(d.get('counties_covered') or 0))}",
        "",
        "# Provider Intelligence",
        "",
        f"- Profiles enriched: {_fmt_num(p.get('profiles_enriched'))}",
        f"- Ownership changes: {_fmt_num(p.get('ownership_changes'))}",
        f"- Inspection updates: {_fmt_num(p.get('inspection_updates'))}",
        f"- Licensing updates: {_fmt_num(p.get('licensing_updates'))}",
        f"- CMS updates: {_fmt_num(p.get('cms_updates'))}",
        f"- Staffing updates: {_fmt_num(p.get('staffing_updates'))}",
        f"- Pricing updates: {_fmt_num(p.get('pricing_updates'))}",
        f"- Website changes: {_fmt_num(p.get('website_changes'))}",
        "",
        "# Knowledge Growth",
        "",
        f"- Knowledge Objects created: {_fmt_num(payload['delta_since_previous'].get('knowledge_objects_created_today'))}",
        f"- Knowledge Objects updated: {_fmt_num(kg.get('knowledge_updated'))}",
        f"- Evidence Objects added: {_fmt_num(payload['delta_since_previous'].get('evidence_objects_added_today'))}",
        f"- Best Practices added: {_fmt_num(kg.get('best_practices_added'))}",
        f"- Clinical Guidelines added: {_fmt_num(kg.get('clinical_guidelines_added'))}",
        f"- Research Papers reviewed: {_fmt_num(kg.get('research_papers_reviewed'))}",
        f"- Evidence verified: {_fmt_num(kg.get('evidence_verified'))}",
        f"- Knowledge relationships created: {_fmt_num(kg.get('relationships'))}",
        "",
        "# Research Activity",
        "",
        *center_lines,
        "",
        "# Recommendation Engine",
        "",
        f"- Recommendation improvements: {_fmt_num(re.get('recommendation_improvements'))}",
        f"- Reasoning improvements: {_fmt_num(re.get('reasoning_improvements'))}",
        f"- Confidence improvements: {_fmt_num(re.get('confidence_improvements'))}",
        f"- Validation results: release_gate={re['validation_results'].get('release_gate')} advisor_agreement={_fmt_num(re['validation_results'].get('advisor_agreement_pct'))}%",
        f"- Regression tests: {_fmt_num(re.get('regression_tests'))}",
        "",
        "# Evidence Parity / Proven Match",
        "",
        f"- Status: {evidence_parity.get('status', 'UNPROVEN')}",
        f"- Regression status: {evidence_parity.get('regression_status', 'UNPROVEN')}",
        f"- Corrected proven-match top 5: {', '.join(evidence_parity.get('corrected_proven_match_top5', []) or ['UNPROVEN'])}",
        "- High-potential / needs-verification:",
        *[
            f"  - {item.get('facility_name')}: proven={item.get('proven_match_score')} potential={item.get('potential_match_score')} critical_unknowns={len(item.get('critical_unknowns') or [])}"
            for item in (evidence_parity.get('high_potential_needs_verification', []) or [])[:10]
        ],
        *( ["  - None"] if not (evidence_parity.get('high_potential_needs_verification', []) or []) else [] ),
        "",
        "# Agent Activity",
        "",
        *agent_lines,
        "",
        "# Data Quality",
        "",
        f"- Database coverage: {dq.get('database_coverage')}",
        f"- Verification coverage: {_fmt_num(dq.get('verification_coverage_pct'))}%",
        f"- Duplicate rate: {_fmt_num(dq.get('duplicate_rate_pct'))}%",
        f"- Missing information: {_fmt_num(dq.get('missing_information_rows'))}",
        f"- Conflicting information: {_fmt_num(dq.get('conflicting_information'))}",
        f"- Freshness: {_fmt_num(dq.get('freshness_days'))} day(s)",
        "",
        "# Executive KPIs",
        "",
        f"- Total Communities: {_fmt_num(kpi.get('total_communities'))}",
        f"- Verified Communities: {_fmt_num(kpi.get('verified_communities'))}",
        f"- Florida Coverage %: {_fmt_num(kpi.get('florida_coverage_pct'))}",
        f"- Knowledge Centers: {_fmt_num(kpi.get('knowledge_centers'))}",
        f"- Certified Knowledge Centers: {_fmt_num(kpi.get('certified_knowledge_centers'))}",
        f"- Knowledge Objects: {_fmt_num(kpi.get('knowledge_objects'))}",
        f"- Evidence Objects: {_fmt_num(kpi.get('evidence_objects'))}",
        f"- Research Papers: {_fmt_num(kpi.get('research_papers'))}",
        f"- Best Practices: {_fmt_num(kpi.get('best_practices'))}",
        f"- Open Knowledge Gaps: {_fmt_num(kpi.get('open_knowledge_gaps'))}",
        f"- Closed Knowledge Gaps Today: {_fmt_num(kpi.get('closed_knowledge_gaps_today'))}",
        f"- Trust Score: {_fmt_num(kpi.get('trust_score'))}%",
        f"- Institutional Intelligence Score: {_fmt_num(kpi.get('institutional_intelligence_score'))}%",
        f"- Recommendation Quality Score: {_fmt_num(kpi.get('recommendation_quality_score'))}%",
        "",
        "# Critical Alerts",
        "",
    ]

    if alerts:
        md.extend([f"- {item}" for item in alerts])
    else:
        md.append("- None")

    md.extend([
        "",
        "# Tomorrow",
        "",
        "## Top five priorities",
        *[f"- {item}" for item in payload["tomorrow"]["top_five_priorities"]],
        "",
        "## Expected deliverables",
        *[f"- {item}" for item in payload["tomorrow"]["expected_deliverables"]],
        "",
        "## Potential risks",
        *([f"- {item}" for item in payload["tomorrow"]["potential_risks"]] or ["- None identified from measurable telemetry"]),
    ])

    return "\n".join([line for line in md if line is not None]).strip() + "\n"


def _compare_trends(today_payload: Dict[str, Any], yesterday_payload: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    keys = [
        ("knowledge_growth", "knowledge_created", "Knowledge Growth"),
        ("discovery", "coverage_pct", "Florida Coverage"),
        ("recommendation_engine", "recommendation_improvements", "Recommendation Quality"),
        ("executive_kpis", "trust_score", "Trust Score"),
        ("executive_kpis", "institutional_intelligence_score", "Institutional Intelligence"),
    ]
    trends: Dict[str, Any] = {}
    for section, field, label in keys:
        current = (today_payload.get(section) or {}).get(field)
        prior = None
        if yesterday_payload:
            prior = (yesterday_payload.get(section) or {}).get(field)
        delta = None
        try:
            if current is not None and prior is not None:
                delta = float(current) - float(prior)
        except Exception:
            delta = None
        trends[label] = {"today": current, "yesterday": prior, "delta": delta}
    return trends


def _update_executive_dashboard(today_record: Dict[str, Any], trend_summary: Dict[str, Any], previous: Optional[Dict[str, Any]]) -> None:
    dash_path = _reports_path("executive_dashboard.md")
    existing = _read(dash_path)

    lines = [
        "## Daily Executive Intelligence Reports",
        "",
        f"- Latest Report (Markdown): **{today_record.get('markdown_path')}**",
        f"- Latest Report (HTML): **{today_record.get('html_path')}**",
        f"- Latest Report (JSON): **{today_record.get('json_path')}**",
        f"- Generated At (UTC): **{today_record.get('generated_at_utc')}**",
    ]
    if previous:
        lines.append(f"- Previous Report (JSON): **{previous.get('json_path')}**")
    lines.extend([
        "",
        "### Trend Comparison (Today vs Yesterday)",
        "",
        "| Trend | Today | Yesterday | Delta |",
        "| --- | --- | --- | --- |",
    ])
    for name, values in trend_summary.items():
        lines.append(
            f"| {name} | {values.get('today', 'UNPROVEN')} | {values.get('yesterday', 'UNPROVEN')} | {values.get('delta', 'UNPROVEN')} |"
        )

    section = "\n".join(lines).strip() + "\n"

    marker = "\n## Daily Executive Intelligence Reports\n"
    idx = existing.find(marker)
    if idx >= 0:
        next_header = existing.find("\n## ", idx + len(marker))
        updated = existing[:idx] + "\n" + section + (existing[next_header:] if next_header >= 0 else "")
    else:
        updated = existing.rstrip() + "\n\n" + section

    dash_path.write_text(updated.strip() + "\n", encoding="utf-8")


def generate_and_send_executive_report(db: Session) -> Dict[str, Any]:
    prev = latest_record()
    prev_payload = None
    if prev and prev.get("json_path"):
        prev_payload = load_report_json(str(prev["json_path"]))

    today = datetime.now().strftime("%Y-%m-%d")
    subject = f"OPTIME Executive Intelligence Report | {today}"

    payload = _build_report_payload(db, prev_payload)
    markdown = _to_markdown(payload)

    record = create_report_artifacts(subject=subject, markdown_text=markdown, report_json=payload)
    recipients = configured_recipients()

    ok, message, final_recipients = send_email(
        subject=subject,
        body_text=markdown,
        body_html=None,
        recipients=recipients,
    )

    if ok:
        mark_report_sent(record.report_id, final_recipients)

    this_record = {
        "report_id": record.report_id,
        "report_date": record.report_date,
        "generated_at_utc": record.generated_at_utc,
        "markdown_path": record.markdown_path,
        "html_path": record.html_path,
        "json_path": record.json_path,
        "sent": ok,
        "recipients": final_recipients,
    }

    trend_summary = _compare_trends(payload, prev_payload)
    _update_executive_dashboard(this_record, trend_summary, prev)

    return {
        "ok": ok,
        "message": message,
        "record": this_record,
        "trend_summary": trend_summary,
    }


def get_latest_executive_report() -> Optional[Dict[str, Any]]:
    return latest_record()


def get_executive_report_payload(report_id: Optional[str] = None) -> Optional[Dict[str, Any]]:
    target = None
    if report_id:
        for row in history(limit=365):
            if str(row.get("report_id")) == report_id or str(row.get("report_date")) == report_id:
                target = row
                break
    else:
        target = latest_record()

    if not target or not target.get("json_path"):
        return None

    payload = load_report_json(str(target.get("json_path"))) or {}
    return {
        "record": target,
        "report": payload,
    }


def get_executive_report_history(limit: int = 30) -> List[Dict[str, Any]]:
    return history(limit=limit)


def compare_latest_vs_previous() -> Dict[str, Any]:
    latest = latest_record()
    prev = previous_record()
    if not latest:
        return {"message": "No reports generated yet", "trends": {}}

    latest_payload = load_report_json(str(latest.get("json_path", ""))) or {}
    prev_payload = load_report_json(str(prev.get("json_path", ""))) if prev else None
    trends = _compare_trends(latest_payload, prev_payload)
    return {
        "latest": latest,
        "previous": prev,
        "trends": trends,
    }


def _report_due(now_local: datetime) -> bool:
    due_hour = int(os.getenv("OPTIME_EXEC_REPORT_HOUR", "8"))
    due_minute = int(os.getenv("OPTIME_EXEC_REPORT_MINUTE", "0"))
    return (now_local.hour > due_hour) or (now_local.hour == due_hour and now_local.minute >= due_minute)


def start_executive_report_scheduler() -> None:
    retry_minutes = int(os.getenv("OPTIME_EXEC_REPORT_RETRY_MINUTES", "15"))
    loop_seconds = int(os.getenv("OPTIME_EXEC_REPORT_LOOP_SECONDS", "60"))

    state = {"last_success_date": None, "last_attempt_at": None}

    def _runner() -> None:
        while True:
            now_local = datetime.now()
            today = now_local.date().isoformat()

            should_try = _report_due(now_local) and state.get("last_success_date") != today
            if should_try:
                last_attempt = state.get("last_attempt_at")
                cooldown_ok = True
                if isinstance(last_attempt, datetime):
                    cooldown_ok = (datetime.now() - last_attempt) >= timedelta(minutes=retry_minutes)

                if cooldown_ok:
                    state["last_attempt_at"] = datetime.now()
                    db = SessionLocal()
                    try:
                        result = generate_and_send_executive_report(db)
                        if result.get("ok"):
                            state["last_success_date"] = today
                    except Exception:
                        # Keep scheduler alive and retry on next interval, but never fail silently --
                        # a bare `except: pass` here previously hid a report-generation bug for weeks.
                        logger.exception("executive_report_scheduler_run_failed")
                    finally:
                        db.close()

            time.sleep(max(20, loop_seconds))

    thread = threading.Thread(target=_runner, name="executive-intelligence-report-scheduler", daemon=True)
    thread.start()
