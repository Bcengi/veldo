#!/usr/bin/env python3
"""The request Telegram doorbell (W4 of PLAN-0016): a concise notice + a link on a new or
updated human touchpoint - a SIGNAL only, never the decision surface.

When a veldo.request/v1 touchpoint opens or changes, the responsible person gets a short nudge
on a chat channel (a Telegram bot) with a link to the tracker Decision issue: "there is
something for you, here is where to decide." The decision itself is ALWAYS made and recorded
in the tracker (the W3 projection is the ticket a human reads and decides on); Telegram is a
DOORBELL, not the decision surface. So this module deliberately builds only an outbound notice:
there is NO path here that reads a reply as a decision, no approve/decide action rides the
notice, and nothing is written back onto the request. It reads the record READ-ONLY.

Four disciplines, each mirrored from a shipped sibling so this is a composition, not a new
mechanism:

  SIGNAL ONLY. build_notice turns a veldo.request/v1 into a concise notice - a title, the tier,
  a one-line what, and the tracker link from record.tracker - and nothing that captures a
  decision. A request with no tracker link yet is SKIPPED (nothing to link to), not errored.

  SEND INJECTED, REFERENCE-WIRED, FAIL-SAFE. The send is an INJECTED sink seam (passed in),
  exactly like the live tracker adapter is injected into the W3 projection: the gate drives a
  deterministic FakeSink with no network, and the real Telegram send (TelegramSink) is
  reference-wired - a secret-reference bot token resolved at the seam, failing closed with no
  token - and is NEVER run in the gate. A send failure is CAUGHT by ring and reported, NEVER
  raised into the caller: a doorbell that cannot deliver must not block or advance a request.

  IDEMPOTENT per (request_id, status). notice_key is (request_id, status), and the sink is
  keyed-idempotent like FakeTracker.comment (a keyed send delivers at most once per key). A
  chat channel gives NO read-back (the Telegram Bot API exposes no history), so the delivery
  channel owns the "already rung" marker keyed by the request+status - a re-run or a
  re-projection at the same status is suppressed, a genuine status change is a new key and
  rings again. No second offset ledger (the reconciler posture).

  REDACTED (RULE #3). The notice text passes through the W3 redactor before it is returned, so
  no secret reference (env:/keychain:) and no org-declared operating datum reaches the chat
  channel. redact / _safe are REUSED from .veldo/request_projection.py, never re-implemented,
  so the doorbell scrubs with the same declared-scope, fail-closed discipline as the ticket:
  the tracker link is dropped fail-closed if it cannot be cleaned (then the request is skipped).

Pure stdlib, no network, no third-party imports on the gate path. request_projection.py (W3)
owns the redactor; request.py (W2) owns the record it reads; this is the sibling that rings
the bell.

  python3 .veldo/request_doorbell.py selfcheck   # drive a fixture request over the fake sink
"""
import argparse
import importlib.util
import json
import sys
from pathlib import Path

_HERE = Path(__file__).resolve().parent


