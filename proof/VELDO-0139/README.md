# VELDO-0139 proof: veldo factory setup

`bin/veldo factory setup` is the one owner command that lays a real factory down on this host. It lives
in `.veldo/control_factory_setup.py` (byte-identical in `engine/.veldo/`, laid down by `init_scaffold.py`);
`bin/veldo` only routes `factory` to the module's own `main`. It orders and checks the existing pieces and
reimplements none of them:

1. the control store at `<state-root>/authority/control.sqlite3` (`control_store.open_store`);
2. the owner bootstrap: his own `enroll_principal`, signed with the key he names and admitted by
   `control_membership.admit` through `bootstrap_problems` (the genesis, journal sequence 1);
3. the key projection `<state-root>/host/allowed_signers` (`control_keys.publish`);
4. his chat enrollment from the chat id he gives (the VELDO-0064/0065 `channel_enrollment` entity);
5. the VELDO-0067 edge key generated in the protected key directory `<state-root>/keys`, enrolled by his
   signed `enroll_channel_edge` with the edge key's possession proof (`control_channel_enrollment`);
6. his delegation of decision answers on that edge (`grant_delegation`, his signature, 90 days), then
   the qualification requester `qualification-requester`, a service member whose key is generated in
   `<state-root>/keys`, enrolled by his signed `enroll_principal` with that key's possession co-signature;
   setup republishes the key projection itself;
7. this host's trust at `control_eligibility.host_trust_path()` naming the host identity, him as
   enrollment signer and the settlement signer;
