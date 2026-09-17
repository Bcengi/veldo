# PLAN-0019: Dark Factory project coordination inside Veldo

**Provenance.** Design draft v2, drafted by Codex against checkout `f3d2e451bd1ead6d6a472496d2405dfe0a105abd` and attacked by the context guardian. Recorded 2026-09-16. Governing authority is Dmitry's rulings dated 2026-09-16. This document is normative for PLAN-0019 in the same way PLAN-0016's Confluence design document is normative for that plan. Recording it does not approve the draft plan or activate its proposed policies.

**Later ruling and precedence.** Dmitry, 2026-09-16 22:38: "jira was old decision. It should be where the input surface is, not just jira. If we are doing it via chat, it should be via chat as long as decision is made." R36, R38, R41, R60, and R72 below apply this ruling and are marked [REVISED]. Every enrolled input surface is a decision surface; the authority settles once, and every channel is a proxy. This supersedes PLAN-0016's prohibition on chat decisions and any tracker-only or ticket-only answer requirement retained elsewhere in this v2 text, including R03, R07, R12, R18, R37, R51, R53, R61, R65, R71, and R74. Tracker-specific delivery and activation requirements continue to govern the tracker adapter; they do not make it a prerequisite for another independently enrolled and qualified channel. Lifecycle spellings use US English, including `CANCELED`.

**R01. Purpose and governing boundary. [REVISED]**

Veldo shall coordinate projects from proposed objectives through requirements, admission, engineering execution, and accepted outcomes. The project manager reasons and proposes. Deterministic Veldo services authenticate, authorize, validate, persist, schedule, and publish. An agent response, conversation, graph checkpoint, tracker transition, or process exit shall never independently authorize work or establish completion.

The existing specification, proof, review, gate, and landing machinery remains the factory floor. This plan repairs that floor before relying on it.

**R02. Inspection basis and limits. [REVISED]**

`CLAUDE.md` and `VELDO.md` were read first. Git identifies this checkout as the stated baseline. The design's repository claims were checked against the corresponding source, including release and behavior-floor contracts, claims, runs, execution, dependencies, decisions, requests, authorization, credentials, landing, events, architecture enforcement, and pack assembly.

Read-only probes reproduced acceptance of an empty-criteria proof naming a nonexistent commit, refusal of direct `verdict.recorded` emission, a 31-type emitter vocabulary against a 21-type validator vocabulary, and an unparseable architecture contract returning the same absence result as a missing contract. Clock probes returned `unanswerable` from claim liveness and run classification while `_is_stale` returned false.

The repository includes a stdio JSON-RPC MCP test client and a web runner using Node and Playwright. Those do not establish a wired model-backed coordinator. `LiveLoop`, `LiveReviewer`, and `LiveSizingAgent` have production entry points, but their model-mediated operations remain refusing seams. The standard-library restriction applies to enforcement and contract code.

No repository files were changed. No full gate run or implementation completion is claimed. The supplied frozen kernel is normative input, not a document found in this checkout. The unrelated review-script preamble and invalid review range from v1 are discarded.

**R03. Decisions recorded before implementation. [REVISED]**

Decision records shall precede executable changes for orchestrator ownership of process lifetime, operational authority and persistence, LangGraph's replaceable execution boundary, and review and completion semantics.

The SQLite authority with signed Git replication, off-host publication before mutation acknowledgement, Linux systemd and cgroup v2 runner requirement, and isolated worker clones with shared object storage are ACCEPTED for this draft under the guardian's recommendation, pending Dmitry's word.

The process decision records Dmitry's retirement of `no_detached_processes` and agent-mediated launch requirements for this project layer. It shall identify the architecture-contract revision, policy loading changes, capability declarations, and affected tests that activate the replacement. Recording a decision alone does not change effective enforcement. The lexical prohibition in `scripts/suites/06_capabilities_manifest_honesty_veldo.py` shall be replaced for the governed runner by lifecycle and containment obligations with real failure tests. Extending that lexical scan to reject the adopted runner is prohibited.

The separate-repository rule, single-operator restriction, terminology ban, and fixed fifteen-role roster do not apply by Dmitry's ruling. The remaining supplied kernel contracts are ported below, with explicit applicability limits. PLAN-0016's tracker decision surface remains binding.

**R04. Stable identity and ownership. [REVISED]**

Every new durable entity shall have a coordination-domain UUID, repository UUID where applicable, entity type, globally unique UUID, schema version, creation provenance, and monotonically increasing concurrency version. Readable identifiers are aliases, never filesystem paths or authentication subjects. Existing specification and plan identifiers remain unchanged and are repository-qualified outside their repository.

Every project has a named owner and one execution repository. Every objective belongs to one project, every backlog item to one objective, and every execution unit to exactly one backlog item. Two projects cannot own or execute the same unit. Another project may consume its accepted artifact through an explicit dependency.

Ownership transfers require an authorized transition and receipt. They never transfer admission authority implicitly. Terminal history retains the ownership under which its effects occurred.

**R05. Project contract. [REVISED]**

A project is a continuing coordination and accountability boundary, independent of the release hierarchy. It is neither a plan, a release, nor an execution of one release. It owns a charter, objectives, authority bindings, team configuration, specialist roster, budget envelopes, policies, and coordination history.

Its lifecycle is `DRAFT`, `ACTIVE`, `PAUSED`, `COMPLETED`, or `CANCELED`. Activation requires a signed charter, resolvable owner, applicable authority policy, and bounded coordination budget. Pausing prevents new assignments and dispatches and invokes the running-work stop policy. Completion requires terminal objectives and reconciliation of assignments, decisions, dispatches, release executions, and reservations.

Project cancellation closes future authorization and directs disposition of its unfinished work. It does not erase landed revisions or assert that an incomplete release succeeded. Continuation after a terminal state creates a linked project. R65 defines the project's relationship to releases and plans.

**R06. Objective contract. [REVISED]**

An objective states an observable outcome, beneficiary, scope, exclusions, acceptance authority, and required evidence. Its lifecycle is `PROPOSED`, `ACCEPTED`, `ACTIVE`, `BLOCKED`, `SATISFIED`, `REJECTED`, or `CANCELED`.

The named acceptance authority accepts the objective. Acceptance permits bounded elaboration; it does not admit every feature subsequently proposed. An objective may be supported by release executions, plans, and standalone specification outcomes through explicit contribution links. Those links do not confer ownership or execution authority.

Satisfaction requires a signed assessment against the exact accepted objective revision. Shipping associated specifications is insufficient when the promised outcome remains unproven.

**R07. Backlog item contract. [REVISED]**

The kernel's canonical work item becomes a **backlog item**, distinct from existing `plan.work` entries. Each backlog item has exactly one work class, admission request, backlog state, lane, priority, authority record, and source provenance record. It may reference zero or more specifications and execution units.

The admission request is the kernel's ticket. Its authoritative revisions reside in Veldo; its tracker issue is the required decision surface. The tracker issue and request retain a durable correlation. A tracker status or a specification marked `ready` cannot supply missing admission authority.

A standing-maintenance occurrence has its own admission request and receipt chain referencing the signed standing ticket. It does not reuse another occurrence's identity.

**R08. Work classes and lanes. [REVISED]**

The governed work classes are exactly `PRODUCT_CHANGE`, `POLICY_DEFECT`, `SECURITY_EMERGENCY`, `INCIDENT_CONTAINMENT`, `STANDING_MAINTENANCE`, `TECHNICAL_CHANGE`, and `COMPLIANCE_EXPIRY`. Every item has one class before admission. Unknown or unresolved classifications remain quarantined.

`PRODUCT_CHANGE` and `TECHNICAL_CHANGE` require the admission authority to shape and prioritize the request. `POLICY_DEFECT` requires that authority or the Admission Service applying a signed defect policy. `SECURITY_EMERGENCY` requires the security authority or bounded break-glass authority subject to ratification. `INCIDENT_CONTAINMENT` requires the operations authority or a signed standing containment policy. `STANDING_MAINTENANCE` requires an authorized person's deliberately authored recurring ticket and signed policy. Non-standing `COMPLIANCE_EXPIRY` requires the admission authority to shape and prioritize it; a signed standing policy may authorize a bounded occurrence.

All seven classes are retained. Compliance work applies when an enrolled repository has an actual obligation and named authority; none is presumed for Veldo. Production containment and deployment-specific emergency actions remain unavailable without separately admitted target adapters. Repository credential containment and release suspension may apply under explicit policy.

Ordinary, policy-qualified, and emergency lanes are scheduling routes. No lane bypasses identity, scope, priority, evidence, quarantine, or audit. R66 through R69 define the complete Section 2 admission contract.

