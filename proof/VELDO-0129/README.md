# VELDO-0129 proof

The installed LiveLoop and LiveReviewer use an owner supplied worker configuration to
construct the Runner, proof service and floor authority. No build or review callable is
required. The factory loop is unchanged and belongs to VELDO-0154.

The suite is `82_veldo_0129_worker_wiring`. It installs the reference distribution through
init_scaffold, overlays the production module under mutation, and drives the public entry
points. Its SQLite store, journal and reviewer signatures, account registrations, claims,
reservations, Git commits, isolated clones, receiver processes, containment groups and
custody restrictions are real. Each run uses a fresh dispatch and clone. The receiver
records the group before releasing the worker. Collection neutralizes the used clone's
Git configuration before reading it and imports its objects without moving the source ref.

The engines are fixture executables. Claude is pinned with the production pin operation;
Codex is qualified as a vendor package. Their output uses the recorded CLI event table in
proof/VELDO-0062/cli-formats.json, Claude's initialize table in
proof/VELDO-0155/claude-baseline.json, and Codex's installed event and item tables. The suite
checks every emitted line. No real engine or model runs, no real credentials are read, and
no remote host is contacted. This proves adapter wiring on the landed qualification,
not a new qualification of vendor binaries or model quality.

## Criteria and rows

| Criterion | Rows | Observation |
| :--- | :--- | :--- |
| AC1 | build/claude, build/codex | Default builds launch real contained processes in accepted clones, deny key access, return dispatch-bound commits and proof, and record groups before engine work. |
| AC1 | build/configuration, installation/assets | Missing configuration refuses; the scaffolder installs the runtime and its existing floor dependencies; engine copies match; fixture output follows the recorded formats. |
| AC2 | review/loop-claude, review/loop-codex, review/reviewer-claude, review/reviewer-codex | Both entry points and both engines receive exactly the assignment, committed spec, source diff and accepted proof. The process and reviewer identity differ from the builder. Signed verdicts answer that subject. |
| AC2 | review/independence-policy | Self review refuses and the accepted critical policy requires two distinct reviewers. |
| AC3 | outcome/nonzero, outcome/missing-build, outcome/missing-review, outcome/malformed-review | Failed exits, absent result artifacts and wrong review subjects refuse. A zero exit cannot manufacture a verdict. Both engines are exercised. |
| AC3 | outcome/missing-usage, outcome/reservation | Build and review retain unknown token exposure and their invocation charge. Exhausted allowances prevent process invocation. |
| AC3 | proof/authority, proof/empty-acceptance | Stored contextual proof is required by the floor. A committed manifest alone and a hook returning no acceptance cannot offer built work. |
| AC3 | source/no-completion | Build and review leave the source ref unchanged and create no completion receipt. |

Gate observations in this suite are explicit fixtures at the proof service boundary. Gate
execution and isolation remain covered by VELDO-0058 and its regression suite. The test does
not claim a gate pass. The receiver and runtime both use the configured host trust for the
eligibility Gate's settlement trust.

## Reproduction and negative controls

`drive.py` with the red option and `a4769f68` extracts that commit using git archive and
runs the current suite against its unchanged production code. `red-at-a4769f68.json` records
all 18 rows false by assertion, one report per name. The base's installed build seam refuses
because no worker is wired. No production file in the extracted tree is edited.

Finding 129 registers eight unique mutations. `mutations.json` retains the exact old and
new snippets, source and mutant digests, all row observations and each named rejection.
The declared falsifiers are worker129-build-unwired, worker129-builder-context-reused and
worker129-exit-manufactures-review. Additional mutations remove subject validation, the
empty-proof refusal, pre-launch group recording, runtime installation and required stored
proof. The driver uses temporary copies and checks that failures are assertions rather
than fixture setup errors.

## Installed configuration

Pass a receiver JSON path as `configuration` to LiveLoop, LiveReviewer or Dispatcher, or
install it as `.veldo/worker.json` in the authority checkout. The receiver fields retain
their existing meaning. Add `clones` with clone and cache roots, protected directories and
engine directories. Add `work` with `builder`, `reviewers`, `candidates` and `projections`.
Each role names `identity`, `account`, `adapter`, `seconds` and `configuration`; reviewers
also name `signing_file`. Signing files stay outside clones, in the protected directory.
The configured local adapter starts with control_keys_custody.confined and the installed
clone entrance, followed by the qualified engine according to its existing command protocol.
No new role capability policy is introduced.

Builds commit implementation and evidence first, then the proof manifest. The final answer
is JSON with the final commit and proof. A review's final answer is a subject-bound
veldo.review_receipt/v1 body with verdict and findings. The authority signs that observed
body under the assigned review identity; the floor independently checks the signature,
assignment and receiver artifact. Call LiveLoop.close or Runtime.close when the synchronous
session ends. Failed or uncertain dispatches retain the existing Runner obligations.

## Validation limits

Selected selftest runs deliberately exit 2 when all assertions pass. They are partial
regression results, not an aggregate gate stamp or passed unit-evidence record. The full
repository gate was not run, as requested. The final validation record lists the selected
suites and validator result. Independent review and landing remain outstanding.
