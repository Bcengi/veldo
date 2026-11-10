"""Wait for the preceding gate job before running round 10 suites."""

from pathlib import Path
import time


log = Path('/home/dmitry/projects/myday/research/lock-queue/runner.log')
while True:
    lines = log.read_text().splitlines() if log.exists() else []
    marker = next((line for line in lines if line.startswith('78a-landing-c-gate9 rc=')), None)
    if marker is not None:
        print(marker, flush=True)
        break
    print('Waiting for the gate 9 completion marker.', flush=True)
    time.sleep(120)
