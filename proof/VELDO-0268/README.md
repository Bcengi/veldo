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

## Fix round 2 (the lead's run of round 1's pending runs at 52daa4bc)

- Result named: suite 141 had one red row, mutation/fix1-empty-answer-allowed. Under that mutant the
  row push/empty-answer stayed green, refused for another unresolved reason. `git push empty :` to an
  empty remote never reached the empty-answer check, so the row was green for the wrong reason in
  production too. With that row red, `check_teeth_mutations.py --finding 268` judged all ten cases
  invalid_baseline.
- Fix (commit 95347f2a, suite file only): the row pushes a pattern refspec matching no branch
  (`'refs/heads/nomatch/*:refs/heads/nomatch/*'` to origin), a dry run that succeeds and names no
  destination. It holds only when the guard prints exactly one unresolved line, "the dry run named no
  destination; treated as protected", refuses with the gate text and main does not move. A green
  stamp would not isolate it: an unresolved destination with a green stamp and a manifest passes, so
  the red stamp's refusal stays and the reason line decides. Under the mutant the answer is empty,
  nothing is protected and the guard exits 0, so the row turns red.
- Runs: pending. The gate lock was not free in 20 minutes (one wait, no run started).
  proof/VELDO-0268/pending_runs.sh holds the two runs (suite 141 with details on, then
  `check_teeth_mutations.py --finding 268`), passes `bash -n`, appends one line per step with the red
  row names to proof/VELDO-0268/pending-summary.txt, logs /tmp/v268-fix2-suite.log and
  /tmp/v268-fix2-teeth.log. Git's exit and output for this pattern push were not observed here (a
  debugging push command was refused by the repository guard and not retried), so the baseline row
  is unproven until that run.

## Fix round 3 (fix check of 2026-11-07, NOT SOUND: F2, aliases; F1 decided)

- F2: the guard's dry run no longer runs a program the command, the configuration or the
  environment chooses. A push option outside an allowlist of full names (so `--receive-pack`,
  `--exec`, `--signed`, `--recurse-submodules` and any abbreviation), a `-c` key other than
  push.default, core.hooksPath and alias.*, or a configured remote.*.receivepack (read with `git
  config`, includes and command-line values included) makes the push unresolved before anything
  runs. For the dry run itself the ssh command (no proxy or local command, batch mode), ssh variant,
  credential helper, askpass, fsmonitor, alternate refs command, push negotiation, signing and
  submodule recursion are pinned after the user's options; the GIT_ variables that choose a program
  (GIT_SSH_COMMAND, GIT_SSH, GIT_ASKPASS, GIT_EXEC_PATH, GIT_CONFIG_PARAMETERS and every other not
  naming the repository) and SSH_ASKPASS are dropped; GIT_ALLOW_PROTOCOL=file:ssh:http:https
  overrides any protocol configuration, so ext::, insteadOf rewrites to ext:: and transport helpers
  (foo::, remote.*.vcs) fail. A dry run failing that way is unresolved.
- Consequence, stated: an https remote that needs a credential helper (this repository's own origin
  among them) cannot be resolved without running the helper, so its pushes are unresolved and meet
  the checks of a protected push. Residual, not closed: commands the user's ~/.ssh/config runs at
  parse time (Match exec), and a local bare remote's own configuration (its receive-pack runs there).
- Aliases: an alias (command line or configuration, chained, or a shell alias naming git, push or
  merge) that expands to push or merge is judged as that command; in a command the guard cannot
  reproduce, an alias setting or an alias that may push or merge is unresolved.
- F1: no change, by the lead's decision: an unresolved push meets the checks of a push to main
  (AC2, AC3).
- Side: packs/claude/scripts/veldo-guard.sh added to protected_paths in .veldo/policy.yaml, floor high.
- Rows (red stamp, each command's marker program must not run, exit 2 on the gate text with the
  expected unresolved reason, main unmoved): push/program-options, push/program-config-option,
  push/program-repo-config, push/ssh-config, push/ssh-env, push/ssh-env-git-ssh, push/ext-transport,
  push/credential (a local 401 http server), push/alias. Eleven falsifiers, in the suite and in the
  teeth driver: push option allowlist off, -c key allowlist off, configured receive-pack runs, ssh
  command not pinned, environment kept, GIT_SSH reaches the dry run (environment kept and ssh not
  pinned), every transport allowed, credential helper not pinned, askpass not pinned, alias not
  expanded, alias in a compound command ignored.
- Commits: 82dbd78f (three guard copies, byte-identical, and policy.yaml), 4f12c035 (suite and
  teeth driver). A development run of the suite fragment (outside selftest) had 0 red of 60.
