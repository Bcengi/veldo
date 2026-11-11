# VELDO-0292 proof

The guard judges the live text of a command, and since amendment 2 it finds a write to git
configuration by where the text goes, not by how a later command spells git. Every row and mutation
of the spec is built and green in the quick run. The five commands build 1 let through are
now refused. After the build check of 2026-11-11, sort is no longer a plain text tool. Two commands
still pass and push main: they are the limit the spec states and the owner accepts with the
approval, and they are measured below, with the other known holes listed beside them.

## What was built

Commit d1c5da1a built the scanner on the spec at a5c17de6. Commit aeb93690 applies amendment 2
(spec revision 7, ready at 0412bfa3).

- `scripts/veldo-guard.sh` and its two copies, byte-identical. One scanner reads the command over
  the subset the Design defines and writes its live text. Three tests then run on a command the
  scanner has read. Test 1 collects the places the command writes: the target of every redirection
  that is not an input, and every argument of a plain text tool that writes. A place whose word
  holds an expansion, a glob, a brace, a tilde or a joined line, or whose text after quote removal
  holds git or config anywhere, sends the whole command to the judgment as written. So does the word
  config outside data. Test 2 does the same for a construct in text that reaches a program other
  than a plain text tool. Test 3 is the name test with only its first form, in any letter case. The
  existing judgment is unchanged.
- `scripts/suites/141_veldo_0268_protected_refs.py`: 20 rows and 38 mutation rows, 142 rows with the
  older ones. live/config-write has 23 commands, live/config-include 4, live/construct 6 and
  live/plain-runs 2.
- `scripts/check_teeth_mutations.py`: the 35 mutations as finding 292. A scratch check at aeb93690
  compared the 34 of that build field by field with the suite's own list and found them equal, each
  anchor present once in the guard and each mutant valid Python and valid bash. The 35th,
  guard292-sort-plain, is written with the same anchor and replacement in both files.
- `scripts/suites/manifest.json`: the suite's description.

## The build check of 2026-11-11: sort is not a plain text tool

The reviewer of record checked the build at 0a2057f5 and returned CHANGES. GNU sort runs its
compress program on its own temporary data, and sort was in the plain text tool set. A push fed to
sort as a quoted string or heredoc body was therefore data, nothing named git, and sort handed the
text to sh. 646ff7c8 refuses such a command and the build let it through.

The fix, in all three copies of the guard: sort is out of the set. The membership test is now
stated in the spec's Design and in the guard: a program is in the set only if no option of this
program runs another program. The list of tools that do not write is unchanged, so the tools that
write are nine. Suite 141 has the row live/plain-runs and the mutation guard292-sort-plain, which
puts sort back and must turn the row red. The registry of finding 292 goes from 34 to 35.

The check named three commands, S1 to S3. A scratch probe (not stored) ran each against this
tree's guard and then under bash with a recording program first on PATH:

    S2    cat of a quoted heredoc holding the push, piped into
          sort -S 1K -T D --compress-program=sh - D/big           guard exit 2, bash runs the push
    S3    printf of the quoted push, piped into
          sort -S 1K -T D --compress-prog=sh - D/big              guard exit 2, bash runs the push
    S1    printf of the quoted push into D/a, then
          sort -S 1K -T D --compress-program=sh D/a D/big         guard exit 0, bash runs the push

S2 and S3 are the row. S1 is not refused by this fix, and the check expected it to be. In S1 the
push is a string given only to printf, which writes it to a file at a path that names neither git
nor config, and sort then reads that file. Taking sort out of the set makes sort a program the
guard cannot read, and S1 becomes the stated limit: a plain text tool writes a file and a program
the guard cannot read uses it, the same shape as printf into D/a followed by sh D/a. The guard does
not follow a file. The spec's first reviewer bullet now names S1 as that case, so the row carries
S2 and S3 only. The reviewer and the owner should read this as a difference from the check's fix
list, not as the fix applied in full.

The four summaries committed as 282d9afb are the runs of lock job 96a over 0a2057f5, before this
fix. They are kept as committed until `heavy_runs.sh` runs again under the lock and replaces them.

## The five commands of build 1 are refused

