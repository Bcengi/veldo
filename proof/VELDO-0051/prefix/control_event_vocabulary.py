"""STAND-IN, proof/VELDO-0051/red.py only. 8231708 has no canonical vocabulary: events.py and
validate.py each hold their own list of event types and neither loads this file. It carries the
registry suite 66 enumerates (the owners the commit's producers already write), taken from this
change's module below this line; at the commit nothing reads it, so every row judges the commit's own
emitter, validator, scaffold and writer."""

SCHEMA = "veldo.event/v1"
HISTORICAL_SCHEMAS = ("w" "arp.event/v1",)
SCHEMAS = (SCHEMA,) + HISTORICAL_SCHEMAS

# The producers, by the string each writes and the file its code is in.
HAND = "events.py"                                   # `events.py emit`, the skills and the operator
VERDICT_PROJECTION = "events.py reconcile-verdicts"  # derived from committed verdict artifacts
JOURNAL_PROJECTION = "control_event_projection.py"   # derived from the committed control journal
EXECUTOR = "executor.py"
GATE = "verify.sh"
GUARD = "veldo-guard"
SPEND_RECORDER = "spend.py"                          # the agent's own record of what a change cost
INCIDENT_RECONCILER = "veldo.incident_reconcile/v1"
REQUEST_RECONCILER = "request_reconcile.py"          # writes no producer field of its own

OWNER_FILES = {
    HAND: ".veldo/events.py",
    VERDICT_PROJECTION: ".veldo/events.py",
    JOURNAL_PROJECTION: ".veldo/control_event_projection.py",
    EXECUTOR: ".veldo/executor.py",
    GATE: "scripts/verify.sh",
    GUARD: "scripts/veldo-guard.sh",
    SPEND_RECORDER: ".veldo/spend.py",
    INCIDENT_RECONCILER: ".veldo/incident_reconcile.py",
    REQUEST_RECONCILER: ".veldo/request_reconcile.py",
}

# THE REGISTRY: every event type and its owner. Adding a type is a conscious contract change.
EVENTS = {
    # The loop's human-driven steps, hand-emitted.
    "plan.created": HAND, "plan.approved": HAND, "plan.revised": HAND, "work.pulled": HAND,
    "spec.ready": HAND, "spec.blocked": HAND, "index.updated": HAND, "merge.completed": HAND,
    "emergency.closed": HAND,
    # Completion: only the journal projection, from a confirmed landing receipt for its exact unit
    # and dispatch (control_event_projection.py). Never hand-emitted.
    "spec.shipped": JOURNAL_PROJECTION,
    # The gate and the push guard write their own lines.
    "gate.passed": GATE, "gate.failed": GATE,
    "emergency.push": GUARD,
    # Spend actuals (WARP-0733): what a change cost, recorded by the agent that did the work. Spend is
    # not completion. Before VELDO-0051 the recorder wrote each record as a spec.shipped line; those
    # lines stay valid under that historical spelling, and every reader of spend actuals still reads them.
    "spend.recorded": SPEND_RECORDER,
    # The executor's own steps (VELDO-0050).
    "proof.recorded": EXECUTOR, "review.requested": EXECUTOR, "approval.recorded": EXECUTOR,
    # The review projection (WARP-0722), descriptive: derived from committed verdict artifacts.
    "verdict.recorded": VERDICT_PROJECTION,
    # Run Lens durable milestones (PLAN-0005). runlog.py records them in the run folder's live
    # stream; the tracked stream receives them through the emitter.
    "run.started": HAND, "run.blocked": HAND, "run.resumed": HAND, "run.done": HAND, "run.aborted": HAND,
    # The incident lifecycle (PLAN-0012); incident.py owns the vocabulary, the reconciler closes.
    "incident.opened": HAND, "incident.diagnosed": HAND, "remedy.proposed": HAND,
    "incident.closed": INCIDENT_RECONCILER,
    # The human-touchpoint request lifecycle (PLAN-0016); request.py owns the vocabulary.
    "request.opened": REQUEST_RECONCILER, "request.accepted": REQUEST_RECONCILER,
    "request.rejected": REQUEST_RECONCILER, "request.superseded": REQUEST_RECONCILER,
    "decision.decided": REQUEST_RECONCILER,
}
EVENT_TYPES = frozenset(EVENTS)

# The types only a projection writes, and the producer each projection writes.
PROJECTIONS = {etype: owner for etype, owner in EVENTS.items()
               if owner in (VERDICT_PROJECTION, JOURNAL_PROJECTION)}


def owner_of(etype):
    """The producer that owns `etype`, or None for a type outside the vocabulary."""
    return EVENTS.get(etype)


def line_problems(event, types=EVENT_TYPES, schemas=SCHEMAS):
    """Why one parsed log line is not a valid envelope, by name: not an object, a schema no
    spelling admits, a type outside the vocabulary, no timestamp. The validator passes its own
    sets so a private copy of it can be driven without mutating this module."""
    if not isinstance(event, dict):
        return ["not a JSON object"]
    problems = []
    if event.get("schema") not in schemas:
        problems.append("bad or missing schema (want %s)" % SCHEMA)
    if event.get("type") not in types:
        problems.append("unknown event type %r" % (event.get("type"),))
    if not event.get("at"):
        problems.append("missing at (timestamp)")
    return problems
