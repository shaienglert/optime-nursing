from __future__ import annotations

import argparse
import json
import math
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.parse import urlparse


BLOCKED_DOMAINS = (
    'cms.gov','medicare.gov','dpbh.nv.gov','nvdpbh.aithent.com','health.nv.gov',
    'myhealthfacilitylicense.nv.gov','aplaceformom.com','caring.com','seniorly.com',
    'yelp.com','facebook.com','instagram.com','linkedin.com','bbb.org','yellowpages.com',
)


def _blocked(url: str) -> bool:
    domain = urlparse(str(url or '')).netloc.lower().split(':', 1)[0]
    return not domain or any(domain == d or domain.endswith('.' + d) for d in BLOCKED_DOMAINS)


def _run_chunk(index: int, *, chunk_size: int, queue_path: str, throttle: float, tmp_dir: Path) -> tuple[int, list[dict]]:
    offset = index * chunk_size
    tmp = tmp_dir / f'chunk_{index:03d}.json'
    cmd = [
        sys.executable,
        'scripts/enrich_nevada_pca_operational_primary_sources_v4.py',
        '--queue', queue_path,
        '--output', str(tmp),
        '--offset', str(offset),
        '--limit', str(chunk_size),
        '--throttle', str(max(0.0, throttle)),
    ]
    subprocess.run(cmd, check=True)
    payload = json.loads(tmp.read_text(encoding='utf-8'))
    return index, list(payload.get('records') or [])


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--queue', default='reports/NEVADA_PCA_OPERATIONAL_RESEARCH_QUEUE.json')
    ap.add_argument('--output', default='reports/NEVADA_PCA_OPERATIONAL_FULL_SWEEP.json')
    ap.add_argument('--chunk-size', type=int, default=25)
    ap.add_argument('--workers', type=int, default=4)
    ap.add_argument('--throttle', type=float, default=0.05)
    args = ap.parse_args()

    queue = json.loads(Path(args.queue).read_text(encoding='utf-8'))
    tasks = list(queue.get('tasks') or [])
    chunk_size = max(1, int(args.chunk_size))
    workers = max(1, min(8, int(args.workers)))
    chunks = math.ceil(len(tasks) / chunk_size) if tasks else 0

    tmp_dir = Path('reports/pca_full_sweep_chunks')
    tmp_dir.mkdir(parents=True, exist_ok=True)
    chunk_records: dict[int, list[dict]] = {}

    with ThreadPoolExecutor(max_workers=workers) as executor:
        futures = {
            executor.submit(
                _run_chunk,
                index,
                chunk_size=chunk_size,
                queue_path=args.queue,
                throttle=max(0.0, args.throttle),
                tmp_dir=tmp_dir,
            ): index
            for index in range(chunks)
        }
        for future in as_completed(futures):
            index, records = future.result()
            chunk_records[index] = records
            print(json.dumps({'chunk_completed': index, 'records': len(records)}, indent=2))

    all_records: list[dict] = []
    for index in range(chunks):
        all_records.extend(chunk_records.get(index, []))

    sanitized = []
    rejected_not_primary = 0
    for row in all_records:
        item = dict(row)
        if item.get('identity_verified') is True and _blocked(item.get('primary_source_url') or ''):
            item['identity_verified'] = False
            item['research_status'] = 'CANDIDATE_REJECTED_NOT_PRIMARY'
            rejected_not_primary += 1
        sanitized.append(item)

    verified = [r for r in sanitized if r.get('identity_verified') is True]
    payload = {
        'schema_version': 'nevada-pca-operational-full-sweep-v1.2.0',
        'licensed_valley_input_count': queue.get('licensed_valley_input_count'),
        'already_operationally_verified_count': queue.get('already_operationally_verified_count'),
        'research_task_count': len(tasks),
        'attempted': len(sanitized),
        'workers': workers,
        'chunk_size': chunk_size,
        'chunk_count': chunks,
        'identity_verified': len(verified),
        'source_not_found': sum(r.get('research_status') == 'SOURCE_NOT_FOUND' for r in sanitized),
        'candidates_not_identity_verified': sum(r.get('research_status') == 'CANDIDATES_NOT_IDENTITY_VERIFIED' for r in sanitized),
        'candidate_rejected_not_primary': rejected_not_primary,
        'coverage_after_verified_staging': (int(queue.get('already_operationally_verified_count') or 0) + len(verified)),
        'remaining_after_verified_staging': max(0, 363 - int(queue.get('already_operationally_verified_count') or 0) - len(verified)),
        'records': sanitized,
        'policy': 'Full-sweep output is staging evidence. Production promotion still requires live HCQC/ALiS identity gating plus primary-provider evidence. UNKNOWN remains UNKNOWN.',
    }
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    print(json.dumps({k: payload[k] for k in (
        'research_task_count','attempted','workers','chunk_count','identity_verified','source_not_found',
        'candidates_not_identity_verified','candidate_rejected_not_primary',
        'coverage_after_verified_staging','remaining_after_verified_staging',
    )}, indent=2))

    if payload['attempted'] != len(tasks):
        raise SystemExit(f"Full PCA sweep incomplete: attempted {payload['attempted']} of {len(tasks)}")
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
