# VELDO-0161 round 11: finding 28's eight survivors

Branch agent/claude/agent/claude/veldo-0161, from f132f399 (round 10). Commit 3986fc00 holds the change; this
evidence and the specifications' history follow it. Run on the host. Nothing here is a gate result, a review
verdict or an approval: the selftest run is a partial run and `./scripts/verify.sh` was not run. Every result is
in `host-runs.json` beside this file.

## What was wrong

Round 10 found eight finding-28 cases (scripts/check_teeth_mutations.py) that survived at f132f399 and at the
VELDO-0153 base b44736c0 with suite 58 running to its end. The mutation stage counts a case killed only when EVERY
row it targets turns red. VELDO-0153 rewrote the suite 58 rows these cases targeted, so each case kept at least
one target that the mutated code can no longer reach: a row that now judges the identity profile, or a refusal
made before anything is recorded. The registrations were never updated. No mutation was removed and no row was
weakened to fix it.

## The eight cases now

| Case (module) | Targets at f132f399 | Targets now | Why |
| --- | --- | --- | --- |
| effects-push-by-send-pack (control_effect_executor) | pre-push-hook, url-rewrite, smart-http | pre-push-hook, smart-http | url-rewrite expects `binding_mismatch:identity_transport_config` before any push (0153 AC3), so it cannot see the push's form. The other two turn red on the mutant. |
| effects-destination-not-recorded (control_effects) | records-resolved-destination, destination-without-credentials | records-resolved-destination | destination-without-credentials is refused `binding_mismatch:remote_host` before any record (0153 AC2), so a dropped record leaks nothing it could see. |
| effects-destination-with-credentials (control_effect_executor) | destination-without-credentials | record-scrubs-destination (new) | See below. |
| effects-destinations-not-scrubbed (control_effect_executor) | destination-without-credentials, scrub-transport-prefix | record-scrubs-destination (new) | See below. |
| effects-network-profile-without-global-config (git_process) | global-insteadof, global-credential-helper, global-ssh-command, config-selection-parity | network-profile-strips-coordinates | Publication runs in the identity profile (0153 AC1), so the publication rows no longer reach the network profile. This row reads `clean_env(profile='network')` directly and requires every transport and configuration variable kept as given. |
| effects-network-profile-drops-transport-variables (git_process) | env-ssh-command | network-profile-strips-coordinates | Same. |
| effects-network-profile-drops-config-selection (git_process) | config-selection-parity, network-profile-strips-coordinates | network-profile-strips-coordinates | Same; config-selection-parity judges the identity push. |
| effects-network-profile-drops-config-injection (git_process) | config-selection-parity, network-profile-strips-coordinates | network-profile-strips-coordinates | Same. |

Every row named is `effects/publication-<name>` in scripts/suites/58_veldo_0028_effects.py. No old target was kept
where it cannot turn red, because the stage would then count the case as surviving whatever the other targets do.

## The record site's scrubbing, and the new row

`receive()` builds the publication record with `scrubbed_url(remote)` and `scrubbed_url(url)` for each destination.
VELDO-0153's `check_remote` runs before that and refuses user information other than ssh `git`, a query, a
fragment, any port but the scheme's own and anything not https or ssh on github.com. So no destination that
reaches the record through the executor can carry a credential, and the existing scrub rows call `scrubbed_url`
itself, never the record site. That is why the two mutants that skip the record's scrubbing could not be killed.

The scrubbing is not dead code. It runs on every publication, and for an ssh identity it changes the record:
`ssh://git@github.com/fixture/x.git` is recorded `ssh://github.com/fixture/x.git` and `git@github.com:fixture/x.git`
is recorded `github.com:fixture/x.git` (checked on the host against .veldo/control_effect_executor.py). Against a
credential it is defense in depth behind the owner check, so it stays and stays tested.

New row `effects/publication-record-scrubs-destination` runs the receiver (`receive`) in the suite's own process,
where the owner check can be replaced for that one call, with a stand-in owner check that lets the destination
through: it hands the real `check_remote` the destination with its user information, query, fragment and transport
prefix removed. Four destinations, each to a fresh bare repository that the identity wire maps from the literal
destination text, so the identity push and both listings are real:

| Case | Destination | Recorded URL required |
| --- | --- | --- |
| userinfo | `https://<user>:<password>@github.com/fixture/record-userinfo.git` | `https://github.com/fixture/record-userinfo.git` |
| query | `https://github.com/fixture/record-query.git?private_token=<token>` | `https://github.com/fixture/record-query.git` |
| fragment | `https://github.com/fixture/record-fragment.git#<token>` | `https://github.com/fixture/record-fragment.git` |
| transport | `veldotest::https://<user>:<password>@github.com/fixture/record-transport.git` | `veldotest::https://github.com/fixture/record-transport.git` |

The fake values are the suite's run-time assembled `_V28_U`, `_V28_P` and `_V28_T`. For each case the row requires:
the real `check_remote` refuses the destination (the control that only the defense in depth is exercised), the
publication completes and the bare repository holds the tip, the record is exactly
`{'authorized_url': <recorded URL>, 'destinations': [{'url': <recorded URL>, 'outcome': 'at-tip'}]}`, and no fake
credential appears in the answer or in the identity events. The real check is restored after each call.

The row is green on the honest code and red on both mutants (worker stdout in the 8-case run shows it `[false]`
under effects-destination-with-credentials and effects-destinations-not-scrubbed).

A row that publishes over ssh through the executor, end to end, would also reach the record site on the
production path (the `git@` user above). Suite 58's fixture repository is bound to a token identity, which refuses
an ssh remote (`binding_mismatch:push_transport`), so that row needs a second, ssh-bound repository in the suite. It
is not added here; it is a possible later addition, not a gap in what these two cases judge.

## Host results at 3986fc00

1. `python3 scripts/selftest.py --suite 58_veldo_0028_effects`: exit 2 (a partial run, by design), 78 passed,
   0 failed in 36.35s. Round 10 had 77; the new row is the 78th.
2. `python3 scripts/check_gate_mutations.py --root $(pwd -P)` with the eight cases by `--case`: passed, 8
   registered, 8 executed, 8 killed, 14 workers all exit 0.
3. Same with `--finding 28`: passed, 73 of 73 killed (65 of 73 before), 85 workers all exit 0, no driver_error,
   no invalid result, no surviving worker.
4. Same with `--finding 161 --finding 56`: passed, 79 of 79 killed (161: 57 of 57; 56: 22 of 22, as at round 10),
   95 workers all exit 0.

Each run used its own `--receipt` and `--worker-log-dir` under /tmp/v161g; the receipts' sha256 are in
`host-runs.json`. Only finding 28 registers cases against suite 58, so no other finding's cases read the rows
changed here.
