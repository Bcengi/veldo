#!/usr/bin/env python3
"""The architecture contract loader (VELDO-0016 AC3, PLAN-0019 W1): three states and a flag.

The loader this replaced answered (None, None) both for "this repository has no contract" and for
"this repository has a contract nobody can read", so a truncated, unreadable, malformed or
structurally invalid contract stood EVERY consumer down exactly as if the repository had adopted
none: the ready transition let a placeless spec through, the frontier offered it, run-check
cleared it and the shape gate printed "standing down (adoption safe)". Absence is a state a
repository's policy may call optional. Presence never is.

A contract organ in the sense arch.py is: pure over its arguments, standard library only, given
the arch organ and the one front-matter parser by its caller (validate_checks) so there is one
reader of the artifact and one parser of it. It starts nothing and writes nothing. validate_checks
loads it EAGERLY, because consumers catch ContractRefused by name.
"""
import collections
import os
from pathlib import Path

CONTRACT_ABSENT, CONTRACT_VALID, CONTRACT_INVALID = "absent", "valid", "invalid"
# The error taxonomy VELDO-0016 and VELDO-0053 name, one word each, so a consumer's diagnostic and a
# suite's row can name the class without parsing prose.
CONTRACT_KINDS = ("optional_absence", "required_absence", "unreadable", "parse_failure",
                  "invalid_structure", "valid")


class ContractLoad(collections.namedtuple(
        "ContractLoad", "state kind arch contract problems path required")):
    """The one result type every architecture-loading entry point shares. `state` is one of
    CONTRACT_ABSENT / CONTRACT_VALID / CONTRACT_INVALID, `kind` one of CONTRACT_KINDS, `arch` the
    loaded arch organ (None only when nothing was at the path), `contract` the parsed dict (only
    when valid), `problems` the refusal reasons by name (empty unless refused), `path` where the
    contract was looked for and `required` the flag that was in force."""
    __slots__ = ()

    @property
    def refused(self):
        """True when a consumer may NOT proceed as if the shape were known: a present contract that
        is not valid, or an absent contract the policy requires. Optional absence is the one state
        that stands down (adoption safe)."""
        return self.state == CONTRACT_INVALID or (self.state == CONTRACT_ABSENT and self.required)

    @property
    def reason(self):
        return "; ".join(self.problems) if self.problems else None


class ContractRefused(ValueError):
    """Raised by validate_checks.load_repo_contract when the load is refused, carrying the
    ContractLoad, so a consumer written against the (arch, contract) pair cannot receive
    (None, None) for a contract that exists: it either handles the refusal by name or fails
    closed."""

    def __init__(self, load):
        super().__init__(load.reason or "architecture contract refused")
        self.load = load


def contract_requirement(repo_root):
    """Whether this repository's policy declares its architecture contract REQUIRED: the line
    `architecture_contract: required` (or `optional`) at the top level of .veldo/policy.yaml. No
    policy file, or no line, means optional (adoption safe: a repository that never said is
    unaffected). A line that is present and does not say `optional` means required, so a
    misspelling closes rather than opens. A policy entry that is not a regular file (a directory,
    a dangling link, a FIFO) or that cannot be read is NOT OPENED and means required: the kind
    question is asked before the read, so nothing here can block, and an unreadable policy closes.
    Proportionate line reader, the posture policy_check.protected_patterns and
    decision_review.required_reviews_for take with the same file (one policy, no second parser)."""
    p = Path(repo_root) / ".veldo" / "policy.yaml"
    if not os.path.lexists(p):
        return False
    if not p.is_file():
        return True
    try:
        text = p.read_text()
    except OSError:
        return True
    for line in text.splitlines():
        if line.startswith("architecture_contract:"):
            value = line.split(":", 1)[1].split("#", 1)[0].strip().strip("'\"")
            return value != "optional"
    return False


def load_contract_state(repo_root, arch, parse, required=None, contract_path=None):
    """The tri-state load of a repository's architecture contract, as a ContractLoad. `arch` is the
    loaded arch organ and `parse` the one front-matter parser. `required` None reads the policy
    flag (contract_requirement); True or False overrides it (the CLI's and a fixture's explicit
    flag). Presence is decided by os.path.lexists, so a directory, a dangling symlink or an
    unreadable file at the path is PRESENT and refused as unreadable, never mistaken for absence.
    A present file is read by arch.load_contract (the one reader) and then structurally validated
    by arch.validate_contract with a collecting reporter, so "valid" here means exactly what
    check_arch means by it and a consumer never gates against a contract the gate would refuse."""
    base = Path(repo_root)
    p = Path(contract_path) if contract_path else base / ".veldo" / "architecture.yaml"
    req = contract_requirement(base) if required is None else bool(required)
    if not os.path.lexists(p):
        if req:
            return ContractLoad(CONTRACT_ABSENT, "required_absence", None, None,
                                ("architecture contract is required by this repository's policy but "
                                 "absent (fail closed): nothing is placeable, claimable or buildable "
                                 "until it exists",), str(p), True)
        return ContractLoad(CONTRACT_ABSENT, "optional_absence", None, None, (), str(p), False)
    try:
        data = arch.load_contract(p, parse)
    except arch.ArchContractError as e:
        kind = "unreadable" if getattr(e, "kind", None) == "unreadable" else "parse_failure"
        return ContractLoad(CONTRACT_INVALID, kind, arch, None, (str(e),), str(p), req)
    problems = []
    arch.validate_contract(data, base, p, lambda _where, msg: (problems.append(msg), 1)[1])
    if problems:
        return ContractLoad(CONTRACT_INVALID, "invalid_structure", arch, None,
                            tuple(problems), str(p), req)
    return ContractLoad(CONTRACT_VALID, "valid", arch, data, (), str(p), req)


def pair_or_refuse(load):
    """(arch, contract) for a valid load, (None, None) for an optional absence, ContractRefused
    for everything else: the (arch, contract) contract every existing consumer was written to."""
    if load.refused:
        raise ContractRefused(load)
    return load.arch, load.contract


def report_problems(load, fail):
    """The gate's rendering of a load: 0 when not refused, else one fail(path, problem) per
    problem, returning the error count (check_arch)."""
    if not load.refused:
        return 0
    errs = 0
    for msg in load.problems:
        errs += fail(load.path, msg)
    return errs
