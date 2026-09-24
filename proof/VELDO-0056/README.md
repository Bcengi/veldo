# VELDO-0056 proof

Disposable landing candidate construction and failure isolation, PLAN-0019 revision 3 W41 (Release 1
stage 1). Branch `build-veldo-0056`, built on 8995740 and merged with origin/main 5ba4a02. Specification
status is unchanged; this proof is for independent review, and the canonical gate is the lead's.

## What landed

**The candidate** (`.veldo/lander.py`, engine copy identical). `GitLandOps` no longer checks out, merges
into or fetches into the caller's trunk. `sync_main` makes a dedicated workspace: a new repository
(`git init --template=`) whose object store borrows the caller's objects through alternates, as
VELDO-0042's worker clones do, with no worktree link, refs, index or configuration shared. It fetches
the published trunk once into the workspace and that exact commit is the watermark (with push disabled,
the caller's local trunk tip, read and never written). `reconcile` reads the unit's proof manifest at the
evidence commit (the build ref), requires the implementation commit it names to exist and to be an
ancestor of the evidence, merges the implementation, then the evidence, each with `--no-ff`, and derives
the projections (`specs/index.md`, by the candidate's own generator over the merged tree) in their own
commit. The candidate is required clean and to descend from the watermark, the implementation and the
evidence. Every Git invocation goes through one checked step: any failure refuses the candidate naming
the operation, and missing required evidence refuses it before anything is merged. The gate runs in the
candidate and is green only on exit 0 with `GATE: GREEN (<candidate>)`. `finalize` asks the policy and
only then pushes the exact candidate commit, fast forward only. The workspace is removed at the end of
every land (`Lander.land` calls the ops' `discard`). Every stage reports an event (operation, domain,
repository, unit, candidate, accepted input versions, outcome, named refusal, taxonomy); `status()`
counts and names the pending candidate.

**The policy.** A factory land is given `CandidatePolicy`, installed code outside the candidate (R50):
VELDO-0050's `resolve()` of the unit's bundle at the evidence commit, naming the implementation merged;
VELDO-0049's floor record handed off at exactly that evidence commit and proof digest with no unresolved
finding; VELDO-0052's publication decision with the candidate as the Gate's workspace. A pre-factory land
(no policy wired) asks the repository policy, `policy_check.py` at the candidate, whose range is exactly
watermark..candidate.

**Suite 04.** WARP-0704's real-Git lander rows now build the candidate, read it, and require the caller
untouched; each keeps its name and claim (footprint and History line added before any mutation).

## Rows (suite `67_veldo_0056_candidates`, 11 rows: 7 assertions and 4 `ran/` rows)

Real Git: a bare remote whose trunk is `mainline`, the caller's clone on `desk` while a second worktree
holds `mainline`, a builder clone, and a prior land pushed after the builds branched (it touches the
index, the capability catalog and README.md, and claims PORT 7). Real SQLite store with OpenSSH journal
and review signatures. Each factory unit goes the whole way: claim, a VELDO-0039 build dispatch whose real
child makes the implementation and evidence commits, the canonical gate captured and the proof accepted
(or refused), accept_build, assignment, a review dispatch whose real child signs its receipt, the recorded
review and the handoff. The suite's process is the receiver (no VELDO-0040 containment). The lander's Git
invocations are observed at its own boundary, which is also where one is made to fail.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `candidate/detached-held-trunk` | AC1 | `candidate-checks-out-trunk`, `candidate-checkout-ignores-other-worktrees`, `candidate-fetch-into-caller` |
| `candidate/whole-candidate` | AC1 | `candidate-evidence-not-merged`, `candidate-projection-skipped`, `candidate-watermark-from-caller-trunk` |
| `candidate/git-failures-refuse` | AC2 | `candidate-merge-failure-ignored`, `candidate-fetch-failure-ignored`, `candidate-missing-evidence-accepted` |
| `candidate/every-git-operation-checked` | AC2 | `candidate-projection-commit-unchecked`, `candidate-tree-lookup-unchecked`, `candidate-union-stage-read-as-empty` |
| `candidate/rejection-leaves-trunk` | AC3 | `candidate-trunk-moved-before-policy`, `candidate-gate-result-ignored`, `candidate-policy-refusal-ignored` |
| `candidate/named-policy-refusals` | AC3 | `candidate-proof-not-resolved`, `candidate-review-not-read`, `candidate-findings-not-counted`, `candidate-publication-not-decided` |
| `candidate/observations` | observability | `candidate-refusal-not-observed`, `candidate-unknown-classified`, `candidate-pending-hidden` |

What they run. **AC1**: a valid unit lands; when its gate is reached (before verification) the caller's
whole Git directory (HEAD, index, every ref, the worktree records), both worktrees' bytes and the remote
are byte-identical to before, every Git invocation aimed at the caller is `rev-parse`, `remote get-url`
or `config --get`, and the workspace is its own repository outside the caller, detached, borrowing
exactly the caller's objects. The candidate's first-parent chain is projection commit, evidence merge
(parents: implementation merge, evidence), implementation merge (parents: watermark, implementation),
watermark = the remote tip; every path each input changed is carried with that input's bytes, both
capability notes survive the union, and the projection equals `update_index.py` run by the suite over the
evidence merge's own tree, differing from both inputs' index. After the land the remote trunk is the
candidate and the local trunk is where it was. **AC2**: an unreachable remote and an absent remote trunk
(fetch), a README.md conflict (merge), a build with no proof, a proof naming a commit outside its history
and a missing build ref are each refused by name before the gate with nothing moved and the workspace
gone; then one real construction's 40 Git invocations (fetch, merge, rev-parse, cat-file, commit and the
rest, enumerated from the run itself) are each made to fail in a land of their own, and every one refuses
before the gate naming exactly that operation. **AC3**: a red gate (the build is green alone and red only
merged with the prior land), an invalid proof (the proof service refused a wrong artifact digest, so
nothing resolves), an unresolved finding (a blocking review), a rejected approval, and a repository
policy objection (pre-factory land) each refuse with exactly their own refusal and leave everything
byte-identical, while the valid unit built the same way lands.

## Red record

`red.py <commit>` runs the current suite with its one anchor pointed at that commit's lander.py.
`red-8995740.json`: the first red record, at the branch base (suite as of b20060f, every other module the
commit's own). `red-5ba4a02.json`: the final suite at the merged origin/main, whose lander.py is byte for
byte 8995740's, every other module the commit's own. In both all 7 assertion rows fail by assertion and
all 4 `ran/` rows pass: the pre-change `sync_main` checks out `mainline` in the caller, which the second
worktree holds, so every land raises `CalledProcessError` before any candidate exists.

## Mutations

22 registered as finding 56 in `scripts/check_teeth_mutations.py`; `mutations.py` drives them and writes
`mutations.json` with each diff in `mutations/`. Every named row is red by assertion with its region
completing, every row has three or four, and the unmutated control (a byte-identical lander through the
mutants' own substitution) is green on all 11 rows. The declared AC2 falsifier needs two edits (ignore the
conflict and skip the ancestry verification), because the fixed code guards the defect twice; with both
the conflicted build reaches the gate and is stopped only by the policy.

## Costs and the stage environment

Suite 67: 21.5 to 22.5 s. Finding 56 with 4 jobs: 131 s. Both were also run under the gate's mutation
stage environment (`env -i`, PATH of a python3 symlink plus /usr/bin and /bin, HOME and TMPDIR a new
/dev/shm directory, GIT_CONFIG_GLOBAL=/dev/null, GIT_CONFIG_NOSYSTEM=1): green. `observations.json`
(`drive.py`) keeps one run.

## Not done here, stated

Local trunk synchronization, the exact-old-tip compare-and-swap and the completion receipt are VELDO-0057
(`finalize` pushes the exact candidate fast forward only; with push disabled nothing moves); gate output
isolation and tree equality after the gate are VELDO-0058 (the stamp and events the gate writes stay in
the workspace, which is discarded); a kill or restart during construction and competing landers are
Release 2. The union merge of the append-only files is kept as WARP-0704 built it. Found, and outside this
footprint: `policy_check.py` (a protected path) treats a VELDO-0050 manifest's digest `spec_revision` as
stale, so the repository policy refuses every factory proof; the factory path therefore asks the
authority's policy, never the candidate's own policy code. The candidate's commits carry the identity the
caller passes, else the caller repository's own configured identity (the isolated Git profile reads no
global identity). The remote's fetch and push URLs come from the caller's configuration; other per-remote
settings in the caller's own local configuration are not carried into the workspace. Not run here: the
Mac and the full gate.
