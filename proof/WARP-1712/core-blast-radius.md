# Required-evidence impact

Actual old and proposed check_required_evidence; declared corpus membership; spec_id join. Groups overlap. Non-passing includes all unknown outcomes, not just failed/pending. Check name only means a named check without a passing outcome.

```json
{
  "specs": 184,
  "manifests": 173,
  "matched_pairs": 173,
  "unmatched": 0,
  "changed_pairs": 107,
  "spec_parse_errors": 6,
  "pair_parse_errors": 5,
  "old_pass": 168,
  "new_pass": 61,
  "by_cause": {
    "check name only": 12,
    "result absent": 106,
    "result failed or pending": 12,
    "unit test presented as integration": 38
  }
}
```

## check name only

| Spec | Proof | Verdict |
| --- | --- | --- |
| specs/VELDO-0160-the-suite-states-the-defect-instead-of-certifying-it.md | proof/VELDO-0160/manifest.json | pass -> fail |
| specs/VELDO-0161-every-interface-has-a-test-that-a-caller-without-credentials-is-refused.md | proof/VELDO-0161/manifest.json | pass -> fail |
| specs/VELDO-0180-a-refusal-test-proves-the-refusal-it-names.md | proof/VELDO-0180/manifest.json | pass -> fail |
| specs/VELDO-0360-a-caller-nobody-established-is-refused-before-the-handler.md | proof/VELDO-0360/manifest.json | pass -> fail |
| specs/VELDO-0361-a-session-from-a-peer-that-never-associated-is-not-dispatched.md | proof/VELDO-0361/manifest.json | pass -> fail |
| specs/VELDO-0370-a-merge-is-proven-by-a-record-of-its-own.md | proof/VELDO-0370/manifest.json | pass -> fail |
| specs/VELDO-0371-what-a-merge-changed-is-the-content-that-is-in-neither-parent.md | proof/VELDO-0371/manifest.json | pass -> fail |
| specs/VELDO-0380-continuous-integration-tells-a-declared-red-from-a-regression.md | proof/VELDO-0380/manifest.json | pass -> fail |
| specs/VELDO-0381-where-else-the-rule-lives.md | proof/VELDO-0381/manifest.json | pass -> fail |
| specs/VELDO-0440-a-credit-control-request-is-served-as-the-peer-the-exchange-named.md | proof/VELDO-0440/manifest.json | pass -> fail |
| specs/VELDO-0450-a-charging-decision-is-taken-only-for-the-tenant-the-subscriber-belongs-to.md | proof/VELDO-0450/manifest.json | pass -> fail |
| specs/VELDO-0470-the-same-walk-every-time.md | proof/VELDO-0470/manifest.json | pass -> fail |

## result absent

