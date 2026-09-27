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
