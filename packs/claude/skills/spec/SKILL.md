---
description: Draft a Veldo specification by interviewing the human, then validate it and update the index.
---

Create a specification for: $ARGUMENTS

Use the veldo-spec subagent approach: interview the human about outcome,
constraints, edge cases, and what failure looks like; draft from
specs/TEMPLATE.md (or TEMPLATE-standing.md for a recurring change class);
make every acceptance criterion observable and testable; check
.veldo/policy.yaml protected paths and set risk honestly.

When the repository carries an architecture contract (.veldo/architecture.yaml),
ask for the change's placement and footprint as part of elaboration: which
contract area(s) it lands in (placement) and the path globs it is allowed to
touch (footprint). This is mandatory, not optional, once a contract exists: a
spec may not reach ready without a placement that resolves to a contract area,
and a footprint that crosses an area boundary raises the risk tier and never
lowers it (validate.py refuses the ready transition otherwise). Run
python3 .veldo/validate.py ready <file> before promoting the spec to ready.

Classify the change's DIAGNOSABILITY as part of elaboration (PLAN-0012 W9): set
`behavior_bearing: true` for a change that introduces or alters runtime behavior a
future responder (a stranger to the code) would need to diagnose in production, and
`behavior_bearing: false` for one that does not (pure docs, config, or a non-runtime
change). When a change is behavior-bearing, declare an `observability:` block naming
the criteria it carries from the vocabulary - `logs` (structured logs at decision
points), `metrics`, `traces`, `error_taxonomy` (an honest error taxonomy) - each a
short description of what is logged, measured, or traced and where. Observability is
acceptance criteria for behavior-bearing changes because every future responder is a
stranger: a behavior-bearing spec that declares no observability criteria is refused
at the ready transition (validate.py ready runs this gate). Where the architecture
contract declares a system's observability rules (an `observability.required` list),
declare each required criterion. The gate enforces the floor and the vocabulary; a
reviewer judges whether the criteria are SUFFICIENT for a stranger to diagnose the
change. Both fields are optional when no architecture contract exists (the gate stands
down); absent `behavior_bearing` is treated as not behavior-bearing.

When the work is routed to an external tracker (one tracker project spanning
many repos), set the optional `tracker_repo` field to the repo the resolver
(.veldo/tracker.py) returns for the source ticket, so the spec names exactly one
resolvable target repo. Omit it for the single-repo default; validate.py fails
closed if it names a repo the tracker config does not know.

Then: python3 .veldo/validate.py spec <file> must pass, and run
scripts/update_index.py. Leave status draft until the human approves it as
ready. Append a spec.ready event to .veldo/events.jsonl when it becomes ready, with a human_minutes field covering the owner's attention in the dialogue (the method's scarce-resource metric derives from these events).
