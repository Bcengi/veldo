---
schema: veldo.spec/v1
id: VELDO-0189
title: Re-running factory setup upgrades any earlier installation's engine to the current one in place, keeping every store, key, enrollment and setting, switching in one step so a failure leaves a runnable engine, and a second run changes nothing
status: ready
risk: critical
owner: dmitry
human_approval: required
lane: planned
plan: PLAN-0019
work: W149
plan_revision: 4
depends_on: [VELDO-0047, VELDO-0139]
placement: [engine, distribution]
protected_paths: []
footprint:
  - "scripts/suites/support/setup_runtime.py"
  - "engine/.veldo/control_factory_setup*.py"
  - ".veldo/control_factory_setup*.py"
  - "engine/.veldo/control_service.py"
  - ".veldo/control_service.py"
  - "engine/.veldo/control_store.py"
  - ".veldo/control_store.py"
  - "engine/.veldo/services/*"
  - ".veldo/services/*"
  - "engine/.veldo/init_scaffold.py"
  - ".veldo/init_scaffold.py"
  - "bin/veldo"
  - "engine/bin/veldo"
  - "scripts/suites/*_veldo_0189_*.py"
  - "scripts/suites/73_veldo_0139_factory_setup.py"
  - "scripts/suites/85_veldo_0171_setup_api.py"
  - "scripts/suites/86_veldo_0186_setup_assets.py"
  - "scripts/suites/86_veldo_0168_text.py"
  - "scripts/suites/manifest.json"
  - "scripts/suites/requires.json"
  - "scripts/check_teeth_mutations.py"
  - "specs/VELDO-0189-setup-upgrades-an-earlier-installation.md"
  - "specs/index.md"
  - "proof/VELDO-0189/*"
behavior_bearing: true
observability:
  logs: >
    Record each engine upgrade with the installed and current engine digests, the files it changed,
    added and removed, the switch, the record and unit writes, the restart and its outcome, and a
    switch back with its reason; never a key, token or store row.
  metrics: >
    Count setup runs that upgraded, found the engine already current, switched back, or refused an
    installed engine by name.
  traces: >
    Join each upgrade to the setup run, the installation record it read and the one it wrote, and the
    restart that followed.
  error_taxonomy: >
    Distinguish an installed engine file whose bytes are not the ones the installation records
    (invalid_input:install_root:differs:<path>), a file in the engine directory the record does not name
    (invalid_input:install_root:unrecorded:<path>), an install root whose filesystem cannot exchange two
    directories in one step (unavailable_service:install_root:exchange), and a restarted service that does
    not come up on the new engine, after which setup has switched back (unavailable_service:authority:upgrade_start).
