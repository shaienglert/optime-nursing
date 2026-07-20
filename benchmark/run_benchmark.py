from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from benchmark.adapters.anthropic_adapter import AnthropicAdapter
from benchmark.adapters.fixture_adapter import FixtureAdapter
from benchmark.adapters.gemini_adapter import GeminiAdapter
from benchmark.adapters.openai_adapter import OpenAIAdapter
from benchmark.adapters.optime_adapter import OptimeAdapter
from benchmark.adapters.perplexity_adapter import PerplexityAdapter
from benchmark.contracts import BenchmarkRunRecord, stable_hash, utc_now_iso
from benchmark.evaluation.hallucination_audit import audit_hallucinations
from benchmark.evaluation.identity_resolution import resolve_identities
from benchmark.evaluation.metrics import score_dimensions
from benchmark.evaluation.source_audit import audit_claim_sources
from benchmark.evaluation.top5_overlap import overlap_analysis
from benchmark.judges.blind_evaluation import build_blind_packet
from benchmark.normalization.normalize_response import normalize_raw_response
from benchmark.prompts.canonical_prompt import build_canonical_prompt


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")


def git_head() -> str:
    try:
        result = subprocess.run(["git", "rev-parse", "HEAD"], check=True, capture_output=True, text=True, cwd=repo_root())
        return result.stdout.strip()
    except subprocess.CalledProcessError:
        return "UNKNOWN"


def build_case_freeze_manifest(cases_payload: dict[str, Any]) -> dict[str, Any]:
    entries = []
    for case in cases_payload.get("cases", []):
        case_hash = stable_hash(case)
        entries.append({"case_id": case["case_id"], "version": case["version"], "content_hash": case_hash})
    return {
        "registry_version": cases_payload.get("registry_version"),
        "generated_at": utc_now_iso(),
        "entries": sorted(entries, key=lambda item: item["case_id"]),
    }


def select_case(cases_payload: dict[str, Any], case_id: str) -> dict[str, Any]:
    for case in cases_payload.get("cases", []):
        if case.get("case_id") == case_id:
            return case
    raise ValueError(f"Unknown case_id {case_id}")


def make_claims_from_normalized(normalized: dict[str, Any], retrieval_date: str) -> list[dict[str, Any]]:
    claims: list[dict[str, Any]] = []
    for facility in normalized.get("TOP_5", []):
        for source in facility.get("sources", []):
            claims.append(
                {
                    "claim": facility.get("why_selected", ""),
                    "facility": facility.get("facility_name"),
                    "source": {
                        "url": source.get("url"),
                        "source_type": source.get("source_type", "UNKNOWN"),
                        "source_date": source.get("source_date"),
                        "retrieval_date": retrieval_date,
                    },
                    "supported_by_source": bool(source.get("url")),
                    "conflict_status": "UNKNOWN",
                }
            )
    return claims


def make_hallucination_flags(normalized: dict[str, Any]) -> list[dict[str, Any]]:
    return [{"type": "UNVERIFIED", "claim": text} for text in normalized.get("UNSUPPORTED_OR_UNVERIFIED_CLAIMS", [])]


def models_by_provider() -> dict[str, str]:
    return {
        "optime": "optime-runtime",
        "openai": "gpt-5.3-codex",
        "anthropic": "claude-sonnet-4-5",
        "google": "gemini-2.5-pro",
        "perplexity": "sonar-pro",
    }


def live_status_map(run_records: list[dict[str, Any]]) -> dict[str, Any]:
    summary: dict[str, Any] = {}
    for provider in {record["provider"] for record in run_records}:
        rows = [row for row in run_records if row["provider"] == provider]
        statuses = sorted({row["raw_response"]["run_status"] for row in rows})
        summary[provider] = {
            "statuses": statuses,
            "errors": [row["raw_response"]["error"] for row in rows if row["raw_response"].get("error")],
        }
    return summary


def provider_requirements() -> dict[str, list[str]]:
    return {
        "openai": ["OPENAI_API_KEY"],
        "anthropic": ["ANTHROPIC_API_KEY"],
        "google": ["GOOGLE_API_KEY"],
        "perplexity": ["PERPLEXITY_API_KEY"],
        "optime": [],
    }


