from __future__ import annotations

import datetime as dt
import json
from pathlib import Path
from typing import Any, Dict, List


REPO_ROOT = Path(__file__).resolve().parents[1]
WAVE1_JSON = REPO_ROOT / "database" / "community_intelligence_wave1.json"
OUTPUT_PROFILE = REPO_ROOT / "database" / "community_intelligence_profile.json"
OUTPUT_SIGNAL_GRAPH = REPO_ROOT / "database" / "community_signal_graph.json"
OUTPUT_CONFIDENCE = REPO_ROOT / "database" / "community_confidence_scores.json"

TIER_1 = {
    "CMS",
    "AHCA",
    "Google Reviews",
    "Caring",
    "A Place for Mom",
    "Seniorly",
    "Indeed",
    "Glassdoor",
    "Google News",
    "Official Website",
}

TIER_2 = {
    "LinkedIn",
    "YouTube",
    "Facebook",
    "Instagram",
    "Lawsuits",
    "Awards",
    "Ownership changes",
}


def _now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat()


def _load_wave1_records() -> List[Dict[str, Any]]:
    payload = json.loads(WAVE1_JSON.read_text(encoding="utf-8"))
    return list(payload.get("records") or [])


def _confidence_to_score(confidence: str) -> int:
    normalized = (confidence or "").upper()
    if normalized == "HIGH":
        return 90
    if normalized == "MEDIUM":
        return 70
    if normalized == "LOW":
        return 50
    return 20


def _build_profile_records(records: List[Dict[str, Any]], generated_at: str) -> List[Dict[str, Any]]:
    profile_records: List[Dict[str, Any]] = []

    for record in records:
        registry = list(record.get("source_registry") or [])

        tier_1_sources: List[Dict[str, Any]] = []
        tier_2_sources: List[Dict[str, Any]] = []

        for source in registry:
            source_type = source.get("source_type")
            source_row = {
                "source_type": source_type,
                "source_url": source.get("source_url"),
                "timestamp": source.get("timestamp"),
                "confidence": source.get("confidence"),
                "facts": source.get("facts") or [],
                "signals": source.get("signals") or [],
            }

            if source_type in TIER_1:
                tier_1_sources.append(source_row)

        for source_name in sorted(TIER_2):
            tier_2_sources.append(
                {
                    "source_type": source_name,
                    "source_url": None,
                    "timestamp": generated_at,
                    "confidence": "UNKNOWN",
                    "facts": [],
                    "signals": [],
                }
            )

        profile_records.append(
            {
                "community_id": record.get("community_id"),
                "community_name": record.get("community_name"),
                "county": record.get("county"),
                "state": record.get("state"),
                "collection_timestamp_utc": record.get("collection_timestamp_utc") or generated_at,
                "tiers": {
                    "tier_1": tier_1_sources,
                    "tier_2": tier_2_sources,
                },
                "coverage": record.get("coverage") or {},
            }
        )

    return profile_records


def _build_signal_graph(records: List[Dict[str, Any]], generated_at: str) -> Dict[str, Any]:
    nodes: List[Dict[str, Any]] = []
    edges: List[Dict[str, Any]] = []
    seen_nodes = set()

    for record in records:
        community_id = record.get("community_id")
        community_name = record.get("community_name")
        community_node = f"community:{community_id}"

        if community_node not in seen_nodes:
            nodes.append({"id": community_node, "type": "community", "label": community_name})
            seen_nodes.add(community_node)

        for source in record.get("source_registry") or []:
            source_type = source.get("source_type")
            source_node = f"source:{source_type}"
            if source_node not in seen_nodes:
                nodes.append({"id": source_node, "type": "source", "label": source_type})
                seen_nodes.add(source_node)

            edges.append(
                {
                    "from": community_node,
                    "to": source_node,
                    "relationship": "HAS_SOURCE",
                    "timestamp": source.get("timestamp") or generated_at,
                    "confidence": source.get("confidence") or "UNKNOWN",
                }
            )

            for signal in source.get("signals") or []:
                signal_name = signal.get("signal_name")
                if not signal_name:
                    continue
                signal_node = f"signal:{signal_name}"
                if signal_node not in seen_nodes:
                    nodes.append({"id": signal_node, "type": "signal", "label": signal_name})
                    seen_nodes.add(signal_node)

                edges.append(
                    {
                        "from": source_node,
                        "to": signal_node,
                        "relationship": "EMITS_SIGNAL",
                        "timestamp": signal.get("timestamp") or generated_at,
                        "confidence": signal.get("confidence") or "UNKNOWN",
                    }
                )

                edges.append(
                    {
                        "from": community_node,
                        "to": signal_node,
                        "relationship": "HAS_SIGNAL",
                        "timestamp": signal.get("timestamp") or generated_at,
                        "confidence": signal.get("confidence") or "UNKNOWN",
                    }
                )

    return {"generated_at_utc": generated_at, "nodes": nodes, "edges": edges}


def _build_confidence_scores(records: List[Dict[str, Any]], generated_at: str) -> Dict[str, Any]:
    score_rows: List[Dict[str, Any]] = []

    for record in records:
        registry = list(record.get("source_registry") or [])
        confidence_values = [_confidence_to_score(source.get("confidence") or "UNKNOWN") for source in registry]
        average_confidence_score = round(sum(confidence_values) / len(confidence_values), 2) if confidence_values else 0.0
        verified_sources = int((record.get("coverage") or {}).get("verified_unique_source_count") or 0)

        score_rows.append(
            {
                "community_id": record.get("community_id"),
                "community_name": record.get("community_name"),
                "verified_unique_source_count": verified_sources,
                "source_registry_confidence_score": average_confidence_score,
                "overall_confidence_level": (
                    "HIGH" if average_confidence_score >= 80 else "MEDIUM" if average_confidence_score >= 60 else "LOW"
                ),
                "timestamp": record.get("collection_timestamp_utc") or generated_at,
            }
        )

    average_confidence = round(
        sum(item["source_registry_confidence_score"] for item in score_rows) / len(score_rows), 2
    ) if score_rows else 0.0

    return {
        "generated_at_utc": generated_at,
        "record_count": len(score_rows),
        "average_source_registry_confidence_score": average_confidence,
        "scores": score_rows,
    }


def main() -> None:
    generated_at = _now_utc()
    wave1_records = _load_wave1_records()

    profile_payload = {
        "generated_at_utc": generated_at,
        "record_count": len(wave1_records),
        "policy": {
            "no_invented_information": True,
            "preserve_source_provenance": True,
            "preserve_source_timestamps": True,
            "assign_confidence_levels": True,
        },
        "records": _build_profile_records(wave1_records, generated_at),
    }

    signal_graph_payload = _build_signal_graph(wave1_records, generated_at)
    confidence_payload = _build_confidence_scores(wave1_records, generated_at)

    OUTPUT_PROFILE.write_text(json.dumps(profile_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_SIGNAL_GRAPH.write_text(json.dumps(signal_graph_payload, indent=2, ensure_ascii=False), encoding="utf-8")
    OUTPUT_CONFIDENCE.write_text(json.dumps(confidence_payload, indent=2, ensure_ascii=False), encoding="utf-8")

    print(
        json.dumps(
            {
                "community_intelligence_profile": str(OUTPUT_PROFILE),
                "community_signal_graph": str(OUTPUT_SIGNAL_GRAPH),
                "community_confidence_scores": str(OUTPUT_CONFIDENCE),
                "record_count": len(wave1_records),
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
