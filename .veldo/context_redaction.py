#!/usr/bin/env python3
"""Context secret-free by construction (WARP-1303, W3 of PLAN-0013).

Everything an agent reads passes through one seam, and secrets are removed there. Not filtered out
of the transcript afterwards, not stripped from the log later: removed before the bytes become
context.

**A CONTEXT THAT NEVER HELD A SECRET CANNOT LEAK ONE**, and that is the entire argument. Once a
credential is in a model's context it is in the transcript, in whatever the model quotes back, in
any summary it writes and in the compaction that follows. There is no recall. So the only defensible
place for the removal is upstream of the boundary, which is what makes this a seam rather than a
filter.

WHAT IT REDACTS, and why the list is two things rather than one:

  **Known values.** Anything the runtime resolved through the secret seam is redacted by VALUE, so a
  credential the agent was never handed cannot arrive by a side route - quoted in a log line, echoed
  in an error, embedded in a config dump. This is the part that actually protects you, because it
  does not depend on the secret looking like anything in particular.

  **Credential shapes.** The `secret_scan` detectors, reused rather than reimplemented, for secrets
  the runtime never resolved and therefore cannot know by value: someone else's token in a log file
  the responder is reading. Best-effort by construction and declared as such.

**THE REDACTION IS LENGTH-PRESERVING IN NEITHER DIRECTION AND THAT IS DELIBERATE.** A placeholder
that preserved length would let an observer read the secret's length off the transcript, and length
is a real signal - it identifies the provider. The placeholder names the reference where one is
known, so a human reading the transcript can see WHICH secret was removed without seeing it.

**FAIL CLOSED: IF REDACTION RAISES, NOTHING IS RETURNED.** A partially redacted string is worse than
no string, because it looks scrubbed. `redact` raises rather than returning a best effort, and the
caller must decide what to do with a chunk it cannot make safe.
"""
import importlib.util
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

SCHEMA = "veldo.context_redaction/v1"

# What replaces a secret. Deliberately NOT length-preserving: a fixed-width mask would leak the
# length of the value, which identifies the provider.
def placeholder(ref=None):
    return "[REDACTED:%s]" % ref if ref else "[REDACTED]"


class RedactionError(RuntimeError):
    """Raised when a chunk cannot be made safe. Carries no fragment of what it was redacting."""


def _scanner():
    spec = importlib.util.spec_from_file_location("veldo_secret_scan_redact",
                                                  ROOT / ".veldo/secret_scan.py")
    m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m)
    return m


class ContextSeam:
    """The one place data becomes context.

    Constructed with the secret VALUES the runtime resolved (mapped to their references, so the
    placeholder can name which one was removed). Everything that would reach an agent goes through
    `admit`."""

    def __init__(self, known=None, shape_scan=True):
        # {value: reference}. Values are held here and NOWHERE else in the agent's process, and
        # this object is never itself put into context.
        self._known = {v: r for v, r in (known or {}).items() if isinstance(v, str) and v}
        self._shape_scan = shape_scan
        self.redactions = []          # (reference-or-shape, count) for the audit line

    def admit(self, text, where="<context>"):
        """Return `text` safe to put in an agent's context, or raise.

        Order matters: KNOWN VALUES FIRST, because they are certain, and a value that is also
        shape-detectable should be labelled with its reference rather than a generic mask."""
        if text is None:
            return ""
        if not isinstance(text, str):
            raise RedactionError("%s: only text becomes context; got %s"
                                 % (where, type(text).__name__))
        out = text
        for value, ref in sorted(self._known.items(), key=lambda kv: -len(kv[0])):
            if value in out:
                n = out.count(value)
                out = out.replace(value, placeholder(ref))
                self.redactions.append((ref, n))
        if self._shape_scan:
            out = self._redact_shapes(out, where)
        # THE LAST LINE OF DEFENCE, AND IT IS CHEAP: if any known value survived, refuse the whole
        # chunk. This catches a replacement bug in the loop above rather than trusting it.
        for value in self._known:
            if value in out:
                raise RedactionError("%s: a known secret survived redaction; refusing the chunk "
                                     "entirely rather than returning something that looks scrubbed"
                                     % where)
        return out

    def _redact_shapes(self, text, where):
        """Mask credential-shaped tokens the runtime never resolved, using the SAME detectors the
        gate scan uses. Reused rather than reimplemented: two spellings of 'what a secret looks
        like' would drift, and the one that drifted would be this one."""
        scan = _scanner()
        lines, changed = text.splitlines(keepends=True), False
        for i, line in enumerate(lines):
            if not scan.scan_text(line):
                continue
            masked = line
            for rx, _why in scan.PATTERNS:
                masked = rx.sub(placeholder(), masked)
            for tok in set(scan._CANDIDATE.findall(masked)):
                if scan._is_digest(tok) or scan.shannon(tok) < scan.ENTROPY_THRESHOLD:
                    continue
                masked = masked.replace(tok, placeholder())
            if masked != line:
                lines[i], changed = masked, True
                self.redactions.append(("shape", 1))
        return "".join(lines) if changed else text

    def audit(self):
        """What was removed, by reference, never by value. The line a human reads to know that
        redaction happened and which secrets it touched."""
        if not self.redactions:
            return "context redaction: nothing removed"
        counts = {}
        for ref, n in self.redactions:
            counts[ref] = counts.get(ref, 0) + n
        return "context redaction: " + ", ".join(
            "%s x%d" % (r, n) for r, n in sorted(counts.items()))
