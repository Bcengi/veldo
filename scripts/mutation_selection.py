#!/usr/bin/env python3
"""VELDO-0267: which registered mutation cases a gate runs, and what the nightly sweep left behind.

THE RULE. A gate runs the cases its candidate's changed paths select plus a fixed canary set, never
all of them, unless a trigger forces the full sweep. A case is selected when a changed path is
  (a) the module the case mutates, at its root or its engine copy        reason mutated_module
  (b) the case's suite file                                              reason suite_file
  (c) a file of its covered set: its declared entry in
      scripts/mutation_case_inputs.json when it has one, otherwise the
      repository files its baseline read in the last green nightly sweep  reason covered_file
and always when the coverage map does not know it (new, or its definition digest changed), reason
no_coverage_record. Canaries (scripts/mutation_selection.json) are always run, reason canary.

THE FULL SWEEP is forced, and named, when the candidate changes a path of the declared trigger list,
when the toolchain digests of scripts/mutation_case_inputs.json differ from the coverage map's, when
the coverage map is missing or unreadable, when the last green or explained nightly sweep finished
more than max_age_hours (36) before the gate started (nightly_stale), and when anything the rule
needs cannot be read (selection_unavailable). A failure to compute a selection never runs fewer cases.

THE RECORD (veldo.mutation-selection/v1) holds every input and, for every registered case, whether it
was selected and every reason it was; recompute() rebuilds the set from the record, the coverage map
and the declared inputs and must agree.

THE NIGHTLY STATE lives in the authority's state directory, outside every candidate tree:
  <state>/sweeps/<run id>.json   veldo.mutation-sweep/v1, one per sweep
  <state>/coverage.json          veldo.mutation-coverage/v1, published by a green sweep only
landing_refusal() is the landing check: the latest finished sweep red and not explained by an owner
approval naming its run id and every failing case with a reason refuses as nightly_red.

Standard library only.
"""
import datetime
import fnmatch
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
RULE = HERE / 'mutation_selection.json'
RULE_SCHEMA = 'veldo.mutation-selection-rule/v1'
SCHEMA = 'veldo.mutation-selection/v1'
COVERAGE_SCHEMA = 'veldo.mutation-coverage/v1'
SWEEP_SCHEMA = 'veldo.mutation-sweep/v1'
REASONS = ('mutated_module', 'suite_file', 'covered_file', 'no_coverage_record', 'canary')
CANARY_BOUNDS = (6, 12)


class Invalid(Exception):
    pass


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':')).encode()


def digest(value):
    return hashlib.sha256(canonical(value)).hexdigest()


