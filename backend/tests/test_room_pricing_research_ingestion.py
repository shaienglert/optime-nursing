from unittest.mock import MagicMock, patch
from app.services.decision_research_worker import _ingest_room_pricing

def test_room_pricing_ingestion_preserves_qualifier_and_availability_as_reported():
    db=MagicMock()
    interpretation={"room_pricing":[{"room_type_name":"Studio","base_monthly_price":4450,"pricing_qualifier":"STARTING_AT","care_fee":None,"mandatory_monthly_fees":None,"availability_status":"AVAILABLE","evidence_summary":"Studio starting at $4,450"}]}
    with patch("app.services.facility_room_service.upsert_room_type") as upsert:
        count=_ingest_room_pricing(db,"NV-1","https://example.org/pricing",interpretation)
    assert count==1
    kwargs=upsert.call_args.kwargs
    assert kwargs["monthly_price_cents"]==445000
    assert kwargs["pricing_qualifier"]=="STARTING_AT"
    assert kwargs["availability_status"]=="AVAILABLE"
    assert kwargs["source"]=="OFFICIAL_WEBSITE"