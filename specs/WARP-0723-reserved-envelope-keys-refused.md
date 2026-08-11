---
schema: veldo.spec/v1
id: WARP-0723
title: One documented flag permanently reds the gate - the event CLI lets a caller overwrite the envelope
  fields the validator requires, in a log nothing may rewrite, so the reserved keys must be refused at the
  same place the projection-owned type already is
status: shipped
risk: high - the fix is small and local, but it sits in .veldo/events.py, which ships to adopters in eight
  byte-identical copies, and the failure mode of getting it wrong is the opposite of the defect: a refusal
  written too broadly would reject the projection's OWN entitled append and stop the review log recording
  verdicts at all. It is high and not critical because no protected path is touched and the guard point
  already exists (the projection-owned type is refused on the assembled line immediately before the
  append), so this widens an existing refusal rather than inventing a mechanism
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: []
placement: [engine]
footprint:
  - ".veldo/events.py"
  - "packs/*/.veldo/events.py"
  - "engine/.veldo/events.py"
  - "scripts/selftest.py"
  - "specs/WARP-0723-reserved-envelope-keys-refused.md"
  - "proof/WARP-0723/**"
protected_paths: []
acceptance_criteria:
  - id: AC1
    text: >
      A CALLER'S VALUE ON ANY OF THE FIVE RESERVED ENVELOPE KEYS IS JUDGED ON THE ASSEMBLED LINE AGAINST THE
      ENVELOPE'S OWN INVARIANTS, and refused unless they admit it, at the same point and by the same mechanism
      that already refuses a projection-owned type: reading the FINAL dict immediately before the bytes are
      appended, never an argument a caller passed separately. The keys are schema, id, type, at and producer.
      THIS IS SHAPE ENFORCEMENT AND NOT NON-SETTABILITY, which the item states rather than blurs: a value the
      invariants DO admit still lands carrying the caller's string. A selftest drives the routes enumerated
      here - the positional argument, the --field flag, a repeated --field so the last value wins, a padded,
      case-variant or `str`-SUBCLASS key, and an in-process extra or override dict - and requires each refused
      with a non-zero exit AND the log BYTE-UNCHANGED, proven by reading the log back rather than by trusting
      the exit code. No completeness over routes is claimed beyond the ones driven.
  - id: AC2
    text: >
      THE PROJECTION'S OWN APPEND STILL LANDS, which is the failure mode of over-refusing and is therefore a
      required control rather than an afterthought. A selftest runs reconcile-verdicts over real committed
      verdict artifacts and asserts the derived events are appended and resolvable exactly as before, and
      that a hand-emitted event of an ALLOWED type with NO reserved key still lands at exit 0. If the
      entitled append cannot be distinguished from a forgery without a caller-supplied string, that is a
      finding to report, not a thing to work around.
  - id: AC3
    text: >
      THE HARM IS REPRODUCED FIRST AND THEN SHOWN CLOSED, on the shipped tree, with no code change and
      documented flags only. MEASURED 2026-07-28 at a328f8e: `python3 .veldo/events.py emit proof.recorded
      --field schema=nope` exits 0, the line LANDS (events.jsonl md5 3cc066fc -> dbb587b7), and thereafter
      `python3 .veldo/validate.py all` exits 1 reporting "line 806: bad or missing schema (want
      veldo.event/v1)" and `./scripts/verify.sh` prints "contracts: FAIL" and GATE: RED. The same holds for
      `--field at=` (emit exit 0, validate exit 1). A selftest asserts the identical invocations now exit
      non-zero and that validate.py and the gate stay green afterwards.
  - id: AC4
    text: >
      THE EIGHT COPIES STAY BYTE-IDENTICAL and the guard is asserted in the copy the gate imports, not only
      in the root, so an adopter running a pack gets the same refusal. The existing drift check already
      proves byte-identity; this criterion requires that the assertion which proves the refusal is driven
      against a copy rather than assuming the root stands for all eight.
required_evidence: [unit, baseline]
rollback: revert the commit; the guard is additive and nothing depends on the CLI being able to set an
  envelope field, which is the whole point of the item.
---

## Intent

`validate.py check_events` requires exactly three things of every line in the event log: `schema` equal to
`veldo.event/v1`, a `type` in the declared vocabulary, and a truthy `at`. WARP-0722 moved ONE of those three
onto the bytes, so a caller can no longer forge the projection-owned `type`. The other two were left
reachable, and the manifest of that item asserted they were harmless payload. **That sentence was measured
false and deleted; this item closes the hole it described.**

The severity comes from the log's own contract rather than from the size of the mistake. The event log is
append-only - nothing in the tool rewrites it - so a single invocation of a documented command puts a line
in it that the validator refuses forever. The gate does not degrade, it stops: `contracts: FAIL`, `GATE:
RED`, on every run, for every item, until someone edits a file the method says must never be edited.

## Context

The guard point already exists. WARP-0722 put the refusal on the assembled dict at the last point before
the append and asserted it by reading back the line that landed, after six rounds of guarding the various
ways a caller could NAME the type. That mechanism is the right one and this item reuses it: the same
predicate, one wider key set. It does not need a new design, and it must not invent one.

## Round 2 (the reviewer's route, closed here)

The independent review found one route round 1 missed, with a worse consequence than a refused value: a `str`
SUBCLASS key in an in-process `extra` dict. It hashes elsewhere, so the dict keeps BOTH entries and every
value lookup reads the genuine one; it overrides only `__eq__`, so the confusable test `alias != key` is
answered by the inherited `str.__ne__` and reads False. The line lands carrying the reserved key TWICE, and
`json.loads` takes the LAST, so `validate.py` exits 1 forever on an append-only log. The close is at the layer
that declares the contract, not in the reader: the key is normalised to the spelling `json.dumps` will write,
taken off `str`'s own data so no overridden method can lie about it, and a reserved name is accepted only from
an EXACT `str`. It needed in-process Python, which already permits appending to the log directly, so this
grants no new capability - what it closes is a way of corrupting the module's own assembled line.

## Out of scope

The `type` key is already refused and is not re-litigated here. The `GIT_DIR`/`GIT_WORK_TREE` redirect that
lets a foreign repository's artifacts be reconciled into this log is a separate item: it needs control of
the process environment, which already permits appending to the log directly, so it grants nothing new. A
writer that never imports the module - a shell append, a hand-edited log - is refusable by nothing inside
the module and belongs to the signed-log question, not here.

## Promotion

PROMOTED TO READY on the owner's instruction, 2026-07-29 07:31 UTC, Telegram: asked whether to "promote the
two new defect specs so they can be built", he answered "2 yes". `human_approval` is not_required for this
item, so his instruction is sufficient and no approval record is owed.
