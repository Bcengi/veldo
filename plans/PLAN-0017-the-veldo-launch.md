---
schema: veldo.plan/v1
id: PLAN-0017
title: The Veldo launch - the name becomes one declared fact enforced by the build, the public tree is
  DERIVED from the private repository by a repeatable pipeline and never hand-maintained, the site stands
  up before the repository is public, every claim the printed book makes about the reference
  implementation is verified true at the published tag before a single copy ships, and the two
  irreversible acts of the whole method (publishing a public repository and publishing a book) go through
  the method's own two-key rule
kind: mvp
status: ready
revision: 1
owner: dmitry
approved_by: dmitry
approved_at: 2026-07-24
risk: high

outcomes:
  - id: O1
    becomes_true: >
      The name is ONE DECLARED FACT, not a find-and-replace that mostly worked. The external name is
      Veldo across every published surface (the product name, the repository, the command, the plugin,
      the documents, the site, the schema identifiers, the state directory), and the internal-versus-
      external split that carried the project through development is CLOSED: there is no second name
      left anywhere in a shipped surface. The build refuses a reintroduction, so the old name cannot
      drift back in through a new file, a doc edit, or a generated artifact.
    measure: >
      A mechanical check enumerates every shipped surface and reports ZERO residual occurrences of the
      old name outside historical git objects and the one file that records the rename decision; a
      seeded reintroduction in each surface class (a document, a module, a generated artifact, a
      schema identifier, a plugin manifest) is REFUSED by name.
  - id: O2
    becomes_true: >
      Publication is DERIVED AND REPEATABLE, never a hand-curated copy. A pipeline produces the public
      tree from the private repository: the generic method and engine in, every internal artifact out
      (the private plans and specifications that reference internal work, the internal proof corpus,
      the tracker configuration, anything naming a company, a customer, or a person). Running it twice
      produces no diff, and it is proven completely OFFLINE against a scratch target before anything
      is public.
    measure: >
      The pipeline runs to a byte-identical result twice over (idempotent), a scan of its output finds
      zero company, customer, person, or internal-project references and zero secrets, and a seeded
      internal artifact planted in the source is provably ABSENT from the output; all of it proven with
      no network and no public repository in existence.
  - id: O3
    becomes_true: >
      THE SITE IS THE FRONT DOOR AND IT EXISTS FIRST. veldo.dev is live before the public repository
      exists, because the book prints that address as a fact and a reader who types it must land
      somewhere real. It answers what the method is, shows the loop, and routes a reader to the
      documents and to the repository, and its content is RENDERED FROM THE SAME documents the
      repository ships rather than a second hand-written copy that will drift.
    measure: >
      The site builds from the repository's own document sources with no duplicated prose, every
      printed entry point resolves to a real page, and the site is verified live BEFORE the public
      repository is created (the ordering is a checked precondition of the repository item, not a
      hope).
  - id: O4
    becomes_true: >
      The public repository is REAL AND USABLE BY A STRANGER. Apache-2.0 licensed, with the plugin
      installable and the loop runnable in a fresh repository by someone who has never seen the
      private one: specification to gate to proof to independent review, green. The published artifact
      is a versioned release at a tag, not a moving branch.
    measure: >
      From the published release alone, in a scratch repository, the initialisation lays the method
      down and the canonical gate runs GREEN on a seeded specification; the licence, contribution,
      security and conduct files are present and correct; the release is a tag with attached
      artifacts.
  - id: O5
    becomes_true: >
      EVERY PRINTED CLAIM IS TRUE AT THE TAG. Each claim the book makes about the reference
      implementation - that it exists, that it is open source at that address, and every capability
      the manuscript asserts as built - is audited claim by claim against the published release, and a
      false claim BLOCKS the publish. A claim is made true by shipping it or removed, never softened
      into future tense to slip the gate.
    measure: >
      An enumerated claim inventory (every sentence in the manuscript asserting something about the
      reference implementation, with its chapter and line) is resolved against the published tag with
      a verdict per claim and evidence per verdict; a deliberately false claim seeded into the
      inventory is REFUSED; the publish item structurally cannot proceed while any claim is unresolved
      or false.
  - id: O6
    becomes_true: >
      The book ships, and the two irreversible acts of this plan went through the method's own
      two-key rule. Creating a public repository and publishing a book cannot be undone: both carry a
      recorded human authorization bound to the exact artifact digest PLUS an independent fresh-context
      confirmation that what is about to become permanent is what was reviewed. The method's own
      launch is the strongest possible demonstration that its rules are not decoration.
    measure: >
      Each irreversible act has a recorded two-key authorization bound to the digest of exactly what
      was published, and neither key alone permitted it; the published book's interior matches the
      audited manuscript digest; the launch runbook is recorded so the next release is mechanical
      rather than remembered.

