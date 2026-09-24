# VELDO-0047 proof: authority service installation, start, stop and absent-service behavior

`.veldo/control_service.py` (engine copy identical) installs one authority instance for the enrolled
workspaces of one domain on this Linux host: a fixed read-only executable (the service and the
closure it and the launch receiver load), a protected configuration, the enrollment signers this
host trusted, one launch receiver configuration per repository carrying this host's qualified
linux-systemd worker profile, and a systemd user unit rendered from
`.veldo/services/veldo-authority.service` (no `[Install]` section, `Restart=no`). Installation starts
nothing; start and stop are explicit operations actions. The running service takes an exclusive
flock on the stable lock file beside the store before it touches the store or the socket, serves
VELDO-0107's socket through `control_client.Authority`, and applies signed commands to the
configured store (generic mutations through `control_store.execute`, claims through
`control_claim.Receiver`), answering with the committed receipt and the store's watermark.
`.veldo/control_client.py` now names the service unit and the start procedure in every
AUTHORITY_UNAVAILABLE refusal and stale inspection. Both are installed by `.veldo/init_scaffold.py`.

## Rows

Suite `scripts/suites/66_veldo_0047_authority.py`: 20 rows, 10 assertion rows and 10 rows saying each
region ran to its end. Real enrolled Git clones, OpenSSH signatures, this host's trust file, the
configured SQLite store read back through the suite's own connection, the owner's systemd user
manager, the kernel's lock and socket tables and the real claim client.

| Criterion | Rows |
|-|-|
| AC1 install, start, stop, one instance | authority/installed-fixed-and-protected, authority/one-instance-under-the-lock, authority/key-directory-placement, authority/receiver-configured-with-host-profile |
| AC2 signed commands reach the configured store | authority/mutation-reaches-the-configured-store, authority/wrong-coordinates-or-actor-refused |
| AC3 absent and exited service | authority/absent-service-refuses-by-name, authority/unexpected-exit-waits-for-an-operator |
| Observability and installation | authority/observations, authority/installed-assets |

One recorded run: `observations.json` (20 passed, 0 failed, about 4 s), written by `drive.py`.

## The key directory

The installer refuses a key directory that is absent, a link, not this account's, open to anyone
else, or inside or above a directory workers write into directly (the home and temporary
directories), each by name, and for an absent one it prints the exact one-time root step
(`sudo install -d ...` under `/var/lib/veldo/keys`). This account can create no directory outside the
home and temporary directories without root, so the suite passes the key directory and the set of
worker directories explicitly for the installation it runs, and asserts the default placement's
refusal and guidance, and the home and temporary refusals, separately.

## Red record

`red-b738c79.json`, written by `red.py`: the CURRENT suite over the pre-change code. Substituted:
`control_client.py` and `init_scaffold.py` at b738c79, and the stand-ins `prefix/control_service.py`
and `prefix/veldo-authority.service` (neither exists there; the stand-in installs, starts and refuses
nothing). Every other installed module is identical to b738c79. All 10 assertion rows fail by
assertion, nothing raised, and all 10 region rows pass.

## Mutations

24 registered as finding 47 in `scripts/check_teeth_mutations.py`, each diff in `mutations/`, the run
in `mutations.json` (`python3 -B scripts/check_teeth_mutations.py --finding 47 --jobs 4 --diff-dir
proof/VELDO-0047/mutations`): every target row red by assertion with its region completing, baseline
green. The declared falsifiers: `authority-two-schedulers` (AC1, one-instance-under-the-lock),
`authority-callback-success` (AC2, mutation-reaches-the-configured-store) and
`authority-client-starts-missing-service` (AC3, absent-service-refuses-by-name). Every assertion row has
at least one further, different mutation.

## Costs

The suite adds about 4 s to the gate. Finding 47's mutations take about 36 s with 4 jobs.

## Not done here

Automatic restart and recovery are Release 2; further host profiles, remote inspection and the legacy
status listener are Release 4. Persistence while logged out (lingering) is established separately.
Wiring engine adapters behind the custody wrapper is VELDO-0129: installation writes the adapters it
is given.