acceptance_criteria:
  - id: AC1
    text: >
      Claim: Running factory setup again with the same arguments over an installation laid down by any
      earlier engine replaces the installed engine with the current one, and the host ends as a fresh
      installation of the current engine would be, apart from the owner's data, keys and enrollments, which
      are kept. Set and completeness: The re-run, after VELDO-0171 AC4's argument checks and before any other
      step, reads the installation record (`<install root>/<service>/config/service.json`, VELDO-0047's
      installer) and compares its `closure` and `runtime_assets` together (each installed engine file's name and sha256 digest) and
      `template` digest with the current engine's (control_service.closure() and runtime_assets(), with any file a later
      specification records the same way): the files whose digest differs are changed, the names only the
      current engine lists are new, and the names only the record lists are removed. Before it writes, every
      file in the installed `bin` directory must equal its recorded digest, and a file that differs or that
      the record does not name is refused by name, writing nothing. It works only from the record, which
      every installation since VELDO-0139 writes, so it has no code path per engine version. It writes the
      changed and new files, leaves out the removed ones, rewrites the record's `closure`, `runtime_assets` and `template`, adds
      a key the current installer writes that the record lacks with the value a fresh installation would
      write for the same arguments, and renders the authority unit and VELDO-0171's API unit from the current
      templates. The suite lays down two older engines, each as its own scratch host with its own state
      root, install root, unit directory, host trust and clone: the whole `.veldo` of commit 8bc34e94 (the
      merge that landed VELDO-0139) and of commit 971186ac (the landing of VELDO-0155 and VELDO-0156), each
      taken with `git archive` and set up by its own setup module, and upgrades each with the current setup;
      a fresh scratch host is set up by the current setup with the same arguments. The installed engine
      directories, including runtime asset subdirectories, must be equal byte for byte in names, bytes and
      installer modes. The upgrade pins the qualified Claude Code version under
      `<state root>/engines/claude_code/<version>` and writes `host/engines.json`, each only when absent,
      as a fresh installation would. These pinned bytes and modes and the engines record join the equality
      set; the unit files, the record and every
      configuration file must be equal after each host's scratch root is substituted, apart from fields
      listed in proof/VELDO-0189/fresh-equivalence.json, each with its reason (a key id, an enrollment digest,
      the store and domain identities, the host identity), and any other difference fails the row. A third
      row upgrades a current installation to a fixture engine derived from the current one without one module
      it installs, and requires that file gone. A census row reads every first-parent commit of main from
      8bc34e94 on and requires each one's installer to write the `closure` and `template` keys the upgrade
      reads. Falsifier: Write only the files whose names the installed record already lists, and the 8bc34e94
      row must fail on the upgraded engine directory lacking control_client_api.py.
    falsified_by: >
      Write only the files whose names the installed record already lists, and the 8bc34e94 row must fail
      on the upgraded engine directory lacking control_client_api.py.
  - id: AC2
    text: >
      Claim: At every point of an upgrade a complete engine, the previous one or the current one, is
      installed, so an upgrade that fails or is killed leaves a factory that runs, and running setup again
      finishes it. Set and completeness: Before its first write the upgrade checks that the install root's
      filesystem exchanges two directories in one step (renameat2 with RENAME_EXCHANGE through the C
      library, probed on two empty directories it then removes), refusing by name otherwise. It writes the
      current engine complete into a new directory beside `bin`, at the installer's modes, and reads every
      file back against the current engine's digests; then one exchange puts the new directory at `bin` and
      the previous engine beside it; then the record and the units are each written to a new file and renamed
      over the old one. Any failure setup sees after the exchange (a record or unit write, or the restart of
      AC4) exchanges the directories back, restores the previous record and units and refuses by name, and a
      failed restart also restarts the service once on the previous engine. The previous engine directory is
      removed only after the upgrade and its restart have succeeded. A re-run that finds a new directory
      left beside `bin` removes it and starts again; one that finds the installed files equal to the current
      engine's digests but the record not yet rewritten writes the record, and restarts the service once as
      AC4 does when its step log shows the exchange with no restart after it; the kill rows after the exchange
      require that restart in the invocation log. The suite takes the upgrade's
      write points in order from its own step log, so a new write is a new point, and kills setup at each
      one over the 8bc34e94 host; after each kill the installed `bin` equals exactly one engine's digests,
      and the installed control_service.py `serve` starts on the scratch store and answers an inspect over
      its socket; a second run then ends as AC1 requires. A stand-in systemctl fails the restart once, and
      the row requires the previous engine back in `bin`, its record restored and the service answering.
      Falsifier: Write the new files over the installed ones in place, one by one, and the kill row at the
      first new file must fail on an engine directory that equals neither engine's digests.
    falsified_by: >
      Write the new files over the installed ones in place, one by one, and the kill row at the first new
      file must fail on an engine directory that equals neither engine's digests.
  - id: AC3
    text: >
      Claim: The upgrade keeps everything the owner or setup wrote other than the engine: every store,
      journal, key, enrollment, account profile and configuration value. Set and completeness: The upgrade
      writes only the engine directory, the record's engine keys, the keys the record lacks, and the two
      unit files, plus the pinned Claude Code copy under `<state root>/engines/claude_code/<version>` and
      `host/engines.json`, each only when absent. A receiver configuration gaining `state_root` also gains
      `runs` naming the directory it already resolves beside its store, preserving any explicit `runs`.
      The runs directory joins the snapshot set. Every file under the key directory, the host trust, the workspace binding, the token file
      and every registered account's profile directory (VELDO-0160) is unchanged byte for byte; every
      journal row and entity row in the store before the upgrade is unchanged, in order and digest; and every
      value in every configuration file under the installation's `config` directory (service.json's values
      other than its engine keys, the ingress, API and work configurations, each receiver configuration)
      keeps what was there, the only change being a key the file lacked. Before upgrading each older host of
      AC1, the suite sets one value in each configuration file as the owner could have (a receiver
      configuration's adapters, the work configuration's lines) and snapshots every file above and the store's
      rows, and compares them after the upgrade. Falsifier: Write each configuration file as a fresh
      installation would, and the kept-data row must fail on the receiver configuration's owner-set adapters.
    falsified_by: >
      Write each configuration file as a fresh installation would, and the kept-data row must fail on the
      receiver configuration's owner-set adapters.
  - id: AC4
    text: >
      Claim: The owner upgrades with the one command he already runs, is told in plain words what will change
      and what changed, the service restarts once, and a second run changes nothing. Set and completeness:
      The upgrade is a step of `veldo factory setup` with the same arguments; there is no other command.
      Before its first write, setup prints to its standard error one plain line naming what it will change
      (for example "Upgrading the installed factory engine: 12 files change, 3 are new, 0 are removed; the
      authority service will restart once."), and its JSON answer's `engine_upgrade` step says what it did,
      with the previous and current engine digests and the files changed, added and removed, or
      `already_done` when the installed engine is current. After the switch, when the authority unit is
      active, setup restarts it once through control_service's Systemctl (the API unit restarts with it,
      VELDO-0171 AC2) and waits for the service to answer an inspect over its socket; when the service runs
      but not through its unit (the store lock is held and the unit is inactive), it restarts nothing and the
      answer names the one command to run; when nothing runs, it starts nothing and the answer says the next
      start runs the current engine. A second run over the upgraded host writes nothing: every file under the
      state root, install root, unit directory, host trust and workspace binding is byte for byte the same,
      the journal head is unchanged, and the stand-in systemctl's invocation log, which the suite owns
      outside setup's write access, shows no restart. Falsifier: Restart the authority unit on every run, and
      the second-run row must fail on the restart in the invocation log.
    falsified_by: >
      Restart the authority unit on every run, and the second-run row must fail on the restart in the
      invocation log.
