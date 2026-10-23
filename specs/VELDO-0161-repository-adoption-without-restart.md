---
schema: veldo.spec/v1
id: VELDO-0161
title: A repository the owner names is adopted under one identity on his settled answer and taken on by the running factory without a restart
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W121
plan_revision: 4
depends_on: [VELDO-0028, VELDO-0029, VELDO-0047, VELDO-0068, VELDO-0139, VELDO-0142, VELDO-0153]
placement: [contracts, fleet, distribution]
protected_paths: []
footprint:
  - "engine/.veldo/control_repository*.py"
  - ".veldo/control_repository*.py"
  - "packs/*/.veldo/control_repository*.py"
  - "engine/.veldo/control_effect_executor*.py"
  - ".veldo/control_effect_executor*.py"
  - "packs/*/.veldo/control_effect_executor*.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "packs/*/.veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service*.py"
  - ".veldo/control_service*.py"
  - "packs/*/.veldo/control_service*.py"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "packs/*/.veldo/init_scaffold.py"
  - "scripts/suites/*_veldo_0161_*.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0161-repository-adoption-without-restart.md"
  - "specs/index.md"
  - "proof/VELDO-0161/*"
  - "proof/VELDO-0161/round2/*"
  - "proof/VELDO-0161/round3/*"
  - "proof/VELDO-0161/round4/*"
  - "proof/VELDO-0161/round5/*"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
behavior_bearing: true
observability:
  logs: >
    Record each adoption with the repository, identity and settled decision, the scaffold commit when one
    was laid, each adoption signature with the decision it answered, and the service taking the
    repository on, or the named refusal; never a token.
  metrics: >
    Count repositories adopted and refused by reason, adoption signatures issued, and repositories taken
    on by the running service.
  traces: >
    Join the settled decision, the scaffold commit, the adoption signature, the store binding and the
    running service's receiver configuration for the repository.
  error_taxonomy: >
    Distinguish remote owner mismatch, push refused, no settled decision, signature refused and a
    repository the running service did not take on; a repository left `failed` names its reason.
acceptance_criteria:
  - id: AC1
    text: >
      Claim: An existing repository the owner names is adopted under his chosen identity, with the
      scaffold laid as one recorded commit when missing, and signed by the adoption signer only for a
      repository a settled decision names. Set and completeness: Adopt a repository that carries the
      scaffold and one that does not; the provisioner checks its remote owner against the identity
      (VELDO-0153), lays the scaffold as one recorded commit and pushes it where missing, and the proposal
      he answered names that commit. The adoption signer is a service key setup enrolls among the host's
      enrollment signers, whose only use is signing a VELDO-0029 binding for a repository named in a
      settled owner decision; the effect executor checks the settlement before asking for the signature,
      and every signature is journaled. Falsifier: Let the adoption signer sign a binding for a repository
      no settled decision names, and the signer-scope check must fail; lay the missing scaffold in a commit
      the answered proposal does not name, and the scaffold-commit row must fail.
    falsified_by: >
      Let the adoption signer sign a binding for a repository no settled decision names, and the
      signer-scope check must fail; lay the missing scaffold in a commit the answered proposal does not
      name, and the scaffold-commit row must fail.
  - id: AC2
    text: >
      Claim: An adopted repository is taken on by the running authority service without a restart or
      reinstallation. Set and completeness: With the installed authority service running and serving one
      repository, adopt a second; the store binds it, the running service adds its receiver configuration,
      and the repository record becomes `active`, while the service's process identity and start time
      are unchanged and nothing is reinstalled; a packet from the new repository's receiver is then
      accepted by that same running service, and one from a repository no settlement adopted is refused.
      Falsifier: Take the adopted repository on only by restarting the authority service; the
      same-process row must fail.
    falsified_by: >
      Take the adopted repository on only by restarting the authority service; the same-process row must
      fail.
required_evidence: [unit, integration]
rollback: >
  Stop adoption and disable the adoption signer; repositories already adopted stay as they are, with
  their records, for the owner to remove by hand. No automatic rollback is authorized.
---

## Intent

The owner names an existing repository, or asks for a new one that the factory creates and then
adopts, and the running factory takes it on under one identity on his answer, with no separate command,
restart or reinstallation.

## Context

W121 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. Section 5 of the
approved [operating-model design](../docs/design/PLAN-0019-operating-model-design.md) (owner Telegram
29162) designs adoption, the adoption signer and the service taking the repository on without a
restart; its section 12 builds this with VELDO-0143 (item 19). These were VELDO-0143 AC3, split out on
the third review of revision 4 so taking a repository on without a restart has a falsifier of its own,
which would have given VELDO-0143 a fifth criterion; VELDO-0143 keeps the factory project's proposal,
creation and activation, and its creation path ends in this adoption. VELDO-0139 is a standalone built
item, so its edge is kept here and not in the plan graph. This new specification is draft; authoring it
supplies neither implementation proof nor operational activation.

## Out of scope

Creating a repository (VELDO-0143 AC2); moving a repository between identities (refused); Git hosts
other than GitHub; several projects in one repository.

## What the reviewer judges

- Normal use: the owner answers a proposal to adopt a repository, or to create one; the provisioner
  checks the remote owner, lays the scaffold if it is missing, the adoption signer signs its binding, and
  the running service takes it on, all with no restart.
- Threat model: a binding signed without a settled owner answer; the adoption signer used for anything
  other than a repository a settled decision names; a remote under another owner adopted; the service
  restarted or reinstalled to take on the repository; a packet from a repository nobody adopted
  accepted. The owner's account, the keystore, GitHub and the store are trusted.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962); forged rows in
  our own store and files planted in the installed directory.

## Notes

The adoption signer widens enrollment, so every signature it makes is journaled, and the review should
judge exactly that it signs only for a repository named in a settled owner decision (section 13 of the
design). The scaffold is laid before the lander has anything to judge a unit by, so it is one recorded
commit rather than a first unit.

## History

2026-09-25: split from VELDO-0143 AC3 on the third review of PLAN-0019 revision 4. AC1 is the former AC3's
adoption, scaffold commit and signer scope, with its falsifier unchanged; AC2 is its "taken on by the
running service without a restart", which had no falsifier, now with its own. A draft: only the owner
marks a specification ready.

2026-09-25, PLAN-0019 revision 4, fourth review: AC1's scaffold half, one recorded commit named by the
proposal he answered, gets a falsifier of its own beside the signer-scope one. Criterion meaning
unchanged. A draft.

2026-10-22 implementation on agent/claude/veldo-0161, built on VELDO-0153 (b44736c0, not yet landed).
control_repository holds the repository record, the adoption proposal and its brief, the settled-decision
check and the adoption signer, which judges the settled decision itself, signs one binding per decision and
journals every signature before handing it back. control_repository_provisioner checks the remote owner with
VELDO-0153's one check, lays a missing scaffold as one commit recorded under refs/veldo/adoption/ before the
owner is asked (no branch moves, nothing is pushed), so the proposal names it, and pushes exactly that commit
through the identity profile on his answer. control_effect_executor_adoption checks the settlement before
anything else. The authority service takes an adopted repository on in its running process: it judges the
decision, the signature, the binding and the store binding again, writes the repository's receiver
configuration beside the installed ones and writes the record active naming its own process and instance;
a new instance serves adopted repositories again at its start. Factory setup generates the adoption signer
and enrolls it among the host's enrollment signers; a factory set up before this change keeps its signers
file, a re-run neither adds nor requires the signer, and adoption there refuses signature_refused:not_enrolled.
Suite 109_veldo_0161_adoption carries the rows; finding 161 registers seven mutations, the three declared
falsifiers first. The AC1 rows ran green in the sandbox and both declared AC1 falsifiers turned their rows
red; the AC2 rows need a local socket the sandbox refuses, are red there by name, and with the AC2 falsifier
are the host's to run (proof/VELDO-0161/README.md). Acceptance criteria, risk, readiness and approval
requirements are unchanged.

2026-10-22, same branch: the provisioner's local Git steps in the adopted repository (the scaffold's fetch,
the fast-forward) run no hook of the repository, as no identity push does (VELDO-0153); the scaffold-commit
row plants four hooks and a registered mutation proves the part. Finding 161 now registers eight mutations.
Criteria unchanged.

2026-10-22, round 2 on the same branch, on the host run and the independent review of b44736c0..da39f3fb.
The host's fence counted 137 SSH agent contacts: they were the suite's own ssh-keygen calls (sign_as and key
generation), which now run without SSH_AUTH_SOCK and SSH_AGENT_PID; every ssh-keygen of control_repository
goes through one _quiet_env, and a row proves with a recording stand-in ssh-keygen that no signer call is
started with an agent named. The adoption effect runs every check that changes nothing (the named scaffold
commit, the configured remote, the repository's own commands, an existing binding, the host trust, the signer
enrolled, a missing key not enrolled) before it fast-forwards or pushes; any other fault ends the record
failed with unknown_outcome:<type>; a push Git accepted whose branch does not read back is
push_unconfirmed:remote. Every local Git step runs with core.fsmonitor off and a repository whose
configuration names a filter command or an fsmonitor is refused by name. prepare checks the remote is the one
the repository is configured with and that the repository id is one ref component, and the scaffold ref is
removed after the push or a refusal. The adoption signer pins host_identity and authority_generation and
refuses a generation below the store's. The serve-loop poll of the journal and the effect's 50 ms wait are
gone: the effect hands the record to the running service over its authenticated socket (a take_on packet from
the adopted repository's workspace, signed with the journal key in its own namespace, which only that packet
is verified under) and reports the service's synchronous answer; the reconcile at start stays, and a faulted
take-on is judged again by a timer ADOPTION_RETRY_SECONDS after its own fault. The service writes a record
active before it serves the repository, serves an active record again on its signature, binding and store
binding rather than on current membership, and writes again a receiver configuration it wrote. The instance's
token is instance_id. Finding 161 now registers 37 mutations, one at least for each fix. The footprint gains
proof/VELDO-0161/round2/*, the directory this round's evidence was asked for, which the one-segment glob
proof/VELDO-0161/* does not cover. Criteria, risk, readiness and approval requirements are unchanged.

Round 3 (the host run at 7b60b7c0): suite 73's setup/lays-down still expected the owner as the only enrollment
signer. AC1 says the adoption signer is a service key setup enrolls among the host's enrollment signers, so the
row now asserts exactly two lines, the owner with his key and adoption-signer with the public key of the key
setup generated, both in the enrollment namespace, and setup's output is unchanged. The footprint gains that
suite and proof/VELDO-0161/round3/*. The adoption161-signer-agent mutant ended in a driver error on the host:
the other rows' adoption signatures reached the hermetic fence's recording agent, and the fence raised at the
suite's end. adoption/signer-no-agent now owns an agent of its own, a recording socket where local sockets may
be made, and every AdoptionSigner.sign in the suite runs with the agent variables naming it and a recording
ssh-keygen first on PATH; the row is judged at the suite's end, over every adoption signature, and fails on
any agent variable passed on or any connection. Every other process stays under the fence. Finding 161 adds
three mutations of setup's enrollment signers (omitted, another key, an extra signer), targeting suite 73.
Criteria, risk, readiness and approval requirements are unchanged.

Round 4 (the independent review of rounds 2 and 3, proof/VELDO-0161/REVIEW-claude-2026-10-23.md, and the host
run at 0511a31a). R1: a running service reads the repository records once more right after its socket is
bound, so a record written while it started, whose hand-off found no socket, is taken on by that same
instance; nothing polls. The effect's hand-off names every fault: a refusal keeps its own code, a service
that did not answer in time is not_taken_on:timeout, anything else not_taken_on:unknown_outcome:<type>. R2: the
repository's own configuration is judged against an allowlist of keys local steps read as data, so
core.alternateRefsCommand and any other key not known to be data are refused by name, and a repository that
borrows objects (objects/info/alternates) is refused invalid_input:repository_alternates, at prepare and in the
effect's checks. R3: the identity binding (check only), the store's binding of the repository and the
configured generation against the store's are judged before the branch moves. R4: each run holds a lock for its
repository beside the store (flock, released by the kernel however the process ends); a run that finds its
request's record provisioning without enrollment and no live run holding the lock writes it failed with
unknown_outcome:interrupted at the step the record names (the scaffold step is now recorded before the branch
moves) and removes the scaffold ref, and one that finds the lock held refuses stale_subject:adoption_in_progress.
adoption/signer-no-agent counts the stand-in's adoption-key signatures against the journaled ones. Finding 161
adds twelve mutations. The three setup161 cases run suite 73, which the mutation stage's confined domain cannot
run (no user manager); the gate runs them in its unconfined leg, as it runs finding 139's, and
proof/VELDO-0161/round4/drive_setup.py runs them as ordinary processes. The footprint gains
proof/VELDO-0161/round4/*. Criteria, risk, readiness and approval requirements are unchanged.

Round 5 (the independent review of round 4, proof/VELDO-0161/REVIEW-claude-r4-2026-10-23.md). N1: the scaffold
push sets push.followTags=false on its command line and passes --no-follow-tags, as the VELDO-0153 effect push
does, so it sends exactly the commit the owner answered and no annotated tag the repository's push.followTags
would add; push.followtags stays in the allowlist because the push overrides it and nothing else reads it. N2:
prepare and the effect's checks run the identity transport's own judge (config_overrides) over the
repository's configuration for the proposal's remote and refuse by the code the push would give
(binding_mismatch:identity_transport_config), before anything is laid or the branch moves; one judge, not a
second list. Finding 161 adds three mutations. The footprint gains proof/VELDO-0161/round5/*. Criteria, risk,
readiness and approval requirements are unchanged.
