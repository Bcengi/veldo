# VELDO-0124 batch 2, 2026-10-15

BLOCKED on current native qualification, not shipped. This round starts at
`bb23dd41` with main `9763249e` already integrated. The catalog repair is
`c6768100`; the proof-schema and falsifier-driver repair is `eebad4f9`.
No runtime asset or acceptance criterion changed. All three criteria remain
pending. This is a development record, not independent review, activation,
approval, or a passing proof bundle.

## Repairs and round inventory

The committed conflict markers in `scripts/suites/manifest.json` were resolved
by retaining both sets of registrations, including the two 0124 suites and
main's six additions. `python3 scripts/run_scope.py --emit-requires` regenerated
`scripts/suites/requires.json`, exit 0: 164 executable suites, 165 manifest
entries including shared state. No other suite was run.

The existing proof manifest failed contract validation on exactly three rows:
missing rollback, missing unit evidence declaration, missing integration evidence
declaration. Added the rollback policy and explicit `not_run` declarations;
all criteria and evidence arrays remain pending/empty. Full unit evidence and
native integration evidence have not been manufactured from selected runs.
`batch2/contracts.log` is the red observation; `batch2/contracts-final.log` and
its `.exit` file record exit 0 after repair.

The falsifier driver now accepts `--output`, preserving older captures, and
includes the latest review's Claude sandbox check-removal case. Production files
are never mutated; each case uses a disposable module copy. Every subprocess
still selects exactly one of this specification's suites, sequentially.

There was no separately named round/review document or verdict in the supplied
`proof/VELDO-0124/` directory. The newest available follow-up is README's
"Claude settings discovery and admission", `claude-negative-control.json`, and
the 2026-10-10 spec history (commits `a5fc50ba`, `3b59a3b9`). Those and the
earlier recorded native findings were read. The table below answers the concerns
recoverable from those records; it does not invent or certify an absent review.

## Review response locations

Paths below are relative to the repository root and line numbers refer to this
round. Earlier native observations remain historical, not recaptured here.

| Recorded concern | Implementation and current check |
| --- | --- |
| Claude's nested bash sandbox, settings sources and late settings changes | `engine/.veldo/project_runner_macos_profile.py:40`, `:87`, `:133`; trusted recheck at `engine/.veldo/project_runner_macos_wrapper.py:56`. `scripts/suites/103_veldo_0124_macos.py:148`, `:176`, `:260`; pre-acceptance store refusal at `scripts/suites/104_veldo_0124_control.py:143`. Fresh check-removal mutant fails `AC1/claude-sandbox-refused`. |
| Overbroad writes, owner credentials, other account/project/dispatch reads | Deny rules at `engine/.veldo/project_runner_macos_profile.py:223`; overlap and exact rule checks at `scripts/suites/103_veldo_0124_macos.py:57`. Native access enforcement needs recapture. |
| launchd job creation, Keychain and signals to authority processes | Same policy function and exact rule checks; historical per-rule native results in `native-falsifiers.json`. This host could not exercise Apple enforcement. |
| Owner HOME/TMPDIR leaking into a worker | `engine/.veldo/project_runner_macos.py:66`, `engine/.veldo/project_runner_macos_control.py:30`; current signed-store acceptance/environment row at `scripts/suites/104_veldo_0124_control.py:89`. |
| Engine kill also kills trusted wrapper | Separate child group at `engine/.veldo/project_runner_macos_wrapper.py:85`; `AC3/hard-kill-unknown`, historical native `hard-kill`. |
| Parent exit leaves a setsid descendant | Coalition enumeration at `engine/.veldo/project_runner_macos_os.py:65`, observation/escalation at `engine/.veldo/project_runner_macos.py:267`; `scripts/suites/103_veldo_0124_macos.py:301`. Both parent-only and group-only falsifiers fail `AC3/descendant`. |
| Supervisor loss loses deadline enforcement | Wrapper backstop at `engine/.veldo/project_runner_macos_wrapper.py:106`, persisted recovery at `engine/.veldo/project_runner_macos.py:200`; `AC3/recover`, historical native `supervisor-loss`. Fresh native backstop falsifier needs the Mac. |
| Wrong interpreter or launchd session type | Profile validation at `engine/.veldo/project_runner_macos_profile.py:267`, admission at `engine/.veldo/project_runner_macos.py:84`, plist at `engine/.veldo/project_runner_macos_os.py:99`; `AC1/interpreter`, `AC1/apple-interfaces`, fresh session-type falsifier. |
| Unknown outcome releases reservation | `engine/.veldo/project_runner_macos_control.py:120`, `engine/.veldo/project_runner_macos.py:336`; `scripts/suites/104_veldo_0124_control.py:184` and fresh unknown-retirement falsifier. |
| Installed copies differ from canon | `scripts/suites/103_veldo_0124_macos.py:375` assembles all seven packs; static template sync compares repository copies. Both checks have no failures. |