**R09. Admission request contract. [REVISED]**

An admission request is deliberately authored authorization material with stable identity and immutable revisions. It binds work class, outcome, machine-comparable scope, exclusions, priority, ratified budget, lane, applicable policy version, relevant specification revisions, affected protected paths, maximum release authority, expiry conditions, and source evidence.

Machine-prepared material remains a draft until the authorized person or named policy identity signs the exact revision. Policy admission also binds the policy digest, signer, evaluation inputs, evaluation result, and expiry. An agent's reproduction claim cannot substitute for trusted reproduction observations.

Material changes supersede the revision and invalidate dependent authorization under R69. Request content identity includes its version. Presentation identity additionally binds what the person was shown under R72.

**R10. Specifications remain the engineering unit of work. [REVISED]**

Every engineering execution unit binds exactly one primary specification revision, one admitted backlog item, and an immutable execution contract. A specification has one concern and three or four acceptance criteria. Every criterion states the claim, quantified set, completeness mechanism, and concrete falsifier.

A unit may cite additional specifications as constraints or record that its outcome also satisfies them. It never combines admission authority from several backlog items. There cannot be two active engineering units for the same admitted specification revision.

Repeated coordination operations bind a governing coordination specification and distinct operation units. They publish coordination artifacts and receipts without claiming source landing.

Before admission creates any artifact for a unit, the Admission Service shall call the installed `claim.unit_id_problem` with its proposed identifier. Any reported problem refuses admission. No second spelling of those identifier rules is permitted. R73 governs allocation and publication of specification aliases.

**R11. Backlog lifecycle. [REVISED]**

The permitted states are exactly `RAW`, `QUARANTINED`, `PREPARED`, `AWAITING_GROOMING`, `REJECTED`, `ADMITTED`, `PRIORITIZED`, `ACTIVE`, `BLOCKED`, `DONE`, and `CANCELED`.

Validated intake moves `RAW` to `PREPARED`; unsafe or unresolved intake moves it to `QUARANTINED`. Quarantine resolution may return an item to preparation. Prepared work enters grooming or its applicable signed-policy evaluation. Authorized admission produces `ADMITTED`; a recorded priority assignment produces `PRIORITIZED`. No dispatch occurs directly from intake or admission.

Only prioritized items may create executable units eligible for scheduling. Claiming the first unit atomically makes the item active. Remaining units from the approved decomposition may proceed. Adding units requires a new prioritization act over the revised decomposition.

An active item remains active until its units are terminal or the item is blocked. Blocked items retain the interrupted phase and reason; validated resolution restores that phase. `REJECTED`, `DONE`, and `CANCELED` are terminal. Reconsideration creates a linked new item.

**R12. Grooming is an authorization ceremony. [REVISED]**

Grooming presents the admission authority with the exact request revision, evidence, proposed decomposition, alternatives, exclusions, priority, cost ceiling, and unresolved questions through its tracker ticket. Its signed receipt records admission, rejection, or return for elaboration, with reasoning. Admission and priority may be decided together but remain distinct decisions.

Only a cleanly reproduced defect may originate new discretionary engineering work through automatic admission. The complete defect predicates are in R66. Standing maintenance, containment, and compliance occurrences execute previously signed, bounded authorization; they do not give preparation agents discretion to invent features. Break-glass authority is the narrowly bounded exception defined in R68.

Preparation agents cannot move `RAW`, `QUARANTINED`, `PREPARED`, or `AWAITING_GROOMING` work to `ADMITTED` or `PRIORITIZED`. A project manager cannot relabel desired functionality as restoration of accepted behavior.

**R13. Execution lifecycle. [REVISED]**

Units use `PLANNED`, `READY`, `CLAIMED`, `DISPATCHING`, `RUNNING`, `VERIFYING`, `REVIEWING`, `READY_TO_LAND`, `LANDING`, `COMPLETED`, `FAILED`, `CANCELED`, and `AWAITING_AUTHORITY`. The last is Veldo's name for the kernel's authority-required stop state.

Every transition has a deterministic entry predicate and durable receipt. `AWAITING_AUTHORITY` records the interrupted station, reason, outstanding effects, and required resuming authority. It does not imply a running worker.

A failed attempt remains immutable. A permitted retry creates a new attempt and contract under the same unit when scope is unchanged and the previous attempt is reconciled. Cancellation never counts as completion without signed reconciliation accepting an alternative outcome. A backlog item becomes done only when all required units are completed or such reconciliation covers the exceptions.

**R14. Dependencies and regression. [REVISED]**

Dependencies are typed edges between exact accepted outcomes or artifact revisions. Engineering dependencies resolve to verified completion receipts, never status strings or path existence.

One graph combines plan work edges, specification `depends_on` edges, project dependencies, decision prerequisites, and applicable release-execution ordering. Release membership is separately validated as the existing typed forest; it does not silently imply execution order. The combined dependency graph must be acyclic before dependent execution is authorized. Separately valid graphs are insufficient.

Cycles block affected backlog items and require the technical authority to resolve them. Missing, ambiguous, or inaccessible targets block with named unresolved references. A rejected graph amendment remains evidence and cannot leave the prior graph silently executable when it reveals an actual prerequisite.

Withdrawal or invalidation of a prerequisite revokes queued readiness and running publication permission until revalidation. Completed dependents retain historical receipts and gain impact records requiring a new decision.

**R15. Contracts, artifacts, and receipts.**

A contract is immutable and binds its unit, station, actor constraints, input digests, accepted scope, allowed tools, sandbox profile, budget reservation, deadline, output schema, verification obligations, and authorization versions.

An artifact is identified by a cryptographic digest. References include media type, length, provenance, and a resolvable location. Mutable paths are locations, not identities.

The Evidence Service signs immutable receipts binding the contract, observed actor, inputs, observations, assertions, outputs, costs, and provenance. Agent statements are explicitly assertions. Captured exit codes, bytes, tool invocations, and process events are observations of those particular subjects, not automatic proof that the agent's interpretation is correct. Corrections append superseding receipts.

**R16. Stations and services.**

Intake, elaboration, grooming, prioritization, construction, verification, review, landing, and outcome acceptance are stations. Each station declares its entry conditions, exit conditions, authorized actors, contract schema, required receipts, and allowed failure transitions.

Services are deterministic enforcement components: authorization, scheduling, evidence, runner supervision, accounting, artifact publication, and landing. They are not agent roles. A model-mediated reviewer is an agent type; the service that verifies its receipt and enforces unresolved findings is not.

A station with no source-code effect still requires an explicit publication receipt for its accepted artifact. A missing applicable receipt cannot be replaced with a generic success flag.

**R17. Core team and specialist roster. [REVISED]**

A project's versioned team configuration names one project-manager role and the roles required for its work, including requirements elaboration, implementation, and independent review. These are configurable role definitions, not a fixed roster of people or perpetual processes.

Each role declares responsibilities, allowed proposals, capabilities, engine eligibility, context restrictions, budget limits, and independence constraints. Specialists receive bounded assignments against those requirements. An agent cannot invent a role, increase its permissions, or turn roster membership into admission authority.

Missing mandatory expertise produces a blocker or staffing request to the project owner. Existing repository restrictions on review independence and model selection remain effective unless explicitly changed through their governing policy.

**R18. One assignment model for people and agents. [REVISED]**

An assignment binds a unit and station to required actor kind, capabilities, authority predicates, expected artifact, deadline, and budget. Its states are `OFFERED`, `ACCEPTED`, `IN_PROGRESS`, `SUBMITTED`, and `SATISFIED`, with explicit declined, expired, and canceled outcomes.

An agent may satisfy a production assignment whose actor predicate permits it. It cannot substitute for a person, named principal, specified authority, or independent signer. Reassignment preserves those predicates and records a version change.

Assignments requiring a person's action are delivered through tracker tickets. Waiting for an answer holds no worker process or claim lease. The assignment and delivery obligations remain durable.

**R19. Requirements elaboration and coordination authority. [REVISED]**

Elaboration produces versioned requirements, assumptions, alternatives, proposed specifications, dependencies, and questions. Unresolved questions affecting scope or acceptance block the applicable admission or execution boundary.

The project manager's governing specification authorizes bounded drafting and proposals. It does not authorize feature admission, priority changes, scope expansion, trusted observations, or landing. Every cycle consumes a reservation and produces a receipt, including a cycle proposing no action.

Limits on cycles, tokens, elapsed time, and repeated unchanged proposals prevent unbounded self-triggered reasoning. Concurrent authors use R73's source-to-artifact allocation transaction; they never choose identifiers from their checkout's maximum existing number.

**R20. One authority across clones. [REVISED]**

