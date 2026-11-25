# Round 2 host-pending controls: fresh pc2 evidence

Date: 2026-11-25. Both controls are now **green**, original and split.

Original authority: `369d6d04e56b6bf6a771814e61447edba803e39d`.
Split authority: `80cbb6c7042c181eb0cdcd6ab4ee21c127e10e1f`.
Each ran through an exclusive pc2 remote-run slot using explicit
`/usr/bin/python3 -I -S`, one worker at a time, with fresh baseline, no-op
and mutant execution. No pc1 workload was started.

| Control | Original stage seconds | Split stage seconds | Named kill |
| --- | --- | --- | --- |
| pool-shared-profile | 147.623 | 147.489 | VELDO-0160 pool/per-account-isolation |
| role127-resource-grant-omitted | 226.815 | 206.596 | VELDO-0127 wire/resources |

All four stages passed, each executing and rejecting one mutant with zero reuse,
invalid results or surviving workers. Every baseline/no-op observation is true.
Named kills agree between original and split. All common observations agree in
all three modes. The split parents omit only their previously extracted rows:
`VELDO-0160 install/assets` and `VELDO-0127 review/init-bound`, respectively.
No new extraction or assertion change was made by this evidence run.

The receipts preserve `kill_by: unproven`, the existing conservative
classification for suites with clock sites. A green bounded mutation result
does not upgrade that timing classification or constitute a full-gate result.

Both runs report distro Python 3.14.4, system Node v22.22.1 and npm 9.2.0.
The account-home Codex 0.166.0 binary hashes to
`b8a11fedf24b2dfb59a70c9e52b030f9a508dcd49cd2dd0d41956f4c785156b8`;
Claude 2.1.317 hashes to
`eb224419e344575faa4a1f39b290b649425a10cd5ee2ef1d003480cd9ae57eb0`.
Both private fixture allocations were removed. The wrapper returned zero and
fetched receipts, raw worker output and environment metadata for each authority.

`controls.py` is the exact driver supplied as the remote command. It uses the
existing private fixture parent and normal registered mutation driver. No PATH
injection, observer-output patch, runtime installation, credential transfer,
source modification, confinement widening or assertion replacement was needed.
`summarize.py` performs only receipt comparison; `summary.json` preserves the
per-mode observations, named kills, outcomes and evidence hashes.
