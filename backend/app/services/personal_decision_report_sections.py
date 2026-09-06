from __future__ import annotations

"""Strict section normalization for Personal Decision Reports."""

from typing import Iterable

from app.services.personal_decision_report_contract import ReportSection


def normalize_report_sections(values: Iterable[object], default: ReportSection) -> tuple[ReportSection, ...]:
    sections: list[ReportSection] = []
    for value in values:
        if isinstance(value, ReportSection):
            sections.append(value)
        else:
            sections.append(ReportSection(str(value)))
    return tuple(sections) or (default,)