Each enrolled repository belongs to one coordination domain with one designated authority store and active authority process. Enrollment binds repository UUID, domain UUID, store UUID, host identity, and authority generation. Every participating clone and worktree routes mutations to that authority.

Separate clones may coordinate the same project when enrolled against those identities. Local clients use authenticated IPC; remote clients use an authenticated SSH command relay to that IPC endpoint. No separate network application server is introduced. An unreachable authority makes mutation and execution admission unavailable.

One authority instance does not serve several repositories in this design. One installed Veldo distribution and workstation may host separate domain service instances for Veldo, CoreConnect, and the mobile repository. Each has its own Git common directory, store, lock, keys, journal, and enrollment. These are separate installations of the same storage boundary, not additional databases inside one domain.

Cross-domain work is unsupported. R75 specifies service installation, startup, restart, and absent-service behavior.

**R21. Authoritative storage and checkpoint placement. [REVISED]**

The authority uses one local SQLite database at `<git-common-dir>/veldo/control/control.sqlite3`, on a filesystem qualified for locking and durability. Network-mounted SQLite storage is unsupported.

Veldo owns the signed journal, entity records, accepted document digests, dispatch records, assignments, decisions, nonces, reservations, receipts, and publication cursors. LangGraph checkpoints occupy separate adapter-owned tables in that file. Checkpoint writes cannot alter domain tables, accepted history, or domain transaction results.

The model execution process receives no database path, handle, or filesystem access. A trusted checkpoint access boundary restricts adapter operations to checkpoint data and rejects cross-namespace SQL and indirect writes. Domain code imports no LangGraph package. Qualification must prove these restrictions and bounded checkpoint contention.

Removing LangGraph removes its adapter and checkpoint data without changing Veldo's domain schema or history. Sharing a file does not confer shared authority.

**R22. Transaction and version contract.**

Every command carries a globally unique command ID, authenticated principal, expected entity versions, and referenced artifact digests. A duplicate command with identical content returns its prior committed result. Reuse with different content is rejected.

A successful domain transaction atomically updates affected entity versions, appends its signed journal record, records consumed nonces and reservations, and records required subsequent effects. SQLite uses foreign-key enforcement and full durability settings.

The journal includes sequence number, previous-record digest, authority generation, command digest, relevant identities, before and after versions, transition data, and receipt references. Canonical encoding is versioned and deterministic. Plan `revision` remains a scope-staleness value; it is never reused as a concurrency version.

**R23. Publication and durable backup. [REVISED]**

A committed transaction produces a signed immutable export containing its journal record and newly referenced artifacts. Exports are published in order to a dedicated protected Git ref in the existing repository remote. This is an audit and recovery replica, not a second writable authority or message queue.

Mutation success, external dispatch, and dependent publication are withheld until the corresponding export has an off-host durable acknowledgement. Failure leaves a committed transaction visibly pending publication. Recovery retries the same export identity. A lost acknowledgement is reconciled against the exact remote ref and export digest.

The status surface shall show the last durable sequence, local committed sequence, pending export count, oldest pending age, and `PAUSED_PUBLICATION` condition. A pending command is not reported as rejected or safely repeatable under a new identity.

Installation must establish the remote's durability and protected-ref access contract. A local bare remote proves protocol behavior in tests, not survival of authority-machine loss.

**R24. Leadership and fencing. [REVISED]**

Startup acquires an exclusive OS lock on a stable store lock file before opening a scheduling session. The file is never deleted to steal leadership. A second process cannot schedule.

After recovery checks, startup commits a new authority generation. Claims, launch permits, publication permits, and worker capabilities bind it. Accepting services reject stale generations. Losing leadership stops new dispatch within two seconds.

Dispatch also requires a live supervisor control channel. A stalled orchestrator cannot satisfy this requirement through a timer inside itself. The trusted runner and effect executor independently revoke acceptance when that channel fails.

An already accepted effect is reconciled before a replacement leader permits conflicting work. Failure tests cover lock loss, process suspension, control-channel loss, and an old process resuming. Host replacement additionally requires R26 fencing.

**R25. Claims remain ownership authority. [REVISED]**

The existing claim module remains the single claim API for enrolled work. It routes to the authority store and commits claim ownership, unit transition, and monotonically increasing claim generation together. Independent clone-local claims are prohibited after enrollment.

Lease expiry is liveness evidence, not permission for an old worker to publish. Every protected effect checks claim generation. Reclaim requires fencing the prior attempt and reconciling its effects.

VELDO-0015's clock stand-down implementation is present at the baseline. It shall not be described as a new implementation dependency or inferred complete from its status field. The scheduler preserves `unanswerable`, records both clocks and the configured tolerance, stops affected dispatch, and requests operations reconciliation. `_is_stale` returning false cannot be interpreted as proof of life.

The three recorded report follow-ups cover task reporting, claim-refusal propagation including landing, and the status display. They are required before the first floor slice.

**R26. Process death, machine death, and clone replacement. [REVISED]**

After process death, the replacement leader verifies and replays history, reconciles claims and runner containment, and resolves unfinished dispatches before admitting new work. An unresolved dispatch may be durably quarantined in `AWAITING_AUTHORITY`; unrelated work may resume only after recovery establishes that it cannot conflict or exceed reserved exposure.

After machine loss, the operations authority must establish that the old host cannot execute or publish through host isolation, credential revocation, and removal of publication authority. Network silence alone is insufficient. The replacement imports and verifies the signed replica, creates a new authority generation, and reconciles external outcomes.

Client-clone replacement requires reenrollment. Authority-clone replacement is a controlled migration or restoration, never empty initialization from source files. Missing unpublished tails require explicit uncertainty treatment even when all acknowledged history survives.

**R27. Corruption and rollback. [REVISED]**

Startup verifies database integrity, journal signatures, sequence and hash-chain continuity, artifact digests, and agreement between replayed history and materialized state. Valid history may rebuild derived tables.

A corrupt authoritative journal stops dispatch. Damaged material is preserved for signed operations reconciliation against a verified replica. Veldo never truncates unexplained records and continues. A missing tail is not evidence that work never ran.

Logical checkpoint corruption may quarantine checkpoint data and restart graph execution from Veldo state. Physical corruption of the shared database cannot be dismissed as checkpoint-only damage without proving the domain history intact.

The previous known-good release and compatible schema reader remain installable until the new release completes its proof plan. Schema downgrade is never implicit.

**R28. Wake-up and delivery. [REVISED]**

Durable commits wake consumers through in-process signals and authenticated IPC notifications. Causes include intake, decision settlement, assignment submission, dependency changes, worker completion, revocation, and budget availability.

Event sequences and consumer cursors support replay after startup, reconnect, and explicit resynchronization. Consumers do not periodically query storage to discover rare changes. The database stores history and delivery obligations; it is not the transport.

Commit notification and transition to idle share a serialized event-loop boundary. An unexpectedly terminated notifier causes channel closure and recovery replay, preventing a committed but unsignaled event from leaving a live consumer asleep indefinitely. Timers serve actual deadlines, heartbeat supervision, and bounded reconnect backoff.

Tracker changes use a qualified notification or doorbell transport followed by an authenticated canonical-history pull. Existing PLAN-0016's session-start pull remains the compatibility trigger until its separately authorized ingress activation. That limitation is displayed and cannot be advertised as continuous event-driven delivery.

**R29. Project-manager serialization. [REVISED]**

At most one project-manager cycle is active per project. A cycle binds a project version, journal watermark, governing coordination contract, complete input snapshot, and budget reservation.

Events arriving during a cycle advance a pending watermark. On completion, Veldo schedules one follow-up cycle when relevant unprocessed input remains. Unrelated events need not interrupt the model.

Proposals commit only against their declared read set under R70. Owner actions and deterministic services need not wait for the model. Stale proposals are refused; a bounded fresh cycle may follow. Separate projects may reason concurrently.

**R30. Proposal validation.**

The project manager returns typed proposed actions, never executable shell commands or database instructions. Each action names its target entities, expected versions, evidence, intended transition, authority requirement, and idempotency key.

Veldo validates schema, identity, authorization, scope, dependency closure, unresolved decisions, roster eligibility, separation of duties, budgets, and lifecycle legality. It commits an explicitly declared atomic action group completely or rejects it completely. Independent groups receive separate results.

Repeated proposals use stable action identities bound to the same cycle and logical operation. Graph retries cannot allocate fresh identities to evade duplicate suppression. Model confidence is never an admission predicate.

**R31. Dispatch preparation. [REVISED]**

Before invoking a worker or external service, Veldo commits and publishes dispatch ID, unit, station, attempt, complete precondition set, contract digest, idempotency key, claim generation, authority generation, and reservation.

