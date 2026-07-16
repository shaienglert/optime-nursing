const fs = require('fs');
const path = require('path');

const repoRoot = path.join(__dirname, '..');
const storePath = path.join(repoRoot, 'data', 'outcome_event_log.json');

function nowIso() {
  return new Date().toISOString();
}

function createEmptyStore() {
  return {
    version: 1,
    created_at: nowIso(),
    updated_at: nowIso(),
    sessions: [],
  };
}

function ensureStoreDir() {
  fs.mkdirSync(path.dirname(storePath), { recursive: true });
}

function loadStore() {
  ensureStoreDir();
  if (!fs.existsSync(storePath)) {
    const initial = createEmptyStore();
    fs.writeFileSync(storePath, JSON.stringify(initial, null, 2));
    return initial;
  }

  try {
    const parsed = JSON.parse(fs.readFileSync(storePath, 'utf8'));
    if (!parsed || !Array.isArray(parsed.sessions)) {
      return createEmptyStore();
    }
    return parsed;
  } catch (_error) {
    return createEmptyStore();
  }
}

function saveStore(store) {
  store.updated_at = nowIso();
  fs.writeFileSync(storePath, JSON.stringify(store, null, 2));
}

function upsertSearchSession(session) {
  const store = loadStore();
  const index = store.sessions.findIndex((item) => item.search_id === session.search_id);
  const normalized = {
    search_id: session.search_id,
    persona_type: session.persona_type,
    top_10_recommendations: session.top_10_recommendations || [],
    weights_used: session.weights_used || [],
    confidence_score: Number(session.confidence_score || 0),
    events: session.events || [],
    selected_facility_id: session.selected_facility_id || null,
    cohort: session.cohort || 'unknown',
    created_at: session.created_at || nowIso(),
    updated_at: nowIso(),
  };

  if (index === -1) {
    store.sessions.push(normalized);
  } else {
    store.sessions[index] = {
      ...store.sessions[index],
      ...normalized,
      events: normalized.events.length > 0 ? normalized.events : (store.sessions[index].events || []),
      created_at: store.sessions[index].created_at || normalized.created_at,
      updated_at: nowIso(),
    };
  }

  saveStore(store);
  return normalized;
}

function appendEvent(searchId, eventType, payload = {}) {
  const store = loadStore();
  const session = store.sessions.find((item) => item.search_id === searchId);
  if (!session) {
    throw new Error(`Unknown search_id: ${searchId}`);
  }

  const event = {
    event_type: eventType,
    facility_id: payload.facility_id || null,
    user_feedback_score: payload.user_feedback_score ?? null,
    metadata: payload.metadata || {},
    occurred_at: payload.occurred_at || nowIso(),
  };

  session.events = session.events || [];
  session.events.push(event);
  session.updated_at = nowIso();
  saveStore(store);
  return event;
}

module.exports = {
  storePath,
  loadStore,
  saveStore,
  upsertSearchSession,
  appendEvent,
};