def live_configuration_status() -> dict[str, Any]:
    requirements = provider_requirements()
    providers = {}
    for provider, keys in requirements.items():
        configured = all(bool(os.getenv(key)) for key in keys) if keys else True
        providers[provider] = {
            "configured": configured,
            "required_env": keys,
            "status": "CONFIGURED" if configured else "NOT_CONFIGURED",
        }
    any_external = any(
        row["configured"]
        for key, row in providers.items()
        if key in {"openai", "anthropic", "google", "perplexity"}
    )
    return {
        "providers": providers,
        "live_smoke_overall": "READY" if any_external else "NOT_CONFIGURED",
    }


def adapter_registry(dry_run: bool, fixtures: dict[str, Any]) -> dict[str, Any]:
    if dry_run:
        return {
            provider: FixtureAdapter(provider=provider, fixture_payload=fixtures[provider])
            for provider in ["optime", "openai", "anthropic", "google", "perplexity"]
        }

    return {
        "optime": OptimeAdapter(),
        "openai": OpenAIAdapter(),
        "anthropic": AnthropicAdapter(),
        "google": GeminiAdapter(),
        "perplexity": PerplexityAdapter(),
    }


def render_report(
    *,
    output_path: Path,
    run_id: str,
    dry_run: bool,
    case_count: int,
    prompt_hash_parity: dict[str, Any],
    live_status: dict[str, Any],
    live_config: dict[str, Any],
    artifacts: list[str],
) -> None:
    if live_config.get("live_smoke_overall") == "NOT_CONFIGURED":
        live_mode = "NOT_CONFIGURED"
    else:
        live_mode = "DRY_RUN_FIXTURES" if dry_run else "LIVE_SMOKE_ATTEMPT"
    lines = [
        "# MULTI AI BENCHMARK SYSTEM REPORT",
        "",
        "## EXECUTIVE PURPOSE",
        "Build repeatable, auditable benchmark infrastructure for comparing OPTIME and independent AI systems on identical senior-living cases.",
        "",
        "## BENCHMARK PARTICIPANTS",
        "- OPTIME",
        "- OpenAI",
        "- Anthropic",
        "- Google Gemini",
        "- Perplexity/Search-grounded",
        "",
        "## TRACK A — OPEN WORLD",
        "Shared case only. Search/tooling allowed if provider supports it.",
        "",
        "## TRACK B — CONTROLLED EVIDENCE",
        "Shared frozen case + shared frozen evidence packet. External search disabled by protocol.",
        "",
        "## CASE REGISTRY",
        f"Frozen cases loaded: {case_count}",
        "",
        "## PROMPT PARITY",
        f"Parity hashes: {json.dumps(prompt_hash_parity, ensure_ascii=True)}",
        "",
        "## RESPONSE CONTRACT",
        "Raw responses are preserved. Normalized responses are generated alongside raw outputs.",
        "",
        "## SOURCE AUDIT",
        "Claim-source auditing captures citation type, support status, and freshness buckets.",
        "",
        "## HALLUCINATION AUDIT",
        "Unsupported and unverifiable claims are tracked separately; unverifiable defaults to UNVERIFIED, not FALSE.",
        "",
        "## FACILITY IDENTITY RESOLUTION",
        "Top-5 facility names map to canonical IDs with CONFIRMED/PROBABLE/AMBIGUOUS/NO_MATCH labels.",
        "",
        "## METRICS",
        "Scorecards are reported by dimensions A-H without forced composite weighting.",
        "",
        "## BLIND EVALUATION",
        "Provider/model identities are redacted in blind packets and answer order is randomized.",
        "",
        "## JUDGE GOVERNANCE",
        "Rubric fixed prior to scoring and supports multi-judge panels. No single self-judge allowed.",
        "",
        "## OBJECTIVE VS SUBJECTIVE METRICS",
        "Objective and subjective dimensions are separated and not conflated.",
        "",
        "## OPTIME ADAPTER STATUS",
        "Uses frontend runtime engine through existing simulation bridge; returns CHAIN_BREAK when runtime path cannot execute.",
        "",
        "## PROVIDER ADAPTER STATUS",
        f"{json.dumps(live_status, indent=2, ensure_ascii=True)}",
        "",
        "## LIVE EXECUTION STATUS",
        f"{live_mode}",
        "",
        "### LIVE EXECUTION REQUIREMENTS",
        f"{json.dumps(live_config, indent=2, ensure_ascii=True)}",
        "",
        "## COST/LATENCY MODEL",
        "Latency is captured when available; token/cost fields are preserved only from provider outputs when present.",
        "",
        "## REGRESSION DESIGN",
        "Run records include OPTIME commit hash, benchmark version, case version, provider model, and timestamp for before/after comparison.",
        "",
        "## KNOWN LIMITATIONS",
        "- Dry run uses fixtures and cannot support comparative conclusions.",
        "- Live execution requires configured provider API keys.",
        "- BENCHMARK_CONCLUSION_STATUS = INSUFFICIENT_EVIDENCE",
        "",
        "## BLOCKERS",
        "- Providers without credentials are marked NOT_CONFIGURED.",
        "",
        "## NEXT EXECUTION PLAN",
        "1. Configure provider keys via environment variables.",
        "2. Run one-case live smoke test per configured provider.",
        "3. Review blind judging outputs with multi-judge panel.",
        "",
        "## ARTIFACTS",
    ]

    for artifact in artifacts:
        lines.append(f"- {artifact}")

    output_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="Run OPTIME multi-AI benchmark harness")
    parser.add_argument("--case-id", default="POST_STROKE_MIAMI_001")
    parser.add_argument("--live-smoke", action="store_true", help="Attempt one-case live execution for configured providers")
    parser.add_argument("--run-label", default="manual")
    args = parser.parse_args()

    root = repo_root()
    benchmark_version = "1.0.0"
    run_id = stable_hash({"at": utc_now_iso(), "label": args.run_label})[:12]
    dry_run = not args.live_smoke

    cases_payload = load_json(root / "database" / "benchmark_cases.json")
    case = select_case(cases_payload, args.case_id)
    controlled_packet = load_json(root / "benchmark" / "cases" / "controlled_evidence_packet_v1.json")
    fixtures_all = load_json(root / "benchmark" / "fixtures" / "providers_fixture_outputs.json").get("providers", {})
    provider_models = models_by_provider()

    case_manifest = build_case_freeze_manifest(cases_payload)
    write_json(root / "benchmark" / "cases" / "case_freeze_manifest.json", case_manifest)
    write_json(
        root / "benchmark" / "cases" / "controlled_evidence_packet_manifest.json",
        {
            "packet_id": controlled_packet.get("packet_id"),
            "version": controlled_packet.get("version"),
            "hash": stable_hash(controlled_packet),
            "generated_at": utc_now_iso(),
        },
    )

    adapters = adapter_registry(dry_run=dry_run, fixtures=fixtures_all)
    optime_commit = git_head()

    run_records: list[dict[str, Any]] = []
    prompt_hashes_by_track: dict[str, set[str]] = {"TRACK_A_OPEN_WORLD": set(), "TRACK_B_CONTROLLED_EVIDENCE": set()}

    for track in ["TRACK_A_OPEN_WORLD", "TRACK_B_CONTROLLED_EVIDENCE"]:
        for provider in ["optime", "openai", "anthropic", "google", "perplexity"]:
            model = provider_models[provider]
            prompt = build_canonical_prompt(
                track=track,
                case_definition=case,
                provider=provider,
                model=model,
                controlled_evidence_packet=controlled_packet if track == "TRACK_B_CONTROLLED_EVIDENCE" else None,
            )
            prompt_hashes_by_track[track].add(prompt.prompt_hash)

            raw = adapters[provider].run(prompt, case_payload=case, live=not dry_run)
            normalized = normalize_raw_response(raw.response_text, raw.response_json)

            retrieval_date = utc_now_iso()
            claim_rows = make_claims_from_normalized(normalized, retrieval_date)
            claim_audit = audit_claim_sources(claim_rows)
            hallucination_rows = make_hallucination_flags(normalized)
            hallucination_audit = audit_hallucinations(hallucination_rows)

            top_names = [row.get("facility_name", "") for row in normalized.get("TOP_5", [])]
            identity = resolve_identities(top_names, controlled_packet.get("facilities", []))
            metrics = score_dimensions(case, normalized, claim_audit, hallucination_audit)

            record = BenchmarkRunRecord(
                benchmark_version=benchmark_version,
                run_id=run_id,
                track=track,
                case_id=case["case_id"],
                case_version=case["version"],
                optime_commit_hash=optime_commit,
                provider=provider,
                model=model,
                model_version=raw.model_version,
                run_timestamp=raw.run_timestamp,
                prompt=prompt,
                raw_response=raw,
                normalized_response=normalized,
                claim_source_audit=claim_audit,
                hallucination_audit=hallucination_audit,
                identity_resolution=identity,
                metrics=metrics,
            )
            run_records.append(record.to_dict())

    blind_packet = build_blind_packet(run_records)
    scorecards = {
        "run_id": run_id,
        "benchmark_version": benchmark_version,
        "tracks": {
            track: [
                {
                    "provider": record["provider"],
                    "model": record["model"],
                    "metrics": record["metrics"],
                }
                for record in run_records
                if record["track"] == track
            ]
            for track in ["TRACK_A_OPEN_WORLD", "TRACK_B_CONTROLLED_EVIDENCE"]
        },
        "top5_overlap": {
            track: overlap_analysis(
                {
                    record["provider"]: [item.get("facility_name", "") for item in record["normalized_response"].get("TOP_5", [])]
                    for record in run_records
                    if record["track"] == track
                }
            )
            for track in ["TRACK_A_OPEN_WORLD", "TRACK_B_CONTROLLED_EVIDENCE"]
        },
        "composite_score": None,
        "composite_weights_documented": False,
    }

    live_status = live_status_map(run_records)
    live_config = live_configuration_status()
    prompt_parity = {track: sorted(list(hashes)) for track, hashes in prompt_hashes_by_track.items()}

    run_output_path = root / "benchmark" / "runs" / f"benchmark_run_{run_id}.json"
    blind_output_path = root / "benchmark" / "runs" / f"blind_packet_{run_id}.json"
    score_output_path = root / "benchmark" / "runs" / f"scorecards_{run_id}.json"
    write_json(run_output_path, {"run_id": run_id, "records": run_records})
    write_json(blind_output_path, blind_packet)
    write_json(score_output_path, scorecards)

    report_path = root / "reports" / "MULTI_AI_BENCHMARK_SYSTEM_REPORT.md"
    artifacts = [
        str(run_output_path.relative_to(root)).replace("\\", "/"),
        str(blind_output_path.relative_to(root)).replace("\\", "/"),
        str(score_output_path.relative_to(root)).replace("\\", "/"),
        "benchmark/cases/case_freeze_manifest.json",
        "benchmark/cases/controlled_evidence_packet_manifest.json",
        "benchmark/providers_config_metadata.json",
    ]
    render_report(
        output_path=report_path,
        run_id=run_id,
        dry_run=dry_run,
        case_count=len(cases_payload.get("cases", [])),
        prompt_hash_parity=prompt_parity,
        live_status=live_status,
        live_config=live_config,
        artifacts=artifacts,
    )

    summary = {
        "run_id": run_id,
        "dry_run": dry_run,
        "providers": sorted({r["provider"] for r in run_records}),
        "tracks": ["TRACK_A_OPEN_WORLD", "TRACK_B_CONTROLLED_EVIDENCE"],
        "live_status": live_status,
        "report": str(report_path.relative_to(root)).replace("\\", "/"),
    }
    write_json(root / "benchmark" / "runs" / f"summary_{run_id}.json", summary)


if __name__ == "__main__":
    main()
