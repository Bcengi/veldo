# VELDO-0171 capture and implementation blocker

Implementation is blocked at AC2. This is evidence of the blocker, not a completed
implementation or acceptance proof. No production code has changed.

On 2026-09-27 the builder ran exactly the three authorized read-only Tailscale
commands: version, JSON status, and JSON Serve status. All exited zero. Raw stdout
and stderr remain only in
`/home/dmitry/projects/veldo-live-captures/2026-09-27/tailscale/`.

`scrub_tailscale.py` produces `tailscale-capture.json` from those files. Its named
allowlist retains schema field names, the CLI version and backend-state constants.
Other strings and dynamic map keys become string placeholders, numeric values
become zero of the original type, and booleans and null retain their types. The
scrubber checks every raw string value longer than three characters, plus dynamic
keys and version-output lines, against the serialized result. There were 97
nonconstant strings and zero literal substring matches. No raw output is copied
into this repository.

The captured status has Self, CurrentTailnet and CertDomains. Serve status has
TCP and Web. Neither output exposes the configured operator account or a
background-persistence capability. AC2 requires setup to distinguish their absence
before any write, and its refusal fixtures must be listed field edits of the real
capture. Inserting invented operator or persistence fields would make a fake
interface pass without proving that the installed CLI supports it. The capture
therefore has no derived states and no field edits. No stand-in was built.

An owner decision is needed on the read-only production source for these two
preconditions and the corresponding capture contract. The authorized read-only
commands cannot establish those observations from the captured output. No
additional daemon query or state-changing Tailscale command was attempted.

AC1 through AC4 remain unimplemented and unproven. There is no behavior suite,
red record or mutation record for an implementation that does not exist. The
live Serve activation leg remains pending with the lead and owner.

Validation on this branch:

- Git subprocess boundary: pass, no findings.
- Footprint: four changed files, nothing outside VELDO-0171.
- Anchor check: zero bad anchors.
- Repository validator, all: exit zero.
- Literal fixed-string grep of the capture against all 97 nonconstant raw strings:
  zero matches. A planted host name, home path, numeric identifier and dynamic map
  key also all disappear through the scrubber.
- Ordinary whole selftest: exit zero, 6860 passed, zero failed. HOME was an isolated
  scratch directory. No worktree edits were made while the test ran.
- Whole selftest under the requested isolated gate environment: exit one before
  completion, with no assertion failure printed. The existing
  `12_warp_1210_hardening_four.py` suite raises FileNotFoundError at line 5946 in
  `_m10_r12_fifo_at`: bytecode suppression prevents its warmup from creating the
  cache directory where it then tries to create a FIFO. The ordinary full run
  subsequently passed this test. The suite was not modified.

The gate was not run. No service manager or state-changing Tailscale command was
invoked. No acceptance row, red record or mutation rejection is claimed for
VELDO-0171.
