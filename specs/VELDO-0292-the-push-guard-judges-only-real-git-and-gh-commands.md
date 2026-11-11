---
schema: veldo.spec/v1
id: VELDO-0292
title: The push guard judges only the git and gh commands the shell would run, so a mention of one in a comment, or in a quoted string or heredoc body given only to plain text tools in a command that names no git or gh, is not refused, while a git command the guard cannot resolve stays protected
status: ready
risk: high
risk_areas: [auth_security]
owner: dmitry
human_approval: required
lane: standalone
depends_on: [VELDO-0268]
placement: [enforcement]
protected_paths: ["scripts/veldo-guard.sh", "engine/scripts/veldo-guard.sh", "packs/claude/scripts/veldo-guard.sh"]
footprint:
  - "scripts/veldo-guard.sh"
  - "engine/scripts/veldo-guard.sh"
  - "packs/claude/scripts/veldo-guard.sh"
  - "scripts/suites/141_veldo_0268_protected_refs.py"
  - "scripts/suites/manifest.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0292-the-push-guard-judges-only-real-git-and-gh-commands.md"
  - "specs/index.md"
  - "proof/VELDO-0292/**"
behavior_bearing: true
observability:
  logs: >
    A command whose every mention of git or gh is data prints nothing and passes. When the guard
    refuses a command that is not one simple git or gh command, its existing "destination unresolved"
    line now ends with what it found: the matched text, cut at 120 characters, and where it sits (a
    command of a list or pipeline, the argument or input of a program that is not a plain text tool
    with the program named, text in a command that also names git or gh, or text the guard does not parse with
    the construct named). The incident's message gave the builder no way to see which
    words had been read as a command.
  metrics: >
    None added.
  traces: >
    None added.
  error_taxonomy: >
    No new refusal and no new exit code. Fewer commands reach the existing "destination unresolved"
    refusal. A command the scanner cannot read is judged on its whole text as today, and an error
    inside the destination check still ends in the existing "the destination check failed; treated as
    protected" line.
