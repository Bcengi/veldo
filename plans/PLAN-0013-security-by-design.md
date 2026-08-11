---
schema: veldo.plan/v1
id: PLAN-0013
title: Security by design - secrets are references never values, a fail-closed gate with zero exceptions, secret-free agent context, least-privilege per-task credentials, untrusted input as data, supply chain as flagged decisions, and signed attributable work
kind: mvp
status: released
revision: 3
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-22
risk: standard

outcomes:
  - id: O1
    becomes_true: >
      Secrets are references, never values. An agent integrating a service wires
      a reference (a name in a managed store) and the runtime resolves it at the
      moment of use through a pluggable seam; the agent never handles the
      literal secret. Because references are the only legitimate mechanism, a
      literal secret has no valid reason to exist in any file, diff, config, or
      agent context.
    measure: >
      Conformance against a fake store: an integration wired by reference works
      end to end; the resolver never logs, echoes, or returns a value into agent
      context; malformed or unresolvable references refuse at use; reference
      syntax is validated at contract time.
  - id: O2
    becomes_true: >
      The gate fails closed on any literal secret, anywhere, with zero
      exceptions. Pattern and entropy scanners run on every diff, every
      generated file, and every recorded artifact, with no allowlist mechanism
      at all - no "it is just a test key" - and the check can be this absolute
      only because O1 removed every legitimate hit. The design removes the
      excuses first; then enforcement removes the mercy.
    measure: >
      Seeded literal secrets of each class (known patterns and high-entropy
      strings) refuse in a diff, a generated file, and a proof artifact, with
      the finding named; the check exposes no allowlist or exception path; the
      clean tree stays green.
  - id: O3
    becomes_true: >
      The agent's context is clean by construction: redaction sits at the seam
      where data enters context, so a secret cannot leak from a context window
      that never contained it; and untrusted input (issue bodies, READMEs,
      dependency docs, logs) enters context as data, never as instructions,
      containing prompt injection for agents that hold commit access.
    measure: >
      A seeded secret present in source data never appears in the agent's
      context transcript; a seeded injection payload in an issue body, a
      README, and a log line does not alter agent behavior in the conformance
      harness, and the content is demonstrably handled as data.
  - id: O4
    becomes_true: >
      Credentials are per-agent, per-task, least-privilege, short-lived, and
      attributable. An agent receives the narrowest capability its declared
      task needs, for the duration of the task, attributable to that agent and
      task in the audit record - never the organization's keys, never forever.
    measure: >
      Against a fake issuer: a request broader than the task's declared needs
      refuses; an expired credential fails at use; the audit record names the
      agent, the task, and the reference resolved; nothing issues without a
      declared task scope.
  - id: O5
    becomes_true: >
      The rest of the surface is policy as code. A new dependency is a flagged
      decision unit, not a silent convenience, with lockfile integrity,
      provenance, and license policy enforced; generated infrastructure is held
      to least privilege at the gate; and commits are signed and attributable,
      so every action of the fleet is on the record.
    measure: >
      A dependency added without a recorded decision reference refuses; a
      tampered lockfile refuses; a license outside policy refuses; an
      over-broad generated-infrastructure privilege refuses with the rule
      named; an unsigned or unattributed commit refuses wherever enforcement is
      enabled (default per D3).
  - id: O6
    becomes_true: >
      Security is a review dimension and the existing estate is migrated
      honestly. The independent reviewer grades secrets handling, input trust,
      privilege footprint, and dependency delta above the mechanizable floor;
      and the repositories VELDO itself lives in and builds are inventoried for
      literal secrets, migrated to the reference seam, and only then flipped to
      the fail-closed gate (sequencing per D4), with any found exposure
      surfaced to a human for rotation.
    measure: >
      A correct-but-insecure fixture change is refused by review with a
      security finding; the inventory report exists for this repository, the
      migrations land through the normal loop, and the fail-closed flip is
      recorded; no secret value appears in any report or artifact along the
      way.

