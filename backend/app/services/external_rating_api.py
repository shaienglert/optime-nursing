from fastapi import APIRouter, HTTPException
from fastapi.responses import JSONResponse

from app.services.external_rating_display import external_ratings_for_facility


def external_rating_router(get_facility_index):
    router = APIRouter()

    @router.get("/canonical-facilities/{canonical_facility_id}/external-ratings")
    def get_ratings(canonical_facility_id: str):
        row = get_facility_index().get(canonical_facility_id)
        if row is None:
            raise HTTPException(404, "Facility not found", headers={"Cache-Control": "no-store"})
        # Canonical catalog keys are the identity authority, not caller-supplied metadata.
        return JSONResponse(external_ratings_for_facility({**row, "canonical_facility_id": canonical_facility_id}),
                            headers={"Cache-Control": "no-store"})

    return router
