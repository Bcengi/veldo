---
schema: veldo.spec/v1
id: WARP-1310
title: 898 pattern findings collapse to 18 lines and every one is a fixture - so a disposition
  covers ONE line by digest, never a path, and entropy does not gate at 20 noise hits per real one
status: shipped
risk: high - this decides what a repository's secret posture IS and, once flipped, whether work can
  land at all. Getting the triage wrong in the permissive direction hides a real credential; getting
  it wrong in the strict direction gets the gate switched off, which is the same outcome slower.
owner: dmitry
human_approval: not_required
lane: planned
plan: PLAN-0013
work: W10
depends_on: [WARP-1301, WARP-1302]
placement: [enforcement, runners]
footprint:
  - ".veldo/secret_inventory.py"
  - "engine/.veldo/secret_inventory.py"
  - "scripts/secret_inventory.py"
  - "engine/scripts/secret_inventory.py"
  - ".veldo/secret_inventory.json"
  - ".veldo/capabilities.yaml"
  - "engine/.veldo/capabilities.yaml"
  - "scripts/suites/01_warp_0101_reviewer_notes.py"
  - "specs/WARP-1310-honest-migration.md"
  - "specs/index.md"
acceptance_criteria:
  - id: AC1
    text: >
      THE INVENTORY COVERS REACHABLE HISTORY, NOT ONLY THE TREE. A credential committed and then
      deleted is still in every clone, every fork and whatever CI cached the checkout. This
      repository's run scanned 1,248 tracked files AND 3,252 reachable blobs; a history-only finding
      is classified as exposed even when the tree is clean.
  - id: AC2
    text: >
      NO FINDING EVER CARRIES A VALUE. The scanner returns (line, kind, why) and nothing else, so
      there is no matched text to leak even by accident; a finding is identified by a truncated
      digest of its LINE. An inventory that quoted what it found would be a second copy of every
      secret in the repository, in a file people paste into tickets.
  - id: AC3
    text: >
      A DISPOSITION COVERS ONE EXACT LINE BY DIGEST - NEVER A PATH AND NEVER A PATTERN. A path
      allowlist exempts a location forever, so a real credential dropped there later is invisible;
      that is the mechanism WARP-1302 refuses to ship and this does not reintroduce it under another
      name. A selftest mutates a dispositioned line and the disposition stops matching.
  - id: AC4
    text: >
      A MALFORMED DISPOSITION DISPOSITIONS NOTHING. Missing decider, missing date or a token reason
      leaves the finding OUTSTANDING, so an incomplete record fails toward the finding being visible
      rather than away from it.
  - id: AC5
    text: >
      WHICH DETECTOR GATES IS A MEASURED DECISION, NOT AN ASSUMPTION. Over this repository the
      shipped detectors produced 898 pattern hits and 17,849 entropy hits - 20 noise findings per
      real one. Entropy is a proportionate diff-time tripwire; as an inventory gate at that ratio it
      guarantees the gate gets switched off. Pattern gates, entropy reports.
  - id: AC6
    text: >
      THE FLIP IS DECLARED AND DATED, NEVER INFERRED FROM A SCAN (D4). A scan returning empty
      because a path was skipped or a detector broke must not silently arm the gate, and the same
      accident in reverse must not silently disarm it. Declaring enforcing while anything is
      outstanding refuses; a malformed declaration falls back to advisory AND reports its own
      problem.
  - id: AC7
    text: >
      ENFORCING DOES NOT SILENTLY DOWNGRADE. Once a repository declares enforcing, going back to
      advisory without a written reason refuses. The commonest way a security gate dies is somebody
      turning it off during an incident and nobody turning it back on.
  - id: AC8
    text: >
      ROTATION IS SURFACED, NEVER PERFORMED. `rotation_worklist` produces named work for named
      people and this tooling issues nothing and revokes nothing. Findings with no declared owner
      are still raised, addressed to `unassigned`, because an unowned exposed credential is the one
      most worth surfacing. This repository's worklist is empty: no real credential was found.
required_evidence: [unit]
rollback: >
  Delete the module, the runner script and the record. Nothing is wired into scripts/verify.sh yet,
  so no gate behaviour changes either way.
---

## Outcome

This repository knows what is actually in it, by reference, including history - and can flip its
gate to fail-closed on a human's dated decision rather than on an agent's scan.

## What the inventory actually found

1,248 tracked files and 3,252 reachable blobs. 898 pattern findings, 17,849 entropy findings.

The 898 collapse to **eighteen distinct lines**, and all eighteen are conformance fixtures: AWS's
published documentation example key, `sk_live_` followed by the alphabet, a bare PEM header with no
key body, textbook JWTs decoding to `{"sub":"1"}`, `hunter2xyz`. One is not even a fixture - it is a
reviewer's note quoting the fixture file name.

There are no real credentials in this repository, in the tree or in reachable history. The rotation
worklist is empty for the only reason that counts: nothing was exposed.

## Why a per-digest disposition is not an allowlist with better manners

WARP-1302 ships no allowlist on purpose, and this must not reintroduce one under another name. The
distinction is what the exemption covers:

A path allowlist exempts a location forever. A real credential committed to that path afterwards is
invisible, and the exemption was granted by somebody who never saw it.

A per-digest disposition covers one byte-identical line. Change the line and it stops matching. A
new secret has a new digest and inherits nothing. The eighteen decisions here are eighteen lines
somebody read, each with a written reason another person can disagree with.

That the 898 collapse to 18 is what makes this practical rather than theoretical. A human can read
eighteen lines. Nobody reads 898.

## Why entropy does not gate

This is a measured call, not a preference. Twenty entropy findings for every pattern finding across
a whole-history sweep. Entropy is a good diff-time tripwire, where the unit is a handful of changed
lines and a false positive costs somebody ten seconds. As an inventory gate it produces a wall
nobody can triage, and a gate nobody can triage is a gate that gets switched off - which catches
strictly less than the advisory report it replaced.

## What still needs a human

The flip to enforcing, and putting the record under `protected_paths`. Both touch protected files.
The dispositions were written by an agent and that is safe precisely because they gate nothing until
someone declares enforcing on a date, with the inventory in hand.
