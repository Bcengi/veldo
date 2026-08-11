#!/usr/bin/env python3
"""The absolute secret scan (WARP-1302, W2 of PLAN-0013).

Pattern plus entropy over every diff, every generated file and every recorded artifact. It fails
closed and **there is no allowlist mechanism at all**.

WHY NO ALLOWLIST, WHICH IS THE ONLY INTERESTING DECISION HERE. Every secret scanner in the world
ships with an exemption list, and every one of those lists rots into a tunnel: the first entry is a
test fixture, the tenth is a real credential somebody was in a hurry about, and nobody re-reads it.
The exemption exists because in a normal codebase there are legitimate reasons to hold a literal
credential-shaped string.

**W1 removed those reasons.** A secret is a reference; a literal has no legitimate place in any
file. So the exemption has nothing to be for, and the correct number of exemption mechanisms is
zero. That is only defensible BECAUSE of W1, and the refusal text says so, because a future reader
hitting a false positive needs to know why the door they are looking for was deliberately not built.

**A FALSE POSITIVE IS RESHAPED, NEVER EXEMPTED.** A hash in a fixture or a sample token in
documentation is fixed by making the artifact not look like a credential - shorten it, obviously
fake it, move it behind a reference. That costs minutes at machine prices. The alternative costs a
credential in git history, where deleting it does not remove it.

TWO DETECTORS, because each catches what the other misses. PATTERNS catch known shapes - a provider
prefix, a private key header - including high-entropy-looking strings that are not random. ENTROPY
catches the unknown provider whose format nobody has written a pattern for yet. Neither alone is
enough and the combination is deliberately noisy in the safe direction.
"""
import math
import re

SCHEMA = "veldo.secret_scan/v1"

# KNOWN SHAPES. Each is a provider format or a structural marker, not a guess.
PATTERNS = (
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----"), "an inline private key"),
    (re.compile(r"\b(sk|rk)_(live|test)_[A-Za-z0-9]{16,}"), "a Stripe-style secret key"),
    (re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}"), "a GitHub token"),
    (re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{10,}"), "a Slack token"),
    (re.compile(r"\b(AKIA|ASIA)[A-Z0-9]{16}\b"), "an AWS access key id"),
    (re.compile(r"\bAIza[A-Za-z0-9_\-]{35}\b"), "a Google API key"),
    (re.compile(r"\beyJ[A-Za-z0-9_\-]{10,}\.[A-Za-z0-9_\-]{10,}\."), "a JWT"),
    (re.compile(r"(?i)\b(password|passwd|secret|api[_-]?key|token)\s*[:=]\s*"
                r"['\"][^'\"\s]{8,}['\"]"), "a credential assigned as a literal"),
)

# ENTROPY. A long, high-entropy, unbroken token is the shape of a key nobody has a pattern for.
ENTROPY_MIN_LEN = 32
ENTROPY_THRESHOLD = 4.0
_CANDIDATE = re.compile(r"[A-Za-z0-9+/=_\-]{%d,}" % ENTROPY_MIN_LEN)

# The ONE mechanism that is not an allowlist: a token that is structurally incapable of being a
# secret because it is a hex digest of a known width. Git object ids and sha256 digests are
# everywhere in this repository's own proofs, they are derived from public content, and they are
# not credentials. This is a SHAPE rule, not a list of blessed strings, which is the difference
# that stops it rotting.
_PURE_HEX = re.compile(r"\A[a-f0-9]+\Z", re.I)
DIGEST_WIDTHS = frozenset({7, 8, 10, 12, 32, 40, 64, 128})


def shannon(s):
    if not s:
        return 0.0
    counts = {}
    for ch in s:
        counts[ch] = counts.get(ch, 0) + 1
    n = len(s)
    return -sum((c / n) * math.log2(c / n) for c in counts.values())


def _is_digest(tok):
    return bool(_PURE_HEX.match(tok)) and len(tok) in DIGEST_WIDTHS


def scan_text(text, where="<text>"):
    """Every finding in one blob, as (line, kind, why). Empty means clean.

    Line numbers are 1-based and real, because a finding an operator cannot locate is a finding
    they will disable."""
    out = []
    for i, line in enumerate(text.splitlines(), 1):
        for rx, why in PATTERNS:
            if rx.search(line):
                out.append((i, "pattern", why))
                break
        else:
            for tok in _CANDIDATE.findall(line):
                if _is_digest(tok):
                    continue
                if shannon(tok) >= ENTROPY_THRESHOLD:
                    out.append((i, "entropy",
                                "a %d-character high-entropy token (%.2f bits/char), which is the "
                                "shape of a key no pattern covers yet" % (len(tok), shannon(tok))))
                    break
    return out


def refusal(where, findings):
    """The refusal text. It states that there is no allowlist AND why, because a reader hitting a
    false positive will go looking for the exemption mechanism and needs to find the reason it
    does not exist rather than concluding the tool is broken."""
    head = "%s: %d possible secret(s) found" % (where, len(findings))
    body = ["  line %d: %s (%s)" % (ln, why, kind) for ln, kind, why in findings[:8]]
    tail = [
        "  THERE IS NO ALLOWLIST, DELIBERATELY. Secrets are references (see .veldo/secretref.py),",
        "  so a literal credential has no legitimate reason to exist in any file, so an exemption",
        "  mechanism would have nothing to be for except the case this check exists to catch.",
        "  FIX A FALSE POSITIVE BY RESHAPING THE ARTIFACT, never by exempting it: shorten the",
        "  sample, make it obviously fake, or move it behind a reference. Minutes of work, against",
        "  a credential in git history that deleting does not remove.",
    ]
    return [head] + body + tail


def scan_files(files, read=None):
    """Scan an iterable of paths. `read` is injectable so the gate can scan a diff, a generated
    artifact or a proof body without this module knowing where any of it came from."""
    reader = read or (lambda p: open(p, "r", encoding="utf-8", errors="replace").read())
    out = {}
    for p in files:
        try:
            found = scan_text(reader(p), str(p))
        except (OSError, UnicodeError):
            # UNREADABLE IS NOT CLEAN. A file the scanner cannot read is a file it cannot vouch
            # for, and passing it silently is how a binary blob becomes the hiding place.
            found = [(0, "unreadable", "could not be read, so it cannot be vouched for")]
        if found:
            out[str(p)] = found
    return out
