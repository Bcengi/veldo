#!/usr/bin/env python3
"""Journal-derived event publication (PLAN-0019 W36, VELDO-0051, R48, R76).

WHAT THIS MODULE IS. The projector that publishes the events the committed control journal
authoritatively carries into an enrolled repository's event log (.veldo/events.jsonl), in journal
order, at an explicit watermark. It reads the journal of ONE store (one domain) through a read-only
connection, walks every committed record in sequence, and derives an event where a record commits
the authoritative fact behind it. It writes nothing to the store.

WHAT IT DERIVES. spec.shipped, and only from a CONFIRMED LANDING RECEIPT FOR ITS EXACT UNIT AND
DISPATCH: a record committing a `completion_receipt` whose fact is revision_landed, and which

  - establishes that fact for the unit's current accepted revision and certifies it with a complete
    landing receipt (completion_contract.fact_problems and landing_receipt_problems, the predicates
    the Gate's completion reader applies to the same record);
  - names that unit in its landing receipt, and a unit of the projected repository;
  - names as its dispatch a PUBLICATION already committed in the journal (the VELDO-0028 protected
    effect `effect:<dispatch>`), of that same unit, domain and repository, whose push completed
    with every destination at the tip, and whose published commit and old tip are the receipt's
    candidate commit and old remote tip.

Anything else derives nothing, and a revision_landed receipt that fails any of these is REFUSED by
name and observed. A build-only attempt, an accepted artifact, a passing review, a receipt naming
another dispatch and a publication whose remote result is unknown are each not a landing. The event
is keyed to (domain, repository, unit, dispatch), so a second receipt for the same landing is
counted as a duplicate and never published twice, and it carries the journal record's sequence,
command and digest so it joins the authoritative journal by identity.

THE WATERMARK. The last journal sequence projected, and that record's digest, stored beside the log
(.veldo/events.watermark.json) after the events are appended. A projection starts after it and runs
to the head, or to an explicit sequence the caller names; a stored watermark whose digest is not the
journal's record at that sequence is refused (stale_subject:watermark), and nothing is written.

THE LOG. Appended through events.py's journal-projection path, which admits only this projection's
types with this projection's producer, under the same exclusive, non-blocking lock the review
projection takes. Historical bytes are never rewritten.

EXPLICIT COORDINATES. The store path, the domain, the repository and the destination root are
arguments; nothing is routed from the current directory or a module's ROOT.

WHAT IT IS NOT. Release 1 function only: one projector per destination, no replay after a crash
between the append and the watermark beyond skipping an id already in the log, no second clone, no
replica-failure recovery (Release 2) and no multi-repository matrix (Release 4). Standard library.
"""
import argparse
import datetime
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

try:                      # POSIX advisory locking, as events.py takes it for the review projection
    import fcntl
except ImportError:       # pragma: no cover - platform dependent
    fcntl = None


def _organ(name):
    spec = importlib.util.spec_from_file_location('event_projection_' + name.split('.')[0],
                                                  Path(__file__).resolve().with_name(name))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


EV = _organ('events.py')
CC = _organ('completion_contract.py')
VOCAB = EV._VOCAB

SCHEMA = 'veldo.event_projection/v1'
PRODUCER = VOCAB.JOURNAL_PROJECTION
SHIPPED = 'spec.shipped'
LOG = Path('.veldo') / 'events.jsonl'
WATERMARK = Path('.veldo') / 'events.watermark.json'
RECEIPT_KIND = 'completion_receipt'
LANDED = 'revision_landed'
EFFECT_KIND = 'protected_effect'
TAXONOMY = ('invalid_input', 'missing_authority', 'stale_subject', 'unavailable_service', 'missing_evidence',
            'unknown_outcome')
GENESIS = 'sha256:genesis'


def taxonomy(code):
    """The error class of a refusal code; a code with no class is an unknown outcome, never success."""
    head = str(code).split(':', 1)[0]
    return head if head in TAXONOMY else 'unknown_outcome'


class Refused(Exception):
    def __init__(self, code, detail=''):
        super().__init__('%s: %s' % (code, detail) if detail else code)
        self.code = code


def _text(value):
    return isinstance(value, str) and value.strip() != ''