def utc(moment):
    return datetime.datetime.fromtimestamp(moment, datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')


def parse_utc(text):
    return datetime.datetime.strptime(text, '%Y-%m-%dT%H:%M:%SZ').replace(
        tzinfo=datetime.timezone.utc).timestamp()


# The declaration.

def load_rule(path=RULE):
    try:
        rule = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise Invalid('the selection rule %s cannot be read (%s)' % (path, error))
    if not isinstance(rule, dict) or rule.get('schema') != RULE_SCHEMA:
        raise Invalid('the selection rule is not %s' % RULE_SCHEMA)
    canaries = rule.get('canaries')
    if (not isinstance(canaries, list) or any(not isinstance(c, str) or not c for c in canaries)
            or len(set(canaries)) != len(canaries)):
        raise Invalid('canaries must be a list of distinct case identities')
    low, high = CANARY_BOUNDS
    if not low <= len(canaries) <= high:
        raise Invalid('canaries: the set holds between six and twelve cases, found %d' % len(canaries))
    triggers = rule.get('triggers')
    if not isinstance(triggers, list) or not triggers or any(not isinstance(t, str) or not t for t in triggers):
        raise Invalid('triggers must be a non-empty list of paths')
    nightly = rule.get('nightly')
    if (not isinstance(nightly, dict) or type(nightly.get('max_age_hours')) not in (int, float)
            or not nightly['max_age_hours'] > 0 or not isinstance(nightly.get('state_directory'), str)
            or not isinstance(nightly.get('trunk'), str) or not isinstance(nightly.get('notifier'), list)):
        raise Invalid('nightly must name max_age_hours, trunk, state_directory and notifier')
    return rule


def state_directory(rule):
    text = rule['nightly']['state_directory']
    return Path(os.path.expanduser(text)) if text.startswith('~') else Path(text)


def check_canaries(rule, cases, unconfined, resources):
    """The canaries are registered and cover both drivers, both legs and a service fixture.
    unconfined(case) and resources(case) answer for one registered case."""
    by_identity = {c['identity']: c for c in cases}
    missing = [c for c in rule['canaries'] if c not in by_identity]
    if missing:
        raise Invalid('canaries not registered: ' + ', '.join(missing))
    chosen = [by_identity[c] for c in rule['canaries']]
    drivers = {c['driver'] for c in chosen}
    if len(drivers) < 2:
        raise Invalid('canaries must cover both drivers, cover only ' + ', '.join(sorted(drivers)))
    legs = {bool(unconfined(c)) for c in chosen}
    if legs != {True, False}:
        raise Invalid('canaries must cover the confined and the unconfined leg')
    if not any(resources(c) for c in chosen):
        raise Invalid('canaries must hold at least one case that needs a service fixture')


# What changed.

def git_command(root):
    def run(*args):
        result = subprocess.run(['git', '-C', str(root), *args], capture_output=True, timeout=120)
        if result.returncode:
            raise Invalid('git %s: %s' % (' '.join(args), result.stderr.decode(errors='replace').strip()[:300]))
        return result.stdout
    return run


def changed_paths(git, base, candidate, dirty=True):
    """Every path changed between base and candidate, both sides of a rename, and every dirty path
    of the working tree. git(*args) returns the command's standard output as bytes."""
    changed = set()
    parts = git('diff', '--name-status', '-M', '-z', base, candidate).split(b'\0')
    index = 0
    while index < len(parts):
        status = parts[index].decode()
        if not status:
            index += 1
            continue
        count = 2 if status[:1] in ('R', 'C') else 1
        names = parts[index + 1:index + 1 + count]
        if len(names) != count:
            raise Invalid('unreadable diff of %s..%s' % (base, candidate))
        changed.update(os.fsdecode(n) for n in names)
        index += 1 + count
    if dirty:
        parts = git('status', '--porcelain=v1', '-z', '--untracked-files=all').split(b'\0')
        index = 0
        while index < len(parts):
            entry = parts[index]
            index += 1
            if not entry:
                continue
            if len(entry) < 4:
                raise Invalid('unreadable working tree status')
            changed.add(os.fsdecode(entry[3:]))
            if entry[:1] in (b'R', b'C') or entry[1:2] in (b'R', b'C'):
                changed.add(os.fsdecode(parts[index]))
                index += 1
    return sorted(changed)


def merge_base(git, trunk, candidate):
    return git('merge-base', trunk, candidate).decode().strip()


# What a case owns.

def module_paths(case):
    if case.get('fixture'):
        target = 'scripts/fixtures/' + case['module']
    else:
        target = str(Path(case.get('dir', '.veldo')) / case['module'])
    return {target, 'engine/' + target}


def suite_path(case):
    return 'scripts/suites/' + case['suite']


def definition_digest(case):
    return digest(case)


def toolchain_digests(case_inputs):
    chains = case_inputs.get('toolchains') if isinstance(case_inputs, dict) else None
    if not isinstance(chains, dict):
        raise Invalid('scripts/mutation_case_inputs.json declares no toolchains')
    return {driver: digest(entry) for driver, entry in sorted(chains.items())}


def declared_files(case_inputs, identity):
    entry = (case_inputs.get('cases') or {}).get(identity) if isinstance(case_inputs, dict) else None
    if isinstance(entry, dict) and isinstance(entry.get('files'), list):
        return set(entry['files'])
    return None


def load_coverage(path):
    try:
        document = json.loads(Path(path).read_text())
    except FileNotFoundError:
        raise Invalid('coverage map missing')
    except (OSError, ValueError) as error:
        raise Invalid('coverage map unreadable (%s)' % error)
    body = {k: v for k, v in document.items() if k != 'digest'} if isinstance(document, dict) else None
    if (body is None or document.get('schema') != COVERAGE_SCHEMA or document.get('digest') != digest(body)
            or not isinstance(document.get('cases'), dict) or not isinstance(document.get('toolchains'), dict)
            or not isinstance(document.get('finished_at'), str) or not isinstance(document.get('run_id'), str)):
        raise Invalid('coverage map unreadable (not a sealed %s)' % COVERAGE_SCHEMA)
    for entry in document['cases'].values():
        if (not isinstance(entry, dict) or not isinstance(entry.get('definition'), str)
                or not (entry.get('files') is None or isinstance(entry.get('files'), list))):
            raise Invalid('coverage map unreadable (a malformed case entry)')
    return document


def seal(document):
    body = {k: v for k, v in document.items() if k != 'digest'}
    return dict(body, digest=digest(body))


def reasons_for(case, changed, coverage, case_inputs, canaries):
    """Every reason this case is selected; empty when it is not."""
    reasons = []
    changed = set(changed)
    if changed & module_paths(case):
        reasons.append('mutated_module')
    if suite_path(case) in changed:
        reasons.append('suite_file')
    known = coverage['cases'].get(case['identity'])
    declared = declared_files(case_inputs, case['identity'])
    if declared is not None:
        covered = declared
    elif known is not None and known.get('files') is not None:
        covered = set(known['files'])
    else:
        covered = set()
    if changed & covered:
        reasons.append('covered_file')
    if known is None or known.get('definition') != definition_digest(case) or (
            declared is None and known.get('files') is None):
        reasons.append('no_coverage_record')
    if case['identity'] in canaries:
        reasons.append('canary')
    return reasons


def trigger_path(changed, triggers):
    for path in changed:
        for pattern in triggers:
            if fnmatch.fnmatchcase(path, pattern):
                return path, pattern
    return None


# The nightly state.

def sweeps(state):
    """Every finished sweep record, oldest first by end time. Unreadable records are skipped."""
    found = []
    for path in sorted((Path(state) / 'sweeps').glob('*.json')):
        try:
            record = json.loads(path.read_text())
            if (record.get('schema') == SWEEP_SCHEMA and isinstance(record.get('run_id'), str)
                    and record.get('verdict') in ('green', 'red') and isinstance(record.get('finished_at'), str)):
                parse_utc(record['finished_at'])
                found.append(record)
        except (OSError, ValueError, AttributeError, TypeError):
            continue
    def order(record):
        epoch = record.get('finished_epoch')
        return (epoch if type(epoch) in (int, float) else parse_utc(record['finished_at']), record['run_id'])
    return sorted(found, key=order)


def failing_cases(record):
    return sorted({f['case'] for f in record.get('failures', []) if isinstance(f, dict) and isinstance(f.get('case'), str)})


def explaining_approval(record, approvals, now):
    """The first approval that names this red sweep's run id and gives a reason for each failing
    case: veldo.approval/v1, decision approved, unexpired, an approver, scope.nightly_run equal to the
    run id and scope.cases mapping every failing case to a non-empty reason. A red record that names
    no failing case cannot be explained by name and stays red."""
    failing = failing_cases(record)
    if not failing:
        return None
    for name, approval in approvals:
        if not isinstance(approval, dict) or approval.get('schema') != 'veldo.approval/v1':
            continue
        if approval.get('decision') != 'approved' or not approval.get('approver'):
            continue
        scope = approval.get('scope')
        if not isinstance(scope, dict) or scope.get('nightly_run') != record['run_id']:
            continue
        cases = scope.get('cases')
        if not isinstance(cases, dict) or any(not isinstance(cases.get(c), str) or not cases[c].strip()
                                              for c in failing):
            continue
        try:
            expires = datetime.datetime.fromisoformat(approval['expires_at'].replace('Z', '+00:00')).timestamp()
        except (KeyError, AttributeError, ValueError):
            continue
        if expires <= now:
            continue
        return name
    return None


def landing_refusal(state, approvals, now=None):
    """None when landing may proceed, else ('nightly_red', detail). Only the LATEST finished sweep
    decides: a later green sweep clears an earlier red one without approval."""
    now = now if now is not None else datetime.datetime.now(datetime.timezone.utc).timestamp()
    records = sweeps(state)
    if not records:
        return None
    latest = records[-1]
    if latest['verdict'] == 'green':
        return None
    if explaining_approval(latest, approvals, now):
        return None
    return ('nightly_red', 'the nightly sweep %s on %s is red: %s' % (
        latest['run_id'], str(latest.get('trunk_commit'))[:12], ', '.join(failing_cases(latest)) or 'no case named'))


def last_trusted(state, approvals, now):
    """The finish time of the last green or explained sweep, or None."""
    trusted = [r for r in sweeps(state) if r['verdict'] == 'green' or explaining_approval(r, approvals, now)]
    return parse_utc(trusted[-1]['finished_at']) if trusted else None


def nightly_summary(state):
    records = sweeps(state)
    if not records:
        return None
    latest = records[-1]
    return {k: latest.get(k) for k in ('run_id', 'trunk_commit', 'verdict', 'finished_at')}


def read_approvals(root):
    found = []
    for path in sorted(Path(root).glob('proof/*/approval*.json')):
        try:
            found.append((str(path), json.loads(path.read_text())))
        except (OSError, ValueError):
            continue
    return found


# The selection.

def select(cases, rule, *, base, candidate, changed=None, coverage=None, case_inputs=None,
           approvals=(), state=None, started=None, error=None):
    """The selection record. Any input that is None (or an error) makes the full sweep, named."""
    started = started if started is not None else datetime.datetime.now(datetime.timezone.utc).timestamp()
    canaries = set(rule['canaries']) if rule else set()
    record = {'schema': SCHEMA, 'base': base, 'candidate': candidate,
              'changed': list(changed) if changed is not None else None,
              'coverage': None, 'toolchains': None, 'started_at': utc(started),
              'canaries': sorted(canaries), 'trigger': None, 'nightly': None}
    trigger = None
    if error is not None:
        trigger = {'kind': 'selection_unavailable', 'detail': str(error)}
    elif changed is None:
        trigger = {'kind': 'selection_unavailable', 'detail': 'the changed paths could not be read'}
    else:
        hit = trigger_path(changed, rule['triggers'])
        if hit:
            trigger = {'kind': 'trigger_path', 'path': hit[0], 'pattern': hit[1]}
    if trigger is None:
        if coverage is None or isinstance(coverage, Invalid):
            trigger = {'kind': 'coverage_missing', 'detail': str(coverage or 'coverage map missing')}
        else:
            record['coverage'] = {'run_id': coverage['run_id'], 'digest': coverage['digest'],
                                  'finished_at': coverage['finished_at']}
    if trigger is None:
        try:
            current = toolchain_digests(case_inputs)
        except Invalid as problem:
            trigger = {'kind': 'selection_unavailable', 'detail': str(problem)}
        else:
            record['toolchains'] = current
            if current != coverage['toolchains']:
                changed_drivers = sorted(d for d in set(current) | set(coverage['toolchains'])
                                         if current.get(d) != coverage['toolchains'].get(d))
                trigger = {'kind': 'toolchain_changed', 'detail': ', '.join(changed_drivers)}
    if trigger is None:
        limit = rule['nightly']['max_age_hours'] * 3600
        finished = parse_utc(coverage['finished_at'])
        if state is not None:
            trusted = last_trusted(state, approvals, started)
            finished = max(finished, trusted) if trusted is not None else finished
        record['nightly'] = {'last_trusted_at': utc(finished), 'max_age_hours': rule['nightly']['max_age_hours']}
        if started - finished > limit:
            trigger = {'kind': 'nightly_stale',
                       'detail': 'the last green or explained nightly sweep finished %s, more than %g hours '
                                 'before this gate started' % (utc(finished), rule['nightly']['max_age_hours'])}
    record['trigger'] = trigger
    record['mode'] = 'full' if trigger else 'selected'
    entries = {}
    for case in cases:
        if trigger:
            reasons = ['full'] + (['canary'] if case['identity'] in canaries else [])
        else:
            reasons = reasons_for(case, changed, coverage, case_inputs, canaries)
        entries[case['identity']] = {'selected': bool(reasons), 'reasons': reasons}
    record['cases'] = entries
    counts = {reason: sum(reason in e['reasons'] for e in entries.values()) for reason in REASONS}
    record['counts'] = dict(counts, selected=sum(e['selected'] for e in entries.values()),
                            registered=len(entries),
                            canaries=sum(i in canaries for i in entries))
    return seal(record)


def recompute(record, cases, coverage, case_inputs):
    """Rebuild every case's reasons from the record's own inputs; True when the record agrees."""
    body = {k: v for k, v in record.items() if k != 'digest'}
    if record.get('digest') != digest(body) or set(record['cases']) != {c['identity'] for c in cases}:
        return False
    canaries = set(record['canaries'])
    for case in cases:
        entry = record['cases'][case['identity']]
        if record['mode'] == 'full':
            expected = ['full'] + (['canary'] if case['identity'] in canaries else [])
        else:
            expected = reasons_for(case, record['changed'], coverage, case_inputs, canaries)
        if entry != {'selected': bool(expected), 'reasons': expected}:
            return False
    return True


def chosen(record):
    return {identity for identity, entry in record['cases'].items() if entry['selected']}


def line(record):
    """The one selection line the stage prints before any case runs."""
    counts = record['counts']
    coverage = record.get('coverage') or {}
    trigger = record.get('trigger')
    if trigger:
        named = trigger['kind'] + ((' ' + trigger['path']) if trigger.get('path') else
                                   (' (' + trigger['detail'] + ')') if trigger.get('detail') else '')
    else:
        named = 'none'
    return ('   mutation selection: mode=%s base=%s candidate=%s changed=%s coverage=%s digest=%s '
            'mutated_module=%d suite_file=%d covered_file=%d no_coverage_record=%d canary=%d '
            'selected=%d of %d trigger=%s' % (
                record['mode'], record['base'] or 'unknown', record['candidate'] or 'unknown',
                'unknown' if record['changed'] is None else len(record['changed']),
                coverage.get('run_id', 'none'), (coverage.get('digest') or 'none')[:16],
                counts['mutated_module'], counts['suite_file'], counts['covered_file'],
                counts['no_coverage_record'], counts['canary'], counts['selected'], counts['registered'], named))


def plan(cases, *, git, candidate, base=None, trunk=None, rule_path=RULE, case_inputs_path=None,
         approvals=(), started=None, unconfined=lambda c: False, resources=lambda c: {}):
    """The gate's selection: never raises. Anything that cannot be read is the full sweep, named."""
    try:
        rule = load_rule(rule_path)
    except Invalid as error:
        return select(cases, None, base=base, candidate=candidate, error=error, started=started)
    try:
        check_canaries(rule, cases, unconfined, resources)
        # The merge base with the trunk commit the gate was told to compare against (a landing's
        # synced trunk commit), else with the rule's trunk branch.
        base = merge_base(git, base or trunk or rule['nightly']['trunk'], candidate)
        changed = changed_paths(git, base, candidate)
        case_inputs = json.loads(Path(case_inputs_path).read_text())
    except (Invalid, OSError, ValueError, subprocess.SubprocessError) as error:
        return select(cases, rule, base=base, candidate=candidate, error=error, started=started)
    state = state_directory(rule)
    try:
        coverage = load_coverage(state / 'coverage.json')
    except Invalid as error:
        coverage = error
    return select(cases, rule, base=base, candidate=candidate, changed=changed, coverage=coverage,
                  case_inputs=case_inputs, approvals=approvals, state=state, started=started)


def write_record(path, record):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_name('.' + path.name + '.%d' % os.getpid())
    pending.write_bytes(canonical(record))
    os.replace(pending, path)


def stamp_field(receipt_path, record_path):
    """The last_verify mutation block, as `"mutation":{...}`, or `"mutation":null` when the stage
    left no selection to report."""
    try:
        receipt = json.loads(Path(receipt_path).read_text())
        block = receipt['selection']
        if not isinstance(block, dict):
            raise ValueError('no selection')
        if record_path:
            body = Path(record_path).read_bytes()
            if hashlib.sha256(body).hexdigest() != block.get('record_sha256'):
                raise ValueError('the selection record differs from the one the stage wrote')
        field = {k: block.get(k) for k in ('mode', 'selected', 'canaries', 'run', 'wall_seconds',
                                           'digest', 'trigger', 'nightly')}
    except (OSError, ValueError, KeyError, TypeError):
        field = None
    return '"mutation":' + json.dumps(field, sort_keys=True, separators=(',', ':'))


def main(argv):
    if len(argv) == 3 and argv[0] == '--stamp-field':
        print(stamp_field(argv[1], argv[2]))
        return 0
    if len(argv) == 1 and argv[0] == '--check':
        try:
            load_rule()
        except Invalid as error:
            print('mutation selection rule: invalid (%s)' % error)
            return 1
        print('mutation selection rule: valid')
        return 0
    print('usage: mutation_selection.py --stamp-field <receipt> <record> | --check', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
