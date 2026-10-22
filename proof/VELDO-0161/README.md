# VELDO-0161: repository adoption on the owner's settled answer, taken on without a restart

Branch agent/claude/veldo-0161, built on VELDO-0153 (b44736c0, which is not landed yet). Code commits
bbe023d3, a2af558b and 5b6631b5; the specification's history entry is f0b634da. Nothing here is a gate
result, a review verdict or an approval. The full gate, the AC2 rows and the AC2 falsifier are the host's to
run (Host runs, below).

## What was built

| Piece | Where |
| --- | --- |
| Repository record (`repository:<uuid>`, provisioning, active or failed with a named reason, history), adoption proposal and brief, the settled-decision check, the adoption signer | `engine/.veldo/control_repository.py` |
| Provisioner steps: VELDO-0153 owner check (operation `adoption`), the missing scaffold as one commit recorded under `refs/veldo/adoption/<uuid>` before he is asked, fast-forward and identity-profile push of exactly that commit on his answer | `engine/.veldo/control_repository_provisioner.py` |
| The adoption effect: settlement first, record, remote, scaffold, identity, signature, store binding, each recorded and stopping by name | `engine/.veldo/control_effect_executor_adoption.py` |
| The running service takes an adopted repository on (judges decision, signature, binding and store binding again; writes its receiver configuration; record active naming this process and instance); a new instance serves adopted repositories again at its start; `inspect` reports the instance and the repositories served | `engine/.veldo/control_service.py` (`Service.take_on`, `serve`) |
| Setup generates the adoption signer in the protected key directory and enrolls it among the host's enrollment signers | `engine/.veldo/control_factory_setup.py` (`adoption_signer`, `host_files`) |
| The three modules in the scaffold's file list | `engine/.veldo/init_scaffold.py` |
| Suite `109_veldo_0161_adoption`, finding 161 (seven mutations) | `scripts/suites/`, `scripts/check_teeth_mutations.py` |

Each `.veldo/` copy is byte-identical to its engine file (template sync).

## Per criterion

**AC1** (adoption under the chosen identity, the scaffold as one recorded commit the answered proposal
names, signed only for a repository a settled decision names). Rows: `adoption/remote-owner-refused`,
`adoption/settlement-before-signature`, `adoption/signer-scope`, `adoption/scaffold-present`,
`adoption/scaffold-commit`, `adoption/signatures-journaled`, `adoption/signer-enrolled`,
`adoption/push-refused`, `adoption/observed`. All green in this sandbox (observations.json). Declared
falsifiers: `adoption161-signer-unscoped` turns `adoption/signer-scope` red and only it;
`adoption161-scaffold-relaid` turns `adoption/scaffold-commit` red and only it; both green again on the
restored baseline (falsifiers.json). Further teeth: settlement unchecked, remote owner unchecked and
signature unjournaled each turn their rows red.

**AC2** (taken on by the running service without a restart or reinstallation). Rows:
`adoption/taken-on-running`, `adoption/same-process`, `adoption/packet-accepted`,
`adoption/not-taken-on-named`. They install the service with `control_service.install` and run the unit's
ExecStart as a separate process serving its real socket. This sandbox refuses `socket(AF_UNIX)` at the
seccomp level (also with the tool sandbox disabled), so no service can serve here: the four rows are red by
name, never stood down. The declared falsifier `adoption161-restart-take-on` (the serving process execs
itself, keeping its pid and kernel start time, so only the instance token and serving time can tell) and
`adoption161-receiver-configuration-absent` are registered and not judged here.

A development observation, not AC2 evidence: `inprocess_harness.py` runs the same suite with the installed
`bin/control_service.py`'s own `serve()` in a thread over a socketpair transport. All 23 rows are green, and
the receiver-configuration mutant turns `adoption/taken-on-running` red. A thread shares the process, so it
cannot establish the same-process claim and cannot run the exec falsifier.

## How the suite behaves where it runs

- Settlement is real: VELDO-0068 terms, the VELDO-0064 inbox, the VELDO-0065 presenter over a loopback Bot
  API, the owner's answer through the API edge.
- Pushes go through the VELDO-0153 identity profile inside the identity wire's hermetic fence. Where AF_UNIX
  is refused the fence runs without its recording SSH agent and SSH_AUTH_SOCK names a path where nothing
  listens (printed); every other wall is the wire's own.
- Where the systemd user manager cannot qualify the worker profile (here, and the gate's confined leg), the
  installer's containment qualification is answered qualified (printed); the service under test launches
  no worker.

## Dependency suites here (consumer-suites.json)

Green: 46 (VELDO-0029), 69 (VELDO-0068), 108 (VELDO-0153), 77 (VELDO-0149), 26 (init_scaffold stamp).
Stopped at `socket(AF_UNIX)` before their rows: 103 (VELDO-0142), 107 (VELDO-0153), 58 (VELDO-0028).
66 (VELDO-0047) stood down by name and 73 (VELDO-0139) is red at the user-manager qualification: both are
on the gate's unconfined list.

Static checks run here: lint, template sync, generated (requires.json regenerated), the mutation anchors of
finding 161 resolve and compile.

## Host runs (required before review)

1. `bash scripts/verify.sh` (full gate, both legs, mutation stage).
2. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: all rows green, the four AC2 rows included.
3. `python3 scripts/check_teeth_mutations.py --finding 161`: all seven cases killed, in particular
   `adoption161-restart-take-on` (AC2's declared falsifier) on `adoption/same-process`.
4. Unconfined suites this change touches: 66_veldo_0047_authority and 86_veldo_0189_engine_upgrade (the
   service and its closure), 73_veldo_0139_factory_setup, 85_veldo_0171_setup_api, 91_veldo_0167_setup_records
   and 106_veldo_0185_dispatch_setup (setup's keys and host trust).
5. Socket suites stopped here: 103_veldo_0142_git_identities, 107_veldo_0153_identity_push,
   58_veldo_0028_effects.

## Assumptions and limits

- VELDO-0153 is this branch's base and is not landed; this lands after it.
- A factory set up before this change has no adoption signer; a setup re-run neither adds nor requires it,
  and adoption there refuses `signature_refused:not_enrolled` (row `adoption/signer-enrolled`).
- The adoption effect is the trusted supervisor-side entry (`control_effect_executor_adoption.py <config>
  <request>`); VELDO-0143 wires the factory PM's proposal to it.
- Setup's laying of the signer is exercised through `adoption_signer` and `host_files`, the functions setup
  writes them with; the full setup path is suite 73's, on the host.
