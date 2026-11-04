# VELDO-0248 proof: the LangGraph runtime moves to langgraph 1.2.19

Built 2026-11-04 on branch agent/claude/veldo-0248 from 67594919 (spec ready, owner approval Telegram 39087).
The full gate was not run here; the lead runs it under the gate lock. Everything below was run.

## Owner stop (AC2): none

No package is new to the reviewed closure, none was removed, no SPDX license changed and every license is
inside the approved set (`.veldo/control_runtime.py` APPROVED_LICENSES). `closure-diff.json`
`owner_approval_needed` is empty, so the build continued. Two items are listed for the owner's information
only; neither is an AC2 stop:

- **License basis only (no approval needed, per AC2):** jsonpatch (registry license "Modified BSD License",
  now license expression BSD-3-Clause) and tenacity ("Apache 2.0", now license expression Apache-2.0). The
  SPDX expression is unchanged for both.
- **langsmith (named exception) publishes from a new repository in the same organization (the old one is archived with the vendor's own "moved" notice):** the
  registry source and the PEP 740 publisher moved from `langchain-ai/langsmith-sdk` (workflow release.yml)
  to `langchain-ai/langsmith-python` (workflow publish-pypi.yml). The owner (github.com/langchain-ai,
  LangChain, United States) is unchanged, so the origin and the approval are carried as they were.

Named exceptions, origin and owner checked against the 1.2.12 records: langgraph-sdk 0.4.12 (source
langchain-ai/langgraph, no attestation, as before), orjson 3.13.0 (ijl/orjson, publisher ijl/orjson
artifact.yaml, as before), xxhash 4.0.2 (ifduyue/python-xxhash, publisher build.yml, as before), langsmith
0.14.17 (above). Each keeps its VELDO-0043 approval at the new version.

## What was regenerated, and how

| Artifact | Tool |
|---|---|
| `.veldo/control_graph_lock.py`, `engine/.veldo/control_graph_lock.py` (byte-identical) | `proof/VELDO-0248/lock.py` |
| `proof/VELDO-0248/dependency-closure.json` (veldo.dependency-closure/v3) | `proof/VELDO-0248/lock.py` |
| `proof/VELDO-0248/closure-diff.json` | `proof/VELDO-0248/lock.py` |
| `engine/runtime/langgraph-records.json`, `.veldo/runtime/langgraph-records.json` (byte-identical) | `proof/VELDO-0045/records.py SCRATCH proof/VELDO-0248/dependency-closure.json` |

No hash was typed by hand. `lock.py` runs `pip install --dry-run --only-binary=:all: --report` for
`langgraph==1.2.19` in a throwaway CPython 3.12.3 venv (pip 24.0, linux x86_64), reads each exact release
and project from PyPI through records.py's own `fetch`, refuses a wheel whose registry sha256 differs from
the resolved one, computes `why_not_latest` from the closure's own requirement specifiers (a pin below its
latest with no capping requirement stops it), carries origin and approval from the VELDO-0043 closure by
exact name, and stops with exit 3, writing only the diff, when a package has no reviewed entry or its SPDX
license changed or falls outside the approved set. A resolution against explicit platform tags
(`--python-version 3.12 --platform manylinux... --implementation cp`) gave the identical 38 rows.

`records.py` gained one optional argument, the reviewed closure; the default stays
`proof/VELDO-0043/dependency-closure.json`, so the VELDO-0045 proof is unchanged. A locked package with no
entry in the closure now stops it by name before anything is downloaded (before, it was a bare KeyError).
Its output: `{"packages": 38, "lock_digest": "fb75e741fdd6f683d486e015e288c4ef840e3c4be1c40a7aea933abdb87eb84e",
"attested": 20, "not_latest": {"pydantic_core": "2.50.3", "uuid_utils": "1.2.0"}}`.

**Reproduce offline.** `registry/` holds every registry read both tools made (`reads.json` lists each
file with the sha256 and size of the body as served; project reads keep only their `info` object, the only
part either tool reads; 24 reads with non-ASCII characters are re-serialized as ASCII JSON with the same
parsed content) and `registry/pip-report.json`, the resolution. Copy `registry/*` (without reads.json) and
the 38 downloaded wheels into an empty scratch directory and run both tools on it: the lock, closure, diff
and both records files came out byte-identical to the committed ones (sha256 checked, 2026-11-04). Without
the wheels, records.py downloads them and checks them against the lock and the registry.

