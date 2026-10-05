from app.services.semantic_facility_requirements import _row_verifies_budget

def test_budget_accepts_verified_total_through_ten_percent():
    assert _row_verifies_budget({"starting_monthly_price":5500,"total_affordability_status":"KNOWN"},{"budget":5000})
    assert not _row_verifies_budget({"starting_monthly_price":5501,"total_affordability_status":"KNOWN"},{"budget":5000})

def test_room_starting_price_is_searchable_with_final_fees_pending():
    row={"starting_monthly_price":4500,"total_affordability_status":"PENDING","price_truth_basis":"ROOM_BASE_ONLY_TOTAL_PENDING"}
    assert _row_verifies_budget(row,{"budget":5000})
