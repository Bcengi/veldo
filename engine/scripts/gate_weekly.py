"""VELDO-0367 weekly authority primitives. No scheduling or live entry until increment 5.

The coordinator supplies authority time and host observations, never candidate values.
Admission is an event-driven state machine: a waiting return schedules no validation.
All callers use the same private Store endpoint, repository identity and host enrollment.
"""
import argparse
import copy
import importlib.util
import math
from pathlib import Path
import secrets

WEEKLY_ENABLED = False
WEEK_SECONDS = 7 * 24 * 60 * 60
SCHEMA = 'veldo.weekly-run/v1'


def sibling(name):
    spec = importlib.util.spec_from_file_location(name, Path(__file__).with_name(name + '.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def repository_state(ledger, repository):
    if not isinstance(repository, str) or not repository:
        raise ValueError('weekly repository identity')
    return ledger['repositories'].setdefault(repository, dict(last_full_started_at=None,
                                                             reservation=None, runs={}))


def timestamp(now):
    if isinstance(now, bool) or not isinstance(now, (float, int)) or not math.isfinite(now) or now < 0:
        raise ValueError('authority timestamp')
    return now


class Weekly:
    def __init__(self, store, repository):
        self.store, self.repository = store, repository

    def request(self, commit, host, now):
        """Concurrent seed, weekly and recovery requests share the one reservation.

        A pending reservation consumes no slot. A crash after start consumes the week.
        The selected commit/host is immutable; another caller joins that request.
        """
        timestamp(now)
        if not isinstance(commit, str) or len(commit) not in (40, 64) or any(c not in '0123456789abcdef' for c in commit):
            raise ValueError('weekly immutable commit')
        if not isinstance(host, str) or not host:
            raise ValueError('weekly host identity')
        with self.store.weekly_transaction() as ledger:
            state = repository_state(ledger, self.repository)
            if state['reservation'] is not None:
                return copy.deepcopy(state['reservation'])
            previous = state['last_full_started_at']
            if previous is not None and now - previous < WEEK_SECONDS:
                return dict(status='waiting', reason='seven-day limit', eligible_at=previous + WEEK_SECONDS)
            if any(run['status'] == 'running' for run in state['runs'].values()):
                return dict(status='waiting', reason='prior full run retains custody')
            reservation = dict(schema=SCHEMA, run_id=secrets.token_hex(16), commit=commit,
                               host=host, status='waiting', reason='exclusive idle-host admission')
            state['reservation'] = reservation
            return copy.deepcopy(reservation)

    def cancel(self, run_id):
        with self.store.weekly_transaction() as ledger:
            state = repository_state(ledger, self.repository)
            if state['reservation'] and state['reservation']['run_id'] == run_id:
                state['reservation'] = None

    def start(self, reservation, now, custody, old_results):
        """Called only after exclusive locks and a second all-user occupancy observation."""
        timestamp(now)
        if not custody.admitted(reservation['host']):
            return dict(status='waiting', reason=custody.reason)
        with self.store.weekly_transaction() as ledger:
            state = repository_state(ledger, self.repository)
            if state['reservation'] != reservation:
                return dict(status='waiting', reason='reservation changed')
            previous = state['last_full_started_at']
            if previous is not None and now - previous < WEEK_SECONDS:
                return dict(status='waiting', reason='seven-day limit')
            # This is the only consumption point, immediately before any validation starts.
            run = dict(reservation, status='running', started_at=now,
                       old_results=copy.deepcopy(old_results), ticket=None)
            state['last_full_started_at'] = now
            state['runs'][run['run_id']] = run
            state['reservation'] = None
            return copy.deepcopy(run)

    def red(self, run_id, failed_items, observations, *, stages=(), uncertain=False):
        """Atomically revoke a dependency closure and create an idempotent durable ticket.

        old_results maps item IDs to {result_digest, stage, depends_on: [item IDs]}.
        Missing localization or observer/inventory failures invalidate the whole inventory.
        Every inherited source digest must be included in old_results by the coordinator.
        """
        with self.store.weekly_transaction() as ledger:
            state = repository_state(ledger, self.repository)
            run = state['runs'][run_id]
            if run['status'] == 'red':
                return copy.deepcopy(run['ticket'])
            if run['status'] != 'running':
                raise ValueError('weekly run already settled')
            old = run['old_results']
            failed = set(failed_items)
            affected = set(old) if uncertain or not failed and not stages else failed & set(old)
            affected.update(key for key, value in old.items() if value['stage'] in stages)
            if failed - set(old):
                affected.update(old)
            while True:
                expanded = affected | {key for key, value in old.items()
                                       if set(value.get('depends_on', ())) & affected}
                if expanded == affected:
                    break
                affected = expanded
            revoked = {old[key]['result_digest'] for key in affected}
            ledger['revoked'] = sorted(set(ledger['revoked']) | revoked)
            ticket = dict(schema='veldo.weekly-ticket/v1', key='weekly/' + run_id,
                          run_id=run_id, commit=run['commit'], failed_items=sorted(failed),
                          affected_items=sorted(affected), old_results=copy.deepcopy(old),
                          fresh_observations=copy.deepcopy(observations), status='pending')
            run.update(status='red', ticket=ticket)
            return copy.deepcopy(ticket)

    def recover(self, run_id):
        """Keeper calls after descendant cleanup on interruption, before dropping locks."""
        state = self.store.weekly_read()['repositories'][self.repository]
        if run_id in state['runs'] and state['runs'][run_id]['status'] == 'running':
            return self.red(run_id, [], {'interrupted': True}, uncertain=True)
        return None

    def deliver_ticket(self, run_id, create):
        """The backlog adapter must upsert by key. A failed send leaves a durable retry."""
        run = self.store.weekly_read()['repositories'][self.repository]['runs'][run_id]
        ticket = run['ticket']
        if ticket is None or ticket['status'] == 'delivered':
            return ticket
        external_id = create(copy.deepcopy(ticket))
        if not isinstance(external_id, str) or not external_id:
            raise ValueError('backlog ticket acknowledgement')
        with self.store.weekly_transaction() as ledger:
            ticket = repository_state(ledger, self.repository)['runs'][run_id]['ticket']
            ticket.update(status='delivered', external_id=external_id)
            return copy.deepcopy(ticket)

    def execute(self, reservation, now, custody, root, inventory, old_results, execute, cleanup):
        """Dormant common-gate adapter; all workload launches use custody.launch.

        execute receives the fresh plan and a monitor it must service on process/host
        events. Its build directory must be newly created; no cache-read capability
        is supplied. Production enrollment requires cgroup cleanup, including escaped
        descendants. The fixture adapter uses private process groups.
        """
        if not custody.acquire():
            return dict(status='waiting', reason=custody.reason)
        run_id = reservation['run_id']
        custody.guard(cleanup, lambda: self.recover(run_id))
        try:
            run = self.start(reservation, now, custody, old_results)
            if run['status'] != 'running':
                return run
            def monitor():
                if not custody.admitted(reservation['host']):
                    raise ValueError('weekly occupancy changed: ' + str(custody.reason))
            try:
                plan = fresh_plan(root, reservation['commit'], inventory)
                receipt = execute(plan, monitor, custody.launch)
                cleanup(custody.groups)
                custody.reap()
                monitor()
                fresh_plan(root, reservation['commit'], inventory)  # immutable checkout recheck
                return self.green(run_id, root, inventory, receipt)
            except Exception as error:
                cleanup(custody.groups)
                custody.reap()
                self.red(run_id, [], {'error': str(error)}, uncertain=True)
                raise
        finally:
            custody.close()

    def green(self, run_id, root, inventory, receipt):
        """Fresh full receipts refresh sources; partial, carried and row-only runs cannot."""
        changes = sibling('gate_changes')
        with self.store.weekly_transaction() as ledger:
            return self._green(run_id, root, inventory, receipt, changes, ledger)

    def _green(self, run_id, root, inventory, receipt, changes, ledger):
        run = repository_state(ledger, self.repository)['runs'][run_id]
        if run['status'] != 'running' or receipt['candidate_commit'] != run['commit']:
            raise ValueError('weekly run identity')
        changes.validate_receipt(receipt, inventory)
        for item in receipt['items']:
            if item['status'] in ('not-applicable', 'waived', 'removed'):
                continue
            if item['status'] != 'executed' or item['source_commit'] != run['commit']:
                raise ValueError('weekly fresh execution required')
            dep = changes.item_evidence(self.store, item)
            if not dep['complete']:
                raise ValueError('weekly complete observations required')
            result = self.store.get(item['result_digest'])
            if result.get('execution_record_digest'):
                execution = self.store.get(result['execution_record_digest'])
                if execution['result']['execution_scope'] != 'suite':
                    raise ValueError('weekly whole-suite mutation required')
        gate = changes.publish_gate(root, self.store, self.repository, inventory, receipt)
        run.update(status='green', gate_digest=gate['record_digest'])
        return gate


def fresh_plan(root, commit, inventory):
    """No selected rows, carried controls, or cache inputs in a weekly execution plan."""
    changes = sibling('gate_changes')
    changes.pin(root, commit)
    if (changes.git(root, 'rev-parse', 'HEAD').decode().strip() != commit
            or changes.git(root, 'status', '--porcelain', '--untracked-files=all')):
        raise ValueError('weekly requires a clean immutable checkout')
    changes.validate_inventory(inventory)
    return dict(candidate_commit=commit, inventory=inventory,
                items=[dict(item, action='execute' if item['state'] == 'required' else item['state'])
                       for item in inventory['items']],
                cache_reads=False, fresh_build_outputs=True, mutation_scope='suite',
                controls='once-per-suite', publish=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--candidate')
    parser.add_argument('--sink')
    parser.parse_args(argv)
    if not WEEKLY_ENABLED:
        print('weekly: waiting (inactive until increment 5; no full run started)')
        return 75
    raise ValueError('weekly enrollment and common gate adapter required')


if __name__ == '__main__':
    raise SystemExit(main())