## The closure diff (closure-diff.json)

Root langgraph 1.2.12 to 1.2.19; 38 packages, the same 38 names; added none, removed none; 24 moved.

| Package | 1.2.12 lock | 1.2.19 lock | | Package | 1.2.12 lock | 1.2.19 lock |
|---|---|---|---|---|---|---|
| anyio | 4.15.1 | 4.16.0 | | langsmith | 0.14.0 | 0.14.17 |
| certifi | 2026.7.22 | 2026.10.23 | | orjson | 3.12.0 | 3.13.0 |
| charset-normalizer | 3.5.1 | 3.5.2 | | ormsgpack | 1.12.2 | 1.13.0 |
| httpcore2 | 2.13.1 | 2.16.0 | | pydantic | 2.13.5 | 2.14.2 |
| httpx2 | 2.13.1 | 2.16.0 | | pydantic_core | 2.46.5 | 2.50.2 |
| jsonpatch | 1.33 | 1.42 | | tenacity | 9.1.4 | 9.2.1 |
| jsonpointer | 3.1.1 | 3.8 | | truststore | 0.10.4 | 0.10.5 |
| langchain-core | 1.6.4 | 1.7.5 | | typing-inspection | 0.4.4 | 0.4.5 |
| langchain-protocol | 0.0.19 | 0.0.20 | | uuid_utils | 0.17.1 | 0.19.0 |
| langgraph | 1.2.12 | 1.2.19 | | websockets | 16.1.1 | 17.4 |
| langgraph-checkpoint | 4.2.0 | 4.3.1 | | xxhash | 4.0.1 | 4.0.2 |
| langgraph-prebuilt | 1.1.0 | 1.1.1 | | | | |
| langgraph-sdk | 0.4.5 | 0.4.12 | | | | |

Unchanged (14): annotated-types, distro, h11, httpcore, httpx, idna, packaging, PyYAML, requests,
requests-toolbelt, sniffio, typing_extensions, urllib3, zstandard.

**Where the build day differs from the draft's 2026-11-04 read** (the spec's Context allows this and asks
that it be said):

- **uuid_utils is 0.19.0, not 0.18.0.** 0.19.0 is the newest release below 1.0 and its only linux x86_64
  wheel for CPython 3.12 is `cp310-abi3` (manylinux_2_17), which the lock records. Still capped:
  langsmith 0.14.17 requires `uuid-utils<1.0,>=0.12.0` (latest 1.2.0).
- **pydantic_core is now below its latest.** PyPI serves 2.50.3; pydantic 2.14.2, the latest pydantic,
  requires `pydantic-core==2.50.2`. `why_not_latest` says so.
- websockets 17.4 is the latest, so it is no longer capped, as the draft said.
- Wheel names that changed beyond the version: jsonpatch (`py2.py3` to `py3`), uuid_utils (`cp312-cp312`
  to `cp310-abi3`), pydantic_core (the same tags, listed in a different order). charset-normalizer and
  websockets keep the cp312 manylinux wheel, as before.

## AC1: met

- Lock: root `langgraph==1.2.19` (still the latest 1.2.x on PyPI on 2026-11-04, uploaded 2026-10-30; no
  newer stable release), RESOLVED 2026-11-04, 38 rows, both copies byte-identical, digest
  `fb75e741fdd6f683d486e015e288c4ef840e3c4be1c40a7aea933abdb87eb84e`. Every pin is the latest its closure
  allows; the two below latest carry `why_not_latest` (above).
- Records: regenerated by records.py with the new closure, bound to the new lock digest, both copies
  byte-identical, read 2026-11-04; each wheel downloaded, checked against the lock and the registry sha256
  and every member against its RECORD.
