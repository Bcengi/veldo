# VELDO-0124 open items, 2026-10-29 round 3

Status: REMAINING. The acceptance text is unchanged. AC1 and AC3 still require
real Claude Code observations on the selected Mac. No qualification record or
operational activation was issued by this round.

Round 3 addresses fixcheck N1 and N2 only. The forged qualification cases now
require the intended ValueError cause for evidence outside protected storage,
a complete row map with exactly one blocked row, a wrong schema, non-native kind
and a relative path. Five isolated mutants each remove one corresponding check.
The round 2 fixture commit identity is neutral, and its README corrects the
earlier blocked-row coverage claim. Results are in `round3-2026-10-29/README.md`.
The owner action below is unchanged and was not attempted in this round.
Native observations below refer to round 2 and earlier.

All fifteen local mutants were rejected, including all five new verification
check mutants on `AC1/forged-qualification`. Restored suite 103 passed 55 checks
and suite 104 passed 33 checks, both with zero failures and partial exit 2. The
final logs and red/green receipt are complete. These scoped diagnostics do not
qualify the Mac or close the existing acceptance blockers.

## Owner action: Claude Code login through VELDO-0147

The existing real Claude Code natural, cooperative and deadline rows remain
blocked. The new signal ignoring child row is prepared and also blocked. On
`dmitrys-mini.lan`, macOS 26.5.1, Claude Code 2.1.303 reports loggedIn=false and
authMethod=none inside the actual Keychain denying Seatbelt policy.

To unblock these rows, the owner must provide a working Claude account login
inside that exact sandbox. One concrete route is to create a long lived token
on the Mac with `claude setup-token`, using the intended account, and have
VELDO-0147 deliver it locally to the accepted run. Token creation alone is
insufficient: VELDO-0147 must implement and qualify the trusted account scoped
credential delivery path because the current control layer strips
`CLAUDE_CODE_OAUTH_TOKEN` and the profile rejects it as a settings source.
The token must remain on the Mac, outside repository and proof files. Do not
copy it into a prompt, Linux authority fixture, log or commit.

After that delivery works, verify authenticated status inside Seatbelt, bind
the revised adapter configuration and binary identities, and rerun the real
natural, cooperative, deadline and signal ignoring child probes for Claude.
Run the complete required observation matrix against one final profile for both
engines before publishing qualification evidence. The previous Codex rows and
this round's child row use different profile digests and cannot simply be
combined into an eligibility record. An independent review and the owner's
later batch gate are still required. This is an acceptance blocker, not a
waiver or a change to the spec.

## Qualification evidence trust boundary

Each required row now references an absolute file path and its SHA256 digest.
The resolved file must be inside the profile's protected storage. Its native
observation document must bind the exact profile digest, host and OS version
and report that row passed. Missing files, edited bytes, substituted bindings,
malformed references and handwritten truthy row labels refuse before launch.
The profile digest includes both engine identities and configuration digests.

The trusted operator still publishes these observation files. A digest proves
integrity and binding, not that an operator actually performed an experiment.
This change does not claim a cryptographic attestation of physical observation
or protection from an authority operator who replaces both evidence and record.
The requested evidence verification closes the unchecked reference defect.

## Other scope and accounting notes

Network restriction and the broader launchd helper escape matrix remain Release
2 work. The Keychain denial remains in place. Codex's `SSL_CERT_FILE` setting is
part of the accepted adapter configuration digest, as recorded by the authority
coordinator.

The real Codex child row verifies lifecycle slot release after OS exit and an
empty coalition. Its interrupted stream has no final token receipt. The signed
control store retains the invocation as unknown with observed wall time and
one invocation charged. Lifecycle slot release is not authority reservation
retirement or a claim of final provider accounting.
