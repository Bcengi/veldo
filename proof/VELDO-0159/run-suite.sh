#!/bin/bash
# Run one command under the gate lock in a bounded user unit, waiting at most $WAIT seconds for the lock
# (exit 75 when the lock was not taken). Usage: WAIT=570 proof/VELDO-0159/run-suite.sh <log> <command...>
log=$1; shift
cd "$(dirname "$0")/../.." || exit 1
flock -w "${WAIT:-570}" /home/dmitry/.local/state/core-gates/.gate.lock \
  systemd-run --user --unit=${UNIT:-veldo-0159}-$(date +%s) -p MemoryHigh=14G -p MemoryMax=16G -p OOMScoreAdjust=900 \
  --wait --collect --pipe --quiet --working-directory="$PWD" --setenv=PATH="$PATH" \
  bash -c '"$@" > "'"$log"'" 2>&1; echo "exit $?" >> "'"$log"'"' _ "$@"
status=$?
[ $status -eq 1 ] && [ ! -s "$log" ] && exit 75
exit $status
