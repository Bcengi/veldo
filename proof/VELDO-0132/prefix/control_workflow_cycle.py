"""MARKED STAND-IN for the red record (proof/VELDO-0132/red.py). NOT production code.

At 5a5dfcd there is no workflow cycle service. What a caller had was the VELDO-0043 adapter over the
VELDO-0045 runtime and the production runner, which registers no workflow (its own docstring:
"Workflow definitions are supplied by VELDO-0132; this module registers none"), so every start
answers the named failure unsupported_workflow. This file gives the names suite 65 calls exactly
that behaviour: one adapter exchange per call through the unmodified runner, nothing bound, nothing
stored, nothing checked, nothing reported.
"""
import hashlib
import importlib.util
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCHEMA = 'pre-change: no workflow cycles'


def _sibling(alias, name):
    spec = importlib.util.spec_from_file_location(alias, HERE / name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def runner_source(revision):
    """The production runner exactly as it is: nothing registered."""
    return (HERE / 'control_graph_langgraph.py').read_text()


class Cycles:
    def __init__(self, store, conn, workflows, *, gate, principal, signer, sign, generation=1, runtime=None,
                 home=None, stage=None, timeout=120, observe=None, clock=None):
        self.conn, self.workflows, self.stage = conn, workflows, stage
        self.counts = {'accepted': 0, 'refused': 0}
        self.records = {}
        graph = _sibling('prechange_graph', 'control_graph.py')
        self.graph = graph
        self.adapter = graph.Adapter.installed(workflows.domain, workflows.repository, stage=stage)

    def start(self, cycle, *, workflow, subject, snapshot):
        row = self.conn.execute('SELECT version, data FROM entities WHERE id=?', ('workflow:' + workflow,)).fetchone()
        reference = {'id': workflow, 'version': row[0] if row else 1,
                     'digest': 'sha256:' + hashlib.sha256((row[1] if row else '').encode()).hexdigest()}
        try:
            answer = self.adapter.start(cycle, cycle + '.1', snapshot, reference)
            state = answer['outcome']
            refusal = (answer.get('failure') or {}).get('code')
        except self.graph.Refused as error:
            state, refusal = 'refused', error.code
        self.records[cycle] = {'cycle': cycle, 'subject': subject, 'state': state, 'refusal': refusal, 'trace': [],
                               'binding': None, 'steps': 0, 'proposals': [], 'waiting': None, 'assignment': None}
        return self.records[cycle]

    def advance(self, cycle, results=None):
        return self.records.get(cycle)

    def cancel(self, cycle):
        return self.records.get(cycle)

    def record(self, cycle):
        return self.records.get(cycle)

    def status(self):
        return dict(self.counts, pending=[])
