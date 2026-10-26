VERDICT: HAS DEFECTS (R1 medium, R2 medium, R3 low, R4 low)

# VELDO-0161 rounds 2 and 3: independent review

Reviewer: Claude, a fresh context that wrote none of this code. Range da39f3fb..0511a31a, worktree at
0511a31a. Read: the specification and its history, proof/VELDO-0161/round2 and round3 (README.md,
falsifiers.json, setup-signers.json), the diffs of control_effect_executor_adoption.py,
control_repository.py, control_repository_provisioner.py and control_service.py (engine/.veldo and .veldo are
byte-identical; the template sync check passes), suites 109 and 73, and the finding-161 mutations in
scripts/check_teeth_mutations.py. This review is not an approval.

## Findings

### R1 (medium): a take-on hand-off that does not reach the running service is never taken on by it

Files: engine/.veldo/control_service.py:2522 (start-time take_on) and :2539 (CC.bind, later);
engine/.veldo/control_effect_executor_adoption.py:142 (every OSError read as authority_unavailable) and :288
(a hand-off fault that is not OSError or RoutingRefused).

Since B6 removed the poll, the running instance takes a `provisioning` record with an enrollment digest on
in exactly three ways: the effect's take_on packet, the start-time take_on(), and the retry sweep, which only
runs when some record already has a fault timer (adoption_due). A record whose hand-off is lost while an
instance is running therefore waits for the next restart, which is what AC2 rules out.

Concrete scenarios:

1. Restart window. serve() runs service.take_on() at line 2522, then opens the channel, the API and the
   factory loop, and only then binds the socket at line 2539 (CC.bind unlinks the old path first). An adoption
   effect that writes `provisioning, step=enrolled` after the start-time read and connects before the bind
   gets ECONNREFUSED or ENOENT. take_on() reports not_taken_on:authority_unavailable and the effect exits 1
   with the record `provisioning`. The new instance has already reconciled and does not poll. The repository
   is not served until another restart, or until an unrelated record's fault timer happens to fire.
2. A hand-off fault that is not OSError: the journal signer in TAKE_ON_NAMESPACE raises
   R.Refused('unavailable_service:journal_key') or subprocess.TimeoutExpired, or send raises ValueError on a
   malformed answer. The outer handler at line 288 reports unknown_outcome:Refused or
   unknown_outcome:TimeoutExpired. That loses the named code. The record stays `provisioning` with no timer
   anywhere, so it is taken on only at a restart.
3. A 60 second socket timeout while the service is busy in loop.run() is an OSError. It is reported
   authority_unavailable and the effect may print `waiting`, even though the request was delivered and the
   service later writes the record `active`.

Fix: bind the listener before the start-time take_on(), so a connect made during start-up waits in the
backlog and is answered afterwards. Alternatively, run take_on() once more right after the bind. In take_on()
of the effect, catch every exception and keep a named code (R.Refused keeps its own). Report a timeout as
not_taken_on:timeout, not authority_unavailable. Add a row: write an enrolled record between a Service's
take_on() and its serving, and require that the same instance serves it.

### R2 (medium): the prepare fetch runs a command from the repository's own configuration (B4 not closed for all local steps)