non_goals:
  - id: NG1
    text: >
      No secrets manager is built. The seam resolves references through
      pluggable adapters (environment and OS-keychain reference
      implementations; a specific manager as blessed default is D1); VELDO never
      stores, proxies, or caches secret values itself.
  - id: NG2
    text: >
      No live credential operations. Everything is proven offline against fake
      stores and fake issuers; the migration inventory runs locally
      in-session; rotating any real exposed secret it finds is a human act the
      plan surfaces with a named owner, never performs.
  - id: NG3
    text: >
      No exception machinery, ever. The secret gate ships with no allowlist,
      no waiver field, and no bypass flag, and this plan never adds one; the
      only legitimate path for a secret is the reference seam. An exception
      mechanism would silently rebuild the excuse the design exists to remove.
  - id: NG4
    text: >
      No daemons and no detached processes. Every check and every pass runs
      inside the gate, the validator, or a normal in-session invocation; the
      established posture stands.
  - id: NG5
    text: >
      No rebuild of the loop. This plan upgrades the built-in secret scan,
      fills gate slots, extends the verdict contract the way the shape-fit
      lane did, and reuses the policy and decision machinery; it does not
      redesign any of them.
  - id: NG6
    text: >
      No security theater. What cannot be checked mechanically is not faked as
      a scanner; it goes to the security review lane as honest reviewer
      guidance, and every mechanical check ships with the negative test that
      proves it refuses.

constraints:
  - id: C1
    text: >
      Every item is built through VELDO itself: spec, gate, proof, independent
      fresh-context review; the refusals are the product, and every safety
      property lands as a negative test (anti-vacuity).
  - id: C2
    text: >
      The enforcement core is protected: specs touching the secret gate check,
      the resolver seam, the signing verification, or the policy files carry a
      high risk floor with recorded human approval. Anything may raise a risk
      class; nothing may lower it.
  - id: C3
    text: >
      Fail closed, everywhere: an unresolvable reference refuses at use, a
      scanner hit refuses rather than warns once fail-closed is active, an
      unknown dependency source refuses, and doubt never downgrades to a
      warning.
  - id: C4
    text: >
      Ordering is explicit: the reference mechanism ships before the absolute
      check is enforced, and an existing repository flips to fail-closed only
      after its inventory and migration (sequencing per D4). Design removes
      the excuses first; enforcement removes the mercy second, and never in
      the other order.
  - id: C5
    text: >
      No secret value ever appears in a spec, proof, log, event, verdict,
      report, or context transcript; references only. This generalizes the
      established keep-tokens posture from the tracker edge to the whole
      platform.
  - id: C6
    text: >
      Cross-plan seams are soft: context redaction shares the seam family with
      the production responder's evidence plane (PLAN-0012), and supply-chain
      decision units use the foundational-decision records (PLAN-0011) where
      that machinery exists, standing down to a built-in decision note where
      it does not; never a hard dependency edge across plans.
  - id: C7
    text: >
      The canon is engine: every seam, check, skill change, and
      policy template lands in the engine, syncs byte-identical to this
      repository's instances, and stays fully generic; all machinery is
      runnable in-session.

feature_tree:
  - id: F1
    title: The reference seam - secrets as names resolved at the moment of use
    outcome_refs: [O1]
  - id: F2
    title: The absolute gate - fail closed on any literal secret, zero exceptions
    outcome_refs: [O2]
  - id: F3
    title: Clean context - secret-free by construction and untrusted input as data
    outcome_refs: [O3]
  - id: F4
    title: Least privilege - per-agent per-task credentials and generated infrastructure
    outcome_refs: [O4, O5]
  - id: F5
    title: Supply chain and attribution - dependencies as decisions, signed commits
    outcome_refs: [O5]
  - id: F6
    title: The security review lane and the honest migration
    outcome_refs: [O6]
  - id: F7
    title: Release - the engine ships it and the docs are true
    outcome_refs: [O1, O2]

