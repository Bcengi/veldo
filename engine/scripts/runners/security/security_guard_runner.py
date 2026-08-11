#!/usr/bin/env python3
"""VELDO security-guard runner (reference).

Sends a corpus of known-hostile and known-benign inputs at a set of security
guard predicates and proves that every hostile input is BLOCKED and every benign
input is ALLOWED. A guard is only as good as the attacks it actually stops, so a
happy-path unit test that never feeds it a real attack string is no proof. This
runner drives the guard with the attacks themselves (an internal SSRF target, a
path-traversal escape, a leaked credential) and fails the run naming any hostile
input the guard let through. An input the guard should have blocked but allowed
is a SECURITY BYPASS: the worst kind of silent green.

  security_guard_runner.py <fixture.json>

The fixture is a JSON list of cases. A case:

  {
    "name": "cloud metadata endpoint",     # optional label
    "guard": "is_ssrf_target",             # which guard predicate to apply
    "input": "http://169.254.169.254/",    # the input handed to the guard
    "label": "block",                      # the REQUIRED verdict: block | allow
    "config": {}                           # optional per-guard configuration
  }

The label is the required verdict and the corpus is the source of truth: a case
labeled "block" is a hostile input the guard MUST reject, a case labeled "allow"
is a benign input the guard MUST permit. The runner applies the named guard to
the input and compares the guard's verdict to the label. A hostile input the
guard allows is a SECURITY BYPASS (the dangerous failure); a benign input the
guard blocks is a FALSE POSITIVE (a usability failure). Either disagreement fails
the case and names it. Exit 0 = every case matched its label; exit 1 = at least
one did not, with the offending input and the direction of the failure on stdout.

The guard predicates are pure functions (input, config) -> (blocked, reason)
with no I/O, so the control logic is driven over the fixtures in
scripts/selftest.py with no network, filesystem, or external dependency. The
three reference guards:

  is_ssrf_target     blocks a URL or host that targets an internal, loopback,
                     link-local (including the 169.254.169.254 cloud metadata
                     endpoint), private, or otherwise non-global address, and any
                     non-http(s) scheme (file:, gopher:, dict:, and the like)
  is_path_traversal  blocks a path that escapes an allowed root, whether by a
                     .. traversal (../../etc/passwd) or by an absolute path
                     pointing outside the root (/etc/passwd)
  is_secret_leak     blocks text carrying a recognizable credential: an AWS-style
                     access key, a Google API key, a GitHub or Slack token, a JWT,
                     a bearer token, or a PEM private-key header

These are reference implementations an adopting repo wires to its own gate slot
and extends with its own corpus and patterns; the config seam (an SSRF host
allowlist, a path root, a replacement pattern set) is how a repo adapts them. The
reference guards deliberately do no DNS resolution: DNS rebinding and
resolve-then-connect races are a production concern documented in the README and
are out of scope for a deterministic, stdlib-only reference.
"""
import ipaddress
import json
import os
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit


# guard 1: SSRF target detection

_INTERNAL_HOSTNAMES = {
    "localhost", "localhost.localdomain", "ip6-localhost", "ip6-loopback",
    "metadata", "metadata.google.internal",
}
_INTERNAL_SUFFIXES = (".localhost", ".local", ".internal", ".localdomain")
_ALLOWED_SCHEMES = {"http", "https"}


def _host_from(value):
    """Split a URL or bare host into (scheme, host). scheme is None when the
    input carries no scheme. host is None when the input is a scheme-only opaque
    URI (file:/etc/passwd) that names no host."""
    v = value.strip()
    # full URL with an authority component
    if "://" in v:
        parts = urlsplit(v)
        return (parts.scheme.lower() or None), (parts.hostname or None)
    # scheme:opaque form without an authority (file:/x, javascript:x, data:x),
    # distinguished from a bare host:port where the part after the colon is a port
    m = re.match(r"^([a-zA-Z][a-zA-Z0-9+.\-]*):(.*)$", v)
    if m and not m.group(2).isdigit():
        return m.group(1).lower(), None
    # bare host, optionally host:port and/or /path
    host = v.split("/", 1)[0]
    if host.startswith("["):  # bracketed IPv6, optionally with :port
        end = host.find("]")
        if end != -1:
            host = host[1:end]
    elif host.count(":") == 1:  # host:port (a single colon, so not bare IPv6)
        host = host.rsplit(":", 1)[0]
    return None, (host or None)


