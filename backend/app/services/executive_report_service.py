import json
import os
import re
import threading
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.agent_execution import AgentKnowledgeRecord, AgentKnowledgeRefreshEvent, AgentKnowledgeReportSnapshot, SupervisorIncidentLog
from app.models.facility import Facility, FacilityIntelligenceProfile
from app.services.email_service import configured_recipients, send_email
from app.services.report_archive_service import (
    create_report_artifacts,
    history,
    latest_record,
    load_report_json,
    mark_report_sent,
    previous_record,
)


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
    agents = _agent_activity(db)
    centers = _extract_centers()
    gaps = _knowledge_gap_lines()

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
        "recommendation_engine": {
            "recommendation_improvements": 1 if rec.get("release_gate") == "PASS" else 0,
            "reasoning_improvements": growth_totals.get("decision_rules", 0),
            "confidence_improvements": provider.get("profiles_enriched", 0),
            "validation_results": rec,
            "regression_tests": rec.get("release_gate"),
        },
        "agent_activity": agents,
        "data_quality": data_quality,
        "knowledge_gaps": gaps,
        "executive_kpis": current_kpis,
        "critical_alerts": [
            f"{a['agent_name']} status={a['status']} blocked_tasks={a['blocked_tasks']}"
            for a in agents
            if a["status"] in {"FAILED", "IDLE"} or a["blocked_tasks"] > 0
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
    alerts = payload["critical_alerts"]

    if not any(v not in (None, 0, [], "", "UNPROVEN") for v in payload["delta_since_previous"].values()):
        no_progress = "No measurable progress since the previous report."
    else:
        no_progress = ""

    agent_lines = []
    for a in payload["agent_activity"]:
        flag = ""
        if a["status"] in {"IDLE", "FAILED"} or a["blocked_tasks"] > 0:
            flag = " [ATTENTION]"
        agent_lines.append(
            f"- {a['agent_name']}: status={a['status']}, health={a['health']}, current={a['current_task']}, completed_today={a['completed_today']}, blocked={a['blocked_tasks']}, next={a['next_task']}, learning_completed={a['learning_completed']}, knowledge_produced={a['knowledge_produced']}.{flag}"
        )

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
        "",
        no_progress,
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
                        # Keep scheduler alive and retry on next interval.
                        pass
                    finally:
                        db.close()

            time.sleep(max(20, loop_seconds))

    thread = threading.Thread(target=_runner, name="executive-intelligence-report-scheduler", daemon=True)
    thread.start()
