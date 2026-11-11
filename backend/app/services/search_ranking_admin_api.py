"""Staff-only history; dependency injection reuses the application's admin gate."""
import json

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.models.search_ranking_audit import SearchRankingAudit


def search_ranking_router(require_admin, get_db):
    router = APIRouter(prefix="/api/admin/search-ranking-audits", dependencies=[Depends(require_admin)])

    @router.get("")
    def list_audits(limit: int = Query(default=25, ge=1, le=100),
                    offset: int = Query(default=0, ge=0), db: Session = Depends(get_db)):
        records = db.query(SearchRankingAudit).order_by(
            SearchRankingAudit.created_at_epoch.desc(), SearchRankingAudit.id.desc()
        ).offset(offset).limit(limit + 1).all()
        items = []
        for record in records[:limit]:
            payload = json.loads(record.payload_json)
            items.append({"id": record.id, "created_at_epoch": record.created_at_epoch,
                          "returned_count": payload.get("returned_count"),
                          "total_candidates_scored": payload.get("total_candidates_scored"),
                          "top_count": len(payload.get("rows") or [])})
        return JSONResponse({"items": items, "has_more": len(records) > limit},
                            headers={"Cache-Control": "no-store"})

    @router.get("/{audit_id}")
    def get_audit(audit_id: str, db: Session = Depends(get_db)):
        record = db.get(SearchRankingAudit, audit_id)
        if record is None:
            raise HTTPException(status_code=404, detail="Search audit not found")
        return JSONResponse({"id": record.id, "created_at_epoch": record.created_at_epoch,
                             **json.loads(record.payload_json)}, headers={"Cache-Control": "no-store"})

    return router
