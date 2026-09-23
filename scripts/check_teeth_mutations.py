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
    # VELDO-0043 AC3: the declared falsifier and two different defects target the isolated-
    # enforcement row (one each only the run, and only the static closure, can see); graph start
    # without a runtime has two of its own. The gate additionally drives an unchanged copy.
    def graph(name, module, old, new, row):
        add(43, name, '59_veldo_0043_graph.py', module, old, new, ['graph/' + row])

    graph('graph-authorization-imports-langgraph', 'authorization.py',
          'from pathlib import Path\nimport json\n',
          'from pathlib import Path\nimport json\nimport langgraph\n', 'isolated-enforcement')
    graph('graph-authorization-dynamic-runtime-import', 'authorization.py',
          '    req = request if isinstance(request, dict) else {}\n',
          "    __import__('lang' + 'graph')\n    req = request if isinstance(request, dict) else {}\n",
          'isolated-enforcement')
    graph('graph-authorization-unexercised-runtime-import', 'authorization.py',
          '        spec = importlib.util.spec_from_file_location("veldo_two_key_authz", p)\n',
          '        import langgraph.graph\n'
          '        spec = importlib.util.spec_from_file_location("veldo_two_key_authz", p)\n',
          'isolated-enforcement')
    graph('graph-start-without-runtime-launches', 'control_graph.py',
          '    if not available(runtime):\n', '    if False:\n', 'start-unavailable')
    graph('graph-start-unavailable-mislabelled', 'control_graph.py',
          "        raise Refused('runtime_unavailable', 'no graph runtime is installed for this operation",
          "        raise Refused('unknown_outcome', 'no graph runtime is installed for this operation",
          'start-unavailable')
    # VELDO-0043 AC1 and AC2 against the actual installed LangGraph: each declared falsifier, a
    # second different defect per row, and two for the tracing-off and typed-proposal rows.
    graph('graph-runner-emits-langgraph-object', 'control_graph_langgraph.py',
          '        body = json.dumps(closed(reply), allow_nan=False)\n',
          "        body = json.dumps(reply, allow_nan=False, default=lambda o: {'__class__': "
          "type(o).__module__ + '.' + type(o).__qualname__, 'repr': repr(o)})\n", 'runtime/plain-data')
    graph('graph-runner-tuple-as-plain', 'control_graph_langgraph.py',
          '    if kind is list:\n', '    if isinstance(value, (list, tuple)):\n', 'runtime/plain-data')
    graph('graph-child-inherits-working-directory', 'control_graph.py',
          'cwd=str(empty),', 'cwd=None,', 'authority/no-direct-write')
    graph('graph-child-inherits-store-descriptor', 'control_graph.py',
          'close_fds=True,', 'close_fds=False,', 'authority/no-direct-write')
    graph('graph-runner-accepts-untyped-assertion', 'control_graph_langgraph.py',
          '            if untyped:\n', '            if False:\n', 'authority/typed-proposals-only')
    graph('graph-untyped-proposal-read-as-priority', 'control_graph.py',
          "            if kind not in PROPOSALS:\n"
          "                raise Refused('invalid_response', where + ': untyped proposal')\n",
          "            if kind not in PROPOSALS:\n"
          "                item, kind = dict(item, type='priority'), 'priority'\n",
          'authority/typed-proposals-only')
    graph('graph-child-inherits-caller-environment', 'control_graph.py',
          'env=dict(ENVIRONMENT),', 'env=None,', 'runtime/tracing-off')
    graph('graph-tracing-switch-on', 'control_graph.py',
          "'LANGSMITH_TRACING_V2': 'false'", "'LANGSMITH_TRACING_V2': 'true'", 'runtime/tracing-off')
    # Review findings F5, F4, F3, F2 and F1 (2026-09-23): two different defects per new row.
    graph('graph-deep-answer-unbounded', 'control_graph.py',
          '    if text_depth(raw) > MAX_DEPTH:\n', '    if False:\n', 'shape/deep-answer')
    graph('graph-deep-answer-unnamed', 'control_graph.py',
          "        raise Refused('invalid_response', 'answer nests deeper than ' + str(MAX_DEPTH))",
          "        raise ValueError('answer nests deeper than ' + str(MAX_DEPTH))", 'shape/deep-answer')
    graph('graph-digest-prefix-only', 'control_graph.py',
          r"DIGEST = re.compile(r'sha256:[0-9a-f]{64}\Z')", r"DIGEST = re.compile(r'sha256:')",
          'shape/closed-request')
    graph('graph-request-path-unchecked', 'control_graph.py',
          '        if looks_like_path(text):\n', '        if False:\n', 'shape/closed-request')
    graph('graph-answer-resume-open', 'control_graph.py',
          "        _resume_shape(value['resume'], 'resume', 'invalid_response')\n", "        pass\n",
          'shape/closed-response')
    graph('graph-answer-notes-any-plain', 'control_graph.py',
          "    if type(value['notes']) is not str or len(value['notes']) > MAX_NOTES:\n",
          "    if len(value['notes']) > MAX_NOTES:\n", 'shape/closed-response')
    graph('graph-suspend-without-graph', 'control_graph_langgraph.py',
          '    return run_cycle(request, workflow, resume)\n',
          "    if request['operation'] == 'suspend':\n"
          "        return _reply(request, 'suspended', {'name': 'langgraph', 'version': '1.2.12'}, resume=resume)\n"
          '    return run_cycle(request, workflow, resume)\n', 'runtime/lifecycle')
    graph('graph-runtime-evidence-unchecked', 'control_graph.py',
          '            if self.evidence is not None and not evidenced(result, self.evidence):\n',
          '            if False:\n', 'runtime/lifecycle')
    graph('graph-runner-launched-in-place', 'control_graph.py',
          "            proc = subprocess.Popen([runtime['python'], '-I', '-B', str(staged)],",
          "            proc = subprocess.Popen([runtime['python'], '-I', '-B', runtime['runner']],",
          'authority/no-direct-write')
    # The stated limit's real falsifier (second review): the adapter makes itself non-dumpable,
    # which closes /proc/<parent>/cwd and fd to a same-account child. It replaces the two earlier
    # notes-path mutants, which broke the row's observation channel rather than the limit.
    graph('graph-proc-closed-by-nondumpable', 'control_graph.py',
          '        staged, work = stage(runtime)\n',
          "        __import__('ctypes').CDLL(None).prctl(4, 0, 0, 0, 0)\n        staged, work = stage(runtime)\n",
          'authority/proc-limit')
    # Second review (2026-09-23): links the adapter did not make, answer encodings, request
    # paths and sizes, process groups, the runtime's pyvenv.cfg.
    graph('graph-stage-links-unchecked', 'control_graph.py',
          "    runners, work = _unlinked(root, 'runners'), _unlinked(root, 'work')\n",
          "    runners, work = root / 'runners', root / 'work'\n"
          "    runners.mkdir(exist_ok=True)\n    work.mkdir(exist_ok=True)\n", 'authority/stage-links')
    graph('graph-stage-link-checks-off', 'control_graph.py',
          "    if path.is_symlink():\n"
          "        raise Refused('runtime_unavailable', 'the stage ' + name + ' is a link the adapter did not make')\n"
          "    if path.exists() and not path.is_dir():\n"
          "        raise Refused('runtime_unavailable', 'the stage ' + name + ' is not a directory')\n"
          "    path.mkdir(mode=0o700, exist_ok=True)\n"
          "    if path.is_symlink() or not path.is_dir() or path.resolve() != path:\n",
          "    if path.exists() and not path.is_dir():\n"
          "        raise Refused('runtime_unavailable', 'the stage ' + name + ' is not a directory')\n"
          "    path.mkdir(mode=0o700, exist_ok=True)\n"
          "    if False:\n", 'authority/stage-links')
    graph('graph-runners-repository-unchecked', 'control_graph.py',
          '    if inside_repository(runners):\n', '    if False:\n', 'authority/stage-links')
    graph('graph-git-not-asked', 'control_graph.py',
          '        if _shaped_like_repository(place) or any(git_finds_repository(start) for start in _discovery_starts(place)):\n',
          '        if _shaped_like_repository(place):\n', 'authority/stage-links')
    graph('graph-runtime-loop-escapes', 'control_graph.py',
          '    except (OSError, RuntimeError, ValueError) as error:\n'
          "        raise Refused('runtime_unavailable', 'the runtime cannot be judged: '",
          '    except OSError as error:\n'
          "        raise Refused('runtime_unavailable', 'the runtime cannot be judged: '", 'authority/stage-shapes')
    graph('graph-stage-loop-escapes', 'control_graph.py',
          '    except (OSError, RuntimeError, ValueError) as error:\n        reason = ',
          '    except (OSError, ValueError) as error:\n        reason = ', 'authority/stage-shapes')
    graph('graph-nul-path-judged', 'control_graph.py',
          "    if '\\x00' in os.fspath(path):\n", '    if False:\n', 'authority/stage-shapes')
    # Round 5 review: undriven behaviors, the reviewer's mutants (renamed graph-*), and new code.
    graph('graph-command-runs-removed', 'control_graph.py',
          "        pieces = value.split(' ')\n",
          '        pieces = []\n', 'runtime/pyvenv-clean')
    graph('graph-command-shlex-removed', 'control_graph.py',
          '            words = shlex.split(value)\n',
          '            words = []\n', 'runtime/pyvenv-clean')
    graph('graph-quote-strip-removed', 'control_graph.py',
          '    elif len(value) >= 2 and value[0] == value[-1] and value[0] in \'"\\\'\':\n',
          '    elif False:\n', 'runtime/pyvenv-clean')
    graph('graph-stage-written-place-dropped', 'control_graph.py',
          "    for place in (Path(os.path.abspath(runtime['stage'])), root):\n",
          '    for place in (root,):\n', 'authority/stage-shapes')
    graph('graph-stage-resolved-place-dropped', 'control_graph.py',
          "    for place in (Path(os.path.abspath(runtime['stage'])), root):\n",
          "    for place in (Path(os.path.abspath(runtime['stage'])),):\n", 'authority/stage-shapes')
    graph('graph-prefix-resolve-dropped', 'control_graph.py',
          'for base in (prefix, prefix.resolve())',
          'for base in (prefix,)', 'authority/stage-shapes')
    graph('graph-refused-workdir-kept', 'control_graph.py',
          "        _remove(path)\n        raise Refused('runtime_unavailable', 'the child working directory",
          "        raise Refused('runtime_unavailable', 'the child working directory", 'authority/stage-links')
    graph('graph-rebuild-message-dropped', 'control_graph.py',
          "'; '.join(problems) + '; rebuild it with: ' + REBUILD_COMMAND)",
          "'; '.join(problems))", 'runtime/pyvenv-clean')
    graph('graph-root-file-check-dropped', 'control_graph.py',
          "    if root.exists() and not root.is_dir():\n        raise Refused('runtime_unavailable', 'the stage root is not a directory')\n",
          '', 'authority/stage-shapes')
    graph('graph-option-values-unjudged', 'control_graph.py',
          "        words += [word.partition('=')[2] for word in words if word.startswith('-') and '=' in word]\n",
          '', 'runtime/pyvenv-clean')
    graph('graph-rebuild-no-restore', 'control_graph_install.py',
          '    except OSError:\n        os.rename(retired, target)\n        raise\n', '    except OSError:\n        raise\n',
          'runtime/rebuild-swap')
    graph('graph-rebuild-old-left', 'control_graph_install.py',
          '    if retired.is_symlink() or not retired.is_dir():\n        retired.unlink()\n    else:\n        shutil.rmtree(retired)\n',
          '', 'runtime/rebuild-swap')
    graph('graph-problems-repeated', 'control_graph.py',
          '    return list(dict.fromkeys(problems))\n', '    return problems\n', 'runtime/pyvenv-clean')
    graph('graph-shape-opinion-dropped', 'control_graph.py',
          '        if _shaped_like_repository(place) or any(git_finds_repository(start) for start in _discovery_starts(place)):\n',
          '        if any(git_finds_repository(start) for start in _discovery_starts(place)):\n', 'authority/stage-links')
    graph('graph-stage-oserror-unnamed', 'control_graph.py',
          "    except (OSError, RuntimeError, ValueError) as error:\n        reason = ",
          "    except FileNotFoundError as error:\n        reason = ",
          'authority/stage-shapes')
    graph('graph-staged-runner-shape-unchecked', 'control_graph.py',
          "    if target.exists() and not target.is_file():\n", "    if False:\n", 'authority/stage-shapes')
    graph('graph-stage-root-judged-resolved-only', 'control_graph.py',
          "    if inside_repository(runtime['stage']):\n", "    if inside_repository(root):\n", 'authority/stage-shapes')
    graph('graph-stage-inside-runtime-allowed', 'control_graph.py',
          "        if any(place == base or base in place.parents for base in (prefix, prefix.resolve())):\n",
          "        if False:\n", 'authority/stage-shapes')
    graph('graph-descriptors-in-parent-tmpdir', 'control_graph.py',
          'given, answer = tempfile.TemporaryFile(dir=work), tempfile.TemporaryFile(dir=work)',
          'given, answer = tempfile.TemporaryFile(), tempfile.TemporaryFile()', 'authority/no-direct-write')
    graph('graph-unserializable-escapes', 'control_graph.py',
          '    except (ValueError, TypeError, OverflowError, RecursionError) as error:\n'
          "        raise Refused('invalid_input', 'request cannot be serialized: ' + type(error).__name__) from error\n",
          '    except OverflowError as error:\n'
          "        raise Refused('invalid_input', 'request cannot be serialized: ' + type(error).__name__) from error\n",
          'shape/closed-request')
    graph('graph-pyvenv-unchecked', 'control_graph.py',
          '        raise Refused(\'runtime_unavailable\', \'the runtime cannot be judged: \' + str(error)[:120]) from error\n    if problems:\n',
          '        raise Refused(\'runtime_unavailable\', \'the runtime cannot be judged: \' + str(error)[:120]) from error\n    if False:\n',
          'runtime/pyvenv-clean')
    graph('graph-pyvenv-command-ignored', 'control_graph.py',
          "                if inside_repository(path):\n",
          "                if key.strip() != 'command' and inside_repository(path):\n", 'runtime/pyvenv-clean')
    graph('graph-pyvenv-values-split', 'control_graph.py',
          "    else:\n        words = [value]\n", "    else:\n        words = value.split()\n", 'runtime/pyvenv-clean')
    graph('graph-interpreter-final-hop-only', 'control_graph.py',
          '    for hop in visited_paths(python):\n', '    for hop in visited_paths(python)[-1:]:\n', 'runtime/pyvenv-clean')
    graph('graph-relative-link-misjoined', 'control_graph.py',
          "            if target.startswith('/'):\n                current = '/'\n",
          "            current = '/'\n", 'runtime/pyvenv-clean')
    graph('graph-repository-judged-resolved-only', 'control_graph.py',
          '    places = [os.path.abspath(path), visited_paths(path)[-1]]\n',
          '    places = [visited_paths(path)[-1]]\n', 'runtime/pyvenv-clean')
    graph('graph-answer-utf16-unguarded', 'control_graph.py',
          "        value = json.loads(text, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))\n"
          "    except RecursionError as error:\n"
          "        raise Refused('invalid_response', 'answer nests too deeply to parse') from error\n",
          "        value = json.loads(raw, parse_constant=lambda token: (_ for _ in ()).throw(ValueError(token)))\n",
          'shape/deep-answer')
    graph('graph-path-check-skips-keys', 'control_graph.py',
          '            stack.extend(item.keys())\n            stack.extend(item.values())\n',
          '            stack.extend(item.values())\n', 'shape/closed-request')
    graph('graph-request-size-unbounded', 'control_graph.py',
          'MAX_REQUEST_BYTES = 1 << 20\n', 'MAX_REQUEST_BYTES = 1 << 30\n', 'shape/closed-request')
    graph('graph-child-shares-session', 'control_graph.py',
          'close_fds=True, start_new_session=True)', 'close_fds=True, start_new_session=False)',
          'boundary/process-group')
    graph('graph-group-kept-on-exit', 'control_graph.py',
          '        try:\n            finished = _wait_unreaped(proc.pid, timeout)\n        finally:\n            _end_group(proc)\n',
          '        finished = _wait_unreaped(proc.pid, timeout)\n        if not finished:\n            _end_group(proc)\n'
          '        else:\n            proc.wait()\n        if True:\n', 'boundary/process-group')
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
    # VELDO-0053: architecture at every eligibility entry. Each declared falsifier, a second and
    # different defect of its row, and a driven defect for every other row the suite asserts.
    def architecture(name, module, old, new, rows):
        add(53, name, '60_veldo_0053_architecture.py', module, old, new, ['architecture/' + r for r in rows])

    IDENTITY = "            found['validator'] = {module: dict(entry) for module, entry in snapshot.identity.items()}"
    SEAM = "        return self.validate.entry_contract(workspace, required, arch=self.arch)"

    architecture('architecture-malformed-as-optional-absence', 'control_eligibility.py',
                 "        found.update(kind=load.kind, state=load.state, required=load.required,\n",
                 "        if load.kind == 'parse_failure':  # defect: a present malformed contract read as optional absence\n"
                 "            load = load._replace(state='absent', kind='optional_absence', problems=(), required=False)\n"
                 "        found.update(kind=load.kind, state=load.state, required=load.required,\n",
                 ['ready-refusal'])
    loader_parse = ('        kind = "unreadable" if getattr(e, "kind", None) == "unreadable" else "parse_failure"\n'
                    '        return ContractLoad(CONTRACT_INVALID, kind, arch, None, (str(e),), str(p), req)\n')
    architecture('architecture-loader-malformed-as-absence', 'contract_loader.py', loader_parse,
                 loader_parse.replace('        return ContractLoad(CONTRACT_INVALID',
                                      '        if kind == "parse_failure":  # defect: the shared loader reads malformed as absence\n'
                                      '            return ContractLoad(CONTRACT_ABSENT, "optional_absence", None, None, (), str(p), False)\n'
                                      '        return ContractLoad(CONTRACT_INVALID'),
                 ['ready-refusal', 'state-kinds'])
    architecture('architecture-loader-wrong-type-as-absence', 'contract_loader.py',
                 '    if not p.is_file():\n        # PRESENT AND NEVER OPENED',
                 '    if not p.is_file():\n'
                 '        return ContractLoad(CONTRACT_ABSENT, "optional_absence", None, None, (), str(p), False)  # defect\n'
                 '        # PRESENT AND NEVER OPENED',
                 ['ready-refusal', 'state-kinds'])
    architecture('architecture-review-skipped', 'control_eligibility.py',
                 "                      for s in FLOOR_STATIONS}\n# The refusal each refused architecture kind",
                 "                      for s in FLOOR_STATIONS}\n"
                 "STATION_PREDICATES['review'] = tuple(p for p in STATION_PREDICATES['review'] if p != ARCHITECTURE_PREDICATE)"
                 "  # defect: direct review skips the architecture\n# The refusal each refused architecture kind",
                 ['forbidden-review-launch'])
    architecture('architecture-review-decision-skips', 'control_eligibility.py',
                 "                    if name == ARCHITECTURE_PREDICATE:\n",
                 "                    if name == ARCHITECTURE_PREDICATE and station == 'review':\n"
                 "                        continue  # defect: the review decision never asks the architecture\n"
                 "                    if name == ARCHITECTURE_PREDICATE:\n",
                 ['forbidden-review-launch'])
    architecture('architecture-invalid-structure-passes', 'control_eligibility.py',
                 "        if load.refused:\n            found['refusals']",
                 "        if load.refused and load.kind != 'invalid_structure':  # defect: only unreadable input refuses\n"
                 "            found['refusals']",
                 ['entries-blocked'])
    architecture('architecture-record-not-required', 'control_eligibility.py',
                 "snapshot.contract(self.workspace, True if accepted else None)",
                 "snapshot.contract(self.workspace, None)  # defect: acceptance no longer makes the contract required",
                 ['entries-blocked', 'substitution'])
    architecture('architecture-provider-request-unasked', 'control_eligibility.py',
                 "STATION_PREDICATES = {s: tuple(dict.fromkeys(('admission_current', ARCHITECTURE_PREDICATE) + tuple(CC.ENTRY_PREDICATES[s])))",
                 "STATION_PREDICATES = {s: tuple(dict.fromkeys(('admission_current',) + ((ARCHITECTURE_PREDICATE,) if s != 'provider_request'"
                 " else ()) + tuple(CC.ENTRY_PREDICATES[s])))",
                 ['registrations', 'entries-blocked'])
    architecture('architecture-clone-validator', 'control_eligibility.py',
                 "            self._validator = ValidatorSnapshot()\n",
                 "            self._validator = ValidatorSnapshot(os.path.join(self.workspace, '.veldo'))"
                 "  # defect: the workspace's own validator judges the workspace\n",
                 ['substitution'])
    architecture('architecture-accepted-digest-ignored', 'control_eligibility.py',
                 "        elif accepted and parsed != accepted['digest']:",
                 "        elif False:  # defect: whatever bytes are at the path are the accepted architecture",
                 ['substitution'])
    architecture('architecture-identity-from-workspace', 'control_eligibility.py',
                 IDENTITY,
                 "            found['validator'] = {module: {'path': os.path.join(self.workspace, '.veldo', os.path.basename(entry['path'])),\n"
                 "                                           'digest': entry['digest']}\n"
                 "                                  for module, entry in snapshot.identity.items()}  # defect: names what the workspace carries",
                 ['substitution'])
    architecture('architecture-identity-not-recorded', 'control_eligibility.py',
                 "        if decision.get('architecture'):\n",
                 "        if False:  # defect: the decision's architecture is not in its observation\n",
                 ['observations'])
    architecture('architecture-unaccepted-record-accepted', 'control_eligibility.py',
                 "        if accepted and (not isinstance(record, dict) or record.get('state') != 'accepted'",
                 "        if accepted and (not isinstance(record, dict)",
                 ['record-states'])
    # Review fix: a Gate with no workspace never passes, record or no record.
    architecture('architecture-store-only-passes', 'control_eligibility.py',
                 "            found['basis'] = 'store_only'\n            found['refusals'] = ['missing_evidence:architecture/workspace']\n",
                 "            found['basis'] = 'store_only'\n"
                 "            if accepted:  # defect: without a record a store-only Gate passes\n"
                 "                found['refusals'] = ['missing_evidence:architecture/workspace']\n",
                 ['store-only-refuses'])
    architecture('architecture-store-only-reads-cwd', 'control_eligibility.py',
                 "        self.workspace = str(workspace) if workspace is not None else None\n",
                 "        self.workspace = str(workspace) if workspace is not None else os.getcwd()  # defect: the process directory\n",
                 ['store-only-refuses'])
    # Review fix: the Gate judges only through validate.py's public entry_contract.
    architecture('architecture-private-seam', 'control_eligibility.py', SEAM,
                 "        return self.validate._VC.entry_contract(workspace, required, arch=self.arch)  # defect: around the public name",
                 ['public-seam'])
    snapshot_load = ("        spec = self._named('eligibility_validator_snapshot', 'validate')\n"
                     "        module = importlib.util.module_from_spec(spec)\n"
                     "        spec.loader.exec_module(module)\n"
                     "        self.validate, self.arch = module, module.entry_validator()\n")
    architecture('architecture-validate-checks-direct', 'control_eligibility.py', snapshot_load,
                 snapshot_load.replace("'validate')", "'validate_checks')")
                 .replace("        self.validate, self.arch = module, module.entry_validator()\n",
                          "        module.parse_yamlish = module._Y.parse  # defect: around validate.py\n"
                          "        self.validate, self.arch = module, module._arch_module()\n"),
                 ['public-seam'])
    # Review fix: the snapshot runs from the bytes in memory; no copy on disk stands between digest and code.
    architecture('architecture-snapshot-private-copy', 'control_eligibility.py', snapshot_load,
                 "        import tempfile  # defect: a private copy on disk, loaded after it is written\n"
                 "        with tempfile.TemporaryDirectory(prefix='veldo-validator-') as private:\n"
                 "            engine = Path(private) / '.veldo'\n"
                 "            engine.mkdir()\n"
                 "            for held, body in self._bodies.items():\n"
                 "                (engine / (held + '.py')).write_bytes(body)\n"
                 "            spec = importlib.util.spec_from_file_location('eligibility_validator_snapshot', str(engine / 'validate.py'))\n"
                 "            module = importlib.util.module_from_spec(spec)\n"
                 "            spec.loader.exec_module(module)\n"
                 "            self.validate, self.arch = module, module.entry_validator()\n",
                 ['snapshot-in-memory'])
    architecture('architecture-siblings-from-disk', 'control_eligibility.py',
                 "        util.spec_from_file_location = self._spec\n",
                 "        pass  # defect: a sibling loaded by path is read from disk\n",
                 ['snapshot-in-memory'])
    # Review fix: the identity is taken once, from the bytes loaded, and every decision records that.
    architecture('architecture-identity-read-at-decision', 'control_eligibility.py', IDENTITY,
                 "            found['validator'] = {module: {'path': entry['path'], 'digest': 'sha256:' + hashlib.sha256(\n"
                 "                Path(entry['path']).read_bytes()).hexdigest()} for module, entry in snapshot.identity.items()}"
                 "  # defect: the files on disk now, not the bytes that ran",
                 ['identity-is-what-ran'])
    architecture('architecture-validator-reexecuted-per-call', 'control_eligibility.py', SEAM,
                 "        return self.validate.entry_contract(workspace, required, arch=_organ('arch'))"
                 "  # defect: the structural validator re-executed from disk at every call",
                 ['identity-is-what-ran'])
    architecture('architecture-snapshot-per-decision', 'control_eligibility.py',
                 "        if self._validator is None:\n            self._validator = ValidatorSnapshot()\n",
                 "        if True:  # defect: a new snapshot for every decision\n            self._validator = ValidatorSnapshot()\n",
                 ['identity-is-what-ran'])
    # Review fix: the digest compared is the loader's, of the very bytes it parsed.
    architecture('architecture-digest-second-read', 'control_eligibility.py',
                 "        elif accepted and parsed != accepted['digest']:",
                 "        elif accepted and 'sha256:' + hashlib.sha256(Path(load.path).read_bytes()).hexdigest() != accepted['digest']:"
                 "  # defect: a second read",
                 ['validated-is-digested'])
    reported = ("    if digested is not None:\n        digested(body_digest)\n    problems = []\n"
                "    arch.validate_contract(data, base, p, lambda _where, msg: (problems.append(msg), 1)[1])\n")
    architecture('architecture-loader-digest-second-read', 'contract_loader.py', reported,
                 "    problems = []\n    arch.validate_contract(data, base, p, lambda _where, msg: (problems.append(msg), 1)[1])\n"
                 "    if digested is not None:\n"
                 "        digested(arch.read_contract(p, parse)[1])  # defect: the digest of a second read, after validation\n",
                 ['validated-is-digested'])
    # Review fix: bytes that are not UTF-8 are a named parse failure with their digest.
    decode = ('    try:\n        text = io.TextIOWrapper(io.BytesIO(body), encoding="utf-8").read()\n'
              '    except UnicodeDecodeError as e:\n'
              '        raise ArchContractError("architecture contract is not UTF-8 text: %s" % e, digest=digest)\n')
    architecture('architecture-decode-outside-refusal', 'arch.py', decode,
                 '    text = io.TextIOWrapper(io.BytesIO(body), encoding="utf-8").read()  # defect: decoded outside the refusal\n',
                 ['not-text-refused'])
    # defect: a lossy decode replaces what is not UTF-8 and parses the rest
    architecture('architecture-decode-lossy', 'arch.py', 'io.TextIOWrapper(io.BytesIO(body), encoding="utf-8")',
                 'io.TextIOWrapper(io.BytesIO(body), encoding="utf-8", errors="replace")',
                 ['not-text-refused'])
    # Review fix (round 4, the lead's design): the snapshot is keyed by module NAME, never by a path; a name
    # not held is the named stop ImportError, recorded in the durable stop event.
    by_name = "        return self._named(name, file_name[:-3] if file_name.endswith('.py') else '')\n"
    architecture('architecture-snapshot-disk-fallback', 'control_eligibility.py', by_name,
                 "        held = file_name[:-3] if file_name.endswith('.py') else ''\n"
                 "        if held not in self._bodies:\n"
                 "            return importlib.util.spec_from_file_location(name, location, *args, **kwargs)  # defect: a miss read from disk\n"
                 "        return self._named(name, held)\n",
                 ['snapshot-by-name'])
    architecture('architecture-snapshot-keyed-by-path', 'control_eligibility.py', by_name,
                 "        by_path = {}\n"
                 "        for held in self._bodies:\n"
                 "            by_path[str(self._installed / (held + '.py'))] = held\n"
                 "            by_path[os.path.realpath(str(self._installed / (held + '.py')))] = held\n"
                 "        where = str(location) if location is not None else ''\n"
                 "        return self._named(name, by_path.get(os.path.abspath(where)) or by_path.get(os.path.realpath(where)) or '')"
                 "  # defect: keyed by path\n",
                 ['snapshot-by-name'])
    architecture('architecture-stop-error-unrecorded', 'control_eligibility.py',
                 "            if found.get('error'):\n                # The durable stop event",
                 "            if False:  # defect: the stop event does not name its error\n                # The durable stop event",
                 ['snapshot-by-name'])
    # Review fix: the bytes compiled are the bytes digested (a writer lands between the one read and the compile).
    architecture('architecture-exec-rereads-disk', 'control_eligibility.py',
                 "exec(compile(self.body, key, 'exec', dont_inherit=True), module.__dict__)",
                 "exec(compile(Path(module.__spec__.origin).read_bytes(), key, 'exec', dont_inherit=True),"
                 " module.__dict__)  # defect: compiled from a second read of the disk",
                 ['snapshot-in-memory'])
    architecture('architecture-arch-digest-reread', 'control_eligibility.py',
                 "        self.snapshot._executed[self.held] = 'sha256:' + hashlib.sha256(self.body).hexdigest()\n",
                 "        self.snapshot._executed[self.held] = 'sha256:' + hashlib.sha256(\n"
                 "            self.body if self.held != 'arch' else (self.snapshot._installed / 'arch.py').read_bytes()).hexdigest()"
                 "  # defect: arch.py digested from a second read\n",
                 ['snapshot-in-memory'])
    # Review fix: tracebacks and inspect show the code that ran.
    seed = ("        linecache.cache[key] = (len(self.body), None, importlib.util.decode_source(self.body).splitlines(True),"
            " key)\n")
    architecture('architecture-linecache-unseeded', 'control_eligibility.py', seed,
                 "        pass  # defect: linecache reads the file on disk by name\n", ['snapshot-source'])
    architecture('architecture-linecache-mtime-checked', 'control_eligibility.py', seed,
                 seed.replace("(len(self.body), None,", "(len(self.body), os.stat(module.__spec__.origin).st_mtime,")
                 .rstrip("\n") + "  # defect: checkcache drops it after an edit\n", ['snapshot-source'])
    architecture('architecture-get-source-missing', 'control_eligibility.py',
                 "        return importlib.util.decode_source(self.body)\n",
                 "        return None  # defect: the loader hands back no source\n", ['snapshot-source'])
    # Round 4: snapshot lines are kept under a key no other loader uses, unique to each snapshot.
    architecture('architecture-linecache-keyed-by-path', 'control_eligibility.py',
                 "        key = self.snapshot.source_key(self.held)\n",
                 "        key = str(self.snapshot._installed / (self.held + '.py'))  # defect: the installed path, shared\n",
                 ['snapshot-source'])
    architecture('architecture-linecache-key-shared', 'control_eligibility.py',
                 "        return '<veldo validator snapshot %s: %s>' % (self._id, self._installed / (held + '.py'))\n",
                 "        return '<veldo validator snapshot: %s>' % (self._installed / (held + '.py'))  # defect: one key for every snapshot\n",
                 ['snapshot-source'])
    # Round 5: the recorded identity is every held module the snapshot executes, not a fixed list.
    executed = ("        return {held: {'module': held, 'role': ROLE_LABELS.get(held), 'path': str(self._installed / (held + '.py')),\n"
                "                       'digest': digest}\n"
                "                for held, digest in self._executed.items()}\n")
    architecture('architecture-identity-static-five', 'control_eligibility.py', executed,
                 "        return {name[:-3]: {'module': name[:-3], 'role': role, 'path': str(self._installed / name),\n"
                 "                            'digest': 'sha256:' + hashlib.sha256(self._bodies[name[:-3]]).hexdigest()}\n"
                 "                for role, name in VALIDATOR_ROLES}  # defect: the hand-written list of five\n",
                 ['identity-covers-what-ran'])
    architecture('architecture-identity-roles-only', 'control_eligibility.py', executed,
                 executed.replace("for held, digest in self._executed.items()}",
                                  "for held, digest in self._executed.items() if held in ROLE_LABELS}  # defect: labelled modules only"),
                 ['identity-covers-what-ran'])
    # Round 6: the identity is keyed by module name; a file named after a role label takes no other module's place.
    architecture('architecture-identity-keyed-by-role', 'control_eligibility.py', executed,
                 executed.replace("        return {held: {'module': held,", "        return {ROLE_LABELS.get(held, held): {'module': held,")
                 .rstrip("\n") + "  # defect: keyed by role label\n",
                 ['identity-keyed-by-module'])
    architecture('architecture-identity-role-named-dropped', 'control_eligibility.py', executed,
                 executed.replace("for held, digest in self._executed.items()}",
                                  "for held, digest in self._executed.items()\n"
                                  "                if held not in ROLE_LABELS.values()}  # defect: a module named after a role is left out"),
                 ['identity-keyed-by-module'])
    # Round 5: only a non-empty module name is held and only a regular file is read.
    architecture('architecture-snapshot-holds-empty-name', 'control_eligibility.py',
                 " for path in sorted(installed.glob('*.py')) if path.name[:-3]}",
                 " for path in sorted(installed.glob('*.py'))}  # defect: a file named .py is held under the empty name",
                 ['snapshot-held-names'])
    architecture('architecture-snapshot-request-any-suffix', 'control_eligibility.py',
                 "        return self._named(name, file_name[:-3] if file_name.endswith('.py') else '')\n",
                 "        return self._named(name, os.path.splitext(file_name)[0])  # defect: any suffix names a held module\n",
                 ['snapshot-held-names'])
    architecture('architecture-snapshot-reads-any-file', 'control_eligibility.py',
                 "        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):\n",
                 "        if False:  # defect: a FIFO or other non-regular file is read like a file\n",
                 ['snapshot-held-names'])
    architecture('architecture-snapshot-blocking-read', 'control_eligibility.py',
                 "_read_engine_file(path) for path in sorted(installed.glob('*.py'))",
                 "path.read_bytes() for path in sorted(installed.glob('*.py'))",
                 ['snapshot-held-names'])
    # Round 6: a held file is read up to the stated limit and no further; one over it is the named stop.
    bounded_read = "        body = handle.read(ENGINE_FILE_LIMIT + 1)\n"
    over_limit = "    if len(body) > ENGINE_FILE_LIMIT:\n"
    architecture('architecture-snapshot-read-unbounded', 'control_eligibility.py', bounded_read,
                 "        body = handle.read()  # defect: the whole file is read before its length is judged\n",
                 ['snapshot-file-bounded'])
    architecture('architecture-snapshot-read-limit-short', 'control_eligibility.py', bounded_read,
                 "        body = handle.read(ENGINE_FILE_LIMIT)  # defect: a longer file is cut to the limit and held\n",
                 ['snapshot-file-bounded'])
    architecture('architecture-snapshot-length-unjudged', 'control_eligibility.py', over_limit,
                 "    if False:  # defect: a file over the limit is held\n",
                 ['snapshot-file-bounded'])
    architecture('architecture-snapshot-limit-exclusive', 'control_eligibility.py', over_limit,
                 "    if len(body) >= ENGINE_FILE_LIMIT:  # defect: a file of exactly the limit is refused\n",
                 ['snapshot-file-bounded'])
    # Round 5 pins: __file__ is the installed path of the name, and linecache is seeded before a module runs.
    origin = "origin=str(self._installed / (held + '.py')))\n"
    architecture('architecture-snapshot-file-resolved', 'control_eligibility.py', origin,
                 "origin=os.path.realpath(str(self._installed / (held + '.py'))))  # defect: the link's target\n",
                 ['snapshot-module-files'])
    architecture('architecture-snapshot-file-is-key', 'control_eligibility.py', origin,
                 "origin=self.source_key(held))  # defect: __file__ is the snapshot's cache key, not the installed path\n",
                 ['snapshot-module-files'])
    load_block = (seed + "        self.snapshot._keys.append(key)\n"
                  "        # Recorded before the module runs. A module whose load raises stays in the identity only when the module\n"
                  "        # loading it catches the error; a raise out of the snapshot refuses the decision with validator {}.\n"
                  "        self.snapshot._executed[self.held] = 'sha256:' + hashlib.sha256(self.body).hexdigest()\n"
                  "        exec(compile(self.body, key, 'exec', dont_inherit=True), module.__dict__)\n")
    architecture('architecture-linecache-seeded-after-load', 'control_eligibility.py', load_block,
                 load_block.replace(seed, "").rstrip("\n") + "  # defect: lines cached only after the module ran\n" + seed,
                 ['snapshot-module-files'])
    architecture('architecture-linecache-seeded-for-roles-only', 'control_eligibility.py', seed,
                 "        if self.held in ROLE_LABELS:  # defect: only the labelled modules' lines are cached\n    " + seed,
                 ['snapshot-module-files'])
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
    parser.add_argument('--finding', type=int, choices=sorted({case['finding'] for case in cases()}))
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
