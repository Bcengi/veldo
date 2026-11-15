# VELDO-0329 build blocker

Inspected base: 8ef46604e80e6a69909556c82e4e9b17e2acde87, branch veldo-space-0329.

The supplied baseline description lists VELDO-0315 and VELDO-0323 as built. Their
implementations are absent in this tree. VELDO-0314 is also absent.

Evidence from the supplied tree:

- packs/claude/hooks/hooks.json contains only PreToolUse. There are no SessionStart
  or SessionEnd hooks or session scripts to install.
- engine/bin/veldo:space_event documents and implements the missing-command answer
  space_no_command:space_event. Its session event carries a session id and paths,
  but creates no session scratch item.
- engine/.veldo/control_space.py has no event command. Its reconcile command only
  records counts; it does not run the snapshot or missing-hook checks.
- engine/.veldo/control_space_reconcile.py implements Docker ownership placement
  only. Its module documentation assigns the snapshot and other reconcile rows
  to VELDO-0315. It contains no reconcile runner.

AC2 requires a session under the second installed account to create an item.
AC3 requires a reconcile after a hook disappears to report that hook. These
end-to-end proofs cannot be produced from the supplied runtime without building
other tickets. The instruction to build only VELDO-0329 excludes that work.

No implementation, removal, hook installation, capture edit or protected-path
change was made. No acceptance test or falsifier was run, and no passing proof
manifest is claimed. The ticket remains ready with its criteria unchanged.

Resume on a base containing the session hooks, event command and reconcile
runner, or obtain an explicit scope decision allowing installer-only work with
its integration evidence pending. The lead's full verification command remains
./scripts/verify.sh.

Checks on the blocker record:

- python3 .veldo/validate.py all: exit 0.
- bash scripts/check_docs.sh: exit 0, docs hygiene pass.
- Template sync was not needed: engine/ was unchanged.
- No full gate, heavy suite, teeth run or policy check was run.
