# MULTI AI BENCHMARK SYSTEM REPORT

## EXECUTIVE PURPOSE
Build repeatable, auditable benchmark infrastructure for comparing OPTIME and independent AI systems on identical senior-living cases.

## BENCHMARK PARTICIPANTS
- OPTIME
- OpenAI
- Anthropic
- Google Gemini
- Perplexity/Search-grounded

## TRACK A — OPEN WORLD
Shared case only. Search/tooling allowed if provider supports it.

## TRACK B — CONTROLLED EVIDENCE
Shared frozen case + shared frozen evidence packet. External search disabled by protocol.

## CASE REGISTRY
Frozen cases loaded: 20

## PROMPT PARITY
Parity hashes: {"TRACK_A_OPEN_WORLD": ["548e03c73738d269ac1b1cc900d2c7b6f4f3c4779335e6fa0b57d8902c6e25cb"], "TRACK_B_CONTROLLED_EVIDENCE": ["178796377818abb947a1f6739927ee602ab70ba12f45f72114c5912f2a92a810"]}

## RESPONSE CONTRACT
Raw responses are preserved. Normalized responses are generated alongside raw outputs.

## SOURCE AUDIT
Claim-source auditing captures citation type, support status, and freshness buckets.

## HALLUCINATION AUDIT
Unsupported and unverifiable claims are tracked separately; unverifiable defaults to UNVERIFIED, not FALSE.

## FACILITY IDENTITY RESOLUTION
Top-5 facility names map to canonical IDs with CONFIRMED/PROBABLE/AMBIGUOUS/NO_MATCH labels.

## METRICS
Scorecards are reported by dimensions A-H without forced composite weighting.

## BLIND EVALUATION
Provider/model identities are redacted in blind packets and answer order is randomized.

## JUDGE GOVERNANCE
Rubric fixed prior to scoring and supports multi-judge panels. No single self-judge allowed.

## OBJECTIVE VS SUBJECTIVE METRICS
Objective and subjective dimensions are separated and not conflated.

## OPTIME ADAPTER STATUS
Uses frontend runtime engine through existing simulation bridge; returns CHAIN_BREAK when runtime path cannot execute.

## PROVIDER ADAPTER STATUS
{
  "perplexity": {
    "statuses": [
      "OK"
    ],
    "errors": []
  },
  "google": {
    "statuses": [
      "OK"
    ],
    "errors": []
  },
  "optime": {
    "statuses": [
      "OK"
    ],
    "errors": []
  },
  "openai": {
    "statuses": [
      "OK"
    ],
    "errors": []
  },
  "anthropic": {
    "statuses": [
      "OK"
    ],
    "errors": []
  }
}

## LIVE EXECUTION STATUS
NOT_CONFIGURED

### LIVE EXECUTION REQUIREMENTS
{
  "providers": {
    "openai": {
      "configured": false,
      "required_env": [
        "OPENAI_API_KEY"
      ],
      "status": "NOT_CONFIGURED"
    },
    "anthropic": {
      "configured": false,
      "required_env": [
        "ANTHROPIC_API_KEY"
      ],
      "status": "NOT_CONFIGURED"
    },
    "google": {
      "configured": false,
      "required_env": [
        "GOOGLE_API_KEY"
      ],
      "status": "NOT_CONFIGURED"
    },
    "perplexity": {
      "configured": false,
      "required_env": [
        "PERPLEXITY_API_KEY"
      ],
      "status": "NOT_CONFIGURED"
    },
    "optime": {
      "configured": true,
      "required_env": [],
      "status": "CONFIGURED"
    }
  },
  "live_smoke_overall": "NOT_CONFIGURED"
}

## COST/LATENCY MODEL
Latency is captured when available; token/cost fields are preserved only from provider outputs when present.

## REGRESSION DESIGN
Run records include OPTIME commit hash, benchmark version, case version, provider model, and timestamp for before/after comparison.

## KNOWN LIMITATIONS
- Dry run uses fixtures and cannot support comparative conclusions.
- Live execution requires configured provider API keys.
- BENCHMARK_CONCLUSION_STATUS = INSUFFICIENT_EVIDENCE

## BLOCKERS
- Providers without credentials are marked NOT_CONFIGURED.

## NEXT EXECUTION PLAN
1. Configure provider keys via environment variables.
2. Run one-case live smoke test per configured provider.
3. Review blind judging outputs with multi-judge panel.

## ARTIFACTS
- benchmark/runs/benchmark_run_8a303893171d.json
- benchmark/runs/blind_packet_8a303893171d.json
- benchmark/runs/scorecards_8a303893171d.json
- benchmark/cases/case_freeze_manifest.json
- benchmark/cases/controlled_evidence_packet_manifest.json
- benchmark/providers_config_metadata.json
