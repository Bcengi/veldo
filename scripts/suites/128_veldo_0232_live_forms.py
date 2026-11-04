"""VELDO-0232 AC3, VELDO-0172's rule: every Antigravity fake engine in the suites prints the forms of a recorded real
1.5.0 stream-json run, the one the owner approves, kept in the proof (proof/VELDO-0232/live-stream.jsonl, one
stdout line per line as the binary printed it).

Run: python3 scripts/selftest.py --suite 128_veldo_0232_live_forms

Only shared ROOT and expect are consumed. Reads the recorded run and the fake's forms (scripts/suites/support/
v232_agy_forms.py, which suite 127's fake prints); a form is a line's type, its step type and the names of its
fields. Red until the lead records the run: no capture is no evidence. Writes nothing.
"""


def _v232_live_forms():
    import importlib.util
    import json

    LIVE = ROOT / 'proof' / 'VELDO-0232' / 'live-stream.jsonl'
    spec = importlib.util.spec_from_file_location('v232_live_forms', str(ROOT / 'scripts/suites/support/v232_agy_forms.py'))
    forms = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(forms)
    record = json.loads((ROOT / '.veldo' / 'runtime' / 'antigravity-qualification.json').read_text())
    live, unread = set(), 0
    if LIVE.is_file():
        for raw in LIVE.read_text().splitlines():
            try:
                event = json.loads(raw)
            except ValueError:
                unread += 1
                continue
            if isinstance(event, dict):
                live.add(forms.form(event))
    fakes = forms.fake_forms(record['tool_registry'])
    missing = sorted(map(str, fakes - live))
    expect('VELDO-0232 stream/live-forms' + ((': the fakes print forms the recorded real run does not [%s]'
                                              % missing[:3]) if missing or not live else ''),
           bool(live) and not missing)


_v232_live_forms()
