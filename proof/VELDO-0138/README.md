# VELDO-0138 proof

The authority service runs the Telegram ingress and takes the owner's activation commands.
Specification status, risk and `.veldo/policy.yaml` are unchanged. This proof is for independent
review; it is not a self-approval, and the canonical gate is run by the lead.

## What was built

- `.veldo/control_service_channel.py` (new; engine copy identical, in `init_scaffold._FILES`, not
  substrate; part of the service's fixed executable through `control_service.closure()`). `Channel`
  opens the ingress with VELDO-0073's `control_channel_ingress.open_ingress`, unchanged, and owns its
  lifetime. `tick` is one pass: `Ingress.wake` (the gate decides first; a refused pass presents,
  acquires and writes nothing), then `Presenter.publish` for pending requests, then, in a
  qualification run, the qualification the service records itself with `Activations.qualify` once a
  request it presented has settled from the owner's acquired answer. `authorize` hands a
  `channel_activation_authorize` packet to the ingress's own `Activations.authorize`, which admits only
  the owner's own signed envelope. `status` is the read-only view the owner's command surface builds
  from. `installable` refuses an ingress configuration that is not this authority's (store, domain,
  store id, generation, a served repository, the service's own journal principal and key).
- `.veldo/control_service.py`: `install --channel-ingress <file>` copies the configuration 0600 into
  `config/channel-ingress.json` and names it in `service.json`; `serve` opens the channel, runs a pass
  every `POLL_SECONDS` between requests, and closes it on stop; `apply` routes the owner's command to
  the channel (refused by name when no channel runs or the command is for another repository);
  `inspect` carries the channel status. An ingress that cannot be constructed leaves the service
  serving, its refusal reported by name.
- `.veldo/control_channel_activation.py`: `main`, the owner's command surface
  (`status|qualify|activate|stop`), and `owner_command`, which builds the one command of an action
  from what the running service reports. It signs with the owner's enrolled key file and sends
  through `control_client`; it decides nothing the service does not check again.
- `bin/veldo channel ...` routes verbatim to that surface (engine copy identical).

The unauthorized leg: the owner has no second person (Telegram 29047), so when no unenrolled sender's
update came from the platform in the run, the service acquires one update from an unenrolled sender id
from an in-process loopback stand-in of a separate probe bot (`PROBE_BOT_ID`, its own evidence ids and
cursor, so the real bot's cursor and the platform's pending updates are untouched) and the record marks
its provenance `stand_in`, as VELDO-0073's live runner did.

## Rows, falsifiers and red record

Suite `scripts/suites/71_veldo_0138_channel_service.py` (about 25 s; stage environment green). The
service is installed with `control_service.install` and started, stopped and restarted with its own
`start` and `stop` lifecycle functions through a user manager stand-in of the suite's own, which runs
the installed unit's ExecStart as a Type=notify process; nothing is installed into or started by the
owner's real user manager. The owner's commands run as `bin/veldo channel` processes signing with his
enrolled key. Every Bot API exchange goes to a loopback stand-in, and a socket guard refuses anything
beyond 127.0.0.1 in the suite process and, through a sitecustomize on the stand-in manager's
PYTHONPATH, in every service process (the suite asserts it was armed in each). The store is read
through the suite's own connections.

| Row | Criterion | Mutations (declared falsifier first) |
| --- | --- | --- |
| `install/assets` | all | `channel-module-not-scaffolded`, `foreign-store-ingress-installed` |
| `served/inert` | AC1 | `inert-edge-presents` |
| `served/settlement` | AC1 | `service-skips-open-ingress` |
| `qualification/recorded-by-service` | AC1, AC2 | `probe-on-the-real-bot` |
| `command/owner` | AC2 | `owner-command-unrouted` |
| `command/owner-only` | AC2 | `member-authorizes-owner-edge`, `envelope-signature-unchecked`, `owner-checked-against-params-only` |
| `command/stop-live` | AC2 | `stop-needs-restart` |
| `command/stop-keeps-pending` | AC2 | `resume-drops-backlog` |
| `restart/active-stays-active` | AC3 | `service-skips-open-ingress` and `owner-command-unrouted` also red it |
| `restart/stopped-stays-stopped` | AC3 | `restart-resumes-stopped` |
| `restart/never-activated-stays-inert` | AC1, AC3 | `inert-edge-presents` also reds it |
| `qualification/transport-failure-named` | AC2 (filed F2) | `transport-failure-named-fixture` |

Registry: `scripts/check_teeth_mutations.py --finding 138` (13 mutants, all rejected, each reddening
its named row). `python3 -B proof/VELDO-0138/drive.py` regenerates `mutations.json` and the diffs.
`red-at-b74c8a6.json`: the suite of that build against the pre-change tree (the service loads no
channel module and bin/veldo has no channel subcommand), every row red by assertion.
`red-at-af8e477.json`: the current suite against the build before the first review's fix, red by
assertion in `command/owner-only` (the steward's stop naming himself stops the owner's edge, and a
second project_owner person re-qualifies it onto his own enrolled chat), in
`restart/stopped-stays-stopped` (that re-qualified run presents after the restart) and in
`qualification/transport-failure-named`.

## First review fix

Over an existing activation record every command (stop, qualify, activate) must be signed by the owner
that record names, still a current person member holding project_owner; otherwise `not_owner`, the
record unchanged. A first qualification with no record keeps the rule it had. Handing the edge to a new
owner is out of Release 1 scope (spec Notes). Row `command/owner-only` adds, over the active record,
the steward's stop naming himself, and over the stopped record, a second project_owner person
(`deputy`, enrolled as the suite enrolls members, with his own chat enrollment) qualifying and stopping
in his own name: each refused by name with the record unchanged and nothing sent.

Filed F2: an exchange the gate's transport could not complete now records the failure's class
(`transport_failure`), and a run holding one is refused as `unavailable_service`, not
`fixture_only_evidence`. Row `qualification/transport-failure-named` drives it honestly for the
Telegram origin: a separate authority of the run's own, the owner's signed qualify for
`https://api.telegram.org`, and the gate's own transport making getMe, where only the network is a
stand-in (for each call the connection is refused, times out or the name does not resolve, before any
socket opens). The control keeps an exchange that has no TLS and did not fail in transport as
`fixture_only_evidence`. VELDO-0073's `fixture-evidence-accepted` mutation was re-aimed at the reshaped
test (still red in `qualification/real-platform-proof`), and the live record
`proof/VELDO-0073/live/qualification.json` (branch `live-0073-record`) still passes
`qualification/live-record-consistent`.

## The live real-factory qualification (the lead, once, with the owner)

Not run here, and no real token file was read. Through the running factory service:

1. Install the factory's authority service with the channel:
   `python3 .veldo/control_service.py install --workspace <enrolled clone> --channel-ingress <ingress.json>`,
   where `ingress.json` is the account's own 0600 veldo.telegram_ingress/v1 configuration of that
   authority (its store, identities and generation, the service's journal principal and key, bot_api
   origin `https://api.telegram.org` and the account's own 0600 token file; no copy of the token is
   written). Start it: `systemctl --user start <unit>`. It is inert: `veldo channel status` shows no
   record and each pass refused as not_activated.
2. The owner opens the run: `veldo channel qualify --principal <owner> --key <his enrolled key>`
   (15 minutes by default, `--minutes` up to 60).
3. One decision request is opened in the factory's inbox (VELDO-0064 open and VELDO-0065 frame, signed
   by its requester); the running service presents it to the owner's enrolled chat in its next pass.
4. The owner replies to that message in Telegram (`accept: <reason>`). The service acquires the
   reply, settles it, takes the unauthorized leg and records the qualification from its own gate's
   exchanges (refused by name unless every exchange was with api.telegram.org over verified TLS).
   `veldo channel status ...` then shows `qualification` with its id and digest.
5. The owner activates: `veldo channel activate --principal <owner> --key <his enrolled key>`, which
   signs over exactly that id and digest. `veldo channel stop ...` halts the edge at any time.

## Known limits

- Opening a decision request goes through the existing inbox and framing commands on the store; the
  service's socket routes no inbox command (not in this footprint).
- A pass runs in the serve loop between requests, so a slow Bot API exchange delays the next request
  by up to the exchange's timeout (hardening is Release 2), and a restart during a qualification run
  loses that run's exchanges, so the run is qualified again (restart recovery is Release 2).

`red-at-7ae39ff.json`: the current suite against the tree before review 2's filed fix, where
`owner/demoted-halts` is the one red row, by assertion (a demoted owner's edge was still admitted). Mutation
`demoted-owner-still-binds` reds that row; finding 138 now has 14.