A uniqueness constraint permits at most one active logical dispatch per unit and station. The unit enters `DISPATCHING`. The receiver durably accepts that identity before engine launch. Veldo commits and publishes the acceptance acknowledgement before advancing to `RUNNING`.

Delivery retries query or address the same dispatch. They do not start another worker. A new attempt requires a reconciled terminal prior attempt and applicable retry authorization. Admission and claim predicates are rechecked by the accepting boundary, not merely by selection.

**R32. Recovery distinguishes outcomes. [REVISED]**

Recovery records five distinct findings, with supporting evidence.

**Not dispatched** means durable receiver evidence establishes that execution never started. The existing dispatch may proceed if authorization remains valid.

**Running** means the receiver identifies the matching containment group and invocation. Veldo resumes observation without launching another engine.

**Effect committed** means trusted target evidence establishes the exact effect. Veldo records it without repeating execution.

**Acknowledgement lost** means receiver acceptance or completion is established but its Veldo acknowledgement is absent. Veldo imports and commits the evidence.

**Outcome unknown** means none of those conclusions is justified. The unit enters `AWAITING_AUTHORITY` with an effect-specific reconciliation task. Process absence, checkpoint loss, lease expiry, and nonce consumption do not establish nonexecution. R74 defines resolution, retry, and compensation.

**R33. At-most-once limits. [REVISED]**

The runner maintains a durable launch record keyed by dispatch ID and records intent before spawning. Death between intent and conclusive launch evidence prevents relaunch until recovery establishes nonexecution.

An external target must provide idempotency or a conclusive outcome query before automatic recovery may repeat delivery. Otherwise uncertainty requires the designated authority's reconciliation.

This guarantees one active logical dispatch and prevents blind redispatch. It does not promise exactly-once effects from arbitrary targets. A newly authorized attempt requires documented outstanding effects, duplicate risk, applicable compensation, and fencing. A signed decision cannot turn an unknown historical effect into a known non-effect.

**R34. LangGraph boundary. [REVISED]**

LangGraph is adopted now as a replaceable execution adapter over Veldo-owned snapshots, cycle identities, supplied results, and typed proposals. The interface supports starting, advancing, suspending, canceling, and returning a proposal or failure.

Checkpoints may hold graph position, conversation state, and artifact references. They cannot establish admission, priority, assignment, completion, authorization, or dispatch identity. Replayed nodes reuse Veldo command IDs.

A checkpoint ahead of authoritative state cannot authorize its apparent progress. A checkpoint behind it receives committed results through replay. Conflicting checkpoint content is discarded or quarantined. No LangGraph server or hosted control plane is used.

**R35. Dependency installation and replacement. [REVISED]**

Package B owns the LangGraph adapter and packaging boundary before Package C's skeleton uses them. The installer carries a tested, pinned execution runtime, SQLite checkpoint support, and complete transitive dependency lock with hashes and licenses. Installation uses an isolated environment.

`.veldo/architecture.yaml` declares `stdlib_only_enforcement`: enforcement and contract code must remain Python standard library only. LangGraph and its dependencies cannot enter gate imports, contract validators, authorization, journal replay, or recovery. Package qualification verifies that these paths operate with the execution environment unavailable.

The engine manifest, assembly rules, scaffolder inventory, dependency artifacts, and install-and-run test shall include the runtime boundary explicitly. Existing globs do not cover every required new asset. Versions, Python compatibility, and the checkpoint implementation are established by compatibility proof, not assumed here.

**R36. Principal authentication. [REVISED]**

People, services, policies, and agent runs have distinct principal types. Git authors, display names, tracker labels, and model-provided actor strings do not authenticate them.

Bootstrap and administrative commands use OpenSSH-envelope Ed25519 signatures binding domain, repository, store, command ID, request revision, challenge nonce, and expiry. The authority verifies active membership and delegation records. SSH transport authentication does not replace command authentication.

Routine decision answers may originate from every enrolled input surface, including Telegram chat, Jira, signed CLI, and email when enrolled. Each channel edge authenticates its platform or signed command, obtains canonical attributed evidence, maps the stable sender identity to enrolled membership, and submits a constrained assertion under R38 and R72. For chat, evidence includes the platform message ID, sender ID, and timestamp pulled from the platform; text alone never authenticates the sender or proves the decision. An edge signature never claims that a platform action carried a locally produced personal signature.

Each agent invocation receives a unique short-lived identity bound to one contract, unit, station, sandbox, and expiry. Credentials expire no later than fifteen minutes after the contract deadline.

**R37. Several named authorities. [REVISED]**

Membership binds named principals to scoped roles including membership steward, project owner, admission authority, priority authority, technical authority, security authority, and operations authority. Role overlap remains subject to separation requirements.

Dmitry is the only named initial authority supplied and supported by the repository's recorded approver ruling. No additional person's identity or key is invented. Dmitry must provide each additional name, verified key, tracker account binding, role scope, and applicable membership policy through enrollment.

Until those enrollments exist, assignments requiring another named authority and quorums requiring distinct people remain blocked. PLAN-0016's recorded owner-plus-independent-machine confirmation is a separate two-key rule; it cannot satisfy a quorum requiring two people.

Membership changes follow the accepted membership policy and require proof of key possession. This draft does not silently replace the current owner bootstrap with v1's invented universal two-person membership quorum. Agents and services cannot enroll principals or grant authority.

**R38. Signatures and key lifecycle. [REVISED]**

Public verification keys live under `.veldo/keys/allowed_signers`. Accepted membership and key transitions determine active authority, independent of a worker's branch. Private keys remain outside repositories, sandboxes, model contexts, transcripts, and builds.

Admission, priority, baseline acceptance, risk acceptance, and emergency ratification require the applicable principal's signature or explicitly enrolled channel-edge delegation. Every enrolled channel has its own restricted signing key. Delegation binds the principal, channel, permitted assertion kinds, request and presentation versions, authority scope, and expiry. The signature envelope records the principal, channel-edge service identity, delegation, presentation receipt, and canonical attribution evidence. Chat evidence includes platform message ID, sender ID, and timestamp obtained from the platform, never the message text alone. Signed CLI assertions retain the verified personal command signature as source evidence within the channel-edge model.

The protected signer independently checks these conditions. An edge cannot use its key to manufacture an assertion, change membership, sign arbitrary commands, or impersonate another channel. Failure to establish safe restricted signing blocks that channel's activation. Another enrolled and qualified channel may receive the decision under the same authority and presentation rules; it does not bypass a blocked edge or create a second authoritative record.

The Evidence Service separately signs observations and receipts, preserving agent assertion identities. Rotation preserves retired verification keys and records effective, retirement, and revocation times.

**R39. Revocation and authorization rechecks. [REVISED]**

Authorization is rechecked at command acceptance, proposal commit, assignment acceptance, claim, dispatch acceptance, privileged-tool use, result acceptance, decision settlement, and landing publication.

Revocation blocks new affected operations, invalidates queued capabilities, requests stop of running work, and removes publication and privileged-tool permission. Submitted outputs remain evidence but cannot satisfy revoked obligations without fresh authorization.

An accepted external operation may already be in flight. Revocation records it and requires stop or reconciliation before reporting effective closure. Revocation and effect acceptance share a serialized boundary, establishing their order without promising retroactive cancellation.

Membership, policy, scope, decision, and dependency revisions participate in these checks, including when only an indirectly referenced record changed.

**R40. Decisions and settlement. [REVISED]**

A decision request binds subject revision and digest, proposed ruling choices, required actor kind, named-authority restrictions, roles, quorum, independence, expiry, and consequences.

An answer contains the ruling and reasoning, bound to the versioned presentation receipt. Effective role and quorum predicates are the conjunction of policy and request requirements. Expired, stale, duplicate, or insufficient answers cannot settle.

Settlement atomically records accepted assertions, ruling, terminal request state, consumed nonce where applicable, domain transitions, receipt, and delivery obligations. One request version can have only one terminal settlement; several changelog IDs cannot create several winners.

Settlement of a decision record must update the exact dependency bindings in R71. Merely writing a receipt or changing a tracker status cannot unblock a plan.

**R41. Andon and decision surfaces. [REVISED]**

Any authenticated agent or service may request `AWAITING_AUTHORITY`. Veldo records the request even when its author cannot resolve the issue. Only the designated authority or a signed automatic recovery policy may resume the unit.