work:
  - item: W1
    spec: WARP-1301
    title: >
      The secret reference seam. veldo.secretref/v1: a reference is a name
      resolved at the moment of use through a pluggable resolver seam
      (environment and OS-keychain reference adapters; blessed default per D1),
      with reference syntax validated at contract time, resolution that never
      logs or echoes values, and refusal on any unresolvable or malformed
      reference. Agents wire references only; the helper API gives them no way
      to read a value into their own context. Proven against a fake store.
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-1302
    title: >
      The absolute gate check. Upgrade the built-in secret scan to pattern plus
      entropy scanning over every diff, every generated file, and every
      recorded artifact (proofs, logs, reports), failing closed with zero
      exceptions and no allowlist mechanism at all - possible only because W1
      removed every legitimate hit, and the check says so in its refusal text.
      Ships with seeded negative tests per secret class; fail-closed activation
      in an existing repository is sequenced by the W10 migration per D4.
    feature_refs: [F2]
    depends_on: [WARP-1301]
    order: 20
  - item: W3
    spec: WARP-1303
    title: >
      Context secret-free by construction. Redaction at the seam where data
      enters an agent's context, in the same seam family as the production
      responder's evidence plane (soft cross-plan seam, per C6): values
      resolved by the runtime are opaque to the agent, and source data is
      scrubbed before it becomes context. Conformance proves a seeded secret in
      source data never appears in the context transcript.
    feature_refs: [F3]
    depends_on: [WARP-1301]
    order: 25
  - item: W4
    spec: WARP-1304
    title: >
      Per-agent, per-task credentials. A credential issuance model over the
      resolver seam: scope derived from the task's declared needs and nothing
      more, short-lived with enforced expiry, attributable to the agent and
      task in the audit record, never an organization-wide key. Reference
      implementation against a fake issuer, with refusal tests for over-broad
      requests, missing task scope, and expired credentials at use.
    feature_refs: [F4]
    depends_on: [WARP-1301]
    order: 30
  - item: W5
    spec: WARP-1305
    title: >
      Untrusted-input isolation. External text - issue bodies, READMEs,
      dependency docs, log lines, tracker content - enters agent context as
      data, never as instructions: mechanical labeling and quarantine at the
      seams where it arrives (extending the tracker edge's established
      untrusted posture), with conformance harnesses that seed injection
      payloads at each seam and prove behavior does not change. Day-one seam
      scope per D2.
    feature_refs: [F3]
    depends_on: []
    order: 35
  - item: W6
    spec: WARP-1306
    title: >
      Supply chain policy as code. A new dependency is a flagged decision unit,
      not a silent convenience: a manifest or lockfile change without a
      recorded decision reference refuses; lockfile integrity is verified;
      provenance and license policy are declared in policy files and enforced
      at the gate. Uses the foundational-decision records where PLAN-0011 has
      shipped and stands down to a built-in decision note where it has not
      (soft seam, per C6).
    feature_refs: [F5]
    depends_on: []
    order: 40
  - item: W7
    spec: WARP-1307
    title: >
      Generated-infrastructure least privilege. Infrastructure artifacts the
      machine generates are held to least privilege at the gate: wildcard
      permissions, over-broad roles, and public-exposure defaults refuse with
      the rule named, through a stdlib-proportionate reference check with a
      pluggable per-stack slot, in the runner-suite posture. Negative tests
      seed each violation class.
    feature_refs: [F4]
    depends_on: []
    order: 45
  - item: W8
    spec: WARP-1308
    title: >
      Signed, attributable commits. Commit signing and agent attribution as
      policy: the machinery to sign, the verification at the gate and push
      seam, and the attribution convention that names which agent produced a
      change, so the fleet's work is auditable end to end. Enforcement default
      (required from first release or configurable-on) per D3; the machinery
      ships either way and is proven with refusal tests when enforcement is
      enabled.
    feature_refs: [F5]
    depends_on: []
    order: 50
  - item: W9
    spec: WARP-1309
    title: >
      The security review dimension. The independent reviewer grades security
      above the mechanizable floor - secrets handling, input trust, privilege
      footprint, dependency delta - the way the shape-fit lane grades
      architecture: the verdict contract carries the security finding,
      correct-but-insecure is a legitimate rework verdict, and a conformance
      fixture proves the refusal.
    feature_refs: [F6]
    depends_on: [WARP-1302, WARP-1305]
    order: 55
  - item: W10
    spec: WARP-1310
    title: >
      The honest migration. Inventory this repository and the codebases the
      platform builds for literal secrets (working tree and reachable history,
      report by reference-shaped finding, never by value), migrate each finding
      to the reference seam through the normal loop, surface anything that was
      exposed to a named human for rotation (a human act, never performed by
      the machine), and then flip the absolute gate check to fail-closed with
      the sequencing D4 selects.
    feature_refs: [F6]
    depends_on: [WARP-1301, WARP-1302]
    order: 60
  - item: W11
    spec: WARP-1311
    title: >
      Release. Land the seam, the checks, the isolation wrappers, the policy
      templates, and the review-lane extension in the canonical engine so
      /veldo:init lays them down and the packs carry them; make the docs true
      (the method and setup documents gain security by design as shipped
      behavior, fully generic); record capabilities honestly; bump the plugin
      version; mark the plan released once the regression is green.
    feature_refs: [F7]
    depends_on: [WARP-1303, WARP-1304, WARP-1306, WARP-1307, WARP-1308, WARP-1309, WARP-1310]
    order: 80

