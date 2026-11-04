# VELDO-0235: each project has a landing destination, land and push or land locally

Spec: `specs/VELDO-0235-a-project-can-land-locally-without-pushing.md` (ready, owner approval Telegram 39065).

## What changed

- `control_project.py` (engine and synced `.veldo/` copy): `LANDING_DESTINATIONS = (land_and_push, land_locally)`,
  `landing_destination(data)` (a record without the field reads as land_and_push and is never rewritten for it), and
  the operation `set_landing_destination`, signed and checked as every operation after activation (active person,
  project_owner in a scope covering the project, the owner the record names, the record's version). Any other value
  is `invalid_input:landing_destination`. Not a lifecycle edge: it appends one `landing_destination_history` entry
  (previous, new, by, at, command_id); the observation names project, previous, new and command id.
- `control_landing.py`: `unit_destination` (the unit's project record read through control_project), `binding`,
  `destination_words`; a Landing runs under a destination. land_and_push is the existing code path. land_locally
  keeps every check before publication, copies the candidate's objects into the project repository with
  pack-objects and unpack-objects, records `effect:<dispatch>` (accepted, then completed or refused) through its own
  `record_local_publication` command, swaps `refs/heads/<trunk>` from the watermark with `git update-ref <ref> <new>
  <old>`, and completes by re-reading that local ref into the same revision_landed receipt. A trunk found moved
  before the swap is refused `stale-subject`, a lost swap `trunk-moved`; both end the land as trunk_moved (VELDO-0148).
  The destination is bound: a grant bound to another destination (none means land_and_push), or a destination changed
  since the dispatch began, refuses `stale_subject:landing/destination`; when that and an older tree are all a grant
  lacks, the refusal carries the exact subject a fresh grant binds, its destination included for land_locally.
- `control_landing_station.py`: each land reads the destination when it opens and records `destination` and
  `destination_command` in the land dispatch record; the Landing and lander get it; `grant` binds the destination;
  `status()` counts land dispatches by destination and outcome.
- `lander.py`: `GitLandOps(destination=land_locally)` takes its watermark from the local trunk (no fetch) and
  publishes through the wired Landing.
- `control_service.py`: the owner's land grant brief (Line.grant, the one landing question the factory asks, for a
  missing re-merged tree grant and now for a destination) ends with `Destination: land and push to <remote>.` or
  `Destination: land locally on <trunk>, nothing pushed.`
- `engine/ui/src/features/projects/projects.ts`: each ProjectView carries `destination` and `destinationWords`; spec
  in `projects.spec.ts`. Rendering it needs the view file outside the footprint: OPEN.md item A.
- New suite `scripts/suites/128_veldo_0235_land_locally.py` (manifest, requires.json regenerated);
  `scripts/check_teeth_mutations.py` finding 235 (five cases).

## Per acceptance criterion

Suite 128, before the change (`before-change.txt`, the five engine modules of 31923d91 in a scratch worktree): 8 of 8
rows red. After (`after-change.txt`): 8 of 8 green, 34 checks.

| AC | Rows | Result |
| --- | --- | --- |
| AC1 | destination/default-push, destination/owner-sets, destination/refused | green |
| AC2 | local/lands, local/trunk-moved | green |
| AC3 | bound/brief, bound/destination-changed; UI: projects.spec.ts | green; view rendering open (OPEN.md A) |
| AC4 | push/unchanged; suites 70 (VELDO-0057), 86_0148, 107 and 108 (VELDO-0153) unchanged | green |

- AC1: project `pushed` has no field, reads as land_and_push, its unit lands through the station under land_and_push
  and the bare origin receives the candidate; the record keeps its version and gains no field. The owner's signed
  command sets `local` to land_locally with one history entry naming previous, new, owner and command id. Another
  value, a non-text value, a command signed by another key, another principal (no scope) and an unsigned command are
  refused (`invalid_input:landing_destination`, `not_authorized`, `not_authorized:scope`) with the journal head and
  record version unchanged.
- AC2: project `local`'s unit lands: the caller's main moves from the watermark to the candidate, the publication
  records ref, old tip and new tip, the receipt's confirmation is the local ref re-read, spec.shipped is projected,
  the bare origin is byte for byte unchanged, the logging Git (first on PATH for every process) shows no push, fetch
  or ls-remote, the executor is never called and no identity transport runs. A local main moved between the gate and
  the publication ends the land trunk_moved (`stale-subject`), the moved commit stays the tip, and the re-land
  (follows the first) lands on it.
- AC3: Line.grant's brief, run over a recording inbox, says "land and push to origin" and "land locally on main,
  nothing pushed". A grant bound (no field, so land_and_push) to the exact tree, then the destination changed to
  land_locally: the land is refused `stale_subject:landing/destination` as awaiting_approval with nothing moved, its
  subject names land_locally and the tree, the brief asked names the destination, the owner's grant binds
  `destination: land_locally`, and the land after it lands locally. UI: `ui-vitest-before.txt` (the new spec red on
  the old projects.ts), `ui-vitest-after.txt` (4 of 4 green); vue-tsc clean.
- AC4: a project explicitly set to land_and_push and one without the field each land with today's effect contract
  keys and payload, the executor's completed publication at the tip, and a receipt confirmation of remote, ref,
  commit and read_at; the set land's log shows fetch, ls-remote and push and the origin received it. The existing
  landing suites pass unchanged: 70 57/57, 86_0148 52/52, 107 146/146, 108 32/32.

## Fix round 1 (review F2, 2026-11-04)

The review found AC3's project view unrendered, and its words "its remote" and "its trunk". The lead widened the
footprint to `engine/ui/src/views/ProjectsView.vue` (spec History, d18d1d4c).

- The service names its work configuration's land remote and trunk by execution repository
  (`control_service.landing_names`) and gives them to the API authority when it serves a factory loop;
  `ApiAuthority.read` adds `landing` to the objectives read, the remote and trunk by project name
  (`control_api_authority.landing_of`), as the repositories read adds `identities`. A project whose repository names
  no land entry is left out.
- `projects.ts` reads `landing` and words each project's destination with that remote and trunk, the brief's own
  words ("land and push to origin", "land locally on main, nothing pushed"); "the remote" or "the trunk" only when
  the read names none, as control_landing.destination_words says.
- `ProjectsView.vue` shows the destination on each project card and in the selected project's detail panel
  (`Landing`), with `data-destination` naming the value.

Evidence, red before and green after:

- UI: `fix1-ui-vitest-before.txt` (on the projects.ts and ProjectsView.vue of d18d1d4c: the new
  `features/projects/ProjectsView.spec.ts` 2 of 2 red, the card and the detail panel name no destination; the
  extended `projects.spec.ts` 2 of 5 red on "its remote"), `fix1-ui-vitest-after.txt` (2 of 2 and 5 of 5 green,
  vue-tsc clean). Each file run alone, from the locked dependencies in a scratch copy.
- Suite 128 row bound/view: `fix1-suite128-before.txt` (on the control_service.py and control_api_authority.py of
  d18d1d4c: red, the service has no landing_names, so the suite raises and every row is red),
  `fix1-suite128-after.txt` (35 of 35 green).
- Landing and neighbour suites at the fix tip: `fix1-suites.txt`.

## Falsifiers (finding 235), each run alone through the gate's driver

`check_teeth_mutations.py --case <name>`: every case passed (baseline green, no-op green, mutant red). Receipts in
`mutations/*.txt`, summary `mutations/summary.txt`.

- dest235-absent-reads-local (AC1): `landing_destination` defaults to land_locally. destination/default-push red
  (the record reads as land_locally; its land publishes nothing).
- dest235-local-also-pushes (AC2): after the local swap the candidate is also pushed to the origin. local/lands red on
  the bare origin's changed ref (and the logged push).
- dest235-destination-unbound (AC3): the approval's destination is not compared. bound/destination-changed red: the
  land after the change lands instead of awaiting a grant.
- dest235-push-routed-local-0057 and dest235-push-routed-local (AC4): every landing takes the local path. VELDO-0057's
  exact-tip/compare-and-swap red (the remote never moved: `unknown_outcome:confirmation`), and suite 128's
  destination/default-push and push/unchanged red.

## Neighbour suites run (all green)

`neighbour-suites.txt`: 32 suite runs (suite 128 among them) over the suites loading the changed modules, every one 0 failed. `scripts/verify.sh` was not run.
