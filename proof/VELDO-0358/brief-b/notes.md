# VELDO-0358 brief B: census, lists and supersession

Branch veldo-0358-b, built on e3451130. Criteria: AC6, AC7, AC14. This file says what was built, how the
first baseline compares with the design's counts, which exceptions were written and why, and what the lead
has to decide or do. The logs beside it are the evidence.

## What was built

| Piece | Where |
| - | - |
| The census stage | scripts/check_wallclock.py, canon copy engine/scripts/check_wallclock.py |
| The exceptions (23 keys, 36 sites) | scripts/suites/wallclock.json |
| The first baseline (2869 keys, 3015 sites) | scripts/suites/wallclock_baseline.json |
| The stage in the gate | scripts/verify.sh (catalog slot `wallclock`, required), scripts/gate_graph.json (node `wallclock`), engine/scripts/verify.sh (the slot, declared na in the template) |
| Protected paths | .veldo/policy.yaml: the tool, its canon copy and both lists, floor high |
| AC14 | specs/VELDO-0223 (blocked, History), specs/VELDO-0215 (History), specs/index.md regenerated |
| Rows | scripts/suites/158_veldo_0358_census.py: census/each-rule, census/lists-from-authority, census/stage-declared, supersede/0223-not-claimable, supersede/result-words-closed |
| Falsifiers | scripts/check_teeth_mutations.py, block "VELDO-0358 BRIEF B": eleven cases, finding 358 |

The stage reads source only. It has no sleep, no clock read and no timeout of its own, and the suite's
children are started with no timeout.

## How the stage is run

The catalog command is `python3 scripts/check_wallclock.py`, run like every other catalog stage. The gate
exports `VELDO_GATE_AUTHORITY` (its own checkout) just before the catalog, and the stage reads the
exceptions and the authority's baseline from there and the candidate's baseline from the tree it runs in.
Run by hand with no variable, the checkout is its own authority. The command holds no quote on purpose:
suites 64, 114_veldo_0216 and 127 read catalog commands with a pattern that stops at a quote.

A key is (file, rule, text of the source line with its whitespace collapsed, qualified name of the
enclosing function). A line longer than 200 characters is cut and carries a digest of the whole. Line
numbers are not part of a key, so code moving up or down a file changes nothing; a rewritten line is a new
key, as the design intends.

## First run against the design's counts (design 4.1)

Log: census-first-run.txt. scripts/suites figures below leave out this brief's own suite (20 sleeps in
fixture text, all excepted).

