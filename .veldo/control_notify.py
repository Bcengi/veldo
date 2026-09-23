"""Release 1 journal notifications: in-process signals, never transport authority.

The authority installs Delivery with its explicit store path, coordinates, enabled
consumer names and real handlers. Use execute instead of calling the store directly;
other existing commit paths may notify with the returned journal identity AFTER commit.
Each handler receives a freshly resolved journal event, not the supplied payload.
The caller owns the event-loop thread and calls run_once (blocking while quiet).
Failed handlers and unavailable journal reads remain pending; successful handlers are
not retried. A retry waits a bounded exponential delay (retry_initial doubling up to
retry_cap) on the same condition commits signal, so a failing subscriber never polls
the store. A handler can act before raising, so handlers must tolerate retries.
observations is a bounded recent window; metrics() counts every operation.
Pending work is in-memory, not crash recovery.

Only the store writes domain state. Handlers still own their normal authorization
checks. This module grants none. No replay, reconnect, crash recovery, durable cursor,
worker launch, Telegram projection or database discovery polling is implemented here.
"""
from collections import Counter, deque
import json
import math
import threading
import time

SCHEMA = 'veldo.control_notification/v1'
# Consumer subscriptions are explicit. Intake and PM activate only when installed.
SUBSCRIPTIONS = {
    'settlement': ('settlement',),
    'assignment': ('assignment',),
    'dependency': ('dependency',),
    'completion': ('completion',),
    'budget': ('budget',),
    'intake': ('intake',),
    'pm': ('settlement', 'assignment', 'dependency', 'completion', 'budget', 'intake'),
}
COORDINATES = ('domain_uuid', 'repository_uuid', 'store_uuid')
IDENTITY = ('command_id', 'record_digest', 'watermark')


class Refused(Exception):
    def __init__(self, reason):
        super().__init__(reason)
        self.reason = reason


