# VELDO-0174 batch 2

Base: 22bec40f, incorporating main 9763249e. This is implementation evidence,
not an independent verdict, gate stamp, or proof manifest. Status: in progress.

The newest inherited round consists of README.md and evidence.json in this
folder; there is no separate review verdict or numbered round artifact.
The inherited evidence remains unchanged as history.

Completed so far:
- AC1 now has signed change_conversation_role and attach_conversation_project
  commands, owner checks, exact integer version checks, durable updates and replay.
- Suite 107 checks stale and unauthorized mutations, unknown targets, replay and
  closed-conversation refusal through the production signed command handler.
- Both pinned fake engines read a nonempty accepted skill from actual launch inputs.
- The priority journey uses a production project Line, a signed active project,
  a real claimed execution unit, eligibility Gate, Runner and receiver subprocess.
  The project build waits while the conversation holds the only Claude account,
  then starts when the turn ends. No Line or pool chooser is replaced.

Latest focused run at this checkpoint: python3 scripts/selftest.py --suite
107_veldo_0174_conversations, exit 1, 29 ticket rows passed, one failed:
AC1/restart-open. The production service's AF_UNIX socket creation raises
PermissionError: [Errno 1] Operation not permitted. This remains a failure.

Next: run the declared falsifiers and static checks, retain exact results and
host commands, and answer all inherited open items with source references.
