#!/usr/bin/env python3
"""Run only suite 86 while one native process occupies most available cores.

The foreground supervisor owns and waits for exact PIDs. There are two workloads:
one threaded CPU burner and one suite. All load threads die with their process.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

ROOT = Path(__file__).resolve().parents[2]
HERE = Path(__file__).resolve().parent
SUITE = '86_veldo_0148_re_land'
PROGRAM = r'''
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
static void *busy(void *unused) {
    volatile unsigned long value = 1;
    for (;;) value = value * 1664525UL + 1013904223UL;
    return unused;
}
int main(int argc, char **argv) {
    int count = atoi(argv[1]);
    pthread_t threads[count];
    for (int i = 0; i < count; i++)
        if (pthread_create(&threads[i], NULL, busy, NULL)) return 1;
    puts("ready");
    fflush(stdout);
    pthread_join(threads[0], NULL);
    return 0;
}
'''


def main():
    cpus = sorted(os.sched_getaffinity(0))
    count = max(1, len(cpus) - 2)
    log = Path(tempfile.gettempdir()) / 'veldo148-cpu-load.log'
    with tempfile.TemporaryDirectory(prefix='v148-load-') as directory:
        source, binary = Path(directory) / 'busy.c', Path(directory) / 'busy'
        source.write_text(PROGRAM)
        subprocess.run(['cc', '-O2', '-pthread', str(source), '-o', str(binary)], check=True, capture_output=True)
        load = subprocess.Popen([str(binary), str(count)], stdout=subprocess.PIPE, text=True)
        started = time.monotonic()
        try:
            assert load.stdout.readline().strip() == 'ready'
            before = os.getloadavg()
            with log.open('w') as output:
                result = subprocess.run([sys.executable, 'scripts/selftest.py', '--suite', SUITE],
                                        cwd=ROOT, stdout=output, stderr=subprocess.STDOUT, timeout=1200)
            assert load.poll() is None
            # Account for real CPU use, not merely for creating idle threads.
            stat = Path('/proc/%d/stat' % load.pid).read_text().split()
            cpu_seconds = (int(stat[13]) + int(stat[14])) / os.sysconf('SC_CLK_TCK')
            after = os.getloadavg()
        finally:
            load.terminate()
            try:
                load.wait(timeout=30)
            except subprocess.TimeoutExpired:
                load.kill()
                load.wait(timeout=30)
            load.stdout.close()
    text = log.read_text()
    summary = re.search(r'selftest \(PARTIAL,.*?: (\d+) passed, (\d+) failed', text)
    report = dict(suite=SUITE, suite_sha256=hashlib.sha256(
        (ROOT / 'scripts/suites' / (SUITE + '.py')).read_bytes()).hexdigest(),
        cpus=cpus, load_threads=count, load_pid=load.pid, load_returncode=load.returncode,
        load_cpu_seconds=cpu_seconds, loadavg_before=before, loadavg_after=after,
        seconds=round(time.monotonic() - started, 3), subset_exit=result.returncode,
        passed=int(summary[1]) if summary else None, failed=int(summary[2]) if summary else None)
    (HERE / 'cpu-load.json').write_text(json.dumps(report, indent=1, sort_keys=True) + '\n')
    print(json.dumps(report))
    assert result.returncode == 2 and summary and int(summary[2]) == 0
    assert cpu_seconds > 0


if __name__ == '__main__':
    main()
