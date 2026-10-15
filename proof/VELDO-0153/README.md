# VELDO-0153 review fixes

Current batch-2 record: [2026-10-15](round-2026-10-15.md). The remaining text and earlier
JSON receipts below are historical. The current manifest names the final code commit
and retains incomplete integration and host qualification explicitly.

Identity Git transport creates an empty private directory for each invocation and uses
it for HOME, XDG_CONFIG_HOME and hooksPath until Git exits. Pushes also disable the
pre-push hook. The configuration inspection follows includes in the local and worktree
scopes. Routing and authentication overrides, including URL-named remote sections,
refuse before transport. The positional destination must be the checked literal URL.

Both the lander's watermark fetch and the landing service's remote listing now use
the identity profile. The operator's network profile is unchanged. Missing credentials
never fall back to ambient authentication.

Executor observations are git_identity_operation entities written through the signed
command path. Direct-lander observations are flushed and fsynced to
`veldo-identity-operations.jsonl` in the Git common directory, outside the disposable
candidate. A new lander instance reads durable push and refusal counts. Successful and
refused observations report the owner actually parsed by the owner check.

| Review item | Regression rows | Registered falsifiers |
| --- | --- | --- |
| Private HOME and netrc | profile/netrc, profile/check-output-home, profile/private-home-cleaned | identity153-netrc |
| Included config | profile/include, profile/include-if | identity153-includes |
| Worktree config | profile/worktree-config | identity153-worktree |
| URL-named remotes | profile/url-section-url, profile/url-section-pushurl | identity153-url-section |
| Push hooks | profile/pre-push-hook/alpha | identity153-pre-push-hook |
| Literal destination | profile/literal-destination | identity153-literal-destination |
| Identity network reads | lander/watermark-identity, landing/list-identity | identity153-watermark-network, identity153-listing-network |
| Signed observations | executor/signed-observations, executor/execute-signed, executor/refused-signed | identity153-unsigned-observations |
| Durable counts | lander/alpha/durable, executor/durable, lander/alpha/beta/refusals-durable | identity153-volatile-counts |
| Parsed owner logging | lander/owner-spelling | identity153-configured-owner-log |
| Global config isolation | profile/global-config | identity153-global-config |

The original planted-helper and host-only owner falsifiers remain registered. Each
falsifier is applied to canonical and installed copies, runs the named 0153 suite alone,
and restores both files in a finally block. No repository mutation driver is run.
`falsifiers.json` records the expected failing rows, actual failing labels and exit codes.
A permission error or setup failure alone does not count as rejecting a falsifier.

`observations.json` contains the 0153 rows. `verification.json` records the exact scoped
run and source hashes. `consumer-suites.json` contains the individually selected consumer
runs and failures; `baseline-comparison.json` compares selected failing consumers with
starting commit aaef5980. These are partial observations, not aggregate unit evidence,
a green gate, a review verdict or permission to land.

## Executed results

The restored 0153 suite passed 91 named rows and 26 shared assertions. All 14
falsifiers failed at their expected rows. The dispatcher returned partial-run exit 2
for the positive run; no aggregate pass is claimed.

Of 68 individually selected consumer suites, 30 passed, 26 finished with failures,
and 12 stopped before a summary. Four further consumers invoke prohibited mutation
drivers and were deferred to the reviewer. Exact labels and incomplete-run diagnostics
are in consumer-suites.json. Permission failures do not count as guard refusals.

Baseline comparisons reproduced identical failure labels in the effects, landing and
relanding suites. The identity-author suite adds the worker-commit-mismatch failure;
the candidate suite adds git-failures-refuse and every-git-operation-checked failures.
These rows use file-remote fixtures and stop at the newly protected watermark fetch.
Their fixtures still need identity-aware transport adapters. The production profile
continues to refuse file remotes. Consumer verification remains red.

## Host qualification

The host driver is `proof/VELDO-0153/host_check.py`. It accepts an absolute JSON config
path with a `repositories` array containing at least two complete identity records,
their disposable GitHub remote URLs and two mismatched owners per entry. Both token
and SSH credential kinds must be represented. Credentials must already be stored as
Secret Service references. SSH references resolve to absolute key paths.

The driver requires an accessible SSH agent and verifies both key fingerprints and the
GitHub usernames authenticated by the selected key and the agent. The usernames must
differ; another key for the same user is rejected. Offline rows also reject a missing
agent username or one differing only in case. The driver plants a global helper,
system rewrite, netrc, included rewrite and ambient SSH command. The included rewrite
must be refused before it is removed for the push legs. Branches created on the
disposable repositories remain for independent inspection.

Host qualification was not run. No live pushes or real credentials were used. The
reviewer owns the aggregate gate and landing stamp. VELDO-0143's absent provisioner
must use this same owner check and profile for its creation/adoption integrations.