def _ip_class(ip):
    if ip.is_loopback:
        return "loopback"
    if ip.is_link_local:
        return "link-local"
    if ip.is_private:
        return "private"
    if ip.is_reserved:
        return "reserved"
    if ip.is_unspecified:
        return "unspecified"
    if ip.is_multicast:
        return "multicast"
    return "non-global"


def is_ssrf_target(value, config=None):
    """A URL or host is an SSRF target when its scheme is not http(s) or its host
    is a non-global address (loopback, link-local, private, reserved). An IP
    literal is classified with ipaddress; a bare hostname is blocked when it names
    a known-internal host and otherwise treated as public (a production guard also
    resolves DNS and re-checks). config.allow_hosts is an explicit allowlist a
    repo may set to permit one named internal host; a host on it is not blocked,
    which is exactly the kind of config hole this runner's fixture proves it
    catches when a corpus entry insists that host must stay blocked."""
    config = config or {}
    if not isinstance(value, str) or not value.strip():
        return True, "empty or non-string target is not a safe URL"
    scheme, host = _host_from(value)
    if scheme is not None and scheme not in _ALLOWED_SCHEMES:
        return True, f"non-http scheme {scheme!r} is not allowed"
    if host is None:
        return True, "no host could be parsed from the target"
    host = host.strip().rstrip(".").lower()
    allow_hosts = {h.lower() for h in config.get("allow_hosts", [])}
    if host in allow_hosts:
        return False, f"host {host!r} is on the explicit allowlist"
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        if host in _INTERNAL_HOSTNAMES or host.endswith(_INTERNAL_SUFFIXES):
            return True, f"internal hostname {host!r}"
        return False, f"public hostname {host!r}"
    if not ip.is_global:
        return True, f"non-global address {host!r} ({_ip_class(ip)})"
    return False, f"global address {host!r}"


# guard 2: path traversal detection

DEFAULT_ROOT = "/srv/app/data"


def is_path_traversal(value, config=None):
    """A path is a traversal when, resolved against the allowed root, it lands
    outside that root: a .. escape (../../etc/passwd) or an absolute path pointing
    elsewhere (/etc/passwd). The check is lexical (normpath, no filesystem
    access) so it is deterministic; config.allowed_root sets the sandbox root."""
    config = config or {}
    if not isinstance(value, str) or value == "":
        return True, "empty or non-string path"
    if "\x00" in value:
        return True, "path contains a NUL byte"
    root_norm = os.path.normpath(config.get("allowed_root", DEFAULT_ROOT))
    if os.path.isabs(value):
        candidate = os.path.normpath(value)
    else:
        candidate = os.path.normpath(os.path.join(root_norm, value))
    # inside the root iff it equals the root or sits under root + separator
    # (the trailing separator stops the /data vs /database prefix trap)
    if candidate == root_norm or candidate.startswith(root_norm + os.sep):
        return False, f"{candidate!r} stays within {root_norm!r}"
    return True, f"{value!r} escapes {root_norm!r} (resolves to {candidate!r})"


# guard 3: secret leak detection