required_evidence: [unit, integration]
rollback: >
  While the previous engine directory is still beside `bin`, stop the service, exchange the two by hand and
  put back the previous service.json and units. Run bin.upgrade/control_service.py restore-owners
  <config>/service.json from the current engine directory before starting the previous engine; this restores
  its ownership declarations. The store rows, keys, enrollments and every configuration value are kept. No automatic rollback beyond AC2's switch back is authorized, and a
  downgrade after the previous engine is removed is out of scope.
---

## Intent

Anyone running an older factory installation, the owner's own host first, brings it up to the current
Veldo by running factory setup again, as he already does, and loses nothing: his stores, keys, enrollments
and settings stay, and a failure never leaves a factory that cannot start.

## Context

Built on build-veldo-0171 at 1dbf0b88, whose re-run and API unit it extends; VELDO-0171 lands with it.
W149 of [PLAN-0019 revision 4](../plans/PLAN-0019-dark-factory.md), Release 1 stage 5. The owner's host
holds an installation that VELDO-0139's setup laid down at an older engine. VELDO-0171's review found that
its re-run refuses that host (`unavailable_service:api:not_installed`), because VELDO-0171 AC4 said the
installed engine files are never replaced, which contradicts its promise to add the API steps to a
VELDO-0139 host. The owner asked for the upgrade in Release 1 (Telegram 29307, "For 0171, ok to add") and
for it to work for anyone on an old installation, not only his host (29309, "Need to make sure anybody
running old install upgrades easily too"). VELDO-0047's installer lays the engine down under
`<install root>/<service>/bin`, byte for byte and read-only, and records each file's digest in the
installation's service.json `closure`; that record is what this upgrade compares, so it needs no knowledge
of past versions. VELDO-0171 now depends on this specification, its AC4 says installed engine files are
replaced only by this upgrade, and its rows over a VELDO-0139 host lay the host down from the whole engine
of the older commit. VELDO-0139 is a standalone built item, so its edge is kept here and not in the plan
graph. A draft: only the owner marks it ready.

## Out of scope

Store schema migrations, which each specification that changes the store owns; downgrading to an older
engine (the rollback is by hand); the Mac's installation (VELDO-0147); replacing an existing engine pin.

## What the reviewer judges

- Normal use: the owner, or anyone with an older installation, updates Veldo and runs `veldo factory
  setup` with the same arguments; setup says it is upgrading the engine and what will change, replaces
  it, restarts the service once, and reports what changed; his factory runs on the current engine with
  his stores, keys, enrollments and settings as they were. Running setup again changes nothing.
- Threat model: an older installation left on its old engine, or refused; an upgrade that overwrites a
  key, an enrollment, a store row or a configuration value; an engine half old and half new after a
  failure; a file the current engine no longer ships left installed and loaded; an engine file edited by
  hand overwritten without notice; a restart on every run; a service left stopped after an upgrade.
- Out of review scope (filed, not blocking): unlikely edge cases (owner, Telegram 28962), such as two
  setups upgrading one installation at once, or the host losing power during the exchange itself (the
  exchange is one system call); files planted in the installed directory by another account; forged rows
  in our own store.

## Notes

The exchange keeps every path the unit and the record name unchanged, so the unit needs no edit to run
the new engine; only a changed template rewrites it. A running service has loaded its modules already,
and the launch receiver and API process it starts read `bin` afresh, which is why the restart follows the
switch at once.

## History

2026-09-28: new draft for the owner's requirement that setup upgrade an older installation in place
(Telegram 29307) and that anyone on an old installation upgrade the same way (29309). Only the owner marks
a specification ready.

2026-09-28: marked ready by the owner (Telegram 29313, "Ok approved"), after the fresh check's text fixes.

2026-09-28, build: built on build-veldo-0171 with VELDO-0171, one row short of green. The upgrade is
.veldo/control_factory_setup_upgrade.py, run by control_factory_setup's re-run after every read-only check
and before any other write; the current installer's rendering of an installation's arguments is
control_service.layout, the pure half of install(), which install() now writes. The staged engine is one
write point of the step log (<home>/state/engine-upgrade.jsonl), since it is not installed until the
exchange. Over 8bc34e94 and 971186ac the receiver configuration lacks the host_trust key the current launch
receiver needs, so the upgrade adds it (AC3's "the only change being a key the file lacked"), and VELDO-0171
AC4's row over the 7fefdb9a host accepts that added key too. A service running outside its unit is not
restarted, and VELDO-0171's re-run then starts no API unit beside it. Proof in suite
86_veldo_0189_engine_upgrade and proof/VELDO-0189/. Blocked: switch/kill-points is red over the 8bc34e94 host
because the store's ownership declarations bind control_channel_activation.py to the bytes the 8bc34e94
service first attached (changed at 7fefdb9a), so the upgraded service's channel is refused
ownership_conflict and the API edge enrollment through it is refused. Carrying ownership across an upgrade
is a store write that AC3 and the rollback rule out, and a control_store change outside this footprint: the
owner decides. Over a 971186ac kill host every row is green and every mutation is rejected.

2026-09-28, build: the blocker fixed. A fresh installation's store names the current bytes of every owning
module, so AC1 needs the ownership declarations carried to the upgraded engine; they are carried by the
engine that holds them, not by setup, so AC3's list of what the upgrade writes stands. control_store gains
rebind_owners, its one re-declaration path, and the footprint gains .veldo/control_store.py and its engine
copy for it: a declaration naming an installed engine file by path is rebound to the digest the
installation record holds, only when the file's bytes have that digest now; selector, value, owner and
commands never change. control_service.serve calls it with the record's closure right after it opens the
store and before anything attaches, only when the running module is the record's executable, and logs each
rebinding (ownership_rebind). An edited file, or a service started on the new files before the record is
rewritten, keeps its declaration and is refused at attach as before. switch/kill-points is green over the
8bc34e94 host, and two mutations (the carry removed; a digest the file does not have taken) are rejected
on it. The limit this leaves, stated in control_store: an engine that predates rebind_owners cannot attach
its owners to a store a later engine rebound, so the rollback by hand to such an engine after the current
one has served leaves its owned commands refused ownership_conflict (a rollback to an engine with
rebind_owners carries them back from the restored record).

2026-09-28, review fix: the review found that a restart which brings the current engine up and then fails
switched back to a previous engine whose owned commands were refused ownership_conflict, because the current
engine had rebound the declarations to its bytes (AC2 and the rollback). The lead's decision, as built: while
the previous engine directory is beside `bin`, the rebinding records each rebound declaration's previous
digest in the same store transaction; the switch back stops the unit and, before the previous engine
starts, runs the current engine's own `restore-owners` from its directory beside `bin` (setup never opens
the store), which binds each recorded declaration to its previous digest only when the file at its path has
those bytes (ownership_restore_differs by name otherwise, the new bindings kept) and clears the record; a
committed upgrade has setup ask the running service, signed, to drop the record, and a service that starts
with no previous engine beside it drops any left. Rebind, restore and drop are each observed
(ownership_rebind, ownership_restore, ownership_commit) inside their transaction before the commit. New rows
switch/failed-after-start (over both older hosts), ownership/restore-differs and ownership/committed, and four
finding 189 mutations. The rollback by hand still needs the restore run before the previous engine starts,
which the rollback text does not say: the owner's decision.


2026-09-28, follow-up review: recovery reads exchanges and successful restarts across every begin in the
step log. A prepared entry keeps the original record and unit renderings before exchange, so resumed
failures restore every unit written across runs. An interrupted switch back completes its stop, ownership
restore and previous-engine restart before removing a directory; setup releases its own store lock for
that recovery and reacquires it afterwards. Stop failures and restore refusals are named to the owner,
with every blocking declaration named and forward setup as recovery; restore remains all or nothing.
The manual rollback instruction now includes the real restore-owners command. Seven additional rows
cover resumed failures, rollback kills, stop refusal, restore reporting, serve cleanup, commit refusal
and stop-before-restore. Finding 189 mutations cover each. No acceptance criterion or footprint changed.

2026-09-29: implemented the owner-approved criteria amendment requested in Telegram 29385 and approved
in 29386 (2026-09-28). AC1 compares and installs closure plus runtime assets, including subdirectory
modes, and includes the qualified Claude Code pin and host/engines.json in fresh equivalence. AC3 permits
those two additions only when absent and preserves the existing runs resolution when adding state_root;
the runs tree is snapshotted. Removed the incorrect re-run claim from Out of scope. The footprint adds
the 0171 and 0186 suites because the merged setup requires both engine fixtures and the Tailscale
stand-in, and their existing installation assertions must cover the extended installation set.

2026-09-29, merge verification: the footprint also names the 0168 suite. Its exhaustive send census
now lists the setup API, passkey and upgrade service_request calls as local authority socket transports;
AC4 uses the last for inspect and ownership commitment. Telegram endpoints and rendering assertions stay
the same. This resolves the census failure introduced by combining the two branches.

2026-09-29, amendment proof: the three new rows are red by assertion against merged baseline 3fa0d77b;
the current upgrade suite passes all 51 checks in both ordinary and empty gate environments. All ten
selected integration suites pass, and 0171 also passes in the empty environment. Finding 189 has 36
registered mutants with valid anchors and syntax; their execution and the aggregate gate are reserved
to the reviewer. Verification and the baseline red record are in proof/VELDO-0189/.

2026-09-29, setup recovery review at be94c919: AC1 and AC2 now cover publishing host/engines.json
through a sibling temporary file and rename, repairing an unreadable record on retry, and refusing a
readable different record by path before pin or engines-record writes. AC1 uses the fresh setup's Codex digest refusal on
upgrade too. AC4 reports actual pin and record writes even when the engine is already current. AC1's
inspection refuses malformed runtime inventories and receivers missing store by path before any write.
Seven new behavior rows exercise the real setup and engine writer over a host the current installer
made. Finding 189 gains their falsifiers and a wrong pin mode mutant against the existing equivalence
row, isolating its mode assertion. The acceptance criteria and footprint are unchanged. Mutation runs
and the aggregate gate remain the reviewer's work under the owner's run restrictions.


2026-09-29, recovery review proof: red-at-be94c919.json has all seven new defect rows red by assertion,
with the other 25 behavior rows green. The final source passes the selected 0189 suite normally and in
the requested empty environment: 58 checks, zero failures in each. The validator passes; all engine
copies match; finding 189 has 46 mutants with valid unique anchors and syntax, ten added for this review.
Their execution remains reserved to the reviewer. The review diff stays within this footprint; the
supplied origin/main checker still reports inherited stacked paths and historical gate stamps.

2026-09-29, suite runtime review: retain every behavior row and kill point while reusing
content-keyed engine derivations within one suite run and waiting on service readiness or exit.
The footprint adds scripts/suites/support/setup_runtime.py because both setup suites need the
same isolated computation cache and process event waits. No production contract or gate budget changes.

2026-09-29, runtime proof: the unprofiled baseline at 5730a17e passes its behavior checks but
fails the 60-second runtime assertion at 345.246 seconds. The final selected suite passes 58 checks
in 53.37 seconds ordinarily and 56.98 seconds in the empty gate environment, with no failures.
Every existing check and kill loop is retained. Per-row timings, the runtime red record and the
assertion audit are in proof/VELDO-0189/performance.json and its companion records. Finding 189
mutations remain registered; their execution and the full gate are reserved to the reviewer.

2026-09-29, mutation registration review: six fresh-equivalence mutants now name both
upgrade/from-8bc34e94 and upgrade/from-971186ac directly. Each row already calls equals_fresh,
including runtime asset names, bytes and modes, the runtime inventory in service.json, the qualified
pin and host/engines.json. No mutation edit or behavior assertion changed. The separate equivalence
row remains. Audit every finding 189 and 171 target using the checker's final-word matching rule.
The footprint is unchanged; mutation execution stays with the reviewer.

2026-09-29, registration proof: all 63 finding 189 and 171 targets match one passing row;
all mutation names are globally unique and the anchor checker reports zero bad anchors. Both
selected suites pass normally and in the empty gate environment (58 and 44 checks). The requested
baseline drive at 7f38b201 observes all 32 upgrade rows passing, including the disputed equivalence
row, so no all-red behavior claim is made for this registration-only repair. Exact row lists,
matching results and the inherited origin/main footprint discrepancy are in
proof/VELDO-0189/registration-audit.json. Mutation execution remains reviewer pending.
