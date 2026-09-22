# Parser corpus comparison before migration

Baseline: `34342c3`. New reader: `6b2135a`. No caller or corpus document changed before this measurement.

Enumerated **331** real specification/plan documents; **330** have front matter.
**331** differ for at least one existing reader; **88** are refused by the new reader.

The JSON report lists every document, its input digest, and exact old/new values at each changed field for each reader. A refusal records the diagnostic and the old value rather than pretending the document is absent. The additional YAML section measures substrate configurations separately from the historical denominator.

## New-reader refusals

- `plans/PLAN-0009-fleet-distribution.md`: <text>:258: colon in plain scalar; quote literal text
- `plans/TEMPLATE.md`: <text>:4: colon in plain scalar; quote literal text
- `specs/VELDO-0001-every-criterion-declares-its-own-falsification.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/VELDO-0002-recorded-work-state-surviving-a-dead-session.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/VELDO-0003-a-work-source-for-work-that-is-not-construction.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/VELDO-0006-budget-continuity-on-the-operators-path.md`: <text>:10: text after value
- `specs/VELDO-0011-release-contract-and-registry.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/VELDO-0012-behaviour-floor-contract.md`: <text>:11: colon in plain scalar; quote literal text
- `specs/VELDO-0015-liveness-stands-down-on-clock-disagreement.md`: <text>:5: text after value
- `specs/WARP-0113-review-findings-hardening.md`: <text>:60: text after value
- `specs/WARP-0305-llm-eval-runner.md`: <text>:26: colon in plain scalar; quote literal text
- `specs/WARP-0309-suite-catalog.md`: <text>:17: text after value
- `specs/WARP-0311-contract-schema-runner.md`: <text>:36: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-0312-streaming-runner.md`: <text>:24: colon in plain scalar; quote literal text
- `specs/WARP-0315-security-guard-runner.md`: <text>:22: colon in plain scalar; quote literal text
- `specs/WARP-0316-plugin-load-runner.md`: <text>:33: colon in plain scalar; quote literal text
- `specs/WARP-0317-sandbox-isolation-runner.md`: <text>:22: colon in plain scalar; quote literal text
- `specs/WARP-0318-mcp-server-client-runner.md`: <text>:18: colon in plain scalar; quote literal text
- `specs/WARP-0319-terminal-tui-runner.md`: <text>:25: colon in plain scalar; quote literal text
- `specs/WARP-0401-executor.md`: <text>:35: colon in plain scalar; quote literal text
- `specs/WARP-0402-veldo-init-scaffold.md`: <text>:19: colon in plain scalar; quote literal text
- `specs/WARP-0403-lessons-store.md`: <text>:58: text after value
- `specs/WARP-0404-metrics-dashboard.md`: <text>:48: colon in plain scalar; quote literal text
- `specs/WARP-0405-cost-token-budget-governance.md`: <text>:58: colon in plain scalar; quote literal text
- `specs/WARP-0407-release-rollback-automation.md`: <text>:34: colon in plain scalar; quote literal text
- `specs/WARP-0501-run-registry.md`: <text>:37: colon in plain scalar; quote literal text
- `specs/WARP-0503-status-reader.md`: <text>:34: colon in plain scalar; quote literal text
- `specs/WARP-0505-run-interaction.md`: <text>:49: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-0506-chat-surface.md`: <text>:29: colon in plain scalar; quote literal text
- `specs/WARP-0602-routing-enforcement.md`: <text>:19: colon in plain scalar; quote literal text
- `specs/WARP-0603-tracker-seam.md`: <text>:32: colon in plain scalar; quote literal text
- `specs/WARP-0612-jira-init-board-bootstrap.md`: <text>:14: colon in plain scalar; quote literal text
- `specs/WARP-0613-jira-snapshot-current-state-reconcile.md`: <text>:16: colon in plain scalar; quote literal text
- `specs/WARP-0614-fenced-agent-identity.md`: <text>:15: colon in plain scalar; quote literal text
- `specs/WARP-0615-human-touchpoint-request-record.md`: <text>:110: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-0617-outbound-decision-projection.md`: <text>:58: colon in plain scalar; quote literal text
- `specs/WARP-0618-request-telegram-doorbell.md`: <text>:60: colon in plain scalar; quote literal text
- `specs/WARP-0619-request-inbound-reconcile.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/WARP-0620-live-sandbox-proof.md`: <text>:5: colon in plain scalar; quote literal text
- `specs/WARP-0621-risky-action-execution-binding.md`: <text>:12: colon in plain scalar; quote literal text
- `specs/WARP-0623-live-provisioner-name-collision.md`: <text>:12: colon in plain scalar; quote literal text
- `specs/WARP-0624-machine-actor-structural.md`: <text>:11: colon in plain scalar; quote literal text
- `specs/WARP-0625-live-changelog-reader.md`: <text>:40: colon in plain scalar; quote literal text
- `specs/WARP-0626-shadow-check-covers-the-class.md`: <text>:12: colon in plain scalar; quote literal text
- `specs/WARP-0701-claim-ledger.md`: <text>:40: colon in plain scalar; quote literal text
- `specs/WARP-0702-claimable-frontier.md`: <text>:37: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-0703-work-loop.md`: <text>:44: colon in plain scalar; quote literal text
- `specs/WARP-0710-claim-race-hardening.md`: <text>:39: colon in plain scalar; quote literal text
- `specs/WARP-0711-lint-one-interpreter.md`: <text>:9: colon in plain scalar; quote literal text
- `specs/WARP-0712-suite-decomposition.md`: <text>:51: colon in plain scalar; quote literal text
- `specs/WARP-0713-mobile-runner-injected-clock.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/WARP-0714-compute-once.md`: <text>:7: colon in plain scalar; quote literal text
- `specs/WARP-0715-process-fixture-windows.md`: <text>:8: colon in plain scalar; quote literal text
- `specs/WARP-0716-enumerate-suite-crossing-state.md`: <text>:13: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-0717-subset-runner.md`: <text>:9: colon in plain scalar; quote literal text
- `specs/WARP-0718-credential-supply-codified.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/WARP-0719-quorum-degrades-loudly.md`: <text>:51: colon in plain scalar; quote literal text
- `specs/WARP-0720-approver-registry-declared.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/WARP-0722-review-events-derived-not-appended.md`: <text>:11: colon in plain scalar; quote literal text
- `specs/WARP-0723-reserved-envelope-keys-refused.md`: <text>:9: colon in plain scalar; quote literal text
- `specs/WARP-0725-entitlement-is-the-projections-domain.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/WARP-0726-withheld-reports-every-refusal.md`: <text>:8: colon in plain scalar; quote literal text
- `specs/WARP-0727-one-enumeration-for-the-domain-and-the-validated-set.md`: <text>:9: colon in plain scalar; quote literal text
- `specs/WARP-0728-keyed-bytes-are-the-validated-bytes.md`: <text>:9: colon in plain scalar; quote literal text
- `specs/WARP-0729-footprint-globs-must-match-a-path.md`: <text>:28: colon in plain scalar; quote literal text
- `specs/WARP-0730-verdict-authority-leaves-the-agent.md`: <text>:12: colon in plain scalar; quote literal text
- `specs/WARP-0809-cross-pack-conformance.md`: <text>:28: colon in plain scalar; quote literal text
- `specs/WARP-0901-real-dispatcher.md`: <text>:20: colon in plain scalar; quote literal text
- `specs/WARP-0902-worker-spawner-accounts.md`: <text>:36: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-0903-per-account-governor-resume.md`: <text>:44: colon in plain scalar; quote literal text
- `specs/WARP-0904-veldo-cli.md`: <text>:25: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-0906-docs-made-true.md`: <text>:19: text after value
- `specs/WARP-0908-release-fleet-distribution.md`: <text>:20: colon in plain scalar; quote literal text
- `specs/WARP-1205-the-action-whitelist.md`: <text>:6: colon in plain scalar; quote literal text
- `specs/WARP-1206-the-execution-organ.md`: <text>:6: colon in plain scalar; quote literal text
- `specs/WARP-1207-the-two-key-rule.md`: <text>:6: colon in plain scalar; quote literal text
- `specs/WARP-1208-incident-as-intent-and-reconciliation.md`: <text>:5: colon in plain scalar; quote literal text
- `specs/WARP-1210-the-support-numbers.md`: <text>:15: colon in plain scalar; quote literal text
- `specs/WARP-1212-two-key-freshness-fail-closed.md`: <text>:6: colon in plain scalar; quote literal text
- `specs/WARP-1307-generated-infrastructure-least-privilege.md`: <text>:5: colon in plain scalar; quote literal text
- `specs/WARP-1403-sizing-pass.md`: <text>:33: colon in plain scalar; quote literal text
- `specs/WARP-1404-historical-analogy.md`: <text>:10: colon in plain scalar; quote literal text
- `specs/WARP-1405-reconciliation-and-estimator-accuracy.md`: <text>:12: unexpected structure under scalar; quote or use a block scalar
- `specs/WARP-1406-normalization-stable-planning-unit.md`: <text>:32: colon in plain scalar; quote literal text
- `specs/WARP-1408-budget-rollup-dollars-and-pacing.md`: <text>:9: colon in plain scalar; quote literal text
- `specs/WARP-1409-cost-to-change-per-area.md`: <text>:12: colon in plain scalar; quote literal text
- `specs/WARP-1704-publication-pipeline.md`: <text>:8: colon in plain scalar; quote literal text
- `specs/WARP-1711-history-dependent-proofs-in-a-flattened-repository.md`: <text>:10: colon in plain scalar; quote literal text

## Interpretation before migration

Unquoted colon-bearing prose, indentation that resembles a nested mapping under a scalar, and broken flow delimiters are not accepted as text by the new reader. Those require explicit quoting or a block scalar. The old full parse is preserved in the report for review. Comments inside intended prose must become quoted content. Actual status/risk annotations must become comments, not status values. Flattened-reader differences also expose lists, numbers, and quote delimiters that used to be strings. No refusal is resolved by this report, and historical proof bindings must not be fabricated after document edits.
