# VELDO-0108 proof

PLAN-0019 W85, revision 2. Author: Ava (Claude), under Dmitry's rule that when Codex is out the
author writes and Codex validates. Codex validates this item in the batch of 2026-09-22.

**NOT A CLAIM YET.** The specification is DRAFT, so by the methodology's own ready boundary this
bundle is held as `manifest.draft.json` and is not a proof: a specification must be READY before it
is built and proven, and `.veldo/policy_check.py` refuses a tree where a draft spec carries a
`manifest.json`. The work is real; the claim would be premature.

## What landed

`.veldo/control_relay.py`, mirrored byte for byte into `engine/.veldo/`. The program sshd runs on the
authority's machine. It reads one request from its standard input, writes those bytes unchanged to
the local IPC endpoint, and writes the endpoint's answer unchanged to its standard output. That is
the whole of it.

## Why it does so little on purpose

The temptation is the convenient one: the relay has already watched SSH authenticate somebody, so
let it decide. SSH says **who is carrying** the command. The command's own signature says **who
authored it** and what it may do. Collapsing those two makes every host with relay access an
authority.

So this program never parses the payload, never verifies a signature, never reads the enrollment
binding, and never consults the principal SSH authenticated. It cannot make an authorisation
decision because it does not hold the material for one.

The endpoint is an **argument**, given once by whoever installed it beside an authority. A relay that
chose its target from the request would move the routing decision out of the signed binding, at the
one point in the system where the binding is not being read.

Source inspection checks that the relay contains no bind/listen calls. Separately, AC3 compares
pathname Unix sockets under the fixture directory in /proc/net/unix before invocation and after
the relay exits. No additional fixture-local Unix socket remains afterward. These snapshots are
not a process census or a general listener proof: they miss transient listeners, abstract Unix
sockets, paths outside the fixture, and other protocols. The wider no-listener requirement and
host process census are INTENDED and NOT YET DEMONSTRATED; they need kernel-level lifecycle
observation.

## What the evidence is

Eight rows in `scripts/suites/48_veldo_0108_relay.py`. The relay runs as a real child process with the
request on stdin, against real authority child processes on real sockets. A valid command arrives
unchanged and is accepted. A command tampered with in transit and one signed by a key the authority
does not know are both refused **at the authority**. With the authority stopped,
`relay/an-unreachable-authority-is-reported-not-answered` requires exit 3, raw stdout equal
to `b""`, and the endpoint named on stderr.
Suite 48 also requires exactly zero stdout bytes in `relay/usage-has-zero-stdout`,
`relay/oversized-request-has-zero-stdout`, and `relay/oversized-response-has-zero-stdout`.
`python3 scripts/check_teeth_mutations.py --finding 2` injects `null`, one newline, and one
space into each of these four paths in temporary relay copies; each fails its named assertion.
It also drives `{}` on the unavailable path. The successful empty echo remains a raw-byte
comparison in `relay/the-authority-judges-not-the-relay`.

The carrying promise is measured separately against a bare echo socket, byte for byte, on a NUL byte,
text that is not valid UTF-8, half a megabyte and an empty payload, because a relay that quietly
re-encodes what it carries breaks signatures for reasons nobody can find.

| falsifier | mutation | result |
|---|---|---|
| AC1 | the relay forwards but replaces the authority's answer with its own | AC1 red, and AC2 and AC3 with it |
| AC1 carrying | `forward()` re-encodes through a lossy utf-8 round trip | AC1 red, four rows pass |
| AC2 | the relay accepts whenever a principal is in the environment | AC2 red, four rows pass |
| AC3 | the endpoint taken from `VELDO_CONTROL_SOCKET` | AC3 red, and AC2 with it |

The couplings are recorded as couplings rather than hidden. A relay that answers for the authority
genuinely does make an unsigned command look accepted and genuinely does make the relayed answer
differ from the local one; and AC2's claim includes that the relay reads no environment variable, so
the mutation that makes it read one belongs to AC2 as well. The first mutation was deliberately
sharpened from "never connect" to "replace the answer" for the same reason: a mutant that breaks the
whole fixture reds every row and proves nothing about any one of them.

## Stood down by name

There is **no SSH server on this machine**, so the leg where sshd authenticates the remote principal
and refuses an unknown one is NOT exercised. That leg is sshd's, not this program's. What is
exercised is every decision this program makes, and the thing that matters about the boundary: the
relay is given SSH's own environment, including a principal, and it changes nothing about the answer,
because the relay never reads it and the authority never sees it. A correctly signed command with no
SSH environment at all is accepted, which is the mirror: the signature authorises and SSH's presence
is neither sufficient nor required for it.

## What the drive found in the suite rather than the code

Three faults, all recorded in `driven.json` under their own heading, because the useful record is not
that the rows pass but what had to be fixed before passing meant anything. The echo helper waited on
`accept()` with no timeout, so a mutant hung the gate instead of reddening a row. AC3 indexed the
applied log at `[-2]` without checking its length, so a mutant killed the run mid-suite. And the
negative control asserted a literal refusal reason, so it reddened under mutations instead of proving
only that copying is neutral.
