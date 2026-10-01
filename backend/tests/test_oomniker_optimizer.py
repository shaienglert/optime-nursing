from app.services.oomniker_optimizer import analyze_oomniker

def test_oomniker_recommends_but_never_mutates():
    profile={"budget":5000,"radius_miles":5}
    original=dict(profile)
    rows=[{"starting_monthly_price":5200,"distance_miles":8},{"starting_monthly_price":4800,"distance_miles":3}]
    out=analyze_oomniker(profile,rows)
    assert profile==original
    assert out["profile_mutated"] is False
    assert {x["parameter"] for x in out["suggestions"]}=={"budget","radius_miles"}