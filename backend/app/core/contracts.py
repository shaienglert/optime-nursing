"""Domain-neutral contracts for OPTIME decision support.

This module intentionally contains no Senior Living or Employment concepts.
Domains translate their own entities into these contracts through adapters.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Mapping, Sequence


class RequirementLevel(str, Enum):
    MUST = "MUST"
    IMPORTANT = "IMPORTANT"
    NICE_TO_HAVE = "NICE_TO_HAVE"


class EvidenceState(str, Enum):
    YES = "YES"
    NO = "NO"
    UNKNOWN = "UNKNOWN"
    LIMITED = "LIMITED"
    CONFLICTING = "CONFLICTING"


class EligibilityStatus(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    ELIGIBLE_WITH_UNKNOWNS = "ELIGIBLE_WITH_UNKNOWNS"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"


@dataclass(frozen=True)
class DecisionParty:
    party_id: str
    party_type: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class DecisionOption:
    option_id: str
    option_type: str
    label: str
    attributes: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Requirement:
    requirement_id: str
    label: str
    level: RequirementLevel
    desired_value: Any
    acceptable_values: Sequence[Any] = field(default_factory=tuple)
    source: str = "UNKNOWN"
    rationale: str = ""


@dataclass(frozen=True)
class EvidenceRecord:
    option_id: str
    requirement_id: str
    state: EvidenceState
    value: Any = None
    source: str = "UNKNOWN"
    confidence: float | None = None
    observed_at: str | None = None
    explanation: str = ""


@dataclass(frozen=True)
class RequirementEvaluation:
    requirement_id: str
    state: EvidenceState
    matched: bool | None
    explanation: str
    evidence: Sequence[EvidenceRecord] = field(default_factory=tuple)


@dataclass(frozen=True)
class TradeOff:
    subject: str
    benefit: str
    cost: str


@dataclass(frozen=True)
class ClarificationQuestion:
    question_id: str
    target_party: str
    question: str
    reason: str


@dataclass(frozen=True)
class Explanation:
    why_presented: Sequence[str] = field(default_factory=tuple)
    advantages: Sequence[str] = field(default_factory=tuple)
    disadvantages: Sequence[str] = field(default_factory=tuple)
    unknowns: Sequence[str] = field(default_factory=tuple)
    questions: Sequence[ClarificationQuestion] = field(default_factory=tuple)


@dataclass(frozen=True)
class AuditTrace:
    rules_applied: Sequence[str] = field(default_factory=tuple)
    evidence_sources: Sequence[str] = field(default_factory=tuple)
    warnings: Sequence[str] = field(default_factory=tuple)


@dataclass(frozen=True)
class PairEvaluation:
    party: DecisionParty
    option: DecisionOption
    eligibility: EligibilityStatus
    requirement_evaluations: Sequence[RequirementEvaluation]
    explanation: Explanation
    trade_offs: Sequence[TradeOff] = field(default_factory=tuple)
    audit: AuditTrace = field(default_factory=AuditTrace)

    @property
    def failed_must_requirement_ids(self) -> tuple[str, ...]:
        return tuple(
            item.requirement_id
            for item in self.requirement_evaluations
            if item.matched is False
        )