Every enrolled input surface is a decision surface under the kernel's master-and-proxies principle. A person may answer through the enrolled channel where the request is presented, including Telegram chat, Jira, signed CLI, or email when enrolled. Every answer binds the presentation the person saw. Veldo records one authoritative settlement with originating-channel attribution; projections and notifications are proxies, never second records. A notification without an attributable, presentation-bound answer grants no authority. Projection creation stores each channel's external identifier and correlation durably. Lost acknowledgement triggers lookup, never blind duplicate creation.

PLAN-0016 remains inert until its tracker activation conditions are satisfied. The orchestrator's process ruling does not by itself activate any channel ingress or authorize board mutations. Required workflow and ingress changes receive their own specifications and channel-specific proof. R60 qualifies enrolled decision surfaces without giving the tracker first-answer precedence.

**R42. Worker engine adapter. [REVISED]**

Claude Code and Codex implement the same runner contract: validate the installed version, launch with explicit inputs and tool permissions, report acceptance and process identity, stream observations, accept cooperative stop, report exit, expose recovery status, and return artifacts for independent validation.

Qualification records exact executable digest, version, invocation contract, terminal-output shape, usage semantics, and recovery capabilities. The guardian's stated Codex version is a qualification input to verify, not a claim that this draft tested that binary.

Unsupported output, missing terminal records, and malformed or absent usage fail explicitly. Zero exit status never establishes specification completion. This design relies on tested adapters rather than the unverifiable v1 documentation link.

**R43. Process lifetime and descendant containment. [REVISED]**

Production autonomous workers require Linux, systemd, and cgroup v2. Other hosts, including a Mac, refuse activation until an equivalent adapter passes the same contract.

Each dispatch has a dedicated containment group and trusted wrapper. Forking, new sessions, and grandchildren cannot escape it. Worker credentials and namespaces cannot modify containment controls, reach the authority's service manager, or signal authority processes.

Systemd supervises the authority and its runner lifecycle. On authority death, control-channel failure, or service stop, the trusted supervisor retires all affected containment groups before a replacement schedules. A narrowly scoped, operations-installed local runner helper supplies any OS privileges needed for distinct worker identities and namespace setup; those privileges never enter the model process.

Exit detection uses OS notifications. Process identity includes boot identity and start identity. A reused PID cannot revive a prior invocation. The provider-neutral implementation exists before crash qualification.

**R44. Liveness and stopping. [REVISED]**

The trusted wrapper emits a heartbeat every ten seconds, independent of model output. A thirty-second missed-heartbeat deadline marks liveness uncertain and closes effect permissions. Claim renewal cannot depend on a blocking engine call returning.

Cooperative stop asks the adapter to terminate and flush observations. After ten seconds, the supervisor terminates the containment group; after another five seconds, it kills remaining descendants. These are versioned policy defaults. Loss of leadership still closes new-dispatch acceptance within R24's two-second bound.

Capacity is released only after containment is empty and outcome and accounting are durably recorded. Unproven emptiness quarantines the slot. Silence is not proof of death.

**R45. Sandboxes, credentials, and accounting. [REVISED]**

Workers receive isolated per-run clones at an explicit accepted commit. They cannot write the authority clone, Git common directory, claims, signing material, other workers, or operational database. This replaces PLAN-0007's shared-worktree provisioning boundary for enrolled autonomous work.

Provisioning shall use a trusted shared object cache through read-only Git alternates or an equivalently qualified object-sharing mechanism. Cache access exposes Git objects only, never authority metadata or credentials. Referenced objects are pinned until dependent clones retire; garbage collection cannot invalidate a running checkout. Workers cannot mutate shared object bytes.

The Credential Service is the real issuer of short-lived internal capability handles derived from accepted contracts, not caller-supplied task declarations. Security and operations authorities revoke them. Protected service storage holds provider and target credentials. The trusted Effect Executor alone exchanges handles for permitted privileged operations and rechecks authority at use.

Provider authentication stays outside untrusted tool and build contexts. An adapter that cannot enforce this separation remains disabled. No reusable account profile is mounted into a worker.

Admission reserves cost and capacity per account, project, and unit before concurrent launch. Usage is deduplicated by invocation and sequence. Unknown spend retains conservative exposure and blocks further affected admission when that exposure cannot be bounded. Estimates remain labeled estimates.

**R46. Verification and review have separate meanings. [REVISED]**

Verification establishes mechanical claims through the canonical gate and required evidence. Independent review records scrutiny, findings, and disposition. A passing model verdict is an assertion that the reviewer found no blocker, not a credential or landing permission.

Landing requires a trusted receipt establishing that independent review occurred against the relevant inputs, disposition of blocking findings, applicable authority approvals, valid proof, and a green candidate gate. Builder and reviewer cannot be the same responsible actor. Another pass cannot erase an unresolved objection.

This preserves the push policy's objection semantics while replacing dispatcher and work-state interpretations that treat passing verdicts as completion authority.

**R47. Proof must survive process boundaries. [REVISED]**

Build proof becomes immutable artifacts before review eligibility. Validation resolves the exact Git object, accepted specification revision, complete criterion set, required evidence, checks, producer identity, and artifact digests.

The current validator already rejects a passed criterion without evidence. The repair also rejects empty or incomplete criterion universes, nonexistent commits, duplicate mappings, missing trusted observations, and fabricated default checks. Execution must invoke contextual validation, not only the current structural subset.

Proof binds the implementation commit. Review binds that proof and reviewed source. Integration evidence binds the exact candidate. Gate-generated stamps and events are external observations under R76, not uncommitted modifications silently included in a success claim.

Receipts cannot contain themselves inside the commit they certify. Signed operational publication joins implementation, proof, review, candidate, and landing.

**R48. Landing never modifies trunk before acceptance. [REVISED]**

The serialized lander fetches remote trunk and constructs a disposable candidate in a dedicated detached workspace. It merges admitted implementation and evidence, materializes accepted projections, and creates the candidate commit.

All conflict handling occurs there. Failed Git commands, failed regeneration, unresolved conflicts, and failed merge commits stop the attempt. Arbitrary union merging of capability catalogs, self-tests, or authoritative history is prohibited. Event exports derive from ordered authoritative records.

The gate, proof checks, review obligations, protected-path authorization, and current scope checks run against the candidate. Failure leaves both local and remote trunk unchanged.

The existing lander checks out configurable `self.trunk`, defaulting to `main`; another worktree holding that branch can make checkout fail. The replacement avoids that checkout entirely.

**R49. Publication and completion. [REVISED]**

Immediately before publication, the lander rechecks claim and authority generations, admission, plan and release scope, decisions, dependencies, approvals, candidate identity, and expected remote trunk tip.

Publication is a fast-forward compare-and-swap against that exact tip. A changed tip requires a new candidate and fresh applicable checks. The remote integration must enforce the expected-old-tip condition; an unconstrained push is insufficient.

The candidate contains the intended shipped projection. Operational completion occurs only after remote confirmation and a committed, replicated landing receipt with `spec.shipped`. Local trunk synchronization follows where safe.

A lost push acknowledgement triggers an exact candidate and ancestry query. It never triggers an inferred success or duplicate publication. R76 defines the tested-tree and evidence binding.

**R50. Enforcement runs outside worker control. [REVISED]**

The authority uses installed, versioned verifier and policy code. A candidate cannot replace the enforcement process authorizing its publication. Candidate tests run under controlled execution, with trusted observations naming executable and input digests.

Architecture loading distinguishes absent, valid, and invalid contracts. An absent optional contract may stand down under adoption rules. An unreadable, malformed, or invalid present contract refuses eligibility at every entry. PLAN-0019's required contracts cannot stand down through absence.

Changes to gate, policy, authorization, runner, and receipt machinery follow protected-path rules and applicable authority requirements. Source landing does not activate a new authority installation. Activation is separately receipted with rollback material.

Denied authorization records identity, operation, unit, contract digest, and reason. Failure to durably record a denial leaves the operation denied and stops dispatch.

**R51. Required floor repairs. [REVISED]**

The following allocation is binding; later packages cannot hide missing prerequisites behind wrappers.

Package A specifies release and behavior-floor relationships, unified completion and eligibility, combined graph semantics, decision bindings, architecture failure behavior, and replacement process enforcement.

Package B implements journaled commands, identity and revocation, protected effect access, explicit repository routing, fenced claims, clock-report fixes, nonce consumption, effect reconciliation, durable reservations, atomic identifier allocation, provider-neutral containment, and the LangGraph packaging boundary.

Package C repairs `dispatch.py` and `tracker_bridge.py` status mutations; `executor.py` proof persistence, contextual validation, default checks, and event ownership; `events.py` and `validate.py` vocabulary and publication; `work.py`, `work_state.py`, `frontier.py`, `plan.py`, and direct execution eligibility; `validate_checks.py` architecture failure handling; `lander.py` candidate publication; and gate-output isolation. It also implements decision-record dependency evaluation and release-regression evidence consumption needed by the slice.