8. the VELDO-0029 enrollment of the workspace clone, signed by him (`control_enrollment.enroll`);
9. the 0600 VELDO-0073 ingress configuration `<state-root>/host/ingress.json`, naming the account's own
   0600 token file (read back through `control_channel_ingress.load_config`, `read_token`,
   `journal_signer` and `decision_signer`; the ingress itself is not opened, because its organs bind the
   store's owned entities to the code that first attaches them, which must be the installed service);
10. the VELDO-0047 service installed with `--channel-ingress` (`control_service.install`). Nothing is
    started; the service's channel is inert (`not_activated`) until the owner's qualify and activate.

Every check runs before the first write. A state root that is absent, a link, not a directory, not this
account's, not 0700, or already holding a store, a trust or anything else is refused by name; so is an
existing host trust file, an already enrolled workspace, a token file that is not the account's own 0600
file, a chat id that is not a user id, an owner key that does not sign, and a service principal name used
as the owner. The setup never deletes: a failure after writing began is named with its step.

## Suite

`scripts/suites/73_veldo_0139_factory_setup.py` (`python3 scripts/selftest.py --suite 73_veldo_0139_factory_setup`).
Every path it writes is scratch (`/dev/shm/b139-*`): state roots, host trust path, install root and unit
directory. The installed unit runs under a user manager stand-in of the suite's own, the Bot API is a
loopback stand-in, and a socket guard (in the suite and, through a sitecustomize, in the service process)
refuses every connection beyond 127.0.0.1. Each row is reported once.

| Criterion | Rows |
|---|---|
| AC1 | `install/assets`, `setup/lays-down`, `refuse/writes-nothing`, `refuse/existing-store` (declared falsifier) |
| AC2 | `edge/enrolled-with-possession`, `chat/enrolled`, `ingress/configuration`, `token/never-copied` (declared falsifier), `service/starts-inert` |
| AC3 | `journey/qualified-and-active`, `qualification/one-request-across-restart`, `genesis/owner-signed` (declared falsifier) |
| Review 1, filed items | `rollback/rerun`, `store/private-and-closed`, `host-trust/directory-checked`; the empty `host/` case is part of `refuse/writes-nothing` |

`journey/qualified-and-active` uses only shipped commands: the setup's own command surface, the service
start through the user manager stand-in, `bin/veldo channel qualify` with the owner's key, the owner's
reply to the presented message through the loopback Bot API, and `bin/veldo channel activate`. Nothing
in the suite enrolls a member, republishes the projection or opens a request: the running service's
channel opens the run's one qualification request as the requester setup enrolled, addressed to the
owner, and presents it on its next pass; the qualification its own gate records names that request and
the owner's answer; the edge is active. `qualification/one-request-across-restart` restarts the service
inside the run (after the qualification is recorded, before activate): the run still has exactly its one
request, found by its alias, and nothing is presented again. `rollback/rerun` checks that the spec's and
this README's rollback name the workspace binding, carries that rollback out after the whole journey and
runs setup again over the same state root, host trust path and clone: it succeeds. The real Telegram leg is PENDING: the lead runs it once with the owner and records it here. No
fixture counts as it.

Stage environment run: 41 passed, 0 failed (26 preamble, 15 rows), about 15 seconds.

## Red record

`red-at-c98d63f.json`: the current suite over `git archive c98d63f`, unchanged. That tree has no setup
module and no `factory` subcommand; all 11 rows fail by their own assertion (the suite records the missing
module against each row, it does not raise).

`red-at-7bf5d59.json` (review 1): the current 15-row suite over `git archive 7bf5d59`, unchanged. Red by
assertion, each on its own check: `journey/qualified-and-active` (no request is opened without the suite's
hand preparation), `qualification/one-request-across-restart`, `rollback/rerun` (the rollback text names
no binding), `store/private-and-closed` (the store is 0644 and the failed store step leaves its connection
open), `host-trust/directory-checked`, `refuse/writes-nothing` (the empty `host/` is named a trust) and
`setup/lays-down` (no requester key). The other eight rows stay green there.

## Mutations (finding 139)

Registered in `scripts/check_teeth_mutations.py`, each declared falsifier first; `drive.py` records
`mutations.json` and one applied diff per mutant. All 20 turn their named row red by assertion; the
baseline and the no-op copies (one per mutated module) are green. `check_teeth_mutations.py --finding 139`:
20 rejected.

| Mutant | Named row |
|---|---|
| existing-store-overwritten (AC1 falsifier) | refuse/existing-store |
| state-root-mode-unchecked | refuse/writes-nothing |
| host-trust-overwritten | refuse/writes-nothing |
| host-directory-open | setup/lays-down |
| module-not-scaffolded (init_scaffold.py) | install/assets |
| token-copied (AC2 falsifier) | token/never-copied |
| edge-key-outside-protected | edge/enrolled-with-possession |
| chat-not-the-owners | chat/enrolled |
| setup-starts-service | service/starts-inert |
| genesis-not-owner-signed (AC3 falsifier) | genesis/owner-signed |
| owner-delegation-omitted | journey/qualified-and-active |
| requester-not-enrolled (review 1) | journey/qualified-and-active |
| requester-projection-stale (review 1) | journey/qualified-and-active |
| qualification-request-not-opened (control_service_channel.py) | journey/qualified-and-active |
| qualification-alias-per-process (control_service_channel.py) | qualification/one-request-across-restart |
| rerun-blocked-by-kept-directory | rollback/rerun |
| store-world-readable | store/private-and-closed |
| store-connection-left-open | store/private-and-closed |
| host-trust-directory-unchecked | host-trust/directory-checked |
| empty-host-named-trust | refuse/writes-nothing |

The other findings' `init_scaffold.py` mutations (39, 40, 41, 42, 45, 47, 50, 51, 67, 68, 73, 75, 76, 138)
were each run honest and mutant after the scaffold change: all still reject.

## Running it on this host

The lead runs this with the owner, from the Veldo checkout whose engine is to be installed, as the
owner's own account. Preconditions: `/var/lib/veldo` exists, is owned by the account, is mode 0700 and is
empty; `~/.config/veldo/host_trust.json` does not exist, and `~/.config/veldo`, if it exists, is the
account's own 0700 directory; the workspace clone is not enrolled. If his key has a passphrase,
ssh-keygen asks for it at each signature.

1. Set the factory up (prints one JSON answer naming the unit):

```
bin/veldo factory setup \
  --state-root /var/lib/veldo \
  --owner dmitry \
  --owner-key <path of his OpenSSH private key> \
  --workspace <path of the workspace clone the factory serves> \
  --chat <his numeric Telegram user id> \
  --token-file <path of the account's own 0600 bot token file>
```

2. Start the service: `systemctl --user start <unit from the answer>`.
3. Start the qualification run:
   `bin/veldo channel qualify --principal dmitry --key <his key> --workspace <clone>`.
   The running service opens one qualification request and presents it in his chat on its next pass.
4. He replies `accept` to that message in Telegram.
5. Once `bin/veldo channel status --principal dmitry --key <his key> --workspace <clone>` shows the
   qualification, activate: `bin/veldo channel activate --principal dmitry --key <his key> --workspace <clone>`.

Rollback: `python3 .veldo/control_service.py stop <unit>`, then `python3 .veldo/control_service.py uninstall <unit>` (VELDO-0047's lifecycle, from the same checkout); the owner removes by hand `/var/lib/veldo`'s contents, `~/.config/veldo/host_trust.json` and the workspace binding `<clone>/.git/veldo/control/enrollment.json`. The setup deletes nothing. A second setup over the same paths then succeeds.

## Open items for the lead

- Filed, not built here: the delegation is bound to request and presentation version 1 with a 90-day life
  (a lifecycle ticket); the store ownership binding blocks engine upgrades (Release 2); the chat
  enrollment is signed by the journal key (no owner-signed chat enrollment command exists); `api-edge` is
  enrolled by VELDO-0130's own setup when it lands; a passphrase key prompts at each signature.
- The host identity is this host's name (`platform.node()`).