| Scope | Figure | Design | First run | Difference and its cause |
| - | - | - | - | - |
| scripts/suites | R1 sleep calls | 119 | 122 | 3 more: sleep commands later in a list are found once each (113:207, 231; 63:1285; 67:705; 151:1160, 1272), and the two aliased sleeps of suite 13 (7226, 7255) |
| scripts/suites | sleeps in source text | 112 | 112 | none |
| scripts/suites | R2 clock reads | 914 | 1002 | 88 more: 77 are `__import__('time').time()` written inline, which the design's scan did not resolve; 11 are clocks reached through a name bound by assignment (for example `_v13_real_clock`) |
| scripts/suites | R3 timeouts | 890 | 928 | 38 more: 34 are a timeout given as a variable or an expression (the rule says anything other than zero, None or a named constant; the design's scan counted numbers only); 4 are positional forms the design's split does not list (create_connection, alarm, poll) |
| scripts, top level | R1, R2, R3 | 9, 64, 26 | 9, 64, 38 | R3: the 12 more are all timeouts given as a variable |
| proof | R1, R2, R3 | 17, 341, 218 | 18, 341, 221 | 1 sleep command; 2 timeouts given as a variable; 1 positional |

With the two deliberate extensions set aside (inline imports and non-numeric timeouts) the figures are
925 against 914 for R2 and 894 against 890 for R3 in scripts/suites, 26 against 26 for the tooling, and
219 against 218 for proof. Class totals in scripts/suites: S1 27, S2 86, S3 9, P 202, D1 724, D2 76, T 928
against the design's S1 28, S2 83, S3 7, F 1, P 201, D1 628, D2 85, T 890; the D1 growth is the 88 extra
clock reads. The class is data for the reader and judges nothing.

Every R4 site of the design's section 4.3 is found, and suite 63's lines 722, 1069 and 1268.

## The exceptions written, and those not written

| Kind | Sites | Why |
| - | - | - |
| subject | suite 13, seven sleeps in fixture text (lines 6742 to 7317) | named by the brief and design 9.3 |
| subject | suite 42, lines 400 and 404 | named by the brief and design 9.3: two fixtures that differ only in duration |
| subject | suite 04, line 761 | named by the brief: fixture pacing, class F |
| subject | suite 158 (this brief's), twenty sleeps in fixture text and expected output | the census's own test subjects |
| supplied_clock | suite 63, line 722 | named by the brief |
| lower_bound | suite 86_veldo_0148, the two 5.25 s sleeps in fixture text | design 9.3's own example; read by the lower bound of line 1456 |
| lower_bound | suite 113, line 231 (`sleep 2` holder) | read by the lower bound of line 236 |
| lower_bound | suite 111, line 45 (0.2 s fixture stage) | read by the lower bound of line 304 |
| lower_bound | suite 58_veldo_0028, line 954 (3 s receive hook) | read by the lower bound of line 974 |

Not written, for the lead and the owner to rule on:

- The other four lower bounds of design 4.3 (62:676, 67:509, 75:1463, 151:1205) are fed by a fixture
  engine's scripted hold or by a holder the design converts to a latch (151:1160). There is no site to
  except; the clock reads beside them stay in the baseline until they become stamps.
- Suite 42, lines 153 and 468, are sleeps in fixture text but the design lists 468 as a holder to
  convert, and 153 is not named. Both are in the baseline.
- Suite 63, lines 880, 883, 885 and 896, are upper bounds on values of the same fake manager clock as
  line 722 (manager_sequence, lines 466 to 494). The design names only 722. They are in the baseline, so
  brief E cannot bring suite 63 to zero sites without four more supplied_clock entries, which only the
  owner can add. Suite 112's bounds (223 to 271) are on a supplied clock in the same way.

## For the lead

1. The opened-files record's place. The contract fixes its content, not its name. The stage reads
   `--record PATH`, by default `.veldo/opened_files.json` of the authority. Brief A's writer takes its
   path from VELDO_OPENED_FILES. Whoever sets that variable in the gate should write the file there, or
   the default here changes. Until a record exists the scope is all of scripts/ and proof/.
2. A record narrows the scope. A baseline entry of a file outside the scope is then required to equal the
   authority's entry (the file is the authority's own, byte for byte), so the first baseline stays valid
   when the first record appears.
3. Files outside brief B's list that had to change:
   - scripts/suites/113_veldo_0220_gate_host.py and 114_veldo_0220_gate_scope.py, one line each: their
     fixture gates copy the real verify.sh and stub every stage's script by hand, so a new required stage
     needs its stub. Neither file is in the specification's footprint; it needs them added.
   - scripts/suites/manifest.json and requires.json: the entry of suite 158.
   - scripts/suites/158_veldo_0358_census.py is new and matches the footprint's pattern.
4. The engine template gate declares the slot as na. Making it required for adopters needs
   engine/.veldo/init_scaffold.py to lay the tool down, and that file is outside the footprint.
5. Not built: the gate stamp and event carrying the census counts (the specification's traces line). The
   stage prints them; putting them in the stamp is a change to the stamp section of verify.sh that
   brief D's load record also needs, so it belongs to the combining step.
6. Protected paths. This change touches .veldo/policy.yaml, both verify.sh files and gate_graph.json and
   adds two protected lists. `.veldo/policy_check.py` reports blocked until the owner's approval, as
   expected; no approval was authored here.
7. Landing order. This branch's baseline describes the tree at e3451130 plus brief B. Each brief that
   lands after it lowers the entries it removed: run `python3 scripts/check_wallclock.py` and take out
   each line it names as baseline_stale. A brief that adds a site (brief A's waits.py is exempt from R1
   to R3; its fixture suites are not) needs it excepted or converted before the stage is green.
8. In an ordinary checkout gate the checkout is its own authority, so a builder who adds a site and its
   baseline line in the same tree passes there. The landing gate (candidate mode, installed authority)
   is where the rule binds, as for scripts/gate_unconfined.json.

## Evidence

| File | What it shows |
| - | - |
| census-first-run.txt | the stage's output on this tree and the counts by scope against the design |
| falsifiers.txt | 11 of 11 rejected. Each of the eleven registered mutants: the diff that landed, the target row green on a no-op copy and red under the mutant, and the row's own words |
| suites.txt | the eleven affected suites, 590 rows passed and none failed. The full selftest was queued under the host lock behind a gate and seven other jobs and had not started; it is not claimed |
| checks.txt | lint, template sync, generated files, contracts, personal setup, the stage itself |
