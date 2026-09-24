# VELDO-0047 proof: authority service installation, start, stop and absent-service behavior

`.veldo/control_service.py` (engine copy identical) installs one authority instance for the enrolled
workspaces of one domain on this Linux host: a fixed read-only executable (the three entry points,
the architecture validator the launch receiver's recheck runs, and every module these load, derived
at installation), a protected configuration, the enrollment signers this host trusted, one launch
receiver configuration per repository carrying this host's qualified linux-systemd worker profile, and
a systemd user unit rendered from `.veldo/services/veldo-authority.service` (no `[Install]` section,
`Restart=no`). Installation starts nothing; start and stop are explicit operations actions. The
running service takes an exclusive flock on the stable lock file beside the store before it touches
the store or the socket, serves VELDO-0107's socket through `control_client.Authority`, and applies
signed commands to the configured store (generic mutations through `control_store.execute`, claims
through `control_claim.Receiver`), answering with the committed receipt and the store's watermark.
`.veldo/control_client.py` names the service unit and the start procedure in every
AUTHORITY_UNAVAILABLE refusal and stale inspection. Both are installed by `.veldo/init_scaffold.py`.

## Rows

Suite `scripts/suites/66_veldo_0047_authority.py`: 30 rows, 15 assertion rows and 15 rows saying each
region ran to its end. Real enrolled Git clones, OpenSSH signatures, this host's trust file, the
configured SQLite store read back through the suite's own connection, the owner's systemd user
manager, the kernel's lock and socket tables, the real claim client, and a real launch through the
installed receiver whose worker runs in a transient scope of this run's own slice.

| Criterion | Rows |
|-|-|
| AC1 install, start, stop, one instance | authority/installed-fixed-and-protected, authority/one-instance-under-the-lock, authority/key-directory-placement, authority/key-directory-location-before-existence, authority/key-directory-guidance-changes-no-directory, authority/key-directory-relative-refused, authority/receiver-configured-with-host-profile, authority/installed-receiver-launches, authority/installation-refuses-an-underivable-closure |
| AC2 signed commands reach the configured store | authority/mutation-reaches-the-configured-store, authority/wrong-coordinates-or-actor-refused |
| AC3 absent and exited service | authority/absent-service-refuses-by-name, authority/unexpected-exit-waits-for-an-operator |
| Observability and installation | authority/observations, authority/installed-assets |

One recorded run: `observations.json` (30 passed, 0 failed, about 6.5 s), written by `drive.py`.

## The fixed executable

The review found that the receiver copied into `<home>/bin` refused every launch as
`unavailable_service:architecture_validator`: the installed modules were a hand list that left out
the architecture validator, which the receiver's recheck loads from its own directory
(`control_eligibility.ValidatorSnapshot`). `control_service.closure()` now derives the set at
installation, from the engine directory `install()` runs in. Its seeds are the entry points and the
validator files `control_eligibility.VALIDATOR_ROLES` declares (the snapshot loads the validator by
module name, not through a load any source spells, so its files come from the declaration of the
module that loads them). From there it follows every sibling load to a fixed point: the location of
each `spec_from_file_location` call, each call of a loader helper whose location is built from a
parameter (`organ(name)`, `_organ(name, path)`), called directly, bound with `functools.partial` or
through another module's helper assigned to a name (`_load = _runner()._load`), and each import. A
variable names a file only when every binding of it in its module is a plain assignment naming one. A
load naming a module the engine directory lacks, a load site whose module this reading cannot name
for certain, or a loader helper handed on as a value, refuses installation by name
(`invalid_input:closure:absent`, `invalid_input:closure:unresolved`), so the installed program is
never short of a module it loads. Here it installs 45 modules where the hand list had 25. The
scaffold's `REQUIRED_SUBSTRATE` is not a seed: it declares a repository's gate rather than what the snapshot loads, and `init_scaffold.py` is
not laid down in an adopter's tree, where this installer runs too. `supervisor.py`, which the
installer loads for its default unit directory, is now laid down by the scaffolder.

`authority/installed-receiver-launches` drives the reference end to end: the VELDO-0039 Runner from
the installed `bin/control_launch.py` invokes that receiver on the configuration the installer wrote;
the dispatch is accepted and exits 0, and the worker ran as the recorded process in the dispatch's own
scope in the profile's slice with the profile's memory and task caps, then its slot is retired and the
scope is gone. `authority/installed-assets` lays down exactly the `.veldo` modules the scaffolder lists
into a fresh tree, an adopter's, and requires that tree's installer to derive the same closure with
nothing absent and to find its default unit directory.
`authority/installation-refuses-an-underivable-closure` installs from two engine copies, one whose
receiver loads a module by a computed name and one whose receiver loads a module the engine lacks,
and requires each refused by name with nothing laid down.

