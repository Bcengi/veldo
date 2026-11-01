# VELDO-0159: open items

## A. "Set at" is the moment the route accepted the write, not a read of the record

AC2 has the form show the credential's label, set at and set by after each write. The API refuses every
read-back of a credential (`mcp.credential_read` answers `unauthorized:credential_read_back`, VELDO-0144 AC2),
and the credential write's answer carries `outcome, id, reference, version, seq` but not the record's
`set_at`. So the form shows the label it sent and the route accepted, set by from the passkey session's member
(whom the authority records as `set_by`), and set at as the moment the accepted answer arrived. The
cred/metadata-only row compares all three with the stored credential record: label and set by exactly, set at
within 5 seconds (observed well under one second). Returning `set_at` (and `label`, `set_by`) in the write's
answer would make it exact; that is `engine/.veldo/control_api.py` (its `keep` list), which is outside this
specification's footprint, so it is not done here. A reviewer may judge the approximation acceptable or file it.

## B. Credential metadata lives in the page's memory only

What the field shows (label, set at, set by) and the version the next write needs as `base` are kept in the
`servers` Pinia store for the page's life, never in storage. After a reload the form no longer knows a
credential written earlier: it shows no metadata for it, and a Replace from a fresh credential id slot sends
`base` 0 and is refused `stale_version` beside the action, by name. Nothing is lost or overwritten. The
credential list with its records is VELDO-0131's row ("the catalog table and credential list").

## C. Mutation proof leg

See README "Falsifiers": whether the coordinator's confined leg could run suite 118 (it builds the UI with the
account's nvm Node and drives system Chrome; the confined leg's PATH is /usr/bin:/bin, whose Node 18 is older
than the locked toolchain needs). If it could not, the falsifiers are proven by the driver's own worker
unconfined (`falsifiers.py`, as VELDO-0227 did), and putting `118_veldo_0159_mcp_credential_form` on
`scripts/gate_unconfined.json` is a protected-path change for the owner.

## D. Footprint

Every file touched is inside the declared footprint. `engine/ui/e2e/harness.py` (shared with VELDO-0145 and the
other UI builder) gained the catalog and credential commands and two control routes, additively.
