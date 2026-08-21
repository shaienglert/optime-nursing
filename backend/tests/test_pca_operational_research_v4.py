from scripts.enrich_nevada_pca_operational_primary_sources_v3 import UNKNOWN
from scripts.enrich_nevada_pca_operational_primary_sources_v4 import research_task_v4


def test_v4_preserves_v3_extended_unknown_semantics(monkeypatch):
    monkeypatch.setattr(
        'scripts.enrich_nevada_pca_operational_primary_sources_v4.discover_candidates_v4',
        lambda task: [{'url': 'https://example.test', 'title': 'Example', 'discovery_method': 'TEST'}],
    )
    monkeypatch.setattr(
        'scripts.enrich_nevada_pca_operational_primary_sources_v4.verify_candidate_v3',
        lambda candidate, task, throttle: {
            'primary_source_url': candidate['url'],
            'identity_verified': True,
            'serves_las_vegas_valley': True,
            'post_surgical_care': True,
            'minimum_weekly_hours': 12,
            'registered_nurse_oversight': UNKNOWN,
        },
    )
    row = research_task_v4({'agency_name': 'Example', 'license_number': '1-PCS-0'}, 0)
    assert row['identity_verified'] is True
    assert row['post_surgical_care'] is True
    assert row['minimum_weekly_hours'] == 12
    assert row['registered_nurse_oversight'] == UNKNOWN
    assert 'positive-only' in row['policy']