def _load(name, rel):
    """Load a sibling module by path, the codebase convention (no reimplementation, one parser)."""
    spec = importlib.util.spec_from_file_location(name, _HERE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


# The W3 redactor, REUSED not re-implemented: redact masks secret references (env:/keychain:)
# and declared operating terms; _safe drops a value fail-closed on any doubt. The doorbell is a
# sibling of the projection and shares its one scrub, so a notice cannot leak what a ticket cannot.
_RP = _load("veldo_request_projection_for_doorbell", "request_projection.py")
redact = _RP.redact
_safe = _RP._safe
REDACTION_MARKER = _RP.REDACTION_MARKER


class DoorbellError(ValueError):
    """A doorbell was MISCONFIGURED (a live sink with no bot token resolved) - raised by name on
    the reference path, never a silent no-op (parallels ProjectionError / MirrorError). A SEND
    failure is NOT a DoorbellError: it is caught by ring and reported, never raised (fail-safe)."""


def _is_str(v):
    return isinstance(v, str) and v.strip() != ""


# The one-line "what" per touchpoint - what the person is being nudged about, in plain words. An
# unknown touchpoint falls back to a generic line (build_notice never fabricates a specific claim).
_TOUCHPOINT_WHAT = {
    "spec_approval": "A spec is awaiting your approval.",
    "plan_approval": "A plan is awaiting your approval.",
    "decision_choice": "A foundational decision needs to be made.",
    "review_disposition": "A review disposition is awaiting you.",
    "risky_action_authorization": "A risky action needs your authorization.",
    "escalation": "An item has been escalated to you.",
}


def _what(touchpoint):
    return _TOUCHPOINT_WHAT.get(touchpoint, "A human touchpoint needs your attention.")


def _label(touchpoint):
    return touchpoint.replace("_", " ") if isinstance(touchpoint, str) else str(touchpoint)


def notice_key(record):
    """The idempotency key: ONE notice per (request_id, status). A re-run at the SAME status is
    suppressed by the sink's keyed marker; a genuine status change is a NEW key and rings again."""
    return "%s:%s" % (record.get("id"), record.get("status"))


def build_notice(record, terms=()):
    """PURE. Turn a veldo.request/v1 into a concise doorbell notice (title + tier + one-line what
    + the tracker link from record.tracker) and the link, or (None, None) when the request has no
    tracker link yet (nothing to link to -> the caller SKIPS it, not an error).

    SIGNAL ONLY: the notice points at the tracker where the decision is made and recorded; it
    carries NO approve/decide action, and this module never reads a reply as a decision. The link
    is _safe'd (dropped fail-closed if it cannot be cleaned, which skips the request), and the
    WHOLE notice is redacted before it is returned (the W3 redactor reused), so the string is safe
    to emit onto the chat channel. Reads the record read-only; writes nothing back."""
    tracker = record.get("tracker")
    url = tracker.get("url") if isinstance(tracker, dict) else None
    link = _safe(url, terms)
    if not link:
        return None, None
    ba = record.get("bound_artifact") or {}
    body = "\n".join([
        "[Doorbell] %s: a decision is needed" % _label(record.get("touchpoint")),
        "Request %s | Tier %s | Status %s" % (record.get("id"), record.get("tier"), record.get("status")),
        _what(record.get("touchpoint")),
        "Bound: %s %s" % (ba.get("kind"), ba.get("ref")),
        "Decide in the tracker (the decision is made and recorded there): %s" % link,
    ])
    return redact(body, terms), link


def ring(record, sink, terms=()):
    """Ring the doorbell for ONE request over the INJECTED sink. SIGNAL ONLY and FAIL-SAFE.

    It builds the redacted notice, and hands it to the sink KEYED by (request_id, status) so the
    same request at the same status delivers AT MOST ONCE (a status change rings again). A
    delivery failure is CAUGHT and reported, NEVER raised into the caller - a doorbell that cannot
    deliver must not block or advance a request. Reads the record read-only; writes nothing back.

    Returns a result dict a stranger can read: the request id, the status, the outcome
    (notified | suppressed | skipped | failed), the link, and any error."""
    rid = record.get("id")
    status = record.get("status")
    text, link = build_notice(record, terms)
    if link is None:
        return {"request": rid, "status": status, "outcome": "skipped",
                "reason": "no tracker link yet (nothing to link to)", "link": None}
    key = notice_key(record)
    try:
        delivered = sink.send(text, link, key=key)
    except Exception as exc:
        return {"request": rid, "status": status, "outcome": "failed",
                "error": "%s" % exc, "link": link}
    return {"request": rid, "status": status, "link": link,
            "outcome": "notified" if delivered else "suppressed"}


def ring_all(records, sink, terms=()):
    """Ring the doorbell for each request in turn over the ONE injected sink. One-way and fail-safe
    end to end: a record that is not a mapping or carries no id is skipped, and one request's
    delivery failure never stops the rest. Returns the per-request results and a compact tally."""
    results = []
    for record in records:
        if not isinstance(record, dict) or not _is_str(record.get("id")):
            continue
        results.append(ring(record, sink, terms))
    tally = {"notified": 0, "suppressed": 0, "skipped": 0, "failed": 0}
    for r in results:
        tally[r["outcome"]] = tally.get(r["outcome"], 0) + 1
    return {"results": results, "tally": tally}


# --- the sinks: a deterministic fake for the gate, a reference Telegram send never gate-run -----
class FakeSink:
    """Deterministic in-memory doorbell sink for the gate (no network). Models the delivery channel
    AND its keyed idempotency marker: because the channel gives no read-back, the "already rung"
    memory is the sink's own, keyed like FakeTracker.comment - a KEYED send delivers AT MOST ONCE
    per key (a repeat returns False, no delivery), a keyless send always delivers. Records every
    delivered notice so a test can read exactly what fired."""

    def __init__(self):
        self.sent = []
        self._keys = set()

    def send(self, text, link, key=None):
        if key is not None and key in self._keys:
            return False
        self.sent.append({"text": text, "link": link, "key": key})
        if key is not None:
            self._keys.add(key)
        return True


class FailingSink:
    """A sink whose delivery ALWAYS fails (models a network/API error). Proves the doorbell's
    fail-safe: ring catches the error and reports it, never raising into the caller. It records the
    attempt but marks nothing delivered, so a later retry can still succeed."""

    def __init__(self):
        self.attempts = 0

    def send(self, text, link, key=None):
        self.attempts += 1
        raise RuntimeError("doorbell delivery failed (reference: no network in the gate)")


def _resolve_secret_ref(token_ref):
    """Resolve a token from its secret reference (env:NAME) via the SHIPPED tracker resolver,
    loaded lazily so the gate - which never constructs the live sink - never imports it. Reuses
    tracker_intake._default_secret_resolver, never a second implementation of the convention."""
    ti = _load("veldo_tracker_intake_for_doorbell", "tracker_intake.py")
    return ti._default_secret_resolver(token_ref)


class TelegramSink:
    """REFERENCE-WIRED real send, NEVER run in the gate. Posts the doorbell notice to a chat channel
    (a Telegram bot) via stdlib urllib. The bot token is a SECRET REFERENCE resolved at the seam
    (token_ref, e.g. env:TELEGRAM_BOT_TOKEN), never a raw credential in a config, prompt, proof, or
    log; it FAILS CLOSED (DoorbellError) when no token resolves. The chat channel gives no
    read-back, so idempotency is the caller's key plus a DURABLE keyed marker the adopter wires;
    this reference keeps no marker of its own (it always attempts a send), so it is paired with a
    durable keyed store or driven only by the reconciler. A real chat needs a live network, so this
    path is reference-wired and the FakeSink is what runs in the gate."""

    def __init__(self, chat_id, token_ref, resolve_secret=None):
        self._chat_id = chat_id
        resolver = resolve_secret or _resolve_secret_ref
        self._token = resolver(token_ref)
        if not self._token:
            raise DoorbellError("no bot token resolved from %r (set the secret, never inline it)" % token_ref)

    def send(self, text, link, key=None):
        import urllib.request
        message = text if (link and link in text) else ("%s\n%s" % (text, link) if link else text)
        payload = json.dumps({"chat_id": self._chat_id, "text": message,
                              "disable_web_page_preview": True}).encode()
        req = urllib.request.Request(
            "https://api.telegram.org/bot%s/sendMessage" % self._token, data=payload, method="POST")
        req.add_header("Content-Type", "application/json")
        with urllib.request.urlopen(req, timeout=30) as resp:
            resp.read()
        return True


def selfcheck():
    """Drive a fixture request through the doorbell over the FakeSink offline and report (exit 0/1).
    A human smoke test; the authoritative proof is the selftest block in scripts/selftest.py."""
    checks = []

    def check(name, ok):
        checks.append({"name": name, "ok": bool(ok)})

    rec = {"schema": "veldo.request/v1", "id": "REQ-1", "version": 1, "touchpoint": "spec_approval",
           "tier": "standard", "status": "needs_decision",
           "bound_artifact": {"kind": "approval", "ref": "proof/X/approval.json", "digest": "sha256:abcd"},
           "tracker": {"issue": "VEL-1", "url": "https://tracker.example/browse/VEL-1"}}
    sink = FakeSink()
    r1 = ring(rec, sink)
    check("a new request rings once with the tier and the tracker link",
          r1["outcome"] == "notified" and len(sink.sent) == 1
          and "Tier standard" in sink.sent[0]["text"]
          and sink.sent[0]["link"] == "https://tracker.example/browse/VEL-1")
    r2 = ring(rec, sink)
    check("the same request at the same status does NOT ring again (idempotent)",
          r2["outcome"] == "suppressed" and len(sink.sent) == 1)
    r3 = ring(dict(rec, status="changes_requested"), sink)
    check("a genuine status change rings again", r3["outcome"] == "notified" and len(sink.sent) == 2)
    fr = ring(rec, FailingSink())
    check("a send failure is swallowed (never raised) and reported",
          fr["outcome"] == "failed" and "error" in fr)
    passed = all(c["ok"] for c in checks)
    print(json.dumps({"passed": passed, "checks": checks}, indent=2))
    return 0 if passed else 1


def main(argv=None):
    ap = argparse.ArgumentParser(
        description="request Telegram doorbell: a signal-only notice + link, injected send, idempotent, redacted")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("selfcheck", help="drive a fixture request through the doorbell over the fake sink")
    args = ap.parse_args(list(argv) if argv is not None else None)
    if args.cmd == "selfcheck":
        return selfcheck()
    return 2


if __name__ == "__main__":
    sys.exit(main())
