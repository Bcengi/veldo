# The entry scripts/gate_unconfined.json needs for VELDO-0319

scripts/gate_unconfined.json is a protected path (.veldo/policy.yaml, VELDO-0208). This ticket does
not edit it. The lead adds this one entry to its `suites` list, in suite order (after
`124_veldo_0131_factory_reads_commands`, before `128_veldo_0254_confined_runner`), with the owner's
approval at landing:

```json
    {"suite": "150_veldo_0319_space_ui", "reason": "system Chrome and the npm registry: the Space screen is built from the UI's locked dependencies (npm ci needs the registry and the network) and driven in a real browser (Playwright, /opt/google/chrome) against the space harness"},
```

Why. The suite builds engine/ui from its locked dependencies and runs engine/ui/e2e/space.spec.ts in
system Chrome against engine/ui/e2e/space_harness.py, as suites 120 to 124 do. Inside the gate's
confinement every one of its rows fails by name, and its teeth cases of finding 319 are
invalid_baseline (five browser cases: space319-numeric-cells-lose-to-table-rule,
space319-poll-on-an-interval, space319-run-row-without-its-hold,
space319-keep-answer-without-the-packet, space319-sign-keep-sends-nothing).

The amendment of 2026-11-16 (AC5 to AC7) adds no second entry: its browser rows, ac5/keep-applied
and ac7/sign-keep, are rows of this same suite.
