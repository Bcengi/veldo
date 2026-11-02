# Sign in and add a passkey

Route `/sign-in`, outside the shell. Before sign-in nothing else exists: no navigation, no data. On
desktop a cobalt field carries the wordmark and what the factory UI is for, beside the panel; on a phone
the field is a band above it.

| Step | API routes |
|---|---|
| Sign in | `auth.challenge`, then `auth.sign_in` with the passkey assertion |
| Add a passkey | `auth.registration_begin` (label), `navigator.credentials.create`, `auth.registration_credential`, a possession assertion over `possession_challenge` limited to the new credential, `auth.registration_possession` |
| Compare at the host | shows the pending label and fingerprint exactly as `veldo factory passkey` shows them |
| Sign in with it | `auth.challenge`, `auth.sign_in`; refused `unauthenticated:unknown_credential` until the host approves |

States: start, enroll form, pending (fingerprint), refusal (beside the action). The fingerprint is set
in mono at `--text-xl`, four groups to a row, so it can be read aloud group by group against
`veldo factory passkey`.
