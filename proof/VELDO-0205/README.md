# VELDO-0205 proof: every served repository's PM services on the shared connections, one Telegram bot for all

Built on branch build-veldo-0205 at 01734c59 (the VELDO-0088 ingress grooming fix branch merged with the
reviewed specification). Nothing of it is on main yet.

## The design as built

**One transition per command, keyed by repository.** Each per-repository service registers through a small
`_serve` function in its own module (so the store's ownership check still sees that module's code): the
connection's entry for the command keeps a `repositories` map and one transition that hands the command to
the service of the repository it names, refusing `invalid_input:repository` when that repository has no
service there. What picks the service is what the service itself derived from its own coordinates: Teams'
`repository_uuid` store parameter (new), Inbox's `assignment:<repository>:<alias>` id, the claim id
`claim:<repository>:<unit>`, the framing's and the settlement's request id, the terms and API answer ids,
and for ReadSets the `repository_uuid` that `ReadSets.execute` now adds to the parameters of
`accept_snapshot` and every enabled operation. The picked service keeps every check it had, so a wrong pick
refuses rather than writes. Backlog and Grooming were keyed by the VELDO-0088 fix.

**The checks against the project's repository.** Teams refuses `wrong_repository` for a project whose
`execution_repository` is not its own (before asking the owner anything, and again inside the transaction)
and for an assigned unit of another repository; a backlog `take` refuses it for a feature whose project is
executed elsewhere; a line's decomposition refuses it for another repository's item before allocating.

**from_line.** It first asks `control_api_authority.authority_problem` with the service's authority lock
descriptor (`Service.lock`, set by `serve`) for both connections; refuses only a second build of the same
repository (`invalid_registration:pm_services`, judged by the snapshot authority a completed build ends
with); attaches the one allocation authority over every line of the loop and binds the line's own
publisher; shares one Intake per connection; and builds the line's Grooming with its own repository's
ingress Inbox, Presenter and Settlement. The pm_snapshot_inputs read set narrows decisions to the line's
repository and dispatches to `contract.repository`, and gains the PROPOSED intake proposals of the project
recorded for the line's repository; a cycle picks up an awaiting factory inbox proposal only when its
recorded repository is the line's (a proposal recorded before this has none and is still picked up).

**Telegram.** `open_ingress(config, clock, repositories=, lock=)` builds one gate and one acquirer and, per
served repository, its Inbox, Presenter and Settlement (`Ingress.served`); `Channel.tick` presents every
repository's pending requests and every settlement runs. The Acquirer reads the replied receipt, takes the
repository from its request id and hands the reply to that repository's presenter; a receipt of no served
repository is `unknown_presentation`. The protected answer signer signs an answer naming the repository
whose request it answers (same domain and store). With more than one served repository each presentation,
tell and hint begins with `Repository: <final path component> (<first 8 of the uuid>)` and, for a request
or message of one project, `Project: <name>`; the presentation's lines are its receipt's `repository_label`
and part of the rendered bytes its digest covers. With one served repository nothing is added. Intake
records each proposal's `repository` (its project's execution repository; the factory's for a message
naming none), refuses `missing_authority:repository_not_served` for a project of a repository not served
and tells the owner so in the hint, which is then sent even with nothing waiting; a routed proposal records
its new project's repository, and the unclear-route question labels each project.

**Observability.** Each keyed transition appends one record per command it hands on, naming the operation
and the repository of the service it picked, to the `handoffs` list of the connection's entry for the
command (beside `repositories`), as ReadSets keeps its observations. from_line logs one `pm_registration`
observation per PM service a line registers (its repository, connection and service kind) to the
installation's observation log through `Service._log`, and counts them in `Service.pm_registrations` by
repository and kind; the service's own accepted and refused tally skips them.

## Rows (scripts/suites/95_veldo_0205_multirepo.py)

- **pm/two-lines**: The production Service on its own connection holding the lock, the real ingress, two lines and from_line: exactly two connections opened; every keyed command serves both repositories; per repository a signed chain (intake, objective, feature, take, publish, prepare, grooming, admission), a snapshot, a team proposal and an inbox request opened and answered, every record read back with its own repository_uuid.
- **pm/same-repository-twice**: A's line built again: `invalid_registration:pm_services`, journal head and both registries unchanged.
- **pm/unserved-repository**: Each keyed command on each connection, named for a third repository directly through control_store execute: `invalid_input:repository`, nothing written; the signed command for it through the service: `missing_authority:repository_not_served`.
- **lock/not-the-authority**: from_line and open_channel with a descriptor of the store's lock this process does not hold: `missing_authority:not_the_authority`, registries unchanged.
- **pm/cross-repository**: An allocation, snapshot, team propose (both directions), team assign, backlog take (both directions), inbox answer and disposition, backlog operation and grooming proposal signed with one repository's ids naming the other's entity: each named refusal, the entity and both journal heads unchanged.
- **pm/views**: Each repository's inbox index, backlog listing, cycle records, pending obligations and accepted pm_snapshot_inputs list its own records only; one dispatch per repository (a fixture row written around execute, `contract.repository` set to that repository) is listed in its own snapshot and not in the other's.
- **pm/observed**: The team, inbox, backlog and snapshot hand-offs on the service's connection and the backlog and grooming hand-offs on the ingress's each recorded with their operation and both repositories; each line's six PM registrations counted once by repository and kind, and each observed in the log with its repository and connection.
- **telegram/one-repository**: The same store served as one repository: no repository_label, and the presentation, hint and notice are the bytes control_channel_presentation renders at 01734c59 (read with git show).
- **telegram/two-presentations**: One pending request per repository, one tick: two messages through the one bot, each beginning with its own label.
- **telegram/reply-routes**: B's message answered: B's request settled by B's settlement, A's pending; then A's answered and settled.
- **telegram/label-bound**: A receipt whose label is removed or changed (written into the store) is `presentation_mismatch`.
- **telegram/addressed-by-project**: Messages carrying A's and B's ticket keys and an API request naming A's project: each proposal records its project's repository, each hint begins with that label, and only that repository's snapshot inputs list it.
- **telegram/unaddressed**: A message naming no project: a factory inbox proposal only the factory project's cycle inputs list; routed to B's project, listed in B's inputs only.
- **telegram/unserved-project**: A ticket key of a project on an adopted but unserved repository: refused `missing_authority:repository_not_served`, no proposal, the owner told so.

## Red record

`python3 -B proof/VELDO-0205/drive.py --red 01734c59` runs the current suite against the whole tree of
01734c59 (red-at-01734c59.json): pm/two-lines, pm/unserved-repository, lock/not-the-authority,
pm/cross-repository, pm/views, pm/observed and all six telegram behaviour rows are red, by their own checks
(`by_assertion: true`). Two rows hold there by design: pm/same-repository-twice (the code before this
refused every second line by the same name) and telegram/one-repository (it asserts the single-repository
bytes are unchanged).

## Mutations

Finding 205 in scripts/check_teeth_mutations.py, 20 mutations, each red on its named row by assertion with
the baseline and every no-op control green; drive.py writes mutations.json and one diff each.
v205-snapshot-reads-every-dispatch (the dispatches `where` back to `{}`) reds pm/views, and
v205-handoff-names-no-repository (the team hand-off record without its repository) reds pm/observed. The four declared falsifiers: v205-team-single-registration (pm/two-lines),
v205-snapshot-skips-revision-repository (pm/cross-repository), v205-replies-settle-through-authority
(telegram/reply-routes), v205-proposal-records-authority-repository (telegram/addressed-by-project).
