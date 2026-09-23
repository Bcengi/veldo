#!/usr/bin/env python3
"""Require the teeth review's named assertions to fail on temporary defective production copies.

Run all findings, or --finding N. Workers run the entire named suite; exceptions, timeouts,
missing rows and process failures are errors, never successful mutation detections.
"""
import argparse
import ast
import contextlib
import difflib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

sys.dont_write_bytecode = True

ROOT = Path(__file__).resolve().parent.parent
SIGNED = '("schema", "workspace", "domain_uuid", "store_uuid", "command") + IDENTITY_FIELDS'
FIELDS = ('schema', 'workspace', 'domain_uuid', 'store_uuid', 'command',
          'repository_uuid', 'repository_root_commit', 'clone_uuid',
          'binding_digest', 'authority_generation')


def cases():
    result = []

    def add(finding, name, suite, module, old, new, rows):
        result.append(dict(finding=finding, name=name, suite=suite, module=module,
                           old=old, new=new, rows=rows))

    def signature(name, old, new, rows):
        add(1, name, '47_veldo_0107_ipc.py', 'control_client.py', old, new, rows)

    signature('command-only', SIGNED, '("command",)',
              ['ipc/signature-covers/' + f for f in FIELDS if f != 'command'])
    for field in FIELDS:
        signature('omit-' + field, SIGNED,
                  'tuple(k for k in (' + SIGNED + ') if k != ' + repr(field) + ')',
                  ['ipc/signature-covers/' + field])
    signature('unsigned-request-field', '    req.update({k: binding[k] for k in IDENTITY_FIELDS})',
              '    req["extra_coordinate"] = "added"\n'
              '    req.update({k: binding[k] for k in IDENTITY_FIELDS})',
              ['ipc/signature-fields-match-request'])
    signature('signed-nonrequest-field', SIGNED, SIGNED + ' + ("extra_coordinate",)',
              ['ipc/signature-fields-match-request'])
    empty_paths = {
        'unreachable': ('        return EXIT_UNREACHABLE',
                        'relay/an-unreachable-authority-is-reported-not-answered'),
        'usage': ('        return 64', 'relay/usage-has-zero-stdout'),
        'oversized-request': ('        return EXIT_TOO_LARGE\n    try:',
                              'relay/oversized-request-has-zero-stdout'),
        'oversized-response': ('        return EXIT_TOO_LARGE\n    stdout.write(answer)',
                               'relay/oversized-response-has-zero-stdout'),
    }
    for path, (anchor, row) in empty_paths.items():
        for name, payload in [('null', b'null'), ('newline', b'\n'), ('space', b' ')]:
            add(2, path + '-' + name, '48_veldo_0108_relay.py', 'control_relay.py',
                anchor, '        stdout.write(' + repr(payload) + ')\n' + anchor, [row])
    add(2, 'unreachable-object', '48_veldo_0108_relay.py', 'control_relay.py',
        '        return EXIT_UNREACHABLE',
        '        stdout.write(b"{}")\n        return EXIT_UNREACHABLE',
        ['relay/an-unreachable-authority-is-reported-not-answered'])
    scope = '    scope = start_line_scope(repo, start_line or "", commit, bundle_landed_at(repo, proof_dir))'
    # Preserve the scope expression: the suite also replaces it for its existing
    # precedence control. An additive assignment composes with that mutation.
    for name, assignment in [
        ('manifest-fallback', 'start_line or manifest.get("from_commit")'),
        ('nested-manifest-fallback', 'start_line or manifest.get("fix_validation", {}).get("from_commit")'),
        ('manifest-precedence', 'manifest.get("from_commit") or start_line'),
    ]:
        add(3, name, '44_veldo_0105_startline.py', 'fix_validation_record.py', scope,
            '    start_line = ' + assignment + '\n' + scope,
            ['proofcheck/start-line-not-author-writable'])
    add(5, 'clone-local-store', '46_veldo_0029_enrollment.py', 'control_enrollment.py',
        '             "problems": [p[0] for p in problems]})\n    return binding["store_path"]',
        '             "problems": [p[0] for p in problems]})\n'
        '    return binding["store_path"] + "." + binding["clone_uuid"]',
        ['enrollment/independent-clones-share-bound-store'])
    add(6, 'dead-socket-success', '49_veldo_0109_unavailable.py', 'control_client.py',
        '            seen = last_seen(enrollment, workspace, binding)',
        '            seen = last_seen(enrollment, workspace, binding)\n'
        '            if os.path.exists(address) and __import__("stat").S_ISSOCK(os.stat(address).st_mode):\n'
        '                return {"accepted": True, "watermark": seen.get("watermark") if seen else None}',
        ['unavailable/sigkill-refuses-generic-client'])
    add(12, 'exclusive-request-limit', '48_veldo_0108_relay.py', 'control_relay.py',
        '        if total > limit:', '        if total >= limit:',
        ['relay/exact-limit-request-is-carried'])
    add(12, 'exclusive-response-limit', '48_veldo_0108_relay.py', 'control_relay.py',
        '            if total > MAX_BYTES:', '            if total >= MAX_BYTES:',
        ['relay/exact-limit-response-is-carried'])
    def grammar(name, module, old, new, row):
        add(118, name, '54_veldo_0118_grammar.py', module, old, new, ['grammar/' + row])
        result[-1]['fixture'] = True

    grammar('omit-folded-block', 'grammar_cases.py',
            "    for identity, node, fmt in coverage_accepted(data):\n",
            "    for identity, node, fmt in coverage_accepted(data):\n"
            "        if 'folded' in coverage_seen(node, data)['production']:\n            continue\n",
            'all-coverage-targets-exist')
    grammar('omit-recursive-pair', 'grammar_cases.py',
            "    for site in sorted(required['pair']):\n",
            "    for site in sorted(required['pair']):\n"
            "        if site == ('flow-map', 'value', 'flow-map'):\n            continue\n",
            'all-coverage-targets-exist')
    for name, rule in [('omit-duplicate-key', 'duplicate-key'), ('omit-tab-edit', 'bad-indentation')]:
        grammar(name, 'grammar_cases.py',
                "    for rule, parent, slot, child in sorted(coverage_targets(data)['boundary']):\n",
                "    for rule, parent, slot, child in sorted(coverage_targets(data)['boundary']):\n"
                "        if rule == " + repr(rule) + ":\n            continue\n",
                'all-boundary-sites-exist')
    grammar('omit-oracle-observation', 'yaml_oracle.py',
            "    yaml = cap['module']\n",
            "    if text == 'a: a\\n':\n        return dict(result, state='unobserved')\n"
            "    yaml = cap['module']\n", 'oracle-observations-complete')
    grammar('oracle-runtime-error', 'yaml_oracle.py',
            "    yaml = cap['module']\n",
            "    if text == 'a: a\\n':\n        return dict(result, state='oracle_error')\n"
            "    yaml = cap['module']\n", 'oracle-observations-complete')
    grammar('delegate-oracle-to-reader', 'yaml_oracle.py',
            "return {'state': 'value', 'value': adapt_node(raw['tree'])}",
            "return {'state': 'value', 'value': __import__('yamlish').parse(raw['source'])}",
            'oracle-is-independent')
    grammar('delegate-oracle-to-front-matter', 'yaml_oracle.py',
            "return {'state': 'value', 'value': adapt_node(raw['tree'])}",
            "return {'state': 'value', 'value': __import__('yamlish').front_matter(raw['source'])}",
            'oracle-is-independent')
    grammar('absence-counts-as-agreement', 'yaml_oracle.py',
            "            result['unobserved'] += 1\n",
            "            result['unobserved'] += 1\n"
            "            if raw['state'] == 'oracle_unavailable':\n"
            "                result['compared'] += 1\n                result['agreed'] += 1\n",
            'missing-oracle-is-unproven')
    grammar('broken-dependency-counts-as-absence', 'yaml_oracle.py',
            "state = 'oracle_unavailable' if exc.name == 'yaml' else 'oracle_error'",
            "state = 'oracle_unavailable'",
            'missing-oracle-is-unproven')
    def agreement(name, module, old, new, row, fixture=False):
        add(119, name, '55_veldo_0119_agreement.py', module, old, new, ['reader/' + row])
        if fixture:
            result[-1]['fixture'] = True

    agreement('reader-strip-quoted-hash', 'yamlish.py',
              "                return ''.join(out)",
              "                return ''.join(out).split('#', 1)[0]",
              'generated-grammar-agrees')
    agreement('reader-coerce-leading-zero', 'yamlish.py',
              "return int(word) if _INT.fullmatch(word) else word",
              "return int(word) if re.fullmatch(r'-?[0-9]+', word) else word",
              'generated-grammar-agrees')
    agreement('reader-overwrite-duplicate', 'yamlish.py',
              "                if key in out:\n                    self.error(n, 'duplicate key ' + repr(key))",
              "                if False:\n                    self.error(n, 'duplicate key ' + repr(key))",
              'generated-boundaries-refuse')
    agreement('reader-accept-unclosed-flow', 'yamlish.py',
              "        self.error('unclosed collection')",
              "        return out",
              'generated-boundaries-refuse')
    agreement('reader-unavailable-counts-as-compared', 'reader_agreement.py',
              "            report['unobserved'] += 1",
              "            report['unobserved'] += 1\n"
              "            if raw['state'] == 'oracle_unavailable':\n"
              "                report['compared'] += 1",
              'agreement-requires-full-oracle-domain', fixture=True)
    agreement('reader-omit-from-required-domain', 'reader_agreement.py',
              "    required = Counter(identity(case) for case in cases)",
              "    if omit is not None:\n        cases = cases[1:]\n        omit = None\n"
              "    required = Counter(identity(case) for case in cases)",
              'agreement-requires-full-oracle-domain', fixture=True)
    def policy(name, module, old, new, row, fixture=False):
        add(120, name, '57_veldo_0120_policygrammar.py', module, old, new, ['policyread/' + row])
        if fixture:
            result[-1]['fixture'] = True

    policy('policy-strip-quoted-hash', 'yamlish.py',
           "                return ''.join(out)",
           "                return ''.join(out).split('#', 1)[0]",
           'generated-settings-agree')
    policy('policy-coerce-leading-zero', 'fix_validation_record.py',
           '        block[START_KEY] = str(block[START_KEY])',
           '        block[START_KEY] = str(int(block[START_KEY])) if str(block[START_KEY]).isdigit() else str(block[START_KEY])',
           'generated-settings-agree')
    policy('policy-syntax-becomes-absent', 'fix_validation_record.py',
           '        raise ValidationError(f"{policy_path}: {exc}") from exc',
           '        return {}', 'generated-invalid-is-not-absent')
    policy('policy-shape-becomes-absent', 'fix_validation_record.py',
           '        raise ValidationError(f"{policy_path}: {FLAG_KEY} must be a nonempty mapping")',
           '        return {}', 'generated-invalid-is-not-absent')
    policy('policy-absent-oracle-qualifies', 'policy_agreement.py',
           "    return (report['oracle_state'] == 'available' and report['inventory_complete']",
           "    return (report['oracle_state'] == 'oracle_unavailable' or report['oracle_state'] == 'available' and report['inventory_complete']",
           'generated-oracle-coverage-is-honest', fixture=True)
    policy('policy-omit-required-result', 'policy_agreement.py',
           '    executed = {name: Counter() for name in readers}',
           "    if omit is not None:\n        cases = cases[1:]\n        expected = expected.copy()\n        del expected[next(iter(expected))]\n        omit = None\n"
           '    executed = {name: Counter() for name in readers}',
           'generated-oracle-coverage-is-honest', fixture=True)

    def signing(name, module, old, new, row):
        add(27, name, '56_veldo_0027_signing.py', module, old, new, ['signing/' + row])

    signing('signing-prelock-clock', 'control_keys.py',
            "    at, kid = time.time(), params['key_id']",
            "    at, kid = params['admitted_at'], params['key_id']", 'transition-clock')
    signing('signing-truncated-clock', 'control_keys.py',
            "    at, kid = time.time(), params['key_id']",
            "    at, kid = int(time.time()), params['key_id']", 'transition-clock')
    restriction = "        if request.get('channel') != channel or request.get('edge_key_id') != key['key_id']:"
    signing('signing-remove-channel-restriction', 'control_signer.py', restriction,
            '        if False:', 'cross-channel')
    signing('signing-permit-foreign-channel', 'control_signer.py', restriction,
            "        if request.get('channel') == channel and request.get('edge_key_id') != key['key_id']:", 'cross-channel')
    auth = "        channel = authenticate(state, challenge, request, identity, authentication, now)"
    signing('signing-request-channel', 'control_signer.py', auth,
            auth + "\n        channel = request['channel']", 'channel-comes-from-the-connection')
    signing('signing-request-key-channel', 'control_signer.py', auth,
            auth + "\n        channel = K.entries(state)[request['edge_key_id']]['channel']", 'channel-comes-from-the-connection')
    selection = "        key = K.select(state, config['allowed_signers'], channel, now)"
    signing('signing-request-key', 'control_signer.py', selection,
            selection + "\n        key = K.entries(state).get(request.get('edge_key_id'), key)", 'key-comes-from-the-channel')
    signing('signing-ignore-key-crosscheck', 'control_signer.py', restriction,
            "        if request.get('channel') != channel:", 'key-comes-from-the-channel')
    attribution = "    if any(not attribution.get(field) for field in fields):"
    signing('signing-text-without-identity', 'control_signer.py', attribution,
            '    if False:', 'text-only')
    signing('signing-text-substitutes-identity', 'control_signer.py', attribution,
            "    if not payload.get('text') and any(not attribution.get(field) for field in fields):", 'text-only')
    accepted = """    if body != projection(state):
        raise Refused('projection-mismatch')
    return state['keyring']"""
    branch_keys = """    return [dict(k, public_key=' '.join(line.split()[-2:]))
            for k in state['keyring'] for line in body.splitlines()
            if line.split() and line.split()[0] == k['principal']]"""
    signing('signing-branch-projection-authority', 'control_keys.py', accepted, branch_keys, 'branch-key')
    signing('signing-branch-preflight-bypass', 'control_keys.py',
            "    keyring = administrative_keyring(state, projection_path)",
            "    if Path(projection_path).read_text() != projection(state):\n"
            "        return {'committed': True}\n"
            "    keyring = administrative_keyring(state, projection_path)", 'branch-key')
    content = "               for field in AC.DECISION_ASSERTION_FIELDS):"
    signing('signing-ignore-personal-content', 'control_signer.py', content,
            "               for field in ()):", 'personal-content-binding')
    signing('signing-ignore-personal-ruling', 'control_signer.py', content,
            "               for field in ('presentation_id',)):", 'personal-content-binding')
    signing('signing-bind-only-original-fields', 'control_signer.py', content,
            "               for field in ('ruling', 'presentation_id')):", 'personal-relabel/presentation_digest')
    signing('signing-default-missing-personal-fields', 'control_signer.py',
            "        if any(field not in parameters or field not in payload or parameters[field] != payload[field]",
            "        if any(parameters.get(field, payload.get(field)) != payload.get(field)",
            'personal-missing/presentation_digest')
    binding = "    if payload.get('edge_key_id') != request['edge_key_id']:"
    signing('signing-ignore-selected-key-binding', 'control_signer.py', binding,
            "    if False:", 'rotation-requires-rebound-delegation')
    signing('signing-retired-key-inherits-grant', 'control_signer.py', binding,
            "    if payload.get('edge_key_id') != request['edge_key_id'] and K.active(K.entries(state)[payload['edge_key_id']], now):",
            'rotation-requires-rebound-delegation')
    signing('signing-leak-source-before-auth', 'control_signer.py', auth,
            "        source = state['entities'].get(request.get('source_id'), {}).get('data', {})\n"
            "        diagnostic.update(principal=source.get('principal'), assertion_kind=source.get('assertion_kind'))\n" + auth,
            'unauthenticated-diagnostic-is-empty')
    signing('signing-leak-revision-before-auth', 'control_signer.py', auth,
            "        diagnostic['delegation_revision'] = state['delegation_version']\n" + auth,
            'unauthenticated-diagnostic-is-empty')
    envelope_check = "        if problems:\n            raise K.Refused('missing-attribution')"
    signing('signing-ignore-envelope-problems', 'control_signer.py', envelope_check,
            "        if False:\n            raise K.Refused('missing-attribution')", 'personal-envelope-expiry')
    signing('signing-ignore-envelope-expiry', 'control_signer.py', envelope_check,
            "        if any('expired' not in problem for problem in problems):\n            raise K.Refused('missing-attribution')",
            'personal-envelope-expiry')
    signing('signing-copy-envelope-coordinates', 'control_signer.py',
            "        authority = dict(authority_ids, membership_version=state['membership_version'],",
            "        authority = dict(envelope, membership_version=state['membership_version'],",
            'personal-foreign/store_uuid')
    signing('signing-ignore-coordinate-problems', 'control_signer.py', envelope_check,
            "        if any('wrong repository, domain or store' not in problem for problem in problems):\n"
            "            raise K.Refused('missing-attribution')", 'personal-foreign/domain_uuid')
    # VELDO-0036: each reservation assertion has two independently driven defects.
    def reservation(name, module, old, new, row):
        add(36, name, '58_veldo_0036_reservations.py', module, old, new,
            ['reservations/' + row])

    reservation('reservation-final-reuses-partial', 'control_reservations.py',
                "if unit in p['usage']:\n                        value['charge'][unit] = p['usage'][unit]",
                "if unit in value['observed']:\n                        value['charge'][unit] = value['observed'][unit]",
                'partial-final-retained')
    reservation('reservation-final-forgets-reservation', 'control_reservations.py',
                "            elif p['final']:",
                "            elif p['final']:\n                value['charge']['wall_seconds'] = p['usage'].get('wall_seconds', 0)",
                'partial-final-retained')
    reservation('reservation-report-before-enforcement', 'control_reservation_runtime.py',
                "        try:\n            reached = now - active['start'] >= active['wall_seconds']\n            if reached:\n                self._stop(active)\n            receipt = self.reservations.report(command_id, invocation, sequence, usage,\n                                               now=now, final=final, outcome=outcome)\n",
                "        receipt = self.reservations.report(command_id, invocation, sequence, usage,\n                                           now=now, final=final, outcome=outcome)\n        try:\n            reached = now - active['start'] >= active['wall_seconds']\n            if reached:\n                self._stop(active)\n", 'report-failure-stops')
    reservation('reservation-report-error-keeps-worker', 'control_reservation_runtime.py',
                "            # Reporting, authorization and policy reads must fail closed for the worker.\n            self._stop(active)",
                "            # Defect: report failure leaves the worker running.\n            pass",
                'report-failure-stops')
    reservation('reservation-active-ignores-wall-cap', 'control_reservation_runtime.py',
                "                for unit, cap in policy['caps'].items():",
                "                for unit, cap in policy['caps'].items():\n                    if unit == 'wall_seconds':\n                        continue",
                'current-caps')
    reservation('reservation-active-skips-project-cap', 'control_reservation_runtime.py',
                "            for policy in self.reservations._policies(call['context'], records):",
                "            for policy in self.reservations._policies(call['context'], records):\n                if policy['scope'] == 'project':\n                    continue",
                'current-caps')
    reservation('reservation-extra-slot', 'control_reservations.py',
                "if balance[unit] + wanted.get(unit, 0) > cap:",
                "if balance[unit] + wanted.get(unit, 0) > cap + 1:", 'ceilings')
    reservation('reservation-ignore-ceiling', 'control_reservations.py',
                "if balance[unit] + wanted.get(unit, 0) > cap:",
                "if False:", 'ceilings')
    reservation('reservation-check-outside-transaction', 'control_reservations.py',
                "        self._command = command",
                "        self._command = command\n"
                "        if action in ('worker', 'invocation'):\n"
                "            snapshot = self._records()\n"
                "            self._check = lambda context, wanted, records, now: type(self)._check(self, context, wanted, snapshot, now)",
                'atomic-last-slot')
    reservation('reservation-ignore-capacity-and-count', 'control_reservations.py',
                "if balance[unit] + wanted.get(unit, 0) > cap:",
                "if unit not in ('capacity', 'invocations') and balance[unit] + wanted.get(unit, 0) > cap:",
                'atomic-last-slot')
    reservation('reservation-follow-on-after-launch', 'control_reservation_runtime.py',
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                "            if boundary == 'follow_on':\n                self.launch(invocation, configuration)\n"
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                'pre-call-order')
    reservation('reservation-retry-after-launch', 'control_reservation_runtime.py',
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                "            if boundary == 'retry':\n                self.launch(invocation, configuration)\n"
                "            receipt = self.reservations.reserve_call(command_id, dispatch, invocation, boundary, wall_seconds, now=now)",
                'pre-call-order')
    reservation('reservation-ignore-wall-time', 'control_reservation_runtime.py',
                "            reached = now - active['start'] >= active['wall_seconds']",
                "            reached = False", 'usage-controls')
    reservation('reservation-ignore-window', 'control_reservations.py',
                "            for window in policy.get('windows', {}).values():",
                "            for window in ():", 'usage-controls')
    reservation('reservation-duplicate-settlement', 'control_reservations.py',
                "                return {}  # Duplicate sequence under a different delivery command settles nothing twice.",
                "                value['charge'] = {k: v * 2 for k, v in value['charge'].items()}\n"
                "                return {target: {'kind': 'subscription_reservation', 'data': value}}",
                'settles-once')
    reservation('reservation-double-reported-usage', 'control_reservations.py',
                "value['charge'][unit] = max(value['charge'].get(unit, 0), amount)",
                "value['charge'][unit] = max(value['charge'].get(unit, 0), amount) + amount",
                'settles-once')
    reservation('reservation-timeout-frees-exposure', 'control_reservations.py',
                "            elif p['final']:",
                "            elif p['final']:\n"
                "                if p['outcome'] == 'timeout':\n                    value['charge'] = dict.fromkeys(USAGE, 0)",
                'unknown-retained')
    reservation('reservation-cancel-frees-exposure', 'control_reservations.py',
                "            elif p['final']:",
                "            elif p['final']:\n"
                "                if p['outcome'] == 'cancelled':\n                    value['charge'] = dict.fromkeys(USAGE, 0)",
                'unknown-retained')
    reservation('reservation-parent-exit-releases-slot', 'control_reservations.py',
                "            if observation.get('terminated') is not True:",
                "            if False:", 'retirement')
    reservation('reservation-ignore-cleanup', 'control_reservations.py',
                "            if observation.get('cleaned') is not True:",
                "            if False:", 'retirement')
    # VELDO-0035: each declared falsifier and a distinct second mutation target
    # the same assertion row; the gate additionally drives an unchanged copy.
    def snapshots(name, module, old, new, row):
        add(35, name, '58_veldo_0035_snapshots.py', module, old, new, ['snapshots/' + row])

    snapshots('snapshot-project-only', 'control_readset.py',
              '                for name in sorted(set(current) | set(accepted)):',
              "                for name in ['entity/project']:", 'stale-input')
    snapshots('snapshot-ignore-collections', 'control_readset.py',
              '                    if current.get(name) != accepted.get(name):',
              "                    if not name.startswith('collection/') and current.get(name) != accepted.get(name):",
              'stale-input')
    snapshots('snapshot-checkout-bytes', 'control_snapshot.py',
              '    return body\n', '    return (Path(repo) / path).read_bytes()\n', 'accepted-bytes')
    snapshots('snapshot-head-bytes', 'control_snapshot.py',
              '    return body\n',
              "    return _git_process.check_output(['git', '-C', str(repo), 'cat-file', 'blob', 'HEAD:' + path])\n",
              'accepted-bytes')
    snapshots('snapshot-working-status', 'control_snapshot.py',
              '        result[safe_path(path)] = canonical(value)',
              '        result[safe_path(path)] = (Path(repo) / path).read_bytes()', 'materialized-revision')
    snapshots('snapshot-wrong-watermark', 'control_snapshot.py',
              "'accepted_commit': snapshot['accepted_commit'], 'watermark': snapshot['watermark'],",
              "'accepted_commit': snapshot['accepted_commit'], 'watermark': snapshot['watermark'] + 1,",
              'materialized-revision')
    snapshots('snapshot-unguarded-connection', 'control_store.py',
              '        if "snapshot_id" in command["parameters"] and "transaction_transition" not in reg:',
              '        if False:', 'connection-bound')
    snapshots('snapshot-deferred-transaction', 'control_readset.py',
              '        if not conn.in_transaction or not conn.command_transaction:',
              '        if not conn.in_transaction:', 'transaction-bound')
    snapshots('snapshot-allow-path-ancestors', 'control_snapshot.py',
              '            str(parent) in inventory for path in paths for parent in PurePosixPath(path).parents):',
              '            False for path in paths for parent in PurePosixPath(path).parents):',
              'path-prefix-inventory')
    snapshots('snapshot-check-only-direct-parent', 'control_snapshot.py',
              'for parent in PurePosixPath(path).parents):',
              'for parent in [PurePosixPath(path).parent]):', 'path-prefix-inventory')
    snapshots('snapshot-skip-empty-commit-validation', 'control_readset.py',
              "        SN.commit_id(self.repo, data['commit'])",
              "        if data['documents']:\n            SN.commit_id(self.repo, data['commit'])", 'status-only-commit')
    snapshots('snapshot-accept-noncommit-id', 'control_snapshot.py',
              '    if result.returncode or result.stdout.decode().strip() != commit:',
              '    if False:', 'status-only-commit')
    # VELDO-0037: each declared falsifier and a distinct second mutation turn the same named
    # row red; the gate additionally drives an unchanged copy. Two further rows get one each.
    def aliases(name, module, old, new, row):
        add(37, name, '59_veldo_0037_aliases.py', module, old, new, [row])

    aliases('alias-checkout-maximum', 'control_alias.py',
            "        number = kind['next']\n",
            "        number = 1 + maximum([p.relative_to(request['workspace']).as_posix()"
            " for p in Path(request['workspace']).rglob('*')], kind)\n", 'aliases/stale-checkouts')
    aliases('alias-counter-not-advanced', 'control_alias.py',
            'dict(kind, next=number + 1)', 'dict(kind, next=number)', 'aliases/stale-checkouts')
    aliases('document-ignore-digest', 'control_alias.py',
            "        if current['digest'] != p['expected_digest']:", '        if False:',
            'documents/stale-overwrite')
    aliases('document-current-version', 'control_alias.py',
            "            expected = request['expected_version']\n", '            expected = head_version\n',
            'documents/stale-overwrite')
    aliases('publication-altered-bytes', 'control_document.py',
            '                    output.write(body)\n                    output.flush()\n'
            '                    os.fsync(output.fileno())\n'
            '                observed = SN.digest(_read_at(parent, temporary, path))\n',
            "                    output.write(body + b'.')\n                    output.flush()\n"
            '                    os.fsync(output.fileno())\n                observed = digest\n',
            'publication/accepted-documents')
    aliases('publication-normalized-newlines', 'control_document.py',
            '                output.write(body)\n',
            "                output.write(body.replace(b'\\r\\n', b'\\n'))\n", 'publication/accepted-documents')
    aliases('reader-trusts-record', 'control_document.py',
            '    observed = SN.digest(body)\n', "    observed = obligation['observed_digest']\n",
            'publication/tampered-refused')
    # Review defects: every row gets its reintroducing mutation and a second, distinct one.
    aliases('publication-follow-parent-symlink', 'control_document.py',
            "_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW | getattr(os, 'O_CLOEXEC', 0)",
            "_DIRECTORY = os.O_RDONLY | os.O_DIRECTORY | getattr(os, 'O_CLOEXEC', 0)",
            'publication/no-symlink-escape')
    aliases('reader-follows-links', 'control_document.py',
            "        body = read_exact(os.path.realpath(root), data['path'])\n",
            "        body = (Path(root) / data['path']).read_bytes()\n", 'publication/no-symlink-escape')
    aliases('alias-overlap-unchecked', 'control_alias.py',
            '            if _meet(_items(data), _items(other)):', '            if False:', 'aliases/one-path-per-kind')
    aliases('alias-overlap-ignores-directories', 'control_alias.py',
            'def _meet(first, second, directories=True):', 'def _meet(first, second, directories=False):',
            'aliases/one-path-per-kind')
    aliases('alias-trusts-first-number', 'control_alias.py',
            '        elif first < floor:', '        elif False:', 'aliases/historical-floor')
    aliases('alias-floor-ignores-history', 'control_alias.py',
            "    for command in (['ls-tree', '-r', '-z', '--name-only', commit],\n"
            "                    ['log', '-m', '-z', '--no-renames', '--format=', '--name-only', commit]):",
            "    for command in (['ls-tree', '-r', '-z', '--name-only', commit],):", 'aliases/historical-floor')
    aliases('alias-skip-unit-id', 'control_alias.py',
            "        problem = CLAIM.unit_id_problem(alias_for(data, data['next']))\n", '        problem = None\n',
            'aliases/invalid-unit-id')
    return result


