"""Wait for the preceding gate job before running round 10 suites."""

import os
from pathlib import Path
import time


# The lock-queue log lives outside the repository; its path comes from the environment.
log = Path(os.environ['LOCK_QUEUE_RUNNER_LOG'])
while True:
    lines = log.read_text().splitlines() if log.exists() else []
    marker = next((line for line in lines if line.startswith('78a-landing-c-gate9 rc=')), None)
    if marker is not None:
        print(marker, flush=True)
        break
    print('Waiting for the gate 9 completion marker.', flush=True)
    time.sleep(120)
