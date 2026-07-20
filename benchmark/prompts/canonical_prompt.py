from __future__ import annotations

from typing import Any

from benchmark.contracts import PromptEnvelope, stable_hash, utc_now_iso


RESPONSE_CONTRACT = """
Return JSON with these top-level fields:
UNDERSTOOD_PERSON_PROFILE
EXPLICIT_NEEDS
MISSING_INFORMATION
CLARIFYING_QUESTIONS
MUST_REQUIREMENTS
PROFESSIONAL_RECOMMENDATIONS
NICE_TO_HAVE
FACILITIES_CONSIDERED
TOP_5
UNSUPPORTED_OR_UNVERIFIED_CLAIMS
NEXT_STEPS_FOR_FAMILY

For TOP_5 items include:
facility_name, location, why_selected, must_satisfied, must_failed, must_unknown,
recommendation_alignment, nice_to_have_alignment, tradeoffs, evidence_gaps, sources, confidence
""".strip()


def _case_block(case_definition: dict[str, Any]) -> str:
    return (
        f"CASE_ID: {case_definition['case_id']}\n"
        f"CASE_VERSION: {case_definition['version']}\n"
        f"SCENARIO: {case_definition['scenario']}\n"
        f"PERSON_PROFILE: {case_definition['person_profile']}\n"
        f"EXPLICIT_NEEDS: {case_definition['explicit_needs']}\n"
        f"EXPLICIT_NON_NEGOTIABLES: {case_definition['explicit_non_negotiables']}\n"
        f"PREFERENCES: {case_definition['preferences']}\n"
        f"KNOWN_UNKNOWNS: {case_definition['known_unknowns']}\n"
        f"LOCATION: {case_definition['location']}\n"
        f"BUDGET_STATUS: {case_definition['budget_status']}\n"
        f"CARE_CONTEXT: {case_definition['care_context']}\n"
    )


def build_canonical_prompt(
    *,
    track: str,
    case_definition: dict[str, Any],
    provider: str,
    model: str,
    controlled_evidence_packet: dict[str, Any] | None,
) -> PromptEnvelope:
    if track not in {"TRACK_A_OPEN_WORLD", "TRACK_B_CONTROLLED_EVIDENCE"}:
        raise ValueError(f"Unsupported track: {track}")

    system_prompt = (
        "You are a senior-living decision support assistant. Be explicit about uncertainty. "
        "Do not invent facts. If evidence is missing, say UNKNOWN or NEEDS_VERIFICATION."
    )

    user_prompt_parts = [
        "Benchmark mode: compare decision quality across systems.\n",
        _case_block(case_definition),
        "\nRequired response contract:\n",
        RESPONSE_CONTRACT,
        "\nRules:\n"
        "1) Preserve explicit requirements.\n"
        "2) Ask clarifying questions for unknown critical data.\n"
        "3) Separate MUST from NICE_TO_HAVE.\n"
        "4) Cite sources for factual claims.\n"
        "5) Mark unverifiable claims as UNVERIFIED, not FALSE.\n",
    ]

    tools_enabled = False
    if track == "TRACK_B_CONTROLLED_EVIDENCE":
        packet = controlled_evidence_packet or {}
        user_prompt_parts.extend(
            [
                "\nControlled evidence packet (frozen, same for all systems):\n",
                str(packet),
                "\nDo not use external search in this track.\n",
            ]
        )
    else:
        user_prompt_parts.append("\nExternal search is allowed only if supported by the system.\n")
        tools_enabled = True

    user_prompt = "".join(user_prompt_parts)
    prompt_hash = stable_hash(
        {
            "track": track,
            "case_id": case_definition["case_id"],
            "system_prompt": system_prompt,
            "user_prompt": user_prompt,
        }
    )

    return PromptEnvelope(
        track=track,
        case_id=case_definition["case_id"],
        provider=provider,
        model=model,
        system_prompt=system_prompt,
        user_prompt=user_prompt,
        prompt_hash=prompt_hash,
        generated_at=utc_now_iso(),
        tools_enabled=tools_enabled,
    )