def materialize(case, mode, directory, root=ROOT):
    """Own case paths, exact replacement and file/directory copies for every driver.

    Digests describe the actual module bytes, even when the suite receives a directory.
    Baselines use the original input; no-op and mutant copies never edit that input.
    """
    if mode not in ('baseline', 'noop', 'mutant'):
        raise ValueError('unknown mutation mode: ' + mode)
    fixture = case.get('fixture') is True
    base = root / 'scripts/fixtures' if fixture else root / '.veldo'
    source = base / case['module']
    before = source.read_bytes()
    old, new = case['old'].encode(), case['new'].encode()
    count = before.count(old)
    if count != 1:
        raise RuntimeError((case['name'], 'mutation anchor moved', count))
    mutant = None
    after = before
    if mode != 'baseline':
        destination = Path(directory)
        destination.mkdir(parents=True, exist_ok=True)
        mutant = destination / ('fixtures' if fixture else case['module'])
        if fixture:
            shutil.copytree(base, mutant, ignore=shutil.ignore_patterns('__pycache__'))
        target = mutant / case['module'] if fixture else mutant
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(before if mode == 'noop' else before.replace(old, new))
        after = target.read_bytes()
    return dict(source=source, mutant=mutant, replacement_count=count,
                old_digest=hashlib.sha256(before).hexdigest(),
                new_digest=hashlib.sha256(after).hexdigest())


