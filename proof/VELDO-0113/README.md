# VELDO-0113 implementation and evidence

Status: blocked, not accepted. The three census-backed absence obligations stand
down on INCOMPLETE qualification. The construction row fails at both shipped
CLI sites, and the missing store-write grant is reported as an explicit gap.

The lead decision of 2026-11-21 is recorded in the specification History. The
original direct-store counterexample remains in `contract-gap.txt` and
`reproduce_contract_gap.py`; it explains the amendment and is not an absence
claim. The original no-op receipt and dependency logs are historical diagnostics.

The consumer now joins the unchanged VELDO-0112 adapters to every current registry
identity and both endpoint states. There are 21 registrations: 11 external clients
and 10 in-process entries, giving 42 assessment cases. External calls run through
the VELDO-0111 observer from before exec through descendant drain. The absent
endpoint is checked for ENOENT. The dead endpoint is a real socket inode whose
binding child acknowledges readiness through a pipe, then is killed with SIGKILL
and reaped before any client call. Refusals must carry the expected kernel error;
a malformed input or unrelated exception does not pass.

The fixture uses real Git enrollment and HMAC signing through the transport's
public signer/verifier seams. It supplies no store handle to external clients.
Claim authorization and state transitions remain the separate live VELDO-0112
suite's obligation. This consumer measures the real client/refusal paths and uses
its adapters unchanged; it does not simulate connection failure.

Launch envelopes declare the root and only the required Git identity lookups
before invoking the observer. Their identities are causal birth slots, not
executable-name exemptions. Each lookup's exact argv and root parent are fixed in
advance. A fixture-controlled wrapper acknowledges its PID and parent, then execs
the real Git binary in the same process. Those acknowledgements join one-to-one
to census birth identities using their observed birth-to-exit intervals, including
PID reuse; missing, extra, duplicate or mismatched births cannot
be waived by a process name. Every service event in the measured scope is
forbidden. The endpoint fixture is already dead and outside that scope.

The three named consumer rows carry distinct PASS, FAIL or STANDS DOWN statuses.
An INCOMPLETE receipt always leaves these rows STANDS DOWN, even when the
observer captured a suspicious birth or service. Such effects remain diagnostics;
Only a COMPLETE receipt permits an absence verdict. Separately, AC3 is refuted
when the consumer accepts an incomplete receipt or loses the required stand-downs. Missing facilities
and all interrupted-observer faults from VELDO-0111 are driven for every
external registry/state case; all three names must remain STANDS DOWN with
census_incomplete and zero PASS rows. The suite separately asserts this protocol;
a passing protocol assertion is not a green absence claim.

The default integration enumerates all eight entries of `census.FAULTS`, giving
176 fault cases across the 22 external invocations. It checks the requested
state, category and capability, including the lost-event counter. Loss and
collector-death drives declare a fixture child before the call so those faults
also fire for childless relays; that child is used only in fault-injected runs.
Earlier two-fault drives remain diagnostics, not full-matrix qualification.

The construction census includes both module trees, both CLI directories and
operational scripts, excluding test harnesses. It recursively finds Python files
and Python front doors, follows direct/imported/assigned constructor aliases,
and reports new construction sites with file, line and source digest. The five
Dispatches sites named by the lead are present in each shipped tree:

- `control_service.py:3172,3904`
- `control_service_api.py:214`
- `control_launch.py:2295`
- `control_launch_work.py:148`

Dispatcher is constructed at `dispatch.py:574`. The expanded census ALSO found
`bin/veldo:285` and `engine/bin/veldo:285`, in `cmd_work`. These are production
constructions outside the authority modules, so the construction row currently
fails. Its preceding `_entry_gate` calls
`control_eligibility.enrolled_gate:429`, which opens the store read-only at line
451; it does not contact the authority endpoint. `construction-census.txt`
retains this finding. The earlier `structural-controls.txt` demonstrates alias
and new-file detection over the narrower module-only scan; it does not discharge
this newly discovered CLI boundary. The lead has been asked to resolve it. No
CLI exemption or architectural refactor has been invented to make the row pass.

There is also no process-specific writable-store grant today.
`control_store.open_store:398` accepts mode rw, checks filesystem support and
SQLite durability, and does not authenticate the calling process. The consumer's
separate non-authority process opens a fresh real store and commits a probe table.
That row reports GAP, never isolation success. Filesystem access by the same
account remains sufficient. This is explicitly permitted as a disclosed gap by
the lead amendment; it is not silently treated as proof of process isolation.

Four falsifiers are registered under finding 113 in the standard teeth inventory:
a fallback Authority constructed in a child and immediately reaped, a transient
abstract Unix listener in the refusal handler, an incomplete census treated as
success, and an extra Dispatches construction in claim.py. The standard suite
anchors support production and fixture copies. `run_checks.py` retains the exact
diffs and full case receipts, and checks the named false rows and restoration.
Full red/green acceptance evidence cannot be claimed while the construction
baseline is false and VELDO-0111 never supplies a COMPLETE receipt.
`proof/VELDO-0111/OPEN.md` identifies implementation gaps, including the
non-exhaustive protocol inventory; this is not merely a host permission issue. The process
and listener falsifiers must stand down on this host under the literal contract;
a captured effect alone cannot substitute for the required false consumer row.
The initial evaluator allowed that substitution; it was corrected after the
first process drive. Earlier diagnostic results are not acceptance evidence.

The full-matrix live captures completed, but the proof writer initially compared
Python fault tuples with their JSON-decoded lists and failed its round-trip
assertion after saving the complete JSON. Original run failures remain in the
`*-run.txt` files. The corrected writer compares canonical JSON bytes, and
`run_checks.py --reassess NAME` explicitly assesses a saved receipt without a new
observer invocation. Reassessment does not turn those writer failures into valid
live red/green drives. Source and original JSON digests remain bound and checked.

Receipt archives use lossless shared capability tables and an LZMA payload
inside a gzip JSON envelope to stay below the proof size limit. `run_checks.read_receipts(path)` reconstructs every original receipt
and verifies its original SHA-256. No home path is rewritten inside a receipt;
the driver refuses to retain one. Human-readable diagnostic output replaces any
user home prefix with `<user-home>`.

The consumer coordinates at most four independent observer subprocesses at once.
Each case has private arguments and launch acknowledgements, and the endpoint
state stays fixed until all cases finish.

All new synchronization uses pipes, waits or terminal process observations. New
deadlines are 1200-second hang detectors; the consumer enlarges the dependency's
Git subprocess timeout without changing its argv, result or refusal, including
fixture setup. The relay main adapter has no timeout argument, so its forward
call's default is enlarged to the same hang bound in the measured process. No new
sleep-based assertion is used. Loaded checks run through the external host-heavy
wrapper. No canonical gate, independent review or owner approval is claimed.

The standard mutation coordinator completed finding 113: four cases registered,
four executed, zero valid rejections, ten workers, and no surviving workers. Its
result is `invalid_baseline`. Confined controls failed the construction boundary,
real-refusal and full-fault assertions. The confinement filter denies ptrace at
`scripts/agent_sandbox.py:199`; no owner-controlled exemption was added. See
`gate-mutations.txt` and `mutation-worker-findings.txt` for the actual findings.

Selected selftests are retained as partial-run diagnostics only. They are not
canonical unit verification or acceptance evidence. The selected VELDO-0109,
VELDO-0111 and VELDO-0112 runs had zero assertion failures. VELDO-0113's construction
failure remains explicit. Lint and the personal-setup sweep are separate checks.
