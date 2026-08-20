-- OPTIME NURSING: an agent report must not be HEALTHY merely because its knowledge is fresh.
-- HEALTHY requires evidence that the agent's knowledge was actually consumed by a recommendation.

CREATE OR REPLACE FUNCTION enforce_agent_delivery_health()
RETURNS trigger
LANGUAGE plpgsql
AS $$
BEGIN
  IF NEW.health_status = 'HEALTHY'
     AND NOT EXISTS (
       SELECT 1
       FROM recommendation_knowledge_usage_logs u
       WHERE u.agent_key = NEW.agent_key
     ) THEN
    NEW.health_status := 'DEGRADED';
    IF COALESCE(NEW.refresh_error, '') = '' THEN
      NEW.refresh_error := 'NO_RECOMMENDATION_USAGE_TRACE';
    END IF;
  END IF;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS trg_agent_delivery_health ON agent_knowledge_report_snapshots;
CREATE TRIGGER trg_agent_delivery_health
BEFORE INSERT OR UPDATE OF health_status, refresh_error, last_refreshed_at
ON agent_knowledge_report_snapshots
FOR EACH ROW
EXECUTE FUNCTION enforce_agent_delivery_health();

UPDATE agent_knowledge_report_snapshots s
SET health_status = 'DEGRADED',
    refresh_error = COALESCE(NULLIF(refresh_error, ''), 'NO_RECOMMENDATION_USAGE_TRACE')
WHERE health_status = 'HEALTHY'
  AND NOT EXISTS (
    SELECT 1
    FROM recommendation_knowledge_usage_logs u
    WHERE u.agent_key = s.agent_key
  );
