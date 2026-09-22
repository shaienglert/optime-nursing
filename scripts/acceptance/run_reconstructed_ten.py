"""Bounded synthetic API check. Run one case per subprocess with no live AI key.

Original run_ten.py and ten_cases.py were unavailable. These fixtures are explicitly
reconstructed. Interview AI is READY; ranking uses its real unavailable path.
Named background workers are paused so requests are reproducible and bounded.
"""
import json
import logging
import os
from pathlib import Path
import sys
import tempfile
import threading
from unittest.mock import patch

from reconstructed_ten_cases import BASE, CASES

index, out = int(sys.argv[1]), Path(sys.argv[2])
os.environ['DATABASE_URL'] = 'sqlite:///' + str(Path(tempfile.mkdtemp(prefix='oomnik-ten-')) / 'case.db')
os.environ['OPTIME_CANONICAL_MARKET'] = 'las-vegas'
os.environ.pop('OPTIME_SEMANTIC_AI_API_KEY', None)
logging.disable(logging.CRITICAL)
original_start = threading.Thread.start

def start(self, *args, **kwargs):
    if self.daemon and str(self.name).startswith(('optime-', 'agent-', 'executive-', 'oomnik-')):
        return None
    return original_start(self, *args, **kwargs)

threading.Thread.start = start
name, assistance, narrative, extra = CASES[index]
questionnaire = dict(BASE, assistanceLevel=assistance, **{})
questionnaire.update(extra)
body = dict(questionnaire_state=questionnaire, natural_language_query=narrative, limit=5)
ready = dict(decision_readiness='READY', next_question=None, statements=[])
with patch.dict(os.environ, {'OPTIME_SEMANTIC_AI_ENABLED': '1', 'OPTIME_SEMANTIC_AI_REQUIRED': '1'}), patch('app.services.human_intelligence_runtime_verified.interpret_client_intent_with_ai', return_value=ready):
    from app.main import app
    from fastapi.testclient import TestClient
    with TestClient(app) as client:
        runs = []
        for repeat in range(2):
            p = client.post('/decision-engine/patient-needs-profile', json=body)
            r = client.post('/decision-engine/recommendations', json=body)
            result = r.json()
            report = client.post('/decision-engine/personal-report', json={**body, 'decision_id': result.get('decision_id')})
            profile = p.json()
            decision = result.get('decision_intelligence', {})
            state = decision.get('canonical_decision_state', {})
            needs = {n['parameter_id']: n['requirement_level'] for n in profile.get('needs', [])}
            shown = result.get('results', []) if state.get('can_show_recommendations') else []
            checks = {'all_http_200': all(x.status_code == 200 for x in (p,r,report)), 'no_pending_recommendations': all(x.get('must_eligibility') == 'MUST_ELIGIBLE' for x in shown)}
            if index in (1,3,6): checks['no_invented_transfers'] = 'transfer_assistance' not in needs
            if index in (3,6): checks['medication_without_adl'] = needs.get('medication_support') == 'HIGH' and 'adl_support' not in needs
            if index == 2: checks['transfer_high'] = needs.get('transfer_assistance') == 'HIGH'
            if index == 4: checks['memory_need'] = 'memory_care' in needs
            if index == 5: checks['pt_and_ot'] = all(x in needs for x in ('pt','ot'))
            if index == 6: checks['dialysis_required'] = needs.get('dialysis_arrangements') == 'REQUIRED'
            if index == 7: checks['wound_high'] = needs.get('wound_care') == 'HIGH'
            household = decision.get('living_strategy', {}).get('household', {})
            if index == 9: checks['couple'] = household.get('type') == 'COUPLE'
            runs.append(dict(repeat=repeat+1, needs=needs, need_records=profile.get('needs', []), musts=decision.get('client_intent', {}).get('must_haves', []), semantic_musts=decision.get('semantic_facility_requirements', {}).get('requirements', []), must_gate=decision.get('must_gate', {}), phase=state.get('phase'), household=household, shown_facilities=[x.get('canonical_facility_id') for x in shown], http=[p.status_code,r.status_code,report.status_code], checks=checks))
        out.write_text(json.dumps(dict(case=name, reconstructed=True, runs=runs, repeated_facilities_identical=runs[0]['shown_facilities']==runs[1]['shown_facilities']), indent=2))
