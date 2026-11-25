#!/usr/bin/env python3
"""Run only suite 160's graph row; exclude its generator and shell-gate controls."""
import contextlib
import importlib.util
import io
from pathlib import Path
import tempfile

ROOT = Path(__file__).resolve().parents[2]
suite = (ROOT / 'scripts/suites/160_veldo_0358_load_leg.py').read_text()
start = suite.index('def _v358d_load_leg():')
prelude_end = suite.index('    # ------------------------------------------------------------------ AC12:')
graph_start = suite.index('    # ------------------------------------------------- AC13 under the graph scheduler:')
graph_end = suite.index('    # ---------------------------------------------- C18:')
fragment = suite[start:prelude_end] + suite[graph_start:graph_end] + '\n    shutil.rmtree(str(top))\n\n_v358d_load_leg()\n'
spec = importlib.util.spec_from_file_location('teeth', ROOT / 'scripts/check_teeth_mutations.py')
teeth = importlib.util.module_from_spec(spec)
spec.loader.exec_module(teeth)
case = next(c for c in teeth.cases() if c['name'] == 'load358-graph-red-not-blocking')
with tempfile.TemporaryDirectory(prefix='v360-load-graph-') as temporary:
    for mode in ('baseline', 'noop', 'mutant'):
        prepared = teeth.materialize(case, mode, Path(temporary) / mode)
        text = fragment
        if prepared['mutant']:
            text = text.replace('ROOT / "scripts" / "gate_schedule.py"', repr(str(prepared['mutant'])))
        rows = []
        with contextlib.redirect_stdout(io.StringIO()):
            exec(compile(text, 'suite160-graph-row-only', 'exec'),
                 dict(ROOT=ROOT, expect=lambda name, ok: rows.append((name, bool(ok)))))
        assert len(rows) == 1 and rows[0][1] == (mode != 'mutant'), rows
        print(mode, rows, flush=True)
