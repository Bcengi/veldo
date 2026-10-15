# Batch 2 independent-review corrections

Implementation commits: 193c72e7 and eb39d109. This record supersedes the mutation and
current-status claims in round-2026-10-15.md. The review-followup receipts supersede
the review-corrections receipts; earlier receipts remain historical, including their
incomplete AST counts and false claims of no unresolved registrations.
No production module changed in this correction. Verification remains BLOCKED on
consumer and fenced integration execution; no full gate was run.

## Teeth accounting

[teeth-inventory.json](teeth-inventory.json) records every retirement, its reason,
replacement where applicable, and the retained guarantees. Retired names are absent
from the active registry and do not count as kills. The real `cases()` data factory
has 2,556 entries. It had 2,563 at 07eb46ae,
so that comparison is seven fewer; the original seed bb1538f2 had 2,561, so the
seed-to-current comparison is five fewer. The previous 2,452/2,459 counts omitted
104 registrations and were wrong. These are registry counts, not kill counts.
[review-followup-registry.json](review-followup-registry.json) records the factory
counts and every omitted name, covering findings 1, 2, 37, 53, 118, 127, 165, 170 and 173.

- `effects-completion-first-destination` and
  `effects-old-tip-checked-at-first-destination` are retired. With AC3's single URL,
  first-only checks are equivalent to production. Their previous empty-slice
  replacements duplicated removal of the destination-state and old-tip checks.
  `effects-completion-from-exit-status` and `effects-push-without-old-tip-check`
  retain those live guarantees.
- `effects-push-timeout-not-scaled` is retired: destination-count scaling is no longer
  observable with one URL. `effects-push-step-timeout-shortened` honestly names the
  flat one-second timeout defect. It targets the existing slow-receiver row; the
  supervisor deadline still has `effects-call-window-not-extended`. Neither kill
  has executed here: the newly authorized suite 58 attempt stops before its first
  assertion at the sandbox AF_UNIX denial.
- The header, fetch-line, HEAD-line, locale-not-forced and messages-locale-only names
  are retired. Production has no remote-show grammar or locale forcing to remove.
  The unrelated origin-reading and stderr-reading defects are removed.
  `publication-resolution-in-c-locale` is retired with its obsolete C-locale claim.
  Its successful publication check is restored as `publication-resolution-with-locale-env`,
  and the expect loop uses that name. It asserts success under caller-selected locale
  variables, without claiming that the locale is installed or that Git forces C.
  Invalid machine config values and exit statuses remain tested.
  `effects-remote-host-unchecked` falsifies the real host guard;
  `effects-local-config-guard-omitted` names the actual config-guard removal.
- Other obsolete names are accounted for explicitly: authorized-URL state reading
  is now local-state reading, first-destination listing is now a pushurl exemption,
  show-exit is now config-exit, and dry-run output is now actual push output.
- Two additional byte-identical pairs were consolidated. `effects-push-skips-hooks`
  duplicated `identity153-pre-push-hook`; `effects-destination-listing-unchecked`
  duplicated `identity153-url-section`. Only the identity153 registrations remain.
  Their consumer assertions are retained.

`effects-resolution-network-profile` replaces the misleading
`effects-resolution-isolated-profile` name. The unchanged mutant adds
`profile='network'` to both named-remote config reads, admitting global configuration
that production deliberately isolates. The AC3 approval record now names only
`identity153-pre-push-hook` as the active hook falsifier.

Suite 107 now asserts that retired entries stay excluded, replacements exist and
there are no byte-identical mutation definitions among findings 28 and 153. These
checks prevent the observed bookkeeping regressions; they do not prove semantic
non-equivalence for every possible pair.

## Mutation worker and fixture defects

The suite-copy defect was broader than the four reported registrations. The starting
source lacked literal copy anchors for both new suite-58 transport registrations and
20 suite-107 registrations. Suite 58 now copies the transport through an explicit
path. Suite 107 installs explicit module copies before loading either direct imports
or sibling imports. The retired duplicate needs no worker. The static audit now
checks suite-copy anchors for findings 28, 56, 57 and 153 as well as production edit
anchors, and exits nonzero if a current anchor is missing. It reports every unresolved
registration expression regardless of prefix. The AST interpreter now handles the
previously omitted constructs and compares every current registration field against
the isolated `cases()` definition with literal globals and restricted builtins. No
driver imports, entry point, workers or suites are executed for that comparison.
The full audit resolves all 2,556 registrations with zero missing production anchors,
zero unresolved expressions and zero missing suite-copy anchors in the four scoped findings.