non_goals:
  - id: NG1
    text: >
      No new method capability. This plan ships no feature, no check that changes how the loop
      behaves, and no new organ. Capability belongs to the plans that own it; this plan renames,
      derives, publishes, verifies, and releases what those plans already built.
  - id: NG2
    text: >
      No divergent public fork. The public repository is DERIVED OUTPUT, never a second working copy.
      No change is ever authored there, no fix is applied there first, and the pipeline is the only
      writer; a public-side edit is a defect in the pipeline, not a merge.
  - id: NG3
    text: >
      No publication of the private history. The development history carries internal material and is
      not published; the public repository starts from a clean derived tree. Nothing in this plan
      rewrites, filters, or force-pushes the private history either.
  - id: NG4
    text: >
      No softened claim. A claim the implementation does not satisfy is either made true by shipping
      it or removed from the manuscript. Rewriting an untrue present-tense claim into future tense to
      get past the audit is explicitly forbidden, because it converts a checkable statement into an
      unfalsifiable one.
  - id: NG5
    text: >
      No company, customer, person, or internal-project reference on any public surface, and no
      operating metric of any business. The generic-documents rule the gate already enforces for the
      method documents extends to every published file, the site included.
  - id: NG6
    text: >
      No standing service and no automation that runs unattended. The pipeline, the site build, the
      audit, and the release are all invoked in-session; publishing is a deliberate human act with a
      recorded authorization, never a scheduled job.

constraints:
  - id: C1
    text: >
      Built through the method itself: every item is a specification with a green canonical gate, a
      proof manifest mapping each acceptance criterion to evidence, and an independent fresh-context
      review. The launch of the method is the last place to cut the method's own corners.
  - id: C2
    text: >
      The rename is MECHANICALLY ENFORCED, never eye-reviewed. A residual old-name token in a shipped
      surface fails the build. Eye-reviewing a rename across a hundred and thirty-five specifications,
      nine packs, the plugin, the documents, and the generated artifacts is exactly the kind of
      manual sweep that silently misses one.
  - id: C3
    text: >
      The identifier rename is a MIGRATION WITH A PROVEN REVERSE. The state directory name and the
      schema identifiers appear in every specification, proof manifest, pack, and template, so the
      change ships as a one-time migrator with a working reverse migration, proven on a scratch copy
      before it touches the repository, and the gate green on both sides of it.
  - id: C4
    text: >
      One source of truth for prose. The site and the public repository render the SAME document
      sources. No page is hand-copied, because two copies of a sentence are one copy and one future
      contradiction.
  - id: C5
    text: >
      Irreversibility is respected as the method defines it. Creating the public repository and
      publishing the book are irreversible and therefore two-key: a recorded human authorization bound
      to the artifact digest plus an independent fresh-context confirmation. Nothing in this plan
      lowers that class, and no schedule pressure may.
  - id: C6
    text: >
      PRECONDITION, DECLARED HONESTLY: this plan executes at the END, after the capability plans are
      released (the founder's sequence: get it all built, then rename, then site, then public
      repository, then publish the book). Its items are not claimable while a capability plan is
      unreleased, so the launch cannot quietly start early and publish a half-built method.
  - id: C7
    text: >
      The gate is the only done, at the tag. The published release is a commit where the canonical
      gate is green, the proof corpus validates, and the claim audit is clean. A release built from a
      dirty or unproven tree is not a release.

