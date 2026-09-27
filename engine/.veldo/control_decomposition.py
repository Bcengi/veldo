"""Decomposition publication (VELDO-0085).

A signed project member command publishes one primary specification for one unit
of one backlog item. Required fields are UNIT_FIELDS plus source, role, front,
body and dependencies. The unit remains a proposal until the backlog's signed
prepare or append, grooming, admission and fresh priority commands accept it.

The allocator renders complete bytes for the authority-selected alias inside its
normal compare-and-swap retry. Identical source tuples reuse their accepted alias;
changed source revision or role allocates another. No checkout maximum is read.
Dependencies name already published units of this same item or existing units;
the specification carries their aliases and the unit carries their execution IDs.

Publication uses VELDO-0037's pending obligation and exact materializer. Recovery
and broader multi-author concurrency qualification remain Release 2. Concurrent
source revisions serialize in the allocator and supersede the earlier specification. This service does
not change admission, spend, review or landing authority.
"""
import importlib.util
from types import SimpleNamespace
from pathlib import Path


def _organ(name):
    spec = importlib.util.spec_from_file_location('decomposition_' + name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


B = _organ('control_decomposition_binding')
Y = _organ('yamlish')
UNIT_FIELDS = ('unit', 'scope', 'requirements', 'eligible_holders')
FIELDS = UNIT_FIELDS + ('source', 'role', 'front', 'body', 'dependencies')


class Decomposition:
    def __init__(self, backlog, allocations, publisher):
        if backlog.conn is not allocations.conn or publisher.service is not allocations:
            raise ValueError('decomposition uses one authority connection')
        self.backlog, self.allocations, self.publisher = backlog, allocations, publisher
        # File-loaded backlog modules need not appear in sys.modules. Reuse the
        # actual method globals so its exception identity and helpers stay together.
        self.CB = SimpleNamespace(**backlog._unit_entry.__func__.__globals__)
        self.refused_by_reason = {}
        self.observations = []
        self.counts = {'accepted': 0, 'refused': 0}

    def pending(self):
        return self.allocations.pending()

    def publish(self, packet):
        CB = self.CB
        command = packet.get('command', {}) if isinstance(packet, dict) else {}
        raw = command.get('unit')
        event = dict(self.backlog.ids, operation='publish_decomposition', item=command.get('item'),
                     unit=raw.get('unit') if isinstance(raw, dict) else None, command_id=command.get('command_id'))
        try:
            result = self._publish(packet, command, event)
        except (CB.Refused, self.allocations.store.StoreRefused) as error:
            result = {'ok': False, 'reason': error.code}
        event.update(outcome='accepted' if result['ok'] else 'refused', refusal=result.get('reason'),
                     taxonomy=None if result['ok'] else CB.taxonomy(result.get('reason')))
        self.counts[event['outcome']] += 1
        if not result['ok']:
            reason = result['reason']
            self.refused_by_reason[reason] = self.refused_by_reason.get(reason, 0) + 1
        self.observations.append(event)
        return result

    def _publish(self, packet, command, event):
        CB = self.CB
        bl, al = self.backlog, self.allocations
        if (command.get('operation') != 'publish_decomposition'
                or any(command.get(k) != v for k, v in bl.ids.items())):
            raise CB.Refused('invalid_input:command')
        state = bl.membership.authority_state(bl.store, bl.conn)
        principal = command.get('principal')
        key = bl.AC.active_key(state['keyring'], principal, bl.clock())
        if key is None or not isinstance(packet.get('signature'), str):
            raise CB.Refused('not_authorized')
        verified, _ = bl.AC.ssh_keygen_verify(bl.store.canonical_bytes(command), packet['signature'],
                                           bl.AC.allowed_signers_line(principal, key['public_key']), principal)
        if not verified:
            raise CB.Refused('not_authorized')
        if not CB._is_str(command.get('item')):
            raise CB.Refused('invalid_input:backlog_item')
        item = CB.read(bl.conn, command['item'])
        if item is None or item.get('version') != command.get('item_version'):
            raise CB.Refused('stale_subject:item')
        event['accepted_versions'] = {'item': item['version']}
        errors = bl._member_problems(state, principal, item['project'], bl.clock())
        project = CB._row(bl.conn, 'project:' + item['project'])
        if errors or project['data']['state'] != 'ACTIVE':
            raise CB.Refused(errors[0] if errors else 'project_not_active')
        if item['state'] not in ('RAW', 'PRIORITIZED', 'ACTIVE'):
            raise CB.Refused('invalid_transition:publication')
        raw = command.get('unit')
        if not isinstance(raw, dict) or set(raw) != set(FIELDS):
            raise CB.Refused('invalid_input:unit_fields')
        problem = CB.CL.unit_id_problem(raw['unit'])
        if problem:
            raise CB.Refused('invalid_input:unit_id', problem)
        entry = {k: raw[k] for k in UNIT_FIELDS}
        # Ask the backlog's own field, scope and identity validator before any artifact.
        proposed_id = raw['front'].get('id', 'VELDO-0000') if isinstance(raw['front'], dict) else 'VELDO-0000'
        bl._unit_entry(bl.conn, item, dict(entry, specification=proposed_id), set())
        if not isinstance(raw['front'], dict) or not isinstance(raw['body'], str):
            raise CB.Refused('invalid_input:document')
        if not isinstance(raw['dependencies'], list) or any(CB.CL.unit_id_problem(d) for d in raw['dependencies']):
            raise CB.Refused('invalid_input:dependencies')
        if raw['unit'] in raw['dependencies'] or len(set(raw['dependencies'])) != len(raw['dependencies']):
            raise CB.Refused('invalid_input:dependencies')
        if not isinstance(raw['role'], str) or raw['role'].split('/', 1)[0] != 'specification':
            raise CB.Refused('invalid_input:role')
        spec_dependencies = []
        for dep in raw['dependencies']:
            alias = B.current_specification(bl.conn, bl.ids['repository_uuid'], dep)
            bound, errors = B.binding(bl.conn, bl.ids['repository_uuid'], alias, bl.workspace) if alias else (None, [])
            unit = CB.unit(bl.conn, dep)
            if errors or (bound and not unit and bound['backlog_item'] != item['uuid']):
                bound = None
            if bound is None:
                raise CB.Refused('missing_evidence:dependency')
            spec_dependencies.append(bound['alias'])
        meta = dict(entry, backlog_item=item['uuid'], dependencies=list(raw['dependencies']),
                    specification_dependencies=spec_dependencies)

        def content(alias):
            front = dict(raw['front'], schema='veldo.spec/v1', id=alias, depends_on=spec_dependencies,
                         decomposition=meta)
            return Y.render_document(front, raw['body']).encode('utf-8')

        signing = dict(signer=bl.journal_signer, sign=bl.sign, authority_generation=bl.authority_generation)
        result = al.allocate(dict(request_id=command['command_id'], principal=principal,
                                  repository_uuid=bl.ids['repository_uuid'], workspace=str(bl.workspace),
                                  source=raw['source'], role=raw['role'], slug='decomposed', content=b''),
                             content_for_alias=content, **signing)
        self.publisher.publish(bl.ids['repository_uuid'], result['alias'], result['version'], principal, **signing)
        bound, errors = B.binding(bl.conn, bl.ids['repository_uuid'], result['alias'], bl.workspace)
        if errors:
            raise CB.Refused(errors[0])
        event.update(accepted_versions={'item': item['version'], 'specification': bound['version']},
                     alias=result['alias'], digest=bound['digest'])
        return dict(ok=True, unit=dict(entry, specification=result['alias'], document=bound),
                    reused=bool(result.get('reused')))
