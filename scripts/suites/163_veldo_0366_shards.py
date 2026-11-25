"""Exact distributed mutation coverage and cleanup, with fake hosts only."""

def _v366_checks():
    import importlib.util
    def load(path):
        spec = importlib.util.spec_from_file_location(path.stem, path)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    shards = load(ROOT / "scripts" / "mutation_shards.py")
    transport = load(ROOT / "scripts" / "mutation_transport.py")
    worker = load(ROOT / "scripts" / "reuse_worker.py")
    gate = load(ROOT / 'scripts/check_gate_mutations.py')
    helpers = load(ROOT / 'scripts/suites/support/v366_nodes.py')
    helpers.checks(gate, shards, transport, ROOT, expect, worker)

_v366_checks()