regression:
  journeys:
    - id: RJ1
      title: >
        Seeded literal secrets of each class refuse in a diff, a generated
        file, and a proof artifact with the finding named; no allowlist or
        exception path exists; the clean tree stays green.
      activation: {when: after:WARP-1302}
      suite: secret-scan negative tests under scripts/verify.sh
    - id: RJ2
      title: >
        A seeded secret in source data never appears in an agent context
        transcript, and resolved values are opaque to the agent.
      activation: {when: after:WARP-1303}
      suite: context-redaction conformance (fake store)
    - id: RJ3
      title: >
        Seeded injection payloads in an issue body, a README, and a log line do
        not alter agent behavior; the content is handled as data at every
        declared seam.
      activation: {when: after:WARP-1305}
      suite: untrusted-input conformance harness
    - id: RJ4
      title: >
        An over-broad credential request refuses, an expired credential fails
        at use, and the audit record attributes agent, task, and reference.
      activation: {when: after:WARP-1304}
      suite: credential issuance conformance (fake issuer)
    - id: RJ5
      title: >
        A dependency added without a recorded decision reference refuses; a
        tampered lockfile refuses; a license outside policy refuses.
      activation: {when: after:WARP-1306}
      suite: supply-chain policy conformance
    - id: RJ6
      title: >
        A wildcard or over-broad generated-infrastructure privilege refuses
        with the rule named across the seeded violation classes.
      activation: {when: after:WARP-1307}
      suite: infrastructure least-privilege negative tests
    - id: RJ7
      title: >
        An unsigned or unattributed commit refuses wherever enforcement is
        enabled, and signed attributable work passes unchanged.
      activation: {when: after:WARP-1308}
      suite: signing and attribution conformance
    - id: RJ8
      title: >
        A correct-but-insecure fixture change is refused by independent review
        with a security finding and reworked.
      activation: {when: after:WARP-1309}
      suite: review conformance over a fixture change
    - id: RJ9
      title: >
        The existing gate stays green across every item, and a repository that
        has not yet migrated is unaffected until its fail-closed activation per
        D4; nothing installs a daemon, timer, or detached process.
      activation: {when: start}
      suite: scripts/verify.sh

release:
  milestone: >
    VELDO security by design v1 - secrets exist only as references resolved at
    use, the gate fails closed on any literal secret with zero exceptions,
    agent context is secret-free by construction, credentials are per-agent
    per-task least-privilege and attributable, untrusted input is data,
    dependencies are flagged decisions with lockfile and license policy,
    generated infrastructure is least-privilege at the gate, commits are signed
    and attributable, security is a review dimension, and the existing estate
    is inventoried and migrated - all proven offline, with rotation of any real
    exposure a surfaced human act.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true
  rollback: >
    The seam and checks stand down where no reference configuration or policy
    exists (adoption-safe posture); git revert the plugin version bump;
    inventory reports, decision notes, and audit records are inert data and
    keep their history. The fail-closed flip in a migrated repository is
    reverted only by an explicit human decision, on the record.
  observation:
    duration: >
      Run this repository migrated and fail-closed for a working period: every
      change scanned absolute, context redaction and untrusted-input wrappers
      on the active seams, at least one dependency change flowing through the
      decision path, and the review lane grading security, before the
      capability is recommended to adopting repositories.
      NOT YET RUNNING, and honestly so. The window requires this repository to
      be fail-closed, and the flip is a human's dated decision on a protected
      path: wiring the inventory check into scripts/verify.sh and placing
      .veldo/secret_inventory.json under protected_paths. Both are escalated to
      the owner rather than self-approved. The inventory itself is clean - zero
      real credentials in the tree or in reachable history - so nothing but the
      two approvals stands between here and the window opening.

open_decisions: []

