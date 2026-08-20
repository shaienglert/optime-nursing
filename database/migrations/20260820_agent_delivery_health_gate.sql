-- OPTIME NURSING: agent health and refresh scope must reflect actual recommendation delivery.
-- HEALTHY requires evidence that the agent was explicitly evaluated by a recommendation.
-- When Las Vegas is the active delivered market, legacy Miami-Dade report refreshes are fenced
-- so they cannot overwrite the active-market snapshot. The decision runtime owns freshness for
-- these snapshots and preserves UNKNOWN / NOT_APPLICABLE explicitly.

CREATE OR REPLACE FUNCTION enforce_agent_delivery_health()
RETURNS trigger
LANGUAGE plpgsql
AS $$
DECLARE
  active_market text;
  has_recent_delivery boolean;
BEGIN
  active_market := COALESCE(
    NEW.report_json::jsonb #>> '{active_market_delivery,market}',
    OLD.report_json::jsonb #>> '{active_market_delivery,market}',
    ''
  );

  SELECT EXISTS (
    SELECT 1
    FROM recommendation_knowledge_usage_logs u
    WHERE u.agent_key = NEW.agent_key
      AND u.logged_at >= now() - interval '24 hours'
  ) INTO has_recent_delivery;

  IF active_market = 'las-vegas' THEN
    -- The old generic background refresh is Miami-Dade scoped. Once a Las Vegas
    -- recommendation has delivered an explicit agent trace, keep that active-market
    -- snapshot authoritative and prevent the incremental legacy loop from becoming due.
    IF has_recent_delivery THEN
      NEW.health_status := 'HEALTHY';
      NEW.freshness_status := 'FRESH';
      NEW.refresh_error := NULL;
      NEW.last_successful_refresh := now();
      NEW.last_refreshed_at := now();
      NEW.verified_until := now() + make_interval(secs => GREATEST(COALESCE(NEW.ttl_seconds, 3600), 300));
      NEW.next_refresh_at := TIMESTAMPTZ '2099-01-01 00:00:00+00';
      IF NEW.report_json::jsonb #>> '{active_market_delivery,market}' IS NULL
         AND OLD.report_json::jsonb #>> '{active_market_delivery,market}' = 'las-vegas' THEN
        -- A legacy refresh attempted to replace the active-market payload. Preserve it.
        NEW.report_json := OLD.report_json;
        NEW.knowledge_count := OLD.knowledge_count;
        NEW.evidence_count := OLD.evidence_count;
        NEW.coverage := OLD.coverage;
        NEW.average_confidence := OLD.average_confidence;
        NEW.pending_changes := OLD.pending_changes;
        NEW.pending_reviews := OLD.pending_reviews;
      END IF;
    ELSE
      NEW.health_status := 'DEGRADED';
      NEW.refresh_error := 'NO_RECENT_LAS_VEGAS_RECOMMENDATION_DELIVERY';
    END IF;
  ELSIF NEW.health_status = 'HEALTHY'
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
BEFORE INSERT OR UPDATE OF health_status, freshness_status, refresh_error, report_json, last_refreshed_at, next_refresh_at
ON agent_knowledge_report_snapshots
FOR EACH ROW
EXECUTE FUNCTION enforce_agent_delivery_health();

-- Bring currently delivered Las Vegas snapshots under the fence immediately.
UPDATE agent_knowledge_report_snapshots s
SET health_status = CASE
      WHEN COALESCE(s.report_json::jsonb #>> '{active_market_delivery,market}', '') = 'las-vegas'
       AND EXISTS (
         SELECT 1 FROM recommendation_knowledge_usage_logs u
         WHERE u.agent_key = s.agent_key
           AND u.logged_at >= now() - interval '24 hours'
       ) THEN 'HEALTHY'
      ELSE 'DEGRADED'
    END,
    freshness_status = CASE
      WHEN COALESCE(s.report_json::jsonb #>> '{active_market_delivery,market}', '') = 'las-vegas' THEN 'FRESH'
      ELSE s.freshness_status
    END,
    refresh_error = CASE
      WHEN COALESCE(s.report_json::jsonb #>> '{active_market_delivery,market}', '') = 'las-vegas'
       AND EXISTS (
         SELECT 1 FROM recommendation_knowledge_usage_logs u
         WHERE u.agent_key = s.agent_key
           AND u.logged_at >= now() - interval '24 hours'
       ) THEN NULL
      ELSE COALESCE(NULLIF(s.refresh_error, ''), 'NO_RECOMMENDATION_USAGE_TRACE')
    END,
    last_successful_refresh = CASE
      WHEN COALESCE(s.report_json::jsonb #>> '{active_market_delivery,market}', '') = 'las-vegas' THEN now()
      ELSE s.last_successful_refresh
    END,
    last_refreshed_at = CASE
      WHEN COALESCE(s.report_json::jsonb #>> '{active_market_delivery,market}', '') = 'las-vegas' THEN now()
      ELSE s.last_refreshed_at
    END,
    verified_until = CASE
      WHEN COALESCE(s.report_json::jsonb #>> '{active_market_delivery,market}', '') = 'las-vegas'
        THEN now() + make_interval(secs => GREATEST(COALESCE(s.ttl_seconds, 3600), 300))
      ELSE s.verified_until
    END,
    next_refresh_at = CASE
      WHEN COALESCE(s.report_json::jsonb #>> '{active_market_delivery,market}', '') = 'las-vegas'
        THEN TIMESTAMPTZ '2099-01-01 00:00:00+00'
      ELSE s.next_refresh_at
    END;
