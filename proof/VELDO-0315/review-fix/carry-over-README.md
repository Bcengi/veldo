# VELDO-0315 implementation evidence

This bundle records targeted checks, not a gate result or an independent review. All acceptance
criteria remain pending the lead's gate and review. Run `./scripts/verify.sh` through the lead's
gate lock. The full gate, heavy suites, teeth stage and policy checker were not run here.

The implementation adopts from declared repositories and committed ownership records, compares both
the locator and marked name, leaves live or unread carriers alone, restores changed marked work,
verifies the keeper's refs and snapshot attempts, and retries due items through Signal and the
existing removers. It bootstraps Service.space before dispatch and records raised ending events in
synced retry records before the journal cursor advances. Reconcile has no timer. Existing act
prerequisites remain in place.

Suite 156 uses real temporary Git repositories, private commits, linked worktrees, a real SQLite
ledger and owner signatures. Its process table and Docker client are fixtures. The act prerequisite
callbacks are supplied only in those fixtures. Every removal test uses the established removers;
the owner Keep, changed marked work, unread carrier, failed snapshot, and unowned work rows retain
their planted work. The concurrent row interleaves another successful removing write at the ledger
boundary and checks that the loser makes no item write and invokes no removal. Startup is the real
Service.space_start; the fixture's immediate dispatch reads the resulting ledger, without running
a worker or an external service. Bootstrap checks use the real central ledger and installation,
then the real ending-event and owner Abandon entry points.

`run_falsifiers.py` reads the literal registrations using AST, checks them against
`falsifier-cases.json`, and runs disposable production copies. It neither imports nor runs the teeth
driver. The final run applies each of the 12 mutations once after a green baseline. A preceding
exploratory run exposed two assertions that reported missing-file exceptions instead of the intended
wrong state; those assertions and the unowned-folder mutant were tightened before the recorded run.
The batch-as-scratch mutation turns the classification row red; the existing remover's independent
repository guard still retains its unique commit. This evidence does not claim that bypassing that
second guard was necessary or tested. The report-removal mutation deliberately deletes fixture-only
unowned work in its disposable copy and the retention row turns red. No such path is in production.

The service ending-event regression passes all 41 selected rows and Docker ownership passes all 25.
The installation suite passes 29 of 30 rows. Its stopped-service row also fails against the starting
revision: systemd reports inactive, no process is bound, and the unbound socket pathname remains.
`installation-comparison.json` records both observations. No prior suite or live capture was edited.
Partial selftest selections intentionally return a nonzero code even with no failed assertions.

The accepted VELDO-0323 worker and service startup were read from their branch with Git. They were
not copied into this branch. At landing, its Consumer startup must retain this ticket's bootstrap
before Consumer.start and the synchronous reconcile callback after replay and received events.
The service entry here is synchronous; introducing the accepted worker is the lead's integration.
The API authority is given the on-demand method; later presentation and CLI tickets own their edges.

All retained artifacts are small summaries. Fixture logs are omitted. The protected real data,
engines, images, captures and database volumes were not used by the VELDO-0315 tests.
