# VELDO-0125 B2 round 20

Starting revision: `b66a1330`. Scope: the owner's receiver-event read-error
finding and source-transport question. This is selected-suite evidence, not a
canonical gate, native Mac qualification, independent approval or landing claim.

Regression commit: `a178110b`. Implementation commit: `37b64d9d`.

## Receiver handoff

An incoming event must either be recorded or fail the receiver invocation.
`read_entry` retains its diagnostic and log-and-skip default for background drain
and recovery. Event enqueue and the receiver's non-queued read instead request
propagation of operational read errors. Errors during event acceptance bypass
delivery-failure recording: a one-shot EIO must not cause a second read to change
the old request, retry count or deadline. Once acceptance finishes, the existing
delivery failure handling applies.

The existing `main` retryable-error path lets OSError escape with a nonzero
process exit. Linux's existing release sender consequently schedules its bounded
backoff resend instead of treating the wake as handed off to the Mac.

`receiver_checks.py` adds five rows to suite 106. Four exercise a release event
against `.waiting` and `.pending`, each with persistent and one-shot EIO. They
assert an actual receiver subprocess fails, emits the read diagnostic, leaves
the old entry byte-identical in its original directory, neither parks nor delivers
it, and accepts and delivers the release on resend from a fresh process. The
fifth fails the receiver's readback after enqueue has recorded the release; it
requires a nonzero exit and preservation and eventual delivery of that event.
Only launch-agent installation and the terminal delivery endpoint are fixture
seams; event acceptance, queue persistence, exception handling and process exit
are production code. These rows do not claim a real SSH or Mac observation.

The prior round 17 EIO/EMFILE/ENFILE/EACCES drain and recovery rows are unchanged.
The new rows were first run against unchanged production code in
`106-before.log`; all five expose a zero exit with `delivery_pending`.

## Source URL question

An operator-configured SSH or HTTPS URL is not forbidden by either specification,
and the receiver passes `config['source']` directly as Git clone's source without
a local-path restriction. However, neither VELDO-0125 nor VELDO-0124 requires
remote source fetching or a source-authentication mechanism. VELDO-0124 AC1
requires an accepted clone; VELDO-0125 AC1 concerns signed commands reaching the
Linux authority through VELDO-0108, not Git transport. The configuration contract
in `proof/VELDO-0125/README.md` describes an operator-managed source mirror
containing the accepted commit. A local mirror fulfills those requirements.

Round 18's clone call in `.veldo/control_worker.py` does **not** preserve arbitrary
operator Git transport configuration. It uses `git_process.run` with its default
`isolated` profile, which strips `GIT_SSH_COMMAND`, `GIT_SSH`, `GIT_ASKPASS` and
injected Git configuration, sets global/system Git config to `/dev/null`, and
disables terminal prompting. Thus an SSH source relying on `GIT_SSH_COMMAND`, or
an HTTPS source relying on a global/system credential helper, cannot be assumed
to remain reachable. `HOME`, `SSH_AUTH_SOCK` and other non-GIT environment
variables remain, so default SSH configuration/agent authentication can still
work; anonymous HTTPS does not need a credential helper. No live remote source
was contacted in this round.

`git-source-audit.json` records the actual environment transformation with
synthetic values, including the available `network` profile for comparison.
That profile retains the named transport variables and operator configuration,
but the receiver does not select it. The subsequent detached checkout and the
Mac commit/tree/cleanliness checks are local operations and do not fetch source.
The existing signed authority relay has its own `ssh_argv` transport and is
unaffected by Git environment cleaning.

Answer: URL syntax is accepted, but credential-dependent remote sources are not
generally preserved by round 18. Remote source fetching is not required by these
specifications, so no Git behavior or source contract was changed, as requested.

## Selected-suite observations

Each command was `python3 scripts/selftest.py --suite NAME`, run one at a time.
Counts below exclude the 26 shared assertions that also passed in each run.

| Suite | Log | Suite assertions | Failures |
| --- | --- | ---: | ---: |
| 106_veldo_0125_routing, before fix | `106-before.log` | 224 passed | 5 |
| 103_veldo_0124_macos | `103-after.log` | 23 passed | 0 |
| 104_veldo_0124_control | `104-after.log` | 6 passed | 0 |
| 105_veldo_0125_relay | `105-after.log` | 17 passed | 0 |
| 106_veldo_0125_routing | `106-after.log` | 229 passed | 0 |

The before run exited 1. Each after run exited 2, the runner's deliberate
successful-partial-run status; each reports zero failures. No full selftest,
gate or mutation checker was run. Existing logs and manifests were not rewritten.
`template-sync.json` records byte identity and SHA-256 for both changed
engine/installed pairs. `results.json` binds these observations to the files
and log digests. The reviewer retains the full gate and merged-tree stamp.