The old-tip/failed-listing mutant at scripts/check_teeth_mutations.py:470 now requires
`publication-refused-when-not-at-old-tip`, which actually reaches that guard. Routing
and config-selection assertions cannot falsify it under AC3 and are no longer listed
as required kills. The completion mutant similarly no longer requires the fan-out
row, which refuses before completion is computed. Those assertions remain intact,
and the URL-section falsifier guards fan-out refusal.

The line-break mutant at scripts/check_teeth_mutations.py:513 now uses
`remote.partition('\n')[0]`. It still plants acceptance of a truncated URL, but an
empty URL stays empty and reaches the named refusal instead of raising IndexError.
Its suite-58 kill remains pending reviewer execution.

Removing the identity profile really would bypass fixture URL translation and trip
the fence. The same defect now targets the dedicated socket-free specification suite
108. It calls the real executor receive path and spies on the Git process boundary:
all three transport calls must carry the identity profile and checked URL. The host
falsifier in the same suite calls the actual owner check with invalid config values
and a valid control. No fence exception is swallowed, and no network mapping is
relaxed. Both mutants fail their required rows; restoration passes both rows.

## Reproduction and evidence

`reproduce_refusal.py:15` requires every designated unit kill as a subset of observed
failures. Additional integration failures are allowed when sockets work. Missing a
required unit kill still fails reproduction, and any restored failure still fails it.
Suite 107 checks these three cases with synthetic observations. Its actual red/eager/
restored reproduction also exits 0; integration still stops at AF_UNIX PermissionError.

The refusal reproducer now excludes `target` and its own scratch destination wherever
it occurs under the checkout. A suite-107 fixture tests an arbitrary nested scratch
directory, and the actual red/eager/restored reproduction succeeds with TMPDIR set
to this checkout's `target/veldo-0153`. The receipts still record integration denial.

Four deliberate regression controls restore the missing publication lookup, hide
unresolved prefixes, drop finding 1 from the audit, and copy target artifacts. Each
fails its named evidence row in [review-followup-regressions.json](review-followup-regressions.json).
The fixes were restored, and subsequent suite-107 unit rows have no named failures.

Reproduce the permitted checks sequentially:

```
python3 scripts/selftest.py --suite 58_veldo_0028_effects
python3 scripts/selftest.py --suite 108_veldo_0153_executor_profile
python3 scripts/selftest.py --suite 107_veldo_0153_identity_push
python3 proof/VELDO-0153/reproduce_executor.py "$TMPDIR/executor.json"
python3 proof/VELDO-0153/reproduce_refusal.py "$TMPDIR/refusal.json"
python3 proof/VELDO-0153/audit_anchors.py "$TMPDIR/anchors.json" all
```

Suite 108 reports two suite assertions passed, zero failed; exit 2 is the deliberate
partial-run status, not a gate pass. Suite 107 has no named failures before socket
denial and exits 1. The reproduction scripts run only these specification suites,
one at a time, in disposable copies. They do not run a mutation driver.

Suite 58 exits 1 at `wire.active()` (line 179), whose `socket(AF_UNIX)` raises
`PermissionError: [Errno 1] Operation not permitted`. This occurs before `row()` is
defined or called: **all 57 named row predicates are unexecuted**, including config
selection, network coordinates, authenticated IPC, worker credential reads, every
revocation row and both effect kinds' scope/nonce/completion criteria.
[review-followup-checks.json](review-followup-checks.json) lists every unexecuted name.
Suite 107 completes all 12 evidence assertions and four isolated-import/refusal
assertions without named failures, then stops before its first fence assertion at
the same AF_UNIX denial. None of its fence or `_v153_suite` rows execute.

Fresh receipts are review-followup-checks.json, review-followup-anchors.json,
review-followup-registry.json, review-followup-executor.json,
review-followup-refusal.json and review-followup-regressions.json.
Consumer mutant kills, the mutation drivers, the full gate and real-host
qualification remain unrun here. The reviewer must establish consumer kills and
integration results in an environment allowing AF_UNIX. The manifest distinguishes
fresh selected checks from earlier lint, docs, shape and security evidence.
