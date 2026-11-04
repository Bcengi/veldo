# VELDO-0234: open items

## A. For the owner: suite 127 on the unconfined list (protected path)

Fix round 1 (2026-11-04): the entry below is now added to `scripts/gate_unconfined.json` on this branch, after the
lead widened the footprint (spec History, d18d1d4c) and the review ruled it the right home
(`proof/VELDO-0235/review-2026-11-04.md`, ruling (a)). The file is protected: the owner approves the entry at
landing. After it lands, the coordinator is re-run on finding 234 at the branch tip.

Suite `127_veldo_0234_https_port` runs VELDO-0171's installed-host fixture, as suites 85 and 117 do, and needs the
systemd user manager: inside the gate's confinement factory setup refuses `unavailable_service:profile:user_manager`,
so the mutation coordinator's confined leg runs every case's baseline red (`mutations/*.txt`). The list
`scripts/gate_unconfined.json` is protected. Entry:

```json
 {"suite": "127_veldo_0234_https_port", "reason": "systemd user manager: factory setup installs the authority and API user services on the host VELDO-0171's fixture installs, and refuses a profile without the user manager"}
```

Until it lands the falsifiers are proven by the teeth driver's own worker outside the confinement
(`falsifiers.py`, `falsifiers.json`). Once it lands, rerun the coordinator on finding 234.

## B. Every AC was met inside the footprint

No extra path was needed.
