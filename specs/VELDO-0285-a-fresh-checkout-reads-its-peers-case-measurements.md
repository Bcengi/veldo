---
schema: veldo.spec/v1
id: VELDO-0285
title: A case this checkout has never measured takes its worker deadline from the same inputs measured by another checkout of this repository
status: ready
risk: high
owner: dmitry
human_approval: not_required
lane: standalone
depends_on: [VELDO-0215]
placement: [enforcement]
protected_paths: ["scripts/check_gate_mutations.py", "engine/scripts/check_gate_mutations.py"]
footprint:
  - scripts/check_gate_mutations.py
  - engine/scripts/check_gate_mutations.py
  - scripts/suites/112_veldo_0215_case_deadlines.py
  - scripts/check_teeth_mutations.py
  - specs/VELDO-0285-a-fresh-checkout-reads-its-peers-case-measurements.md
  - specs/index.md
  - proof/VELDO-0285/**
behavior_bearing: true
observability:
  logs: Unchanged. The receipt's case_deadlines keeps naming each case's enforced deadline, whichever checkout's sample it came from.
  metrics: Unchanged. The store and its records are the same; nothing new is written.
  traces: A peer record is used only when its file name is the key computed for the peer's own path from this checkout's case definition, sources and leg declaration, and its authority field names that same path.
  error_taxonomy: Unchanged. An unreadable record, a gone checkout or a checkout of another repository is skipped, and a case nobody has measured keeps the 120-second floor.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: a case with no live sample under this checkout takes its worker deadline from the
      samples recorded for the same case inputs (definition, direct sources, execution machinery,
      leg declaration) by any other checkout of this repository on this host, with the same
      min(1800, max(120, 3 x seconds)) and 30-day window. Set: a scratch store holding a 130-second
      sample under the key for another checkout's path and none under this one.
      Completeness: case-deadlines/peer-sample drives case_deadlines, the function the stage calls,
      and requires 390 seconds there, while the own-only reader still gives 120 on the same store.
    falsified_by: >
      Restore the same-authority-only read. Registered mutant deadline285-own-authority-only
      (the stage reads no peer authorities) must turn case-deadlines/peer-sample red.
  - id: AC2
    text: >
      Claim: the peer read changes nothing else. A live sample of this checkout's own wins over any
      peer's; a case whose inputs nobody recorded keeps the 120-second floor; a checkout of another
      repository (a different Git common directory) and a gone checkout are not peers; expired
      samples, samples at or under 40 seconds and samples over the ceiling bound as VELDO-0215 does;
      a record whose authority field does not name the path its key was computed for is ignored.
      Completeness: case-deadlines/peer-bounds requires each of these eight cases on its own store.
    falsified_by: >
      Accept any authority in the store regardless of repository. Registered mutant
      deadline285-any-repository must turn case-deadlines/peer-bounds red.
  - id: AC3
    text: >
      Claim: reading peers writes nothing. Records stay written only by the authority CLI after a
      passing fresh, input-stable stage (VELDO-0215 AC3), under this checkout's own authority and
      key; a peer's record is never copied, renewed or rewritten, and once this checkout records its
      own sample that sample decides. Completeness: case-deadlines/peer-read-only compares the
      store's names, bytes and modification times before and after the read, then records an own
      sample and requires the peer file untouched and the own sample to decide.
    falsified_by: >
      Adopt the peer sample as this checkout's own during the read. Registered mutant
      deadline285-peer-adopted must turn case-deadlines/peer-read-only red. The VELDO-0215 rows
      case-deadlines/authority-recording and candidate-authority keep guarding who writes.
required_evidence: [unit]
rollback: Revert both coordinator copies, the suite rows and the three registered mutants; a fresh checkout returns to the floor for every case it has not measured itself.
---

## Intent

Status ready by the lead: test machinery is the lead's call under owner decision 39708.

Two canonical gates of a fresh worktree (landing-b, at 30befb53 and e1c60829) stopped the mutation
stage with mutation_budget_exceeded, 0 of 2851 executed, because one confined baseline ran past
the 120-second floor its case gets when this checkout has no sample. Other checkouts of the same
repository on the same host had measured the same cases at 115 to 150 seconds. The first gate of
every fresh checkout is therefore a draw against host load: a flaky gate, not a defect in the code
under test.

## Findings this spec rests on

- The record key, case_time_key, is a digest of the authority checkout's path, the full case
  definition, the content of the target module, suite, shared harness and execution machinery,
  the case's leg and the whole leg declaration. Because the path is inside the digest, no two
  checkouts ever share a key, so "the same key under another authority" cannot exist; the same
  inputs have one key per checkout. This spec reads a peer's record by recomputing the key for
  the peer's path from this checkout's inputs.
- The authority restriction came in with VELDO-0215 (26585cad). Its stated purposes are
  invalidation (a changed input must not inherit a time) and store hygiene (VELDO-0214 pruning of
  gone checkouts). No trust argument rests on it: the authority field is a path the writer states,
  every checkout's writer runs as the same user, and a key match already proves the peer ran the
  byte-identical coordinator, case and sources. A peer sample can only raise a deadline within
  [120, 1800]; it changes no verdict, and an expired worker stays mutation_budget_exceeded.
- For the delivery case of suite 87 in landing-b, the store holds a 150-second peak under
  veldo-0261 for the same case identity. Its inputs differ from landing-b's in the authority and
  in the leg declaration (landing-b adds two suites to scripts/gate_unconfined.json), so this
  spec alone would not have reached that sample. Changing the coordinator also rekeys every case,
  so the benefit begins once a peer at the same coordinator bytes has recorded.

## Design

case_time_key and case_samples take an optional authority (default ROOT). case_deadline takes
optional peers, (authority, key) pairs, read only when the own key has no live sample.
case_deadlines, which the stage now calls, scans the store once for authority paths other than
ROOT whose Git common directory equals this checkout's (peer_authorities) and computes peer keys
only for cases without an own sample. Writers, pruning, resource claims and the store layout are
unchanged. Measured on the host store (about 30,900 records, 29 peer checkouts, 2851 cases with no
own sample): the read takes about 10 seconds.
