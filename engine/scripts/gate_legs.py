#!/usr/bin/env python3
"""The gate's unconfined leg: the declared suites that run outside the confinement, by name.

Owner decision, Telegram 32403-32407, 2026-10-07 (VELDO-0208, "Unconfined leg"). The suites that
need the systemd user manager or nested strace cannot pass inside the gate's Landlock domain
without granting the escape it denies, and a KVM guest was rejected as too heavy. They run the
way they ran before that domain existed: outside it, in a separate, named leg of the unit and
integration stages, and their mutation cases in the mutation stage's unconfined leg (the stage is
declared with the command MUTATION_COMMAND; scripts/check_gate_mutations.py runs that leg with
mutation_leg and record below, since a mutation case runs its whole suite in one worker, a suite
listed for some rows has every mutation case there). Every other stage and suite stays confined.

THE LIST IS THE AUTHORITY'S, NEVER THE CANDIDATE'S. It is read from beside this file
(scripts/gate_unconfined.json in the authority checkout), a protected path, so adding a suite to
it is a reviewed change with the owner's approval. The installer ships no list: the one this
repository carries is its own owner's decision, so an adopter's gate confines every stage. A candidate's own copy of
the list or an environment variable it sets decides nothing: the leg variables a candidate command
sees are set here, and the caller's are dropped. The candidate's dispatcher applies the list
(scripts/selftest.py, scripts/run_scope.py, scripts/suites/shared.py, and scripts/check_first_use.py,
which hands the leg to its nested selftest.py), and those files are protected too; without that, a
candidate could make its dispatcher ignore the leg. selftest.py and check_first_use.py keep scripts/
and scripts/suites/ behind the standard library on sys.path, so no unprotected file there shadows a
standard-library module they import, and selftest.py loads run_scope.py and suites/shared.py from
their fixed paths, so no unprotected file stands in for either; this runner runs from the authority
as python3 -I -S.

WHAT THE UNCONFINED LEG TRUSTS, stated because it is the cost of the decision. That leg executes
the candidate's dispatcher and the listed suites with the owner's own authority, exactly as before
VELDO-0208; the list and the protected dispatcher bound which suites and rows run there, not
what the code of a listed suite does once it runs. Review of the candidate is the safeguard for
that code. That is why the leg is printed with its suite list on the stage line and recorded in the
stamp and the gate event: it is visible on every run, never silent.

  gate_legs.py --root <candidate> --stage <name> --record <file> -- <command>
      One gate stage. A stage the list declares, with exactly its declared command, runs twice:
      the confined leg (every suite except the ones listed whole, and every row of a suite listed
      for some rows except those rows) through scripts/gate_candidate.py, then the unconfined leg
      (only the listed suites and rows) directly. Any other stage runs confined only.
  gate_legs.py --declared --stage <name> -- <command>
      Exit 0 when the list declares this stage with exactly this command, 1 when it does not, 2
      when the list is invalid. verify.sh asks before the stage runs, so it knows a leg is expected
      whatever candidate code later does to the record.
  gate_legs.py --stamp <file> [--expect <stage,stage>]
      The stamp's "unconfined" value: the declaration's digest and the entries each stage ran
      unconfined. With --expect, a record that is missing, empty, unreadable or does not hold
      exactly those stages is an error, never {}: candidate code in the unconfined leg can delete or
      truncate the record, and that must not read as "no unconfined leg ran".
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

HERE = Path(__file__).resolve().parent
DECLARATION = HERE / 'gate_unconfined.json'
SCHEMA = 'veldo.gate-unconfined/v1'
# verify.sh's mutation stage is no shell command: CHECK_mutation declares it by this text.
MUTATION_COMMAND = 'authority mutation stage'
LEG, ENTRIES, DIGEST = 'VELDO_GATE_LEG', 'VELDO_GATE_UNCONFINED', 'VELDO_GATE_DECLARATION'
SUITE = re.compile(r'^[0-9A-Za-z][0-9A-Za-z_]*$')
ROWS = re.compile(r'^[a-z][a-z0-9-]*$')


class Invalid(ValueError):
    pass


def load(path=DECLARATION):
    """(declaration, digest) of the authority's list, or Invalid naming what is wrong."""
    try:
        raw = Path(path).read_bytes()
        document = json.loads(raw)
    except (OSError, ValueError) as error:
        raise Invalid('unreadable: %s' % error)
    if not isinstance(document, dict) or set(document) != {'schema', 'authority', 'stages', 'suites'}:
        raise Invalid('keys must be exactly schema, authority, stages, suites')
    if document['schema'] != SCHEMA:
        raise Invalid('schema must be %s' % SCHEMA)
    if not isinstance(document['authority'], str) or not document['authority'].strip():
        raise Invalid('authority must name the decision')
    stages = document['stages']
    if not isinstance(stages, dict) or not stages or not all(
            isinstance(k, str) and isinstance(v, str) and v.strip() for k, v in stages.items()):
        raise Invalid('stages must map each stage to its exact command')
    suites, seen = document['suites'], set()
    if not isinstance(suites, list) or not suites:
        raise Invalid('suites must be a non-empty list')
    for entry in suites:
        if not isinstance(entry, dict) or not set(entry) <= {'suite', 'rows', 'reason'} \
                or not {'suite', 'reason'} <= set(entry):
            raise Invalid('each entry is {suite, reason} with optional rows: %r' % (entry,))
        if not isinstance(entry['suite'], str) or not SUITE.match(entry['suite']):
            raise Invalid('suite name %r is not a single safe name' % (entry['suite'],))
        if 'rows' in entry and not (isinstance(entry['rows'], str) and ROWS.match(entry['rows'])):
            raise Invalid('rows of %s must be a lower-case tag' % entry['suite'])
        if not isinstance(entry['reason'], str) or len(entry['reason'].strip()) < 10:
            raise Invalid('%s has no reason' % entry['suite'])
        if entry['suite'] in seen:
            raise Invalid('%s is listed twice' % entry['suite'])
        seen.add(entry['suite'])
    return document, 'sha256:' + hashlib.sha256(raw).hexdigest()


