"""Read-only scope audit; red and green are documentation checks, not owner approval."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
spec = (ROOT / 'specs/VELDO-0219-mutation-workers-admitted-by-measured-cpu-and-memory.md').read_text()
opened = (ROOT / 'proof/VELDO-0219/OPEN.md').read_text()
protected = json.loads(next(line.split(': ', 1)[1] for line in spec.splitlines()
                            if line.startswith('protected_paths:')))
footprint = spec.split('footprint:\n', 1)[1].split('behavior_bearing:', 1)[0]
paths = ['scripts/gate_schedule.py', 'engine/scripts/gate_schedule.py', 'scripts/gate_graph.json']
checks = {
    'protected_paths': all(path in protected for path in paths),
    'footprint': all('  - ' + path + '\n' in footprint for path in paths + ['proof/VELDO-0216/OPEN.md']),
    'dated_pending_amendment': 'Scope amendment, 2026-10-28, pending owner approval' in spec,
    'protected_line_inventory': all(path in opened for path in paths)
        and all(value in opened for value in ('77', '85 to 90', '103 to 105', '138', '168', '179', '185',
            '190', '201 to 213', '243', '250 to 253', '288 to 289', '451', '459 to 467',
            '528', '552 to 561', '571 to 575', '145 to 151')),
    'no_unsupported_authorization': 'authorized scheduler' not in spec,
    'memory_difference_explained': 'AC1 difference' in opened and 'page cache' in opened
        and 'pending owner approval' in opened,
}
result = dict(checks=checks, passed=all(checks.values()), owner_approval=False)
print(json.dumps(result, indent=2))
sys.exit(0 if result['passed'] else 1)
