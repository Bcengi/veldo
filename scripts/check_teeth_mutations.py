#!/usr/bin/env python3
"""Require the teeth review's named assertions to fail on temporary defective production copies.

Run all findings, or --finding N. Workers run the entire named suite; exceptions, timeouts,
missing rows and process failures are errors, never successful mutation detections.
"""
import argparse
import ast
import concurrent.futures
import contextlib
import difflib
import hashlib
import io
import json
import os
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
    # VELDO-0031: each declared falsifier and an independent defect per criterion.
    def claims(name, module, old, new, row):
        add(31, name, '58_veldo_0031_claims.py', module, old, new, ['claims/' + row])

    claims('claims-ownership-without-unit', 'control_claim.py',
           "'data': dict(u, state='CLAIMED')",
           "'data': dict(u, state=u['state'] if unit == 'unit' else 'CLAIMED')", 'atomic-activation')
    claims('claims-ownership-without-backlog', 'control_claim.py',
           "'data': dict(b, state='ACTIVE')",
           "'data': dict(b, state=b['state'] if unit == 'unit' else 'ACTIVE')", 'atomic-activation')
    claims('claims-ignore-use-generation', 'control_claim.py',
           "    if current.get('generation') != params['generation']:",
           "    if op != 'use' and current.get('generation') != params['generation']:", 'current-generation')
    claims('claims-ignore-use-holder', 'control_claim.py',
           "    if current.get('holder') != holder:",
           "    if op != 'use' and current.get('holder') != holder:", 'current-generation')
    claims('claims-uncertainty-as-contention', 'control_claim_client.py',
           "        if result.get('reason') in ('unanswerable', 'ownership_uncertain', 'missing_authority'):\n            raise CL.ClaimStopped(result['reason'])\n        return result",
           "        if result.get('reason') in ('unanswerable', 'ownership_uncertain', 'missing_authority'):\n            return {'ok': False, 'reason': 'claimed'}\n        return result", 'uncertainty-stop')
    claims('claims-detector-as-owned', 'control_claim.py',
           "        return 'unanswerable'",
           "        return 'owned'", 'uncertainty-stop')
    add(31, 'review-r1-command-crash', '59_veldo_0031_review.py', 'control_claim.py',
        '        if not isinstance(command, dict):\n            command = {}',
        '', ['claims/review-r1'])
    add(31, 'review-r1-signature-crash', '59_veldo_0031_review.py', 'control_claim.py',
        "                or not isinstance(packet.get('signature'), str)",
        '                or False', ['claims/review-r1'])
    add(31, 'review-r2-inspect-skips-consistency', '59_veldo_0031_review.py', 'control_claim.py',
        "            status = ownership(current, u['data'], b['data'])",
        "            status = 'owned' if current.get('holder') else 'unowned'", ['claims/review-r2'])
    add(31, 'review-r2-activation-without-owner', '59_veldo_0031_review.py', 'control_claim.py',
        "        return 'ownership_uncertain' if unit.get('state') in ACTIVE_UNIT_STATES else 'unowned'",
        "        return 'unowned'", ['claims/review-r2'])
    add(31, 'review-r6-private-stop-class', '59_veldo_0031_review.py', 'claim.py',
        'ClaimStopped = _claim_errors.ClaimStopped\n',
        '', ['claims/review-r6'])
    add(31, 'review-r6-routing-wrong-exception', '59_veldo_0031_review.py', 'control_claim_client.py',
        '            raise CL.ClaimStopped(exc.reason) from exc',
        '            raise RuntimeError(exc.reason) from exc', ['claims/review-r6'])
    add(31, 'review-r3-publish-without-use', '59_veldo_0031_review.py', 'lander.py',
        '                    self._check_ownership()',
        '                    pass  # omitted publication ownership check', ['claims/review-r3'])
    add(31, 'review-r3-swallow-heartbeat-stop', '59_veldo_0031_review.py', 'lander.py',
        '                self._hb_error = exc',
        '                self._hb_error = None', ['claims/review-r3'])
    add(31, 'review-r4-cwd-selects-enrollment', '59_veldo_0031_review.py', 'claim.py',
        '        ledgers = [claims_root(root)]',
        "        ledgers = [os.path.join(_enrollment_ledger() or os.sep, 'claims')]", ['claims/review-r4'])
    add(31, 'review-r4-refuse-unrelated-root', '59_veldo_0031_review.py', 'claim.py',
        "            if enrolled:\n                raise ClaimStopped('authority_required')",
        "            if enrolled or root:\n                raise ClaimStopped('authority_required')", ['claims/review-r4'])
    add(31, 'review-r5-expiry-revokes-owner', '59_veldo_0031_review.py', 'control_claim.py',
        "    if live == 'stale' and action in ('renew', 'release'):",
        '    if False:', ['claims/review-r5'])
    add(31, 'review-r5-release-ignores-holder', '59_veldo_0031_review.py', 'control_claim.py',
        "    if current.get('holder') != holder:",
        "    if op != 'release' and current.get('holder') != holder:", ['claims/review-r5'])
    # VELDO-0052: every declared falsifier and a second, different defect for its row, plus a
    # driven defect for every other row the suite asserts.
    def floor(name, module, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', module, old, new, ['eligibility/' + row])

    review_gate = ('            decision = gate.decide("review", sid, context=context, ticket=unit.get("eligibility"))\n'
                   '            if not decision["eligible"]:\n'
                   '                return self._refused("review", sid, decision, verdict=None, shipped=False, landed=False)\n')
    floor('eligibility-review-bypass', 'dispatch.py', review_gate,
          '            pass  # defect: direct review launches without the shared review decision\n',
          'entry-dispatch-review')
    floor('eligibility-review-as-provider-request', 'dispatch.py',
          'gate.decide("review", sid, context=context,', 'gate.decide("provider_request", sid, context=context,',
          'entry-dispatch-review')
    floor('eligibility-status-only-recheck', 'control_eligibility.py',
          '        for label in sorted(set(before) | set(accepted)):',
          "        for label in ['unit']:  # defect: only the unit's own record, its current status",
          'stale-input')
    floor('eligibility-recheck-ignores-collections', 'control_eligibility.py',
          '            elif old != new:',
          "            elif 'members' not in (old or new or {}) and old != new:", 'stale-input')
    floor('eligibility-frontier-bypass', 'frontier.py',
          '            if not decision["eligible"]:\n                return\n',
          '            if False:\n                return\n', 'entry-frontier')
    floor('eligibility-executor-bypass', 'executor.py',
          '        return gate.decide("direct_execution", sid, context=self.context, ticket=ticket)',
          '        return dict(gate.decide("direct_execution", sid, context=self.context, ticket=ticket),\n'
          '                    eligible=True)  # defect: the direct executor ignores every refusal', 'entry-executor')
    floor('eligibility-plan-bypass', 'plan.py',
          '        reasons.extend("eligibility refused: %s" % r for r in decision["refusals"])',
          '        pass  # defect: the direct-execution refusals are dropped', 'entry-plan')
    floor('eligibility-build-bypass', 'dispatch.py',
          '            if not decision["eligible"]:\n                return self._refused("build", sid, decision, reviewed=False)',
          '            if False:\n                return self._refused("build", sid, decision, reviewed=False)',
          'entry-dispatch-build')
    floor('eligibility-publication-bypass', 'dispatch.py',
          '            if not decision["eligible"]:\n                return self._refused("publication",',
          '            if False:\n                return self._refused("publication",', 'entry-publication')
    floor('eligibility-work-no-preclaim-decision', 'work.py',
          '            if gate is not None and not gate.decide("claim", u["spec"], ticket=u.get("eligibility"))["eligible"]:\n'
          '                continue\n', '', 'entry-work-rechecks')
    floor('eligibility-work-no-postclaim-recheck', 'work.py',
          '                if not after["eligible"]:', '                if False:', 'entry-work-rechecks')
    floor('eligibility-enrolled-default-runs', 'control_eligibility.py',
          "        raise Stopped('eligibility_required')", '        return None', 'enrolled-entry-stops')
    floor('eligibility-unregistered-work-entry', 'control_eligibility.py',
          "    ('work.py', 'WorkLoop._claim_next', 'claim'),\n", '', 'registrations-from-call-sites')
    floor('eligibility-ignores-scope', 'control_eligibility.py',
          "            return [] if a.get('scope_digest') == data.get('scope_digest') and a.get('scope_digest') else ['stale_scope']",
          "            return []", 'named-refusals')
    floor('eligibility-refusals-not-pending', 'control_eligibility.py',
          "        self.last[decision['unit']] = outcome", "        self.last[decision['unit']] = 'accepted'",
          'observations')

    def completion(name, module, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', module, old, new, ['completion/' + row])

    completion('completion-manifest-verdict-landed', 'work_state.py',
               '        facts = gate.completion(sid) if gate is not None else None',
               '        facts = (dict(gate.completion(sid), revision_landed=bool(concluded(entry, base, vc=vc, passing=passing)))\n'
               '                 if gate is not None else None)', 'readers-agree')
    completion('completion-frontier-reads-status-text', 'frontier.py',
               '    status = EL.completion_status(EL.gate_for(repo_root or ROOT, eligibility), _status_map(idx))',
               '    status = _status_map(idx)', 'readers-agree')
    completion('completion-any-revision-lands', 'control_eligibility.py',
               "            if CC.fact_problems('revision_landed', r, subject):",
               "            if CC.fact_problems('revision_landed', r, None):", 'readers-agree')
    completion('completion-unregistered-consumer', 'control_eligibility.py',
               "    ('work_state.py', 'completion_view'),\n", '', 'consumers-from-call-sites')

    def calls(name, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', 'control_eligibility.py', old, new, ['reservations/' + row])

    invoke = "                receipt = guard.invoke(command_id or 'call/' + invocation, self.dispatch, invocation, boundary,"
    calls('reservation-review-follow-on-bypass', invoke,
          "                if self.station == 'review' and boundary == 'follow_on':\n"
          "                    guard.launch(invocation, configuration)  # defect: no reservation\n"
          "                    receipt = {'replayed': False}\n"
          "                else:\n  " + invoke, 'forbidden-call-observation')
    refused_call = ("                    raise  # a launch failure after its reservation: outcome unknown, exposure retained\n"
                    "                raise named from error")
    calls('reservation-refusal-fails-open', refused_call,
          "                    raise  # a launch failure after its reservation: outcome unknown, exposure retained\n"
          "                guard.launch(invocation, configuration)  # defect: a refused reservation still launches\n"
          "                receipt = {'replayed': False}", 'forbidden-call-observation')
    calls('reservation-retry-bypass', invoke,
          "                if boundary == 'retry':\n"
          "                    guard.launch(invocation, configuration)  # defect: retries skip the reservation\n"
          "                    receipt = {'replayed': False}\n"
          "                else:\n  " + invoke, 'unknown-usage-retained')
    # VELDO-0052, the 2026-09-23 review: each reproduced defect reintroduced, and a second, different
    # mutation for the same row.
    def review(name, module, old, new, row):
        add(52, name, '60_veldo_0052_eligibility.py', module, old, new, [row])

    review('enrolled-git-error-reads-unenrolled', 'control_eligibility.py',
           "        if _claims_a_repository(repo_root):\n            raise Stopped('enrollment_unanswerable') from error\n"
           "        return False\n",
           "        return False  # defect: any git error reads as not enrolled\n",
           'eligibility/enrollment-git-error-stops')
    review('enrolled-discovery-ignores-ancestors', 'git_process.py',
           "        parent = os.path.dirname(current)\n        if parent == current:\n            return False\n",
           "        return False  # defect: discovery looks only at the directory it was given\n",
           'eligibility/enrollment-git-error-stops')
    review('standalone-lane-reads-front-matter', 'frontier.py',
           '    return fm.get("lane") == "standalone" and _lane_status(fm, status) == "ready"',
           '    return fm.get("lane") == "standalone" and fm.get("status") == "ready"',
           'completion/landed-units-not-reoffered')
    review('review-lane-reads-front-matter', 'frontier.py',
           '        if _lane_status(fm, status) == "review":',
           '        if fm.get("status") == "review":',
           'completion/landed-units-not-reoffered')
    review('status-reader-reads-status-text', 'runstatus.py',
           '        status_by_id = PL._status(eligibility)',
           '        status_by_id = PL.spec_status_by_id()',
           'completion/status-reader-agrees')
    review('status-reader-drops-the-stop', 'runstatus.py',
           '    except EL.Stopped as stop:\n        return [], stop.reason',
           '    except EL.Stopped as stop:\n        return [], None  # defect: the stop reads as an empty burn-down',
           'completion/status-reader-agrees')
    # VELDO-0054 review A: veldo status reads decisions through the Gate, as plan status does.
    review('status-reader-decisions-inline', 'runstatus.py',
           "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = PL._decision_blocks(fm)\n", 'completion/status-reader-agrees')
    review('status-reader-decisions-dropped', 'runstatus.py',
           "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = {}\n", 'completion/status-reader-agrees')
    review('dispatch-without-identity', 'control_eligibility.py',
           '        dispatch = self.open_dispatch(unit, context=context)\n',
           "        dispatch = (context or {}).get('dispatch')  # defect: an identity nobody reserved\n",
           'reservations/work-loop-dispatch-identity')
    review('dispatch-identity-not-reserved', 'control_eligibility.py',
           "                self._reservations().reserve_worker('worker/' + dispatch, dispatch, self.account, project, unit,\n"
           "                                                    now=self.clock())",
           "                pass  # defect: an identity no worker slot was reserved for",
           'reservations/work-loop-dispatch-identity')
    review('executor-launches-unreserved', 'executor.py',
           '            if self.calls is None:\n'
           '                # The dispatcher stops here in the same situation: nothing launches unreserved.\n'
           '                raise EL.Stopped("reservation_required")\n',
           '            if self.calls is None:\n'
           '                gate = None  # defect: run on with no reservation handle and no later station\n',
           'eligibility/executor-station-decisions')
    review('executor-review-skips-review-station', 'executor.py',
           '            context = dict(self.context, reviewer=getattr(self.hooks, "reviewer_identity", None))\n'
           '            return gate.decide("review", sid, context=context, ticket=ticket)\n',
           '            return gate.decide("direct_execution", sid, context=self.context, ticket=ticket)  # defect\n',
           'eligibility/executor-station-decisions')
    recheck = '            current = self._decide(gate, sid, launch, decision)\n'
    review('executor-decides-once', 'executor.py', recheck,
           '            current = decision if launch == "build" else self._decide(gate, sid, launch, decision)  # defect\n',
           'eligibility/executor-rechecks-every-launch')
    review('executor-recheck-without-ticket', 'executor.py', recheck,
           '            current = self._decide(gate, sid, launch, None)  # defect: the recheck forgets what it consumed\n',
           'eligibility/executor-rechecks-every-launch')
    review('entry-gate-not-built', 'control_eligibility.py',
           '    return enrolled_gate(repo_root, trust, observe=observe)\n',
           "    raise Stopped('eligibility_required')  # defect: the production entries build no Gate\n",
           'eligibility/production-entries-build-the-gate')
    review('entry-gate-unverified-binding', 'control_eligibility.py',
           "    if problems:\n        raise Stopped('enrollment_refused:' + problems[0][0])\n",
           "    if False:  # defect: a binding that does not verify still builds a Gate\n"
           "        raise Stopped('enrollment_refused:' + problems[0][0])\n",
           'eligibility/production-entries-build-the-gate')
    # VELDO-0052, the second independent check (r52b): defect g reintroduced, and different defects
    # of the same row (a returned launch keeps its slot; closing forgets the calls' exposure).
    review('slot-opened-before-prelaunch-halts', 'dispatch.py',
           '            if self._calls is None:\n                raise EL.Stopped("reservation_required")\n'
           '            # The executor launches the build',
           '            if self._calls is None:\n                raise EL.Stopped("reservation_required")\n'
           '            self._calls.open_dispatch(sid, context=context)  # defect: reserved before the halts, never retired\n'
           '            # The executor launches the build',
           'reservations/dispatch-slot-retired')
    review('slot-kept-after-launch-returns', 'control_eligibility.py',
           "            raise\n        self.close_dispatch(dispatch, 'completed')\n",
           "            raise\n        # defect: a launch that returned normally keeps its worker slot\n",
           'reservations/dispatch-slot-retired')
    review('slot-close-zeroes-exposure', 'control_eligibility.py',
           "                                   final=True, now=self.clock())",
           "                                   final=True, outcome='not_executed', now=self.clock())  # defect",
           'reservations/dispatch-slot-retired')
    # Defect h reintroduced (a signers file inside the workspace vouches for it), then a relative path
    # accepted, and the containment judged on the unresolved path, so a symlink leads back inside.
    review('trust-accepts-workspace-signers', 'control_eligibility.py',
           "        if any(os.path.commonpath([resolved, area]) == area for area in _workspace_areas(workspace)):\n"
           "            raise Stopped('host_trust_refused:signers_inside_workspace')\n",
           "        pass  # defect: the workspace's own signers file vouches for the workspace\n",
           'eligibility/host-trust-outside-workspace')
    review('trust-accepts-relative-signers', 'control_eligibility.py',
           "        if not os.path.isabs(enrollment_signers):\n"
           "            raise Stopped('host_trust_refused:signers_not_absolute')\n",
           "        pass  # defect: a relative signers path resolves against the process's directory\n",
           'eligibility/host-trust-outside-workspace')
    review('trust-judges-unresolved-path', 'control_eligibility.py',
           "        resolved = os.path.realpath(self.enrollment_signers)\n",
           "        resolved = os.path.abspath(self.enrollment_signers)  # defect: symlinks not followed\n",
           'eligibility/host-trust-outside-workspace')
    # A refusal inside a launch escapes Executor.run again (the defect reintroduced), escapes the
    # dispatcher's review as an error, or halts without the name of what refused.
    review('provider-refusal-escapes-run', 'executor.py',
           '            except EL.Refused as error:\n                codes = "; ".join(',
           '            except EL.Refused as error:\n                if opened:\n'
           '                    raise  # defect: a refusal inside the launch escapes run()\n                codes = "; ".join(',
           'eligibility/provider-refusal-halts')
    review('provider-refusal-escapes-review', 'dispatch.py',
           '                    rv = self._reviewer.review(spec, unit, calls=handle) or {}\n',
           '                    try:\n                        rv = self._reviewer.review(spec, unit, calls=handle) or {}\n'
           '                    except EL.Refused as inner:\n'
           '                        raise RuntimeError(inner.code)  # defect: the refusal escapes as an error\n',
           'eligibility/provider-refusal-halts')
    review('provider-refusal-halt-unnamed', 'executor.py',
           '                        else "reservation refused before %s: %s") % (launch, codes)',
           '                        else "reservation refused before %s: %s") % (launch, "refused")  # defect',
           'eligibility/provider-refusal-halts')
    # r52b probe i: a launch entered without the boundary its calls face (reintroduced), or with that
    # boundary decided for the first cycle only.
    review('launch-skips-call-boundary', 'executor.py',
           '            if current["eligible"]:\n                boundary = self._decide_calls(',
           '            if False:  # defect: the builder is entered whatever its calls will be told\n'
           '                boundary = self._decide_calls(',
           'eligibility/launch-decides-its-calls')
    review('launch-call-boundary-first-cycle-only', 'executor.py',
           '            if current["eligible"]:\n                boundary = self._decide_calls(',
           '            if current["eligible"] and cycle == 1:  # defect\n                boundary = self._decide_calls(',
           'eligibility/launch-decides-its-calls')
    # VELDO-0046: retained Release 1 criteria, two independent defects per named row.
    def notification(name, old, new, row):
        add(46, name, '58_veldo_0046_notifications.py', 'control_notify.py',
            old, new, ['notify/' + row])

    notification('notify-stop-after-handler-failure',
                 "                self._observe('handler', event, 'unknown_outcome', stopped_consumer=consumer)",
                 "                return self._observe('handler', event, 'unknown_outcome', stopped_consumer=consumer)",
                 'subscriber-isolation')
    notification('notify-retry-successful-subscribers',
                 "        return self._observe('consume', event, 'unknown_outcome' if failed else 'delivered',",
                 "        if failed:\n            entry.owed = None  # defective: forget who accepted\n"
                 "        return self._observe('consume', event, 'unknown_outcome' if failed else 'delivered',", 'subscriber-isolation')
    notification('notify-drop-unavailable-first-attempt',
                 "if entry.owed is None and exc.reason != 'service_unavailable':",
                 "if entry.owed is None:", 'first-attempt-retained')
    # At-most-once: the subscriber is marked accepted before its callback returns.
    _dispatch = (
                 '        for consumer in ready:\n'
                 '            try:\n'
                 '                # A handler may mutate its argument; the next handler still sees the journal.\n'
                 '                self.handlers[consumer](json.loads(json.dumps(event)))\n'
                 '            except BaseException as exc:\n'
                 '                # The event stays owed to this subscriber, and to any not yet called, even\n'
                 '                # when an interrupt propagates. Only this subscriber waits out a delay.\n'
                 "                self._observe('handler', event, 'unknown_outcome', stopped_consumer=consumer)\n"
                 '                failed.append(consumer)\n'
                 '                self._defer(consumer)\n'
                 '                if not isinstance(exc, Exception):\n'
                 '                    raise\n'
                 '                continue\n'
                 '            self._accept(entry, consumer)\n'
                 '            delivered.append(consumer)\n')
    notification('notify-accept-before-callback', _dispatch,
                 _dispatch.replace('        for consumer in ready:\n',
                                   '        for consumer in ready:\n            self._accept(entry, consumer)\n')
                 .replace('            self._accept(entry, consumer)\n            delivered.append(consumer)\n',
                          '            delivered.append(consumer)\n'),
                 'first-attempt-retained')
    notification('notify-requeue-failed-at-tail',
                 "                self._defer(consumer)\n",
                 "                self._defer(consumer)\n"
                 "                with self._condition:\n"
                 "                    self._queue.remove(entry)\n"
                 "                    self._queue.append(entry)\n", 'subscriber-order')
    notification('notify-skip-head-of-line',
                 "            blocked |= owed\n", "", 'subscriber-order')
    notification('notify-retry-without-backoff',
                 "return min(self.retry_cap, self.retry_initial * 2.0 ** min(failures - 1, 64))",
                 "return 0.0", 'retry-backoff')
    notification('notify-uncapped-backoff',
                 "return min(self.retry_cap, self.retry_initial * 2.0 ** min(failures - 1, 64))",
                 "return self.retry_initial * 2.0 ** min(failures - 1, 64)", 'retry-backoff')
    notification('notify-retry-not-woken-when-due',
                 "bounds = self._retry_waits(now) + ",
                 "bounds = [] + ", 'retry-backoff')
    notification('notify-unbounded-observations',
                 "            while len(self._observations) > self.observation_limit:\n"
                 "                self._observations.popleft()\n",
                 "", 'retry-backoff')
    notification('notify-unbounded-watermark',
                 "or not 1 <= hint['watermark'] <= 2**63 - 1",
                 "or hint['watermark'] < 1", 'watermark-range')
    notification('notify-reject-valid-max-watermark',
                 "or not 1 <= hint['watermark'] <= 2**63 - 1",
                 "or not 1 <= hint['watermark'] < 2**63 - 1", 'watermark-range')
    notification('notify-before-commit',
                 "        # Only identity crosses the queue. Extra transport payload is not domain data.",
                 "        if 'event' in hint and 'transition' in hint['event']:\n"
                 "            for handler in self.handlers.values():\n"
                 "                handler(hint['event'])\n"
                 "        # Only identity crosses the queue. Extra transport payload is not domain data.",
                 'committed-event')
    notification('notify-omit-committed-wakeup',
                 "                self.notify(self.hint(result))",
                 "                pass  # defective: committed event never signals",
                 'committed-event')
    notification('notify-check-outside-idle-lock',
                 "        with self._condition:\n            while True:\n"
                 "                now = self.clock()\n                work = self._ready(now)\n",
                 "        ready = bool(self._queue)\n"
                 "        with self._condition:\n            while True:\n"
                 "                now = self.clock()\n                work = self._ready(now) if ready else None\n",
                 'event-in-the-gap')
    notification('notify-wait-without-queue-predicate',
                 "                now = self.clock()\n                work = self._ready(now)\n",
                 "                self._condition.wait(None if deadline is None else max(0.0, deadline - self.clock()))\n"
                 "                now = self.clock()\n                work = self._ready(now)\n",
                 'event-in-the-gap')
    notification('notify-trust-invented-event-identity',
                 "        if row[0] != hint['command_id'] or row[1] != hint['record_digest']:",
                 "        if row[1] != hint['record_digest']:", 'fabricated-event')
    notification('notify-trust-invented-event-digest',
                 "        if row[0] != hint['command_id'] or row[1] != hint['record_digest']:",
                 "        if row[0] != hint['command_id']:", 'fabricated-event')
    # VELDO-0064: the declared falsifiers plus a second, different defect per named row.
    def inbox(name, module, old, new, row):
        add(64, name, '60_veldo_0064_inbox.py', module, old, new, [row])

    inbox('inbox-retain-claim-while-waiting', 'control_assignment.py',
          "            if 'release' in params:\n                changes.update(self.claims.transition(params['release'], before))\n",
          "            if 'release' in params:\n                pass  # defective: the claim stays owned while the person is asked\n",
          'inbox/waiting-resources')
    inbox('inbox-requester-keeps-waiting', 'control_assignment.py',
          "'released_claim': released, 'stop_requester': op == 'open'}",
          "'released_claim': released, 'stop_requester': False}",
          'inbox/waiting-resources')
    inbox('projection-discard-message-id', 'control_channel_projection.py',
          "message_id=platform['message_id'],", "message_id=None,",
          'projection/correlation')
    inbox('inbox-admit-displayed-assigned-status', 'control_assignment.py',
          "        if item['problems']:\n            return 'invalid_record', inputs\n",
          "        if item['raw'].get('display_status') == 'assigned':\n            return 'admitted', inputs\n"
          "        if item['problems']:\n            return 'invalid_record', inputs\n",
          'inbox/unauthorized-admission')
    inbox('inbox-admit-without-journal-authority', 'control_assignment.py',
          "        if row is None or row[0] != data['owner'] or written.get('version') != item['version'] \\\n"
          "                or written.get('digest') != item['digest']:\n            return 'missing_authority', inputs\n",
          "", 'inbox/unauthorized-admission')
    inbox('inbox-admit-ignores-owner-membership', 'control_assignment.py',
          "        if not active or owner['principal_type'] != 'person' \\",
          "        if False and owner['principal_type'] != 'person' \\", 'inbox/unauthorized-admission')
    inbox('inbox-index-skips-invalid', 'control_assignment.py',
          "            if item['problems']:\n                entry['category'] = 'invalid'\n",
          "            if item['problems']:\n                continue\n", 'inbox/visible-invalid')
    inbox('inbox-trust-tampered-content', 'control_assignment.py',
          "        if raw is not None and self.store.digest_of({'kind': kind, 'data': raw, 'version': version}) != digest:\n"
          "            problems.append('stored data does not match its committed digest')\n",
          "", 'inbox/visible-invalid')
    # VELDO-0064 review r1: a unit parked on a pending person assignment is not claimable.
    inbox('inbox-park-as-plain-release', 'control_assignment.py',
          "params['release'] = dict(action='park',", "params['release'] = dict(action='release',",
          'inbox/parked-unit-unclaimable')
    inbox('claims-claim-ignores-park', 'control_claim.py',
          "        if op == 'claim' and parked:", "        if False and parked:", 'inbox/parked-unit-unclaimable')
    inbox('inbox-resume-without-admission', 'control_assignment.py',
          "        if reason != 'admitted':\n            raise Refused(reason, 'the assignment does not admit the blocked work')\n",
          "", 'inbox/parked-unit-unclaimable')
    # VELDO-0064 review r2: the parked unit is derived from the requester's own claim.
    inbox('inbox-release-only-named-unit', 'control_assignment.py',
          "            held = self._held_claims(entities, principal)\n",
          "            held = [c for c in self._held_claims(entities, principal)"
          " if c[1].get('unit_id') == content.get('unit_id')]\n", 'inbox/release-derived-from-claim')
    inbox('inbox-open-without-generation-keeps-claim', 'control_assignment.py',
          "        if type(generation) is not int:\n            raise Refused('invalid_input', 'releasing a claim names its generation')\n",
          "        if type(generation) is not int:\n            return None\n", 'inbox/release-derived-from-claim')
    inbox('inbox-open-skips-claim-recheck', 'control_assignment.py',
          "        if params['action'] == 'open':\n            rows = conn.execute(",
          "        if False:\n            rows = conn.execute(", 'inbox/release-derived-from-claim')
    # VELDO-0064 review r5: admission verifies the owner's signature over the exact answer.
    inbox('inbox-admit-skips-answer-signature', 'control_assignment.py',
          "        if not verified:\n            return 'missing_authority', inputs\n", "",
          'inbox/admit-verifies-owner-signature')
    inbox('inbox-admit-unbound-answer-signature', 'control_assignment.py',
          "        if not binds:\n            return 'missing_authority', inputs\n", "",
          'inbox/admit-verifies-owner-signature')
    # VELDO-0064 review r3: the intent is committed before the send; an unknown send never repeats.
    inbox('projection-retry-pending-intent', 'control_channel_projection.py',
          "RETRYABLE = ('refused',)", "RETRYABLE = ('refused', 'pending')", 'projection/intent-before-send')
    inbox('projection-send-before-intent', 'control_channel_projection.py',
          "            intent = self._commit(dict(phase='intent', projection_id=pid, record=record), expected)\n"
          "            completion = self._send(enrollment['chat'], text)\n",
          "            completion = self._send(enrollment['chat'], text)\n"
          "            intent = self._commit(dict(phase='intent', projection_id=pid, record=record), expected)\n",
          'projection/intent-before-send')
    # VELDO-0064 review r4: a differing echoed text keeps the returned identity as an anomaly.
    inbox('projection-mismatch-as-refusal', 'control_channel_projection.py',
          "        found = anomalies(data, platform)\n",
          "        if 'presentation_mismatch' in anomalies(data, platform):\n"
          "            return {pid: {'kind': ENTITY_KIND, 'data': dict(data, outcome='refused', refusal='presentation_mismatch')}}\n"
          "        found = anomalies(data, platform)\n", 'projection/echo-mismatch-kept')
    inbox('projection-ignore-echoed-text', 'control_channel_projection.py',
          "    if platform['text'].encode('utf-8') != record['presentation'].encode('utf-8'):\n        found.append('presentation_mismatch')\n",
          "", 'projection/echo-mismatch-kept')
    # VELDO-0064 review r7: each assignment goes to the chat enrolled for its own owner.
    inbox('projection-one-chat-for-every-owner', 'control_channel_projection.py',
          "        refusal, enrollment = self._enrollment(brief['content']['owner'])\n",
          "        refusal, enrollment = self._enrollment('owner')\n", 'projection/owner-enrolled-chat')
    inbox('projection-enrollment-ignores-principal', 'control_channel_projection.py',
          "    if data.get('principal') != principal:\n        problems.append('the enrollment names another principal')\n",
          "", 'projection/owner-enrolled-chat')
    # VELDO-0064 review r8: a message placed in another chat is a named anomaly, not a projection.
    inbox('projection-ignore-returned-chat', 'control_channel_projection.py',
          "    if platform['chat_id'] != record['enrolled_chat']:\n        found.append('chat_mismatch')\n",
          "", 'projection/returned-chat-checked')
    inbox('projection-record-enrolled-chat', 'control_channel_projection.py',
          "chat_id=platform['chat_id'],", "chat_id=data['enrolled_chat'],", 'projection/returned-chat-checked')
    # VELDO-0064 review r2-s4: only Telegram's own 4xx error answer is a definite refusal.
    range_guard = ("            if not 400 <= exc.code < 500:\n"
                   "                raise EdgeRefused('unknown_outcome', 'HTTP %d is not a definite refusal' % exc.code) from None\n")
    body_guard = ("            if not telegram_refusal(exc, exc.code):\n"
                  "                raise EdgeRefused('unknown_outcome', 'HTTP %d without the Bot API error answer' % exc.code) from None\n")
    inbox('projection-any-http-error-refused', 'control_channel_projection.py', range_guard + body_guard, '',
          'projection/only-telegram-refusal-retried')
    inbox('projection-any-4xx-refused', 'control_channel_projection.py', body_guard, '',
          'projection/only-telegram-refusal-retried')
    inbox('projection-telegram-5xx-refused', 'control_channel_projection.py', range_guard, '',
          'projection/only-telegram-refusal-retried')
    # VELDO-0064 review r2-s5: a malformed reply is an unknown outcome; nothing the edge raises stops the loop.
    inbox('projection-edge-protocol-error-escapes', 'control_channel_projection.py',
          "        except (urllib.error.URLError, http.client.HTTPException, OSError, ValueError) as exc:\n",
          "        except (urllib.error.URLError, OSError, ValueError) as exc:\n", 'projection/protocol-error-unknown')
    inbox('projection-edge-error-stops-loop', 'control_channel_projection.py',
          "        except Exception as exc:\n"
          "            return {'platform': None, 'refusal': None, 'detail': 'the edge raised %s' % type(exc).__name__}\n",
          "", 'projection/protocol-error-unknown')
    inbox('projection-protocol-error-as-refusal', 'control_channel_projection.py',
          "            raise EdgeRefused('unknown_outcome', 'no readable platform answer (%s)' % type(exc).__name__) from None\n",
          "            raise EdgeRefused('channel_refused', 'no readable platform answer (%s)' % type(exc).__name__) from None\n",
          'projection/protocol-error-unknown')
    # VELDO-0064 review r2-s7: an answer verifies against the key active when it was accepted.
    inbox('inbox-admit-current-active-key', 'control_assignment.py',
          "        key = self._answer_key(state, data, row, inputs)\n",
          "        key = self.AC.active_key(state['keyring'], data['owner'], now)\n", 'inbox/answer-survives-key-rotation')
    inbox('inbox-answer-key-from-current-entity', 'control_assignment.py',
          "        key = dict(stored['data'], key_id=kid)\n",
          "        key = dict(state['entities'].get(kid, {}).get('data') or {}, key_id=kid)\n",
          'inbox/answer-survives-key-rotation')
    inbox('inbox-answer-key-ignores-revocation', 'control_assignment.py',
          "            if current.get('revoked_at') is not None and current['revoked_at'] <= at:\n                return None\n",
          "", 'inbox/answer-survives-key-rotation')
    # VELDO-0064 review r2-s6: every parked unit is visible with its assignment and why it is parked.
    inbox('inbox-parked-only-awaiting', 'control_assignment.py',
          "            parked.append({'unit_id'",
          "            if reason != 'awaiting_answer':\n                continue\n            parked.append({'unit_id'",
          'inbox/parked-units-visible')
    inbox('inbox-parked-metric-omitted', 'control_assignment.py',
          "pending=pending, parked=len(parked),",
          "pending=pending, parked=sum(1 for u in parked if u['reason'] == 'awaiting_answer'),",
          'inbox/parked-units-visible')
    inbox('inbox-parked-refusal-shown-ready', 'control_assignment.py',
          "reason = 'ready_to_resume' if admission == 'admitted' else 'answer_not_admitted'",
          "reason = 'ready_to_resume'", 'inbox/parked-units-visible')
    # VELDO-0054: every declared falsifier and a second, different defect for its row, plus a
    # driven defect for every other row suite 62 asserts.
    def decisions(name, module, old, new, row):
        add(54, name, '62_veldo_0054_decisions.py', module, old, new, ['decisions/' + row])

    framing = "    if not _is_str(framing) or framing != record.get('framing_digest'):\n"
    decisions('framing-receipt-without-digest', 'control_decision_dependency.py', framing,
              "    if framing is not None and framing != record.get('framing_digest'):\n", 'wrong-framing')
    decisions('framing-shape-only', 'control_decision_dependency.py', framing,
              "    if not _is_str(framing):\n", 'wrong-framing')
    decisions('subject-currency-ignored', 'control_decision_dependency.py',
              "    if current is None or subject.get('digest') != current:\n", "    if False:\n", 'exact-binding')
    decisions('floor-stations-skip-decisions', 'control_eligibility.py',
              "            return self._decision_codes(unit, inputs)\n", "            return []\n", 'exact-binding')
    decisions('inline-status-as-ruling', 'control_decision_dependency.py',
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n",
              "    if isinstance(record, dict) and record.get('state') == 'settled':\n        return []\n"
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n",
              'unsigned-resolution')
    decisions('unsigned-settlement-accepted', 'control_decision_dependency.py',
              "        if verify is None or not isinstance(body, dict) or not _is_str(signature) or not _is_str(signer):\n"
              "            continue\n",
              "        if isinstance(body, dict) and not _is_str(signature):\n            verified.append(body)\n            continue\n"
              "        if verify is None or not isinstance(body, dict) or not _is_str(signer):\n            continue\n",
              'unsigned-resolution')
    decisions('plan-inline-resolution-honored', 'plan.py',
              '        if isinstance(d, dict):\n            for s in d.get("blocks") or []:\n',
              '        if isinstance(d, dict) and d.get("status") != "resolved":\n            for s in d.get("blocks") or []:\n',
              'unsigned-resolution')
    decisions('ambiguous-settlement-first', 'control_decision_dependency.py',
              "    if len(current) > 1:\n        return ['ambiguous_decision:' + rid]\n", "", 'named-blockers')
    decisions('unsupported-obligation-presumed', 'control_decision_dependency.py',
              "SUPPORTED_OBLIGATIONS = ()", "SUPPORTED_OBLIGATIONS = ('tripwire', 'adversarial_decision_review')",
              'named-blockers')
    decisions('missing-reference-ignored', 'control_decision_dependency.py',
              "            codes.append('missing_decision:%s' % ref)\n", "            pass\n", 'named-blockers')
    decisions('frontier-inline-decisions', 'frontier.py',
              "        blocked = PL._decision_blocks(fm, gate)\n", "        blocked = PL._decision_blocks(fm)\n",
              'named-blockers')
    decisions('run-check-ignores-file-references', 'plan.py',
              '        reasons.extend("decision refused: %s" % r for r in gate.decision_blockers(spec_id, references=refs)\n'
              '                       if r not in decision["refusals"])\n', '', 'named-blockers')
    decisions('scope-binding-ignored', 'control_decision_dependency.py',
              "    problems = []\n    if body.get('subject') != record.get('subject'):\n",
              "    return []\n    problems = []\n    if body.get('subject') != record.get('subject'):\n", 'scope-binding')
    decisions('scope-target-may-differ', 'control_decision_dependency.py',
              "    if body.get('scope_digest') != scope_digest(record.get('scope')) \\\n"
              "            or (record.get('scope') or {}).get('target') != (record.get('subject') or {}).get('id'):\n",
              "    if body.get('scope_digest') != scope_digest(record.get('scope')):\n", 'scope-binding')
    decisions('consumer-unregistered', 'control_decision_dependency.py',
              "    ('control_eligibility.py', 'Gate.decision_blockers'),\n", "", 'consumers-from-call-sites')
    decisions('production-trust-not-wired', 'control_eligibility.py',
              "                settlement_trust=settlements)\n", "                settlement_trust=None)\n",
              'production-gate-verifies')
    decisions('taxonomy-unbound-unknown', 'control_eligibility.py',
              "    'unbound_decision': 'stale_subject', 'decision_ruling': 'missing_authority',\n",
              "    'decision_ruling': 'missing_authority',\n", 'observations')
    decisions('status-reader-inline-decisions', 'runstatus.py',
              "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = PL._decision_blocks(fm)\n", 'status-reader-agrees')
    decisions('status-reader-ignores-decisions', 'runstatus.py',
              "            blocked = PL._decision_blocks(fm, PL.EL.gate_for(Path(root), eligibility))\n", "            blocked = {}\n", 'status-reader-agrees')
    # VELDO-0054 review B: malformed records are named invalid_input for the unit they concern.
    decisions('invalid-record-not-observed', 'control_eligibility.py',
              "                self._invalid_record(identity, 'decision')\n", "                pass\n",
              'malformed-records-named')
    decisions('record-invalid-ignored', 'control_decision_dependency.py',
              "    if invalid:\n        return invalid\n", "", 'malformed-records-named')
    decisions('settlement-invalid-ignored', 'control_decision_dependency.py',
              "    if malformed:\n        return malformed\n", "", 'malformed-records-named')
    decisions('reference-invalid-dropped', 'control_decision_dependency.py',
              "            codes.append('invalid_input:decision_reference')\n", "            continue\n",
              'malformed-records-named')
    # VELDO-0054 review 2, item 1: an unhashable subject field is named; veldo status names its stop.
    decisions('subject-digest-type-unchecked', 'control_decision_dependency.py',
              "all(_is_str(subject.get(k)) for k in ('kind', 'id', 'digest'))",
              "all(_is_str(subject.get(k)) for k in ('kind', 'id'))", 'malformed-subject-named')
    decisions('subject-kind-type-unchecked', 'control_decision_dependency.py',
              "all(_is_str(subject.get(k)) for k in ('kind', 'id', 'digest'))",
              "all(_is_str(subject.get(k)) for k in ('id', 'digest'))", 'malformed-subject-named')
    decisions('status-stop-crashes', 'runstatus.py',
              '    except Exception as error:  # noqa: BLE001 - a burn-down it cannot build is named, never a crash\n',
              '    except ZeroDivisionError as error:  # defect: any other failure escapes\n', 'status-names-its-stop')
    decisions('status-stop-unnamed', 'runstatus.py',
              '        return [], "burndown_unanswerable:" + type(error).__name__\n',
              '        return [], None\n', 'status-names-its-stop')
    # Item 2: a malformed blocks holds the unit it names and is recorded.
    decisions('malformed-blocks-govern-nothing', 'control_decision_dependency.py',
              "    named = _named_ids(blocks) if blocks_malformed(record) else set(blocks)\n",
              "    named = set(blocks) if _str_list(blocks) else set()\n", 'malformed-blocks-held')
    decisions('malformed-blocks-unrecorded', 'control_eligibility.py',
              "                self._invalid_record(identity, 'blocks')\n", "                pass\n",
              'malformed-blocks-held')
    # Item 3: a wrong-typed schema is invalid_input, decided before unsupported and unresolved.
    decisions('schema-type-unchecked', 'control_decision_dependency.py',
              "    for name, ok in (('schema', record.get('schema') is None or isinstance(record.get('schema'), str)),\n"
              "                     ('decision_id',",
              "    for name, ok in (('decision_id',", 'invalid-before-unsupported')
    decisions('invalid-after-unresolved', 'control_decision_dependency.py',
              "    invalid = record_invalid(rid, record)\n    if invalid:\n        return invalid\n"
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n"
              "    if not mine:\n        return ['unresolved_decision:' + rid]\n",
              "    mine = [(sid, s) for sid, s in settlements if isinstance(s, dict) and s.get('decision') == rid]\n"
              "    if not mine:\n        return ['unresolved_decision:' + rid]\n"
              "    problems = record_problems(rid, record) if not record_invalid(rid, record) else []\n"
              "    if problems:\n        return problems\n"
              "    invalid = record_invalid(rid, record)\n    if invalid:\n        return invalid\n",
              'invalid-before-unsupported')
    # VELDO-0054 review 3, item 1: blocks walked without recursion; unexpected faults named.
    decisions('blocks-walk-recursive', 'control_decision_dependency.py',
              "    stack = [value]\n    while stack:\n        current = stack.pop()\n",
              "    stack = []\n    current = value\n    if isinstance(current, list):\n"
              "        for item in current:\n            yield from _named(item)\n        return\n"
              "    stack = [value]\n    while stack:\n        current = stack.pop()\n",
              'deep-blocks-named')
    decisions('decide-raises-unexpected', 'control_eligibility.py',
              "        except Exception as error:  # noqa: BLE001 - VELDO-0054: an unexpected fault is named, never raised\n"
              "            decision['refusals'] = [unexpected(error)]\n", "", 'deep-blocks-named')
    decisions('blockers-raise-unexpected', 'control_eligibility.py',
              "        except Exception as error:  # noqa: BLE001 - VELDO-0054: an unexpected fault is named, never raised\n"
              "            codes = [unexpected(error)]\n", "", 'deep-blocks-named')
    # Item 2: veldo status names a store refusal by its code, as decide does.
    decisions('status-store-refusal-generic', 'runstatus.py',
              '    except store_refusals as error:\n        return [], "refused:" + eligibility.refusal_code(error)\n',
              '', 'status-names-store-refusal')
    decisions('status-store-refusal-code-dropped', 'runstatus.py',
              '        return [], "refused:" + eligibility.refusal_code(error)\n',
              '        return [], "refused:" + type(error).__name__\n', 'status-names-store-refusal')
    decisions('blockers-store-refusal-renamed', 'control_eligibility.py',
              "            codes = [self.refusal_code(error)]\n", "            codes = ['invalid_input:' + error.code]\n",
              'status-names-store-refusal')
    # Item 3: a malformed settlement is invalid_input before its record is judged unsupported.
    decisions('unsupported-before-settlement-invalid', 'control_decision_dependency.py',
              "    malformed = [code for sid, s in mine for code in settlement_invalid(sid, s)]\n"
              "    if malformed:\n        return malformed\n"
              "    problems = record_problems(rid, record)\n    if problems:\n        return problems\n",
              "    problems = record_problems(rid, record)\n    if problems:\n        return problems\n"
              "    malformed = [code for sid, s in mine for code in settlement_invalid(sid, s)]\n"
              "    if malformed:\n        return malformed\n",
              'settlement-invalid-before-unsupported')
    decisions('settlement-signature-type-unchecked', 'control_decision_dependency.py',
              "    for name in ('signature', 'signer'):\n", "    for name in ('signer',):\n",
              'settlement-invalid-before-unsupported')
    # Minor: a blocks string names every id it lists; malformed references are recorded.
    decisions('blocks-string-not-split', 'control_decision_dependency.py',
              "        ids.update(text.replace(',', ' ').split())\n", "        pass\n", 'minor-shapes')
    decisions('plan-reference-unrecorded', 'control_eligibility.py',
              "                self._invalid_record(inputs['plan']['id'], 'open_decisions')\n", "                pass\n",
              'minor-shapes')
    decisions('decision-id-unrecorded', 'control_eligibility.py',
              "                self._invalid_record(identity, 'decision_id')\n", "                pass\n", 'minor-shapes')
    # VELDO-0054 review 4, item 1: signer and signature text the verifier cannot be handed is named.
    decisions('settlement-nul-passed', 'control_decision_dependency.py',
              "    if '\\x00' in text:\n        return False\n", "", 'settlement-text-encodable')
    decisions('settlement-unencodable-passed', 'control_decision_dependency.py',
              "    try:\n        text.encode('utf-8')\n    except UnicodeEncodeError:\n        return False\n", "",
              'settlement-text-encodable')
    # Item 2: a named stop under decide propagates as the stop it is.
    decisions('decide-holds-a-stop', 'control_eligibility.py',
              "            decision['refusals'] = ['unavailable_service:store']\n        except Stopped:\n"
              "            raise  # a named stop is the caller's, never a unit hold\n",
              "            decision['refusals'] = ['unavailable_service:store']\n", 'stops-propagate')
    decisions('blockers-hold-a-stop', 'control_eligibility.py',
              "            codes = ['unavailable_service:store']\n        except Stopped:\n"
              "            raise  # a named stop is the caller's, never a unit hold\n",
              "            codes = ['unavailable_service:store']\n", 'stops-propagate')
    # Item 3: an unexpected fault is named with its message, bounded and on one line.
    decisions('unexpected-message-dropped', 'control_eligibility.py',
              "    return code + '/' + message if message else code\n", "    return code\n", 'unexpected-message')
    decisions('unexpected-message-unbounded', 'control_eligibility.py',
              "    message = message.encode('ascii', 'backslashreplace').decode('ascii')[:UNEXPECTED_MESSAGE_LIMIT]\n",
              "    message = message.encode('ascii', 'backslashreplace').decode('ascii')\n", 'unexpected-message')
    decisions('unexpected-message-multiline', 'control_eligibility.py',
              "    message = ' '.join(str(error).split())\n", "    message = str(error)\n", 'unexpected-message')
    decisions('verifier-unavailable-as-unsigned', 'control_decision_dependency.py',
              "            if not verified and str(detail).startswith('ssh-keygen unavailable'):\n",
              "            if False:\n", 'observations')
    # Scope coverage (landed VELDO-0025, found through VELDO-0064's review): a plain-string inner scope
    # such as a repository id was read as the empty set, so every named scope covered it.
    def scope(name, old, new, rows=('membership/scope-covers-named-string',)):
        add(25, name, '61_scope_covers.py', 'control_membership.py', old, new, list(rows))
        result[-1]['siblings'] = True

    scope('scope-string-inner-as-empty',
          '    if isinstance(scope, str):\n        return {scope}\n',
          '    if isinstance(scope, str):\n        return set()\n')
    scope('scope-malformed-as-empty',
          '    if o is _MALFORMED or i is _MALFORMED:\n        return False\n',
          '    if o is _MALFORMED or i is _MALFORMED:\n        o = set() if o is _MALFORMED else o\n        i = set() if i is _MALFORMED else i\n')
    scope('scope-star-list-not-universal',
          '        return None if "*" in scope else set(scope)\n',
          '        return set(scope)\n', ('membership/scope-forms-agree',))
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
        elif case.get('siblings') is True:
            # A module that loads its siblings by its own path (control_membership loads
            # authority_contract and control_store next to itself) gets a whole .veldo copy.
            shutil.copytree(base, destination / 'veldo', ignore=shutil.ignore_patterns('__pycache__'))
            mutant = destination / 'veldo' / case['module']
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
    parser.add_argument('--finding', type=int, choices=(1, 2, 3, 5, 6, 12, 25, 27, 31, 35, 36, 46, 52, 54, 64, 118, 119, 120))
    parser.add_argument('--diff-dir', type=Path, help='retain exact applied mutation diffs')
    parser.add_argument('--worker')
    parser.add_argument('--mutant')
    parser.add_argument('--jobs', type=int, default=min(8, os.cpu_count() or 1),
                        help='mutant runs in parallel (the honest run is once per suite)')
    args = parser.parse_args()
    selected = [c for c in cases() if args.finding is None or c['finding'] == args.finding]
    if args.worker:
        case = next(c for c in selected if c['name'] == args.worker)
        print(json.dumps(worker(case, args.mutant)))
        return
    def run(case, path=None):
        command = [sys.executable, __file__, '--worker', case['name']]
        if path:
            command += ['--mutant', str(path)]
        proc = subprocess.run(command, capture_output=True, text=True, timeout=120)
        if proc.returncode:
            raise RuntimeError(f"{case['name']} did not complete its assertions: {proc.stderr}")
        return json.loads(proc.stdout)

    def targets(observed, case):
        return {label: [ok for name, ok in observed['observations'] if name.split()[-1] == label]
                for label in case['rows']}

    baselines = {}
    with tempfile.TemporaryDirectory(prefix='teeth-mutants-') as directory:
        prepared = {}
        for case in selected:
            prepared[case['name']] = materialize(case, 'mutant', Path(directory) / case['name'])
            if args.diff_dir:
                source = prepared[case['name']]['source'].read_text()
                changed = source.replace(case['old'], case['new'])
                relative = str(prepared[case['name']]['source'].relative_to(ROOT))
                args.diff_dir.mkdir(parents=True, exist_ok=True)
                (args.diff_dir / (case['name'] + '.diff')).write_text(''.join(difflib.unified_diff(
                    source.splitlines(keepends=True), changed.splitlines(keepends=True), n=0,
                    fromfile='a/' + relative, tofile='b/' + relative)))
        # The honest run of a suite does not depend on the mutant, so each suite runs honestly ONCE
        # and every case of it is judged against that run; the mutant runs are independent and run
        # in parallel. Each case's own targets are taken from the shared observations.
        first = {}
        for case in selected:
            first.setdefault(case['suite'], case)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, args.jobs)) as pool:
            honest_runs = {suite: pool.submit(run, case) for suite, case in first.items()}
            broken_runs = {case['name']: pool.submit(run, case, prepared[case['name']]['mutant'])
                           for case in selected}
            for case in selected:
                honest = honest_runs[case['suite']].result()
                broken = broken_runs[case['name']].result()
                assert not honest['failed_rows'], honest
                assert set(honest['row_names']) <= set(broken['row_names']), (honest, broken)
                for label in case['rows']:
                    assert targets(honest, case)[label] == [True], (case['name'], label, honest['failed_rows'])
                    assert targets(broken, case)[label] == [False], (case['name'], label, broken['failed_rows'])
                baselines[case['suite']] = honest['count']
                print(json.dumps({'finding': case['finding'], 'mutation': case['name'],
                                  'baseline': 'green', 'assertions': honest['count'],
                                  'red_rows': broken['failed_rows']}), flush=True)
    print(json.dumps({'mutations_rejected': len(selected), 'green_suites': baselines}))


if __name__ == '__main__':
    main()
