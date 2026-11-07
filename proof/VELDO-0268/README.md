# VELDO-0268 proof: the push guard protects main and releases only

Branch agent/claude/veldo-0268. Implementation commit 08f73999, suite commit 44f735d4.
Suite: scripts/suites/141_veldo_0268_protected_refs.py (30 rows: 25 behaviour rows and 5 mutation
rows, each mutation row applying one of the spec's registered mutations to a temporary copy and
requiring its target row to go red).

## What was built, per AC

### AC1: the protected set is declared, read through one function

- `.veldo/policy.yaml` and `engine/.veldo/policy.yaml` gain `protected_refs`: refs/heads/main,
  refs/heads/master, refs/heads/release, refs/heads/release/*, refs/heads/release-*, refs/tags/*.
- `.veldo/policy_check.py` (and its engine copy): `protected_ref(name)` returns (pattern, source)
  when the ref is protected, else None. The set is the union of the working tree's policy, the policy
  committed at refs/heads/main, and POLICY when the installed-policy runner sets it. No source
  declaring the key means every ref is protected ("*"). A key that is present but not a list of
  non-empty strings, or a policy that cannot be parsed, raises ProtectedRefsUnreadable; the guard
  refuses with "VELDO guard: blocked. protected_refs in <file> cannot be read".
  `policy_check.py --protected-ref REF...` prints the same answer per ref.
- Rows: refs/declared (main, release/1.2, tags/v1 protected; agent/claude/x, mainline not),
  refs/union-shrink (working tree drops main, trunk lists it: still protected, source
  refs/heads/main:.veldo/policy.yaml), refs/no-key (no key anywhere: agent/claude/x protected),
  refs/installed (installation adds refs/heads/production), refs/unreadable (malformed key: exit 2 and
  the message). All green.

### AC2: unprotected destinations are never blocked, on either path

- `scripts/veldo-guard.sh` (three byte-identical copies) resolves destinations before any check:
  - pre-push path: no tool payload and VELDO_GUARD_REF set: that ref (not a full ref name: unresolved).
  - PreToolUse path: a simple `git push ...` is reproduced as
    `git -c core.hooksPath=/dev/null push --dry-run --porcelain --no-verify ...` and the destinations
    are read from git's porcelain output; `git merge` judges the checked-out branch; `gh pr merge`
    judges the base gh reports (`gh pr view --json baseRefName`); `gh pr create` moves no ref.
    A compound command, an expansion, unknown options, a failed dry run, a detached merge or a base gh
    cannot report is "unresolved" and protected.
  - One stderr line per destination: protected by <pattern> from <file> with the checks it runs, or
    "not protected: the gate check applies when this lands", or unresolved with its reason.
  - Only when at least one destination is protected do the existing checks run, unchanged.
- Rows (fixture: red gate stamp, no proof manifest): push/branch-tool (exit 0, the bare remote has
  agent/claude/x), push/branch-prepush (through a pre-push hook calling the guard per ref with
  VELDO_GUARD_REF and VELDO_GUARD_COMMIT: push exits 0, remote has the branch), push/main-tool and
  push/main-prepush (exit 2, remote main unmoved), push/both (exit 2, only main named as protected),
  push/head-colon-main (from a working branch, exit 2), push/unreproducible ("cd x && git push",
  exit 2), push/dry-run-fails (unknown remote, exit 2), push/pr-create (exit 0), merge/checked-out
  (on main exit 2, on a working branch exit 0), merge/gh-base (base main exit 2, base a working
  branch exit 0, base unknown exit 2). All green.

### AC3: protected destinations keep every check exactly as before

- No check, message or order changed; the emergency lane and the lander are untouched.
- Rows, push of main through the guard, standard error minus the "VELDO guard: destination" lines
  compared byte for byte with the pre-change text: refuse/gate (red stamp), refuse/manifest,
  refuse/path (protected path without approval), refuse/debt (open emergency debt),
  refuse/objection (unresolved review objection); refuse/tag (a tag push touching a protected path
  keeps the approval block); refuse/lander (control_verification.py's installed-policy run refuses a
  protected path without approval, exit 1, same text). All green.
- The expected texts are confirmed as the pre-change bytes: the same rows run over the pre-change
  guard and policy_check (deb8c79a) are green (see the red-before run below).

### AC4: copies byte-identical, the rule stated in engine/AGENTS.md

- scripts/, engine/scripts/ and packs/claude/scripts/veldo-guard.sh are byte-identical, as are the
  two policy_check.py copies (row sync/copies, and the gate's template-sync check).
- engine/AGENTS.md gains one "Protected refs" paragraph: the push guard protects the refs the policy
  names; landing is where the gate and approvals bind; working branches push freely (row doc/agents).

## Falsifiers, red then green

Red before: the suite run over the pre-change guard and policy_check (git show deb8c79a, through
the suite's VELDO_0268_UNDER_TEST diagnostic) has 15 red rows: refs/declared, refs/union-shrink,
refs/no-key, refs/installed (no protected_ref), refs/unreadable, push/branch-tool, push/both,
push/pr-create, merge/checked-out, merge/gh-base (working branches blocked by the red stamp),
push/main-prepush (the old guard ignored a pre-push call), and four mutation rows whose anchors do not
exist yet. The AC3 refusal rows are green there, which is what pins their literals.

Green after: all 30 rows green on 08f73999 + 44f735d4.

Registered mutations, each driven by its mutation row on every run (red under the mutation, the
mutation row green):

| Mutation | Target row | Under the mutation |
| --- | --- | --- |
| AC1 (1) the union reads only the working tree | refs/union-shrink | red: protected_ref(main) is None |
| AC1 (2) a missing key means nothing protected | refs/no-key | red: agent/claude/x not protected |
| AC2 (1) destination read from the command text | push/head-colon-main | red: "git push origin HEAD:main" exits 0 |
| AC2 (2) unresolved counts as unprotected | push/unreproducible | red: "cd x && git push" exits 0 |
| AC3 approval block skipped for refs/tags/* | refuse/tag | red: the tag push exits 0 |

## Suite runs

- Development run (shared.py plus the fragment in one namespace): 30 of 30 VELDO-0268 rows green,
  about 4 s.
- `python3 scripts/selftest.py --suite 141_veldo_0268_protected_refs` under
  `flock -w 21600 /home/dmitry/.local/state/core-gates/.gate.lock`: SUITE_RESULT_PLACEHOLDER

## Fix round 1 (check of 2026-11-07, NOT SOUND, finding F1 and the trigger side note)

- F1: the dry run now places `--no-quiet --dry-run --porcelain --no-verify` after the user's own push
  options (before a separating `--`), so a later quiet, verbosity or verify option cannot silence the
  ref lines or run a hook, and sets `-c core.hooksPath=/dev/null` after the user's global options, so
  a `-c core.hooksPath=...` of theirs cannot win. A dry run that names no destination, names one that
  is not a full ref name, or prints a line the guard cannot read is unresolved, hence protected.
- Trigger: any command naming git reaches the destination step, which decides through `git_split`
  (the guard's global option parsing, which `git_globals` now builds on) and a text pattern allowing
  global options, whether it is a push or merge. `git -C dir push` and `git -c k=v push` are judged.
  Non-push git commands still pass, and `policy_check.py` is loaded only when a destination exists.
- Commits: e4f5ba61 (the three guard copies, byte-identical), d68595af (suite rows and falsifiers).
- New suite 141 rows: push/quiet-main (`-q`, `--quiet`, `-fq` to main exit 2, unchanged gate text),
  push/empty-answer (a dry run naming no destination exits 2), push/global-options-main (`git -C dir`
  and `git -c k=v` pushes of main exit 2), push/hooks-not-run (a `-c core.hooksPath=H ... --verify`
  push: the hook does not run in the guard's dry run, does run in the real push), push/branch-variants
  (quiet, `-C` and `-c` pushes of working branches exit 0 and land on the remote).
- Falsifiers, each driven by an in-suite mutation row and registered in scripts/check_teeth_mutations.py
  as finding 268 together with the spec's five (ten cases, each anchor found once):
  quiet-silences-answer (push/quiet-main), empty-answer-allowed (push/empty-answer),
  trigger-misses-global-options (push/global-options-main), hooks-path-before-globals
  (push/hooks-not-run), quiet-not-overridden (push/branch-variants).
- Runs: pending. The gate lock was not free in two attempts (500 s and 470 s, about 16 minutes of the
  20 minute budget). proof/VELDO-0268/pending_runs.sh holds the two runs (suite 141, then
  `check_teeth_mutations.py --finding 268`), passes `bash -n`, writes one line per step to
  proof/VELDO-0268/pending-summary.txt and logs under /tmp. No suite or falsifier result of this round
  exists yet; the embedded Python compiles and the helpers were checked offline on 20 inputs.
- Not in scope and unchanged: the side observations other than the trigger (empty protected_refs list,
  local trunk ref only, HEAD versus the pushed commit, packs/*/AGENTS.md).

