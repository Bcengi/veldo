# VELDO-0167 execution record configuration proof

Factory setup creates the state root's records directory with mode 0700. Every installed receiver
and both copies of the API service configuration name it. Receivers name the authority socket in
record_hint_service. Record hints carry only schema, dispatch identity, last sequence and ended;
the authority checks the local peer and fans them out through ServiceApi.publish, with its existing
subscriber numbering, service instance and dropped-socket accounting. Receivers never read the
subscriber registry. Legacy explicitly configured record_hints remain supported.

The new setup step checks all affected files before writing. It adds only missing or null owned
keys, preserving other bytes. Different existing values are named refusals. A current rerun writes
nothing. When the running service's record configuration gains a key, setup names its restart
command; configuration is read at service startup.

| Criterion | Behavior row | Observation |
| --- | --- | --- |
| AC1 | installed-record | Private shared directory and every receiver/API configuration; a real fixture worker's stdout and stderr through the installed receiver and the authenticated installed API, live and after termination. |
| AC2 | late-subscriber | Two separate API processes subscribe after the worker starts; both receive its next numbered hint with the service instance. The service logs dispatch, sequence and fan-out count without record lines. |
| AC3 | older-host | Production-written configurations with only this step's keys absent or null are upgraded; noncanonical formatting survives; only those files and the records directory change; a second rerun is identical; unrelated receiver/API edits are refused without writes; a running configuration upgrade names its restart. |

Suite: scripts/suites/91_veldo_0167_setup_records.py. Its fixture reuses only the setup and cleanup
portion of VELDO-0171's isolated installed-host fixture, not its behavior rows. Setup, signed
membership enrollment, reservations, dispatch transitions, receiver spawn/reap, record writing,
API subscription, passkey enrollment and authenticated HTTP reads use production interfaces.
The worker is a plain Python fixture; eligibility and vendor engine qualification are outside this
spec's proof. No live model, credential, Telegram endpoint, Tailscale CLI or user service installation
is used. The inert installation engine fixtures use VELDO-0172's shared constructors and call
conform_fake at teardown. The old-host fixture removes only the owned keys from setup's own output;
it does not claim an engine-upgrade qualification.

The red record is red-at-f1e1abb9.json: the current suite runs against the entire unchanged archived
pre-change tree. All three behavior rows fail by assertion. drive.py records assertion failures
separately from unexpected exceptions and keeps one report per behavior row.

Finding 167 registers seven mutations in scripts/check_teeth_mutations.py. mutations.json records
the baseline, byte-identical controls, source digests and each mutant's named failed row; the
adjacent diffs are the exact applied changes. The mutations omit the API records key, substitute a
fixed subscriber list, skip existing receivers during upgrade, fan out to only one subscriber,
omit numbering, ignore the receiver's service socket, and accept unrelated configuration edits.
The scoped proof driver runs them serially. The global mutation CLI and gate are reserved for the
reviewer, as are the whole selftest and load tests.

checks.json records the permitted suite runs and static checks. These are partial verification,
not a gate stamp, release proof, independent review or approval. The specification remains ready.
