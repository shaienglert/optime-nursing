from app.services.research_institute_scheduler import queue_daily_facility_refresh
from app.services.decision_research_worker import run_worker_once

def main():
    summary=queue_daily_facility_refresh()
    processed=0
    while True:
        result=run_worker_once(max_items=50)
        count=int(result.get("processed") or 0)
        processed+=count
        if count==0: break
    print({"queued":summary,"processed":processed})

if __name__=="__main__": main()
