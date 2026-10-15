# Global configuration and publication-row review follow-up

Implementation: fe92ae1a. This record supplements review-corrections.md for the two
reported failures. No production module changed. The aggregate gate, consumer suites
and live-host qualification remain unrun; the reviewer owns those checks.

The deleted locale row is already corrected at the supplied dd822f25 baseline.
scripts/suites/58_veldo_0028_effects.py:1099 defines
`publication-resolution-with-locale-env`, and line 1182 lists
`resolution-with-locale-env` in the publication assertion loop. The stale
`resolution-in-c-locale` name is absent from that suite. The existing regression
and falsifier at scripts/suites/107_veldo_0153_identity_push.py:90-97 check every
literal publication-loop entry and then reintroduce the stale locale entry in
memory. Both assertions pass. This follow-up makes their observations explicit in
the suite output so a later socket failure cannot obscure which checks ran.

The global-config mutant had two independent fixture problems. Its unconditional
environment lookup raised KeyError before the isolation assertion; when given the
variable, the integration fixture's later credential calls raised an uncaught
transport refusal. The mutation now uses the disabled global-config default when
the variable is absent. It still honors an explicitly selected hostile global
file, which is the same isolation defect.

The registration now targets the independent real-Git fixture in
scripts/suites/108_veldo_0153_executor_profile.py:4. It exercises both absent and
selected global configuration. Plain Git proves the planted rewrite is live;
the identity profile must resolve the original URL successfully in both cases.
A typed transport refusal fails the isolation assertion. Only credential lookup
is substituted; config inspection and URL resolution use real Git. The command
`ls-remote --get-url` resolves locally without starting transport. The existing
suite-107 global, helper, network and publication integration assertions are intact.

review-global-config-falsifiers.json records sequential suite-108 runs using the
exact registered mutations, read as data through audit_anchors.py. No mutation
driver was invoked. The global-config mutant completes the selected suite and
fails exactly `VELDO-0153 profile/global-config`; its unset-environment control
passes. The two existing executor/host mutants also complete and fail exactly
their required rows. Restored suite 108 reports 32 passed, zero failed (six suite
assertions plus the shared preamble), exit 2, the repository's selected-run status.
The reproducer requires the named failures, completed summary and expected exit;
a crash without a summary cannot count as a kill.

Reproduce with:

```
python3 proof/VELDO-0153/reproduce_executor.py /path/to/observations.json
```

The helper invokes only `python3 scripts/selftest.py --suite
108_veldo_0153_executor_profile`, one run at a time, in a disposable non-git copy.

review-global-config-checks.json records the final suite-107 attempt: publication
registration and stale-row falsifier both pass, no named assertions fail, then
AF_UNIX socket creation raises PermissionError before fenced integration. This is
not an integration pass or a completed suite. Suite 58 was not run under the
owner's own-specification-only restriction. All corresponding engine/.veldo and
.veldo Python files compare byte-identical. No gate byproducts are committed.
