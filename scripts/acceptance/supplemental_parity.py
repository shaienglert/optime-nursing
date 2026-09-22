"""Run a newly reproduced B2/B3/B4 phrase through the unchanged parity recorder."""
import runpy
import sys
from pathlib import Path
from reconstructed_ten_cases import BASE, CASES as TEN

backend, case_index, output = sys.argv[1:]
index = int(case_index)
name, assistance, query, extra = TEN[index]
here = Path(__file__).resolve().parents[1] / 'decision_parity'
sys.path.insert(0, str(here))
from cases import CASES
CASES[name] = {'questionnaire': {**BASE, 'assistanceLevel': assistance, **extra}, 'query': query}
sys.argv = [str(here / 'parity_case.py'), backend, name, output]
runpy.run_path(str(here / 'parity_case.py'), run_name='__main__')
