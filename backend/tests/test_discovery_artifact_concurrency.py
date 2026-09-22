"""A slow research call must not prevent another connection saving family intake."""
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app import main  # registers the production schema without starting schedulers
from app.models.agent_execution import AgentJobRun
from app.models.facility import Facility
from app.services import agent_knowledge_reports as reports
from app.services import decision_result_store as store
from app.services import external_discovery as discovery


@pytest.fixture
def sessions(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'concurrent.db'}", connect_args={'timeout': 0.05})
    main.Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, autoflush=False)
    monkeypatch.setattr(store, 'SessionLocal', factory)
    yield factory
    engine.dispose()


def test_pending_workflow_releases_writer_before_source_io(sessions):
    tokens = []
    def network_work(_db):
        with sessions() as observer:
            assert observer.query(AgentJobRun).filter_by(status='RUNNING').count() == 1
        tokens.append(store.remember_decision_result({'needs': []}, inputs_fingerprint='family'))
        return {'items_processed': 1}
    with sessions() as db, patch.object(reports, '_provider_intelligence_work', side_effect=network_work):
        reports._run_agent_workflow(db, 'provider_intelligence')
        db.commit()
    assert store.recall_decision_result(tokens[0], inputs_fingerprint='family') == {'needs': []}


def test_discovery_releases_caller_and_previous_source_transactions(sessions):
    with sessions() as db:
        facility = Facility(cms_id='TEST', name='Test home', address='Test', city='Las Vegas', state='NV', zip_code='89101')
        db.add(facility)
        db.commit()
        # Same situation as the scheduled agent: its RUNNING status was flushed.
        db.add(AgentJobRun(agent_key='provider_intelligence', status='RUNNING'))
        db.flush()
        sources = [discovery.SourceDescriptor(f'source-{n}', 'official_facility', f'https://example.test/{n}', None, 'provider_intelligence', 'web') for n in range(2)]
        saved = []
        def network_source(*_args, **_kwargs):
            saved.append(store.remember_decision_result({'needs': []}, inputs_fingerprint='family'))
            return {'request_status': 'RAN_CONNECTED_NO_NEW_VALUE', 'claims': [], 'result_classification': 'CONNECTED_NO_DATA', 'response_code': 200}
        with patch.object(discovery, '_load_source_registry', return_value={}), \
             patch.object(discovery, '_cms_provider_rows', return_value={}), \
             patch.object(discovery, '_cms_inspection_rows', return_value={}), \
             patch.object(discovery, '_cms_quality_rows', return_value={}), \
             patch.object(discovery, '_source_descriptors', return_value=sources), \
             patch.object(discovery, '_process_source', side_effect=network_source):
            result = discovery.run_external_discovery(db)
    assert result['source_failures'] == 0
    assert result['source_successes'] == 2
    assert len(saved) == 2
