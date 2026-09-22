# Full gate verification

- Command: `bash scripts/verify.sh`
- Exit status: `0`
- Result: **GREEN**
- Verified commit: `e559f396dad7811337c70180ed5dc63c50790610`
- Verified Git tree: `1de1ec48d4529b0440240860af46ea1d80450800`
- Gate completion: `2026-09-22T16:57:12Z`
- Gate-reported working tree: `clean`
- Unit result: **5,539 passed, 0 failed**
- Catalog: **8 run, 15 not applicable, 0 waived, 0 undeclared**.
  The complete log records the reasons for non-applicable checks.

Lint, unit, first-use integration, security, generated artifacts, documentation,
packaging, extra checks, secret scan, contracts, and the mechanizable shape gate
passed. Review-lane guidance remains guidance; this run is not an independent
review or approval.

[Complete stdout and stderr](gate.log)

Log SHA-256: `c8a90181761a679bd406767ea78580c037be2b857e7c749575ec6668b65b2f06`.

The following evidence commit adds only this record, the log, and the evidence
README update. The checkout's `.veldo/last_verify` and `.veldo/events.jsonl`
are restored before that commit and are not committed. A merge verification stamp
belongs to the reviewer's checkout of the merged tree.
