# VELDO-0159: open items

## A. "Set at" is the stored record's set at (resolved by review-2026-11-01)

Round 1 showed set at as the moment the browser received the credential write's answer. The independent review
(`review-2026-11-01.md`, finding F1) held that AC2 requires the credential record's own set at, and confirmed a
footprint addition of exactly `engine/.veldo/control_credential.py`, `.veldo/control_credential.py`,
`engine/.veldo/control_api.py` and `.veldo/control_api.py` for that purpose, and nothing more. Fix round 2 uses
exactly those four files: the credential authority answers with the stored record's `set_at` and `set_by`, read
from the journal entry the command committed, so a replayed write answers with the ORIGINAL record's (never a new
clock reading); the API's `keep` list passes both through, never the value; `CredentialField.vue` shows them for
set, replace and delete; `cred/metadata-only` requires exact equality with the record. The `.veldo/` copies are
byte-identical to `engine/.veldo/`. Proof: README "Fix round 2".

## B. Credential metadata lives in the page's memory only

What the field shows (label, set at, set by) and the version the next write needs as `base` are kept in the
`servers` Pinia store for the page's life, never in storage. After a reload the form no longer knows a
credential written earlier: it shows no metadata for it, and a Replace from a fresh credential id slot sends
`base` 0 and is refused `stale_version` beside the action, by name. Nothing is lost or overwritten. The
credential list with its records is VELDO-0131's row ("the catalog table and credential list").

## C. Mutation proof leg (owner)

The coordinator refused every finding-159 case (round 1 two, round 2 three: `r2-coordinator-159.log`) as invalid baselines (`coordinator-159.log`): its confined leg runs
the suite from a snapshot that has no `engine/ui/node_modules` (untracked) and a PATH of /usr/bin:/bin (Node 18,
older than the locked toolchain needs), and suite 118 also starts system Chrome. The falsifiers are proven by the
driver's own worker unconfined instead (`falsifiers.py`, `falsifiers.json`: 3 of 3 since round 2), as VELDO-0227 did. For the
coordinator to prove them itself, the owner would add `118_veldo_0159_mcp_credential_form` to
`scripts/gate_unconfined.json` (protected), and the gate host needs `npm ci` in engine/ui. Not done here.

## D. Footprint

Every file touched is inside the declared footprint, plus the four authority files the review confirmed (A). `engine/ui/e2e/harness.py` (shared with VELDO-0145 and the
other UI builder) gained the catalog and credential commands and two control routes, additively.
