# VELDO-0170 proof

The receiver refuses a configuration without host trust as
`host_trust_required:receiver_configuration` before acceptance or worker spawn.
Its refusal event names the dispatch, repository and configuration and counts the refusal.
Service inspection and lifecycle status enumerate the affected installed configurations
and name the same-argument `veldo factory setup` re-run as the repair.

The re-run reads trust from the installed service's channel ingress, falling back to
`control_eligibility.host_trust_path`, and checks its host identity against the service.
All trust and receiver checks precede writes. The step adds only missing host trust,
using whole-file replacement at 0600, and leaves current files byte for byte.
The engine upgrade leaves this key to the new step, including on a current engine.

Suite `87_veldo_0170_receiver_trust` uses real factory setup and installation with two
enrolled repositories, generated keys and tokens, a loopback Bot API and the existing
captured Tailscale stand-in. No real engine, login, service manager or external host is used.
The inert installation engines use the VELDO-0172 constructor and teardown conformance.
The settlement binding is written by the real signed request, presentation, Telegram
answer acquisition and settlement path. Runner prepares each dispatch and a real receiver
process accepts or refuses the fixture worker. Ordinary prerequisite entities use the
store's command interface, and claims use the claim transition.

| Criterion | Behavior rows and observations |
| :--- | :--- |
| AC1 | `launch/governed` and `launch/ungoverned`: both stop by the configuration name with no acceptance or worker. `status/configurations`: both status interfaces list only the old receiver, then clear after repair without restart. |
| AC2 | `rerun/launch-after-repair`: one old and one current configuration; only the missing key changes, mode is 0600, a second run changes no persistent file or logical store contents, and governed work launches under both. Replacing the trusted signer then refuses both as unsigned. |
| AC2 | `rerun/no-installed-trust`, `rerun/host-identity`: absent or unreadable installed trust and another host's trust stop by name before writes. |
| AC2 | `rerun/differs` (principal), `rerun/differs/workspace`, `rerun/differs/store`, `rerun/differs/journal_key`: each changes exactly one field of the same legacy receiver and independently requires the named refusal with no persistent writes. |
| AC2 | `rerun/default-trust`: an installed ingress without the path uses the host default and reports the added configuration. |

The no-write witness includes persistent file bytes, modes, modification times and the
logical SQLite contents. It excludes SQLite shared-memory and WAL bookkeeping files;
logical database comparison still observes changes committed through the WAL.
The launch transport substitutes the fixture worker in installer-produced configurations;
it does not fake dispatch acceptance, eligibility, settlement verification or launch records.

The red record is `red-at-f1e1abb9.json`. Running `proof/VELDO-0170/drive.py` with
its red option and baseline `f1e1abb9` executes the suite over a read-only Git
archive of that complete tree. The recorded run predates the review follow-up and
all eight behavior rows at that revision fail by assertion. In particular,
the governed launch reports `unsigned_decision:decision:D-9701` before the fix.

Finding 170 registers fourteen uniquely named mutations, including both declared falsifiers,
with intended rows in `mutations.json`. Mutation execution is reserved to the reviewer
by the owner's token rule. No mutation rejection is claimed here. The whole selftest,
mutation checker and canonical gate are also reserved to the reviewer.

Validation: all seven selected suites pass with zero failed assertions, both ordinarily
and in the specified empty gate environment: `87_veldo_0170_receiver_trust`,
`62_veldo_0039_dispatch`, `66_veldo_0047_authority`, `70_veldo_0069_bindings`,
`73_veldo_0139_factory_setup`, `85_veldo_0171_setup_api`, and
`86_veldo_0189_engine_upgrade`. The final isolated runs execute strictly sequentially.
`validation.json` records their actual summaries. Exit 2 is the selftest's required
partial-run exit, even with no failed assertion; these runs do not certify the full gate.

The Git boundary and validator checks pass, every engine copy is byte-identical,
and the anchor checker reports zero bad anchors. The supplied alternate final path
`scratchpadanchor_check.py` does not exist; `scratchpad/anchor_check.py` passes.

AC1 also requires ordinary receiver fixtures in sixteen other launch suites to name
trust. Those constructors now write generated host trust with no settlement signers;
the spec footprint names each affected file. Their existing assertions and fake engines
are unchanged. These additional fixture edits are syntax checked; their broader suite
execution remains with the reviewer under the owner's test scope restriction.
The explicit absent-trust cases in suites 70 and 87 still omit the key.

The review follow-up repairs the same omission in `proof/VELDO-0127/factory.py`
and adds it to the spec footprint. Suite `86_veldo_0127_agent_configuration` was
run alone: 51 passed, 2 failed. The launch fixture failures are cleared; only
`live/claude` and `live/codex` fail because their production hashes still pin
`control_launch.py` before commit `600f9ec9`. That file is unchanged in this
follow-up, but differs from main. Both captures require the owner's real-login
recapture; neither the live driver nor mutation checker was run here.

The expanded suite `87_veldo_0170_receiver_trust` was then run alone: 37 passed,
0 failed (11 specification rows plus 26 shared assertions), exit 2 for a partial
run. Each comparison field has its own finding-170 mutation:
`receiver170-principal-uncompared`, `receiver170-workspace-uncompared`,
`receiver170-store-uncompared`, and `receiver170-journal-key-uncompared`.
Each removes only that field from the comparison and targets its own row.
Their registered patches are syntax checked, not executed. The new rows have
not been run on the historical red baseline; the old red record is preserved.
`validation.json` records the follow-up results separately from the earlier runs.
