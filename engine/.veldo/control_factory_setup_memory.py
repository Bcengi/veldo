"""Memory setup/revise, sharing setup's lock and owner command transport."""
import json
import os
from pathlib import Path
import sys
import uuid
import importlib.util


def organ(name):
    spec = importlib.util.spec_from_file_location('setup_memory_' + name, Path(__file__).with_name(name + '.py'))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


M, CHECK = organ('control_memory'), organ('control_memory_check')


def prepare(manifest, conn=None, revise=False, host=None):
    if manifest is None:
        return None
    try:
        definition = M.normalize(json.loads(Path(manifest).read_text()) if isinstance(manifest, (str, Path)) else manifest)
    except (OSError, ValueError, TypeError):
        raise M.Refused('invalid_input:memory:manifest') from None
    # The host running setup or revise, refused as handoff refuses it.
    M.on_host(definition, host)
    previous = M.read(conn) if conn is not None else None
    if conn is not None:
        M.profiles_outside(conn, definition)
    if previous and previous['definition'] != definition and not revise:
        raise M.Refused('invalid_input:state_root:differs:memory')
    return dict(definition=definition, previous=previous,
                outcome='already_done' if previous and previous['definition'] == definition else 'done')


def apply(plan, memory, ids, S, conn, journal, owner_sign, send=None):
    try:
        return _apply(plan, memory, ids, S, conn, journal, owner_sign, send)
    except Exception as error:
        if hasattr(error, 'code'):
            metrics = dict(memory_steps_refused=1)
            if getattr(error, 'check', False):
                metrics['memory_checks_refused'] = 1
            error.report = dict(step='memory', outcome='refused', reason=error.code, metrics=metrics)
        raise


def claude_mem_feed(root, definition):
    """VELDO-0187 AC1: the installed claude-mem version, read from the memory record's claude-mem part, and this
    host's feed setting under the state root (control_memory_feed.setup): qualified, or refused by name."""
    setting = organ('control_memory_feed').setup(root, definition)
    if setting is None:
        return None
    return dict(version=setting['version'], state=setting['state'], refusal=setting['refusal'],
                qualification=setting['qualification_digest'])


def _apply(plan, memory, ids, S, conn, journal, owner_sign, send=None):
    if memory is None:
        return None
    report = _stored(plan, memory, ids, S, conn, journal, owner_sign, send)
    report['claude_mem_feed'] = claude_mem_feed(plan['root'], memory['definition'])
    return report


def _stored(plan, memory, ids, S, conn, journal, owner_sign, send=None):
    definition, previous = memory['definition'], memory['previous']
    report = dict(step='memory', outcome=memory['outcome'], parts={
        part: dict(entry, digest=M.digest(entry)) for part, entry in definition['parts'].items()},
        metrics={'memory_steps_' + memory['outcome']: 1})
    if memory['outcome'] == 'already_done':
        return report
    checks = []
    try:
        for part in M.PARTS:
            checks.append(CHECK.check(plan['root'], previous['definition'] if previous else definition, part, 'before'))
        # The candidate must preserve memory before any run can read its revision.
        for part in M.PARTS:
            checks.append(CHECK.check(plan['root'], definition, part, 'after'))
    except CHECK.M.Refused as error:
        error.check = True
        raise
    base = previous['revision'] if previous else 0
    command = dict(ids, command_id='memory-' + uuid.uuid4().hex, operation=M.SAVE, principal=plan['owner'],
                   parameters=dict(definition=definition, base=base))
    packet = dict(command=command, signature=owner_sign(S.canonical_bytes(command)))
    if send:
        if not send(packet):
            raise M.Refused('invalid_input:state_root:service_running:memory')
    else:
        writer_module = M
        binding = S.owning_modules(S.entity_owners(conn)).get(M.SAVE)
        if binding and os.path.realpath(binding[0]) != os.path.realpath(M.__file__):
            spec = importlib.util.spec_from_file_location('installed_memory_writer', binding[0])
            writer_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(writer_module)
        try:
            writer_module.Memory(S, conn, ids, *journal).admit(packet)
        except Exception as error:
            if hasattr(error, 'code'):
                raise M.Refused(error.code, getattr(error, 'detail', '')) from None
            raise
    return dict(report, revision=base + 1, command_id=command['command_id'], checks=checks,
                metrics=dict(memory_steps_done=1, memory_revisions=1, memory_checks_passed=len(checks)))


