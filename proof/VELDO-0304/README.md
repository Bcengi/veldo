# VELDO-0304 fix round 3

Implementation: 8d617d8a2d79c7655e5d1c0d64fa34b216c9f036.

The lead decision is recorded in VELDO-0161 and VELDO-0304 History: design 0.2
keeps a failed adoption's unheld commit on the keep step's kept ref. The five
failing adoption checks now accept only refs/veldo/kept/ as leftover Veldo refs.
The repository-commands check contains two affected comparisons.

All ten requested suites ran with nice -n 10 and have zero failed rows.
round3-suites.json records their logs, hashes and exit code 2: these selected
runs are diagnostic partial runs, not aggregate verification or acceptance proof.

The final finding 304 teeth check is pending. Prior teeth files and the other
proof records are historical until the final receipt replaces them. Round 2's
failed teeth stdout is retained as round2-teeth.log. Its input changed during
that run, so rejection of all cases did not make it a valid stage result.
The adoption-preservation files and round2-mutations retain the round 2 work.

No protected path was changed. Policy validation and landing remain the lead's.