def entries(document):
    """The leg's entries in the form the candidate's dispatcher reads: name or name:rows."""
    return [e['suite'] + (':' + e['rows'] if 'rows' in e else '') for e in document['suites']]


def _env(leg=None, listed=(), digest=None):
    env = {k: v for k, v in os.environ.items() if k not in (LEG, ENTRIES, DIGEST)}
    if leg:
        env[LEG], env[ENTRIES], env[DIGEST] = leg, ','.join(listed), digest
    return env


def confined(root, command, env):
    """The stage command in the gate's domain, exactly as verify.sh's veldo_candidate runs it."""
    return subprocess.run([sys.executable, '-I', '-S', str(HERE / 'gate_candidate.py'), '--root',
                           str(root), '--', 'bash', '-c', command], env=env,
                          stdin=subprocess.DEVNULL).returncode


# What verify.sh exports for its own launchers, never for candidate code. The confined launcher
# reads VELDO_EXPECTED_GIT_COMMON and then drops it (agent_sandbox.py); handed on here, it made every
# gate a listed suite runs for a fixture repository check that repository against the authority's
# common directory and refuse it, so 0050 and 0148 failed only inside the real gate.
AUTHORITY_ONLY = ('VELDO_EXPECTED_GIT_COMMON',)


def unconfined(root, command, env):
    """The stage command outside every domain, in the candidate, as before VELDO-0208."""
    env = {k: v for k, v in env.items() if k not in AUTHORITY_ONLY}
    return subprocess.run(['bash', '-c', command], cwd=str(root), env=env,
                          stdin=subprocess.DEVNULL).returncode