def servers_main(args):
    """VELDO-0183: `bridge`, `kb`, `extract` and `servers`."""
    MS = organ('control_memory_servers')
    root = os.path.realpath(args.state_root)
    if args.action == 'bridge':
        return MS.bridge(root, args.part, args.server or args.part.replace('_', '-'), args.catalog_revision,
                         args.memory_revision)
    try:
        if args.action == 'kb':
            KB = organ('control_memory_kb')
            fields = KB.TOOLS[args.subcommand][2]
            arguments = {k: getattr(args, k) for k in fields if getattr(args, k, None) is not None}
            if 'path' in arguments:
                arguments['path'] = os.path.abspath(arguments['path'])
            result = MS.kb(root, args.subcommand, arguments)
            print(json.dumps(result, sort_keys=True))
            return 1 if result.get('isError') else 0
        if args.action == 'extract':
            request = json.loads(sys.stdin.read())
            result = MS.extract(root, request['text'])
        else:
            result = MS.setup_servers(root, args.owner_key, unit_dir=args.unit_dir, install_root=args.install_root)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (M.Refused, OSError, ValueError, KeyError) as error:
        print(json.dumps(dict(outcome='refused', reason=getattr(error, 'code', 'invalid_input:memory'),
                              detail=getattr(error, 'detail', ''))))
        return 1


def main(argv=None):
    import argparse
    parser = argparse.ArgumentParser(prog='veldo memory')
    subs = parser.add_subparsers(dest='action', required=True)
    # VELDO-0183: the store servers' bridge, memory_kb's command line through its store server, the subscription
    # extraction behind ava-memory's smart add, and the servers step.
    bridge = subs.add_parser('bridge')
    bridge.add_argument('part', choices=organ('control_memory_servers').STORES)
    bridge.add_argument('--server')
    bridge.add_argument('--catalog-revision', type=int)
    bridge.add_argument('--memory-revision', type=int)
    kb = subs.add_parser('kb')
    tools = kb.add_subparsers(dest='subcommand', required=True)
    for name, (_module, _function, fields, required) in organ('control_memory_kb').TOOLS.items():
        tool = tools.add_parser(name)
        for field, kind in fields.items():
            if field in required:
                tool.add_argument(field, type=int if kind == 'integer' else str)
            else:
                tool.add_argument('--' + field.replace('_', '-'), dest=field, type=int if kind == 'integer' else str)
    extract = subs.add_parser('extract')
    servers = subs.add_parser('servers')
    servers.add_argument('--owner-key', required=True)
    servers.add_argument('--unit-dir')
    servers.add_argument('--install-root')
    for p in (bridge, kb, extract, servers):
        p.add_argument('--state-root', required=True)
    check = subs.add_parser('check')
    check.add_argument('part', choices=M.PARTS)
    check.add_argument('phase', choices=('before', 'after'))
    revise = subs.add_parser('revise')
    revise.add_argument('manifest')
    revise.add_argument('--owner-key', required=True)
    for p in (check, revise):
        p.add_argument('--state-root', required=True)
    args = parser.parse_args(argv)
    if args.action in ('bridge', 'kb', 'extract', 'servers'):
        return servers_main(args)
    F = organ('control_factory_setup')
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
                              detail=getattr(error, 'detail', ''),
                              memory=getattr(error, 'report', dict(step='memory', outcome='refused', metrics={
                                  'memory_checks_refused' if args.action == 'check' else 'memory_steps_refused': 1})))))
        return 1
    finally:
        if conn is not None:
            conn.close()
        if lock is not None:
            os.close(lock)


if __name__ == '__main__':
    # VELDO-0183: the catalog bridge runs this module by its path (`veldo memory bridge <part>`).
    sys.exit(main())