resolved_decisions:
  - id: D1
    text: >
      The default secrets-manager seam for the reference implementation.
    resolution: >
      Reference-only, with environment and OS-keychain adapters and no blessed
      vendor; adapters keep managers pluggable, so naming a specific store stays
      a per-repo documentation choice. Decided by the founder 2026-07-22 via
      "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D2
    text: >
      Untrusted-input isolation scope on day one.
    resolution: >
      Wrap all four named seam families from the start (tracker content,
      READMEs and dependency docs, logs, fetched web content), tracker first
      since its untrusted posture already exists. Decided by the founder
      2026-07-22 via "use recommendations" (start the build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D3
    text: >
      Signed commits from first release.
    resolution: >
      Ship the machinery configurable, with signing on from the first release.
      Decided by the founder 2026-07-22 via "use recommendations" (start the
      build).
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
  - id: D4
    text: >
      Migration sequencing for existing repositories.
    resolution: >
      An advisory, report-only scan first per repository until its inventory is
      clean, then the fail-closed flip; not an immediate fail-closed flip, so
      no repository is blocked on day one. Decided by the founder 2026-07-22 via
      "use recommendations" (start the build). WARP-1310 (the fail-closed flip)
      is unblocked the moment the plan leaves draft.
    resolved_by: founder via 'use recommendations' (start the build), 2026-07-22
    resolved_at: 2026-07-22
---

## Intent

Every service a modern system touches has an API token, and the default
behavior of the tools is exactly wrong: ask an agent to integrate a service and
it writes the literal secret into a config file, wires it through, and the
security model of the whole company becomes the hope that an ignore file is
spelled correctly. Multiply by agent speed: secrets scattered in plaintext
across every project, sitting inside context windows, echoed into logs,
committed at generation speed the moment the hope fails. This is not a corner
case; it is the default, and security by hope is not a security model. The
platform VELDO itself lives on is not exempt - the repositories it builds carry
environment files with literal values today, and this plan says so and fixes
it rather than pretending otherwise.

The design center is an ordering, and the plan is explicit about it. First,
secrets become references, never values: the agent wires a name, the runtime
resolves it at the moment of use, and the literal secret loses every legitimate
reason to exist in any file, diff, config, or context. Only because of that
first move can the second be merciless: the gate fails closed on any literal
secret anywhere - pattern and entropy scanning on every diff and generated
artifact, zero exceptions, no allowlists, no "it is just a test key" - because
the reference mechanism removed every excuse a hit could hide behind. Around
that core, the same discipline covers the rest of the agent attack surface:
context is secret-free by construction (redaction at the seam where data enters
context, the same seam family the production responder's evidence plane uses);
credentials are per-agent, per-task, least-privilege, short-lived, and
attributable, never the organization's keys and never forever; untrusted input
- issue bodies, READMEs, dependency docs, logs - is data, never instructions,
which is what contains prompt injection for agents that hold commit access; a
new dependency is a flagged decision unit with lockfile integrity, provenance,
and license policy as code; generated infrastructure is held to least
privilege at the gate; commits are signed and attributable; and security joins
review as a graded dimension above the mechanizable floor, the way the
shape-fit lane grades architecture. The reversal this buys: a fleet whose
every action is logged, attributed, least-privileged, and gated is the most
auditable workforce that has ever existed - the insider that cannot hide what
it did.

Three postures bind the plan. Everything is proven offline against fake stores
and issuers, and no live credential operation happens: the migration inventory
runs locally, and rotating any real exposure it finds is a human act the plan
surfaces, never performs. Nothing runs detached: every check lives in the
gate, the validator, or a normal in-session pass. And this is a receipts plan:
the method's companion writing describes this design under "Secrets by design,
and the agent attack surface" and is honest that it is design-stage; releasing
this plan turns that chapter from design into receipts, with all shipped
material fully generic in the engine.

## Data provenance - existing machinery versus new instrumentation

Reused as-is (no new machinery invented):

- The gate and its check slots: the built-in secret scan already runs in
  scripts/verify.sh today; W2 upgrades it to the absolute form rather than
  inventing a scanner from nothing.
- The review verdict contract and the lane-extension pattern proven by the
  shape-fit dimension (PLAN-0011); W9 follows it exactly.
- The policy machinery: risk floors, protected paths, recorded human
  approvals; C2 rides on it unchanged.
- The keep-tokens posture from the tracker edge (secret references, never raw
  values in files, prompts, proofs, or logs) and the tracker's
  content-is-untrusted stance; W1 and W5 generalize what those edges already
  practice.
- The event stream and audit conventions for attribution records.

New instrumentation this plan introduces:

- The reference resolver seam, its store adapters, and the fake store and
  issuer used in conformance (W1, W4).
- The entropy half of the scanner and its artifact-wide coverage (W2).
- The context-redaction and untrusted-input wrappers at the declared seams
  (W3, W5).
- Supply-chain policy checks, lockfile integrity verification, and the
  dependency decision note (W6).
- The infrastructure least-privilege checks with per-stack slots (W7).
- Signing and attribution verification at the gate and push seam (W8).
- The inventory and migration tooling, reporting findings by reference-shaped
  descriptor and never by value (W10).

Cross-plan seams (soft, per C6): context redaction shares the seam family with
PLAN-0012's evidence plane; supply-chain decision units bind to PLAN-0011's
foundational-decision records where present and stand down to a built-in note
where absent. No work item here has a hard dependency on another plan's spec.

## Ordered delivery rationale

W1 (the reference seam) is the root of the secrets half; W2 (the absolute
check), W3 (clean context), and W4 (per-task credentials) fan out from it in
parallel. W5 (untrusted input), W6 (supply chain), W7 (infrastructure least
privilege), and W8 (signed commits) are independent roots of the wider attack
surface and can proceed in parallel from the start. W9 (the security review
dimension) waits for the mechanizable floor to exist (W2) and the input-trust
vocabulary (W5) so the reviewer grades above real checks rather than
duplicating them. W10 (the honest migration) needs the seam to migrate onto
(W1) and the scanner to verify with (W2), and its fail-closed flip is gated by
D4. W11 releases once every lane has shipped and the regression is green. The
frontier after approval is W1, W5, W6, W7, and W8; the widest point is five
parallel items.

## Out of scope

Building or hosting a secrets manager (NG1); any live credential operation,
including rotation, which is surfaced to a named human (NG2); any allowlist,
waiver, or bypass for the secret gate, now or later (NG3); daemons, timers, or
detached processes (NG4); redesigning the gate, review, policy, or decision
machinery this plan extends (NG5); mechanical theater for properties only a
reviewer can judge (NG6). The companion book chapter itself is not work in
this repository; this plan only makes its subject true. Per-repository live
adoption beyond this repository's own migration is a separate act after
release.

## Revisions

Revision 1 (2026-07-21): drafted at intake from the founder's go ("everything
has api tokens, AI just wires them in everywhere, .env, gitignore hopefully is
correct - this is all wrong and how shit hits the fan - need it by design and
part of veldo too") and the method's invention notes ("Secrets by design, and
the agent attack surface"), preserving the seed's dependency order: references
first, which is what makes the fail-closed zero-exception gate possible;
then clean context, least-privilege per-task credentials, untrusted input as
data, supply chain as flagged decisions, infrastructure least privilege,
signed attributable commits, the security review dimension, and the honest
migration of the existing estate. D1 through D4 are surfaced for the founder,
not resolved. Status draft: authored, not activated; no work starts until the
plan leaves draft by a recorded human approval.

Revision 2 (2026-07-22): the founder gave the go to start the build ("start the
5 plans build") and chose "use recommendations", resolving all four open
decisions to their recommended defaults, each now recorded in
resolved_decisions above: D1 reference-only secrets seam with no blessed
vendor, D2 wrap all four untrusted-input seam families with tracker first, D3
ship the signing machinery configurable with signing on from the first
release, D4 advisory scan first then the fail-closed flip and not an immediate
flip. Resolving D4 unblocks WARP-1310. open_decisions is now empty. No scope
change; recording decisions is not approval, so status stays draft and leaving
draft still requires a separate recorded human approval.

Approved (2026-07-22): the founder approved the plan to leave draft on the go to
start the build ("start the 5 plans build"); status set to ready, approved_by
dmitry, approved_at 2026-07-22. Per the repo's approve pattern the approval
flips status and records the approver without bumping the revision. The ready
frontier (WARP-1301, WARP-1305, WARP-1306, WARP-1307, WARP-1308) is now live for
pulling into specs.