- Runtime: `python3 .veldo/control_runtime.py install` built
  `~/.local/share/veldo/langgraph/fb75e741.../` with `pip --require-hashes --no-deps --only-binary=:all:`;
  activation `accepted` with no problem; qualification passed, every answer labelled
  `{"name": "langgraph", "version": "1.2.19"}`. The 1.2.12 runtime directory (b45d1e37...) is left in
  place, as the rollback says.

## Falsifiers (falsify.py, output falsifiers.jsonl): 12 of 12 red as named, control accepted

`TOOL/bin/python -I -B proof/VELDO-0248/falsify.py SCRATCH WHEELS` runs every case on scratch copies (a
copy of `.veldo`, a minimal records.py tree, a copy of the runtime under a scratch home); the repository's
own files are never touched and no case needs the network.

| AC | Case | Observed |
|---|---|---|
| AC1 | one lock sha256 changed (annotated-types) | records.py stops: AssertionError naming annotated-types; activation refuses with `hash_mismatch:annotated-types` (with records_stale and runtime_absent, since the digest moved) |
| AC1 | one member of the langgraph wheel changed in the scratch download | records.py stops: AssertionError naming langgraph (the wheel sha256 no longer equals the lock) |
| AC1 | an installed langgraph file changed in a runtime copy | activation refuses `file_mismatch:langgraph:langgraph/_internal/__init__.py` |
| AC1 | the same file and its RECORD row changed (a hash-bypassed install) | activation refuses exactly `content_mismatch:langgraph` |
| AC1 | the records left at the 1.2.12 digest | activation refuses `records_stale:b45d1e37...` |
| AC1 | pydantic's `pydantic-core==2.50.2` requirement removed from the resolution | lock.py stops: pydantic_core below latest with no requirement capping it; nothing written |
| AC2 | a fake package added to the lock | records.py stops: "no reviewed entry ... for veldo-fake-package (no origin or approval to carry)" |
| AC2 | the same fake package added to the resolution | lock.py exit 3: diff `added: [veldo-fake-package]`, `owner_approval_needed` names it; only the diff written |
| AC2 | tenacity's registry license expression set to GPL-3.0-only in the scratch JSON | lock.py exit 3: the diff lists it under `license_changed` with `spdx_changed: true` and in `owner_approval_needed`; records.py records it and activation refuses `license_unapproved:tenacity:GPL-3.0-only` |
| control | the unaltered copy | activation accepted, no problem |

## AC2: met

`closure-diff.json` names every package added (none), removed (none) and moved (24), every registry
license field change (jsonpatch and tenacity, basis only), and also wheel tag changes and source changes.
Nothing needed the owner, so no new approval id is recorded in the closure; every entry carries its
VELDO-0043 status verbatim.

## AC3: met here, full gate pending (the lead's)

On the 1.2.19 runtime, with no edit to any suite, control_graph*.py other than the lock,
control_workflow*.py or control_runtime.py (`git diff --name-only 67594919..HEAD` lists only footprint
paths), `suites.txt`:

| Suite | Result |
|---|---|
| 32_veldo_0019_combined_graph | 51 passed, 0 failed |
| 59_veldo_0043_graph | 47 passed, 0 failed |
| 62_veldo_0045_runtime | 47 passed, 0 failed |
| 65_veldo_0132_workflow | 42 passed, 0 failed |
| 71_veldo_0130_api | 71 passed, 0 failed |
| 73_veldo_0078_backlog | 47 passed, 0 failed |
| 82_veldo_0085_decomposition | 41 passed, 0 failed |
| 92_veldo_0088_pm_cycles | 56 passed, 0 failed |
| 93_veldo_0152_intake_routes | 50 passed, 0 failed |
| 96_veldo_0204_reservation_policies | 46 passed, 0 failed |
| 110_veldo_0143_new_project | 135 passed, 0 failed |
| 113_veldo_0145_ui | 33 passed, 0 failed |

Each is `python3 -B scripts/selftest.py --suite NAME`; exit 2 is the partial-run code and is not a failure
(and, as the runner says, a partial run is not landing evidence: the full gate is). Mutation rows
(AC3's falsifier): `check_teeth_mutations.py --finding 45 --jobs 2` 23 of 23 rejected (201 s);
`--finding 43 --jobs 2` 61 of 61 rejected (422 s). Not run here: the full gate.
