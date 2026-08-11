# What Is in the Public Repository, and What Is Not

*Veldo was open sourced out of the private repository it was built in. This document says what a pack gives you, what did not travel out of that repository, and why the method is whole without any of it. The order is deliberate: what an adopter gets is the subject, and the removals are footnotes to it.*

*Version 1.0, 2026-08-11*

## What you get

An empty repository plus one pack is a working Veldo installation. Every part of the loop the method describes ships:

- **The gate.** `scripts/verify.sh`, the canonical fail-closed catalog. Every validation slot is declared `required`, `na` with its reason, or `waived` with an expiry; a blank slot makes the gate red and a waiver that passes its date makes it red.
- **The contract system.** `.veldo/validate.py` and its siblings structurally validate a spec, a plan, a proof manifest and a verdict, and enforce that declared evidence kinds appear in the proof and that spec criteria and proof criteria are the same set. Worked examples of each artifact ship under `.veldo/examples/`, so the format is legible without reading anyone's real work.
- **The proof and review layer.** The proof manifest contract, the verdict contract, the verdict corpus reader, and the shape-fit review dimension.
- **The policy guard.** `.veldo/policy_check.py` with a git pre-push hook: a recorded, unresolved blocking finding stops the push, and a change touching a protected path needs a separate human approval whose approver is not the proof producer.
- **The plan layer.** Product Plans as a dependency graph with a release gate, their validator, and the plan and starter templates.
- **The architecture contract.** `.veldo/arch.py`, `.veldo/shape_gate.py`, the foundational decision record and its adversarial review seam, and the assumption tripwires. Adoption safe: a repository with no contract is unaffected and every check stands down by name.
- **The fleet and the CLI.** `.veldo/fleet.py`, `work.py`, `lander.py`, `governor.py`, `dispatch.py` and `bin/veldo` travel with the engine in every pack.
- **Seven packs.** Claude Code, Cursor, Codex CLI, GitHub Copilot, Antigravity CLI, OpenCode and Aider, each composed byte-identical from the one engine, with the same enforcement on every tool.
- **The method itself.** Every generic document under `docs/`, this one included, plus the eleven role training documents.

**This is proven, not promised.** Build the public tree, which composes each of the seven packs with the base, then run the scaffolder from the composed Claude pack into an empty git repository: **49 files laid, 0 skipped**, and that repository's own `bash scripts/verify.sh` prints `GATE: GREEN`. Nothing configured, no network, no access to any private repository. Re-verified 2026-08-11. A repository with no product code in it yet declares most catalog slots `na` with their reasons on record; what runs there and passes is the contract validator, the shape gate and the secret scan. That is the substrate standing up honestly, which is what day one needs.

## Why anything is missing at all

Veldo was built by running Veldo on a real company's real product work, and that is the reason to trust it: every mechanism here exists because a build failed without it. It is also the reason the source tree cannot be published byte for byte. The specifications, plans and proof bundles that record that work name unreleased products, a supplier relationship, and colleagues who did not choose to be published.

Two different things follow, and a reader deserves to know which is which. One is information that was deliberately removed. The other is machinery that was never in a pack in the first place, because it is wired to one company's systems.

## Removal one: private information

The public tree is **derived, never curated**. The publication script applies include globs to the tracked file list, and a path matching no rule is absent. Default deny is the safe direction to fail in: when the development repository grows a directory nobody remembered to think about, the new directory is missing from the public tree rather than published by an exclusion list that was never updated. A curated copy would be a judgement repeated by hand every release, and judgement degrades with familiarity.

What ships is `engine/`, `packs/`, the generic documents and the root files. Of 1,319 tracked files in the development repository, 410 are selected, and the seven packs are then composed with the base. What is absent:

- **Our own paperwork.** The dogfooding corpus: 201 specification files, 18 plans and 445 proof and verdict files at the 2026-08-11 revision. They are receipts of real work on unreleased products, and a release is not the place for them.
- **Internal provenance.** 37 design and research notes under `docs/design/` and `docs/research/`, which carry the rejected options, the customer context, and the reasoning behind decisions.
- **The rendered PDFs and the project site**, which are derived artifacts of the documents that do ship.
- **The development repository's own tooling**: the publication and migration scripts, the name list they read, the self-test suite, and the harness that drives all seven packs. It describes our repository, not yours.
- **Four modules of an unfinished plan**, held out by name and with the reason recorded in the publication script: they are gate green with real teeth, and their independent review has not run. Adding unreviewed capability at the last moment would make the release something other than what was reviewed.

**One list of names, read by two mechanisms.** The names that must not appear are declared once, in `.veldo/private_names.txt`, and both the gate's genericity sweep over the documents and the publication leak scan read that one file. Two lists would disagree the first time one was updated, and the disagreement would be silent in the direction that matters: the gate green, the published tree carrying the name. The scan reads the **produced tree**, never the source, because the copy is made by different code than a sweep of the source reads. And it **refuses rather than cleans**: on a finding it fails and writes nothing further, because a cleaner would make the output depend on a substitution nobody reviewed.