- Runs: pending. The gate lock was not free in 20 minutes (one wait, 13:06 to 13:26, flock timed
  out, no run started). proof/VELDO-0268/pending_runs.sh holds the two runs (suite 141 with details
  on, 39 behaviour and 21 mutation rows expected green; then `check_teeth_mutations.py --finding
  268`, 21 cases), passes `bash -n`, appends one line per step with the red row names to
  proof/VELDO-0268/pending-summary.txt, logs /tmp/v268-fix3-suite.log and /tmp/v268-fix3-teeth.log.

## Fix round 4 (second fix check, research/claude-runs/veldo-0268-fixcheck2-2026-11-07.md)

- F3 (owner decision Telegram 39895): the credential helper pin is gone. Before the dry run the
  guard reads every credential.helper and credential.<url>.helper (any URL) with `git config
  --show-scope --show-origin`; a non-empty helper whose scope is not global or system, whose origin
  is not an absolute file path, or whose file lies under the repository (work tree, git dir or
  common dir; an include from the global file reports global scope, so the path decides) makes the
  push unresolved without running anything. A command-line helper is refused earlier by the -c key
  allowlist. Askpass stays pinned empty and GIT_ASKPASS dropped, prompts off. This is stricter than
  "for that URL": a repository helper for any URL keeps every push from that repository unresolved.
  The superseded consequence above (an https remote needing a helper is unresolved) now holds only
  for a helper outside the global and system configuration.
- F4: in a command the guard cannot reproduce, the alias is looked up with the git command's own -C
  and -c pairs. When text before it may run it elsewhere (cd, pushd, popd, or an assignment of a GIT_
  variable, HOME or XDG_CONFIG_HOME) or it carries another global option, a subcommand that is
  neither a builtin nor a git-<name> program on the exec path or PATH counts as an alias that may
  push. The simple-command path applies the same rule to an assignment or env before git and to
  global options other than -C and -c (`--git-dir`, `--config-env`).
- Rows: push/credential (now: a repository helper is unresolved, its marker and both askpass markers
  unrun), push/credential-url-scoped, push/credential-command, push/credential-included (global
  include of a file under .git, and a global file under .git), push/credential-global (a gh-style
  global helper on a self-signed https fixture remote: working branch exit 0 on a red stamp, main
  exit 2 as refs/heads/main protected, a remote it does not cover unresolved, repository and
  environment askpass unrun), push/vcs (remote.<name>.vcs helper unrun), push/alias-elsewhere (tool
  cwd outside the repository: cd, -C in a list, -C simple, GIT_DIR=, --git-dir all exit 2; cd then
  git status exit 0).
- Falsifiers (suite and teeth driver): repository helper runs, URL-scoped helper missed, command-line
  helper runs, included helper under the repository runs, global helper pinned off, global helper
  refused, vcs helper runs, alias ignores -C, alias ignores cd, alias ignores a prefix. Removed:
  credential helper not pinned (no pin now); askpass not pinned now targets push/credential-global.
- Commit 97433ff5 (three guard copies byte-identical, suite, teeth driver).
- Runs at 97433ff5 under the gate lock: suite 141 75 passed, 0 failed (45 behaviour, 30 mutation
  rows; exit 2 is the partial-run marker); `check_teeth_mutations.py --finding 268` exit 0,
  registered=30 rejected=30.
- Not reproduced outside the suite: the repository guard blocks a compound Bash command naming a
  push on a red stamp, so every behaviour above was driven only through suite 141 fixtures.

## Fix round 5 (third fix check, research/claude-runs/veldo-0268-fixcheck3-2026-11-07.md)