| Spec | Proof | Verdict |
| --- | --- | --- |
| specs/DEV-1175-ngap-tunnel-allowance-binding.md | proof/DEV-1175/manifest.json | pass -> fail |
| specs/DEV-1191-release-ownership-and-create-recovery.md | proof/DEV-1191/manifest.json | pass -> fail |
| specs/VELDO-0007-charging-proven-against-a-real-database.md | proof/VELDO-0007/manifest.json | pass -> fail |
| specs/VELDO-0022-a-hold-is-a-named-row-with-one-owner.md | proof/VELDO-0022/manifest.json | pass -> fail |
| specs/VELDO-0023-one-conversation-per-epoch-one-durable-answer-per-request.md | proof/VELDO-0023/manifest.json | pass -> fail |
| specs/VELDO-0024-a-durable-name-is-unique-everywhere.md | proof/VELDO-0024/manifest.json | pass -> fail |
| specs/VELDO-0025-a-create-is-claimed-under-the-callers-key.md | proof/VELDO-0025/manifest.json | pass -> fail |
| specs/VELDO-0031-the-create-key-names-the-intent.md | proof/VELDO-0031/manifest.json | pass -> fail |
| specs/VELDO-0032-an-evicted-session-never-keeps-a-hold.md | proof/VELDO-0032/manifest.json | pass -> fail |
| specs/VELDO-0033-the-refusal-cause-survives-the-client.md | proof/VELDO-0033/manifest.json | pass -> fail |
| specs/VELDO-0060-the-review-classes-get-a-mechanical-refusal.md | proof/VELDO-0060/manifest.json | pass -> fail |
| specs/VELDO-0084-the-walker-catches-up-with-the-merged-charging-stack.md | proof/VELDO-0084/manifest.json | pass -> fail |
| specs/VELDO-0130-a-request-is-served-by-the-subject-it-names.md | proof/VELDO-0130/manifest.json | pass -> fail |
| specs/VELDO-0131-a-grant-is-bounded-by-what-the-hold-can-pay-for.md | proof/VELDO-0131/manifest.json | pass -> fail |
| specs/VELDO-0132-a-report-is-named-by-an-identifier-its-caller-sends.md | proof/VELDO-0132/manifest.json | pass -> fail |
| specs/VELDO-0133-the-search-cannot-report-a-clean-sweep-of-nothing.md | proof/VELDO-0133/manifest.json | pass -> fail |
| specs/VELDO-0140-a-request-is-identified-by-the-party-it-is-about.md | proof/VELDO-0140/manifest.json | pass -> fail |
| specs/VELDO-0141-the-search-reaches-the-two-customer-sequence.md | proof/VELDO-0141/manifest.json | pass -> fail |
| specs/VELDO-0142-a-reported-figure-is-bounded-and-never-runs-backwards.md | proof/VELDO-0142/manifest.json | pass -> fail |
| specs/VELDO-0143-the-answer-carries-the-reference-the-decision-returned.md | proof/VELDO-0143/manifest.json | pass -> fail |
| specs/VELDO-0150-a-refusal-tells-the-caller-only-about-its-own-request.md | proof/VELDO-0150/manifest.json | pass -> fail |
| specs/VELDO-0151-a-floor-under-a-set-a-check-may-be-empty-about.md | proof/VELDO-0151/manifest.json | pass -> fail |
| specs/VELDO-0160-the-suite-states-the-defect-instead-of-certifying-it.md | proof/VELDO-0160/manifest.json | pass -> fail |
| specs/VELDO-0161-every-interface-has-a-test-that-a-caller-without-credentials-is-refused.md | proof/VELDO-0161/manifest.json | pass -> fail |
| specs/VELDO-0162-the-merge-guard-is-wired-and-has-been-watched-refuse.md | proof/VELDO-0162/manifest.json | pass -> fail |
| specs/VELDO-0170-an-answer-tells-the-caller-only-its-own-request.md | proof/VELDO-0170/manifest.json | pass -> fail |
| specs/VELDO-0171-a-post-paid-report-is-answered-once.md | proof/VELDO-0171/manifest.json | pass -> fail |
| specs/VELDO-0180-a-refusal-test-proves-the-refusal-it-names.md | proof/VELDO-0180/manifest.json | pass -> fail |
| specs/VELDO-0190-key-material-cannot-be-formatted-or-served.md | proof/VELDO-0190/manifest.json | pass -> fail |
| specs/VELDO-0200-measured-usage-reaches-the-charging-path.md | proof/VELDO-0200/manifest.json | pass -> fail |
| specs/VELDO-0201-a-spent-grant-stops-the-session-in-the-packet-path.md | proof/VELDO-0201/manifest.json | pass -> fail |
| specs/VELDO-0210-a-report-is-charged-at-the-grant-that-authorised-it.md | proof/VELDO-0210/manifest.json | pass -> fail |
| specs/VELDO-0220-a-claim-cannot-poison-the-session-it-is-about.md | proof/VELDO-0220/manifest.json | pass -> fail |
| specs/VELDO-0221-a-grant-bounds-the-packet-path.md | proof/VELDO-0221/manifest.json | pass -> fail |
| specs/VELDO-0222-the-record-commits-with-the-money.md | proof/VELDO-0222/manifest.json | pass -> fail |
| specs/VELDO-0230-a-packet-is-attributed-by-the-tunnel-it-arrived-on.md | proof/VELDO-0230/manifest.json | pass -> fail |
| specs/VELDO-0231-a-session-command-is-served-only-for-the-peer-that-owns-it.md | proof/VELDO-0231/manifest.json | pass -> fail |
| specs/VELDO-0232-a-renewal-does-not-give-away-the-tail.md | proof/VELDO-0232/manifest.json | pass -> fail |
| specs/VELDO-0240-a-boundary-decides-reach-not-the-caller.md | proof/VELDO-0240/manifest.json | pass -> fail |
| specs/VELDO-0241-the-roaming-boundary-forwards-only-where-we-said-it-may.md | proof/VELDO-0241/manifest.json | pass -> fail |
| specs/VELDO-0242-the-console-decides-whose-data-a-request-touches.md | proof/VELDO-0242/manifest.json | pass -> fail |
| specs/VELDO-0250-a-decoder-refuses-hostile-input-rather-than-panicking.md | proof/VELDO-0250/manifest.json | pass -> fail |
| specs/VELDO-0260-a-subscriber-cannot-reach-the-user-planes-own-control-surfaces.md | proof/VELDO-0260/manifest.json | pass -> fail |
| specs/VELDO-0261-the-user-plane-reads-its-own-settings-from-its-own-file.md | proof/VELDO-0261/manifest.json | pass -> fail |
| specs/VELDO-0262-usage-carried-since-the-last-tick-survives-the-tunnel.md | proof/VELDO-0262/manifest.json | pass -> fail |
| specs/VELDO-0270-the-transport-may-not-change-a-decided-request.md | proof/VELDO-0270/manifest.json | pass -> fail |
| specs/VELDO-0271-the-tenant-boundary-reaches-every-transport.md | proof/VELDO-0271/manifest.json | pass -> fail |
| specs/VELDO-0280-a-usage-report-is-charged-only-for-the-user-plane-that-owns-the-session.md | proof/VELDO-0280/manifest.json | pass -> fail |
| specs/VELDO-0281-uplink-from-an-address-that-is-not-the-tunnels-base-station-is-refused.md | proof/VELDO-0281/manifest.json | pass -> fail |
| specs/VELDO-0290-an-answer-belongs-to-the-request-that-asked-for-it.md | proof/VELDO-0290/manifest.json | pass -> fail |
| specs/VELDO-0291-enabling-the-xdp-path-would-remove-three-protections-and-is-refused.md | proof/VELDO-0291/manifest.json | pass -> fail |
| specs/VELDO-0300-deleting-a-tenant-never-widens-a-scope.md | proof/VELDO-0300/manifest.json | pass -> fail |
| specs/VELDO-0301-a-decision-and-the-write-it-authorises-are-one-operation.md | proof/VELDO-0301/manifest.json | pass -> fail |
| specs/VELDO-0302-authority-is-the-record-not-the-token.md | proof/VELDO-0302/manifest.json | pass -> fail |
| specs/VELDO-0303-a-record-is-scoped-by-where-it-happened.md | proof/VELDO-0303/manifest.json | pass -> fail |
| specs/VELDO-0320-the-xdp-data-plane-enforces-the-three-protections-the-userspace-forwarder-does.md | proof/VELDO-0320/manifest.json | pass -> fail |
| specs/VELDO-0321-a-decision-table-in-a-doc-comment-is-prose-not-a-rust-example.md | proof/VELDO-0321/manifest.json | pass -> fail |
| specs/VELDO-0323-the-suite-audit-covers-the-suite-that-exists.md | proof/VELDO-0323/manifest.json | pass -> fail |
| specs/VELDO-0324-the-interface-census-catches-up-with-the-doors-that-exist.md | proof/VELDO-0324/manifest.json | pass -> fail |
| specs/VELDO-0360-a-caller-nobody-established-is-refused-before-the-handler.md | proof/VELDO-0360/manifest.json | pass -> fail |
| specs/VELDO-0361-a-session-from-a-peer-that-never-associated-is-not-dispatched.md | proof/VELDO-0361/manifest.json | pass -> fail |
| specs/VELDO-0370-a-merge-is-proven-by-a-record-of-its-own.md | proof/VELDO-0370/manifest.json | pass -> fail |
| specs/VELDO-0371-what-a-merge-changed-is-the-content-that-is-in-neither-parent.md | proof/VELDO-0371/manifest.json | pass -> fail |
| specs/VELDO-0380-continuous-integration-tells-a-declared-red-from-a-regression.md | proof/VELDO-0380/manifest.json | pass -> fail |
| specs/VELDO-0381-where-else-the-rule-lives.md | proof/VELDO-0381/manifest.json | pass -> fail |
| specs/VELDO-0390-authentication-succeeds-only-when-the-response-is-present-parsed-and-equal.md | proof/VELDO-0390/manifest.json | pass -> fail |
| specs/VELDO-0440-a-credit-control-request-is-served-as-the-peer-the-exchange-named.md | proof/VELDO-0440/manifest.json | pass -> fail |
| specs/VELDO-0450-a-charging-decision-is-taken-only-for-the-tenant-the-subscriber-belongs-to.md | proof/VELDO-0450/manifest.json | pass -> fail |
| specs/VELDO-0470-the-same-walk-every-time.md | proof/VELDO-0470/manifest.json | pass -> fail |
| specs/VELDO-0500-a-timing-check-compares-a-ratio-not-two-positions-on-a-clock.md | proof/VELDO-0500/manifest.json | pass -> fail |
| specs/VELDO-0510-the-judge-and-the-line-it-looks-for-are-asserted-to-agree.md | proof/VELDO-0510/manifest.json | pass -> fail |
| specs/VELDO-0520-a-write-that-changes-who-can-authenticate-carries-the-callers-admission.md | proof/VELDO-0520/manifest.json | pass -> fail |
| specs/VELDO-0530-every-identity-composition-site-says-whether-the-subject-is-part-of-it.md | proof/VELDO-0530/manifest.json | pass -> fail |
| specs/VELDO-0620-a-published-policy-reaches-a-running-core.md | proof/VELDO-0620/manifest.json | pass -> fail |
| specs/VELDO-0630-credit-is-an-exhaustible-balance.md | proof/VELDO-0630/manifest.json | pass -> fail |
| specs/VELDO-0640-a-credit-limit-is-spendable.md | proof/VELDO-0640/manifest.json | pass -> fail |
| specs/VELDO-0650-a-payment-settles-the-credit-it-was-spent-against.md | proof/VELDO-0650/manifest.json | pass -> fail |
| specs/VELDO-0660-a-payment-holds-the-ownership-it-depends-on.md | proof/VELDO-0660/manifest.json | pass -> fail |
| specs/VELDO-0670-a-balance-read-answers-from-one-statement.md | proof/VELDO-0670/manifest.json | pass -> fail |
| specs/VELDO-0680-a-claim-carries-the-tenant-it-was-made-for.md | proof/VELDO-0680/manifest.json | pass -> fail |
| specs/VELDO-0690-the-browser-sends-no-price-nobody-entered.md | proof/VELDO-0690/manifest.json | pass -> fail |
| specs/VELDO-0700-a-price-the-api-accepts-and-the-browser-refuses.md | proof/VELDO-0700/manifest.json | pass -> fail |
| specs/VELDO-0710-an-import-carries-only-what-the-file-says.md | proof/VELDO-0710/manifest.json | pass -> fail |
| specs/VELDO-0720-a-blocked-column-is-read-or-it-is-not-there.md | proof/VELDO-0720/manifest.json | pass -> fail |
| specs/VELDO-0730-a-record-is-as-wide-as-its-header.md | proof/VELDO-0730/manifest.json | pass -> fail |
| specs/VELDO-0740-a-blocking-instruction-survives-every-path.md | proof/VELDO-0740/manifest.json | pass -> fail |
| specs/VELDO-0750-which-column-is-the-price-is-decided-without-guessing.md | proof/VELDO-0750/manifest.json | pass -> fail |
| specs/VELDO-0760-a-price-column-is-named-exactly-or-the-file-is-refused.md | proof/VELDO-0760/manifest.json | pass -> fail |
| specs/VELDO-0770-a-price-list-is-applied-in-full-or-not-at-all.md | proof/VELDO-0770/manifest.json | pass -> fail |
| specs/VELDO-0780-no-column-is-chosen-by-position.md | proof/VELDO-0780/manifest.json | pass -> fail |
| specs/VELDO-0790-a-published-rate-book-reaches-a-running-core.md | proof/VELDO-0790/manifest.json | pass -> fail |
| specs/VELDO-0800-which-network-a-row-is-about-is-stated-or-refused.md | proof/VELDO-0800/manifest.json | pass -> fail |
| specs/VELDO-0810-half-an-identity-is-not-an-identity.md | proof/VELDO-0810/manifest.json | pass -> fail |
| specs/VELDO-0820-the-api-compares-identities-and-the-wildcard-is-refused.md | proof/VELDO-0820/manifest.json | pass -> fail |
| specs/VELDO-0830-a-create-is-a-create.md | proof/VELDO-0830/manifest.json | pass -> fail |
| specs/VELDO-0840-seven-routes-that-decide-access-have-now-been-run.md | proof/VELDO-0840/manifest.json | pass -> fail |
| specs/VELDO-0850-a-grant-settles-at-the-tariff-that-authorised-it.md | proof/VELDO-0850/manifest.json | pass -> fail |
| specs/VELDO-0860-one-answer-to-whether-a-network-may-carry-traffic.md | proof/VELDO-0860/manifest.json | pass -> fail |
| specs/VELDO-0870-an-unavailable-network-stops-the-sessions-already-on-it.md | proof/VELDO-0870/manifest.json | pass -> fail |
| specs/VELDO-0880-the-answer-says-whether-the-session-is-over.md | proof/VELDO-0880/manifest.json | pass -> fail |
| specs/VELDO-0890-an-agreement-carries-traffic-only-while-it-is-in-force.md | proof/VELDO-0890/manifest.json | pass -> fail |
| specs/VELDO-0900-a-grants-deadline-reaches-the-user-plane.md | proof/VELDO-0900/manifest.json | pass -> fail |
| specs/VELDO-0910-a-quiet-session-still-counts-the-time-that-passes.md | proof/VELDO-0910/manifest.json | pass -> fail |
| specs/VELDO-0920-charging-is-not-a-passenger-on-the-analytics-feed.md | proof/VELDO-0920/manifest.json | pass -> fail |
| specs/VELDO-0930-a-report-is-owned-until-it-is-answered.md | proof/VELDO-0930/manifest.json | pass -> fail |
| specs/VELDO-0950-one-authority-decision-for-every-network-function-door.md | proof/VELDO-0950/manifest.json | pass -> fail |