feature_tree:
  - id: F1
    title: The name as one declared, build-enforced fact
    outcome_refs: [O1]
  - id: F2
    title: The derived publication pipeline, proven offline
    outcome_refs: [O2]
  - id: F3
    title: The site, standing up first, from one prose source
    outcome_refs: [O3]
  - id: F4
    title: The public repository and the versioned release a stranger can use
    outcome_refs: [O4]
  - id: F5
    title: The printed claims verified true at the tag
    outcome_refs: [O5]
  - id: F6
    title: The book published, and both irreversible acts two-keyed
    outcome_refs: [O6]

work:
  - item: W1
    spec: WARP-1701
    title: >
      The naming contract and the residual-name check. One declared record of what the name is on
      every surface class (product, repository, command, state directory, schema identifiers, plugin,
      documents, site) and, with it, the mechanical check that enumerates those surfaces and REFUSES
      any residual occurrence of the old name. Ships with the seeded-reintroduction negative tests per
      surface class, so the check has teeth before the rename it is meant to guard. Decides and records
      one thing explicitly: that the rename covers the internal identifiers too (the state directory
      and the schema identifiers), because a fresh public repository with no external adopters is the
      cheapest moment this decision will ever have, and carrying two names forward is the shortcut that
      would never be paid off.
    feature_refs: [F1]
    depends_on: []
    order: 10
  - item: W2
    spec: WARP-1702
    title: >
      The rename executed as a migration with a proven reverse. A one-time migrator renames the state
      directory, the schema identifiers, the command, the plugin manifest and skills, the documents,
      the templates and every pack, and the generated artifacts, with the reverse migration proven on a
      scratch copy first and the canonical gate green on both sides. Every specification, proof
      manifest and pack lands byte-consistent under the new name, the residual-name check from W1 ends
      empty, and the historical proof corpus still validates (a renamed schema identifier must not
      invalidate evidence already recorded).
    feature_refs: [F1]
    depends_on: [WARP-1701]
    order: 20
  - item: W3
    spec: WARP-1703
    title: >
      The parked layout rename, unparked: packs/claude/ becomes packs/claude and the marketplace repoints. This
      was deliberately DEFERRED at the PLAN-0008 release because it MOVES PROTECTED ENFORCEMENT FILES
      (the gate and the push guard inside engine/scripts/) and therefore needs a recorded human
      approval, and it has sat parked ever since. The public repository is the moment it has to happen:
      the layout a stranger clones is the layout that is permanent, and the engine-equals-canonical-source
      story only reads honestly if the Claude pack sits with its siblings. Ships with the recorded
      approval bound to the exact protected paths it touches, the marketplace pointer updated in the same
      change, and the gate green on the moved tree.
    feature_refs: [F1, F4]
    depends_on: [WARP-1702]
    order: 25
  - item: W4
    spec: WARP-1704
    title: >
      The publication pipeline - the public tree is derived, never curated. A repeatable, idempotent
      pipeline produces the public tree from the private repository: the generic documents, the engine,
      the plugin, the templates and packs, the licence and community files in; the private plans and
      specifications, the internal proof corpus, the tracker configuration, and anything naming a
      company, customer, person or internal project out. Proven entirely offline against a scratch
      target with the leak scan and the seeded-internal-artifact negative test, before any public
      repository exists.
    feature_refs: [F2]
    depends_on: [WARP-1703]
    order: 30
  - item: W5
    spec: WARP-1705
    title: >
      veldo.dev - the front door, live before the repository. The site built from the repository's own
      document sources (no duplicated prose): what the method is, the loop, how to install the plugin
      and run the first specification, and the documents themselves. Every entry point the book prints
      resolves to a real page. Standing the site up BEFORE the public repository is the founder's
      declared ordering and becomes a checked precondition of W6 rather than a matter of memory.
    feature_refs: [F3]
    depends_on: [WARP-1704]
    order: 40
  - item: W6
    spec: WARP-1706
    title: >
      The public repository and the 1.0 release. Create the public repository from the pipeline's
      output under Apache-2.0 with the contribution, security and conduct files, and cut a versioned
      release at a tag with the plugin artifact attached. This act is IRREVERSIBLE, so it carries the
      two-key authorization of C5 bound to the digest of exactly the tree being published, and it
      refuses while the site is not live or the pipeline's leak scan is not clean. Proven from the
      other side: a stranger's fresh repository, initialised from the published release alone, runs the
      loop to a green gate.
    feature_refs: [F4]
    depends_on: [WARP-1705]
    order: 50
  - item: W7
    spec: WARP-1707
    title: >
      The printed claims made true and verified at the tag. Build the claim inventory mechanically from
      the manuscript (every sentence asserting something about the reference implementation, with
      chapter and line), resolve each claim against the published release with a verdict and evidence,
      and REFUSE the publish while any claim is unresolved or false. A false claim is fixed by shipping
      the capability or by removing the sentence, never by softening it (NG4). Includes the seeded false
      claim as the anti-vacuity test: the audit must refuse it.
    feature_refs: [F5]
    depends_on: [WARP-1706]
    order: 60
  - item: W8
    spec: WARP-1708
    title: >
      Book production and publish. The mechanical production pass on a manuscript whose claims are
      green: the identifier stamped onto the copyright page, the interior rebuilt and verified against
      the audited digest, the cover finished, the listing prepared, and the book published. This act is
      IRREVERSIBLE and therefore two-keyed (C5), bound to the digest of the exact interior that ships,
      and it structurally cannot run while W6's audit is not clean.
    feature_refs: [F6]
    depends_on: [WARP-1707]
    order: 70
  - item: W9
    spec: WARP-1709
    title: >
      Release and runbook. Make the documents true at the new name and the published state, record the
      capabilities honestly, mark this plan released, and record the launch runbook: the exact
      sequence, the checks, the two-key points and the refusals, so the next release of the method is
      mechanical rather than remembered. The runbook is the artifact that makes this plan repeatable
      instead of a one-off heroic pass.
    feature_refs: [F1, F2, F3, F4, F5, F6]
    depends_on: [WARP-1708]
    order: 80

