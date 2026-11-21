# AC2 qualification attempt, 2026-11-21

Base: `805c30828a9ac92722580224c51fc5a48a856483`, branch
`veldo-0111-complete`. This attempt stops on `socket_destruction`, as requested
when a retained obligation cannot be met. It does not qualify AC2 or remove any
retained obligation. The receipt remains **INCOMPLETE**.

## Results

Both the standalone witness and the recheck completed with exit 0 through the
owner's external `host_heavy.sh`. The recheck's initial and final controls each
passed all 13 suite rows. All 18 distinct mutations were detected: four
acceptance mutations, five round-3 mutations, three swallowed faults,
CLONE_UNTRACED, and five current named qualification gaps. There are 19 completed
red drives because socket-destruction suppression is checked both by evidence
replay and by the live all-family external-reference witness. Focused controls
and reason-replay controls are green. These are regression results, not full
AC2 acceptance.

`receipt.json` retains eight fault receipts, each with all eleven exact named
consumer stand-downs. `socket-destruction.txt` records all four live family
counterexamples. The top-level `qualification.json` now points to this attempt
and its receipt digest instead of the historical protocol-zero discovery.
`validation.txt` records the final proof-integrity and personal-setup checks.
The staged whitespace check rejected space-only context lines in `AC2.diff`
and `silence-family.diff`. Those two retained patches were rendered with zero
context after the run; both resulting mutant digests were checked against the
live-run receipt. The mutations are unchanged. A fresh recheck emits the original
contextual diffs, so retain this formatting step when staging its output.

## Counterexample and observation boundary

`socket_destruction.py` creates a Unix datagram receiver outside the measured
scope before arming. For each of Unix, IPv4, IPv6 and netlink, a traced root
creates a service socket, binds it (and listens where applicable), queues its
descriptor to that receiver with SCM_RIGHTS, closes its descriptors and exits.
The receiver does nothing until `census()` returns with all descendants drained.

After that return, the harness connects and sends to the listener, or unicasts
to the netlink receive binding, while its only reference is still queued. It
then receives the descriptor, checks its inode and address, accepts/receives the
payload through it, and closes it. The trace records the service and local
close, but its `closed={barrier: descendants_drained, exact: false}` cannot be
an upper bound on lifetime: the socket is demonstrably alive after that barrier.
The qualifier's existing explanation that terminal drain bounds destruction is
therefore also refuted. No implementation change conceals this result.

Every ordering comes from socket operations, terminal waits and census return.
The monotonic timestamps document those events; no elapsed duration decides a
pass. Socket timeouts are 120-second hang detectors. The harness's release
acknowledgement is not claimed as an exact kernel destruction timestamp.

This is a mechanism limitation, not merely an omitted close decoder:

* [SCM_RIGHTS](https://www.man7.org/linux/man-pages/man7/unix.7.html) transfers a
  reference to an open file description. The last traced descriptor can close
  while a queue or unrelated process retains that reference.
* [ptrace](https://man7.org/linux/man-pages/man2/ptrace.2.html) observes attached
  tasks. The external holder is neither a traced descendant nor automatically
  attached by descriptor transfer. Its eventual close has no syscall stop in
  this collector, and it may retain the reference beyond any finite drain.
* [sock_diag's published destruction groups](https://github.com/torvalds/linux/blob/master/include/uapi/linux/sock_diag.h)
  cover IPv4/IPv6 TCP/UDP, not every Unix/netlink socket. The receipt records the
  locally installed UAPI group names and the actual subscription result.
  A diagnostic dump or disappearance from `/proc` is a snapshot, not the required
  final-reference destruction event.

The receipt also records effective/permitted capabilities and host BPF/perf
restrictions: both capability masks are zero, `unprivileged_bpf_disabled=2`,
`perf_event_paranoid=4`, and seccomp mode is zero. Subscription to all four
published sock_diag destruction groups succeeds; those groups still do not
cover Unix or netlink. Ptrace itself works in these direct runs. The lifetime
blocker is therefore separate from the mutation driver's confinement issue.
No privilege changes, host monitoring daemon, or tracing of
unrelated holders was attempted. Completing this retained obligation requires a
qualified source of final-reference events across the four families and holders
outside the descendant scope. The selected child-ptrace mechanism plus permitted
snapshot enrichment does not provide it. Waiting longer, labelling drain as
destruction, excluding external references, or retaining an observer-owned
duplicate would not satisfy the existing obligation.

## Reproduction and receipt

Run from the worktree, using the owner's external `host_heavy.sh` as the command
wrapper (the wrapper's personal installation path is deliberately not stored):

```
host_heavy.sh python3 -B proof/VELDO-0111/ac2-attempt/recheck.py
```

`recheck.py` uses the existing suite and original mutation definitions. It
retains actual applied diffs, named boolean outcomes, source digests, the eight
fault receipts with all eleven named consumer rows, and the compact live
counterexample. A missing row, failed baseline, exception or timeout invalidates
the drive. Mutants live only in temporary files; the worktree collector is never
replaced. `receipt.json` is the structured proof; runtime logs are `.txt`.
Full-suite mutants share a fresh full-suite baseline and final control; each
still runs the entire suite against its mutated collector. Focused round-3
mutants have their own focused controls. This avoids repeating identical
unchanged-source full-suite controls between scratch-only mutations.

The replay includes the four acceptance falsifiers, five round-3 falsifiers,
three swallowed-fault falsifiers, the CLONE_UNTRACED falsifier and each named gap
present in the fresh host inventory. Named-gap replays use that live evidence,
instead of the old round-2 reason driver's hard-coded obsolete gap set.
The socket-destruction suppression additionally runs the external-reference
witness live in all four families: removing its reason must turn
`census/external-reference-needs-destruction-observer` false despite the sockets
still being observed alive. That row proves honest incompleteness, not successful
destruction observation.

## Ptrace and mutation-driver execution

Protected path, inspected and unchanged: `scripts/gate_unconfined.json`.
Its current declaration does **not** include `113_veldo_0111_census`. The
declaration digest is recorded in `receipt.json`.

| Falsifiers | Ptrace requirement |
| --- | --- |
| AC1, AC2, AC3, AC4 | Yes: each drives the full live suite. |
| phantom-unix, drop-autobind, other-family-service, silence-family | Yes: each includes a live census. |
| swallow-corrupt, swallow-abi, swallow-loss, clone-untraced | Yes: each drives the full live suite. |
| external-reference socket-destruction suppression | Yes: live queued/external references in all four families. |
| uncovered-state | No in the focused AST-only drive; yes if a driver runs the whole suite. |
| Named qualification-gap evidence replays | No for replay itself; the fresh evidence producer requires ptrace. |

The authority mutation driver must run ptrace-dependent cases with their baseline
and controls in its unconfined leg, selected from the authority's protected
declaration. It runs whole suites, so a row-only declaration cannot route a
whole-suite case. With the current declaration, those suite-113 cases remain
confined and a ptrace-denied baseline is `invalid_baseline`, not a killed
mutation. This attempt uses the requested direct host-wrapper drives; it does
not claim an authority mutation-driver pass or edit the declaration. No candidate
environment variable is a substitute for the authority declaration.

The specification amendment, consumer tickets and production collector remain
unchanged. No broad repository gate or independent review is claimed.