## result failed or pending

| Spec | Proof | Verdict |
| --- | --- | --- |
| specs/VELDO-0160-the-suite-states-the-defect-instead-of-certifying-it.md | proof/VELDO-0160/manifest.json | pass -> fail |
| specs/VELDO-0161-every-interface-has-a-test-that-a-caller-without-credentials-is-refused.md | proof/VELDO-0161/manifest.json | pass -> fail |
| specs/VELDO-0180-a-refusal-test-proves-the-refusal-it-names.md | proof/VELDO-0180/manifest.json | pass -> fail |
| specs/VELDO-0360-a-caller-nobody-established-is-refused-before-the-handler.md | proof/VELDO-0360/manifest.json | pass -> fail |
| specs/VELDO-0361-a-session-from-a-peer-that-never-associated-is-not-dispatched.md | proof/VELDO-0361/manifest.json | pass -> fail |
| specs/VELDO-0370-a-merge-is-proven-by-a-record-of-its-own.md | proof/VELDO-0370/manifest.json | pass -> fail |
| specs/VELDO-0371-what-a-merge-changed-is-the-content-that-is-in-neither-parent.md | proof/VELDO-0371/manifest.json | pass -> fail |
| specs/VELDO-0380-continuous-integration-tells-a-declared-red-from-a-regression.md | proof/VELDO-0380/manifest.json | pass -> fail |
| specs/VELDO-0381-where-else-the-rule-lives.md | proof/VELDO-0381/manifest.json | pass -> fail |
| specs/VELDO-0440-a-credit-control-request-is-served-as-the-peer-the-exchange-named.md | proof/VELDO-0440/manifest.json | pass -> fail |
| specs/VELDO-0450-a-charging-decision-is-taken-only-for-the-tenant-the-subscriber-belongs-to.md | proof/VELDO-0450/manifest.json | pass -> fail |
| specs/VELDO-0470-the-same-walk-every-time.md | proof/VELDO-0470/manifest.json | pass -> fail |

