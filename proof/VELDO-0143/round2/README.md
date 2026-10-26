# VELDO-0143 round 2: the host's failures at a07ad991

Branch agent/claude/veldo-0143, on VELDO-0161 round 5 (8f749423). Round 2's commits: 1b2fb86b (failure 3),
e2e2bc1e (failure 1, and so 2), 6d2880b2 (failure 4), c1bf6dec (finding 143's two new mutations, the falsifier
driver's judgment, the run scripts), then this evidence and the specification's history. Nothing here is a gate
result, a review verdict or an approval. VELDO-0161's own files (the adoption effect, the provisioner, the
adoption signer, suite 109) are not changed; the upgrade path's signer (suite 86) is round 6 of VELDO-0161's and
is not touched.

This sandbox refuses AF_UNIX (so the identity wire's fence runs without its recording SSH agent), has no systemd
user manager (suite 66 stops before authority/installed-assets) and may not write the account's graph stage
(pm/new-project-run is refused runtime_unavailable). `sandbox_run.py` runs suite 110 on a `git archive` copy of a
commit and, only when asked, stands in for the missing pieces: `--stage` points the copy's graph stage under the
run's temporary directory, so the installed LangGraph runtime itself runs; `--agent` puts a stand-in ssh-keygen
first on PATH that records, as the host's agent does, every `ssh-keygen -Y sign` started with the fence's agent
named in SSH_AUTH_SOCK. With both, a07ad991 reproduces the host's suite 110 result here: 17 rows red, the same
HermeticViolation rows, activation/order and activation/failed-activates-nothing ending in KeyError('push'), and
pm/new-project-run refused `proposal_refused:intake_proposal:<digest>` (`110-a07-stage-agent.json`).

## 1. HermeticViolation: the SSH agent contacted by ssh-keygen -Y sign (keys/api-edge, keys/authority)

**Cause.** Not production code: suite 110 runs its rows on VELDO-0152's shared fixture
(proof/VELDO-0152/fixture.py), whose `sign_as` (the API edge's veldo-command signatures, and `journal_sign`, the
authority's veldo-journal signatures, which the fixture's inbox, presenter, settlement and suite 110's intake,
proposals and activation all use) ran `ssh-keygen -Y sign` with the inherited environment. Inside the fence
SSH_AUTH_SOCK names the fence's recording agent, which ssh-keygen contacts when it signs. These are exactly the
two keys the host named. Every ssh-keygen in 0143's range was then checked: 0143's production code runs none of
its own (the provisioner signs through the adoption effect's `_ssh_signer` and `R.AdoptionSigner`, the service
through `control_signer.sign_bytes`, all without the agent variables); suite 110's two key generations did not
use the quiet environment.

**Fix (e2e2bc1e).** The fixture's key generation and `sign_as` run with `quiet()` (SSH_AUTH_SOCK and
SSH_AGENT_PID removed, as suite 109's fixture does), and suite 110's two key generations with
`control_repository._quiet_env()`. The fixture is VELDO-0152's file, shared with suite 93; it is added to 0143's
footprint for this. Suite 93 is unchanged by it (`consumer-suites.json`).

**Row.** `provision/signing-no-agent`, after VELDO-0161's adoption/signer-no-agent: its own agent (a recording
socket where AF_UNIX is allowed, otherwise a path where nothing listens) and a stand-in ssh-keygen recording each
invocation's agent variables. A new project's whole path runs with that agent named: the owner's message signed by
the API edge, intake, route and proposal journaled, the provisioner (journal, adoption signer, take-on), and the
running service's take-on and new-project pass (activation, first team, first objective). The row requires the
API edge, the authority's journal and the adoption signer each to have signed there, no `-Y sign` started with an
agent variable, and nothing to have connected to its agent. (`-Y verify`, authority_contract's verifier, which
never opens an agent, still inherits the variables; it is not 0143's and the row judges signatures.)

**Falsifiers.**
- The fixture's `sign_as` without `quiet()`: the row is red by its own check, naming `('api-edge',
  'veldo-command'), ('authority', 'veldo-journal')` (`110-falsify-fixture-signer-row.json`); with the emulated
  agent, the fence raises in the same seventeen regions as at a07ad991 (`110-falsify-fixture-signer.json`).
- Registered mutation `newproject143-signer-reaches-agent` (control_repository's quiet environment returning the
  whole environment, which the adoption signer, the provisioner's journal and the take-on use): killed
  (`falsifiers-143.json`); by hand, the row named `('adoption-signer', 'veldo-enrollment'), ('authority',
  'veldo-adoption-take-on'), ('authority', 'veldo-journal')`.

## 2. activation/order and activation/failed-activates-nothing: KeyError('push')

**Cause.** A consequence of 1. The wire's violation log accumulates across fences, and `fenced()` raises at its
end when the log holds any violation. The first fenced row with a fixture signature (provision/adoption-path)
recorded one, so every later fence raised too: provision/step-failures' first case (`init`) raised on leaving its
fence, the region ended, and `failures` never received `push`, which both activation rows read. No record or
proposal shape changed: the rows and the product agree with the specification.

**Fix.** 1. With the agent emulated, both rows are green on the fixed branch and red with KeyError('push') at
a07ad991 and on the fixture-signer falsifier (`110-head-stage-agent.json`, `110-a07-stage-agent.json`,
`110-falsify-fixture-signer.json`).

## 3. pm/new-project-run: proposal_refused:intake_proposal:<digest>

**Cause.** The refusal's reason (the PM cycle record's `proposals[0].result`) is
`invalid_input:directory:no_remote`. The rebase's provision/handed-over row (d859b3db) creates a project named
`estuary` under the personal identity, and pm/new-project-run, which runs later, asks for a new project named
`estuary`. With no identity named, the proposal offers every configured identity; the personal identity's
`estuary` directory is now a Git repository, so it is offered for adoption, and it has no `origin` (the provisioner
pushes to the checked URL and sets none), which the proposal refuses by name. The product is right; the rows
collided. Round 1 never reached this here (the graph stage), and the rebase added the colliding row. The row also
expected exactly the three identities the suite configures, but its own `bind_paths` configures the factory
source's `fixture` identity first, and the payload correctly offers every configured identity.

**Fix (1b2fb86b).** provision/handed-over's project is `inlet`; pm/new-project-run expects the identities offered
to be every identity configured when the PM runs, the suite's three among them.

**Falsifiers.** At a07ad991 with the stage stood in, the row is refused `proposal_refused:...` (`110-a07-stage.json`).
On the branch, handed-over's project named `estuary` again: pm/new-project-run refused the same way
(`110-falsify-names-collide.json`). The three-identity expectation restored: the row is red on its payload check
(`110-falsify-three-identities.json`). Fixed, with the stage stood in: green (`110-head-stage-agent.json`).

## 4. Suite 66 authority/installed-assets

**Cause.** 0143's running service starts the provisioner from its installed directory, and the provisioner lays
Veldo with `init_scaffold`, so the installer's closure now reaches init_scaffold.py (control_service,
control_service_projects, control_project_proposal, control_repository_provisioner, init_scaffold: 140 modules,
132 at 8f749423). The scaffold did not lay init_scaffold.py, so an adopter's tree, where the installer runs too,
cannot derive the closure: `invalid_input:closure:absent: ... holds no init_scaffold.py (loaded by
control_repository_provisioner.py)`. Hiding the load from the closure would install a provisioner short of a
module it loads, which the closure exists to refuse.

**Fix (6d2880b2).** The scaffold lays `.veldo/init_scaffold.py`; control_service's closure docstring no longer says
it is not laid. Every composed pack now lays one file more (suite 24's measured counts, `consumer-suites-git.json`).

**Falsifiers.** Suite 66 needs the user manager before this row, so here `installed_assets.py` makes the row's own
comparison (`installed-assets.txt`): 8f749423 and the branch hold, a07ad991 and the branch with mutation
`newproject143-scaffold-not-laid` (registered, the `.veldo/init_scaffold.py` entry removed) are refused by name.
The registered case is not judged here (its row never runs here); the host's.

## Finding 143 and the falsifier driver

Eighteen mutations (`falsifiers-143.json`, worker mode as before): seventeen killed, each target row red on its
mutant and green at baseline; `newproject143-scaffold-not-laid` not judged here. The driver counted a target row
that never ran as killed (an empty result list); it no longer does (c1bf6dec). Baseline before and after: red only
on service/hand-off (AF_UNIX) and pm/new-project-run (the graph stage, here). Finding 161: `falsifiers-161.json`.

## Consumer suites

`consumer-suites.json`: 38 suites on an archive of a07ad991 and the branch at 6d2880b2; 36 the same. Suites 16 and
24 need a Git checkout: on clones (`consumer-suites-git.json`), 16 the same, 24 the same nine rows red (the nested
gate cannot run here), one of them embedding the files laid per pack, each one more.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 110_veldo_0143_new_project`: every row green, provision/signing-no-agent
   with its recording socket, service/hand-off and pm/new-project-run included.
2. `python3 scripts/selftest.py --suite 66_veldo_0047_authority`: every row green, authority/installed-assets
   included.
3. `python3 scripts/check_gate_mutations.py --finding 143`: 18 of 18 killed, newproject143-scaffold-not-laid
   against authority/installed-assets included.
4. `python3 scripts/check_gate_mutations.py --finding 161`: 55 of 55, unchanged.
5. `bash scripts/verify.sh`: the full gate.
