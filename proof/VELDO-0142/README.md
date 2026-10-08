# VELDO-0142 scoped proof

The implementation is bound to bba678d8. Specification status stays ready. No independent
review, approval, full gate, mutation driver, push or merge was performed.

| Criterion | Proving rows in suite 103 | Driven falsifier |
| --- | --- | --- |
| AC1 | setup/full-command-and-rerun; setup/two-identities-and-replay; binding/missing; binding/second; binding/immutable; setup/reference-only-and-unchanged | identity142-binding-replaced makes binding/immutable fail; identity142-setup-binding-omitted makes setup/full-command-and-rerun fail |
| AC2 | launch/no-author-overrides; clone/identity-authors; clone/unbound-refused | identity142-clone-global-author makes clone/identity-authors fail; identity142-environment-overrides-kept makes launch/no-author-overrides fail |
| AC3 | lander/identity-and-reland-authors; lander/unbound-before-commit | identity142-lander-caller-author makes lander/identity-and-reland-authors fail |

The full setup command runs over a real SQLite store, real signing keys, workspace enrollment
and the real installer, with the existing engine and Tailscale stand-ins and a controlled
service manager and host qualification. It creates two identity records, binds the workspace,
and replays. The credential values are never resolved: only keychain references are input.
Additional binding tests compare logical database contents before and after every refusal.

Worker tests provision two real clones, set a conflicting global user, author and committer,
and pass caller author and committer variables to the launch environment function. Real Git
commands in those clones use the returned environment. The assertions read both local settings
and actual commit authors and committers. The environment test includes unknown future names
under both prefixes and an adapter override reintroduced after the first environment strip.

Landing tests use the real candidate constructor, merges, projection generator and leased
publication against disposable local bare remotes. For each identity they land one unit,
construct another candidate, move trunk with a colleague's commit, observe a lost lease and
construct and publish a new candidate. They inspect twelve landed commits, six merges and
projections per identity. Gate observation and policy acceptance are controlled seams here;
this proves authorship without running a gate. VELDO-0148's dispatch scheduling and approval
logic are not requalified by this suite. The existing re-land fixture now binds its repository
explicitly so the reviewer can run that integration suite against the stricter consumer.

observations.json records the actual identity records and worker and landed commit authors.
verification.json records the honest partial suite exit, each mutant source digest, exact diff,
exit and failed assertions. All five mutations were applied individually to this checkout's
installed source, tested with only suite 103 and restored in finally. Their definitions are
registered as finding 142 in scripts/check_teeth_mutations.py; that driver was not executed.
The scoped replay is proof/VELDO-0142/drive.py. It runs only this specification's suite serially.

The honest result is 37 passed, zero failed: 11 criterion rows plus 26 shared preamble checks.
Subset mode deliberately exits 2. This is scoped behavioral evidence, not a full gate verdict
or a landing approval. Consumer suite fixtures were updated to supply explicit identity
records, with their assertions retained. The landing fixture's policy wrapper also passes its explicit identity reader.
Other specifications' suites remain unrun here under
the owner's token rule. The reviewer must run those and the full gate before landing.
