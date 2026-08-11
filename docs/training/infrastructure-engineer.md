# The Infrastructure Engineer in Veldo

*Training series. Your destination role: Platform Reliability Engineer - the person who makes the proof system fast, the deployments evidenced, and the unrecoverable approachable.*

*Version 1.0, 2026-07-16*

## 1. Your job, redefined

You were the person who could SSH in and fix it. That skill saved the company many times, and under Veldo it becomes the emergency lane only: a declared, recorded, backfilled exception, never the normal path. The normal path is that infrastructure is code in the repository, changed through specs, proven by plans and staging evidence, approved against plan digests, and observed after apply. You stop being the human deploy button and start owning three systems: the substrate everything runs on, the gate's own runtime (verification speed is your SLO), and the recovery machinery.

| What stops | What starts |
|---|---|
| Typing terraform, manifests, pipelines by hand | Specifying infrastructure intent; agents construct; you judge the plan |
| Console changes and undocumented fixes | Everything in the repo or it does not exist; console access is the emergency lane |
| Being paged to run deployments | Deployments as evidenced, observed, auto-rolled-back changes |
| Change-ticket approval rituals | Plan-digest approvals: you approve an exact plan, once, with expiry |
| Tolerating slow or flaky CI | The gate's latency and reliability as your product, with a number on it |

## 2. Your unique position: you hold the 0-to-100 lever

The founder's stated gap: zero percent of infrastructure is done this way today. You own that migration, and its first act is honesty: get every definition into the repository (the terraform that lives in a laptop folder, the config that lives in a console). What cannot be read and diffed cannot be governed. Then the floors go into policy, the plan step goes into the gate, and infrastructure becomes the MOST protected class of change instead of the least.

## 3. Your moments in the loop (exact)

**The migration's opening move (per system):**

```
/veldo:spec Import the production load balancer config into infra/ as code;
no behavior change; the plan for the import must show zero deltas against
live state.
```

**Judging a plan (your daily craft):**

```
The plan shows 1 update (autoscaling max) and 1 unexpected replace on the
launch template. The replace is not in the spec. Blocked until explained
or removed.
```

**The prepare-and-execute custody (irreversible ops):**

```
For the key rotation: produce the exact execution plan, dry-run it against
staging, and bring me the plan digest. My approval binds to that digest with
a 1-hour expiry, and execution stops on any mismatch.
```

**Gate runtime engineering:**

```
/veldo:spec Cut gate latency: cache the dependency layer in the runner image;
target under 4 minutes for ordinary changes; the full suite stays intact.
```

## 4. The curriculum

**Module I1 - Everything into the repo.** Exercise: pick one real system managed by hand today; import it as code with a zero-delta plan as the acceptance criterion. This is the migration in miniature.

**Module I2 - Plan literacy as judgment.** Exercise: three plans, one with a planted surprise (a replace hiding behind an update, a wildcard grant, a dependency on the thing being changed). Find it, every time, fast.

**Module I3 - Blast-radius prediction.** Before the agent runs, write down what the change can possibly touch; compare with the plan. Calibration is the skill; the gap is the lesson.

**Module I4 - Recovery as evidence.** A rollback that has never run is a hope. Exercise: for one production system, make "the rollback was exercised on staging" a standing criterion, then exercise it.

**Module I5 - The gate as production.** Flaky infra checks teach bypass. Exercise: find the flakiest check in CI, make it deterministic, and publish the latency number you now own.

## 5. How you break Veldo without meaning to

- **The quiet console fix.** One undocumented change and the repo is no longer the truth; every plan after it lies a little. Declared emergency or through the loop; there is no third door.
- **Everything critical.** Floor the whole infra tree at critical and you are the new bottleneck; the reversible must flow.
- **Approving directions instead of plans.** "Yes, scale it up" is not an approval; the plan digest is what you approve.
- **Letting the gate be slow.** Verification speed bounds the whole company's delivery speed; a 30-minute gate is a company-wide tax you own.

## 6. You have arrived when

- A month of infrastructure changes, all through the loop, zero console fixes.
- You caught a hidden replace in a plan that would have taken production down.
- The emergency lane got used once, worked, and the backfill closed in six hours.
- The gate is faster than it was when humans typed the code it verifies.
- The founder's "0% of infra" line is measurably false in your repos.

## Document History

| Version | Date | Changes |
|---|---|---|
| 1.0 | 2026-07-16 | Initial training document |