release:
  milestone: >
    Veldo 1.0, public - one name on every surface with the build refusing a
    reintroduction, the public tree derived by a repeatable pipeline that leaks
    nothing internal, veldo.dev live as the front door and rendered from the
    repository's own documents, a public Apache-2.0 repository and a versioned
    release a stranger can install into a fresh repository and run to a green
    gate, every claim the printed book makes about the reference implementation
    audited true at that tag, the book published, both irreversible acts carried
    on the method's own two keys, and the launch recorded as a runbook so the
    next release is mechanical rather than remembered.
  mode: continuous
  require_all_work_shipped: true
  require_full_regression: true

regression:
  journeys:
    - id: RJ1
      title: >
        No residual old name survives in any shipped surface, and a seeded reintroduction in each
        surface class is refused by name.
      activation: {when: after:WARP-1702}
      suite: naming conformance (surface enumeration and seeded reintroductions)
    - id: RJ2
      title: >
        The publication pipeline is idempotent, its output carries zero internal, company, customer or
        person references and zero secrets, and a seeded internal artifact is provably absent from the
        output.
      activation: {when: after:WARP-1704}
      suite: publication pipeline conformance (offline, scratch target)
    - id: RJ3
      title: >
        A stranger's fresh repository, initialised from the published release alone, lays the method
        down and runs the canonical gate green on a seeded specification.
      activation: {when: after:WARP-1706}
      suite: cold-start adoption conformance (scratch repository)
    - id: RJ4
      title: >
        The claim audit refuses a seeded false claim and refuses to report clean while any claim is
        unresolved, so the publish gate cannot pass on an untrue printed statement.
      activation: {when: after:WARP-1707}
      suite: claim audit conformance (seeded false claim)
    - id: RJ5
      title: >
        The existing gate stays green across every item of this plan, the historical proof corpus still
        validates after the identifier migration, and each irreversible act refuses with either key
        missing.
      activation: {when: after:WARP-1701}
      suite: full canonical gate plus two-key conformance on the launch acts