DEFAULT_SECRET_PATTERNS = [
    ("aws-access-key", r"\b(?:AKIA|ASIA|AGPA|AIDA|AROA)[0-9A-Z]{16}\b"),
    ("google-api-key", r"\bAIza[0-9A-Za-z_\-]{35}\b"),
    ("github-token", r"\bgh[pousr]_[0-9A-Za-z]{20,}\b"),
    ("slack-token", r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b"),
    ("jwt", r"\beyJ[0-9A-Za-z_\-]{6,}\.eyJ[0-9A-Za-z_\-]{6,}\.[0-9A-Za-z_\-]{6,}\b"),
    ("bearer-token", r"(?i)\bbearer\s+[0-9A-Za-z._\-]{20,}"),
    ("pem-private-key", r"-----BEGIN (?:[A-Z0-9]+ )*PRIVATE KEY-----"),
]
_DEFAULT_COMPILED = [(name, re.compile(rx)) for name, rx in DEFAULT_SECRET_PATTERNS]


def is_secret_leak(value, config=None):
    """Text leaks a secret when it carries a recognizable credential. config may
    supply patterns=[[name, regex], ...] to REPLACE the default set (an adopting
    repo tunes what counts as a secret for its data); a replacement set that omits
    a pattern is a config hole this runner's fixture uses to prove a bypass is
    caught. The defaults match format-specific credentials, which have far fewer
    false positives than a generic high-entropy heuristic."""
    config = config or {}
    if not isinstance(value, str):
        return False, "non-string input carries no text secret"
    raw = config.get("patterns")
    if raw is None:
        patterns = _DEFAULT_COMPILED
    else:
        patterns = [(p[0], re.compile(p[1])) for p in raw]
    for name, rx in patterns:
        if rx.search(value):
            return True, f"matched secret pattern {name!r}"
    return False, "no known secret pattern matched"


# the runner

GUARDS = {
    "is_ssrf_target": is_ssrf_target,
    "is_path_traversal": is_path_traversal,
    "is_secret_leak": is_secret_leak,
}


def evaluate_case(case):
    """Apply the named guard to the input and grade the verdict against the label.
    Pure: no I/O, so the control logic is unit-testable. Returns a result dict
    whose 'kind' names the failure direction (bypass, false_positive, or
    config_error) or is None on a pass."""
    guard = case.get("guard")
    label = case.get("label")
    name = case.get("name") or f"{guard}({case.get('input')!r})"
    result = {"name": name, "guard": guard, "input": case.get("input"),
              "label": label, "passed": False, "kind": None,
              "blocked": None, "reason": None, "failure": None}
    if guard not in GUARDS:
        result["kind"] = "config_error"
        result["failure"] = f"unknown guard {guard!r} (known: {sorted(GUARDS)})"
        return result
    if label not in ("block", "allow"):
        result["kind"] = "config_error"
        result["failure"] = f"case label must be 'block' or 'allow', got {label!r}"
        return result
    if "input" not in case:
        result["kind"] = "config_error"
        result["failure"] = "case has no 'input'"
        return result
    blocked, reason = GUARDS[guard](case["input"], case.get("config"))
    result["blocked"] = blocked
    result["reason"] = reason
    expected_blocked = (label == "block")
    if blocked == expected_blocked:
        result["passed"] = True
        return result
    if expected_blocked and not blocked:
        result["kind"] = "bypass"
        result["failure"] = (
            f"SECURITY BYPASS: {guard} ALLOWED hostile input {case['input']!r} "
            f"(corpus labels it block; guard reason: {reason})")
    else:
        result["kind"] = "false_positive"
        result["failure"] = (
            f"FALSE POSITIVE: {guard} BLOCKED benign input {case['input']!r} "
            f"(corpus labels it allow; guard reason: {reason})")
    return result


def run_fixture(cases, out=None):
    """Grade every case. Returns {"passed": bool, "cases": [...]} and, when out is
    given, prints PASS/FAIL lines naming any bypass or false positive."""
    results = []
    all_passed = True
    for case in cases:
        r = evaluate_case(case)
        results.append(r)
        if out is not None:
            if r["passed"]:
                print(f"PASS  {r['name']}", file=out)
            else:
                print(f"FAIL  {r['name']}: {r['failure']}", file=out)
        if not r["passed"]:
            all_passed = False
    return {"passed": all_passed, "cases": results}


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    fixture = Path(argv[1])
    try:
        cases = json.loads(fixture.read_text())
    except Exception as e:
        print(f"cannot read fixture {fixture}: {e}")
        return 2
    if not isinstance(cases, list) or not cases:
        print(f"fixture {fixture} must be a non-empty JSON list of cases")
        return 2
    summary = run_fixture(cases, out=sys.stdout)
    total = len(summary["cases"])
    passed = sum(1 for c in summary["cases"] if c["passed"])
    bypasses = sum(1 for c in summary["cases"] if c["kind"] == "bypass")
    tail = f"; {bypasses} SECURITY BYPASS(es)" if bypasses else ""
    print(f"security guard runner: {passed}/{total} cases matched their label{tail}")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
