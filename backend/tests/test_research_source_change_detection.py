from unittest.mock import MagicMock, patch
from app.services.decision_research_worker import _process_item

def test_official_source_content_hash_marks_change():
    db=MagicMock()
    item=MagicMock()
    item.agent_key="provider_intelligence"
    item.payload_json='{"canonical_facility_id":"NV-1","facility_name":"Real Home","city":"LAS VEGAS","dimension":"room_pricing","requested_parameters":[]}'
    previous=MagicMock(payload_json='{"source_content_sha256":"old"}')
    db.query.return_value.filter.return_value.order_by.return_value.first.return_value=previous
    with patch("app.services.decision_research_worker._candidate_official_url",return_value="https://example.org"), patch("app.services.decision_research_worker._fetch",return_value=("<html>Real Home Las Vegas Studio $4000</html>",200)), patch("app.services.decision_research_worker._identity_matches",return_value=True), patch("app.services.decision_research_worker.interpret_facility_evidence_with_ai",return_value={"capabilities":[],"room_pricing":[]}), patch("app.services.decision_research_worker._persist_record") as persist:
        _process_item(db,item)
    payload=persist.call_args.kwargs["payload"]
    assert payload["source_changed_since_last_observation"] is True
    assert len(payload["source_content_sha256"])==64
