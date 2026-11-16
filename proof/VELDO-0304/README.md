# VELDO-0304 fix round 3

Implementation: 8d617d8a2d79c7655e5d1c0d64fa34b216c9f036.
Teeth input commit: 577cee1ae223fd4c327ff966b13728b36017ccd2.

The lead decision is recorded in VELDO-0161 and VELDO-0304 History: design 0.2
keeps a failed adoption's unheld commit on the keep step's kept ref. The five
failing adoption checks now accept only refs/veldo/kept/ as leftover Veldo refs.
The repository-commands check contains two affected comparisons.

All ten requested suites ran with nice -n 10 and have zero failed rows.
round3-suites.json records their logs, hashes and exit code 2: these selected
runs are diagnostic partial runs, not aggregate verification or acceptance proof.

The final check was nice -n 10 python3 scripts/check_teeth_mutations.py --finding 304.
It exited 0. Saved stdout reports:

mutations: passed registered=38 executed=38 reused=0 rejected=38 workers=88 elapsed=95.385s

No editor or other command ran and no worktree files were written while teeth
was running. Stdout and stderr were saved outside the worktree. Only proof files
were written after it exited. teeth.log is the saved stdout; teeth-receipt.json
is its parsed receipt. The manifest binds this receipt and sources.json records
the implementation inputs. No further verification command followed teeth.

The current records are this README, manifest.json, sources.json, round3-suites.json,
the ten logs it names, teeth.log and teeth-receipt.json. Other proof records are
historical, including integration-conflict.json and registered-falsifiers.json.
Round 2's failed teeth stdout is retained as round2-teeth.log; its rejection of
all cases did not make that stage valid. The adoption-preservation files and
round2-mutations retain the round 2 work.

No protected path was changed. Policy validation, independent review, aggregate
verification and landing remain the lead's. Acceptance criteria remain pending.