Package D qualifies live engines and their usage and credential behavior on B's lifecycle and accounting foundation.

Package E repairs `request.py`, `request_reconcile.py`, `request_projection.py`, `tracker_adapter.py`, and `authorization.py` for presentation binding, tracker attribution, atomic settlement, and activation. It completes the decision-review and tripwire production flows defined in R71. C cannot claim to test these flows using approval fixtures.

Package F adds project graph operations and governed intake. Package G adds model-mediated coordination. Package H closes distribution, migration, and operational qualification. Recovery commands ship in B, not with a later interface.

**R52. Existing tasks, plans, and readers. [REVISED]**

Legacy tasks become intake candidates for assignments or specification units. Path existence cannot satisfy project completion. Unmigrated tasks remain visible and excluded from autonomous dispatch.

Plans remain accepted scope and dependency documents. Standalone specifications remain valid without invented plans, but enrolled execution requires backlog identity, admission, and project ownership. Releases retain their existing typed hierarchy.

Work-state, status, tracker, metrics, indexes, plan dependencies, and release checks consume the same completion predicates in R70 and R76. A build-only run may finish its attempt without completing engineering work. Declared regression journeys do not prove those journeys ran.

Historical records are imported as historical evidence. Migration fabricates no signatures, admissions, reviewers, or shipped events.

**R53. Module and API boundaries. [REVISED]**

Implementation belongs in canonical `engine/` and follows byte-identical synchronization and pack rules. New modules separate domain contracts, storage and replay, authorization, scheduling, execution adapters, supervision, and floor integration.

The domain layer accepts plain versioned data and returns transitions or named refusals. It imports neither LangGraph nor worker engines. Only the store commits transitions, the runner launches engines, the lander publishes source, and the Evidence Service signs trusted observations.

Every new module or non-code asset has an explicit distribution disposition. Existing template synchronization compares counterparts and does not prove that a new repository-only module is distributed. Packaging must detect omissions against an authoritative inventory.

CLI inspection, stop, and recovery use explicit domain and repository identities. Mutations use the authenticated command API. Ordinary decisions are answered through tracker tickets.

**R54. Migration cutover. [REVISED]**

Enrollment inventories specifications, plans, releases, behavior floors, tasks, claims, runs, requests, decisions, and proof. A signed migration receipt identifies accepted imports, unresolved records, and missing historical authority evidence.

Cutover drains or fences legacy workers, disables legacy writers, establishes authoritative routing, and activates readers and command paths together. Old clients refuse enrolled writes rather than falling back to local ledgers.

Accepted document bytes and operational lifecycle are authoritative in the store and signed replica. Worktree edits are proposals until accepted. A materializer alone produces legacy status files and event views at a declared watermark. Workers start from an explicit accepted commit, not the provisioner's current HEAD.

**R55. Delivery order and specification discipline. [REVISED]**

Packages A through H form an implementation DAG. They are planning groupings, not units. Each concern receives its own new `VELDO` specification through R73's allocation procedure. Existing `WARP` identities remain unchanged.

Every implementation specification has three or four acceptance criteria in R10's form. Proof enumerates the applicable schemas, transitions, boundaries, or adapters and establishes that the tested universe matches them. Removing a failure case cannot silently reduce completeness.

A package is complete only when its required specifications have proof, independent review, and a green gate with the required landing receipts.

**R56. Package A: ratified boundaries and executable contracts. [REVISED]**

A precedes runtime implementation. Separate specifications establish decision records and effective policy amendments, entity and lifecycle schemas, release and behavior-floor integration, combined graph rules, signing and authority contracts, completion predicates, and Section 2 admission semantics.

Its proof establishes schema closure, forbidden-transition rejection, authority substitution refusal, preservation of historical identifiers, and scope revision distinct from concurrency version. It defines missing and stale decision-observation behavior before graph persistence is built.

VELDO-0015's existing implementation is inspected as a prerequisite; its report follow-ups are assigned to B. No new clock-detection implementation is presumed necessary.

**R57. Package B: durable control foundation. [REVISED]**

Depending on A, B implements atomic journaled commands, signed replication, authenticated membership and delegation, revocation, protected signing and effects, explicit routing, fenced claims, complete read-set validation, durable capacity and spend reservations, atomic identifier allocation, and recovery commands.

The provider-neutral runner implements real launch records, process supervision, containment, exit detection, stopping, and safe retirement. Only model responses are faked. LangGraph's adapter boundary, checkpoint isolation, runtime lock, and pack inventory also begin here.

Tests race real processes, kill them at durable boundaries, corrupt signatures, replay commands, replace clone paths, and restore replicas. Effect-resolution commands exist before their crash tests. Required outcomes include one winner, stale-generation rejection, no acknowledged success lacking required replication, and explicit uncertainty without repeated effects.

**R58. Package C: first end-to-end floor slice. [REVISED]**

Depending on A and B, C connects one admitted specification through real claim, isolated clone, construction, canonical gate, proof files, independent review assignment, policy, candidate landing, remote confirmation, and completion receipt.

The model provider is fake. Git, files, SQLite, signing, locks, containment, gate execution, policy, and a bare test remote are real. A minimal LangGraph adapter uses the local checkpointer. Packaging is exercised from the installed artifact.

The slice proves successful landing, unchanged trunk after a red gate or rejected approval, refusal after dependency or authority regression, and recovery after a lost landing acknowledgement without a second publication. Direct executor and review entry points receive the same attacks.

Recorded authorization fixtures may test policy consumption; they do not certify tracker projection, attribution, settlement, or interrupted decision work. Those end-to-end tests belong to E after its repairs. No project-manager feature is built on the floor before C passes.

**R59. Package D: production runner and governor. [REVISED]**

Depending on C, D qualifies Claude Code and Codex against the existing provider-neutral lifecycle, credential boundary, and accounting.

Its universe includes every supported version and host profile, normal and signal exit, hangs, escaped-descendant attempts, orphan recovery, malformed output, missing usage, exhausted budget, scope change, and revocation. Escaping containment, retaining authority after fencing, or unmeasured spend enabling unrestricted concurrency is a falsifier.

Live qualification records actual behavior and costs. Fake-provider success cannot certify production adapters.

**R60. Package E: enrolled-channel work and decisions. [REVISED]**

Depending on C, E implements the assignment inbox and projections on enrolled input surfaces, versioned presentations on every channel, canonical actor attribution, restricted channel-edge signing, atomic settlement, decision binding, and repaired PLAN-0016 projection. Telegram chat, Jira, signed CLI, and email when enrolled are decision surfaces under the same master-and-proxies contract. The tracker has no first-answer precedence.

Each channel edge has its own restricted key, enrollment, and attribution evidence. Chat assertions bind message ID, sender ID, and timestamp pulled from the platform, never text alone. Every answer names the presentation the person saw. Veldo settles once and records the originating channel; neither a conversation nor a tracker projection becomes a second record. Signed CLI remains a bootstrap and administrative primitive and is also a decision surface when enrolled.

Acceptance covers concurrent answers within and across channels, stale presentations, changed brief text, expired requests, stronger request-level roles, insufficient quorum, repeated reviews by one principal across channels, revoked membership or edge keys, lost projection acknowledgements, conflicting history, and crashes around settlement. A full interrupted decision flow changes the governing subject while an answer is pending and proves refusal of the stale answer after restart on every enrolled channel.

Live ingress and external mutations activate per channel only after separate required specifications and real channel sandbox proof. Tracker activation retains its real tracker sandbox requirement. Unestablished attribution, presentation binding, or safe restricted signing blocks the affected channel. No channel may bypass the shared authority predicates. E may proceed alongside D once C passes.

**R61. Package F: projects, objectives, grooming, and dependencies. [REVISED]**

Depending on E, F implements ownership, objective acceptance, backlog lifecycle, tracker grooming, Section 2 work classes, quarantine, standing occurrences, decomposition, release-execution binding, and dependency invalidation.

Proof establishes that objective acceptance does not admit a later feature, failed reproduction routes a defect to grooming without lowering severity, a combined cycle blocks authorization, and prerequisite withdrawal removes readiness. Concurrent elaboration must produce distinct identifiers and one artifact per source revision.

An authorized reader can trace outcome, request, release or plan contribution, specifications, assignments, dispatches, decisions, costs, and acceptance receipts without consulting a model conversation.

**R62. Package G: project-manager execution and configurable teams. [REVISED]**

Depending on D and F, G implements project-manager graphs, team configuration, specialist selection, bounded elaboration, proposal validation, and per-project serialization.

