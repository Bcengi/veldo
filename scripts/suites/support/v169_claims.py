"""VELDO-0169: the project-check receipt a suite's fixture claim carries.

A suite that commits, as its fixture, the claim_operation command the authority service would commit
calls the claim organ (control_claim.transition) straight through the store. Since VELDO-0169 the
organ refuses a claim without the receipt the Gate's project check makes (control_eligibility.Gate.
project_problems), bound to the versions the transaction pins. `receipted` asks that check on the
suite's own store connection, as the claim receiver does, and returns the command with the receipt in
its parameters and the versions the check read among its expected versions. A unit whose project the
Gate refuses is a broken fixture, never a claim, so it raises.
"""

_GATES = {}


def gate(claims, store, conn, domain_uuid, repository_uuid):
    key = (id(claims), id(conn), domain_uuid, repository_uuid)
    kept = _GATES.get(key)
    if kept is None or kept[0] is not conn or kept[1] is not claims:
        eligibility = claims.organ('control_eligibility')
        kept = _GATES[key] = (conn, claims, eligibility.Gate(store, conn, domain_uuid=domain_uuid,
                                                             repository_uuid=repository_uuid))
    return kept[2]


def receipted(claims, store, conn, domain_uuid, command):
    """`command` (a claim_operation command) with the Gate's project-check receipt of its unit when it
    hands work out."""
    params = command['parameters']
    if params['action'] not in claims.HANDOUTS:
        # Renew, release and use hand nothing out and carry no receipt, as at the claim receiver.
        return command
    refusals, read, receipt = gate(claims, store, conn, domain_uuid, params['repository_uuid']).project_problems(
        params['unit_id'])
    if refusals:
        raise AssertionError('fixture unit %s: the Gate refuses its project: %s' % (params['unit_id'], refusals))
    return dict(command, parameters=dict(params, project_check=receipt),
                expected_versions=dict(command['expected_versions'], **read))