Files: engine/.veldo/control_repository_provisioner.py:102-118 (repository_commands lists only filter.*.clean,
smudge, process and core.fsmonitor) and :183 (the scaffold's fetch into the adopted repository).

The B4 fix says "a repository whose own configuration names a filter command or an fsmonitor is refused by
name". The module's docstring claims more: "the keys of the repository's own configuration that name a
command a local step could run". That claim is false for core.alternateRefsCommand. When the repository has
objects/info/alternates, Git's fetch negotiation runs that command from the repository's configuration.
git_process's isolated profile keeps repository-local configuration authoritative (git_process.py line 3), and
neither core.hooksPath nor core.fsmonitor on the command line affects it.

Reproduced here with git 2.43.0 through the provisioner's own git() and repository_commands():

1. Repository `repo` has objects/info/alternates pointing at another repository's objects and
   `core.alternateRefsCommand = touch <tmp>/RAN; true` in .git/config.
2. repository_commands(repo) returns [], so prepare's refuse_commands passes.
3. git(repo, fetch, -q, no-tags, <clone>, +HEAD:refs/veldo/adoption/x), the exact call lay_scaffold makes
   at line 183, creates <tmp>/RAN.

So prepare runs a command that the adopted repository's configuration chose, before the owner is asked. The
merge with ff-only is clean as fixed (the B4 claim in the brief holds for that step).

Fix: refuse core.alternateRefsCommand too, and refuse a repository with objects/info/alternates at prepare
and in the effect's checks. Better still, judge an allowlist of configuration sections for local steps rather
than a list of known command keys. Add a case to adoption/repository-commands and a mutation.

### R3 (low): B1 is closed for the listed checks, but three side-effect-free refusals still come after the push

File: engine/.veldo/control_effect_executor_adoption.py:226-227 (advance and push) come before :234
(configure_identities), :257 (bind_repositories) and the signer's generation check
(engine/.veldo/control_repository.py:410).

All three refusals are knowable from the store before anything moves:
- GI.configure_identities refuses binding_mismatch:repository_identity_path or
  binding_mismatch:repository_identity_change.
- S.bind_repositories refuses repository_binding_conflict.
- The signer refuses signature_refused:scope:generation for a configured generation below the store's.

GI.configure_identities already offers check_only=True for this purpose.

Concrete scenario: the spec's rollback leaves adopted repositories "for the owner to remove by hand". The
owner removes a repository's record and its binding file, but its row in git_identity_repositories stays,
because those rows are immutable. The owner then adopts the same path under a new repository id. prepare and
every pre-push check pass. The default branch is fast-forwarded and the scaffold commit is pushed to the
remote. Then configure_identities refuses binding_mismatch:repository_identity_path, and the record ends
`failed` with a commit already on the remote.

Fix: before P.advance, call configure_identities with check_only=True, compare S.bound_repository for the id
and the path, and check the configured generation against R.store_generation. Add a case to
adoption/signer-enrolled (or a new row) with a mutation that moves them back.

### R4 (low): an interrupted effect leaves its record provisioning forever

File: engine/.veldo/control_effect_executor_adoption.py:184-190 (an existing record refuses
stale_subject:already_adopted) with control_service.py take_on (it skips `provisioning` without enrollment).

B3 ends every exception in `failed`, but not a process that ends without one. Concrete scenario: the host
reboots, or the effect is killed, during the push. The record stays `provisioning` at step `scaffold` with no
enrollment, and the scaffold commit may already be on the remote. If the effect is run again for the same
settled request, it refuses stale_subject:already_adopted before it touches the record. The service skips the
record because it has no enrollment. Nothing ever names its reason, contrary to the error taxonomy's "a
repository left failed names its reason" and the docstring's "no record is left provisioning".

Fix: when the effect runs again for the same request and finds a `provisioning` record without enrollment
that no live effect holds, write the record failed with unknown_outcome:interrupted at its step (and remove
the scaffold ref). An idempotent resume is the other option. Add a row that writes such a record and runs the
effect again.

## 1. The round 2 findings

| Finding | Judgment |
| --- | --- |
| A, agent contacts | Fixed. Every ssh-keygen in control_repository and the effect's journal signer runs with _quiet_env; the suite's own key generation and sign_as strip both variables. adoption161-signer-agent killed here. |
| B1, checks before push | Fixed for the listed checks: scaffold, configured remote, repository commands, existing binding, host trust and signer enrolled all run before advance and push, and enrolled() returns False for a missing or unloadable key. Not complete: see R3. |
| B2, active before served | Fixed. _take_on writes `active` first, then sets self.repositories. A failed write unlinks a receiver configuration it created and serves nothing. Killed (served-before-write). |
| B3, unknown_outcome | Fixed within the steps: every exception from remote to enrolled ends `failed` with _code(). push_unconfirmed:remote is separate from push_refused:remote. Not closed for the hand-off (R1, scenario 2) or for an interrupted process (R4). |
| B4, repository commands in the merge | Fixed for the merge with ff-only: core.fsmonitor is off on the command line, and a filter or fsmonitor is refused at prepare, in the checks and again just before the merge. Not closed for the prepare fetch: see R2. |
| B5, rows with no teeth | Fixed. Each listed fix has a row and at least one mutation (37 adoption cases and 3 setup cases). Round 3's falsifiers.json shows every adoption case red on its target, with the worker exiting 0 over 69 rows. I re-ran 7 of them (below). |
| B6, no polling | Fixed as designed. The watermark poll and the 50 ms wait are gone. The take_on packet is signed in its own namespace with the journal key and verified only under it. The answer is synchronous, and the start-time reconcile stays. The design leaves a gap when a hand-off is lost: R1. |
| B7, restart judgment | Fixed. An `active` record is judged on the settlement it names, the journaled signature (repository, request, digest), the binding and the store binding, never current membership. A receiver configuration that differs is rewritten (temporary file then replace), and an installed one or a symlink is refused. Killed (active-rejudged-membership, receiver-not-regenerated). |
| B8, signer pins | Fixed. host_identity, authority_generation and generation not below store_generation are pinned. Three mutations killed in round 3. |
| B9, retry | Fixed. adoption_faults is per record. take_on_record refuses retry_pending before the record's own time, and the serve loop's select waits on adoption_due(). Killed (retry-reset). |
| B10, prepare | Fixed. The remote must be the one configured for the branch, the repository id must be one ref component (no slash, no `..`, no `.lock` end), and the scaffold ref is removed after a push or a refusal, including a refusal during prepare. |

## 2. Round 3

Suite 73: specification AC1 says "The adoption signer is a service key setup enrolls among the host's
enrollment signers", so the row is right to expect it. setup/lays-down now compares the whole signers file,
line by line, with exactly two entries: the owner with the owner's key, and adoption-signer with the key derived
from keys/adoption-signer, both in veldo-enrollment. It also requires the two keys to differ and adds the
adoption key to the 0600 check. A missing, wrong or extra signer changes the list, so the row fails. I re-ran
probe_setup_signers.py and got the same result as setup-signers.json: the round-3 comparison is true for setup
as it is and false for each of the three mutants' texts, and the round-0 comparison is false. The three setup161
mutations' old text exists in control_factory_setup.py (lines 344 and 544).

adoption/signer-no-agent: AgentWatch patches AdoptionSigner.sign on all three module copies that can sign: the
suite's R, the effect's AD.R and the provisioner's PR.R. AdoptionSigner.signer's closure calls self.sign, so
every adoption signature, the effect's included, runs with the row's SSH_AUTH_SOCK and SSH_AGENT_PID and with
a recording ssh-keygen first on PATH. The suite runs no effect as a subprocess, and the separate service
process never signs adoptions. The row is judged after every other row has run.

The fence is not weakened. It wraps Git, the credential helper and in-process sockets, not ssh-keygen. Its
protected list still holds the real agent. Outside a watched sign every process keeps the fence's own agent
variable.

The mutation (env=dict(os.environ) in sign) turns the row red here (worker exit 0, 69 rows, no other new
failure). On the host it should connect to the row's socket, not the fence's, so no driver_error is expected.
That is the host's to confirm.

One weakness, not a defect: the relation `watch.signed >= max(2, len(signatures))` counts refused calls
too, so it does not by itself prove that every journaled signature was made under the watch, which is what
round3/README.md claims. A signature made outside the watch would still reach the fence's agent on the host.
Comparing the stand-in's `-Y sign` records for the adoption key with the journaled count would make the claim
exact.

## 3. Security, crash windows and races in the range

- Who can hand a record over: a peer with this uid (SO_PEERCRED) and a request signed with the service's
  journal key in veldo-adoption-take-on. verify() dispatches on the same command object that apply() later
  judges, so a keyring signature cannot carry a take_on and a journal-key take_on cannot carry anything else.
  The workspace must resolve through a binding that verifies under the enrollment signers.
- Replay and forgery: a replayed packet only causes the record to be judged again, and is idempotent (an
  already served repository answers ok). A forged record needs journal writes, which the threat model
  trusts. take_on_request also requires repository_uuid to equal the workspace's coordinate and the request
  to equal the record's.
- Effect and service races: the service is single threaded, and the effect writes `enrolled` only after
  binding, so the two never write the same record at once. The remaining windows are R1 (start-up and lost
  hand-off) and R4 (interrupted effect).
- Service crash between writing the receiver file and the `active` write: the start-time take_on() at the
  next start finds the same file with the same text and continues. This is sound.

## 4. What I ran here (the sandbox refuses AF_UNIX sockets and has no user manager)

- selftest.py, suite 109_veldo_0161_adoption: 65 passed, 4 failed. The four failures are exactly the AC2 rows
  (taken-on-running, same-process, packet-accepted, not-taken-on-named), each detailed "AF_UNIX sockets are
  refused on this host". signer-no-agent passed, and there was no HermeticViolation. Exit 1 (a partial run
  never exits 0).