class Delivery:
    def __init__(self, store, path, coordinates, enabled, handlers, *, retry_initial=0.1,
                 retry_cap=30.0, observation_limit=1024, clock=time.monotonic):
        def seconds(value):
            return type(value) in (int, float) and math.isfinite(value) and value > 0
        if (not path or set(coordinates) != set(COORDINATES)
                or any(not isinstance(v, str) or not v for v in coordinates.values())
                or len(enabled) != len(set(enabled)) or not enabled
                or not set(enabled) <= set(SUBSCRIPTIONS)
                or set(enabled) != set(handlers)
                or not all(callable(h) for h in handlers.values())
                or not seconds(retry_initial) or not seconds(retry_cap) or retry_cap < retry_initial
                or type(observation_limit) is not int or observation_limit < 1 or not callable(clock)):
            raise Refused('invalid_registration')
        self.store, self.path = store, path
        self.coordinates, self.handlers = dict(coordinates), dict(handlers)
        self.registrations = {name: SUBSCRIPTIONS[name] for name in enabled}
        self._condition = threading.Condition()
        self._queue = deque()
        self._closed = False
        self._execution = threading.Lock()
        self._counts = Counter()
        # Retry pacing: bounded exponential delay, reached by waiting on the same condition.
        self.retry_initial, self.retry_cap, self.clock = retry_initial, retry_cap, clock
        # Observations are a bounded recent window; counts in metrics() stay complete.
        self.observation_limit = observation_limit
        self._observations = deque()

    @property
    def observations(self):
        with self._condition:
            return list(self._observations)

    def inventory(self):
        """The installed producer-kind/consumer pairs, including optional subscribers."""
        return sorted((kind, consumer) for consumer, kinds in self.registrations.items()
                      for kind in kinds)

    def hint(self, result):
        return dict(self.coordinates, schema=SCHEMA, command_id=result['command_id'],
                    record_digest=result['record_digest'], watermark=result['seq'])

    def execute(self, conn, command, signer, sign, authority_generation, **options):
        """One normal service commit path; failed transactions never notify.

        This is a seam for the authority service, not a replacement command registry.
        A duplicate store result is not a newly committed event and does not notify.
        """
        with self._execution:
            with self._condition:
                if self._closed:
                    raise Refused('service_unavailable')
            result = self.store.execute(conn, command, signer, sign, authority_generation, **options)
            if not result.get('replayed'):
                self.notify(self.hint(result))
            return result

    def notify(self, hint):
        """Queue a transport hint, not an authorized action. Resolve on consumption."""
        if not isinstance(hint, dict):
            return self._observe('notify', {}, 'invalid_input')
        # Only identity crosses the queue. Extra transport payload is not domain data.
        event = {key: hint.get(key) for key in ('schema',) + COORDINATES + IDENTITY}
        with self._condition:
            if self._closed:
                return self._observe('notify', event, 'service_unavailable')
            self._queue.append((event, None, 0, 0.0))
            self._condition.notify()
        return self._observe('notify', event, 'queued')

    def resolve(self, hint):
        """An independent read handle cannot see the writer's uncommitted transaction."""
        if (hint.get('schema') != SCHEMA or type(hint.get('watermark')) is not int
                or not 1 <= hint['watermark'] <= 2**63 - 1
                or any(not isinstance(hint.get(k), str) or not hint[k]
                       for k in ('command_id', 'record_digest'))):
            raise Refused('invalid_input')
        if any(hint.get(k) != v for k, v in self.coordinates.items()):
            raise Refused('missing_authority')
        conn = None
        try:
            conn = self.store.open_store(self.path, mode='r')
            row = conn.execute(
                'SELECT command_id, record_digest, transition, before_versions, after_versions, '
                'reservations, effects, principal, authority_generation FROM journal WHERE seq=?',
                (hint['watermark'],)).fetchone()
        except (OSError, self.store.sqlite3.Error, self.store.StoreRefused):
            raise Refused('service_unavailable') from None
        finally:
            if conn is not None:
                conn.close()
        if row is None:
            raise Refused('missing_evidence')
        if row[0] != hint['command_id'] or row[1] != hint['record_digest']:
            raise Refused('stale_subject')
        return dict(self.coordinates, command_id=row[0], record_digest=row[1],
                    watermark=hint['watermark'], transition=json.loads(row[2]),
                    before_versions=json.loads(row[3]), after_versions=json.loads(row[4]),
                    reservations=json.loads(row[5]), effects=json.loads(row[6]),
                    principal=row[7], authority_generation=row[8])

    def _take(self, timeout):
        deadline = None if timeout is None else self.clock() + timeout
        with self._condition:
            while True:
                now = self.clock()
                work = self._ready(now)
                if work is not None or self._closed:
                    return work
                if deadline is not None and deadline <= now:
                    return None
                # Sleep until the caller's deadline or the next retry falls due, whichever
                # is first; a new commit signals this same wait. Nothing reads the store.
                bounds = self._retry_waits(now) + ([] if deadline is None else [deadline - now])
                self._condition.wait(min(bounds) if bounds else None)

    def _ready(self, now):
        # Caller holds the condition. The first entry whose retry delay has passed.
        work = next((entry for entry in self._queue if entry[3] <= now), None)
        if work is not None:
            self._queue.remove(work)
        return work

    def _retry_waits(self, now):
        # Caller holds the condition. Positive delays until each pending retry falls due.
        return [entry[3] - now for entry in self._queue if entry[3] > now]

    def run_once(self, timeout=None):
        """Wait for an in-process signal. A timeout is caller-owned, never a DB poll.

        One loop owns dispatch. The queue predicate and signal use the same condition:
        an event before waiting stays queued; an event after waiting signals that wait.
        """
        work = self._take(timeout)
        if work is None:
            return None
        hint, remaining, failures, _ = work
        try:
            event = self.resolve(hint)
        except Refused as exc:
            # A retry was already resolved once; a first attempt is retained on the same
            # terms when the store was only unavailable. Other refusals are not events.
            if remaining is not None or exc.reason == 'service_unavailable':
                self._retry(hint, remaining, failures)
            return self._observe('consume', hint, exc.reason)
        kinds = {value['kind'] for value in event['transition'].values()}
        if event['reservations']:
            kinds.add('budget')
        delivered, failed = [], []
        owed = [consumer for consumer, subscriptions in self.registrations.items()
                if kinds.intersection(subscriptions) and (remaining is None or consumer in remaining)]
        for index, consumer in enumerate(owed):
            try:
                # A handler may mutate its argument; the next handler still sees the journal.
                self.handlers[consumer](json.loads(json.dumps(event)))
            except BaseException as exc:
                self._observe('handler', event, 'unknown_outcome', stopped_consumer=consumer)
                failed.append(consumer)
                if not isinstance(exc, Exception):
                    # An interrupt still propagates, but never discards this event for the
                    # interrupted subscriber or for subscribers not yet called.
                    self._retry(hint, failed + owed[index + 1:], failures)
                    raise
                continue
            delivered.append(consumer)
        if failed:
            self._retry(hint, failed, failures)
        return self._observe('consume', event, 'unknown_outcome' if failed else 'delivered',
                             delivered, failed=failed)

    def _retry(self, hint, remaining, failures):
        # Only internal dispatch state chooses retry recipients; transport cannot skip one.
        # Append behind other events so a failing subscriber cannot starve queued work.
        failures += 1
        delay = min(self.retry_cap, self.retry_initial * 2.0 ** min(failures - 1, 64))
        with self._condition:
            self._queue.append((hint, None if remaining is None else tuple(remaining),
                                failures, self.clock() + delay))
            self._condition.notify()

    def _observe(self, operation, event, outcome, delivered=(), stopped_consumer=None, failed=()):
        # Never log transport text, journal payload, principal or exception messages.
        # Coordinates/identities are included only when supplied by the trusted resolver.
        accepted = outcome in ('queued', 'delivered')
        row = dict(self.coordinates, operation=operation, outcome=outcome,
                   accepted=accepted, consumers=list(delivered))
        if outcome == 'delivered' or outcome == 'unknown_outcome':
            row.update({key: event[key] for key in IDENTITY})
            row['accepted_input_versions'] = event['after_versions']
        if failed:
            row['failed_consumers'] = list(failed)
        if stopped_consumer is not None:
            row['stopped_consumer'] = stopped_consumer
        with self._condition:
            self._counts['accepted' if accepted else 'refused'] += 1
            self._observations.append(row)
            while len(self._observations) > self.observation_limit:
                self._observations.popleft()
        return row

    def metrics(self):
        with self._condition:
            return dict(accepted=self._counts['accepted'], refused=self._counts['refused'],
                        pending=len(self._queue))

    def close(self):
        with self._execution:
            with self._condition:
                self._closed = True
                self._condition.notify_all()
