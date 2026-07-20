from __future__ import annotations

from itertools import combinations
from typing import Any


def overlap_analysis(provider_top5: dict[str, list[str]]) -> dict[str, Any]:
    providers = sorted(provider_top5.keys())
    pairwise = []

    for left, right in combinations(providers, 2):
        left_set = set(provider_top5[left])
        right_set = set(provider_top5[right])
        pairwise.append(
            {
                "pair": [left, right],
                "exact_overlap": sorted(left_set & right_set),
                "overlap_count": len(left_set & right_set),
                "unique_left": sorted(left_set - right_set),
                "unique_right": sorted(right_set - left_set),
            }
        )

    all_sets = [set(provider_top5[p]) for p in providers]
    consensus = sorted(set.intersection(*all_sets)) if all_sets else []
    union = sorted(set.union(*all_sets)) if all_sets else []

    outlier_facilities = []
    for facility in union:
        occurrence = sum(1 for values in all_sets if facility in values)
        if occurrence == 1:
            outlier_facilities.append(facility)

    return {
        "provider_top5": provider_top5,
        "pairwise": pairwise,
        "consensus_facilities": consensus,
        "outlier_facilities": sorted(outlier_facilities),
    }