## Main changes checked underneath this ticket

Compared current engine control dependencies with `a5fc50ba`. The five Mac assets
are unchanged. `batch2/source-sha256.json` records those assets, installed copies,
owning suites and the integrated control dependencies examined.

* Current account/store/reservation code is exercised by suite 104 using real
  SQLite, generated OpenSSH signatures, Git and registered accounts. Both engine
  configurations still accept only after preflight and reserve before bootstrap;
  initial, retry and follow-on caps still refuse before invocation. Unknown charge
  exposure and clone/accounting obligations still prevent retirement.
* Main's account memory exclusion and account-pool changes live upstream of this
  host profile. The Mac receiver uses the account selected in the accepted
  reservation and the supplied current-eligibility callback; it does not select
  an account independently. No role-selection or shared-memory qualification on
  macOS is inferred from these tests.
* Main added login-status checks and memory delivery to the Linux receiver in
  `control_launch.py`. This Mac receiver is a separate host seam and does not
  inherit those execution paths. It still requires its own explicit native
  profile/account qualification. The Linux receiver's VELDO-0213 prompt-write
  timing fix and the VELDO-0127 real captures cannot qualify this Mac wrapper:
  it executes pinned profile argv with closed stdin and reports an incomplete
  artifact. No successful autonomous build or provider protocol completion is
  claimed by this ticket's lifecycle fixtures.
* Current clone/identity changes are exercised to the extent used by these
  suites' real isolated Git clones and pinned source checks. Main's Linux
  authenticated clone/landing journey is not re-certified here.

## Local red/green observations

Only `python3 scripts/selftest.py --suite 103_veldo_0124_macos` and
`python3 scripts/selftest.py --suite 104_veldo_0124_control` were run, one at a
time. Each baseline and final run exited **2**, the dispatcher's intentional
PARTIAL status; this is not a green full-suite or gate claim.

| Run | Owning rows passed | Total passed | Failed | Exit |
| --- | ---: | ---: | ---: | ---: |
| 103 baseline, then final | 28 each | 54 each | 0 | 2 |
| 104 baseline, then final | 7 each | 33 each | 0 | 2 |

Logs and exit files are `batch2/suite-103-{baseline,final}.*` and
`batch2/suite-104-{baseline,final}.*`. The totals include shared prerequisite
checks. They are diagnostics only and are not cited as passed manifest evidence.

Command: `python3 proof/VELDO-0124/negative_controls.py --output proof/VELDO-0124/batch2`
exited **0**; all nine mutants exited **1** with their named failed row. The
unmutated final runs above followed these red observations. Source digests,
single-change patches, failed rows and captured logs are in
`batch2/negative-controls.json` and its referenced files.
For committed artifact hygiene, captured log line endings are normalized and
trailing whitespace removed; patch files use zero context. Observed rows and exit
statuses are unchanged. The initial whitespace-check failure is retained in
`batch2/diff-check-before-normalization.log`.