---

## Intent

The method is finished when a stranger can use it, and a stranger cannot use it while it lives in a
private repository under a working name. This plan is the crossing: it takes what the capability plans
built and makes it a public, licensed, versioned thing called Veldo, standing behind an address that a
printed book will point at for as long as that book exists.

The forcing function is the book. The manuscript prints veldo.dev as a fact in exactly the way a book
has to: permanently, with no chance to edit it later. That single printed line converts a pile of
soft intentions into a hard gate. Either the address resolves and the repository behind it is real and
usable, or the book is wrong in print. There is no soft landing between those two states, and the
founder's judgment is the right one: build it all, then rename, then stand up the site, then publish the
repository, then publish the book.

Two design decisions carry this plan, and both are the opposite of the expedient version. First, the
rename is total and mechanically enforced, including the internal identifiers, because a fresh public
repository with no external adopters is the cheapest moment that decision will ever have and carrying a
second name forward is a debt that never gets paid. Second, the public repository is DERIVED by a
repeatable pipeline rather than curated by hand, because a hand-copied public tree diverges on its first
hurried fix and then the published method and the practiced method are two different methods.

And the plan closes the loop on the method itself: publishing a public repository and publishing a book
are the two most irreversible acts in this entire body of work, so they go through the method's own
two-key rule. If the rules are worth printing in a book, they are worth obeying on the day the book
goes out.

## Context

- Sequencing (the founder's call, 2026-07-24): the capability plans finish first, then rename
  everything to Veldo, then the site, then the public repository, then publish the book. The site comes
  before the repository deliberately: the address is the thing readers type, and a live front door that
  routes to the code is better than a repository with no context around it. This plan declares that
  precondition in C6 so its items cannot be claimed while a capability plan is still unreleased.
- What already helps: the method documents are already fully generic and the gate enforces that (zero
  company, product or project references, ASCII character rules), the plugin already installs the method
  into a foreign repository, and the packs already prove the engine assembles for many tools. The
  distance to a publishable tree is therefore mostly naming, derivation, and licence, not rewriting.
- What is genuinely hard: the identifier rename. The state directory name and the schema identifiers
  appear in every specification, every proof manifest, every template and every pack, so the change is a
  migration, not a substitution. It ships with a proven reverse migration and with the gate green on both
  sides, and the historical proof corpus must still validate afterwards, because evidence that stops
  validating when a name changes was never bound to anything real.
- Why the claim audit is a work item and not a checklist: the manuscript asserts things about the
  reference implementation, and a book cannot be patched. The audit builds the claim inventory
  mechanically from the manuscript, resolves each claim against the published tag with evidence, and
  refuses the publish while anything is unresolved or false. The rule that makes it honest is NG4: a
  false claim is made true by shipping the capability or removed outright, never softened into future
  tense, because softening turns a checkable sentence into an unfalsifiable one and quietly lowers the
  bar the whole method exists to hold.

## Out of scope

- Every capability. This plan adds no organ, no check that changes the loop, and no product feature.
  If the launch reveals a missing capability, that is a specification in the plan that owns it, not a
  quiet addition here.
- The private history. It is not published, not rewritten, and not filtered. The public repository
  starts from a derived tree.
- Any public-side authoring. No change is ever made in the public repository; the pipeline is its only
  writer.
- Marketing. This plan builds the front door and the release, not a campaign, a launch push, or any
  paid promotion.

## Notes

- Order matters and is encoded in the dependencies, not in prose: naming contract, migration, pipeline,
  site, repository, claim audit, book, release. The two irreversible items sit behind everything that
  can still be checked cheaply.
- Put the teeth on the rename check BEFORE running the rename (W1 ships the check, W2 runs the
  migration). A residual-name check written after the sweep tends to be written to pass the sweep.
- The site and the repository render the same document sources (C4). If a page reads better as bespoke
  prose, the document is what improves, not a second copy of it.
- Character rules apply to every file this plan produces, the site included: ASCII hyphen only, no em
  dash, no en dash, no prose double-hyphen.
