#!/usr/bin/env python3
"""Read-only verification of frozen evidence; write a new named checkpoint only."""
import argparse
import hashlib
import json
from pathlib import Path
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
REPO = ROOT.parents[3]
MEMORY = ROOT.parent

def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as f:
        for b in iter(lambda: f.read(4*1024*1024), b''):
            h.update(b)
    return h.hexdigest()

def verify(label, root, rows):
    failures = []
    for row in rows:
        p = root / row['path']
        actual = digest(p) if p.is_file() else None
        if actual != row['sha256']:
            failures.append(dict(path=row['path'], expected_sha256=row['sha256'], actual_sha256=actual))
    print(label, len(rows), 'FAIL' if failures else 'PASS', flush=True)
    return dict(label=label, file_count=len(rows), status='FAIL' if failures else 'PASS', failures=failures)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--stage', required=True)
    ap.add_argument('--scope', choices=['repository','external'], default='repository')
    args = ap.parse_args()
    output = ROOT/'integrity'/f'{args.stage}_{args.scope}.json'
    if output.exists():
        raise SystemExit('Refusing to overwrite checkpoint: '+str(output))
    base = json.loads((MEMORY.parent/'baseline_integrity_manifest.json').read_text())
    checks = []
    if args.scope == 'repository':
        checks.append(verify('protected_DATE_repository', REPO, base['repository']['files']))
        specs = [(MEMORY/'GATE2_GATE3_EVIDENCE_MANIFEST.json', MEMORY)]
        for name in ['gate3_openram_attempt03_target_diagnosis','gate3_openram_attempt04_sky130_control_integration_repair','gate3_openram_attempt05_sky130_primitive_view_materialization_qualification','gate3_attempt06_replacement_sram_backend_qualification','gate3_attempt07_sram22_matched_physical_closure','gate3_attempt08_sram22_slew_provenance_and_drv_closure','gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure']:
            root = MEMORY/name
            specs.extend((p,root) for p in root.glob('ATTEMPT*_EVIDENCE_MANIFEST.json'))
        for manifest, root in specs:
            data = json.loads(manifest.read_text())
            rows = data.get('files', data.get('artifacts'))
            result = verify(root.name, root, rows)
            result.update(manifest=str(manifest.relative_to(REPO)).replace('\\','/'), manifest_sha256=digest(manifest))
            checks.append(result)
        src = MEMORY/'gate3_attempt06_replacement_sram_backend_qualification'/'SRAM22_SOURCE_MANIFEST.json'
        data = json.loads(src.read_text())
        rows = [r for r in data['artifacts'] if r['role']=='macro_source_artifact']
        checks.append(verify('Attempt09_frozen_SRAM22_sources', MEMORY/'gate3_attempt09_sram22_residual_interface_drv_and_provenance_closure'/'source_checkout', rows))
    else:
        for label,data in base['external_evidence'].items():
            root = Path(data['root'])
            result = verify(label,root,data['files'])
            expected = {r['path'] for r in data['files']}
            actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file()}
            result['added'] = sorted(actual-expected)
            if result['added']: result['status']='FAIL'
            checks.append(result)
    payload = dict(stage=args.stage, scope=args.scope, generated_utc=datetime.now(timezone.utc).isoformat(), algorithm='sha256-raw-bytes', baseline_manifest_sha256=digest(MEMORY.parent/'baseline_integrity_manifest.json'), checks=checks, status='PASS' if all(r['status']=='PASS' for r in checks) else 'FAIL')
    output.parent.mkdir(parents=True,exist_ok=True)
    output.write_text(json.dumps(payload,indent=2)+'\n')
    raise SystemExit(0 if payload['status']=='PASS' else 1)

if __name__=='__main__': main()
