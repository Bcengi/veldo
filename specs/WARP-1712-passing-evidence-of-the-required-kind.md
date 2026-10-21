---
schema: veldo.spec/v1
id: WARP-1712
title: Required evidence must have the required kind and a recorded passing result
status: blocked
risk: standard
owner: dmitry
human_approval: not_required
lane: standalone
placement: [contracts]
footprint:
  - engine/.veldo/validate.py
  - .veldo/validate.py
  - engine/.veldo/evidence_debt.py
  - .veldo/evidence_debt.py
  - engine/.veldo/init_scaffold.py
  - .veldo/init_scaffold.py
  - .veldo/required-evidence-debt.jsonl
  - engine/.veldo/examples/proof-example.json
  - .veldo/examples/proof-example.json
  - scripts/suites/14_warp_0717_subset_runner.py
  - scripts/suites/106_warp_1712_required_evidence.py
  - scripts/suites/manifest.json
  - scripts/suites/requires.json
  - specs/WARP-1712-passing-evidence-of-the-required-kind.md
  - specs/index.md
  - proof/WARP-1712/**
protected_paths: []
behavior_bearing: true
observability:
  logs: Required-evidence refusals name the missing passing evidence kind and proof path.
  metrics: Corpus comparison records old/new verdict totals and every changed pair by cause.
  error_taxonomy: Wrong kind, absent result, non-passing result, and a check name without a passing record.
acceptance_criteria:
  - id: AC1
    text: Integration requires integration evidence; generic test remains a legacy unit alias only. Existing equivalent-kind aliases remain explicit. A passed check can supply its named kind, but a bare check name cannot.
    falsified_by: Restore test as an integration alias or count a bare check name and the corresponding refusal case fails.
  - id: AC2
    text: An evidence entry or check must itself record a passing outcome. Parent criterion status does not supply a missing outcome. Missing, failed, pending, not-run, unknown and contradictory outcomes cannot satisfy a required kind. A design-review file must record a passing verdict, not merely exist.
    falsified_by: Remove the outcome guard and each absent-result and non-passing-result refusal case fails; accept file existence alone and the failed design review case fails.
  - id: AC3
    text: Before modifying either validator, run the current and proposed required-evidence checks on every matched spec/manifest pair in core's declared proof corpus. Record input digests, totals, skipped inputs, and every changed pair grouped by cause in this proof directory. Core remains read-only and its engine is not reinstalled.
    falsified_by: Omit a matched manifest or alter an input during the measurement and the corpus reconciliation or before/after digest check fails.
  - id: AC4
    text: Veldo's own suite exercises positive controls and refusals in both validator copies. Each new refusal has an assertion that fails against the old implementation. Record focused tests, falsifiers and the canonical gate honestly without rewriting historical proofs to invent passing results.
    falsified_by: Run the refusal matrix against the base validator and it must fail by assertion while the positive controls still pass.
  - id: AC5
    text: Apply the unchanged strict kind/outcome rule to every pair whose spec or proof directory changes in the gate-resolved push range. Unchanged historical failures pass only when listed in the computed debt register. Other contract checks remain enforced.
    falsified_by: Exempt a touched historical pair or refuse an untouched listed pair and the ratchet CLI controls fail.
  - id: AC6
    text: A command produces a sorted committed JSONL register with one spec/proof pair and its strict failure causes per line. The gate requires exact equality with computed failures, rejects passing or fabricated entries and unlisted failures, and refuses additions relative to the push-base register. Initial adoption can register only unchanged historical failures. Later cleanup removes entries incrementally without rewriting old evidence.
    falsified_by: Accept a now-passing entry, a hand-added entry, an omitted failure, a changed cause, or a reintroduced debt and the refusal controls fail.
  - id: AC7
    text: Remeasure core read-only with input digests. The ratchet accepts a push touching none of the 107 historical strict failures and refuses a push touching one of them. Preserve and report the five existing parser errors separately, without claiming that the whole core gate passes.
    falsified_by: Exempt a touched core failure or reject the unchanged registered failures and the measurement assertions fail.
required_evidence: [unit, integration]
rollback: Revert the implementation commits; retain the measurement as historical evidence.
---

## Intent and design

The 2026-10-20 core review found that required integration evidence accepts generic unit tests,
bare check names, and failed or unexecuted entries. The collector must filter on both kind and
outcome. The proof contract is the field-based PROOF_REQ/check_json implementation, not a JSON
Schema file. Existing examples use criterion status=passed and checks result=pass; current
writers also emit checks status=passed. Evidence needs its own recorded outcome: it never
inherits a criterion's status. Accept status=passed and result=pass or passed, and reject a
record if any supplied outcome field disagrees. No text matching, case folding or prose inference.

The check schema names its kind with name; it counts only with a recorded passing outcome.
Evidence names its kind with type. The deliberate alias table preserves equivalent spellings,
including journeys/journey/e2e, and removes test from integration. Design reviews retain their
separate artifact route but must contain verdict=pass or pass_with_notes.

The impact report uses a proposed validator held under this proof directory before changing the
production validator. It calls the actual old and proposed check on the same files, using the
validator's corpus membership rule and spec_id join. Cause groups can overlap; totals distinguish
unique changed pairs from group memberships. A result is absent at the entry level even when a
parent criterion says passed. Existing proof records are immutable, not migration targets.

## Scope and review

Normal use is required-evidence validation of checked-in proof manifests. Review covers exact-kind
and outcome matching, positive controls, corpus completeness, and fidelity of the impact report.
Artifact execution, cryptographic authenticity, and the separate control_proof observation protocol
are outside this change. Core is read-only. No install, push, merge, branch switch or other worktree
change is authorized. WARP-1712 follows the user's explicit numbering instruction over the repository's
general VELDO naming convention. This spec entered ready on the user's build instruction.

## Round 2 owner decision and ratchet

Owner decision: Telegram 35399, "agree", authorizes the strict rule for every ticket a
push touches from now on, with unchanged historical failures as nonblocking debt, paid
down over time, never by a bulk rewrite. This supersedes round 1's whole-corpus enforcement
scope, not its strict predicate, refusals, or falsifiers. Round 2 starts ready on this instruction.

The register is repository-local `.veldo/required-evidence-debt.jsonl`, not an engine template.
`python3 .veldo/validate.py evidence-debt` emits its canonical contents to stdout; it does not
write the register. Each line contains relative spec/proof paths and deterministic strict
failure diagnostics. The gate compares bytes with the same computation. Existing entries
are additionally bounded by the register at the resolved push base, so recomputing the
file cannot silently add a new debt. With no register at that base, adoption is restricted
to unchanged pairs. Once adopted, retain an empty register after the last entry is removed;
deleting it must not reset adoption and allow debt to grow again. Without a resolvable range,
no debt exemption is granted. A spec change
or any file change beneath its proof directory activates strict enforcement, including a
design-verdict change. Round 3 resolves the range against trunk as specified below.

## Round 1 validation and landing blocker

The implementation and targeted proof are complete. The driver passes 213 cases, all 69 new
refusal assertions fail on the old code, and five targeted mutants are rejected. The measured
core impact is 107 changed verdicts among 173 matched pairs, with five unchanged parser errors.

Landing is blocked: the strict check refuses 111 required-kind claims across 79 historical
Veldo proofs. Three assertions in the canonical confined unit run require that historical corpus
to remain accepted (7,933 passed, 3 failed). The unconfined leg also stopped in the unchanged
VELDO-0208 trace test with an incomplete file-read trace. The remaining gate run was interrupted
while integration was running after these blockers were established; the capture command exited
130 and no final verifier exit was recorded. No complete gate result or gate pass is claimed.
Historical evidence was not rewritten, requirements were not waived,
and no assertion was weakened to force green. See proof/WARP-1712/README.md and manifest.json.

## Round 2 validation and remaining blocker

The ratchet and its delivery fixes are implemented at `414e24cc`. The generated Veldo
register contains 79 unchanged historical pairs, with no historical proof rewritten.
Final focused checks report 234 passed, zero failed; all 69 old-code refusal assertions
and all 11 strict-rule/ratchet mutants are rejected. The Git subprocess boundary and
fresh install/reinstall gates pass. Core still has 107 strict failures: the untouched
registered set has zero ratchet errors, and 214 individual spec/proof touches refuse.
The five existing core pair parser errors remain separately reported errors.

The canonical attempt at `3ef567d5` completed confined unit with 7,953 passed and one
Git-boundary source-check failure, then unconfined unit with 871 passed and zero failed.
Round 1's three historical-corpus failures and its incomplete-trace exception did not
recur. The source binding was corrected in `414e24cc`; that commit also closes the
empty-register reset edge and adds multi-commit range coverage. Its focused checks pass.
The gate attempt was stopped during integration before those final corrections. No
complete final-tree gate result is claimed: full canonical validation, including the
remaining integration and later stages, is the outstanding landing blocker. No independent
review, push, merge, or shipped status is claimed. See the round 2 command record and README.

## Round 3 independent review corrections

The owner's round 3 instruction authorizes these corrections to R1-R5 and their falsifiers.
A base-register pair can disappear only after the same spec and proof paths still pair by
id, retain every base-required kind, and pass the strict check. Renaming, moving, deleting,
relabeling, or dropping requirements cannot pay down debt. Touched failing pairs refuse.
The register bound and touched set use the same trunk merge base: an explicit policy BASE
when provided, otherwise origin/HEAD or origin/main. A feature branch's upstream and an
arbitrary commit window cannot grant an exemption. Trunk-only changes after divergence
are excluded. Paths are relative to the VELDO root, including a root vendored in a host repo.
A supplied exit_code must be an integer zero, in addition to an explicit passing outcome;
expected_exit cannot turn a nonzero execution into passing required evidence. Legacy result
spellings remain supported. Each review finding gets a control that fails on round 2 code.
Core is remeasured read-only, then the documented canonical gate runs to completion and its
actual result is recorded, without claiming green from focused checks.
