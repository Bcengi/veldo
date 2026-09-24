# VELDO-0045 proof

Pinned isolated runtime, dependency licenses and distribution inventory (PLAN-0019 revision 3, W30,
Release 1 stage 4). Branch `build-veldo-0045`, built on b21cab1. Status, criteria and every other
specification are unchanged.

## What landed

**Built on VELDO-0043, no second lock or installer.** `.veldo/control_runtime.py` (byte-identical in
`engine/.veldo/`, laid down by `init_scaffold.py`) reads `control_graph_lock.py`, calls
`control_graph_install.py` for the install, builds its adapter with `control_graph.py` and runs its
enforcement children in `control_graph_isolation.py`'s harness.

**Records.** `engine/runtime/langgraph-records.json` (installed at `.veldo/runtime/`) records, for
each of the 38 locked packages, the registry-served wheel URL, upload time and sha256, the registry
license fields and their SPDX form, the source repository, the PEP 740 attestation where PyPI has one
(16 of 38), the latest release (three pins are capped: pydantic_core, uuid_utils, websockets, each
with the requirement that caps it), the origin and approval carried from the reviewed VELDO-0043
closure, and the content digest of the genuine wheel. `records.py` regenerates it from PyPI; it was
run on 2026-09-23, and every downloaded wheel matched the lock and the registry.

**Activation** (`control_runtime.py check`) refuses by name: `missing_asset`, `records_stale`,
`hash_mismatch` (the lock's hash is not the registry's), `unrecorded_package`, `license_unapproved`,
`approval_missing`, `license_mismatch`, `missing_dependency`, `version_mismatch`,
`unlocked_distribution`, `file_mismatch` (a file against RECORD), `content_mismatch` (the wheel's
rows against the genuine wheel), `unsatisfied_dependency` and `path_outside_runtime` (judged by the
runtime's own importlib.metadata and packaging), `runtime_absent`, `runtime_unreadable`. Graph
invocation through `control_runtime.adapter()` reports `runtime_unavailable` with those problems.
`qualify` runs start, suspend, advance and cancel on the real LangGraph through the production
adapter with one deterministic workflow and no model. `install` is the installer, then `qualify`.
`enforcement` enumerates the installation's gate and guard `python3 <module>.py` commands and its
authorization entry and runs each in the isolated harness with the runtime directory hidden.

## Rows

Suite `scripts/suites/62_veldo_0045_runtime.py`: 11 rows and 10 `ran/` rows, 21 passed.

- AC1 `runtime/records-cover-lock`, `runtime/workload`, `runtime/altered-hash-refused`,
  `runtime/altered-wheel-refused` (the runtime-integrity row), `runtime/omitted-dependency-refused`,
  and `runtime/observations`. Tampered runtimes are copies changed by a real pip, offline; pip
  `--require-hashes` refuses the altered wheel and pip check agrees on each dependency scenario.
- AC2 `journey/assets-installed` (the journey-asset row: the traced `install` reached exactly the
  declared JOURNEY, each file laid by the scaffolder with its digest, no read of the source tree, and
  every runtime file it or the runner child opened is in RECORD with its digest) and
  `journey/omitted-asset-named`.
- AC3 `enforcement/entries-enumerated`, `enforcement/no-runtime` (the no-runtime enforcement row) and
  `enforcement/graph-unavailable`.

`observations.json` is one run (`drive.py`).

## Red before the fix

`red.py b21cab1` runs this suite over b21cab1's production modules and engine templates:
`red-b21cab1.json` shows all 11 rows red by assertion, all 10 `ran/` rows green, nothing raised.

## Mutations

`python3 -B scripts/check_teeth_mutations.py --finding 45 --jobs 4`: 23 of 23 rejected, each target
row red by assertion with its region completing (`mutations.json`, diffs in `mutations/`). Declared
falsifiers: `runtime-content-enforcement-bypassed` (AC1), `scaffold-omits-runtime-lock` (AC2),
`authorization-imports-langgraph` (AC3). Every row has at least two.

## Costs

Suite 62: 11.7 to 14.2 s here. `--finding 45`: 76.9 s at 4 jobs (each case reruns the suite). In the
gate's mutation stage the 23 cases add about 280 worker-seconds and raise its budget by 46 s; not
measured inside the gate. Activation 0.2 s, qualification 2.1 s, enforcement 0.6 s.

## Stated limits and filed items

- pip records the bytecode it compiles with no hash, and the interpreter runs that bytecode. Every
  hashed file and the genuine wheel content are verified; compiled bytecode is trusted like the rest
  of the installed directory (planted files are out of review scope). Precisely: every RECORD row
  ending `.pyc` with an empty hash, and every row starting `../`, is skipped by both the file check and
  the genuine-wheel comparison, so an unhashed `.pyc` listed in RECORD by a wheel crafted against this
  check (with pip's own hash refusal bypassed) would not be detected. Filed: skip an unhashed `.pyc`
  only when it is the cache path of a `.py` the genuine wheel ships.
- Filed: `records.py` leaves out only `.data/scripts/` rows on the wheel side while activation skips
  every `../` row, so a future locked wheel with other `.data` members (data, headers, purelib,
  platlib) would be refused as `content_mismatch` on a correct install. None of today's 38 wheels has one.
- Filed: `enforcement_entries` keeps only lowercase-word arguments, so an entry with an option such as
  `--json` or a path argument would run with it dropped. Today's installed entries are unaffected.
- Activation gates `control_runtime.adapter()`. `control_graph.Adapter.installed()` (VELDO-0043's
  footprint) does not call it, so a caller that builds an adapter directly skips activation. Filed
  for VELDO-0043; no production caller exists yet.
- CPython 3.12.3's `sys.stdlib_module_names` omits `_wmi`, so VELDO-0043's harness refuses the
  standard library import `platform` makes (reached by events.py). This check completes the list it
  hands the harness; the same defect in `control_graph_isolation.py` itself is filed for VELDO-0043.
- Hidden means the audit hook refuses open, list and launch under the runtime directory; a stat is
  not an audit event.
- The records are for linux x86_64 CPython 3.12, the lock's platform. The Mac needs its own.
- `enforcement` judges an installation's gate. This repository's own gate also runs development
  scripts (scripts/selftest.py and others) that import scripts/ siblings the harness does not allow,
  so the command is not meant for this checkout and was not run here.