def shipped_event_id(domain, repository, unit, dispatch):
    """The spec.shipped event's identity: one landing of one unit through one dispatch."""
    body = json.dumps([SHIPPED, domain, repository, unit, dispatch], separators=(',', ':'))
    return hashlib.sha256(body.encode()).hexdigest()[:EV.EVENT_ID_LEN]


def _iso(seconds):
    if isinstance(seconds, (int, float)) and not isinstance(seconds, bool):
        return datetime.datetime.fromtimestamp(int(seconds), datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ')
    return EV.now_iso()


def confirmed(publication):
    """Whether a publication effect's remote result is confirmed: completed, and every destination
    the push resolved at the tip. Accepted-only, refused and unknown outcomes are not."""
    destination = publication.get('destination') if isinstance(publication.get('destination'), dict) else {}
    reached = destination.get('destinations') if isinstance(destination.get('destinations'), list) else []
    return (publication.get('status') == 'completed' and publication.get('completed') is True and bool(reached)
            and all(isinstance(d, dict) and d.get('outcome') == 'at-tip' for d in reached))


def _receipt_codes(problems):
    codes = []
    for p in problems:
        if ' evidence ' in p and p.endswith(' is missing'):
            codes.append('missing_evidence:receipt/' + p.split(' evidence ', 1)[1][:-len(' is missing')])
        elif ' is about ' in p or 'names no subject' in p:
            codes.append('stale_subject:receipt/subject')
        elif 'superseded' in p:
            codes.append('stale_subject:receipt/superseded')
        else:
            codes.append('invalid_input:receipt')
    return codes


def _landing_codes(problems):
    return ['missing_evidence:landing/' + p[len('landing receipt lacks '):] if p.startswith('landing receipt lacks ')
            else 'invalid_input:landing' for p in problems]


class Projection:
    """The journal projection of one domain's store into one repository's event log.

    `store` is the control_store module, `database` the explicit store path, `domain` and
    `repository` the coordinates, `root` the destination repository root whose .veldo/events.jsonl
    and .veldo/events.watermark.json it publishes. `observe` receives one record per operation."""

    def __init__(self, store, database, *, domain, repository, root, observe=None):
        if not all(_text(v) for v in (domain, repository)) or not _text(str(database or '')):
            raise Refused('invalid_input:coordinates', 'the store, the domain and the repository are named')
        if not Path(root).is_dir():
            raise Refused('invalid_input:destination', 'the destination root is an existing directory')
        self.store, self.database = store, str(database)
        self.domain, self.repository = domain, repository
        self.root = Path(root).resolve()
        self.log, self.cursor = self.root / LOG, self.root / WATERMARK
        self.observe = observe or (lambda event: None)
        self.counts = {'accepted': 0, 'refused': 0}

    # Reads.

    def _rows(self):
        if not Path(self.database).is_file():
            raise Refused('unavailable_service:store', 'no store at the named path')
        try:
            conn = self.store.open_store(self.database, mode='r')
        except (OSError, self.store.StoreRefused, self.store.sqlite3.Error) as error:
            raise Refused('unavailable_service:store', str(error)) from None
        try:
            return [(seq, command, digest, json.loads(transition), committed) for seq, command, digest, transition, committed
                    in conn.execute('SELECT j.seq, j.command_id, j.record_digest, j.transition, p.committed_at FROM journal j '
                                    'LEFT JOIN publication p ON p.seq = j.seq ORDER BY j.seq')]
        finally:
            conn.close()

    def watermark(self):
        """The stored watermark {watermark, record_digest}, or None before the first projection."""
        try:
            text = self.cursor.read_text()
        except FileNotFoundError:
            return None
        try:
            mark = json.loads(text)
        except ValueError:
            raise Refused('invalid_input:watermark', 'the stored watermark does not parse') from None
        if (not isinstance(mark, dict) or mark.get('schema') != SCHEMA or mark.get('domain') != self.domain
                or mark.get('repository') != self.repository or type(mark.get('watermark')) is not int
                or mark['watermark'] < 0 or not _text(mark.get('record_digest'))):
            raise Refused('invalid_input:watermark', 'the stored watermark is not this projection\'s')
        return mark

    def _landing(self, state, receipt):
        """(refusals, unit, dispatch, landing) for one revision_landed receipt, judged against the
        journal state committed BEFORE the record that carries it."""
        refusals = []
        subject = receipt.get('subject') if isinstance(receipt.get('subject'), dict) else {}
        unit = subject.get('id') if _text(subject.get('id')) else None
        row = state.get(unit) if unit else None
        if not row or row.get('kind') != 'execution_unit':
            refusals.append('missing_authority:unit')
            expected = None
        else:
            if (row.get('data') or {}).get('repository_uuid') != self.repository:
                refusals.append('missing_authority:repository')
            expected = {'id': unit, 'revision': (row.get('data') or {}).get('revision')}
        refusals += _receipt_codes(CC.fact_problems(LANDED, receipt, expected))
        landing = receipt.get('publication_receipt') if isinstance(receipt.get('publication_receipt'), dict) else {}
        refusals += _landing_codes(CC.landing_receipt_problems(landing))
        if landing.get('unit_id') != unit:
            refusals.append('stale_subject:landing/unit')
        dispatch = landing.get('dispatch_id') if _text(landing.get('dispatch_id')) else None
        effect = state.get('effect:' + dispatch) if dispatch else None
        publication = effect.get('data') if effect and effect.get('kind') == EFFECT_KIND else None
        if (not isinstance(publication, dict) or publication.get('kind') != 'publication'
                or publication.get('dispatch_id') != dispatch):
            refusals.append('missing_authority:dispatch')
        else:
            if publication.get('unit') != unit:
                refusals.append('stale_subject:dispatch/unit')
            if (publication.get('domain_uuid'), publication.get('repository_uuid')) != (self.domain, self.repository):
                refusals.append('missing_authority:dispatch/coordinates')
            if not confirmed(publication):
                refusals.append('unknown_outcome:publication')
            payload = publication.get('payload') if isinstance(publication.get('payload'), dict) else {}
            if (landing.get('candidate_commit') != payload.get('commit')
                    or landing.get('old_remote_tip') != payload.get('old_tip')):
                refusals.append('stale_subject:landing/candidate')
        return refusals, unit, dispatch, landing

    def derive(self, rows, after):
        """(events, judged): every spec.shipped the records after `after` carry, in journal order, and
        every revision_landed receipt judged, accepted or with its named refusals."""
        state, events, judged = {}, [], []
        for seq, command, digest, changes, committed in rows:
            if seq > after:
                for eid in sorted(changes):
                    entry = changes[eid] if isinstance(changes[eid], dict) else {}
                    data = entry.get('data') if isinstance(entry.get('data'), dict) else {}
                    if entry.get('kind') != RECEIPT_KIND or data.get('fact') != LANDED:
                        continue
                    refusals, unit, dispatch, landing = self._landing(state, data)
                    item = {'journal_seq': seq, 'command_id': command, 'record_digest': digest, 'receipt': eid,
                            'unit': unit, 'dispatch_id': dispatch, 'refusals': refusals}
                    if not refusals:
                        item['event'] = shipped_event_id(self.domain, self.repository, unit, dispatch)
                        events.append(EV.make_event(
                            SHIPPED, commit=landing['candidate_commit'], spec=unit, producer=PRODUCER,
                            at=_iso(committed), event_id=item['event'],
                            extra={'domain': self.domain, 'repository': self.repository, 'unit': unit,
                                   'dispatch_id': dispatch, 'journal_seq': seq, 'command_id': command,
                                   'record_digest': digest, 'receipt': eid, 'receipt_digest': entry.get('digest'),
                                   'implementation_commit': landing['implementation_commit']}))
                    judged.append(item)
            state.update(changes)
        return events, judged

    # The one write.

    def publish(self, upto=None):
        """Project the journal after the stored watermark up to `upto` (default: the head) into the
        destination log, then store the new watermark. Returns the report; a refusal raises Refused
        with nothing written."""
        try:
            return self._publish(upto)
        except Refused as error:
            self.counts['refused'] += 1
            self._emit('publish', outcome='refused', refusal=error.code, taxonomy=taxonomy(error.code))
            raise

    def _publish(self, upto):
        rows = self._rows()
        head = rows[-1][0] if rows else 0
        digests = {seq: digest for seq, _c, digest, _t, _p in rows}
        mark = self.watermark()
        after = mark['watermark'] if mark else 0
        if mark and digests.get(after, GENESIS if after == 0 else None) != mark['record_digest']:
            raise Refused('stale_subject:watermark', 'the stored watermark names another journal record')
        target = head if upto is None else upto
        if type(target) is not int or not after <= target <= head:
            raise Refused('invalid_input:watermark', 'a projection runs from %d to at most the head %d' % (after, head))
        events, judged = self.derive([r for r in rows if r[0] <= target], after)
        if not self.log.parent.is_dir():
            raise Refused('invalid_input:destination', 'the destination has no .veldo directory')
        with open(self.log, 'a+') as fh:
            if fcntl is None:
                raise Refused('unavailable_service:lock', 'no fcntl on this platform')
            try:
                fcntl.flock(fh.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
            except OSError:
                raise Refused('unavailable_service:lock', 'another projection holds the log') from None
            fh.seek(0)
            present = self._present(fh.read())
            fresh = [e for e in events if e['id'] not in present]
            try:
                EV.append_journal_projection(fh, fresh)
            except ValueError as error:
                raise Refused('invalid_input:event', str(error)) from None
            os.fsync(fh.fileno())
            record = {'schema': SCHEMA, 'domain': self.domain, 'repository': self.repository, 'watermark': target,
                      'record_digest': digests.get(target, GENESIS), 'log': LOG.as_posix()}
            temporary = self.cursor.with_name(self.cursor.name + '.%d.tmp' % os.getpid())
            temporary.write_text(json.dumps(record, sort_keys=True) + '\n')
            os.replace(temporary, self.cursor)
        for item in judged:
            accepted = not item['refusals']
            self.counts['accepted' if accepted else 'refused'] += 1
            refusal = None if accepted else item['refusals'][0]
            self._emit('project_receipt', unit=item['unit'], request=item['command_id'], receipt=item['receipt'],
                       dispatch=item['dispatch_id'], journal_seq=item['journal_seq'],
                       accepted_versions={'watermark': after}, outcome='accepted' if accepted else 'refused',
                       refusal=refusal, refusals=list(item['refusals']),
                       taxonomy=None if accepted else taxonomy(refusal), event=item.get('event'))
        report = {'watermark_before': after, 'watermark': target, 'head': head,
                  'published': [e['id'] for e in fresh], 'duplicates': len(events) - len(fresh),
                  'judged': judged}
        self._emit('publish', outcome='accepted', accepted_versions={'watermark': after}, watermark=target,
                   published=report['published'], duplicates=report['duplicates'])
        return report

    def status(self):
        """Metrics: accepted and refused operations, the stored watermark, the journal head, and the
        pending work: committed records and landings after the watermark, not yet projected."""
        rows = self._rows()
        mark = self.watermark()
        after = mark['watermark'] if mark else 0
        head = rows[-1][0] if rows else 0
        events, _judged = self.derive(rows, after)
        present = self._present()
        return dict(self.counts, watermark=after, head=head, pending_records=max(0, head - after),
                    pending_events=[e['id'] for e in events if e['id'] not in present])

    def _present(self, text=None):
        """The ids of this projection's lines already in the destination log."""
        if text is None:
            try:
                text = self.log.read_text()
            except FileNotFoundError:
                return set()
        present = set()
        for line in text.splitlines():
            try:
                known = json.loads(line)
            except ValueError:
                continue
            if isinstance(known, dict) and known.get('producer') == PRODUCER:
                present.add(known.get('id'))
        return present

    def _emit(self, operation, **fields):
        self.observe(dict({'schema': SCHEMA, 'operation': operation, 'domain': self.domain,
                           'repository': self.repository}, **fields))


def main(argv=None):
    parser = argparse.ArgumentParser(description='Publish the journal-derived events of one store into one repository.')
    parser.add_argument('command', choices=('publish', 'status'))
    parser.add_argument('--store', required=True)
    parser.add_argument('--domain', required=True)
    parser.add_argument('--repository', required=True)
    parser.add_argument('--root', required=True, help='the destination repository root')
    parser.add_argument('--upto', type=int, help='project up to this journal sequence (default: the head)')
    args = parser.parse_args(argv)
    observed = []
    try:
        projection = Projection(_organ('control_store.py'), args.store, domain=args.domain,
                                repository=args.repository, root=args.root, observe=observed.append)
        result = projection.publish(args.upto) if args.command == 'publish' else projection.status()
    except Refused as error:
        print(json.dumps({'refused': error.code, 'taxonomy': taxonomy(error.code), 'observations': observed}))
        return 2
    print(json.dumps({'result': result, 'observations': observed}, sort_keys=True))
    return 0


if __name__ == '__main__':
    sys.exit(main())
