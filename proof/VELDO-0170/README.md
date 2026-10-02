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
| AC2 | `rerun/no-installed-trust`, `rerun/host-identity`, `rerun/differs`: absent or unreadable installed trust, another host's trust, and another receiver field all stop by name before writes. |
| AC2 | `rerun/default-trust`: an installed ingress without the path uses the host default and reports the added configuration. |

The no-write witness includes persistent file bytes, modes, modification times and the
logical SQLite contents. It excludes SQLite shared-memory and WAL bookkeeping files;
logical database comparison still observes changes committed through the WAL.
The launch transport substitutes the fixture worker in installer-produced configurations;
it does not fake dispatch acceptance, eligibility, settlement verification or launch records.

The red record is `red-at-f1e1abb9.json`. Running `proof/VELDO-0170/drive.py` with
its red option and baseline `f1e1abb9` executes the current suite over a read-only Git
archive of that complete tree. All eight behavior rows fail by assertion. In particular,
the governed launch reports `unsigned_decision:decision:D-9701` before the fix.

Finding 170 registers ten uniquely named mutations, including both declared falsifiers,
with intended rows in `mutations.json`. Mutation execution is reserved to the reviewer
by the owner's token rule. No mutation rejection is claimed here. The whole selftest,
mutation checker and canonical gate are also reserved to the reviewer.

Validation is in progress. The selected suite passes all eight behavior rows and the
existing dispatch suite passes. The anchor check reports zero bad anchors.