## The key directory

The installer judges the key directory as named. A relative one is refused as relative before
anything resolves it. Where it is comes before whether it exists: one inside or above a directory
workers write into directly (the home and temporary directories) is refused as `worker_writable`
even when it is absent, and is never given a step to create it there. A directory that exists and is
a link, not this account's or open to anyone else is refused by name. For an absent one outside those
places, the installer prints the one-time root step, which creates only the directories missing below
the first existing ancestor, each named only while it is missing (under the default placement:
`sudo install -d -m 0755 /var/lib/veldo`, then `/var/lib/veldo/keys`, then `sudo install -d -m 0700
-o <user> -g <group> /var/lib/veldo/keys/<service id>`). No printed step changes the mode or owner of
a directory that exists: a directory refused for its mode or owner is answered with a new directory,
not a `chmod` or `chown`. The suite runs the printed steps without `sudo` below a 1777 ancestor of its
own and observes the ancestor unchanged and the key directory accepted. This account can create no
directory outside the home and temporary directories without root, so the suite passes the key
directory and the set of worker directories explicitly for the installation it runs, and asserts the
default placement's refusal and guidance, and the home and temporary refusals, separately.

## Red record

Both records run the CURRENT suite over earlier production code, written by `red.py`, which points the
suite's four production anchors (the service, the client, the scaffolder and the unit template) at the
commit's own copies and checks every other installed module byte-identical to the commit's.

`red-7ed08fb.json`, before the review fixes: the eight new or changed rows fail by assertion, nothing
raised, and every region row passes. The installed receiver refuses the launch as
`unavailable_service:architecture_validator` and no worker runs; the installed executable holds none
of the validator's files; an adopter's tree derives no closure and has no `supervisor.py`; absent key
directories under `/tmp`, the home and a worker directory are refused as absent, the first with the
step `sudo install -d -m 0755 /tmp`; the printed step, run, turns the suite's own 1777 ancestor into
0755; the mode and owner refusals print `chmod` and `chown`; a relative key directory is resolved
against the working directory, where it installs; and both underivable engines install, short of what
their receiver loads.

`red-b738c79.json`, before the service existed: all 15 assertion rows fail by assertion, nothing
raised, and all 15 region rows pass. Substituted there: `control_client.py` and `init_scaffold.py` at
b738c79, and the stand-ins `prefix/control_service.py` and `prefix/veldo-authority.service` (neither
exists there; the stand-in installs, starts and refuses nothing).

## Mutations

38 registered as finding 47 in `scripts/check_teeth_mutations.py`, each diff in `mutations/`, the run
in `mutations.json` (`python3 -B scripts/check_teeth_mutations.py --finding 47 --jobs 4 --diff-dir
proof/VELDO-0047/mutations`): every target row red by assertion with its region completing, baseline
green. The declared falsifiers: `authority-two-schedulers` (AC1, one-instance-under-the-lock),
`authority-callback-success` (AC2, mutation-reaches-the-configured-store) and
`authority-client-starts-missing-service` (AC3, absent-service-refuses-by-name). The review's defect
restored is `authority-closure-listed-by-hand` (installed-fixed-and-protected; it reds the launch and
assets rows too). Every assertion row has at least two mutations: installed-receiver-launches has
`authority-closure-omits-the-validator`, `authority-closure-ignores-loader-helpers` and
`authority-receiver-workspace-omitted`; the key directory rows have existence judged alone, an absent
directory not located, guidance naming the parent or the first existing ancestor, a `chmod` step, a
relative directory made absolute and a relative directory not refused; installed-assets has
`authority-supervisor-not-installed` with the two it had; installation-refuses-an-underivable-closure
has `authority-closure-unresolved-installed` and `authority-closure-absent-installed`.

## Costs

The suite adds about 6.5 s to the gate (about 4 s before these fixes). Finding 47's mutations take
about 75 s with 4 jobs.

## Not done here

Automatic restart and recovery are Release 2; further host profiles, remote inspection and the legacy
status listener are Release 4. Persistence while logged out (lingering) is established separately.
Wiring engine adapters behind the custody wrapper is VELDO-0129: installation writes the adapters it
is given.
