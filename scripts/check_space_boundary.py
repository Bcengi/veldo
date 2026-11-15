#!/usr/bin/env python3
"""VELDO-0304: creation, removal and age boundaries, checked by function."""
import ast
from pathlib import Path
import shlex


# Canonical paths also name their installed copies. Each exception is a function,
# never a whole module. Reasons are reviewed with design 6.10.
CREATORS = {
    ('engine/.veldo/action_executor.py', '_cli'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/authority_contract.py', 'ssh_keygen_verify'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/capsule.py', 'run_capsule'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_agent_config_handoff.py', 'codex_observe'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_api_webauthn.py', 'openssl_verifies'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_architecture.py', 'ArchitectureAuthority._judge'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_batch.py', 'Batch._merge'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_engine_codex.py', 'bundled_catalog'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_engine_codex.py', 'feature_listing'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_factory_setup_dispatch.py', 'checked_work'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_graph.py', '_working_directory'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_graph_install.py', 'install'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_graph_isolation.py', 'probe_graph'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_graph_isolation.py', 'run_entry'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_launch_work.py', 'Runtime._collect'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_memory_check.py', 'check'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_memory_check.py', 'probe'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_repository_provisioner.py', 'lay_scaffold'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_runtime.py', 'metadata_problems'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_runtime.py', 'probe_graph'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_runtime.py', 'qualify'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_runtime.py', 'run_hidden'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_service.py', 'find_principals'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_space_probe.py', 'reader_check'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_workflow_cycle.py', 'Cycles._exchange'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/control_workflow_cycle_pm.py', 'ProjectCycles.exchange'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/executor.py', 'LiveLoop.gate'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/fix_validation.py', 'main'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/fix_validation.py', 'validate'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/fleet.py', 'WorktreeProvisioner.add'): 'Declares the worker worktree through SpaceCreator before adding it.',
    ('engine/.veldo/git_process.py', '_invoke'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/lander.py', 'GitLandOps._union_resolve_one'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/pack_conformance.py', '_conform_one'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/pack_conformance.py', 'gate_exit_for_state'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/pack_conformance.py', 'real_push_exec_bit'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/qualify.py', 'claude_builtins'): 'Creates a private temporary tree for this call.',
    ('engine/.veldo/qualify.py', 'fixtures'): 'Creates a private temporary tree for this call.',
    ('engine/scripts/agent_sandbox.py', 'launch'): 'Creates a private temporary tree for this call.',
    ('engine/scripts/agent_sandbox.py', 'namespace_selftest'): 'Creates a private temporary tree for this call.',
    ('engine/scripts/agent_sandbox.py', 'prepare'): 'The sandbox creator; run context declares the private repository and worktree.',
    ('engine/scripts/check_gate_mutations.py', 'run_stage'): 'Creates a private temporary tree for this call.',
    ('engine/scripts/runners/plugin/plugin_load_runner.py', 'install_case'): 'Creates a private temporary tree for this call.',
    ('engine/scripts/runners/process/process_runner.py', 'run'): 'Creates a private temporary tree for this call.',
    ('scripts/check_first_use.py', 'main'): 'Creates a private temporary tree for this call.',
    ('scripts/check_install_and_run.py', 'check'): 'Creates a private temporary tree for this call.',
    ('scripts/check_review_mutations.py', 'main'): 'Creates a private temporary tree for this call.',
    ('scripts/drive.py', 'main'): 'Creates a private temporary tree for this call.',
    ('scripts/drive.py', 'red'): 'Creates a private temporary tree for this call.',
    ('scripts/parser_corpus_audit.py', 'main'): 'Creates a private temporary tree for this call.',
    ('scripts/propose_case_inputs.py', 'trace_case'): 'Creates a private temporary tree for this call.',
    ('scripts/render_pdfs.py', 'main'): 'Creates a private temporary tree for this call.',
    ('scripts/suite_equiv.py', 'main'): 'Creates a private temporary tree for this call.',
}
REVIEWED = {
    ('engine/.veldo/action_executor.py', '_cli'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/authority_contract.py', 'ssh_keygen_verify'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_agent_config_handoff.py', 'codex_observe'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_api_webauthn.py', 'openssl_verifies'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_architecture.py', 'ArchitectureAuthority._judge'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_batch.py', 'Batch._merge'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_engine_codex.py', 'bundled_catalog'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_engine_codex.py', 'feature_listing'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_factory_setup_dispatch.py', 'checked_work'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_graph.py', '_remove'): 'The graph invocation removes only its freshly built private working directory.',
    ('engine/.veldo/control_graph_install.py', 'install'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_graph_install.py', 'swap_in'): 'Install replaces the folder it just built; design 6.10.',
    ('engine/.veldo/control_graph_isolation.py', 'probe_graph'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_graph_isolation.py', 'run_entry'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_launch_work.py', 'Runtime._collect'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_memory_check.py', 'check'): "Removes this check's private staging copy; design 6.10.",
    ('engine/.veldo/control_memory_check.py', 'copy_chroma'): 'Removes only the copies this call just built; design 6.10.',
    ('engine/.veldo/control_memory_check.py', 'probe'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_repository_provisioner.py', 'lay_scaffold'): 'Removes the private scaffold clone this call made; design 6.10.',
    ('engine/.veldo/control_runtime.py', 'metadata_problems'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_runtime.py', 'probe_graph'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_runtime.py', 'qualify'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_runtime.py', 'run_hidden'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_service.py', '_remove_tree'): "Rolls back the same install or the owner's uninstall of the service home; design 6.10.",
    ('engine/.veldo/control_service.py', 'find_principals'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_space_probe.py', 'reader_check'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_workflow_cycle.py', 'Cycles._exchange'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/control_workflow_cycle_pm.py', 'ProjectCycles.exchange'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/executor.py', 'LiveLoop.gate'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/fix_validation.py', 'main'): "Removes only this validation's private run tree; design 6.10.",
    ('engine/.veldo/git_process.py', '_invoke'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/init_scaffold.py', 'lay_ui'): 'Installs by replacing the folder it just built; design 6.10.',
    ('engine/.veldo/lander.py', 'GitLandOps._union_resolve_one'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/pack_conformance.py', '_conform_one'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/pack_conformance.py', 'gate_exit_for_state'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/pack_conformance.py', 'real_push_exec_bit'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/qualify.py', 'claude_builtins'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/.veldo/qualify.py', 'fixtures'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/scripts/agent_sandbox.py', 'discard_journal'): 'Borrow journal at completed login restoration; design 6.10.',
    ('engine/scripts/agent_sandbox.py', 'namespace_selftest'): "Only the selftest's own freshly created worktree; design 6.10.",
    ('engine/scripts/agent_sandbox.py', 'remove_tree'): "Only the launcher's own unrecorded scratch at its end; design 6.10.",
    ('engine/scripts/agent_sandbox.py', 'restore_login'): 'Recovery folder after its contents are restored; design 6.10.',
    ('engine/scripts/check_gate_mutations.py', 'Workers.release_snapshot'): "Mutation worker's own snapshot; design 6.10.",
    ('engine/scripts/check_gate_mutations.py', 'run_stage'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('engine/scripts/check_gate_mutations.py', 'snapshot'): "Mutation worker's own failed snapshot; design 6.10.",
    ('engine/scripts/gate_schedule.py', 'NodeInputs.close'): "The gate's own schedule inputs; design 6.10.",
    ('engine/scripts/mutation_ownership.py', 'remove_tree'): 'Worker directories recorded in its own ownership ledger at worker end; design 6.10.',
    ('engine/scripts/runners/plugin/plugin_load_runner.py', 'install_case'): "The check's own two temporary folders; design 6.10.",
    ('engine/scripts/runners/process/process_runner.py', 'run'): "The check's own lifecycle temporary folder; design 6.10.",
    ('scripts/check_first_use.py', '_rmtree'): 'Lead decision 2026-11-15: only its own mkdtemp tree, system temporary directory and own prefix.',
    ('scripts/check_install_and_run.py', 'check'): 'Lead decision class: only the mkdtemp result created by this call, with its own prefix.',
    ('scripts/check_review_mutations.py', 'main'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('scripts/drive.py', 'main'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('scripts/drive.py', 'red'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('scripts/parser_corpus_audit.py', 'main'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('scripts/propose_case_inputs.py', 'trace_case'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('scripts/render_pdfs.py', 'main'): 'Scoped TemporaryDirectory owns the exact mkdtemp result and cleans only that tree.',
    ('scripts/suite_equiv.py', 'main'): 'Lead decision class: only each mkdtemp result this call created with its own prefix.',
}
REMOVERS = {
    ('engine/.veldo/control_space_remove.py', 'remove_ref'): 'Ended ledger item, verified keep and compare-and-delete.',
    ('engine/.veldo/control_space_remove.py', '_worktree_remove'): 'The existing non-forced worktree remover.',
    ('engine/.veldo/control_space_remove.py', '<module>'): 'The existing measured engine remover table.',
}


def canonical(path):
    path = str(path)
    if path.startswith('.veldo/'):
        return 'engine/' + path
    if path.startswith('scripts/') and (Path(__file__).resolve().parents[1] / 'engine' / path).is_file():
        return 'engine/' + path
    return path


def name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return name(node.value) + '.' + node.attr
    return ''


def words(node, values, seen=()):
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return [node.value]
    if isinstance(node, ast.Name) and node.id in values and node.id not in seen:
        return words(values[node.id], values, (*seen, node.id))
    if isinstance(node, (ast.List, ast.Tuple)):
        return [word for value in node.elts for word in words(value, values, seen)]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return words(node.left, values, seen) + words(node.right, values, seen)
    return []


def primitives(node, values):
    """Classify executed calls, not examples in strings or comments."""
    if not isinstance(node, ast.Call):
        return set()
    called = name(node.func)
    tail = called.rsplit('.', 1)[-1]
    result = set()
    if tail in ('mkdtemp', 'TemporaryDirectory'):
        result.add('create:temporary folder')
    if tail == 'TemporaryDirectory':
        keywords = {keyword.arg: keyword.value for keyword in node.keywords}
        prefix = keywords.get('prefix')
        scoped = (not node.args and 'dir' not in keywords and None not in keywords
                  and isinstance(prefix, ast.Constant) and isinstance(prefix.value, str) and bool(prefix.value))
        result.add('remove:scoped temporary' if scoped else 'remove:unscoped temporary')
    if tail == 'rmtree':
        result.add('remove:recursive folder')
    if tail in ('unlink', 'rmdir') or called in ('os.remove', 'os.removedirs'):
        result.add('delete:single path')
    if tail in ('remove_tree', '_remove_tree', '_rmtree', 'space_signal', 'remove_ref', 'remove_path'):
        result.add('delete:remover call')
    vector = [word for arg in node.args for word in words(arg, values)]
    if tail in ('run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen'):
        vector = [token for word in vector for token in shlex.split(word)]
    git = 'git' in called.lower() or 'git' in vector
    if git:
        if ('worktree' in vector or 'worktree' in called) and 'add' in vector:
            result.add('create:git worktree add')
        if ('worktree' in vector or 'worktree' in called) and 'remove' in vector:
            result.add('remove:git worktree remove')
        if 'update-ref' in vector and any(x in vector for x in ('-d', '--delete')):
            result.add('history:git ref delete')
        if ('stash' in vector and any(x in vector for x in ('drop', 'clear'))
                or 'reflog' in vector and 'expire' in vector or 'prune' in vector
                or 'gc' in vector):
            result.add('history:git object removal')
    if 'rm' in vector and any(x.startswith('-') and ('r' in x or x == '--recursive') for x in vector):
        result.add('remove:shell recursive remove')
    docker = 'docker' in called or 'docker' in vector or tail in ('_engine', 'client')
    if docker:
        if any(x in vector for x in ('rm', 'rmi', 'prune')):
            result.add('remove:engine remove')
        if any(x in vector for x in ('create', 'run', 'build')):
            result.add('create:engine object')
    return result


def functions(source):
    tree = ast.parse(source)
    found = []

    def visit(node, scope):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope = (*scope, node.name)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            nodes = []

            def local(part):
                nodes.append(part)
                for child in ast.iter_child_nodes(part):
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef, ast.Lambda)):
                        local(child)
            local(node)
            values = {target.id: part.value for part in nodes if isinstance(part, ast.Assign)
                      for target in part.targets if isinstance(target, ast.Name)}
            found.append(('.'.join(scope) or '<module>', nodes, values))
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                visit(child, scope)
            elif not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                visit(child, scope)
    visit(tree, ())
    return found


def inventory(source):
    for function, nodes, values in functions(source):
        hits = [(node.lineno, primitive) for node in nodes for primitive in primitives(node, values)]
        times = [node for node in nodes if isinstance(node, ast.Attribute)
                 and node.attr in ('st_mtime', 'st_ctime', 'st_atime', 'st_mtime_ns', 'st_ctime_ns', 'st_atime_ns')]
        clocks = [node for node in nodes if isinstance(node, ast.Compare) and any(
            isinstance(part, ast.Call) and name(part.func).rsplit('.', 1)[-1] in
            ('time', 'monotonic', 'now', 'utcnow', 'clock') for part in ast.walk(node))]
        # A local clock value compared later is the same test.
        clocks += [node for node in nodes if isinstance(node, ast.Compare) and any(
            isinstance(part, ast.Name) and isinstance(values.get(part.id), ast.Call)
            and name(values[part.id].func).rsplit('.', 1)[-1] in
            ('time', 'monotonic', 'now', 'utcnow', 'clock') for part in ast.walk(node))]
        yield function, hits, bool(times or clocks)


def problems(source, path, creators=None, reviewed=None, removers=None):
    creators = CREATORS if creators is None else creators
    reviewed = REVIEWED if reviewed is None else reviewed
    removers = REMOVERS if removers is None else removers
    path = canonical(path)
    errors, matched = [], set()
    for function, hits, age in inventory(source):
        key = (path, function)
        deleting = any(primitive.split(':')[0] in ('remove', 'history', 'delete') for _, primitive in hits)
        for line, primitive in hits:
            category = primitive.split(':')[0]
            if category in ('remove', 'history'):
                matched.add(key)
            allowed = (category == 'create' and key in creators
                       or category == 'remove' and primitive != 'remove:unscoped temporary'
                       and (key in removers or key in reviewed and (
                           not reviewed[key].startswith('Scoped TemporaryDirectory')
                           or primitive == 'remove:scoped temporary'))
                       or primitive == 'history:git ref delete'
                       and key == ('engine/.veldo/control_space_remove.py', 'remove_ref') and key in removers
                       or category == 'delete')
            if not allowed:
                errors.append(f'{path}:{line}: {function}: {primitive} outside its reviewed boundary')
        if deleting and age:
            errors.append(f'{path}: {function}: removal reads a file time or compares the clock')
    for key, reason in reviewed.items():
        if key[0] == path and (not reason or key not in matched):
            errors.append(f'{path}: {key[1]}: stale reviewed entry or missing reason')
    return errors


def sources(root):
    for directory in ('.veldo', 'engine/.veldo', 'scripts', 'engine/scripts'):
        yield from sorted((root / directory).glob('*.py'))
    for directory in ('scripts/runners', 'engine/scripts/runners'):
        yield from sorted((root / directory).rglob('*.py'))


def check(root):
    errors = []
    present = set()
    for path in sources(root):
        relative = str(path.relative_to(root))
        present.add(canonical(relative))
        try:
            errors.extend(problems(path.read_text(), relative))
        except (SyntaxError, ValueError) as error:
            errors.append(f'{relative}: unreadable syntax: {error}')
    errors.extend(f'{path}: {function}: stale reviewed entry, file absent'
                  for path, function in REVIEWED if path not in present)
    return errors


if __name__ == '__main__':
    errors = check(Path(__file__).resolve().parents[1])
    print('\n'.join(errors) if errors else 'Space boundary: pass')
    raise SystemExit(bool(errors))