Each writes an alias that pushes main to the configuration and runs it through a spelling of git
the old name test did not read:

    printf '[alias]\n\tp = !git push origin main\n' >> '.g''it/config'; <the part below>

    sh -c 'gi$(true)t p'        a command substitution that prints nothing
    sh -c 'gi`true`t p'         the same in backquotes
    sh -c 'gi${x:-${y}}t p'     an expansion with nested braces
    bash -c '{gi,}t'            a brace expansion, with the alias named t
    gi\                         a backslash before a newline inside the name
    t p

Command: `python3 proof/VELDO-0292/unread_spellings.py`, result in `unread-spellings.summary.json`,
run at aeb93690. For each of the five and for the control `sh -c 'g\it p'`, the guard at 646ff7c8
exits 2 and this tree's guard exits 2. Test 1 refuses them on the path `'.g''it/config'`. The same
five spellings behind a path that names neither git nor config are the live/construct row, which
test 2 refuses.

## The stated limit: L1 and L2

Two commands pass this guard and bash then moves the remote's main. 646ff7c8 refuses both. The
spec allows them in the first bullet of What the reviewer judges, and the owner accepts them with
the approval. Both write the alias section with printf to `D/inc`, a path that names neither git
nor config, and then:

    L1    printf '%s%s -c include.path=D/inc p\n' gi t | sh
    L2    python3 -c 'import os; os.system("g" + "it -c include.path=D/inc p")'

Measured in the same run: guard at 646ff7c8 exit 2, this tree's guard exit 0, main moved, for
both. In each a program that is not a plain text tool builds the name git from text it is given
and points it at a file the command wrote. Nothing in the text separates this from the incident of
AC1, where a plain text tool writes a file and a program the guard cannot read uses it. The guard
does not follow a file. In this repository git's pre-push hook is not enabled, so the PreToolUse
guard is the only layer for such a command.

The other known holes, so the owner sees every one in one place. The first two are new with this
spec; the rest pass this guard exactly as they pass 646ff7c8, so they are outside this spec. The
exit codes for X2, X5, PH1, T1 to T4 and the gh forms are the build check's measurements at
0a2057f5 (old guard exit, built guard exit, whether main moved); none of them involves sort.

- S1, sort given a file: printf of a push into D/a, then sort with its compress program set to sh
  reading D/a. 646ff7c8 exit 2, this guard exit 0, bash runs the push. The same class as L1.
- X2 and X5, an extended glob: with the alias section written to D/inc,
  `bash -O extglob -c '/usr/bin/@(gi)t -c include.path=D/inc p'` and the same with `gi+(t)`.
  2, 0, moved. An extended glob pattern is not a construct for tests 1 and 2; the spec's first
  reviewer bullet says so. The capability is no larger than L1.
- PH1, a hook assembled from pieces: printf builds the hook's text from gi and t, writes it to
  .git/hooks/post-commit, and git commit runs it. 0, 0, moved. Test 1 fires on the path, and the
  646ff7c8 judgment it hands to finds no push text.
- T1 to T4, a glob in a command word: `/usr/bin/gi[t] push origin main` bare, after `[ 1 ];`,
  after `[ 1 ] && exec` and after `[ -f README ] &&`. 0, 0, moved. Test 2 fires, and the 646ff7c8
  judgment does not see git in `gi[t]`. The same holds behind a subshell, behind env, and for
  `bash -O extglob -c` with `/usr/bin/@(gi)t push origin main`.
- gh pr new, and gh pr create after a list prefix: 0, 0, and gh is called. 646ff7c8 resolves
  gh pr create as moving no ref (VELDO-0268) and does not read gh pr new as a push.

## Readings of the spec

- The refusal line of test 1 and test 2 ends "in text the guard does not parse" with the reason:
  "a write the guard reads as git configuration:" and the path as written, "the word config
  outside data, which the guard reads as a write to git configuration", or the construct "in text
  a program may run". A backslash before a newline is named in words.
- The awk command of live/interpreter is refused for the braces of its program, as the amendment
  expects. The row's expectation changed with it.
