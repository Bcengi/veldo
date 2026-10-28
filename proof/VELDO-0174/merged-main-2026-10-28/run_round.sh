#!/bin/sh
# VELDO-0174 merged-main round, 2026-10-28. Run from the repository root as:
#   flock /home/dmitry/.local/state/core-gates/.gate.lock sh proof/VELDO-0174/merged-main-2026-10-28/run_round.sh LOGDIR [STEP...]
# Steps: s107 s105 s86 falsifiers. Each command's exit status goes to LOGDIR/status.txt.
logs=$1; shift
mkdir -p "$logs"
steps=${*:-s107 s105 s86 falsifiers}
run() { name=$1; shift; echo "\$ $*" > "$logs/$name.cmd"; "$@" > "$logs/$name.log" 2>&1; echo "$name $?" >> "$logs/status.txt"; }
for step in $steps; do
  case $step in
    s107) run s107 python3 scripts/selftest.py --suite 107_veldo_0174_conversations ;;
    s105) run s105 python3 scripts/selftest.py --suite 105_veldo_0182_memory ;;
    s86) run s86 python3 scripts/selftest.py --suite 86_veldo_0127_agent_configuration ;;
    falsifiers)
      for case in v174-attach-outside-current-scope v174-attach-another-owners-project v174-record-memory-only \
          v174-offer-every-waiting-turn v174-project-lines-first v174-no-work-conversation-line-dropped \
          v174-mutation-siblings-missing v174-signed-commands-bypass-mutant v174-ignore-record-version v174-drop-skills; do
        run "f-$case" python3 proof/VELDO-0174/run_falsifier.py "$case" --log-dir "$logs/falsifiers"
        run "restored-$case" python3 scripts/selftest.py --suite 107_veldo_0174_conversations
      done ;;
  esac
done