Proof covers concurrent input, complete-read-set staleness, repeated graph execution, missing specialists, attempted escalation, exhausted budgets, and checkpoint loss or disagreement. A deterministic replacement adapter must produce identical Veldo transitions for identical authorized proposals.

Deleting all checkpoints leaves admission, dispatch history, decisions, and completion unchanged. No checkpoint may cause a committed effect to repeat.

**R63. Package H: installation, migration, and operational qualification. [REVISED]**

Packaging begins in B and is exercised in C. H depends on all earlier packages and closes full adoption and recovery proof.

Every composed pack installs its declared runtime and runs the first slice from the installed artifact. Qualification covers another clone, another enrolled principal using fixture identities where appropriate, restart, authority replacement, simulated machine loss, journal corruption, revocation during execution, and rollback compatibility. Fixture identities do not enroll real authorities.

The decisive recovery test changes scope or revokes authority while work runs, crashes after an external effect before acknowledgement, restarts from conflicting local observations, and proves neither repeated effect nor unsupported completion.

Source-tree tests alone cannot establish release readiness.

**R64. Deliberate exclusions and remaining facts to establish. [REVISED]**

This plan introduces no Kafka, Redis, Temporal, Kubernetes, second database within a coordination domain, microservice decomposition, LangGraph server, automatic host failover, or cross-repository execution transaction.

It does not authorize customer charging, production deployment, telecom operations, or integration with another operator. It does not design a new management console, prescribe unverified Jira board changes, modify published prose, or incorporate Sompo material.

Remaining installation facts are the workstation's qualified containment and helper configuration, protected remote durability and access controls, exact engine and dependency versions, safe provider authentication separation, quarantine scanner qualification, and a permitted tracker notification transport. Their implementation specifications and observed tests settle them.

Additional named authorities are Dmitry's to enroll under R37. The authority location and multi-repository question are settled by R20 and R75. Kernel Section 2 is supplied and ported; there is no unresolved work-class enumeration or Git review base.

**R65. Releases, plans, and behavior floors.**

The existing `veldo.release/v1` contract remains the typed grouping above plans. Members are releases or plans, plans terminate membership recursion, membership forms a forest, and MVP denotes the first release. Project records do not replace this hierarchy.

Each enrolled release tree and plan has one owning project. A project may own several release trees and standalone plans. Objectives reference contributions from them without acquiring duplicate ownership. A release execution is a new durable record binding one accepted release revision, recursively resolved member digests, required outcomes, regression obligations, acceptance authority, and execution status.

Release execution states are `PLANNED`, `ACTIVE`, `BLOCKED`, `ACCEPTED`, `CANCELED`, and `FAILED`. Acceptance requires every required member outcome plus actual regression receipts. A release declaration's `released` string alone cannot establish acceptance. Cancellation stops its uncompleted authorized work; project cancellation subsumes that stop. Objective cancellation affects units only through an explicit disposition of their owning backlog items.

The separate `.veldo/release.py` rollout machinery is not activated by accepting a release artifact. Deployment remains separately authorized.

Existing behavior-floor records are structurally validated but not yet execution prerequisites. Enrolled work shall bind applicable floor revisions and affected pins into eligibility and verification. Missing required floors, unresolved dispositions, and changed pinned behavior block until the designated baseline authority accepts a version-bound settlement through a ticket. A floor settlement cannot authorize unrelated scope expansion.

**R66. Policy-qualified defects and admission authority.**

A `POLICY_DEFECT` restores behavior already required by an accepted specification or standing invariant. Automatic admission requires a cited accepted revision, named failing criterion, affected supported version, quarantined reproduction, bounded affected surface, and proposed change envelope.

A trusted reproduction operation must demonstrate violation before admission. It records baseline, environment digest, steps, expected behavior, actual observations, and artifact identities. Reproduction does not authorize replacement behavior.

Changing an accepted contract or criterion, public behavior or interface, data model, dependency policy, protected-path scope, release policy, or compatibility target disqualifies policy-defect admission. The item returns to `AWAITING_GROOMING` as `PRODUCT_CHANGE`, `TECHNICAL_CHANGE`, or another applicable class.

Duplicate, obsolete, unsupported-version, destructive, production-data-dependent, and expected-behavior reproductions fail automatic admission. Lack of clean reproduction never lowers severity; the item goes to grooming or security-emergency handling.

The kernel's single-repository defect boundary applies per Veldo coordination domain. A defect requiring changes in several repositories is blocked as unsupported, never partially admitted. Several installations on one host do not waive that rule.

Every admission records policy identity, digest, signer, version, inputs, evaluation, and expiry where policy is used. Automatic admission does not grant queue precedence. Priority comes from the priority authority or signed applicable policy. Incident-originated work uses the same intake and backlog.

Internal retries, lease recovery, merge refresh, and in-scope remediation may continue under valid existing admission. They still require reconciled attempts and current eligibility.

**R67. Quarantine.**

Every external reproduction, attachment, design file, dependency manifest, archive, script, production alert, and generated fixture enters quarantine before model or execution consumption. Quarantine assigns digest, media type, declared source, trust label, size, expansion limit, executable-content flag, secret-scan result, malware-scan result, and prompt-injection taint label.

Unknown or unavailable inspection results are explicit failures for automatic admission, not clean results. Inspection records scanner identity and version. Taint labels survive extraction, copying, and derivation. Scan success does not authorize instructions found in the material.

Archive expansion is limited to 1 GB, 10,000 files, nesting depth 10, and ratio 100:1. An exception requires a signed authority decision that narrows the execution environment further.

Quarantine execution has no repository writes, credentials, production data, deployment access, host filesystem access, or unrestricted network access. Its exposed filesystem consists only of bounded input and scratch mounts.

Network access defaults to denied. Allowlisted requests record destination, method, content digest, byte count, and policy decision. Failure to classify or inspect safely prevents automatic admission. Inspection tools are local execution dependencies behind a stdlib contract boundary; this requirement does not authorize a new scanning service.

**R68. Security emergencies and standing maintenance.**

`SECURITY_EMERGENCY` is reserved for active or credibly imminent exploitation, credential compromise, severe privacy exposure, or a time-bounded security obligation whose ordinary delay materially increases harm.

Break-glass authority binds a named responder and signed policy enumerating repositories, targets, actions, duration, and blast radius. Permitted containment may disable a feature, revoke or rotate credentials, block traffic, halt release, reversibly roll back, or isolate a target only when explicitly listed.

It cannot silently authorize permanent features, public API changes, irreversible migrations, new dependencies, or expanded collection. Before or atomically with execution, it creates a backlog item, admission request, priority, incident record, receipt, and owner-notification obligation. Ratification by the security authority is due within four hours. Adversarial review and a Veldo decision or incident record are due within one business day, using the configured operations calendar.

An unratified patch cannot exceed a 5 percent canary or equivalent isolated cohort and must expire or roll back at the deadline. PLAN-0019 does not provide production rollout, so the percentage rule has no live deployment target here; an unratified patch remains isolated from general distribution. Deadline enforcement cannot depend on the stopped orchestrator. Without a qualified reversible action and deadline enforcer, Veldo stops and requests the security authority.

Standing maintenance requires a deliberately authored signed ticket specifying cadence, start and expiry dates, eligible paths or dependencies, permitted version movement, prohibited breaking changes, per-occurrence budget, concurrency, tests, and release limits. Each occurrence receives a distinct item and receipt chain. An exceeded bound returns it to grooming.

Refactors, upgrades, certificate renewal, SDK migration, test-flake repair, observability, build maintenance, dead-code removal, and deprecation qualify only when explicitly covered. Uncovered technical debt uses `TECHNICAL_CHANGE`.

**R69. Readmission, admission debt, and scope enforcement.**

Admission scope is machine-comparable across paths, interfaces, specifications, criteria, data classes, dependencies, targets, risk tier, and artifact types.

Discovery of a new protected path, public-interface change, migration, unlisted dependency, new target, increased risk, changed criterion, or budget increase above 20 percent invalidates authorization. Smaller budget increases still require authorization when they exceed the signed ceiling; the 20 percent threshold is not free spending permission.

Invalidation moves affected units to `AWAITING_AUTHORITY` and the backlog item to `AWAITING_GROOMING`. Further build and merge actions stop; only already authorized containment, observation, and reconciliation may continue. A post-admission class change also invalidates admission, except an explicit security escalation under R68, which grants only its bounded emergency authority.

Status and tracker views report counts and oldest ages for `RAW`, `PREPARED`, and `AWAITING_GROOMING`. Admission debt is prepared work older than seven days and its total proposed Tokens of Effort. Missing estimates remain visible as unknown, never zero. Debt older than fourteen days creates an andon warning without admission or reprioritization.