- A message value given to git or gh is an argument of a program that is not a plain text tool.
  Test 2 and the config word of test 1 therefore read it, as the Design's sentence on test 2 says.
  A commit whose message holds the word config or one of the construct characters, and also
  mentions a push, is refused as at 646ff7c8. The amendment lists this cost. The other reading
  would treat a stored message as a data string and let it pass. I took the one that refuses.
- A joined line between two words of a plain text tool is outside its words, so test 2 reads it.
  The reviewer's model does the same.
- The tools that write are every plain text tool the guard's list of tools that do not write
  leaves out. Today that is the nine the Design names.
- The membership test is read as "no option names a program for the tool to run". diff stays in the
  set: its -l option runs pr, a fixed program that prints pages and runs no text, and no option of
  diff takes a program's name. A stricter reading of the test would take diff out; the reviewer
  should say if that is wanted.
- The suite takes another temporary directory when the name it was given holds git or config,
  because the new rows name that path. A row fails with a plain message when the path above it
  holds either word.
- AC4's `<<-` command ends with one more line reading EOF, and guard292-git-list-per-line keeps
  live only the last line that names git, as the spec says since revision 5.
- The unresolved line ends with the finding, after the existing "treated as protected" words, so
  the anchors of the older mutations did not move.
- The message rule reads `-m` as its own word. `git commit -am "..."` with a push named in the
  message is still refused.
- A standalone `g\it push origin main` is judged as a push. The spec promises this only inside a
  list or pipeline; it follows from writing command words after quote removal.

## Checks run here

- `python3 -m py_compile` on the suite, the registry and the two proof scripts.
- `bash -n` on the three copies of the guard and on `heavy_runs.sh`; `cmp` on the three copies.
- `python3 scripts/selftest.py --suite 141_veldo_0268_protected_refs` under
  `systemd-run --user --scope -p MemoryMax=10G` on the tree of aeb93690: 140 rows, 0 failed, 270 s
  on a loaded host. This is a partial run and proves nothing by the gate's rules; step 2 of
  `heavy_runs.sh` repeats it under the lock. In that run each of the nine new mutations and each of
  the four name test mutations let at least one command of its row through with exit 0, so no row
  is red on the wording of the line alone.
- `python3 proof/VELDO-0292/unread_spellings.py`, at aeb93690 only.
- `python3 .veldo/validate.py proof-files`, `python3 .veldo/validate.py proof` on the manifest and
  `python3 scripts/check_personal_setup.py`.

After the build check's fix, on the working tree that became commit 7b8ff1fd:

- `python3 -m py_compile` on the suite, the registry and `summarize.py`; `bash -n` on the three
  copies of the guard and on `heavy_runs.sh`; `cmp` on the three copies.
- `VELDO_0268_DETAILS=1 python3 scripts/selftest.py --suite 141_veldo_0268_protected_refs` under
  `systemd-run --user --scope -p MemoryMax=10G`: 142 rows, 0 failed, 129 s. A partial run, which
  proves nothing by the gate's rules. live/plain-runs: both commands exit 2 with the push found
  "in the argument or input of sort, which is not a plain text tool", and bash runs the push for
  both. Under guard292-sort-plain both exit 0, so the row is red on the exit code.
- The scratch probe of S1 to S3 described above, and a scratch read of the registry: 35 cases
  for finding 292, each anchor present once in the guard.
- `python3 .veldo/validate.py spec` on the spec, `proof-files`, `proof` on the manifest and `all`,
  and `python3 scripts/check_personal_setup.py`: each exit 0.

## Pending under the gate lock

`bash proof/VELDO-0292/heavy_runs.sh` runs four steps and writes one summary each:

1. `red-before.summary.json`: suite 141 over the guard and policy_check as they were at 646ff7c8.
   Expected red: the 18 rows the spec calls red there, live/plain-runs among them, and the 38
   mutation rows. Expected green: live/scanner-edges, live/git-args and every older row.
2. `green-after.summary.json`: suite 141 over this tree, 142 rows, none red.
3. `teeth-292.summary.json`: finding 292, 35 cases, each killed.
4. `teeth-268.summary.json`: finding 268, whose anchors sit in the file this change edits.

Not run here: the gate, policy_check, any teeth run, and the red-before run.