| Criterion / mutation | Named failed row |
| --- | --- |
| AC1 qualification kind ignored (declared falsifier) | `AC1/qualification` |
| AC1 launchd Background session omitted | `AC1/apple-interfaces` |
| AC1 Claude enabled-sandbox refusal removed | `AC1/claude-sandbox-refused` |
| AC2 elapsed deadline ignored (declared falsifier) | `AC2/deadline` |
| AC2 capacity ignored | `AC2/capacity` |
| AC2 launch before spend reservation | `AC2/precall-caps` |
| AC3 parent-only exit (declared falsifier) | `AC3/descendant` |
| AC3 signal only engine group | `AC3/descendant` |
| AC3 retire unknown outcome | `AC3/unknown-charge` |

Gate step list read from `scripts/verify.sh`. Static checks run directly with
each exit status captured: lint, secret inventory, generated freshness, docs,
template sync, contract validation and architecture shape. Initial results are
`batch2/static-results.json`; final results are `batch2/static-final-results.json`.
The initial contract failure is retained. Structural validity of a pending proof
manifest does not mean its pending evidence exists.

All seven final static checks exited **0**. The final shape pass required removing
this round's temporary `.local-0124/` inspection files, which it correctly rejected
as outside the declared footprint. The failed attempt remains in
`batch2/shape-final.log`; the clean retry and its exit status are in
`batch2/shape-after-cleanup.log` and `.exit`. No footprint exception was added.

The full gate, whole selftest, global mutation checkers, first-use integration
and install-and-run packaging were not run. The latter two launch broader gate
or suite checks and remain with the reviewer under the owner's run limits.
No gate stamp or events byproduct is part of this work.

## Blockers and exact host commands

`ssh -o BatchMode=yes -o ConnectTimeout=8 -o StrictHostKeyChecking=yes dmitrys-mac-mini 'uname -s; sw_vers -productVersion'`
exited **255** with a port 22 timeout (`batch2/host-access.log`). No login or
provider invocation was attempted. Neither current macOS facts nor current CLI
versions/accounts could be observed. The existing 2026-10-10 native captures
cannot be relabeled as observations of this round.

After access is restored, export this committed checkout into a dedicated probe
directory, without changing any remote branch/worktree. Run from this checkout:

```sh
set -o pipefail
git archive HEAD .veldo proof/VELDO-0124 | ssh -o BatchMode=yes dmitrys-mac-mini 'mkdir -p ~/veldo-0124-batch2 && tar -x -C ~/veldo-0124-batch2'
ssh -o BatchMode=yes dmitrys-mac-mini 'uname -s; sw_vers; /opt/homebrew/bin/python3.12 --version' > proof/VELDO-0124/batch2/native-host.log 2>&1
ssh -o BatchMode=yes dmitrys-mac-mini 'cd ~/veldo-0124-batch2 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py lifecycle' > proof/VELDO-0124/batch2/native-lifecycle.json 2>&1
ssh -o BatchMode=yes dmitrys-mac-mini 'cd ~/veldo-0124-batch2 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py containment' > proof/VELDO-0124/batch2/native-containment.json 2>&1
ssh -o BatchMode=yes dmitrys-mac-mini 'cd ~/veldo-0124-batch2 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_falsifiers.py' > proof/VELDO-0124/batch2/native-falsifiers.json 2>&1
```

Check each command's exit status directly; do not continue after a failed export.
The lifecycle/containment commands still use synthetic engines and do not satisfy
the real CLI requirement. For real CLI probes, first supply the actual pinned
binaries/configuration digests, dedicated qualified subscription profiles,
accepted contracts and genuine current reservation receipts described in
README's "What the engines check needs from the owner". This round neither
possesses those inputs nor grants consent for their six provider calls. Then:

```sh
ssh -o BatchMode=yes dmitrys-mac-mini 'cd ~/veldo-0124-batch2 && /opt/homebrew/bin/python3.12 proof/VELDO-0124/native_checks.py engines ~/veldo-0124-candidate.json' > proof/VELDO-0124/batch2/native-engines.json 2>&1
```

That existing driver covers real CLI natural/cooperative/deadline rows only.
The reviewer must also establish the criterion's real engine/descendant and
authority-write isolation observations for the actual configurations; synthetic
engine containment rows alone cannot certify them. Missing real-engine evidence
is still a blocker even if all local checks or the reviewer gate are green.
