# OPTIME Multi-AI Benchmark Framework

This module builds benchmark infrastructure for two distinct tracks:

- `TRACK_A_OPEN_WORLD`: same case only, provider search/tools allowed when supported.
- `TRACK_B_CONTROLLED_EVIDENCE`: same case + same frozen evidence packet, no external search.

## No-cost dry run

```powershell
.venv\Scripts\python.exe -m benchmark.run_benchmark --run-label dryrun
```

## Validate governance constraints

```powershell
.venv\Scripts\python.exe -m benchmark.validate_benchmark --run-id <RUN_ID>
```

## Optional live smoke test

Live smoke test runs exactly one case (`POST_STROKE_MIAMI_001`) per provider.

```powershell
.venv\Scripts\python.exe -m benchmark.run_benchmark --live-smoke --run-label smoke
```

### Required environment variables for live calls

- `OPENAI_API_KEY`
- `ANTHROPIC_API_KEY`
- `GOOGLE_API_KEY`
- `PERPLEXITY_API_KEY`

Notes:
- Missing keys produce `NOT_CONFIGURED` status.
- Dry run fixtures are labeled `TEST_FIXTURE_NOT_REAL_AI_RESULT` and must not be used for comparative conclusions.
- OPTIME adapter executes the existing frontend runtime engine path via `scripts/run_dynamic_persona_simulation_audit.cjs` bridge and reports `CHAIN_BREAK` if execution fails.
