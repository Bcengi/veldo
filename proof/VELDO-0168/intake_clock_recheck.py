"""Run one VELDO-0168 case through its normal dispatcher, restoring temporary edits."""
from pathlib import Path
import subprocess
import sys
import tempfile

root = Path.cwd()
case = sys.argv[1]
assert case in ('row', 'suite', 'send-mutant', 'clock-mutant')
suite = root / 'scripts/suites/86_veldo_0168_text.py'
source = root / '.veldo/control_intake.py'
helper = root / 'scripts/suites/support/v73_authority.py'
originals = {p: p.read_bytes() for p in (suite, source, helper)}
try:
    if case == 'row':
        # Keep real authority/HTTP setup, clock probes, intake row and finally cleanup.
        # Remove the other row bodies, rather than merely filtering their printed results.
        text = originals[suite].decode()
        start = text.index('    names = ')
        end = text.index('    rows = ', start)
        text = text[:start] + "    names = ('intake/delivery',)\n" + text[end:]
        start = text.index('            def opened(')
        end = text.index('            # Frozen clock probes', start)
        text = text[:start] + text[end:]
        start = text.index('            # Telegram trims')
        end = text.index('        except Exception as error:', start)
        text = text[:start] + text[end:]
        suite.write_text(text)
    elif case == 'send-mutant':
        text = originals[source].decode()
        old = "prompt = render_prompt(question['prompt'])"
        assert text.count(old) == 1
        source.write_text(text.replace(old, "prompt = question['prompt']"))
    elif case == 'clock-mutant':
        text = originals[helper].decode()
        old = "'date': int(time.time()) + st['tick']"
        assert text.count(old) == 1
        helper.write_text(text.replace(old, "'date': 1791000000 + st['tick']"))
    with tempfile.TemporaryDirectory(prefix='veldo0148-home-', dir='/dev/shm') as home:
        env = dict(PATH='/usr/bin:/bin', HOME=home, TMPDIR='/dev/shm', LANG='C.UTF-8',
                   LC_ALL='C.UTF-8', TZ='UTC', PYTHONDONTWRITEBYTECODE='1',
                   PYTHONNOUSERSITE='1', PYTHONHASHSEED='0', GIT_CONFIG_NOSYSTEM='1',
                   GIT_CONFIG_GLOBAL='/dev/null', GIT_TERMINAL_PROMPT='0',
                   XDG_RUNTIME_DIR='/run/user/1000',
                   DBUS_SESSION_BUS_ADDRESS='unix:path=/run/user/1000/bus',
                   VELDO_0168_INTAKE_TRACE='1')
        result = subprocess.run(['python3', 'scripts/selftest.py', '--suite', '86_veldo_0168_text'],
                                cwd=root, env=env)
        print('RECHECK case=%s dispatcher_exit=%s' % (case, result.returncode), flush=True)
finally:
    for path, data in originals.items():
        if path.read_bytes() != data:
            path.write_bytes(data)

sys.exit(result.returncode)