## unit test presented as integration

| Spec | Proof | Verdict |
| --- | --- | --- |
| specs/DEV-1191-release-ownership-and-create-recovery.md | proof/DEV-1191/manifest.json | pass -> fail |
| specs/VELDO-0084-the-walker-catches-up-with-the-merged-charging-stack.md | proof/VELDO-0084/manifest.json | pass -> fail |
| specs/VELDO-0130-a-request-is-served-by-the-subject-it-names.md | proof/VELDO-0130/manifest.json | pass -> fail |
| specs/VELDO-0131-a-grant-is-bounded-by-what-the-hold-can-pay-for.md | proof/VELDO-0131/manifest.json | pass -> fail |
| specs/VELDO-0132-a-report-is-named-by-an-identifier-its-caller-sends.md | proof/VELDO-0132/manifest.json | pass -> fail |
| specs/VELDO-0133-the-search-cannot-report-a-clean-sweep-of-nothing.md | proof/VELDO-0133/manifest.json | pass -> fail |
| specs/VELDO-0140-a-request-is-identified-by-the-party-it-is-about.md | proof/VELDO-0140/manifest.json | pass -> fail |
| specs/VELDO-0141-the-search-reaches-the-two-customer-sequence.md | proof/VELDO-0141/manifest.json | pass -> fail |
| specs/VELDO-0142-a-reported-figure-is-bounded-and-never-runs-backwards.md | proof/VELDO-0142/manifest.json | pass -> fail |
| specs/VELDO-0143-the-answer-carries-the-reference-the-decision-returned.md | proof/VELDO-0143/manifest.json | pass -> fail |
| specs/VELDO-0150-a-refusal-tells-the-caller-only-about-its-own-request.md | proof/VELDO-0150/manifest.json | pass -> fail |
| specs/VELDO-0151-a-floor-under-a-set-a-check-may-be-empty-about.md | proof/VELDO-0151/manifest.json | pass -> fail |
| specs/VELDO-0170-an-answer-tells-the-caller-only-its-own-request.md | proof/VELDO-0170/manifest.json | pass -> fail |
| specs/VELDO-0171-a-post-paid-report-is-answered-once.md | proof/VELDO-0171/manifest.json | pass -> fail |
| specs/VELDO-0200-measured-usage-reaches-the-charging-path.md | proof/VELDO-0200/manifest.json | pass -> fail |
| specs/VELDO-0201-a-spent-grant-stops-the-session-in-the-packet-path.md | proof/VELDO-0201/manifest.json | pass -> fail |
| specs/VELDO-0210-a-report-is-charged-at-the-grant-that-authorised-it.md | proof/VELDO-0210/manifest.json | pass -> fail |
| specs/VELDO-0220-a-claim-cannot-poison-the-session-it-is-about.md | proof/VELDO-0220/manifest.json | pass -> fail |
| specs/VELDO-0221-a-grant-bounds-the-packet-path.md | proof/VELDO-0221/manifest.json | pass -> fail |
| specs/VELDO-0222-the-record-commits-with-the-money.md | proof/VELDO-0222/manifest.json | pass -> fail |
| specs/VELDO-0230-a-packet-is-attributed-by-the-tunnel-it-arrived-on.md | proof/VELDO-0230/manifest.json | pass -> fail |
| specs/VELDO-0231-a-session-command-is-served-only-for-the-peer-that-owns-it.md | proof/VELDO-0231/manifest.json | pass -> fail |
| specs/VELDO-0232-a-renewal-does-not-give-away-the-tail.md | proof/VELDO-0232/manifest.json | pass -> fail |
| specs/VELDO-0241-the-roaming-boundary-forwards-only-where-we-said-it-may.md | proof/VELDO-0241/manifest.json | pass -> fail |
| specs/VELDO-0242-the-console-decides-whose-data-a-request-touches.md | proof/VELDO-0242/manifest.json | pass -> fail |
| specs/VELDO-0250-a-decoder-refuses-hostile-input-rather-than-panicking.md | proof/VELDO-0250/manifest.json | pass -> fail |
| specs/VELDO-0251-the-metrics-listener-changes-nothing.md | proof/VELDO-0251/manifest.json | pass -> fail |
| specs/VELDO-0270-the-transport-may-not-change-a-decided-request.md | proof/VELDO-0270/manifest.json | pass -> fail |
| specs/VELDO-0271-the-tenant-boundary-reaches-every-transport.md | proof/VELDO-0271/manifest.json | pass -> fail |
| specs/VELDO-0280-a-usage-report-is-charged-only-for-the-user-plane-that-owns-the-session.md | proof/VELDO-0280/manifest.json | pass -> fail |
| specs/VELDO-0281-uplink-from-an-address-that-is-not-the-tunnels-base-station-is-refused.md | proof/VELDO-0281/manifest.json | pass -> fail |
| specs/VELDO-0290-an-answer-belongs-to-the-request-that-asked-for-it.md | proof/VELDO-0290/manifest.json | pass -> fail |
| specs/VELDO-0300-deleting-a-tenant-never-widens-a-scope.md | proof/VELDO-0300/manifest.json | pass -> fail |
| specs/VELDO-0301-a-decision-and-the-write-it-authorises-are-one-operation.md | proof/VELDO-0301/manifest.json | pass -> fail |
| specs/VELDO-0302-authority-is-the-record-not-the-token.md | proof/VELDO-0302/manifest.json | pass -> fail |
| specs/VELDO-0303-a-record-is-scoped-by-where-it-happened.md | proof/VELDO-0303/manifest.json | pass -> fail |
| specs/VELDO-0530-every-identity-composition-site-says-whether-the-subject-is-part-of-it.md | proof/VELDO-0530/manifest.json | pass -> fail |
| specs/VELDO-0950-one-authority-decision-for-every-network-function-door.md | proof/VELDO-0950/manifest.json | pass -> fail |
