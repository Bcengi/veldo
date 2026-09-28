# VELDO-0186 proof

Factory setup installs the runtime files its module census names, checks qualified host engines
before writing state, pins Claude Code through its production writer, and records both engine
bindings. The installed receiver uses the same state root and qualification records. No engine is
executed and no service is started by this proof.

| Criterion | Behavior row | Production behavior proved |
| --- | --- | --- |
| AC1 | `runtime/assets` | Factory CLI setup installs the three current records and two future literal assets, including a nested asset, with identical bytes, recorded digests and the actual asset count. |
| AC1 | `runtime/missing` | The service installer names a missing source asset before creating an installation. |
| AC1 | `runtime/setup-missing` | Real factory setup names the missing asset and leaves the fresh state root empty. Removing its early runtime census fails this row even though the service installer still refuses later. |
| AC1 | `runtime/modes` | The installed runtime directory and its nested directory both have mode 0500. |
| AC2 | `bind/engines` | Installed engine bindings match setup's returned and persistent records. Claude's copy is regular, byte-identical and 0555. The receiver configuration names the factory state root. |
| AC2 | `engines/unlisted` | Each engine's unlisted version refuses as missing_evidence:engine_baseline:9.9.9 before state writes. |
| AC2 | `engines/digest` | Changed source bytes for either engine refuse as binding_mismatch:engine_digest before state writes. |
| AC2 | `engines/version` | A Claude command resolving to cli.js refuses as missing_evidence:engine_version:claude_code before state writes. |
| AC2 observability | `metrics/pins` | The production counter reports one actual pin, zero for the real vendor binding alone, and zero for no bindings. Setup reports its real pin inventory. |
| AC2 observability | `metrics/binds` | The installed Receiver binding path emits one binds_refused increment for each engine's changed digest, two in total, and none for a non-engine adapter. |

The suite uses generated OpenSSH keys, a generated token stand-in, real Git repositories, the real
store, enrollment, service installation and pin writers. Containment qualification and daemon reload
are fixture seams. Engine bytes use VELDO-0172's shared fake constructor and the suite runs its format
check at teardown. No engine protocol is emitted, so that supporting check compares zero events.
Codex qualification uses its production writer; Claude uses the committed qualification entry with
the fixture digest. Each behavior row reports once. Unexpected section exceptions are distinguished
from assertion failures by the proof driver.

Setup still supports the versioned native Claude installation. Qualification's existing extraction
code also takes its native version from the resolved filename. This repair explicitly refuses a
non-versioned target such as an npm cli.js with missing version evidence, as the review allows;
it does not execute a version command or add npm installation support.

The receiver emits engine_bind_refused with the engine name, refusal and binds_refused metric through
its existing event stream. Launch._take retains those messages. The pin counter counts distinct
regular, non-symlink files under the factory engine directory from the bindings the installer returns;
the external Codex vendor binary contributes no pin. The source and installed configuration readers,
engine pin and bind writers, setup summary readers, and receiver event reader were audited. AC2's
observability requires control_launch.py and its engine copy, which were added to the footprint.

Suites 73, 74 and 86 now put the fake engine PATH assignment inside their outer try and restore PATH
first in finally, before any teardown checker can raise. Suites 73 and 74 were inspected but were not
run in this job because the owner restricted execution to suite 86. Existing installer fixtures in
suites 66, 71 and 83 remain in the footprint from the original implementation.

The current proof driver was run against unchanged Git archives:

- `red-at-9f1a0445.json`: all ten behavior rows red by assertion against the original implementation base.
- `red-at-aa85e4a2.json`: four rows red by assertion against this repair's starting commit: runtime/modes,
  engines/version, metrics/pins and metrics/binds. The other six remain green because that commit
  already implements those behaviors. In particular, setup's missing-source check already existed;
  the new row closes a mutation coverage gap. This result is intentionally not labeled all-red.

Finding 186 registers thirteen uniquely named mutations:

| Mutation | Named failing rows |
| --- | --- |
| `setup186-python-only` | runtime/assets, bind/engines |
| `setup186-skip-claude-pin` | bind/engines |
| `setup186-missing-runtime-ignored` | runtime/missing |
| `setup186-claude-unlisted-taxonomy` | engines/unlisted |
| `setup186-codex-unlisted-taxonomy` | engines/unlisted |
| `setup186-claude-digest-unchecked` | engines/digest |
| `setup186-codex-digest-unchecked` | engines/digest |
| `setup186-receiver-without-state-root` | bind/engines |
| `setup186-skip-setup-asset-check` | runtime/setup-missing |
| `setup186-writable-runtime` | runtime/modes |
| `setup186-filename-as-version` | engines/version |
| `setup186-constant-pin-count` | metrics/pins |
| `setup186-unmeasured-bind-refusal` | metrics/binds |

Static inspection verifies unique edit anchors, production-copy anchors and mutation names, with
final-label targets covering every behavior row. Mutation execution is reserved for the reviewer;
mutations.json records registration and pending execution, not rejection.

verification.json records the normal and clean-environment suite runs, footprint and anchor checks,
repository validation and byte-identical engine copies. Selected selftest runs exit 2 even when all
assertions pass because RunScope marks them partial. No gate, whole selftest or mutation runner was
run. The History records VELDO-0189's older-install upgrade inputs. This proof makes no gate-stamp or
independent-review claim.
