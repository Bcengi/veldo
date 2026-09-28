# VELDO-0189 proof: re-running factory setup upgrades an earlier installation's engine in place

## The design as built

**Where it runs.** `veldo factory setup` over a state root that holds a store is VELDO-0171's re-run
(`.veldo/control_factory_setup.py`). After its argument checks and the other read-only checks, and before
any other step writes, the re-run inspects the installed engine and, when it is not the current one,
upgrades it (`.veldo/control_factory_setup_upgrade.py`); the answer's first step is `engine_upgrade`. There
is no other command.

**What it compares.** Only the installation's record, `<install root>/<service>/config/service.json`: its
`closure` (each installed engine file's name and sha256 digest) and `template` digest. The current side is
what the current installer would lay down for this installation's arguments: `control_service.layout`, the
pure half of `install()` (install now calls it and writes exactly what it returns), with `existing=True` so
an installed home is expected. Its `fixed` files are `control_service.closure()`. A digest that differs is
a changed file, a name only the current engine lists is new, a name only the record lists is removed. No
code path per engine version exists.

**What is refused, writing nothing.** Every file in the installed `bin` must equal its recorded digest: an
edited one is `invalid_input:install_root:differs:<path>`, one the record does not name is
`invalid_input:install_root:unrecorded:<path>`. Before the first write the upgrade probes the install
root's filesystem: two empty directories beside `bin` exchanged with renameat2 and RENAME_EXCHANGE through
the C library (ctypes), then removed; a filesystem or C library that cannot is
`unavailable_service:install_root:exchange`.

**How it switches.** The current engine is written complete into `bin.upgrade` beside `bin` at the
installer's modes (entry points 0500, every other module 0400, the directory 0500) and read back against
the current digests; one renameat2 exchange then puts it at `bin` and the previous engine at `bin.upgrade`.
Then, each written to a new file and renamed over the old one: a unit whose rendering from the current
template changed (the authority unit, and VELDO-0171's API unit when it exists), each installation
configuration that lacks a key the current installer writes (with the value `layout` renders for the same
arguments; over 8bc34e94 and 971186ac that is the receiver configuration's `host_trust`, which the current
launch receiver needs), and last the record: its `closure` and `template` and the keys it lacks (`work`,
null, over both older engines). The record is written last, so a record naming the current engine means
every other write is done. Then the restart (AC4), and only after it succeeds is `bin.upgrade`, now the
previous engine, removed.

**Failure and kill.** A failure setup sees after the exchange exchanges the directories back, puts back
every file this run replaced (their previous bytes and modes are held in memory) and refuses by name; a
failed restart (`unavailable_service:authority:upgrade_start`) also restarts the service once on the
previous engine. A re-run finds its state from the files alone: `bin` equal to the record with
`bin.upgrade` beside it is a staged engine left by an interrupted run, removed before starting again; `bin`
equal to the current engine with the record not yet rewritten is an upgrade killed after its switch, whose
writes are finished and whose restart is due; `bin` and the record both current with the step log showing
the exchange and no restart after it is a restart still due.

**The step log.** `<home>/state/engine-upgrade.jsonl`, 0600, one line after each write (each line is a
write point): `begin` (the installed and current engine digests and the files changed, added and
removed), `removed_stage`, `staged`, `exchanged`, `unit` and `configuration` (each path), `record`,
`restart` (its outcome), `switched_back` (its reason), `removed_previous`, `done`. It never carries a key,
a token or a store row. The staged directory is one write point: it is not installed until the exchange,
and a kill anywhere inside it leaves a staged directory the re-run removes.

**What the owner is told (AC4).** Before the first write setup prints one line to its standard error, for
example `Upgrading the installed factory engine: 17 files change, 18 are new, 0 are removed; the authority
service will restart once.` The JSON answer's `engine_upgrade` step names the previous and current engine
digests (sha256 of the canonical JSON of the closure and template) and the files changed, added and
removed, or `already_done`. When the authority unit is active setup restarts it once through
control_service's Systemctl and waits for the service to answer an inspect over its socket; when the
service runs outside its unit (the store lock held, the unit inactive) it restarts nothing, starts no API
unit beside it (the re-run's `api_start` is deferred), and names the command; when nothing runs it starts
nothing and says the next start runs the current engine. A second run over the upgraded host writes
nothing and restarts nothing.

## Rows (scripts/suites/86_veldo_0189_engine_upgrade.py)

Each older engine is the whole `.veldo` of its commit taken with `git archive` and set up by its own setup
module on its own scratch host (state root, install root, unit directory, host trust, clone); a fresh host
is set up by the current setup with the same arguments. The authority unit's ExecStart is run by a user
manager stand-in of the suite's own, whose invocation log the suite owns; the killed setups run in a
process of their own whose systemctl calls reach that stand-in over a UNIX socket.

- `upgrade/from-8bc34e94`, `upgrade/from-971186ac` (AC1): each older host upgraded; its engine directory
  equals the fresh one's in names, bytes and modes and holds control_client_api.py, which the older
  engine lacked; its units, record and every configuration file equal the fresh host's after the
  substitutions and apart from the fields in `fresh-equivalence.json` (the one field: service.json's
  `enrollments`, each host's own binding digest); the record names the current engine; nothing is left
  beside `bin`. The 8bc34e94 host upgrades with nothing running, the 971186ac host with its service
  running through its unit.
- `upgrade/removed-module` (AC1): the fresh host upgraded to a fixture engine (the current one with
  control_keys_custody.py no longer an entry point and absent): that file gone from `bin` and the record,
  named removed, `bin` exactly the fixture's files.
- `upgrade/census` (AC1): every first-parent commit from 8bc34e94 on (of HEAD, and of main when present),
  each distinct `.veldo/control_service.py` parsed: its installer writes `closure` as a digest per file and
  `template` as a digest.
- `upgrade/refused-by-name` (AC1, AC2): an edited engine file, a planted file and a C library whose
  renameat2 fails with EINVAL, each refused by name with nothing written, the store's rows unchanged and
  nothing printed.
- `switch/kill-points` (AC2): over the 8bc34e94 host, with its authority running through its unit, a whole
  upgrade names its write points; for each one a fresh copy of the host is restored, setup is SIGKILLed
  right after that point, the engine directory must equal exactly one engine's digests, the installed
  serve (started through the unit) must answer an inspect, a second run must be accepted and end as AC1
  requires, the service is restarted once across both runs, and a kill after the exchange and before its
  restart must have the second run restart it.
- `switch/failed-restart` (AC2): the stand-in fails the restart once; setup refuses
  `unavailable_service:authority:upgrade_start`, the previous engine is back, the record restored byte for
  byte, the service restarted once more on the previous engine and answering, and the step log records
  the switch back with its reason.
- `kept/owner-data` (AC3): before each older host's upgrade the suite sets its receiver configuration's
  adapters as the owner could; afterwards every file under the key directory, the host trust and the two
  signer files it names, the binding, the token file and every registered account's profile directory is
  byte for byte the same (no account is registered on these hosts: the 8bc34e94 engine has no account
  pool, and an account registered from the suite's copy would bind the store to that copy's code), every
  journal row the store held is unchanged in order and digest, every entity row is unchanged but those
  the API steps' own new journal records wrote (VELDO-0171's api edge enrollment), and every configuration
  value keeps what was there, with the owner-set adapters kept.
- `announce/before-first-write` (AC4): one line on standard error, observed when written, with nothing
  written yet; its words; the `engine_upgrade` step's digests and file lists against the suite's own.
- `restart/rules` (AC4): active (971186ac): one `restart` in the invocation log and a new service process
  answering; outside its unit (the fresh host's installed serve started by hand, then upgraded to the
  fixture engine): nothing started or restarted and the command named; nothing running (8bc34e94): nothing
  started and the next start named.
- `second-run/changes-nothing` (AC4): over the upgraded 971186ac host at rest (authority and API running),
  every file under the state root, install root, unit directory, host trust and binding is the same, the
  journal head unchanged and the invocation log shows no restart, start or stop.
- `install/assets`: the module is scaffolded (not substrate), engine copies identical, and no connection
  beyond loopback was attempted.

## The blocker: store ownership bound to the previous engine's bytes

`switch/kill-points` is red over the 8bc34e94 host, and it is red for a real defect, not a suite fault.
control_store's ownership declarations (`entity_owners`) bind each owned command to one module file and
its sha256 at the moment the service first attaches it. The 8bc34e94 authority service declares
`channel_activation` and `channel_qualification` bound to `bin/control_channel_activation.py`, whose bytes
changed at 7fefdb9a (VELDO-0140). After the upgrade the current engine's channel ingress re-declares them
and the store refuses `ownership_conflict` (control_store's own stated limit: "an upgraded module ... is
refused ownership_conflict at attach, and Release 1 has no re-declaration path (Release 2)"). The service
starts and answers an inspect, but its Telegram channel is refused (`{'available': False, 'refusal':
'ownership_conflict'}`), and VELDO-0171's enrollment of the api edge through the running service, which
reads the authority versions from the channel status, is refused
`invalid_input:state_root:service_running:api_edge_enrollment`. Every kill row's second run shows exactly
this in its detail. Any installation whose service ran on an engine older than 7fefdb9a (the owner's own
host laid down by VELDO-0139, if it predates it) hits it.

Fixing it means rebinding, during the upgrade, the ownership rows that name an installed engine file the
upgrade replaces from the previous digest to the current one (with the switch back rebinding them back):
a store write, which AC3's "the upgrade writes only the engine directory, ..." and the rollback's "the
store ... never changed by the upgrade" rule out, and a control_store change outside this footprint. That
is the owner's decision. With the kill host laid down by the 971186ac engine instead (whose owning modules
equal the current ones), every row of this suite is green and `check_teeth_mutations.py --finding 189`
rejects all nine mutants (`teeth-971186ac-kill-host.txt`), which shows the switch, the kill recovery and
the restart rules work; the 8bc34e94 kill rows stay red until ownership is carried across an upgrade.

## Evidence files

- `fresh-equivalence.json`: the substitutions and the one listed field of AC1's comparison, each with its
  reason; the suite checks the file names exactly the placeholders it substitutes.
- `drive.py`: `python3 -B proof/VELDO-0189/drive.py` drives every finding-189 mutation (mutations.json and
  one diff per mutation); `--red <commit>` runs the current suite against that commit's whole tree.
- `red-at-faa11cfc.json`: the red record at the commit before this change.
- `mutations.json`, `*.diff`: the drive's record.
