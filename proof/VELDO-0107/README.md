# VELDO-0107 proof

PLAN-0019 W84, revision 2. Author: Ava (Claude), under Dmitry's rule that when Codex is out the
author writes and Codex validates. Codex validates this item in the batch of 2026-09-22.

## What this item is for

VELDO-0029 decides which authority a workspace belongs to. This item is how a process in that
workspace reaches it, and it is a separate item because the same defect exists at the other end of
the wire. A serving process has its own current directory and its own module location, and neither of
them is the caller's. If the authority works out which repository a request is about from where IT is
standing, the coordinate travelling in the request buys nothing.

## What landed

`.veldo/control_client.py`, mirrored byte for byte into `engine/.veldo/`. A client side that reads
the binding of the workspace it is GIVEN, derives the address from that binding, and sends a request
carrying the coordinate. An authority side that serves exactly one store and judges every request
against that store.

**The signature covers the coordinates, not just the command.** If only the command were signed, a
valid command could be re-addressed to another workspace in flight and still verify: a
wrong-repository write arriving with a good signature on it. The signed bytes are the command
together with the workspace, the domain and the store it names.

**The address follows the record.** It is derived from the store path the binding carries, so there is
no second place to look. The module reads no environment variable at all.

## The attack, and why the resolve is the thing that stops it

A request can name workspace B while declaring A's domain and store uuids, and be correctly signed.
Checking the declared uuids against the ones this authority serves does not catch it, because the
declared uuids are A's. Only resolving **B's own binding** does: it resolves to B's store, which is
not this authority's store, and the request is refused as `coordinate_not_served`.

The row runs that forgery through a real socket to a real authority process. It is refused and
nothing is applied. With the authority mutated to take the store from itself instead of resolving the
request's workspace, the same forgery is accepted.

## The two checks, and why they stay separate

The **transport** check asks who is connected, and the answer comes from the kernel through
`SO_PEERCRED`, which a client cannot claim. Same account by design, so the rule is that the peer's
uid is the authority's own. The socket is `0600` inside a `0700` directory, which is belt beside those
braces: a mode says who may open the file, `SO_PEERCRED` says who actually did.

The **command** check asks who authored the request and whether it is intact, through a verification
callable, so this module never holds key material.

A peer the kernel vouches for is a process on this machine, not an author. A perfect signature
carried by an unauthenticated peer is something somebody picked up. Collapsing the two would make
every process on the box an authority, and the refusals are separate names so a reader can tell which
one fired. A uid the platform will not report is refused as `peer_identity_unavailable` rather than
allowed, because a check that is unavailable must not become a check that succeeded.

## What the evidence is, and what it is HONESTLY not

Four rows in `scripts/suites/47_veldo_0107_ipc.py`, against two authorities running as **real child
processes on real AF_UNIX sockets**, two real enrolled git clones, and the applied log of each store
compared after every call so a write to the wrong one is visible rather than merely unasserted.

| falsifier | mutation | result |
|---|---|---|
| AC1 | the authority takes the store from itself instead of resolving the request's workspace | the forgery is accepted |
| AC2 | the peer uid comparison removed | a foreign uid is accepted |
| AC3 | the address preferred from an environment variable | the client reaches the other authority |

The fourth row is the negative control.

**The honest limit.** A connection from a genuinely different OS account is NOT tested, and cannot be
here: this design has one account on purpose, and inventing a second would need the OS boundary the
design deliberately refuses. The claim is split in two and the row says so. Over a real socket the
suite asserts that the uid the module uses is the one the kernel reports and not anything the request
said. The rule about a foreign uid is asserted by handing the real judging code a uid the kernel would
report for another account. Neither half is the whole claim.

**And the signer is a fixture.** An HMAC the suite supplies, because the module takes signing and
verification as callables and holds no key material. The rows turn on the signature being checked and
on what it covers, not on how strong it is. Key lifecycle is VELDO-0027.

**Still not wired, and less was wired than I first wrote.** `control_db_path` had NO CALLERS: every
place that opens the store already passes an explicit path, so nothing in the repository was reaching
a database chosen by the caller's position. It is now closed and derives nothing. This item builds the
road;
pointing the existing callers down it is the last step of this group, and it is deliberately not
folded in here, because a change that both introduces a transport and re-points every caller is two
items again.
