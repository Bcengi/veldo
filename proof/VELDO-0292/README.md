# VELDO-0292 proof

The guard now judges the live text of a command, and every row and mutation the spec names is built
and green in the quick run. AC2 is not met as its text is written: five commands that 646ff7c8
refuses pass this guard and bash then pushes main. They are measured below. The build follows the
Design exactly, so closing them is a change to the spec, not to this code.

## What was built

Commit d1c5da1a, on the spec at a5c17de6.

- `scripts/veldo-guard.sh` and its two copies, byte-identical. One scanner reads the command over the
  subset the Design defines and writes its live text. The existing judgment is unchanged and reads
  that text. The shell line that decides whether the command goes to the judgment at all now reads
  the text without quote characters and backslashes; without that a command word written `g\it`
  never reached the scanner.
- `scripts/suites/141_veldo_0268_protected_refs.py`: 17 rows and 30 mutation rows. The new rows
  print as `VELDO-0292 <row>`.
- `scripts/check_teeth_mutations.py`: the 27 mutations as finding 292. A scratch check compared
  them field by field with the suite's own list and found them equal, each anchor present once in
  the guard and each mutant valid Python and valid bash.
- `scripts/suites/manifest.json`: the suite's description.

## AC2 is not met for five spellings

AC2 says a git alias whose text names a push, written to a configuration file by a plain text tool
and used later in the same command, is refused exactly as at 646ff7c8. The Design decides whether
the command names git by reading three forms of its text. These spellings are in none of the three.
Each line is the part after the write, which is the same in all of them:

    printf '[alias]\n\tp = !git push origin main\n' >> '.g''it/config'; <the part below>

    sh -c 'gi$(true)t p'        a command substitution that prints nothing
    sh -c 'gi`true`t p'         the same in backquotes
    sh -c 'gi${x:-${y}}t p'     an expansion with nested braces; the second form stops at the first }
    bash -c '{gi,}t'            a brace expansion, with the alias named t
    gi\                         a backslash before a newline inside the name
    t p

Command: `python3 proof/VELDO-0292/unread_spellings.py`, result in `unread-spellings.summary.json`.
For every one of the five, the guard at 646ff7c8 exits 2, this tree's guard exits 0, and bash moves
the remote's main in a scratch repository. The control, `sh -c 'g\it p'`, exits 2 under both.

The spec's reviewer bullet says quotes, backslashes and an expansion that supplies none of the
letters cannot hide the name. The first four are expansions that supply no letter, and the fifth is
a backslash. No row or mutation covers them, so the suite is green with them open.

I did not widen the test on my own. A fourth and fifth form would close these five and leave the
next spelling open. A rule that fails closed would hold better: when the command gives a program
that is not a plain text tool a heredoc body or a word that is quoted or holds a backslash, an
expansion or a brace, or writes a command word that way, nothing in the command is data except the
stored message values. Read against the rows, the incident and every allowed row of AC1, AC3 and
AC5 have no such word, so they would still pass. I have not built or run that rule.

## Readings of the spec

- The spec's Context names the guard's functions, not line numbers, and the names still match.
- AC4's `<<-` command ends with one more line reading EOF, and guard292-git-list-per-line keeps
  live only the last line that names git. Revision 5 of the spec already says both.
- The unresolved line ends with the finding, after the existing "treated as protected" words, so
  the anchors of the older mutations did not move.
- A sole command that is not simple (a redirection, an expansion in an argument) is reported "as
  the command word". Unquoted words of a plain text tool that match are reported under "text in a
  command that also names git or gh", which is true of them.
- An alias refusal whose text holds no push or merge words gets no finding. The existing reason
  already says an alias was found.
- The message rule reads `-m` as its own word. `git commit -am "..."` with a push named in the
  message is still refused. The spec says `-m` and its long spelling, and I kept to that.
- A standalone `g\it push origin main` is now judged as a push. The spec promises this only inside
  a list or pipeline; it follows from writing command words after quote removal.

## Checks run here

- `python3 -m py_compile` on the suite, the registry and the two proof scripts.
- `bash -n` on the guard and on `heavy_runs.sh`.
- `python3 scripts/selftest.py --suite 141_veldo_0268_protected_refs` under
  `systemd-run --user --scope -p MemoryMax=10G`, twice at d1c5da1a: 131 rows, 0 failed, 58 s. This
  is a partial run and proves nothing by the gate's rules; step 2 of `heavy_runs.sh` repeats it
  under the lock.
- `python3 .veldo/validate.py proof-files`, `python3 .veldo/validate.py proof` on the manifest and
  `python3 scripts/check_personal_setup.py`.

## Pending under the gate lock

`bash proof/VELDO-0292/heavy_runs.sh` runs four steps and writes one summary each:

1. `red-before.summary.json`: suite 141 over the guard and policy_check as they were at 646ff7c8.
   Expected red: the 15 rows the spec calls red there and the 30 mutation rows. Expected green:
   live/scanner-edges, live/git-args and every older row.
2. `green-after.summary.json`: suite 141 over this tree, 131 rows, none red.
3. `teeth-292.summary.json`: finding 292, 27 cases, each killed.
4. `teeth-268.summary.json`: finding 268, whose anchors sit in the file this change edits.

Not run here: the gate, policy_check, any teeth run, and the red-before run.
