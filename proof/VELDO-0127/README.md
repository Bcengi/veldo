# VELDO-0127 implementation blocker

This is an inspection record, not implementation proof. No acceptance criterion is
claimed complete. The specification remains ready and production code is unchanged.

The implementation session prohibits running an engine or model, logging in, and
reading real credentials. AC2 requires actual Claude Code and Codex workers. AC4
requires the debug log and first turn context size with and without marker instruction
files in the clone and account profile. The specification explicitly says fixtures
cannot certify real platform, engine or host behavior. Those qualifications cannot be
produced under this session's restrictions. VELDO.md, During implementation, requires:
"If the specification cannot be satisfied safely, stop and record the blocker in the spec."

The existing VELDO-0155 and VELDO-0156 evidence qualifies the engines' everything-off
baselines. VELDO-0172 supplies captured event shapes and shared fake constructors.
VELDO-0173 qualifies Claude Code's native tool selection. None supplies the required
actual worker evidence for newly accepted VELDO-0127 role revisions with selected
catalog servers, skills and instruction files. A new fake could exercise production
adapters but would not establish the missing engine behavior.

Inspection found the existing implementation seams:

* control_mcp_catalog.Catalog.save creates immutable catalog revisions under current
  owner authority. control_credential_delivery.resolve reads selected revisions and
  resolves only their referenced credentials.
* control_launch.Runner.prepare currently records the caller's capability
  configuration. Receiver._bind passes its role_revision to the engine. There is no
  accepted role capability configuration writer in this checkout.
* control_engine_claude.tool_options honors a supplied native tool list, including
  grants beyond the in-run default. Its Guard currently checks login, not equality of
  the complete role capability set.
* control_engine_codex.baseline generates the qualified empty baseline and selected
  MCP servers. It does not implement the role capability schema or compare the role
  with the engine's MCP listing.
* The Claude Code 2.1.281 binary was read statically, never executed. Its initial event
  generator yields system/init before iterating user input. This supports investigating
  a guard that holds the prompt until both login and capability checks finish; it does
  not qualify a live handoff. The binary digest and offsets are in inspection.json.

To resume full delivery, provide a permitted qualification environment or independent
live evidence covering the final implementation's AC2 and AC4 journeys. Implement the
role writer and both handoffs, then add the required production-interface suite, red
record and falsifier mutations. Do not treat this record as a waiver of any criterion.

No behavior suite, red driver or mutation checks ran. No engine was run, no login was
attempted, and no real credential was read. The canonical gate was not run.

Documentation checks: the footprint check reports nothing outside the declared
footprint, the anchor check reports zero bad anchors, and the repository validator
passes. checks.json records these results separately from the missing behavior proof.
