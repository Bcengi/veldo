---
schema: veldo.spec/v1
id: VELDO-0292
title: The push guard judges only the git and gh commands the shell would run, so text that mentions one in a quoted string, a heredoc body, a comment or a file the command writes is never refused, while a git command the guard cannot resolve stays protected
status: draft
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
    command of a list or pipeline, the argument or input of a named text runner, or text the guard does
    not parse, with the construct named). The incident's message gave the builder no way to see which
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
      function body; a push behind a shell alias or a git alias; and a command that carries both a
      quoted mention and a real push. The refusal line names what the guard found and where.
    falsified_by: >
      Suite 141 rows, each requiring exit 2, the gate refusal text, the remote's main unmoved, and one
      "destination unresolved" line that quotes the matched text and names its position. live/shell-string:
      sh -c and bash -c with the quoted string git push origin main, the same under timeout, eval with
      that string, and bash reading it from a quoted heredoc. live/pipeline: true piped into git push
      origin main, the quoted string echoed into sh, and the quoted string echoed into xargs env.
      live/outside-subset: the string assigned to a variable that is then the command word, a function
      whose body pushes and is then called, and a shell alias defined and then used. live/mixed: echo
      of a quoted mention followed by a real push of main after a cd. At 646ff7c8 each row is red only
      because the line does not yet say what was found; the exit code and gate text already hold.
      Registered mutations: guard292-runner-strings-data (the set of text runners is empty) turns
      live/shell-string and live/pipeline red; guard292-unparsed-is-data (a command outside the subset
      has its quoted strings removed anyway) turns live/outside-subset red. Every row and registered
      mutation suite 141 carried at 646ff7c8 still passes; an anchor the change moves is pointed at the
      same defect again.
  - id: AC3
    text: >
      A mention of git or gh in a quoted string, in a heredoc body read by a program that is not a text
      runner, or in a comment is never a git command. A command whose every mention is one of these is
      allowed whatever the gate stamp says, including when it also uses plain variable expansions in its
      arguments.
    falsified_by: >
      Suite 141 rows on the red stamp fixture, each requiring exit 0, no "VELDO guard: destination"
      line, and an empty record from the recording git and gh when the command then runs under bash.
      text/quoted: echo and printf of a double quoted sentence containing git push origin main; grep for
      the single quoted words git push in a fixture file; python3 -c printing them; echo of the quoted
      sentence beside an argument that expands HOME. text/heredoc-stdin: python3 reading a quoted
      heredoc whose body prints the words, and cat of an unquoted heredoc whose body holds them and no
      expansion. text/comment: ls followed by a comment reading git push origin main, alone and after a
      list of two commands. At 646ff7c8 all three rows are red: the guard exits 2 on each command.
      Registered mutations: guard292-quoted-live (quoted strings stay in the judged text) turns
      text/quoted red; guard292-comment-live (comments stay in it) turns text/comment red.
required_evidence: [unit, integration]
rollback: >
  Revert the commit. The guard again refuses any command whose text contains a push or merge phrase, as
  at 646ff7c8. Nothing stored changes shape, so nothing needs migrating.
---

## Intent

The guard must stop refusing commands that only talk about git.

On 2026-11-11 a builder ran one Bash command that wrote a helper script to /tmp, ran it and deleted it.
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
judged as today. That makes its error one-sided: a mistake or a gap in the scanner can only leave a
command refused that could have passed. It can never pass a command by guessing. The existing judgment,
with its dry run, alias lookups and reasons, runs on the live text and is not rewritten.

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
it:

- A comment is data.
- A heredoc body or a quoted string is data when the shell does not expand it (single quotes; double
  quotes with no `$` or backtick; a heredoc with a quoted delimiter, or with no `$` or backtick in its
  body), it is not part of an assignment's value, and no command in its pipeline is a text runner.

A text runner is a program that executes text it is given. A command is one when any of its words,
after quote removal and taken by its last path component, is in one fixed set in the guard:

- the shells: sh, bash, dash, zsh, ksh, mksh, ash, fish, csh, tcsh, busybox;
- the shell builtins that evaluate text: eval, source, `.`, trap, alias, exec, command;
- programs that build a command line from an argument or from standard input: xargs, parallel, watch,
  su, sudo, script, flock, env, ssh;
- git and gh. Git runs some of its own arguments (an editor, a pager, an alias, a command given to
  rebase), so a git or gh command keeps all of its text live.

Checking every word, not only the first, covers wrappers such as timeout and nohup without listing
them. Checking the whole pipeline covers a string echoed into a shell. Assignment values stay live so a
string stored in a variable and run later is still seen.

This set makes text live. It is the opposite of a list of allowed phrases: a name missing from it
leaves a gap, stated below, and a name added to it can only cause a refusal.

The allowed rows run their command under bash with a recording git and gh, so the suite checks on each
host that text the scanner called data is text the shell did not run.

## Out of scope

- Git's own argument grammar. A git or gh command stays live in full, so `git commit -m` with a
  message that mentions a push is still refused. Teaching the guard which git arguments are messages
  is a separate spec.
- Compound commands and substitutions. A command with a loop, a conditional, a function or `$(` and a
  mention of a push is still refused, as today.
- Forms the guard already lets through at 646ff7c8. This spec closes none of them and opens none.
- The git pre-push path, the checks a protected destination runs, policy_check and the lander.
- Core's copy of the guard, which changes through a core specification as VELDO-0268 describes.

## What the reviewer judges

- Nothing that was refused at 646ff7c8 because the shell would run git or gh is allowed now. The only
  commands whose verdict changes are ones where every mention of git or gh is data under the Design's
  definition.
- The scanner never guesses. Any construct outside the subset sends the whole text to today's
  judgment, and the judgment itself is unchanged.
- The stated limit is acceptable to the owner. A program outside the text runner set that executes a
  string it is given (python3 -c starting a subprocess, for one), and a script the command writes and
  then runs, are not followed. That was always true of a script already on disk. Git's pre-push hook
  (packs/claude/hooks/pre-push) judges a push by its destination however it was started, in a
  repository that enables it; this repository does not enable it.
- No list of harmless phrases or harmless commands appears anywhere in the change.

## History

2026-11-11: drafted from the owner's decision 40683 after the VELDO-0290 builder's false hit