Rejected items retain preparation receipts and rejection reasons and consume no floor capacity.

**R70. Authoritative snapshots and executable eligibility.**

An action reads an immutable snapshot identified by domain, repository, accepted source commit, journal sequence, published watermark, and the versions and digests of every input. This includes specifications, plans, releases, decisions, floors, policy, membership, admission, graph, roster, reservations, and relevant receipts.

Commands declare a complete read set, including collection or graph versions for predicates such as absence of blockers. Checking only the project version is insufficient. The transaction rejects changed inputs and newly inserted conflicting records. A shared eligibility service produces named decisions from this snapshot.

Selection, direct execution, build, review, claim, redispatch, result acceptance, and publication all invoke that decision with station-specific predicates. Review cannot bypass draft-plan, decision, or dependency checks. Adapters cannot substitute mutable checkout reads.

The materializer publishes immutable snapshot directories and atomically switches a current pointer. It alone writes enrolled legacy projections. A consumer never reads a partially refreshed corpus. Cached views expose their watermark; authoritative decisions never use stale caches.

Attempt finished means the runner's process attempt ended with trusted exit and accounting observations. Artifact accepted means the station's validator or acceptance authority accepted exact artifact digests. Revision landed means R76's publication receipt exists. Objective satisfied means R06's outcome assessment exists. Each fact names its subject revision and evidence; none implies the next.

These facts are stored as signed receipts and replicated under R23. Invalidation appends a superseding or impact record; it never rewrites the historical observation.

**R71. Decision bindings, independent review, and tripwires.**

A governing decision binds exact subject digests and explicit affected projects, release executions, plans, backlog items, specifications, and contracts. Existing inline `open_decisions` entries become references to these records. Unresolved references block.

Settlement of the current decision revision updates its binding and dependent eligibility atomically. Supersession, expiry, changed framing, or a failed assumption reopens the obligation through a new request revision and withdraws affected readiness. Old settlement evidence remains immutable.

Decision review binds full framing content, not only declared ID and version. Required counts measure distinct authenticated reviewers satisfying independence policy, not supporting files. Several reviews by one principal cannot fill several reviewer positions. Blocking objections require explicit disposition.

Each governing assumption declares its observation type, trusted source, subject digest, maximum age, and failure treatment. Missing, stale, contradictory, or invalid observations block any permission relying on that assumption and open a review ticket. Advisory assumptions may warn only when explicitly classified as non-authorizing. Measured readings expire as well as manual attestations.

**R72. Versioned channel presentation and settlement. [REVISED]**

Every presentation receipt, on every enrolled channel, binds request ID and version, full request digest, subject digests, rendered brief bytes, risk and authority statements, offered choices, channel identity, external conversation or issue identifier, external presentation identifier, and publication time. Signed CLI and enrolled email use the same receipt contract as chat and the tracker.

Presentation keys include version and content digest. Reusing a permanent request brief key cannot suppress revised text. Each replacement visibly supersedes the prior presentation on that channel.

An answer must explicitly identify the presentation it addresses and its ruling and rationale. Canonical channel evidence establishes the enrolled actor and ordering. Current status, answer text, or a timestamp alone cannot prove which revision the person saw. Chat evidence includes platform message ID, sender ID, and timestamp pulled from the platform. A pasted transcript is insufficient.

The channel edge obtains canonical evidence using its protected credential or verifies the signed CLI envelope, verifies presentation and actor binding, and submits its restricted signed assertion under R38. Edits without attributable history, missing actor kind, automation masquerading as a person, and unprovable gaps refuse settlement. Email remains unavailable until its enrollment and canonical attribution evidence are qualified.

Accepted assertions from enrolled channels accumulate toward the required quorum by distinct principal, never by channel count. The request version receives only one terminal transition in Veldo's authority, attributed to the originating channel and bound to the presentation. Settlement, decision effects, nonce consumption, and projection obligations commit together. Outbound terminal projections follow that receipt; a channel is a proxy and never a second record. Lost acknowledgement is recovered using stable correlation and committed state. Concurrent cross-channel answers cannot create competing settlements.

**R73. Atomic allocation and document publication.**

The authority allocates new `VELDO` specification aliases under a transactional per-repository counter and uniqueness constraint. It validates unit identifiers through `claim.unit_id_problem` before reserving unit artifacts.

Source provenance has an idempotency key covering source system, source identity, source revision, and intended artifact role. A repeated identical proposal returns the same allocation. Changed content requires a new revision or named conflict, never an overwrite.

The allocation transaction records identifier, immutable artifact digest, source mapping, version, and publication obligation. Materialization occurs afterward by exclusive creation and atomic replacement of the declared version. Readers consume only published snapshots, so allocation plus eventual file publication is one logical operation without pretending SQLite and a worktree share an atomic write.

Crashes leave recoverable pending publication. Reserved identifiers are not recycled. Concurrent authors cannot overwrite one another. Editing an existing specification compares its expected version and content digest before acceptance.

**R74. Effect-specific reconciliation and recovery commands.**

Every effect contract declares its receiver, idempotency scope, acceptance evidence, outcome query, success predicate, retry conditions, compensation, and resolving authority before dispatch. An effect lacking a safe uncertain-outcome procedure is unavailable for autonomous execution.

Git publication is reconciled against exact remote commit and ancestry. Tracker creation and comments use stable external correlation and canonical history. Worker launch uses containment and durable receiver records. Other target effects require a separately qualified adapter.

A consumed nonce proves only that authority was reserved or used at a boundary. It cannot establish whether the effect started or finished. Resolution records trusted observations and one of R32's findings. A new nonce never erases the original dispatch.

Recovery commands can attach target evidence, import lost acknowledgements, certify nonexecution from conclusive receiver evidence, fence an attempt, authorize a bounded retry, initiate compensation, or retain an unresolved stop. Decisions requiring authority arrive through tickets; command execution applies the accepted ruling.

Compensation is a new contracted effect with its own identity, authorization, and receipt. It cannot be inferred safe from the original permission. Uncertainty remains visible until evidence or an explicit accepted-risk disposition resolves the operational obligation; historical certainty is never invented.

**R75. Authority deployment, startup, and routing.**

The authority runs on the designated Linux workstation as a user systemd service under an operations-controlled account. One instance serves one coordination domain. Operations installs a versioned unit, fixed executable path, protected configuration, runtime socket permissions, and the constrained runner helper.

An authorized installation step enables the instance after host qualification and enrollment. Systemd starts it according to that activation and restarts unexpected exits only through the recovery startup path. Repeated failures leave it stopped with a durable diagnostic. An explicit operations stop remains stopped until authorized restart. Running while logged out requires separately established systemd user-service persistence.

The CLI never silently starts a competing authority. When absent, it reports `AUTHORITY_UNAVAILABLE`, service identity, last known watermark, and the documented operations start procedure. It may read explicitly stale snapshots but cannot grant claims or mutate local substitutes.

Every API call carries domain and repository identity plus explicit artifact or workspace coordinates. Routing never derives from current directory, module-global `ROOT`, ambient environment overrides, or whichever repository supplied an imported event module.

The status listener, when enabled, is read-only and validates loopback binding at the actual socket boundary, including direct API calls. Remote inspection uses the authenticated relay. The current default-host argument is not sufficient enforcement.

**R76. Exact landing evidence and completion publication.**

Landing names an implementation commit, proof artifact or evidence commit, reviewed source and proof digests, old remote trunk tip, integrated candidate commit, exact tested tree, gate invocation, and final publication receipt.

The lander constructs the entire candidate, including deterministic legacy projections at a fixed input watermark, before final verification. The canonical gate's stamp and event output are redirected to a trusted external observation destination in this mode. They cannot dirty the tested tree or become uncommitted evidence silently omitted from publication.

Trusted verification records the candidate commit and tree, command and verifier digests, required checks, actual results, and post-run tree equality. Any unauthorized candidate mutation fails verification. Requiring the final gate's receipt inside the candidate it certifies is prohibited.

Required regression means observed execution of the complete declared journey set against the relevant candidate and environment, with current accepted results. A journey declaration alone is insufficient. New evidence that changes candidate bytes requires a new candidate and applicable verification.

After policy acceptance, the serialized effect executor performs the exact-tip publication and reconciles its acknowledgement. Only then does Veldo commit and replicate the landing receipt and `spec.shipped` event. The append-only event projection joins the authoritative journal by unit and dispatch identity; it is not an independently merged authority.

A clean build-only attempt, accepted proof artifact, passing review assertion, shipped status string, or successful process exit cannot substitute for this completion chain.
