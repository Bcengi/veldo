"""VELDO-0161 development observation, NOT evidence for AC2: suite 109 with the installed authority service's
own serve() running in a thread of this process over a socketpair transport (inprocess_transport.py), for a
sandbox that refuses AF_UNIX sockets. Everything else is the suite unchanged: the installed fixed executable
is loaded from the installation's bin/, its socket bind and the client's connect are the only substitutions,
and its signal handlers are captured so a stop is the SIGTERM handler it installed.

What this cannot show: that the service is a SEPARATE process that is neither restarted nor reinstalled (a
thread shares this process's pid and start time), and the exec-restart falsifier (adoption161-restart-take-on)
would replace this whole process. Those belong to the real suite on a host with local sockets.

    python3 proof/VELDO-0161/inprocess_harness.py <checkout>                       baseline
    python3 proof/VELDO-0161/inprocess_harness.py <checkout> <module> <mutant>     one production copy replaced

Prints one `ROW ok|RED <label>` line per VELDO-0161 row.
"""
import sys
from pathlib import Path

root = Path(sys.argv[1])
suite = (root / 'scripts/suites/109_veldo_0161_adoption.py').read_text()


def rep(old, new):
    global suite
    assert suite.count(old) == 1, old
    suite = suite.replace(old, new)


rep("    UNIX = unix_sockets()\n", "    UNIX = True\n    DEV = __import__('runpy').run_path(%r)\n"
    % str(Path(__file__).with_name('inprocess_transport.py')))
rep("        if UNIX:\n            with wire.active():", "        if False:\n            with wire.active():")
start = suite.index("            def start_service():")
end = suite.index("            def send(workspace, packet, who='steward'):")
suite = suite[:start] + """            def start_service():
                return DEV['start'](installed['executable'], config_path, service_config['socket'])

            def stop_service(proc):
                proc.send_signal(15)
                proc.wait(timeout=30)

""" + suite[end:]
rep("                    return CC.send(str(workspace), packet, CE, binding_verify,",
    "                    return DEV['send'](CC, str(workspace), packet, CE, binding_verify,")
rep("            def process_start(pid):\n                text",
    "            def process_start(pid):\n                pid = __import__('os').getpid()\n                text")
if len(sys.argv) > 3:
    module, mutant = sys.argv[2], sys.argv[3]
    rep('ROOT / ".veldo" / "%s"' % module, '__import__("pathlib").Path(%r)' % mutant)
shared = root / 'scripts/suites/shared.py'
ns = {'__file__': str(shared)}
exec(compile(shared.read_text(), str(shared), 'exec'), ns)
rows = []
original = ns['expect']


def expect(name, condition):
    rows.append((name, bool(condition)))
    return original(name, condition)


ns['expect'] = expect
exec(compile(suite, 'suite109-inprocess', 'exec'), ns)
for name, ok in rows:
    if 'VELDO-0161' in name:
        print('ROW', 'ok ' if ok else 'RED', name)
