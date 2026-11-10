from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.services.external_rating_display import external_ratings_for_facility


# Ratings-only identity: never added to the canonical search catalog.
_SUMMERLIN_CHECK_ID = "verification-summerlin-295083"
_SUMMERLIN_CHECK = {
    "name": "The Heights of Summerlin",
    "address": "10550 W Park Run Dr.",
    "city": "Las Vegas",
}


def external_rating_router(get_facility_index):
    router = APIRouter()

    @router.get("/canonical-facilities/{canonical_facility_id}/external-ratings")
    def get_ratings(canonical_facility_id: str):
        row = (_SUMMERLIN_CHECK if canonical_facility_id == _SUMMERLIN_CHECK_ID
               else get_facility_index().get(canonical_facility_id))
        if row is None:
            raise HTTPException(404, "Facility not found", headers={"Cache-Control": "no-store"})
        # Identity comes from the catalog or the fixed verification record.
        return JSONResponse(external_ratings_for_facility({**row, "canonical_facility_id": canonical_facility_id}),
                            headers={"Cache-Control": "no-store"})

    return router