def worker(case, mutant=None):
    """Capture every assertion, including the shared preamble, with exact row identities."""
    shared = ROOT / 'scripts/suites/shared.py'
    rows = []
    ns = {'__file__': str(shared),
          '__observe__': lambda name, condition: rows.append([name.split(':', 1)[0], bool(condition)])}
    tree = ast.parse(shared.read_text(), str(shared))
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == 'expect':
            node.body = ast.parse('__observe__(name, condition)').body
    with contextlib.redirect_stdout(io.StringIO()):
        exec(compile(ast.fix_missing_locations(tree), str(shared), 'exec'), ns)
        suite = ROOT / 'scripts/suites' / case['suite']
        source = suite.read_text()
        if case.get('fixture'):
            if mutant:
                source = source.replace('ROOT / "scripts" / "fixtures"',
                                        '__import__("pathlib").Path(' + repr(mutant) + ')')
        elif mutant:
            anchor = 'ROOT / ".veldo" / "' + case['module'] + '"'
            if not source.count(anchor):
                raise RuntimeError('suite production-copy anchor moved')
            source = source.replace(anchor, '__import__("pathlib").Path(' + repr(mutant) + ')')
        ns['__suite_file__'] = str(suite)
        exec(compile(source, str(suite), 'exec'), ns)
    return {'count': len(rows), 'observations': rows,
            'row_names': [name for name, _ in rows],
            'failed_rows': [name for name, ok in rows if not ok],
            'targets': {label: [ok for name, ok in rows if name.split()[-1] == label]
                        for label in case['rows']}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--finding', type=int, choices=(1, 2, 3, 5, 6, 12, 27, 35, 36, 37, 118, 119, 120))
    parser.add_argument('--diff-dir', type=Path, help='retain exact applied mutation diffs')
    parser.add_argument('--worker')
    parser.add_argument('--mutant')
    args = parser.parse_args()
    selected = [c for c in cases() if args.finding is None or c['finding'] == args.finding]
    if args.worker:
        case = next(c for c in selected if c['name'] == args.worker)
        print(json.dumps(worker(case, args.mutant)))
        return
    baselines = {}
    with tempfile.TemporaryDirectory(prefix='teeth-mutants-') as directory:
        for case in selected:
            prepared = materialize(case, 'mutant', Path(directory) / case['name'])
            mutant = prepared['mutant']
            if args.diff_dir:
                source = prepared['source'].read_text()
                changed = source.replace(case['old'], case['new'])
                relative = str(prepared['source'].relative_to(ROOT))
                args.diff_dir.mkdir(parents=True, exist_ok=True)
                (args.diff_dir / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                    source.splitlines(keepends=True), changed.splitlines(keepends=True), n=0,
                    fromfile='a/' + relative, tofile='b/' + relative)))

            def run(path=None):
                command = [sys.executable, __file__, '--worker', case['name']]
                if path:
                    command += ['--mutant', str(path)]
                proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
                if proc.returncode:
                    raise RuntimeError(f"{case['name']} did not complete its assertions: {proc.stderr}")
                return json.loads(proc.stdout)

            # Keep each case's baseline target observations, not just the suite's exit code.
            honest = run()
            broken = run(mutant)
            assert not honest['failed_rows'], honest
            assert set(honest['row_names']) <= set(broken['row_names']), (honest, broken)
            for label in case['rows']:
                assert honest['targets'][label] == [True], honest
                assert broken['targets'][label] == [False], broken
            baselines[case['suite']] = honest['count']
            print(json.dumps({'finding': case['finding'], 'mutation': case['name'],
                              'baseline': 'green', 'assertions': honest['count'],
                              'red_rows': broken['failed_rows']}), flush=True)
    print(json.dumps({'mutations_rejected': len(selected), 'green_suites': baselines}))


if __name__ == '__main__':
    main()
