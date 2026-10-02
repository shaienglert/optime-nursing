from app.services.research_institute_scheduler import queue_daily_facility_refresh
from app.services.decision_research_worker import process_pending_decision_research
from app.services.institutional_research import research_coverage_report
from app.services.facility_parameter_service import get_canonical_facility_index
import json
import os

def main():
    summary=queue_daily_facility_refresh()
    processed=0
    # A failing source must not cause an unbounded cron invocation.
    for _ in range(max(1, min(100, int(os.getenv("OOMNIK_RESEARCH_MAX_BATCHES", "20"))))):
        result=process_pending_decision_research(limit=50)
        count=int(result.get("processed") or 0)
        processed+=count
        if count==0: break
    coverage = research_coverage_report(get_canonical_facility_index())
    print(json.dumps({"queued":summary,"processed":processed,"coverage":coverage}, sort_keys=True))
    if coverage["status"] not in {"CURRENT", "NO_REAL_FACILITIES"}:
        raise SystemExit(2)

if __name__=="__main__": main()
