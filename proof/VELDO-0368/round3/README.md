# VELDO-0368 round 3 measurements

These files measure the proposed enforcement design. They do not implement product
behavior or issue coverage certificates.

`measure-inventory.py` reads the same historical receipt as round 2 and checks its
SHA-256 digest. It reads historical source through this checkout's Git objects.
It never opens another worktree or launches validation workers. Run it with
`python3 -B proof/VELDO-0368/round3/measure-inventory.py` to reproduce `inventory.json`.
The receipt lives at the absolute path recorded in that JSON file.

The inventory counts each shared control once within a category. Categories overlap.
The generated import candidates are conservative proposals, with unresolved dynamic
loads and unmeasured fixture inputs. They are not successful narrowed runs. Driver
case registries are removed before scanning their executable bodies. The scan does
not apply each mutation to its target, so it cannot establish the union of imports
for all modes. The spec's production resolver must generate that union. No closed
import set or new historical carry eligibility is claimed from this scan.

`run-pc1.py` sends `measure-landlock.py` as an encoded command payload to the owner's
remote runner on pc1. The repository remains pinned to `f345e09b6`; the measurement
payload's own digest is included in the result. Run it from this worktree with
`python3 -B proof/VELDO-0368/round3/run-pc1.py`. The runner waits for its authorized
slot. It runs only focused probes and serial setup samples, never a full gate.

The final run is `rr20261126125200-be46`; its raw result is `landlock.json`.
`provenance.json` binds the source and result digests. `pc1-run.log` omits
the encoded source command line, which duplicates the committed script, and trims
trailing whitespace.

The scope probe enters the existing worker_tree namespace and IPC launcher, then
calls the production confine_in_tree function. Its broad run uses current worker
grants. Its narrow run adds a read layer for one repository file and fixed runtime
roots. It checks content reads, native cat, directory enumeration, write denial,
metadata and the native watchdog. A deliberately preopened descriptor demonstrates
why descriptor cleanup belongs in the certificate's prerequisites. Neither probe
constructs the projected filesystem view required for certification.

Setup samples fork a fresh process for each policy. Each of five shapes gets 25
samples for the full existing Landlock function and 25 for the added read layer.
Shape zero is one broad repository grant; the other shapes grant 32, 128, 512 or
1,024 individual Python files. Shape order alternates by repetition. Preparation
of the path lists and process creation are outside the timed interval. Path checks,
opens, rule additions, restriction and closing rule descriptors are inside it.
For the added-layer samples, the existing broad domain is installed before the
timer starts. The full function includes its strict IPC filter setup. In the worker_tree path,
that filter is already installed; the read-layer timing isolates the added layer.

The files and interpreter are warm. CPU is process CPU time; wall time is monotonic.
The p95 is sample 24 of 25 in sorted order. Snapshot copying, import generation,
runtime hashing, persistent lookup overhead, full item execution and full-gate wall
time are unmeasured. The raw samples support setup-cost claims only.
