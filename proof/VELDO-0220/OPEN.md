# VELDO-0220 owner decision

REMAINING: the canonical gate cannot pass the host-scope/own-scope row while the
sandbox blocks the systemd user bus. The owner has already been asked. This round
does not change the spec or the protected scripts/gate_unconfined.json.

The exact proposed object to append to the `suites` array is:

```json
{
  "suite": "113_veldo_0220_gate_host",
  "rows": "userbus",
  "reason": "systemd user manager: the gate's own scope is created through the user manager and inspected under /sys/fs/cgroup"
}
```

The owner must authorize the protected path and update the spec's footprint and
protected paths, then apply the entry and run the canonical gate. The row tag
covers both scope creation and the scope teardown checks added in round 2.
It also allows the corresponding mutation baselines to reach the user bus.

The original independent review remains NOT SOUND. Round 2 needs a fresh
independent review of the final commit as well as the owner's green canonical
gate before landing. Targeted green results below are not canonical gate proof.

See [README.md](README.md) for the changes and [round2](round2/) for red and green
records. The owner boundary check in round2/documents.py compares both protected
inputs with a0760882 and verifies this exact proposed object.
