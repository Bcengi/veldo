# VELDO-0170 merge checks

Main at 298d0fd2 was merged as e38c20ec. Receiver fixture repairs are in d7b9ea80.
Every selected suite ran on its own, sequentially. These are partial checks, not a full gate result.
Counts below exclude shared preamble assertions and count failed assertions separately.

- `26_veldo_0009_install_stamp`: 32 passed, 0 failed.
- `50_git_environment`: 4 passed, 0 failed.
- `60_veldo_0052_eligibility`: 54 passed, 0 failed.
- `62_veldo_0039_dispatch`: 21 passed, 0 failed.
- `63_veldo_0040_containment`: 54 passed, 0 failed.
- `63_veldo_0049_floor`: 20 passed, 0 failed.
- `64_veldo_0050_proof`: 14 passed, 0 failed.
- `66_veldo_0047_authority`: 30 passed, 0 failed.
- `67_veldo_0041_heartbeat`: 23 passed, 0 failed.
- `67_veldo_0135_offers`: 9 passed, 0 failed.
- `70_veldo_0069_bindings`: 10 passed, 0 failed.
- `71_veldo_0076_projects`: 32 passed, 0 failed.
- `71_veldo_0130_api`: 42 passed, 0 failed.
- `71_veldo_0138_channel_service`: 13 passed, 0 failed.
- `73_veldo_0139_factory_setup`: 17 passed, 0 failed.
- `75_veldo_0062_accounts`: 23 passed, 0 failed.
- `78_veldo_0060_claude_adapter`: 35 passed, 0 failed.
- `78_veldo_0160_account_pool`: 34 passed, 0 failed.
- `79_veldo_0061_codex_adapter`: 21 passed, 0 failed.
- `80_veldo_0155_claude_baseline`: 18 passed, 0 failed.
- `81_veldo_0156_codex_baseline`: 22 passed, 0 failed.
- `82_veldo_0129_worker_wiring`: 29 passed, 0 failed.
- `82_veldo_0141_execution_record`: 40 passed, 0 failed.
- `82_veldo_0165_launch_hygiene`: 23 passed, 0 failed.
- `82_veldo_0172_live_formats`: 4 passed, 0 failed.
- `82_veldo_0173_tool_registry`: 11 passed, 0 failed.
- `83_veldo_0154_factory_loop`: 13 passed, 0 failed.
- `85_veldo_0158_credential_delivery`: 23 passed, 0 failed.
- `85_veldo_0171_setup_api`: 18 passed, 0 failed.
- `86_veldo_0127_agent_configuration`: 25 passed, 2 failed.
- `86_veldo_0148_re_land`: 25 passed, 0 failed.
- `86_veldo_0186_setup_assets`: 11 passed, 0 failed.
- `86_veldo_0189_engine_upgrade`: 32 passed, 0 failed.
- `87_veldo_0127_codex_delivery`: 176 passed, 0 failed.
- `87_veldo_0170_receiver_trust`: 11 passed, 0 failed.
- `91_veldo_0151_specialists`: 25 passed, 0 failed.
- `92_veldo_0088_pm_cycles`: 25 passed, 0 failed.
- `93_veldo_0152_intake_routes`: 21 passed, 0 failed.

Both the repository validator and the Git subprocess boundary check returned zero.
The owner retains live capture refresh and the full gate. Capture files are unchanged.
See merge-audit.json for conflict resolution, source seam review and the eight capture dependencies.

The two failures are `VELDO-0127 live/claude` and `VELDO-0127 live/codex`: both
report a missing or stale live capture because the captured launch module differs.
All other assertions pass. The captures were neither edited nor regenerated.
