# Security policy

## Reporting a vulnerability

**Please do not open a public issue for a security problem.** Use GitHub's private vulnerability
reporting on this repository: **Security** tab, then **Report a vulnerability**. That channel is
private between you and the maintainers, and it lets us prepare a fix before the problem is public.

Tell us what you can of the following. A partial report is worth sending; do not wait until you have
all of it.

- What the weakness is, and what an attacker gets from it.
- The smallest way to reproduce it, ideally against a scratch repository rather than one you care
  about.
- Which version or commit you saw it on.

You will get an acknowledgement within three working days. If you do not, assume the report did not
arrive and say so publicly in a way that does not disclose the detail: open an issue saying only that
you sent a security report and had no reply.

## What is in scope

This project's threat model is unusual and worth stating, because it decides what counts as a
vulnerability here.

**The gate is the thing being protected.** Its whole purpose is to refuse a change that has not been
proven, so anything that lets a change reach the trunk while LOOKING proven is a security problem,
not a bug. That includes:

- Making the gate report green without every declared check actually running.
- Producing, forging or reusing a proof or verdict that a change did not earn, including binding a
  record to a different commit than the one it reviewed.
- Getting a protected path changed without the recorded human approval the policy requires.
- Escaping the guard on a push: any route that lands a commit whose HEAD has no passing,
  commit-bound verdict.
- Making a check pass vacuously - one that reports success because it looked at nothing.

**Also in scope:** anything in the engine that executes untrusted input, reads outside the
repository it is invoked in, or exfiltrates data; and any secret recoverable from what this
repository publishes.

## What is not in scope

- A repository that has deliberately disabled its own gate. The method is not a defence against its
  owner switching it off.
- Findings that require an attacker who already has commit rights AND the ability to approve their
  own work. Self-separation is enforced structurally where the policy declares it; a single actor
  holding every role is outside the model.
- The illustrative examples shipped under any `examples/` directory. They act against deliberately
  fake systems and are documented as such.
- Reports produced by a scanner with no analysis attached. Tell us what the finding means here.

## Disclosure

We will agree a disclosure date with you, and we would rather it were soon. If a fix is going to take
longer than 90 days we will say why, and you are free to publish at that point regardless. Credit is
yours unless you ask otherwise.