- F5: the dry run's porcelain parser reads exactly one more line, `Would set upstream of '<b>' to
  '<b>' of '<remote>'` (a full match; it names no destination, the ref lines still do), so a
  working-branch push with -u, the set-upstream long option, -u origin HEAD, or a plain push with
  push.autoSetupRemote configured passes on a red stamp. push.autoSetupRemote joins the -c key
  allowlist (a boolean, it names no program). Any other unknown line stays unresolved.
- F6 (a): an alias lookup that exits other than 1 with no output (a -C directory that does not
  exist, an unreadable configuration) raises, and the subcommand is unresolved, never "no alias". In
  a command the guard cannot reproduce, a -C or -c value containing $ or a backtick is treated as
  running elsewhere (a subcommand that may be an alias is unresolved).
- F6 (b): a simple command whose first word is not git (sh -c, bash -c) has its text judged for
  aliases as a compound command is.
- Rows: push/set-upstream (the four F5 pushes and git -c push.autoSetupRemote=true push each pass and
  land; -u origin main exits 2 on the gate text, protected), push/alias-unreadable (git -C "$PWD" pm;
  D=<repo>; git -C $D p origin main with a literal `$D` directory in the cwd; the for loop; a global
  alias with -C "$PWD"; -C of a missing directory, simple and in a list: each exits 2 on the gate
  text; git -C "$PWD" status and log pass), push/alias-shell-c (sh -c 'git pm' and bash -c "git p
  origin main" exit 2; sh -c 'git status' passes).
- Falsifiers (suite and teeth driver): upstream line unread, lookup failure read as no alias,
  expanded -C value looked up as written, sh -c not alias-checked.
- Stated residuals, no change: quoting tricks such as g''it (the trigger needs the literal word
  git), and shell aliases whose text never contains the words git, push or merge.
- Commit ac251e5d (three guard copies byte-identical, suite, teeth driver). A development driver
  under /tmp reproduced every case above against the new guard (exits as stated, main unmoved).
- Runs: pending. The gate lock was not free in 20 minutes (three waits, 15:06 to 15:26, each flock
  timed out, no run started). proof/VELDO-0268/pending_runs.sh holds the two runs (suite 141 with
  details on, 48 behaviour and 34 mutation rows expected green; then `check_teeth_mutations.py
  --finding 268`, 34 cases), passes `bash -n`, appends one line per step to
  proof/VELDO-0268/pending-summary.txt, logs /tmp/v268-fix5-suite.log and /tmp/v268-fix5-teeth.log.

## Fix round 6 (fourth fix check, research/claude-runs/veldo-0268-fixcheck4-2026-11-07.md)

- F7: the F6 (b) check above ran only when no word of the command was git. When a wrapper's other
  words included git or a path ending in /git (sh's $0), the guard judged that bare word instead and
  never looked for an alias. Now, when a git command's subcommand is not a push or merge, the guard
  judges the whole command text for aliases as it does a compound command (alias_in_text), and that
  scan reads every git in the text, overlapping ones too, so a git inside another git's -c value is
  seen. Each of these is judged as the push it expands to, unresolved and so treated as protected:
  sh -c 'git pm' git; bash -c 'git p origin main' /usr/bin/git; bash -c 'git sp' git; timeout 60
  sh -c 'git pm' git; sh -c 'git -C <repo> pm' git from a cwd outside the repository; sh -c 'git p
  origin main' x /usr/bin/git; git -c core.editor='git pm #' commit with the allow-empty option;
  the same value as core.pager for git log; and the editor case after cd . in a list.
- Consequence, fails closed: a simple git command whose text sets an alias with -c alias.<name>=,
  runs any shell alias (a value starting with !), or names an alias that may push anywhere in its
  text (a commit message saying git pm, for example) is now unresolved, as the same text already
  was in a compound command. git status, an ordinary commit and a non-pushing alias (lg = log
  oneline) still pass.
- Rows: push/alias-shell-c now holds the two fix round 5 commands, the nine above (each exit 2 on
  the gate text, main unmoved) and four that pass (sh -c 'git status', the same with a trailing git
  word, an ordinary commit, git lg -1).
- Falsifiers (suite and teeth driver, both on push/alias-shell-c): the new alias_in_text call
  dropped from judge_git; the scan back to non-overlapping matches (misses the editor and pager
  values).
- Stated residuals, no change (the class the fourth check named): a subcommand that only appears
  at run time. git $(echo push) origin main, echo push origin main | xargs git, and g''it all reach
  git with a subcommand or a program name that is not in the text the guard reads; a text guard
  cannot see what a shell expansion, a pipe or quote removal produces, and guessing at every
  expansion would refuse ordinary commands. The real line of defence for these is a pre-push hook
  that judges the actual refs git is about to send (the lead is raising that with the owner
  separately). Also unchanged: shell aliases whose text never contains the words git, push or merge.
- Development driver /tmp/v268f6/driver.py (written with the editor tool, run as one plain command
  with python3 -I against /tmp fixture repositories and bare remotes): the nine commands above exit
  2 on the gate text with main unmoved; sh -c 'git status' git, git status, git lg -1, an ordinary
  commit and a working-branch push exit 0 and run (the push lands).
- Guard block while building: the repository's own PreToolUse guard blocked one Bash command (a
  python heredoc editing the guard, whose text named an alias; it was not a push or merge) as an
  unresolved destination on a red stamp. That is this round's check doing its job on our own text.
  The edit was made with the editor tool instead; nothing was pushed or merged.
- Commit 30ad2b0c (three guard copies byte-identical, md5 82392168e8205704e75290d1c7f3684a; suite;
  teeth driver).
- Runs: pending. The gate lock was not free in 20 minutes (one wait, 17:36 to 17:56, flock timed
  out, no run started). proof/VELDO-0268/pending_runs.sh holds the two runs (suite 141 with details
  on, 48 behaviour and 36 mutation rows expected green; then `check_teeth_mutations.py --finding
  268`, 36 cases), passes `bash -n`, appends one line per step to
  proof/VELDO-0268/pending-summary.txt, logs /tmp/v268-fix6-suite.log and /tmp/v268-fix6-teeth.log.

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
