# VELDO-0109 proof

PLAN-0019 W86, revision 2. Author: Ava (Claude), under Dmitry's rule that when Codex is out the
author writes and Codex validates. Codex validates this item in the batch of 2026-09-22.

**NOT A CLAIM YET.** The specification is DRAFT, so by the methodology's own ready boundary this
bundle is held as `manifest.draft.json` and is not a proof. The work is real; the claim would be
premature.

## The dangerous behaviour here is the helpful-looking one

A client that cannot reach the authority and writes locally "until it comes back" has created a
**second authority**, and the two will disagree about work that was already accepted. Every recovery
rule in the design assumes one history. A local fallback breaks that assumption silently, at exactly
the moment nobody is watching, and it looks like resilience while it does it.

So the whole of this item is three refusals and one honest answer.

## What landed

Additions to `.veldo/control_client.py`, mirrored into `engine/.veldo/`.

An accepted response carries the authority's own **watermark**, supplied as a callable so this
module never reaches into the store. When send receives an accepted response and its caller supplies
an observation time (seen_at is not None), it records the watermark, state and that time in
<git-common-dir>/veldo/control/last_seen.json, beside the clone's enrollment binding. The path is
computed by seen_path from the clone's Git common directory, not from the authority store path.
inspect passes its now argument as seen_at; a call without an observation time does not update
the record. Refused responses are not recorded.

A mutating call against a stopped authority refuses as **`authority_unavailable`** and names the
service it could not reach and the watermark it was last sure of. "Routing failed" cannot be acted
on; an operator needs to know which authority to look at and how far behind the world may have moved.

`inspect()` answers **live if it can and explicitly stale if it cannot**. Refusing to answer a
question about the past helps nobody. Answering it without saying the answer is old is the failure, so
every answer carries `stale`, and a stale one carries the watermark, the moment, the last state and
why. There is no shape in which a caller gets state and has to guess how fresh it is.

The requirement is that nothing auto-starts the authority: starting it is an operator's act.
Across every client this is INTENDED and NOT YET DEMONSTRATED. Suite 49 checks only the expected
address in /proc/net/unix after calls; it does not observe process creation.

## One sentence I had to correct in my own comment

The first draft said the record is "read-only by construction" and that `send` never touches it. That
is false: `send` does read it, in one place, inside the `authority_unavailable` branch, to put the
watermark in the refusal. It is read to **describe** a failure and never to decide one.

A source-level claim that `send` never touches the record would have been easier to check and would
have been a lie, so it is not the claim. The claim is behavioural and the row asserts it that way:
with the authority down and a full record on disk, a mutating call still refuses, does not return the
recorded state, does not report success, and writes nothing.

## How "nothing appeared" is asked, because two obvious ways are wrong

Both were measured, both passed for the wrong reason first.

Comparing the whole directory listing before and after measures the **shutdown**, not the refusal:
the socket file disappears with the authority, so the directory shrinks. The row asks for **new files
only**.

The address-specific observation reads /proc/net/unix and compares its pathname column to the
one expected address. The AC3 mutant binds and listens there in the existing client process;
it starts no process. Waiting for the fixture child confirms that particular child's exit.
Neither measurement is a process census or detects a new process on another address, or a
short-lived process that exits before inspection. Direct process-creation observation is needed
before the wider no-auto-start requirement can be described as demonstrated.

## What the evidence is

Five rows in `scripts/suites/49_veldo_0109_unavailable.py`, against a real authority child process on
a real AF_UNIX socket. Generic control_client.send upserts are tested after graceful stop and,
in unavailable/sigkill-refuses-generic-client, after SIGKILL leaves an actual dead socket inode.
That new row checks the refusal's service and last watermark, unchanged state-directory snapshots,
the child's -9 exit status, and absence of a binding at the expected socket address.
The dead-socket-success production mutant returns success for that dead socket and fails the row.

The registered claim, command and dispatch-admission client matrix, and relay killed while the
authority lives, are INTENDED and NOT YET DEMONSTRATED. They require fleet client and relay lifecycle
fixtures beyond this generic-client suite.

| falsifier | mutation | result |
|---|---|---|
| AC1 | `send` falls back to the recorded state and reports the command applied locally | the mutation "succeeds", which is the second authority |
| AC2 | `inspect` returns the recorded state with `stale` false | old state that looks current |
| AC3 | the client binds the address itself when it cannot connect | a listener appears, which the kernel's table shows |

AC3 uses a missing endpoint and a plain file at the socket path; the added SIGKILL row separately
exercises a real dead socket inode. The existing fourth row is the negative
control, comparing a no-op copy against the original's answers in the same run rather than against
literals.

## What this is not

Recovery, replay and reconciliation after the authority returns are later items under R26. This item
covers only the window in which it is gone. And the watermark here is whatever the authority reports;
that it is monotonic and survives a restart is the store's property, not this module's, and is not
claimed.