acceptance_criteria:
  - id: AC1
    text: >
      The guard reads a command with one scanner over a defined subset of the shell grammar (Design)
      and judges only its live text: the command with each comment, and each heredoc body and quoted
      string that is data, replaced by a placeholder word. The existing judgment then runs on the live
      text unchanged. A command with the incident's shape is allowed: it writes a helper script under
      /tmp from a heredoc, runs the script and deletes it, and its only mention of a push is a
      description string inside the heredoc body.
    falsified_by: >
      Suite 141 row text/incident, on a fixture with a red gate stamp and no proof manifest. The command
      is three lines: cat with a quoted heredoc delimiter writing a Python file under the fixture's
      temporary directory, whose body assigns a description string containing the words git push;
      python3 running that file; rm deleting it. The guard exits 0 and prints no "VELDO guard:
      destination" line. The row then runs the command under bash with a recording git and gh first on
      PATH, and the record stays empty. At 646ff7c8 the row is red: the guard exits 2 with "the command
      is not one simple git or gh command". Registered mutation guard292-heredoc-body-live (heredoc
      bodies stay in the judged text) turns the row red.
  - id: AC2
    text: >
      Text the shell would execute is judged as before, and a git or gh command the guard cannot
      resolve stays protected. Each of these is refused on a red gate stamp exactly as at 646ff7c8: a
      push given as a string to sh -c or bash -c, to eval, or on the standard input of a shell; a push
      as one command of a pipeline or list; a push held in a variable that is then run; a push inside a
      function body; a push behind a shell alias or a git alias; a push given as code to an
      interpreter; a push stored by export, read or printf -v and run by a later shell; a git alias
      whose text names a push, written to a configuration file by a plain text tool and used later in
      the same command; and a command that carries
      both a quoted mention and a real push. The refusal line names what the guard found and where.
    falsified_by: >
      Suite 141 rows, each requiring exit 2, the gate refusal text, the remote's main unmoved, and one
      "destination unresolved" line that quotes the matched text and names its position.
      live/shell-string: sh -c and bash -c with the quoted string git push origin main, the same under
      timeout, eval with that string, bash reading it from a quoted heredoc, and a shell alias defined with
      it and then used. live/pipeline: true piped into git push origin main, the quoted string echoed into
      sh, and the quoted string echoed into xargs env. live/outside-subset: the string assigned to a
      variable that is then the command word, and a function whose body pushes and is then called.
      live/interpreter: python3 -c calling os.system with the push, perl -e calling system with it, awk with
      a BEGIN block calling system with it, and python3 reading a quoted heredoc that calls os.system with
      it. live/stored: export of a variable holding the push, then sh -c running that variable in double
      quotes; read of the push from a quoted heredoc, then the same; printf -v of the push, then the same.
      live/config-write: printf of an alias section mapping p to !git push origin main, appended to
      .git/config by a redirection, then git p; the same section echoed into tee -a .git/config, then
      git p; the printf form on one line and git p on the next; the printf form, then git named by its
      absolute path with p; the printf form, then sh -c with the quoted string git p; the printf form appended to the path written as '.g''it/config', then g\it p; the same, then sh -c with the quoted string g\it p. live/mixed: echo of a quoted mention followed by a real push of main after a cd.
      live/quoted-command-word: true && 'git' push origin main, and true && g\it push origin main.
      At 646ff7c8 live/quoted-command-word is red because the guard exits 0. Every other row is red only
      because the line does not yet say what was found; the exit code and gate text already hold. A git
      alias behind a push is covered by the existing push/alias and push/alias-shell-c rows.
      Registered mutations: guard292-runner-strings-data (a shell, eval and alias count as plain text
      tools) turns live/shell-string and live/pipeline red; guard292-unparsed-is-data (a command outside the
      subset has its quoted strings removed anyway) turns live/outside-subset red;
      guard292-data-set-any-program (every program counts as a plain text tool) turns live/interpreter and
      live/stored red; guard292-git-list-data (text in a command that also names git counts as data) turns
      live/config-write red; guard292-git-list-exact-word (the rule fires only on a word that is exactly
      git or gh) turns live/config-write red; guard292-git-list-per-line (the rule looks only at the line
      that names git) turns live/config-write red; guard292-git-list-quoted (the rule tests the text without deleting quotes and backslashes) turns live/config-write red; guard292-list-tail-data (once a command of a list holds data, the commands
      after it are data too) turns live/mixed red; guard292-command-word-raw (the live text keeps command
      words as written) turns live/quoted-command-word red. Every row and registered mutation suite 141
      carried at 646ff7c8 still passes; an anchor the change moves is pointed at the same defect again.
  - id: AC3
    text: >
      A mention of git or gh in a comment, or in a quoted string or heredoc body that the Design calls
      data, is never a git command. A command whose every mention is one of these is
      allowed whatever the gate stamp says, including when it also uses plain variable expansions in its
      arguments.
    falsified_by: >
      Suite 141 rows on the red stamp fixture, each requiring exit 0, no "VELDO guard: destination"
      line, and an empty record from the recording git and gh when the command then runs under bash.
      text/quoted: echo and printf of a double quoted sentence containing git push origin main; grep for
      the single quoted words git push in a fixture file; tee writing them to a file under the fixture's
      temporary directory; echo of the quoted sentence beside an argument that expands HOME.
      text/heredoc-stdin: grep reading a quoted heredoc whose body holds the words, and cat of an
      unquoted heredoc whose body holds them and no
      expansion. text/comment: ls followed by a comment reading git push origin main, alone and after a
      list of two commands. At 646ff7c8 all three rows are red: the guard exits 2 on each command.
      Registered mutations: guard292-quoted-live (quoted strings stay in the judged text) turns
      text/quoted red; guard292-comment-live (comments stay in it) turns text/comment red.
  - id: AC4
    text: >
      The scanner never calls text data that bash would run. Each command of a fixed corpus places a
      real push of main where bash runs it, beside a construct a careless scanner would misread, and
      the guard refuses every one.
    falsified_by: >
      Suite 141 row live/scanner-edges on the red stamp fixture. The corpus: true a#; git push origin
      main (a # inside a word is not a comment); a comment ending in a backslash, with the push on the
      next line; echo 'a\'; git push origin main; echo '\' (a backslash inside single quotes is
      literal); cat <<EOF; git push origin main, then one body line and EOF (the rest of a heredoc's
      command line is commands, not body); cat <<-EOF, one body line, a tab followed by EOF, then the
      push on the next line (<<- strips leading tabs from the delimiter line). Each must exit 2 with the
      gate refusal text. The row also runs each command under bash with a recording git first on PATH
      and requires the record to hold the push, which proves bash does run it. At 646ff7c8 the row
      already passes, because the guard refuses any text with the words of a push. It holds the line
      the scanner must not cross, and its teeth are the mutants. Registered mutations, each turning the
      row red: guard292-hash-in-word-comment (a # anywhere starts a comment), guard292-comment-continues
      (a trailing backslash continues a comment), guard292-single-quote-escape (a backslash escapes
      inside single quotes), guard292-heredoc-line-is-body (the body starts right after the
      delimiter word), guard292-heredoc-dash-ignored (<<- is read as <<).
  - id: AC5
    text: >
      A git or gh command whose only mention of a push or merge is a message or body it stores is
      allowed whatever the gate stamp says. Every other argument of a git or gh command stays live.
    falsified_by: >
      Suite 141 rows on the red stamp fixture. text/message, each requiring exit 0, no "VELDO guard:
      destination" line, and no push or merge in the record of a recording git and gh when run under
      bash: git commit -m with a message naming git push origin main; git tag -a v0 -m with the same;
      git log with a grep pattern of the words git push; gh issue comment 1 -b with a body naming them;
      gh pr comment 1 -b with the same; git add -A followed by && and git commit -m with the same
      message. At 646ff7c8 the row is red: the guard exits 2 on each.
      live/git-args, each requiring exit 2 and the gate refusal text: git rebase main -x with the
      quoted string git push origin main; git -c core.pager with that string, then log; git commit -m x
      followed by && and a real push of main. Registered mutations: guard292-message-not-data (the
      message rule is off) turns text/message red; guard292-message-not-data-in-list (the message rule
      applies only to a command that stands alone) turns text/message red; guard292-git-args-data (every quoted argument of a
      git command is data) turns live/git-args red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The guard again refuses any command whose text contains a push or merge phrase, as
  at 646ff7c8. Nothing stored changes shape, so nothing needs migrating.
---

## Intent

The guard must stop refusing commands that only talk about git.

On 2026-11-10 a builder ran one Bash command that wrote a helper script to /tmp, ran it and deleted it.
No git command ran. A description string inside the script contained the words "git push", and the
guard refused the whole command with "destination unresolved: the command is not one simple git or gh
command, so it cannot be reproduced; treated as protected" and then "blocked. The canonical gate is not
green for HEAD". The owner was asked whether the guard should keep blocking commands that only contain
"git push" as text. His answer, Telegram 40683: "No don't block".

A refusal for a real push to main has to stay exactly as strict. So the guard has to tell a command the
shell would run from words that are only data, and it has to do that without a list of harmless
phrases.

## Context

VELDO-0268 made the guard judge only protected destinations and take the destination from git itself.
This spec amends one part of it: how the guard decides that a Bash command contains a git or gh command
at all. VELDO-0268 AC2 says a command the guard cannot reproduce counts as a push to a protected ref;
that stays, and this spec defines which text is a command.

Today, in the Python embedded in scripts/veldo-guard.sh:

- words_of splits the command with shlex and returns the words only for one simple command. A newline,
  a pipe, a list, a redirection or a `$` gives None.
- names_push_or_merge then searches the raw text with the PUSHISH pattern. Any occurrence of the words,
  quoted or not, makes the command unresolved. This is the incident: the heredoc made the command
  multi-line, and the description string matched.
- The same search runs for a simple command whose first word is not git, so echo of a quoted sentence
  that mentions a push is refused, and so is a comment after ls, because the pattern reads the raw text.
- alias_in_text scans the raw text for git aliases the same way.

The three copies of the guard (scripts/, engine/scripts/, packs/claude/scripts/) are byte-identical and
all three are protected paths in .veldo/policy.yaml, so this change needs the owner's approval at
landing.

## Design

Three ways to read the command were weighed.

Bash's own parser in no-exec mode. `bash -n` reads a command without running it, but its only answer is
whether the text parses. For a valid command it prints nothing, so the guard learns nothing about where
a git word sits. The known way to get structure back out of bash is to wrap the text in a function
definition and print the function with `declare -f`. That runs whatever the text puts after a closing
brace; a harmless probe on this host printed its injected echo. The guard runs nothing the command
chooses (VELDO-0268 fix round 3), so bash cannot be the parser.

shlex alone. It turns one simple command into words, which is its job in the guard today. It knows
nothing about heredocs, lists or substitutions, so it cannot say that a line is a heredoc body.

The guard's own scanner over a defined subset. This is the choice. The scanner lives in the guard's
embedded Python, uses the standard library only, and runs before the existing judgment. It either reads
the whole command inside the subset and returns its live text, or it gives up and the whole text is
judged as today. Giving up is one-sided: a construct the scanner does not read leaves the command
judged as today. A mistake inside the subset is not. If the scanner ends a heredoc later than bash
does, takes a `#` inside a word for a comment, or reads a backslash inside single quotes as an escape,
it calls a real command data and the guard passes it. AC4 holds the scanner to bash's own reading on
exactly these cases. The existing judgment,
with its dry run, alias lookups and reasons, runs on the live text and is not rewritten. The live text
writes each command word after quote removal, so 'git', "git" and g\it in a list or pipeline reach the
existing judgment as git.

The subset is the part of the shell grammar POSIX fixes:

- simple commands joined by newlines, `;`, `&&`, `||`, `|` and `&`;
- words built from unquoted text, single quotes, double quotes and backslash escapes, including a
  backslash before a newline;
- plain `$NAME` and `${NAME}` expansions in arguments;
- assignments before a command or on their own;
- redirections with a word target, and heredocs (`<<` and `<<-`) with a quoted or unquoted delimiter;
- comments.

Everything else is outside it and sends the whole command to today's judgment: command substitution
with `$(` or backticks, process substitution, arithmetic, `$'...'` strings, here-strings, subshells,
brace groups, function definitions, the reserved words (if, for, while, until, case, select, function,
time, coproc, `!`, `[[`), a command word that contains an expansion or a glob character, and an
unterminated quote or heredoc.

Inside the subset, text is data, and is replaced by a placeholder word, when the shell cannot execute
it and no program it reaches can either:

- A comment is data.
- A heredoc body or a quoted string is data when the shell does not expand it (single quotes; double
  quotes with no `$` or backtick; a heredoc with a quoted delimiter, or with no `$` or backtick in its
  body), it is not part of an assignment's value, and every command in its pipeline is a plain text
  tool.

A plain text tool is a command whose command word, after quote removal and taken by its last path
component, is in one fixed set in the guard of programs that never execute their arguments or their
input: echo, printf, cat, tee, grep, egrep, fgrep, head, tail, wc, sort, uniq, cut, tr, ls, mkdir,
touch, rm, cp, mv, chmod, ln, diff, cmp, sha256sum, base64, test, `[`, true, false and `:`. printf
with -v is not one, because it assigns a variable.

Every other program keeps its text live: the shells and eval, the wrappers (timeout, nohup, env, xargs,
sudo, ssh), the interpreters (python3 -c, perl -e, awk, node -e, a heredoc on an interpreter's standard
input), sed with its e command, make reading a makefile from standard input, and the builtins that keep
text for later (export, declare, typeset, readonly, local, read, mapfile). None of them needs to be
named. A name missing from the set can only cause a refusal. Adding a name is a change to a protected
path, and its reviewer checks that the program cannot run text.

Checking the whole pipeline covers a string echoed into a shell or an interpreter. Assignment values
stay live so a string stored in a variable and run later is still seen.

When git or gh appears anywhere in the command outside comments and the strings that would otherwise
be data, no quoted string or heredoc body anywhere in the command is data, except the message values
named in the next paragraph. The test runs on that text with every quote character and every backslash
deleted, so 'g'it, "gi"t and g\it count as git at any depth of quoting. It counts wherever no letter,
digit or underscore stands right before or after it: as a command word, as part of a path such as
/usr/bin/git or .git/config, as an argument, and inside a string given to a shell, a wrapper or an
interpreter. The command is the whole text of the Bash call, across all its lines. A command that runs
git can use a file it writes, such as a git alias appended to .git/config, a hook under .git/hooks or
a script git runs, so nothing it writes is data, whatever path it writes to.

Git and gh keep their text live with one exception: text they store and never run. In a simple command
whose words after quote removal start with git, with no global option other than -C, and whose
subcommand is commit, tag, notes or stash, the value of -m and of its long spelling, message, is data.
In git log, git show and git rev-list, the value of the grep option is data. In a simple command
starting with gh whose next two words are issue create, issue comment, issue edit, pr create, pr
comment, pr edit, pr review or release create, the values of -t, -b and -n and of their long
spellings, title, body and notes, are data. This holds for such a command standing alone or as one
command of a longer command. Any other argument, any -c option and any alias keep the command live as today.

The allowed rows run their command under bash with a recording git and gh, so the suite checks on each
host that text the scanner called data is text the shell did not run.

## Out of scope

- Git's and gh's argument grammar beyond the message options the Design names. Every other argument of
  a git or gh command stays live.
- Compound commands and substitutions. A command with a loop, a conditional, a function or `$(` and a
  mention of a push is still refused, as today.
- Forms the guard already lets through at 646ff7c8, with one exception. A git or gh command word
  written with quotes or a backslash inside a list or pipeline passes at 646ff7c8, because neither
  PUSHISH nor alias_in_text matches it. The scanner removes those quotes, so the live text closes it.
  The commands this spec newly allows that do run git are named in What the reviewer judges.
- The git pre-push path, the checks a protected destination runs, policy_check and the lander.
- Core's copy of the guard, which changes through a core specification as VELDO-0268 describes.
- The second false hit of the same night, in core. Core's scripts/veldo-guard.sh triggers on the
  pattern git (push|merge), which matches git merge-base, and has no destination step, so a read-only
  git merge-base was refused for a stale .veldo/last_verify. This repository's guard already lets
  read-only git commands through: its pattern refuses merge followed by a hyphen, and the stamp is
  read only after a protected destination is found. Core's copy changes through a core specification
  that brings it to VELDO-0268's destination step.

## What the reviewer judges

- The only commands that move from refused to allowed are ones where every mention of git or gh is
  data under the Design's definition. One kind of them does run git: a command that writes a script
  with a plain text tool and then runs it without git, such as cat into /tmp/x.sh from a heredoc
  holding a push of main followed by bash /tmp/x.sh. A hook written in one Bash call and run by git in
  a later call is the same case. It was refused at 646ff7c8 and is allowed now, because the guard
  does not follow a file. The owner accepts this with the approval. A git whose name is built by an
  expansion inside a string given to a shell, such as sh -c running $a$b p after export a=g b=it, is
  the same case: that spelling of a push already passes the guard at 646ff7c8, and a configuration
  written beside it is not followed. Quoting alone cannot hide the name, because the test deletes
  every quote and backslash, and an expansion in a command word takes the command outside the subset,
  where it is judged on its whole text as at 646ff7c8.
- The scanner gives up rather than guessing: any construct outside the subset sends the whole text to
  today's judgment, and the judgment itself is unchanged. Inside the subset, AC4 holds the scanner to
  bash's own reading.
- The stated limit is acceptable to the owner. A script the command writes and then runs is not
  followed, which was always true of a script already on disk. Git's pre-push hook
  (packs/claude/hooks/pre-push) judges a push by its destination however it was started, in a
  repository that enables it; this repository does not enable it.
- No list of harmless phrases appears anywhere in the change. The one list of programs is the plain
  text tool set, and a program missing from it can only cause a refusal.

## History

2026-11-10: drafted from the owner's decision 40683 after the VELDO-0290 builder's false hit
2026-11-11: revision 1 applies the findings of the review of ba3946cb
2026-11-11: revision 2 applies the findings of the re-review of c880fe11
2026-11-11: revision 3 applies the findings of the second re-review of 2bf465e1
2026-11-11: revision 4 applies the findings of the third re-review of 20962450

2026-11-11: marked ready by the lead; the third re-review found the spec buildable once RR3 was applied (bc696274)
