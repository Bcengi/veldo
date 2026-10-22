# VELDO-0161 round 2: the host run and the independent review, each finding fixed with a row and a falsifier

Branch agent/claude/agent/claude/veldo-0161, from da39f3fb. Code at a506b4d1 (commits 19af8275, be4c8f60,
b8361f20, the mutations, the specification's history). Nothing here is a gate result, a review verdict or an
approval. Every falsifier below was run in this sandbox through the teeth driver's worker mode
(`falsifiers.json`); the rows that need a local socket are the host's (Host runs).

| Finding | Fix | Row(s) | Falsifier(s), result here |
| --- | --- | --- | --- |
| A, 137 agent contacts | The suite's own `sign_as` and key generation ran ssh-keygen with SSH_AUTH_SOCK set; they now strip it, and every ssh-keygen in control_repository goes through one `_quiet_env` (the effect's journal signer uses it too) | `adoption/signer-no-agent`: a stand-in ssh-keygen first on PATH records any agent variable while SSH_AUTH_SOCK and SSH_AGENT_PID are set | `adoption161-signer-agent` killed |
| B1, push before checks | Scaffold, configured remote, repository commands, existing binding, host trust and signer enrolled are all checked before the fast-forward and push; `enrolled()` is False for a missing key | `adoption/signer-enrolled`: the legacy host is an unscaffolded repository with no key; bare and local tips unchanged, ref removed | `adoption161-push-before-checks`, `adoption161-enrolled-missing-key-raises` killed |
| B2, served before active | The record is written active, then served; a failed write serves nothing and removes the receiver configuration it made | `adoption/take-on-write-first` (sqlite3.Error and StoreRefused) | `adoption161-served-before-write` killed |
| B3, stuck provisioning | Every fault in the steps ends `failed` with `unknown_outcome:<type>`; an accepted push whose branch does not read back is `push_unconfirmed:remote` | `adoption/unknown-outcome`, `adoption/push-unconfirmed` (the remote's own post-receive moves its branch back) | `adoption161-fault-stuck`, `adoption161-push-unconfirmed-as-refused` killed |
| B4, repository commands | Every local step passes `-c core.fsmonitor=false`; a filter or fsmonitor in the repository's configuration is refused by name, at prepare and before the fast-forward | `adoption/repository-commands` (an fsmonitor command and a filter planted) | `adoption161-fsmonitor-on`, `adoption161-repository-commands-unchecked` killed |
| B5, rows with no teeth | New rows and cases for each scaffold check, each take-on refusal, the signer's store and root-commit pins, the written receiver configuration used by the launch receiver, and a remote under another owner that nothing else would stop | `adoption/scaffold-problems`, `adoption/take-on-refusals`, `adoption/signer-scope`, `adoption/receiver-configuration-used`, `adoption/remote-owner-refused` | `adoption161-scaffold-unrecorded`, `-scaffold-parent`, `-scaffold-modifies`, `-take-on-decision-unchecked`, `-take-on-signature-unchecked`, `-take-on-binding-signer-unchecked`, `-take-on-store-binding-unchecked`, `-signer-store-unchecked`, `-signer-identity-unchecked`, `-receiver-configuration-wrong`, `-receiver-configuration-absent`, `-remote-owner-unchecked` killed |
| B6, polling | The serve-loop watermark poll and the effect's 50 ms wait are gone. The effect sends a `take_on` packet from the adopted repository's workspace over the service socket, signed with the journal key in `veldo-adoption-take-on` (the only packet verified under that key), and reports the synchronous answer; the reconcile at start stays | `adoption/take-on-answered` (in process, over control_client.Authority), `adoption/taken-on-running` (host: answered active before the effect returns), `adoption/not-taken-on-named` (host: no service, `not_taken_on:authority_unavailable`) | `adoption161-take-on-not-sent`, `adoption161-take-on-unauthenticated` killed; `adoption161-restart-take-on` (AC2 declared) the host's |
| B7, restart stops serving | An active record is judged on its journaled signature, binding and store binding, never current membership; a receiver configuration the service wrote is written again from the installed one | `adoption/active-served-again` (the owner loses project_owner; the installed receiver configuration rewritten) | `adoption161-active-rejudged-membership`, `adoption161-receiver-not-regenerated` killed |
| B8, signer pins | The signer pins host_identity and authority_generation and refuses a generation below the store's journaled one | `adoption/signer-scope` (another host, another generation, a generation below the store's) | `adoption161-signer-host-unchecked`, `-signer-generation-unpinned`, `-signer-generation-below-store` killed |
| B9, retry reset | Faults are kept per record with their own retry time; the serve loop waits on the earliest one (a timer) | `adoption/take-on-retry` | `adoption161-retry-reset` killed |
| B10, prepare | The remote must be the one the repository is configured with; the id must be one ref component; the scaffold ref is removed after the push or a refusal | `adoption/prepare-checks`, `adoption/scaffold-commit`, `adoption/signer-enrolled`, `adoption/push-refused` | `adoption161-remote-configuration-unchecked`, `-repository-id-unchecked`, `-scaffold-ref-kept` killed |
| Style | The instance's `token` is `instance_id` in observations and records | `adoption/same-process`, `adoption/take-on-answered` | covered by the same-process row |

The eight round-1 cases are re-anchored and all killed here except the restart falsifier. That one now
refuses the take-on request and execs the serving process, which keeps its pid and kernel start time, so the
next instance takes the record on at its start. Its exec is confined to the installed serving process: the first
run here showed the in-process rows exec'ing the suite itself, which on the host would have stopped the
suite. Its target row is red at baseline here.

Totals (`falsifiers.json`): 37 registered, 36 killed, 1 not judged here, 0 survived; the baseline is identical
before and after (the four AC2 rows red, by name).

## Why the in-process rows

The take-on, its refusals, the write order, the retry and the restart judgment are the service's own
methods. The suite builds `control_service.Service` over the installed configuration and this store and judges
each request with `control_client.Authority.judge` (peer uid, request signature, workspace binding, then
`Service.apply`), which is the socket's serving side without the socket. So each fix has a row that runs and
fails without it everywhere. AC2's same-process claim still needs the real separate process, and those rows
are the host's.

## Footprint

`proof/VELDO-0161/round2/*` was added: the declared `proof/VELDO-0161/*` covers one path segment only
(arch._glob_re), and this directory is where the round-2 evidence was asked for. No other file outside the
footprint changed.

## Host runs (required before review)

1. `python3 scripts/selftest.py --suite 109_veldo_0161_adoption`: every row green, the four AC2 rows
   included, and no HermeticViolation at the fence's end.
2. `python3 scripts/check_teeth_mutations.py --finding 161`: all 37 cases killed, in particular
   `adoption161-restart-take-on` on `adoption/same-process`, and `adoption161-take-on-not-sent` and
   `adoption161-receiver-configuration-absent` on `adoption/taken-on-running`.
3. The systemd and socket suites this change touches: 66_veldo_0047_authority and 86_veldo_0189_engine_upgrade
   (the service and its closure), 73_veldo_0139_factory_setup, 85_veldo_0171_setup_api,
   91_veldo_0167_setup_records and 106_veldo_0185_dispatch_setup (setup's keys and host trust),
   103_veldo_0142_git_identities, 107_veldo_0153_identity_push and 58_veldo_0028_effects.
4. `bash scripts/verify.sh` (full gate, both legs, mutation stage).