def run_stage(root, stage, command, record, path=DECLARATION):
    try:
        document, digest = load(path)
    except Invalid as error:
        print('   %s: the unconfined list %s is invalid (%s); nothing ran, in either leg'
              % (stage, path, error), flush=True)
        return 1
    declared = document['stages'].get(stage)
    if declared is None or declared != command:
        # Not a declared leg: the whole stage is confined, and no caller variable reaches it.
        return confined(root, command, _env())
    listed = entries(document)
    whole = [e for e in document['suites'] if 'rows' not in e]
    print('   %s: confined leg - every suite except the %d listed whole, and of the %d listed for some '
          'rows, every row but those' % (stage, len(whole), len(listed) - len(whole)), flush=True)
    inside = confined(root, command, _env('confined', listed, digest))
    print('   %s: confined leg: %s' % (stage, 'pass' if inside == 0 else 'FAIL'), flush=True)
    print('   %s: UNCONFINED LEG - runs outside the confinement by owner decision (VELDO-0208, %s), '
          '%d entr%s: %s' % (stage, os.path.basename(str(path)), len(listed),
                              'y' if len(listed) == 1 else 'ies', ', '.join(listed)), flush=True)
    outside = unconfined(root, command, _env('unconfined', listed, digest))
    print('   %s: unconfined leg: %s' % (stage, 'pass' if outside == 0 else 'FAIL'), flush=True)
    write_record(record, stage, digest, listed)
    return 0 if inside == 0 and outside == 0 else 1


def write_record(record, stage, digest, listed):
    with open(record, 'a') as handle:
        handle.write(json.dumps({'stage': stage, 'declaration': digest, 'entries': listed},
                                sort_keys=True) + '\n')


def mutation_leg(path=DECLARATION):
    """The mutation stage's unconfined leg from the authority's list: None when there is no list or
    it does not declare the mutation stage with exactly MUTATION_COMMAND (every case confined, as
    before), else {declaration, entries, suites}. An invalid list raises Invalid: nothing runs."""
    if not Path(path).exists():
        return None
    document, digest = load(path)
    if document['stages'].get('mutation') != MUTATION_COMMAND:
        return None
    return {'declaration': digest, 'entries': entries(document),
            'suites': sorted(e['suite'] for e in document['suites'])}


def declared(stage, command, path=DECLARATION):
    """0 when the list declares this stage with exactly this command, 1 when not, 2 when invalid."""
    try:
        document, _ = load(path)
    except Invalid:
        return 2
    return 0 if document['stages'].get(stage) == command else 1


def stamp(record, expected=None):
    """The stamp value, compact JSON. A record this cannot read is an error, never {}. With the
    stages a leg was expected in, a record that does not hold exactly those is an error too."""
    legs, digests = {}, set()
    if expected is not None and not Path(record).is_file():
        raise Invalid('the leg record is missing')
    try:
        text = Path(record).read_text() if Path(record).exists() else ''
        for line in text.splitlines():
            item = json.loads(line)
            legs[item['stage']] = list(item['entries'])
            digests.add(item['declaration'])
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise Invalid('unreadable leg record: %s' % error)
    if expected is not None and set(legs) != set(expected):
        raise Invalid('the leg record holds stages %s where %s were expected'
                      % (sorted(legs) or 'none', sorted(expected)))
    if not legs:
        return {}
    if len(digests) != 1:
        raise Invalid('the stages ran under different declarations')
    return {'declaration': digests.pop(), 'legs': legs}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root')
    parser.add_argument('--stage')
    parser.add_argument('--record')
    parser.add_argument('--stamp')
    parser.add_argument('--expect')
    parser.add_argument('--declared', action='store_true')
    parser.add_argument('command', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    if args.stamp is not None:
        try:
            expected = None if args.expect is None else [s for s in args.expect.split(',') if s]
            print(json.dumps(stamp(args.stamp, expected), sort_keys=True, separators=(',', ':')))
        except Invalid as error:
            print('null')
            print('gate legs: %s; the gate is RED' % error, file=sys.stderr)
            return 1
        return 0
    command = args.command[1:] if args.command[:1] == ['--'] else args.command
    if args.declared:
        if not args.stage or len(command) != 1:
            parser.error('--declared needs --stage and exactly one command string')
        return declared(args.stage, command[0])
    if not (args.root and args.stage and args.record) or len(command) != 1:
        parser.error('--root, --stage, --record and exactly one command string are required')
    return run_stage(args.root, args.stage, command[0], args.record)


if __name__ == '__main__':
    sys.exit(main())
