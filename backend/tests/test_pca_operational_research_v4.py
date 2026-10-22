from scripts.enrich_nevada_pca_operational_primary_sources_v3 import UNKNOWN
from scripts.enrich_nevada_pca_operational_primary_sources_v4 import discover_candidates_v4, research_task_v4


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


def test_v4_does_not_let_first_phone_query_exhaust_candidate_budget(monkeypatch):
    task = {
        'agency_name': 'Aarti Home Care',
        'city': 'Henderson',
        'phone': '702-523-5804',
        'address': '123 Main Street',
        'license_number': '8173-PCS-13',
    }

    monkeypatch.setattr(
        'scripts.enrich_nevada_pca_operational_primary_sources_v4.hcqc_external_links',
        lambda task: [],
    )

    def fake_bing(query):
        if '702-523-5804' in query and 'Aarti Home Care' in query:
            return [(f'https://aarti-home-care-{i}.test', 'Aarti Home Care Henderson') for i in range(20)]
        if '123 Main Street' in query:
            return [('https://aarti-address.test', 'Aarti Home Care Henderson')]
        if '8173' in query:
            return [('https://aarti-license.test', 'Aarti Home Care Henderson')]
        if 'Henderson' in query:
            return [('https://aarti-name-city.test', 'Aarti Home Care Henderson')]
        return []

    monkeypatch.setattr(
        'scripts.enrich_nevada_pca_operational_primary_sources_v4.bing_result_urls',
        fake_bing,
    )
    monkeypatch.setattr(
        'scripts.enrich_nevada_pca_operational_primary_sources_v4.duckduckgo_lite_urls',
        lambda query: [],
    )

    candidates = discover_candidates_v4(task)
    methods = [row['discovery_method'] for row in candidates]
    assert methods.count('BING_EXACT_PHONE') == 4
    assert 'BING_EXACT_ADDRESS' in methods
    assert 'BING_LICENSE_ROOT' in methods
    assert 'BING_NAME_CITY' in methods
