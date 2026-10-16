# B2 second-review delivery correction

The authority now commits release permission as `release_state=pending`. That
permission lets the configured Mac receiver durably retire its slot (or write a
pre-launch tombstone), but does not free Linux capacity. Only the dispatch-bound,
receiver-signed `worker_retired` command commits `release_state=confirmed` and
retires the Linux reservation, atomically. Reservation validation requires that
confirmation. A result, operator attestation, transport exit or replay alone
cannot free capacity. The confirmation wakes capacity waiters.

An operator release wake first drains any retained result request, including the
original measured usage, then applies retirement. A stored result acknowledgement
still requires local retirement and the signed confirmation. Retained evidence,
request, acknowledgement, retirement request and completed-delivery marker live
outside the removed clone/scratch trees. A per-dispatch file lock serializes the
normal receiver, release wake and outbox resumer.

The installed CLI installs a delivery-only LaunchAgent under the configured Mac
profile home's `Library/LaunchAgents` before accepting work. Its `--resume` entry
point runs at login and restarts on exit; it drains saved results/retirements at
startup and every 30 seconds without claiming or executing work. Result and
retirement delivery retry the same signed request until acknowledged on transport
unavailability. Backoff doubles from one second to a 300-second ceiling, with
half-to-full interval jitter, and has no attempt cap. A process restart reloads
the durable result request. Authorization and binding refusals remain refusals.
The launch agent requires the same enrolled GUI login session as the existing Mac
supervisor. This change does not install a job or change a deployed host here.

The default collector reads retained engine stdout using the existing trusted
`control_engine_codex.Meter` or `control_engine_claude.Meter`, selected from the
accepted adapter identity. It archives outputs before cleanup. Missing or
incomplete usage stays unknown; a successful OS exit never invents token counts.

The authority maintains a partial SQLite index over pending worker release
observations. Restart reads that index only; it never enumerates all historical
workers and looks up each reservation. A persistent confirmed marker removes a
dispatch from the pending index. A single sender serializes SSH wakes and a
service-lifetime set sends each pending dispatch at most once. Queued wakes are
skipped if confirmation arrives before their turn. An unconfirmed
wake can be redelivered on the next authority start. Confirmation is signed
through the authority, never inferred from SSH exit status.

## Regression rows

All rows below are in `106_veldo_0125_routing`; the command-family and signature
boundary rows in `105_veldo_0125_relay` also cover the new command.

- `AC3/stored-release-restart`: crash before Mac retirement preserves Linux
  capacity; the restarted receiver retires before confirming.
- `AC3/release-flushes-saved-usage`: a receiver crash leaves measured usage in the
  outbox; an operator release and authority database restart precede a release
  wake that reports that usage to the original invocation.
- `AC3/operator-release-after-result`: an operator release after the result was
  acknowledged still retires correctly and preserves the original measurement.
- `AC3/default-collector-retains-files`: actual default collector and Codex usage
  parser consume stream events reporting 13 input and 8 output tokens; the
  authority's reserved invocation records 21 measured tokens. The engine stream
  and Apple OS are fixtures, not a claim of a live provider or Mac execution.
- `AC3/result-retry-backoff`: 25 failed deliveries followed by acknowledgement;
  all 26 attempts carry the same request, intervals stay bounded, and ack persists.
- `AC3/startup-resumes-outbox` and `AC3/delivery-launch-agent`: startup drains a
  crash-retained request, writes completion, skips it on the next scan, and the
  installed launch-agent entry point calls that drain.
- `AC3/host-release-replay-and-restart`: pending releases survive authority
  restart; confirmed releases cause no new connection, and startup uses the
  partial index without reservation-history scans.
- `AC3/release-wakes-bounded-once`: 20 queued releases use one sender, and a second
  wake for each dispatch creates no further deliveries; confirmation while a
  wake is queued prevents that connection too.
- `AC3/release-before-start`: release with no local slot writes a durable
  tombstone; a fresh supervisor refuses the late start without bootstrapping.
- Existing late-usage, operator-release, unknown-cleanup and signed-cleanup rows
  retain their accounting checks and now drive the explicit confirmation.

## Checks and negative controls

Only the owner's allowed named suites were run. Their partial-run summaries and
the eight single-change mutant diffs/logs are retained in `b2-delivery/`.
`delivery_falsifiers.py` copies modules to a temporary directory and invokes only
`python3 scripts/selftest.py --suite 106_veldo_0125_routing`, once per mutant,
sequentially. `results.json` identifies the named row that rejects each mutation.
These are targeted regression observations, not a gate stamp, acceptance proof,
or independent approval. No full selftest, canonical gate or global mutation
checker was run. Native macOS, real SSH and live provider execution were not run.
