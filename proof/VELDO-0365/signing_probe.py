"""Light, serial single-case diagnostics; no coordinator, gate or host fixtures.

Use a fresh interpreter for each observation. The observer and materializer are the
normal mutation implementations. A profile hook reads only public timestamp operands
and component booleans at the existing assertion; it changes no verdict or clock.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path
import platform
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
WAIT_HANG_SECONDS = 600


def load(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def one(mode):
    driver = load('check_teeth_mutations')
    observer = load('mutation_observer')
    case = next(c for c in driver.cases() if c['name'] == 'signing-truncated-clock')
    operands = {}

    def profile(frame, event, arg):
        if event != 'call' or frame.f_code.co_name != '_v27_expect':
            return
        if frame.f_locals.get('row') == 'signing/transition-clock':
            ns = frame.f_globals
            operands.update(lock_release=ns['_v27_lock_release'],
                            clock_effective=ns['_v27_effective'])
        if frame.f_locals.get('row') != 'signing/kill-after-rotation':
            return
        ns = frame.f_globals
        keys, state = ns['_v27_keys'], ns['_v27_state']()
        receipt = ns['_v27_race_after']
        key = keys.entries(state)[receipt['envelope']['key_id']]
        operands.update(
            signed_at=receipt['envelope']['signed_at'], retired_at=key['retired_at'],
            effective_at=key['effective_at'], committed=ns['_v27_rotation_commit']['committed'],
            killed=ns['_v27_crash_rotation'].returncode == -ns['_v27_signal'].SIGKILL,
            snapshot_preserved=keys.entries(state) == ns['_v27_rotation_snapshot'],
            unpublished_refusal=ns['_v27_unpublished'].get('refusal'),
            published_accepted=ns['_v27_published']['accepted'],
            historical_valid=keys.verify(state, receipt), fresh_valid=keys.verify(state, receipt, fresh=True,
                now=ns['_v27_crash_epoch'] + 1.25 if '_v27_crash_epoch' in ns else None))

    with tempfile.TemporaryDirectory(prefix='signing365-') as directory:
        material = observer.materialize(case, mode, directory)
        sys.setprofile(profile)
        try:
            result = observer.worker(case, str(material['mutant']) if material['mutant'] else None)
        finally:
            sys.setprofile(None)
    return dict(mode=mode, operands=operands, result=result,
                old_digest=material['old_digest'], new_digest=material['new_digest'])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode', choices=['baseline', 'noop', 'mutant'])
    parser.add_argument('--output', type=Path)
    parser.add_argument('--repeats', type=int, default=3)
    args = parser.parse_args()
    if args.mode:
        print(json.dumps(one(args.mode)))
        return
    runs = []
    for repeat in range(args.repeats):
        for mode in ('baseline', 'noop', 'mutant'):
            process = subprocess.run([sys.executable, '-I', '-S', str(Path(__file__).resolve()),
                                      '--mode', mode], capture_output=True, text=True,
                                     timeout=WAIT_HANG_SECONDS, check=True)
            run = dict(repeat=repeat, **json.loads(process.stdout))
            runs.append(run)
            print(json.dumps(dict(repeat=repeat, mode=mode, operands=run['operands'],
                                  failed_rows=run['result']['failed_rows'])), flush=True)
    result = dict(commit=subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
                  host=platform.node(), python=sys.version, platform=platform.platform(),
                  timezone=os.environ.get('TZ'), localtime=os.readlink('/etc/localtime'),
                  clocksource=Path('/sys/devices/system/clocksource/clocksource0/current_clocksource').read_text().strip(),
                  runs=runs)
    args.output.write_text(json.dumps(result, indent=2) + '\n')


if __name__ == '__main__':
    main()
