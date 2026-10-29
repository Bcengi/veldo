"""Check the deferred batch handoff text, without running a gate."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[3]
text=' '.join((ROOT/'proof/VELDO-0219/OPEN.md').read_text().split())
checks={
    'joint-target': all(s in text for s in ('6,000','VELDO-0216','VELDO-0219','without VELDO-0221')),
    'batch-only': all(s in text for s in ('37191','batch gate','landing candidate')),
    'controls': all(s in text for s in ('fixed-sixteen','serialized','4,000')),
    'measurements': all(s in text for s in ('critical path','quiet measurement','zero worker deadline','every node','every case')),
}
print(json.dumps(checks,indent=2))
raise SystemExit(not all(checks.values()))
