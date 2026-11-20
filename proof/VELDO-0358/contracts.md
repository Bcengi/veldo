# VELDO-0358 contracts shared by build briefs A to H

Fixed by the lead on 2026-11-20 from the design's revision notes, section 3.1. No brief changes these without the lead. The load leg's repetition allowance of 30 minutes is accepted by the lead.


These are the only things the briefs share. The lead writes them into proof/VELDO-0358/contracts.md on day
one, and no brief changes them without the lead.

| Contract | Owner | Read by | Content |
| - | - | - | - |
| Row result lines | A | C, D | A hung row prints a line beginning SELFTEST HUNG with the row, the wait's name and its source line; a row not reached prints a line beginning SELFTEST NOT RUN with the row; failed and passed lines are unchanged |
| Opened-files record | A | B, D | One JSON file per gate run beside the stamp: suite name to the sorted repository-relative paths under scripts/ and proof/ it opened or imported |
| Baseline and exception files | B | C, D | JSON entries of file, rule, normalized text, enclosing qualified function, count, and for the baseline the class, for exceptions the kind, reason and specification |
| Timers table | C | E, F | engine/.veldo/timers.py: one entry per constant (name, value, owning module, kind); one call that sets every entry to the wait hang bound but a named one; one call that reports effective values. Each wave 1 brief adds entries only for the modules it owns |
| Hang constants | A | all | WAIT_HANG_SECONDS 600 and PROCESS_HANG_SECONDS 3600, exported by suites/support/waits.py; the heavy-child list of design 6 |
| Mutant registrations | each brief | lead | Each brief appends its registered mutants to scripts/check_teeth_mutations.py in a block of its own, named by its brief, so merges do not interleave |

Landing order rule: brief B carries the first baseline. A brief that lands after B lowers the baseline
entries its own change removes (H1 makes that required and approval-free). A brief that lands before B
needs nothing; B's first run sees the tree as it is.