**If the full source ever moves out**, a separate one-time migration exists for that day. It copies every tracked file except a declared deny list, substitutes 14 private names case preserving from a declarative map (each unreleased project, vendor and person becomes its generic role word), rewrites absolute home paths to a placeholder, refuses to finish while any private name survives anywhere in the produced tree, and then **runs the gate inside that tree**. The last step is the one that makes the rest trustworthy: a scrub verified only by "no forbidden words remain" is verified by absence, and absence is exactly what a broken repository also looks like. It earned itself immediately. Writing redacted text creates a new file at the default mode, so every executable bit was gone and eleven checks failed at once: every pack's pre-push hook, the guard and the CLI. Git silently skips a hook it cannot execute, so that tree would have shipped looking gated and been fail-open, and no word search would ever have said so.

**The company's own already-public product names are kept on purpose.** They sit on a separate list and are substituted only behind an optional flag that the migration does not use by default. A receipt that names nothing real is worth less than one that names something: the dogfooding records are evidence of work that actually shipped, and a falsified receipt is worth nothing. What must not travel is what was never public, and everyone who did not choose to be published.

## Removal two: machinery that is repo-only

The second reason is not a removal at all. Some machinery only makes sense in the repository that develops Veldo, and it is marked as such in the one place documentation defers to. `engine/.veldo/capabilities.yaml`, laid into your repository as `.veldo/capabilities.yaml`, is the machine-readable truth about what a release implements. 31 of its entries carry `scope: repo-only` as of 2026-08-11, and that file, not this sentence, is the authority.

The marking is gate-enforced in the direction that protects an adopter: every entry NOT marked `scope: repo-only` must have its home resolve in what installing a pack actually lays, and the check is proven able to fail by un-marking one. So an unmarked entry is a promise the gate keeps, and a marked one is a promise nobody made.

By group, what is repo-only:

- **The tracker round trip (22 entries).** The live Jira Cloud and Confluence Cloud adapters, the status mirror, the epic mirror, the intake modules, the inbound bridge and the mirror runner. What ships is the vendor-neutral routing contract and its enforcement, so an adopter gets routing today, not the round trip. `veldo mirror` and `veldo jira init` are listed as subcommands in every pack and each exits 2 with "repo-only and is not present here"; there is no flag or config key that turns them on. The reason is not secrecy. This code is wired to one company's tracker project, its status map and its credentials, and a shipped copy would be a configuration nobody could satisfy. [`tracker-operator-guide.md`](tracker-operator-guide.md) states it in its first section and repeats it in its last.
- **The pack system (4 entries).** The manifest that declares our seven packs, the drift check and the conformance harness that drives each one. They enumerate our packs, not yours.
- **Five others.** A staged rollout controller with its health gates, the live container-backed ephemeral environment, the plan budget governor, the lessons store, and the init scaffolder.

One honest note on the label. `scope: repo-only` means the manifest makes no promise that an adopter has that capability. It does not always mean the file is absent everywhere: two of the 31 name files a pack does carry, the scaffolder your own init runs and the composition function in the engine, and what is repo-only about those is the harness around them.

## What none of this is

It is not a crippled release. Nothing was held back because it does not work, nothing important sits behind a paywall or a private fork, and the enforcement invariant is identical on every one of the seven tools. The two things that are absent are our paperwork and our wiring, and neither is a component of the method. The method is the loop and the machinery that enforces it, and both ship whole: state the intent, let the machine build, require proof, review with fresh context, merge when green.

The thing our removed corpus would have given you is a set of worked examples. It is replaced by better ones, in the sense that they are yours to read and modify: the artifact examples under `.veldo/examples/`, the spec and plan templates, and a starter plan that is valid on the day it lands.

## Where to check this

The authority on what ships is the capability manifest, `engine/.veldo/capabilities.yaml`. Prose defers to it, including this document: a claim here that contradicts a status there is a documentation bug, and the right fix is to correct the prose.

The publication script, the migration script, the name list and the self-test suite are themselves part of the development repository. Some paths named above are therefore references to where a mechanism lives rather than files you can open in this copy, which is the same split this document describes, applied to itself.

## Document History

| Version | Date | Changes |
|-|-|-|
| 1.0 | 2026-08-11 | Initial document. States what a pack gives an adopter and proves it with a real init from a composed pack (49 files laid, that repository's own gate green), then the two reasons something is absent from the public repository: private information removed by a derived, default-deny publication and a declarative redaction map that keeps the company's own already-public product names on purpose, and machinery marked `scope: repo-only` in the capability manifest because it is wired to one company's systems. |
