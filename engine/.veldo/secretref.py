#!/usr/bin/env python3
"""The secret reference seam (WARP-1301, W1 of PLAN-0013).

A secret is NAMED in the repository and RESOLVED at the moment of use. The name is data an agent
may read, write and commit. The value is something an agent never sees.

WHY THE DISTINCTION HAS TO BE STRUCTURAL. Ask an agent to wire up an API token and its default
behaviour, learned from every codebase ever written, is to put the literal string in a config file
and move on. Telling it not to is a rule that holds until the model is tired, the context is long
or the phrasing is unusual. What holds is not having a function that returns a value into the
agent's reach.

**SO THE AGENT-FACING API CANNOT RETURN A SECRET. THAT IS THE WHOLE DESIGN.** `wire()` takes a
reference and hands back a reference; it validates, it never resolves. Resolution lives behind
`resolve_for_runtime()`, which is documented as not-for-agents and returns an opaque handle rather
than a string. A caller that genuinely needs the bytes - the process actually making the API call -
takes them from the handle at the last possible moment.

**NOTHING HERE LOGS, ECHOES OR REPRS A VALUE.** `SecretHandle.__repr__` and `__str__` both return
the reference, never the secret, because the single most common way a credential reaches a log is
an exception formatter or a debug print rendering an object that happened to hold one.

**FAIL CLOSED ON ANYTHING UNRESOLVABLE.** A malformed reference, an unknown scheme and a name the
store does not hold all REFUSE. A resolver returning None must never be read as an empty secret,
because an empty credential is silently accepted by some APIs and then debugged for a day.
"""
import re

SCHEMA = "veldo.secretref/v1"

# THE SCHEMES A REFERENCE MAY USE, and the adapter each resolves through. Declared once. An
# unknown scheme is refused rather than guessed at, so a typo is a refusal and not a lookup miss.
SCHEMES = ("env", "keychain", "file", "vault", "ssm")

# The blessed default (D1). `env` is universally available and needs no daemon; `keychain` is the
# right answer on a developer machine. Both ship; the rest are seams.
DEFAULT_SCHEME = "env"

_REF = re.compile(r"\A(?P<scheme>[a-z]+):(?P<name>[A-Za-z0-9_][A-Za-z0-9_./-]*)\Z")

UNRESOLVED = "unresolved_reference"
MALFORMED = "malformed_reference"
UNKNOWN_SCHEME = "unknown_scheme"


class SecretError(RuntimeError):
    """Raised on any failure to resolve. Carries the REFERENCE, never the value, and never a
    partial value - an error message is a log line waiting to happen."""


def is_reference(value):
    """Whether this string is a well-formed reference. Cheap, total, and safe to call on anything
    including an actual secret, because it neither stores nor echoes what it is given."""
    return isinstance(value, str) and bool(_REF.match(value))


def parse(ref):
    """(scheme, name) for a reference, or raise. The one parser: every other function here calls
    this rather than doing its own regex, so a change to the syntax has one place to happen."""
    if not isinstance(ref, str):
        raise SecretError("%s: a reference must be a string, got %s"
                          % (MALFORMED, type(ref).__name__))
    m = _REF.match(ref)
    if not m:
        raise SecretError("%s: %r is not scheme:name. A secret is NAMED here and resolved at use; "
                          "if you are holding a value, that is the bug" % (MALFORMED, ref[:40]))
    scheme = m.group("scheme")
    if scheme not in SCHEMES:
        raise SecretError("%s: %r is not one of %s" % (UNKNOWN_SCHEME, scheme, list(SCHEMES)))
    return scheme, m.group("name")


def wire(ref):
    """THE AGENT-FACING CALL. Validates a reference and returns THE REFERENCE.

    This is the only function an agent should ever need, and it cannot leak a secret because it
    never has one. Wiring a credential means putting this string in a config file; the runtime
    resolves it later, somewhere the agent is not."""
    parse(ref)
    return ref


class SecretHandle:
    """A resolved secret that resists being printed.

    `__repr__` and `__str__` return the REFERENCE, not the value. That is not decoration: the most
    common route a credential takes into a log is an exception formatter or a debug print rendering
    an object that happens to hold one, and neither of those calls `.reveal()`."""

    __slots__ = ("_value", "_ref")

    def __init__(self, ref, value):
        self._ref, self._value = ref, value

    @property
    def reference(self):
        return self._ref

    def reveal(self):
        """The bytes. Named so that every call site reads as a deliberate act and greps out in one
        search, which is what makes an audit of who touches secrets tractable."""
        return self._value

    def __repr__(self):
        return "<SecretHandle %s>" % self._ref

    def __str__(self):
        return "<SecretHandle %s>" % self._ref

    def __eq__(self, other):
        return isinstance(other, SecretHandle) and self._ref == other._ref

    def __hash__(self):
        return hash(("SecretHandle", self._ref))


class FakeStore:
    """The reference resolver for tests: a dict and a record of what was asked for. Every property
    of this module is proven against it, so none of it needs a real keychain to test."""

    def __init__(self, values=None):
        self._v = dict(values or {})
        self.asked = []

    def get(self, scheme, name):
        self.asked.append((scheme, name))
        return self._v.get("%s:%s" % (scheme, name))


def resolve_for_runtime(ref, store):
    """NOT FOR AGENTS. Resolve a reference to a handle, for the process actually making the call.

    Returns a `SecretHandle`, never a bare string, so a value cannot be picked up by accident from
    a return position. Refuses on anything unresolvable: a store returning None is an ABSENT
    secret, never an empty one, because an empty credential is accepted by some APIs and then
    debugged for a day."""
    scheme, name = parse(ref)
    value = store.get(scheme, name)
    if value is None:
        raise SecretError("%s: %s holds no value. An absent secret is NOT an empty one" %
                          (UNRESOLVED, ref))
    if not isinstance(value, str) or value == "":
        raise SecretError("%s: %s resolved to something that is not a non-empty string" %
                          (UNRESOLVED, ref))
    return SecretHandle(ref, value)


def references_in(mapping):
    """Every reference in a config mapping, by key path. What a scanner uses to check that the
    things which should be references are, without ever reading the values that are not."""
    out = []

    def walk(node, path):
        if isinstance(node, dict):
            for k, v in sorted(node.items()):
                walk(v, "%s.%s" % (path, k) if path else str(k))
        elif is_reference(node):
            out.append((path, node))
    walk(mapping, "")
    return out
