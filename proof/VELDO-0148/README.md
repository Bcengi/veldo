# VELDO-0148 proof

A land refused because another factory moved main ends its original dispatch. The installed
factory service offers a new land dispatch, with a new watermark, merge, candidate gate and
compare-and-swap. A conflict returns to the builder and then review. A lost lease is refused
only when the fetched destination tip does not contain the candidate; containment stays unknown.
A required approval is bound to the candidate tree, so a re-merged tree needs a fresh grant.

Suite: `scripts/suites/86_veldo_0148_re_land.py`, registered with its own prerequisite closure.
It drives real Git repositories and a disposable bare remote, the SQLite store and signed
production writers, build and review child processes, the floor and proof services, the lander,
installed candidate gate, effect executor and publication receipts. The authority service runs
from its installed executable. Another local clone moves the remote before listing or in the
publication clone's pre-push hook. Engine output comes from a generated fake; no real model,
login, external service or real credential is used. Each row reports once.

## Criterion rows

| Criterion | Row | What it proves |
|---|---|---|
| AC1 | `install/land-station` | The installation and scaffold include the land station and its production dependencies; malformed station configuration is refused by name; engine copies match and service passes have wake sources. |
| AC1 | `reland/stale-subject` | A stale-subject refusal ends the original dispatch without another attempt under it. Exactly one new dispatch follows, takes the new watermark, re-merges unchanged build evidence, re-gates and lands with its own receipt. Status counts dispatches and refusals. |
| AC1 | `reland/review-kept` | A clean re-merge retains the review of the unchanged evidence commit and the existing floor record, without another build or review. |
| AC1 | `reland/conflict-rebuild` | A real merge conflict publishes nothing, names the conflicting path and offers one new build instructed to merge the new main, followed by that build's review. |
| AC1 | `reland/never-forced` | Every recorded remote update is a fast-forward and every publication uses the exact watermark of its own land as its lease. |
| AC2 | `lease/trunk-moved` | A push between listing and publication loses the lease; the executor fetches the moved tip, refuses as trunk-moved and the service re-lands under a new dispatch. |
| AC2 | `lease/contains-unknown` | A moved tip containing the candidate remains unknown, judged at the push URL; its named stop leaves no receipt, retry or re-land. |
| AC3 | `grant/fresh-request` | The old tree's grant is refused by name for the re-merged tree without publishing. One owner request survives repeated passes; answering creates an exact-tree grant and the next dispatch lands that tree. |

The control row `format/fake-lines` checks each scripted engine event against the captured binary
format. The separate VELDO-0172 row `fake/capture:0148_re_land` drives the installed fake through
the shared conformance checker.

## Red record

[red-at-ad916989.json](red-at-ad916989.json) records the current suite against an unchanged
archive of `ad91698948dd1d894c0f6af4702b8a4b93c9694e`, before this concern. All eight behavior
rows fail by assertion; `format/fake-lines` stays green. No exception counts as evidence.
[drive.py](drive.py) owns this replay and records the commit, module digests, row results and
detailed assertion failures. This is the previous builder's saved red run.

## Mutations

[mutations.json](mutations.json) records a green baseline, four green no-op module copies and
12 finding-148 mutants, all rejected on their named rows by assertion. Each record includes
source and mutant digests, the exact applied diff and its failure details. A static audit after
merging local main at `9f1a0445` found all records present, all registered replacements and diffs
identical, all digests current, and no duplicate mutation names anywhere in the registry.
The mutation executions are the previous builder's saved evidence; the completion run did not
rerun the mutation checker. Independent replay belongs to the reviewer.

| Mutation | Named row |
|---|---|
| `reland148-stale-left-failed` (AC1 falsifier) | `reland/stale-subject` |
| `lease148-loss-unknown` (AC2 falsifier) | `lease/trunk-moved` |
| `grant148-old-tree-accepted` (AC3 falsifier) | `grant/fresh-request` |
| `reland148-loop-offers-nothing` | `reland/stale-subject` |
| `reland148-conflict-relanded` | `reland/conflict-rebuild` |
| `reland148-rebuild-not-reviewed` | `reland/conflict-rebuild` |
| `reland148-landed-rebuilt` | `reland/review-kept` |
| `reland148-end-wakes-nothing` | `reland/conflict-rebuild` |
| `lease148-contained-refused` | `lease/contains-unknown` |
| `lease148-tip-not-fetched` | `lease/trunk-moved` |
| `never148-forced-push` | `reland/never-forced` |
| `grant148-asked-every-pass` | `grant/fresh-request` |

## Replay

Run the suite with `python3 scripts/selftest.py --suite 86_veldo_0148_re_land`.
Replay the red record with `python3 -B proof/VELDO-0148/drive.py --red ad916989`.
For reviewer use, `python3 -B proof/VELDO-0148/drive.py` regenerates the mutation evidence and
diffs with at most two workers; `python3 scripts/check_teeth_mutations.py --finding 148 --jobs 2`
independently checks the registered mutants. These mutation commands are not part of the
builder's permitted completion run.

The completion run also exercises the proof, floor, candidates and gate output suites separately.
Its final results and footprint, anchor and validation checks are recorded in the specification's
History. Engine production copies are byte-identical to their repository counterparts.

## Completion checks

These are partial suite results on the merged tree, not a full gate verdict. Each final run was
serial; candidates and gate output were repeated separately after their first runs accidentally
overlapped. All reported zero failures; subset mode intentionally exits 2.

| Suite | Context | Passing suite rows |
|---|---|---|
| `86_veldo_0148_re_land` | ordinary environment | 10 |
| `86_veldo_0148_re_land` | gate environment | 10 |
| `64_veldo_0050_proof` | proof | 14 |
| `63_veldo_0049_floor` | floor | 20 |
| `67_veldo_0056_candidates` | candidates | 11 |
| `69_veldo_0058_gate_output` | gate output | 16 |
| `58_veldo_0028_effects` | effect executor | 51 |
| `70_veldo_0057_landing` | landing | 31 |
| `83_veldo_0154_factory_loop` | factory loop | 13 |

The gate-environment run used an empty environment, PATH `/usr/bin:/usr/bin:/bin`, a generated
HOME under `/dev/shm`, TMPDIR `/dev/shm`, `C.UTF-8` language and locale, UTC, disabled Python
bytecode and user site, hash seed 0, disabled system Git configuration, global Git configuration
`/dev/null`, and disabled terminal prompting, exactly as requested.

The supplied footprint check reports 37 changed paths and none outside VELDO-0148. The supplied
anchor check reports 0 bad anchors and no duplicate mutation names. `python3 .veldo/validate.py all`
passes; the diff has no whitespace errors. All eight changed production modules match their engine
copies. The full gate and mutation checker were left to the independent reviewer as directed.