- run_falsifiers.py for adoption161-signer-agent, -take-on-unauthenticated, -retry-reset,
  -active-rejudged-membership, -push-before-checks, -served-before-write and -fsmonitor-on: each target row
  red, worker exit 0, 69 rows. The baseline before and after was the same four AC2 rows.
- selftest.py, suite 73_veldo_0139_factory_setup: 27 passed, 16 failed, all with
  unavailable_service:profile:user_manager. setup/lays-down is red at baseline here. Exit 1.
- probe_setup_signers.py: exit 0, output identical to round3/setup-signers.json apart from digests.
- Suites 66_veldo_0047_authority (27 passed, 0 failed, exit 2) and 46_veldo_0029_enrollment (33 passed,
  0 failed, exit 2). Suite 86_veldo_0189_engine_upgrade: 26 passed, 33 failed, all on the user manager. Exit 1.
- check_template_sync.sh: pass, exit 0.
- Could not run (each stopped at socket creation, PermissionError, exit 1): 103_veldo_0142_git_identities,
  107_veldo_0153_identity_push, 58_veldo_0028_effects and 47_veldo_0107_ipc.
- Not run: the AC2 rows, adoption161-restart-take-on, the three setup161 cases on a real setup,
  85_veldo_0171_setup_api, 91_veldo_0167_setup_records, 106_veldo_0185_dispatch_setup, the full mutation
  driver and scripts/verify.sh. These are the host's.