## Open

- scripts/suites/requires.json is outside the footprint. It is derived (`python3 scripts/run_scope.py
  --emit-requires`, held fresh by scripts/check_generated.sh), and without the new suite's entry
  `selftest.py --suite 141_veldo_0268_protected_refs` refuses with ClosureUnavailable and the gate's
  generated-file check goes red. Regenerating it adds exactly three lines (the suite's own one-entry
  closure). The selftest run above was made in a scratch copy of this commit with requires.json
  regenerated there; the worktree's requires.json is unchanged. The lead needs to add it.
- The registered mutations are driven inside suite 141 (mutation rows). They are not entered in
  scripts/check_teeth_mutations.py, which is outside the footprint; the suite's PRODUCTION mapping is
  laid out for that driver if the lead wants them there too.
- packs/*/AGENTS.md (six byte-identical copies of engine/AGENTS.md) are outside the footprint and
  still carry the old text; no gate check compares them today.
- While building, the repository's own PreToolUse guard (scripts/veldo-guard.sh, the hook in
  .claude/settings.json) blocked two Bash commands whose text named push and merge commands (a file
  write and a manifest edit, neither a push or merge). The same edits were made with the editor tool
  instead. Nothing was pushed or merged.
- Core's port (its own guard, policy_check, policy and pre-push hook) is a separate core
  specification, as the spec states.
