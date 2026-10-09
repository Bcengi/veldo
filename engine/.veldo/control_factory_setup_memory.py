"""Memory setup/revise, sharing setup's lock and owner command transport."""
import json
import os
from pathlib import Path
import uuid
import importlib.util


def organ(name):
    spec = importlib.util.spec_from_file_location('setup_memory_' + name, Path(__file__).with_name(name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M, CHECK = organ('control_memory'), organ('control_memory_check')


def prepare(manifest, conn=None, revise=False):
    if manifest is None:
        return None
    try:
        definition = M.normalize(json.loads(Path(manifest).read_text()) if isinstance(manifest, (str, Path)) else manifest)
    except (OSError, ValueError, TypeError):
        raise M.Refused('invalid_input:memory:manifest') from None
    previous = M.read(conn) if conn is not None else None
    if conn is not None:
        M.profiles_outside(conn, definition)
    if previous and previous['definition'] != definition and not revise:
        raise M.Refused('invalid_input:state_root:differs:memory')
    return dict(definition=definition, previous=previous,
                outcome='already_done' if previous and previous['definition'] == definition else 'done')


def apply(plan, memory, ids, S, conn, journal, owner_sign, send=None):
    if memory is None:
        return None
    definition, previous = memory['definition'], memory['previous']
    report = dict(step='memory', outcome=memory['outcome'], parts={
        part: dict(entry, digest=M.digest(entry)) for part, entry in definition['parts'].items()})
    if memory['outcome'] == 'already_done':
        return report
    checks = []
    for part in M.PARTS:
        checks.append(CHECK.check(plan['root'], previous['definition'] if previous else definition, part, 'before'))
    base = previous['revision'] if previous else 0
    command = dict(ids, command_id='memory-' + uuid.uuid4().hex, operation=M.SAVE, principal=plan['owner'],
                   parameters=dict(definition=definition, base=base))
    packet = dict(command=command, signature=owner_sign(S.canonical_bytes(command)))
    if send:
        if not send(packet):
            raise M.Refused('invalid_input:state_root:service_running:memory')
    else:
        M.Memory(S, conn, ids, *journal).admit(packet)
    for part in M.PARTS:
        checks.append(CHECK.check(plan['root'], definition, part, 'after'))
    return dict(report, revision=base + 1, command_id=command['command_id'], checks=checks)


def main(argv=None):
    import argparse
    F = organ('control_factory_setup')
    parser = argparse.ArgumentParser(prog='veldo memory')
    subs = parser.add_subparsers(dest='action', required=True)
    check = subs.add_parser('check')
    check.add_argument('part', choices=M.PARTS)
    check.add_argument('phase', choices=('before', 'after'))
    revise = subs.add_parser('revise')
    revise.add_argument('manifest')
    revise.add_argument('--owner-key', required=True)
    for p in (check, revise):
        p.add_argument('--state-root', required=True)
    args = parser.parse_args(argv)
    conn, lock = None, None
    try:
        root = os.path.realpath(args.state_root)
        S = F.organ('control_claim').S
        path = os.path.join(root, 'authority', 'control.sqlite3')
        conn = S.open_store(path, mode='r')
        if args.action == 'check':
            record = M.read(conn)
            if record is None:
                raise M.Refused('missing_evidence:memory:record')
            result = CHECK.check(root, record['definition'], args.part, args.phase)
        else:
            memory = prepare(args.manifest, conn, revise=True)
            if memory['previous'] is None:
                raise M.Refused('missing_evidence:memory:record')
            laid = json.loads((Path(root) / 'host/ingress.json').read_text())
            plan = dict(root=root, owner=memory['previous']['owner'], owner_key=args.owner_key,
                        workspace=laid['workspace'], host_trust=laid['host_trust'])
            ids = laid['authority_ids']
            sign = F.organ('control_channel_activation').ssh_signer(args.owner_key)
            conn.close()
            conn = None
            lock = F.take_lock(root)
            if lock is not None:
                conn = S.open_store(path)
            journal = F.organ('control_channel_ingress').journal_signer(laid['journal'])
            result = apply(plan, memory, ids, S, conn, journal, sign,
                           send=(lambda packet: F.service_request(plan, packet)()) if lock is None else None)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (M.Refused, CHECK.M.Refused, OSError, ValueError) as error:
        print(json.dumps(dict(outcome='refused', reason=getattr(error, 'code', 'invalid_input:memory'),
                              detail=getattr(error, 'detail', ''))))
        return 1
    finally:
        if conn is not None:
            conn.close()
        if lock is not None:
            os.close(lock)
