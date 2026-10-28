# VELDO-0111 round 3, 2026-10-28

REMAINING: full AC2 qualification within the four approved families.
The owner approved the amendments in Telegram 37442, "all 3", answering
Telegram 37440 item 1. The specification records the exact AC4 replacement and
limits AC2 to Unix, IPv4, IPv6 and netlink, each fully qualified. Other families
have named, tested not-qualified reasons and their observation makes capture
INCOMPLETE. Only obligations removed by that narrowing were removed.

## Red and green evidence

* spec-red.json rejects the original acceptance text. spec-green.json verifies
  exactly the two approved replacements and the dated amendment against
  baseline 5eeb6664. No other acceptance text is altered.
* regressions-red.json records all three new rows false on the original
  collector. regressions-red-suite.diff retains the exact test additions used
  for that run. regressions-green.json extracts the same focused rows from the complete
  suite run after the fixes. suite-green.json.gz retains the live receipts
  and source/suite digests.
* The family boundary records all excluded discovery families, tests every
  family number from 0 through 45 plus future number 65535, and drives every
  available excluded family/type combination on the real kernel. Operation
  fixtures now cover only the four approved families. Protocol, lifetime and
  shared-memory qualification failures within them remain enforced.
* The Unix probe independently acknowledges getsockname before and after two
  sends, with and without SO_PASSCRED. It requires zero sender events when
  unnamed and exactly one event carrying the actual autobind name when bound.
  A separate undecoded netlink case requires implicit_address with no service.
* The source-state check compares assigned states with FAULTS. The new drained
  finalization fault also runs through the existing complete AC4 matrix, which
  checks capture status separately from qualification and validates all eleven
  named consumer stand-downs.

falsifiers.py retains a diff for each scratch mutation, requires its named row
false in a completed run, then runs a fresh original-source green control:

| Falsifier | Required red row | Green control |
| --- | --- | --- |
| phantom-unix | census/unix-binding-is-real | phantom-unix-green.json |
| drop-autobind | census/unix-binding-is-real | drop-autobind-green.json |
| other-family-service | census/unix-binding-is-real | other-family-service-green.json |
| silence-family | census/family-qualification-boundary | silence-family-green.json |
| uncovered-state | census/fault-state-coverage | uncovered-state-green.json |

Each corresponding red JSON and compressed receipt is retained. Crashes, absent
rows and exceptions do not count as detections. All five retained mutants turned their named rows red and all five original
controls turned them green. The complete ticket run passed 13 of 13 rows in
suite-green.json and suite-green.json.gz. acceptance.json separately records
that the local regressions pass while AC2 remains unfulfilled. The suite does
not turn qualification failures into a COMPLETE host receipt.

## Remaining work

See [OPEN.md](../OPEN.md) for protocol bounds, IPv6 protocol 115 configuration,
asynchronous socket effects, final socket destruction, shared-memory races,
other implicit addresses and compat message decoding. These remain within the
approved families and cannot be waived by this amendment. No real-host receipt
is claimed COMPLETE. The AC4 integration cycle is resolved by the approved
amendment; downstream suites still owe end-to-end propagation evidence.

Only this ticket's suite and falsifiers were run. The single suite-file run
and the small spec green check used the single-file exception in owner rule
37191. The multi-run falsifier driver and the initial red checks used blocking
flock on /home/dmitry/.local/state/core-gates/.gate.lock. Three duplicate queued
green checks were canceled before execution when the host lock was occupied
by a separate gate. No aggregate gate, detached process, push or merge was used.
