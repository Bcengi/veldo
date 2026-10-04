# VELDO-0167 independent merge review repair

Implementation: b32b7d0d. Branch: build-veldo-0167. Nothing pushed.

The store change belongs to VELDO-0037 (declaration ownership) and VELDO-0189
(upgrade rebinding and restoration). Both existing footprints already include
the store copies, their respective suites and the mutation registry. Their
History entries describe only this extension and its checks.

`declare_owners` accepts a strict command superset only for the same owner,
module and digest, after checking that every command is bound to that code.
It updates commands inside the existing transaction. Other differences retain
`ownership_conflict`. Rebinding with `keep_previous=True` records commands as
well as the previous digest; restoration puts both back transactionally. An
existing previous-binding table gains the command column inside the transaction.
Public observation tuples retain their existing shape.

The intake changes from e2892514 and 66110bab are removed. `intake_route` is
again the registered operation used by `route()`, with no `params.operation`
discriminator or compatibility branch. All three changed engine modules match
their repository copies byte for byte.

Added assertions and mutations:

- Suite 59 adds 12 assertions: kind and prefix cases for a different owner,
  removal, replacement, a command bound elsewhere, transaction rollback after
  a later declaration conflict, and an accepted, idempotent strict superset.
- Suite 86 adds `ownership/restore-commands`: an existing table, both selector
  types, repeated rebinding, failed-observation rollback, exact restoration and
  attachment with the old command set.
- Suite 93 rewrites `route/legacy-owner` using the archived 971186ac pre-route
  intake file and the 0126 declaration. It checks the expanded command sets,
  the committed command's `intake_route` operation and journal digest, and actual
  previous-engine attachment after restoration. The artificial already-routed
  declaration block is removed; missing-factory checks remain.
- Finding 37 gains `owners37-different-owner-adds`,
  `owners37-removing-command-allowed`, `owners37-bound-command-added`,
  `owners37-superset-refused`, and `owners37-added-command-lost`.
- Finding 189 gains `upgrade189-previous-commands-not-recorded` and
  `upgrade189-previous-commands-not-restored`.

All seven mutations target assertion failures. Static checks confirm that each
anchor matches once and each substituted module parses. Mutations were registered
only, not executed. Every other 0152 and 0167 row and mutation remains.

Scoped runs, one suite at a time, with zero failures:

Counts below give suite assertions, then totals including shared checks.

- 59_veldo_0037_aliases: 53, total 79.
- 86_veldo_0189_engine_upgrade: 33, total 59.
- 91_veldo_0167_setup_records: 9, total 35.
- 93_veldo_0152_intake_routes: 22, total 48.
- 82_veldo_0172_live_formats: 4, total 30.
- 50_git_environment: 4, total 30.
- 36_veldo_0023_journal: 17, total 43.
- 68_veldo_0126_intake: 18, total 44.

There are 160 suite assertions and 368 total assertions including repeated shared
checks. Suite 59 ran before the replacement assertion's label was made distinct
from the removal assertion; that final edit changes only the label.
The suite selector deliberately returns exit 2 for a partial run even when all
assertions pass. These observations are not a gate result or landing evidence.

`python3 .veldo/validate.py all` and `python3 scripts/check_git_boundary.py` both
returned exit 0. No whole selftest, mutation runner or gate was run. The reviewer
retains those checks and the merged-checkout verification stamp.
