#!/usr/bin/env python3
"""Re-emit today's corpus through the one writer; never rewrite the input files."""
import hashlib
import json
from pathlib import Path
import sys

from test_document_writer import ROOT, Y, differences, yaml


def audit(root=ROOT):
    baseline = json.loads((root / 'proof/VELDO-0110/corpus-before.json').read_text())
    paths = sorted({row['path'] for row in baseline['corpus']} |
                   {p.relative_to(root).as_posix() for folder in ('specs', 'plans')
                    for p in (root / folder).glob('*.md')})
    rows = []
    for path in paths:
        raw = (root / path).read_bytes()
        text = raw.decode('utf-8')
        row = {'path': path, 'sha256': hashlib.sha256(raw).hexdigest(), 'differences': []}
        try:
            original = Y.front_matter(text, path)
            if original is None:
                row['status'] = 'no front matter; body preserved verbatim'
                emitted = text
            else:
                match = Y.front_matter_match(text)
                emitted = Y.render_document(original, text[match.end():])
                row['differences'] = differences(original, Y.front_matter(emitted))
                row['oracle'] = ('STANDS DOWN: writer/corpus-real-yaml-oracle; PyYAML unavailable'
                                 if yaml is None else 'checked')
                if yaml is not None:
                    row['oracle_differences'] = differences(original, yaml.safe_load(Y.front_matter_match(emitted)[1]))
                row['status'] = 're-emitted'
            row['emitted_sha256'] = hashlib.sha256(emitted.encode()).hexdigest()
        except ValueError as exc:
            row['refusal'] = str(exc)
        rows.append(row)
    failures = [r for r in rows if r.get('refusal') or r['differences'] or r.get('oracle_differences')]
    return {'baseline_documents': len(baseline['corpus']), 'documents': len(rows),
            're_emitted': sum(r.get('status') == 're-emitted' for r in rows),
            'oracle': 'PyYAML ' + yaml.__version__ if yaml else 'STANDS DOWN: writer/corpus-real-yaml-oracle; PyYAML unavailable',
            'failures': len(failures), 'corpus': rows}


if __name__ == '__main__':
    report = audit()
    if len(sys.argv) == 2:
        Path(sys.argv[1]).write_text(json.dumps(report, indent=2, ensure_ascii=True) + '\n')
    print(f"Writer corpus: {report['documents']} documents, {report['re_emitted']} re-emitted, {report['failures']} failures; {report['oracle']}")
    for row in report['corpus']:
        if row.get('refusal') or row['differences'] or row.get('oracle_differences'):
            print(json.dumps(row, ensure_ascii=True))
    raise SystemExit(bool(report['failures']))
