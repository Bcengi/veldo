#!/usr/bin/env python3
"""VELDO-0304: creation, removal and age boundaries, checked by function."""
import ast
from pathlib import Path
import re
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
    ('engine/scripts/gate_schedule.py', 'Meter.finish'): 'Ends its own empty kernel cgroup directories; rmdir cannot remove ordinary files.',
    ('engine/scripts/mutation_ownership.py', 'WorkerMeter.close'): 'Ends its own empty kernel cgroup directories after worker exit; rmdir cannot remove ordinary files.',
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
    ('engine/.veldo/control_space_remove.py', 'remove_standalone'): 'Fresh standalone look and keep, then non-forced removal.',
    ('engine/.veldo/control_space_remove.py', 'remove_ref'): 'Ended ledger item, verified keep and compare-and-delete.',
    ('engine/.veldo/control_space_remove.py', '_worktree_remove'): 'The existing non-forced worktree remover.',
    ('engine/.veldo/control_space_remove.py', '<module>'): 'The existing measured engine remover table.',
}
CREATORS[('engine/scripts/verify.sh', '<module>')] = 'The gate creates its own schedule folder.'
REVIEWED[('engine/scripts/verify.sh', '<EXIT trap>')] = 'The gate removes its own schedule folder at exit; design 6.10.'
REVIEWED[('engine/.veldo/control_graph_install.py', 'install')] = 'The install owns its freshly built staging and temporary folders; design 6.10.'


def canonical(path):
    path = str(path)
    if path.startswith('.veldo/'):
        return 'engine/' + path
    paired = {key[0] for table in (CREATORS, REVIEWED, REMOVERS) for key in table}
    if path.startswith('scripts/') and 'engine/' + path in paired:
        return 'engine/' + path
    return path


def name(node):
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return name(node.value) + '.' + node.attr
    if isinstance(node, ast.Call):
        return name(node.func)
    return ''


def resolved_name(node, values, seen=()):
    if isinstance(node, ast.Name) and node.id in values and node.id not in seen:
        value = values[node.id]
        if isinstance(value, (ast.Name, ast.Attribute, ast.Call)):
            return resolved_name(value, values, (*seen, node.id))
    if (isinstance(node, ast.Call) and name(node.func) == 'getattr' and len(node.args) == 2
            and isinstance(node.args[1], ast.Constant) and isinstance(node.args[1].value, str)):
        return resolved_name(node.args[0], values, seen) + '.' + node.args[1].value
    if isinstance(node, ast.Attribute):
        return resolved_name(node.value, values, seen) + '.' + node.attr
    return name(node)


def sequence(node, values, seen=()):
    if isinstance(node, ast.Name) and node.id in values and node.id not in seen:
        return sequence(values[node.id], values, (*seen, node.id))
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        return sequence(node.left, values, seen) or sequence(node.right, values, seen)
    return isinstance(node, (ast.List, ast.Tuple))


def words(node, values, seen=()):
    if isinstance(node, ast.Constant) and isinstance(node.value, (str, bytes)):
        return [node.value.decode('ascii', errors='replace') if isinstance(node.value, bytes) else node.value]
    if isinstance(node, ast.JoinedStr):
        return [''.join(word for value in node.values for word in words(value, values, seen))]
    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'encode':
        return words(node.func.value, values, seen)
    if isinstance(node, ast.Name) and node.id in values and node.id not in seen:
        return words(values[node.id], values, (*seen, node.id))
    if isinstance(node, ast.Name):
        return ['<dynamic>']
    if isinstance(node, (ast.List, ast.Tuple)):
        return [word for value in node.elts for word in words(value, values, seen)]
    if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
        parts = words(node.left, values, seen) + words(node.right, values, seen)
        return parts if sequence(node, values, seen) else [''.join(parts)]
    return []


def primitives(node, values):
    """Classify executed calls, not examples in strings or comments."""
    if not isinstance(node, ast.Call):
        return set()
    called = resolved_name(node.func, values)
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
    if (tail in ('remove_tree', '_remove_tree', '_rmtree', 'space_signal', 'remove_ref', 'remove_path', 'remove_standalone')
            or tail == 'remove' and any(part in called.lower() for part in ('remover', 'space_remove', 'rm.'))):
        result.add('delete:remover call')
    vector = [word for arg in node.args for word in words(arg, values)]
    if tail in ('run', 'call', 'check_call', 'check_output', 'Popen', 'system', 'popen'):
        vector = [token for word in vector for token in (
            shlex.split(word) if re.match(r'^(?:git|rm|docker|mktemp)\s', word) else [word])]
    git = 'git' in called.lower() or 'git' in vector
    if git:
        if ('worktree' in vector or 'worktree' in called) and 'add' in vector:
            result.add('create:git worktree add')
        if ('worktree' in vector or 'worktree' in called) and 'remove' in vector:
            result.add('remove:git worktree remove')
        feed = [word for keyword in node.keywords if keyword.arg in ('input', 'feed', 'stdin')
                for word in words(keyword.value, values)]
        if 'update-ref' in vector and '--stdin' in vector:
            # Unknown input can contain a delete too; no caller may hide the operation in a pipe.
            if not feed or '<dynamic>' in feed or any(re.search(r'(?:^|[\n\0])delete[ \0]', word) for word in feed):
                result.add('history:git ref delete')
        transfer = any(command in vector for command in ('fetch', 'push', 'send-pack'))
        forced_refspec = transfer and any(word.startswith('+') and ':refs/' in word for word in vector)
        forced_fetch = ('fetch' in vector and any(flag in vector for flag in ('--force', '-f'))
                        and any(':refs/' in word for word in vector))
        if forced_refspec or forced_fetch:
            result.add('history:forced ref overwrite')
        if 'update-ref' in vector and any('refs/veldo/kept/' in word for word in vector):
            operands = [word for word in vector[vector.index('update-ref') + 1:] if not word.startswith('-')]
            kept_at = next((i for i, word in enumerate(operands) if word.startswith('refs/veldo/kept/')), None)
            if kept_at is not None and len(operands[kept_at:]) < 3:
                result.add('history:unchecked kept ref overwrite')
        if 'update-ref' in vector and any(x in vector for x in ('-d', '--delete')):
            result.add('history:git ref delete')
        if any(x in vector for x in ('branch', 'tag', 'symbolic-ref')) and any(
                x in vector for x in ('-d', '-D', '--delete')):
            result.add('history:git ref delete')
        if ('stash' in vector and any(x in vector for x in ('drop', 'clear'))
                or 'reflog' in vector and 'expire' in vector or 'prune' in vector
                or 'gc' in vector):
            result.add('history:git object removal')
    if 'rm' in vector and any(x.startswith('-') and ('r' in x or x == '--recursive') for x in vector):
        result.add('remove:shell recursive remove')
    docker = 'docker' in called or 'docker' in vector or tail in ('_engine', 'client')
    sdk = any(part in called.split('.') for part in ('containers', 'volumes', 'networks', 'images'))
    if sdk and tail in ('remove', 'prune'):
        result.add('remove:engine remove')
    if sdk and tail in ('create', 'run', 'build'):
        result.add('create:engine object')
    if docker:
        if any(x in vector for x in ('rm', 'rmi', 'prune')):
            result.add('remove:engine remove')
        if any(x in vector for x in ('create', 'run', 'build')):
            result.add('create:engine object')
    return result


def functions(source):
    tree = ast.parse(source)
    found = []
    globals_ = {target.id: node.value for node in tree.body if isinstance(node, ast.Assign)
                for target in node.targets if isinstance(target, ast.Name)}

    def bindings(nodes):
        values = dict(globals_)
        for part in [*tree.body, *nodes]:
            if isinstance(part, ast.Assign):
                values.update({target.id: part.value for target in part.targets if isinstance(target, ast.Name)})
            if isinstance(part, ast.Import):
                values.update({alias.asname or alias.name: ast.Name(id=alias.name) for alias in part.names})
            if isinstance(part, ast.ImportFrom):
                values.update({alias.asname or alias.name: ast.Attribute(value=ast.Name(id=part.module or ''),
                                                                        attr=alias.name) for alias in part.names})
        return values

    def visit(node, scope):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            scope = (*scope, node.name)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Module)):
            nodes = []

            def local(part):
                nodes.append(part)
                for child in ast.iter_child_nodes(part):
                    if not isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                        local(child)
            local(node)
            values = bindings(nodes)
            found.append(('.'.join(scope) or '<module>', nodes, values))
        for child in ast.iter_child_nodes(node):
            visit(child, scope)
    visit(tree, ())
    return found


def inventory(source):
    for function, nodes, values in functions(source):
        hits = [(node.lineno, primitive) for node in nodes for primitive in primitives(node, values)]
        for loop in nodes:
            if isinstance(loop, (ast.For, ast.AsyncFor, ast.comprehension)):
                traverses = any(isinstance(call, ast.Call) and resolved_name(call.func, values).rsplit('.', 1)[-1]
                                in ('walk', 'rglob', 'iterdir') for call in ast.walk(loop.iter))
                if traverses and any('delete:single path' in primitives(call, values) for call in ast.walk(loop)):
                    hits.append((getattr(loop, 'lineno', 1), 'remove:recursive folder'))
        times = [node for node in nodes if isinstance(node, ast.Attribute)
                 and node.attr in ('st_mtime', 'st_ctime', 'st_atime', 'st_mtime_ns', 'st_ctime_ns', 'st_atime_ns')]
        times += [node for node in nodes if isinstance(node, ast.Call)
                  and resolved_name(node.func, values).rsplit('.', 1)[-1] in ('getmtime', 'getctime', 'getatime')]
        def clock_value(node, seen=()):
            if isinstance(node, ast.Name):
                return (node.id in values and node.id not in seen
                        and clock_value(values[node.id], (*seen, node.id)))
            if isinstance(node, ast.Call):
                return resolved_name(node.func, values).rsplit('.', 1)[-1] in (
                    'time', 'monotonic', 'now', 'utcnow', 'clock')
            if isinstance(node, (ast.Compare, ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.IfExp)):
                return any(clock_value(child, seen) for child in ast.iter_child_nodes(node))
            return False
        clocks = [node for node in nodes if isinstance(node, ast.Compare) and clock_value(node)]
        yield function, hits, bool(times or clocks)


def shell_inventory(source):
    """Shell command segments and traps. Quoted prose is not executed as a command."""
    function = '<module>'
    grouped = {}
    continued = ''
    for number, line in enumerate(source.splitlines(), 1):
        line = continued + line
        if line.endswith('\\'):
            continued = line[:-1] + ' '
            continue
        continued = ''
        match = re.match(r'\s*(?:function\s+)?([\w]+)\s*\(\s*\)\s*\{', line)
        if match:
            function = match.group(1)
        if line.strip() == '}':
            function = '<module>'
        try:
            lexer = shlex.shlex(line, posix=True, punctuation_chars=';|&()')
            lexer.whitespace_split = True
            tokens = list(lexer)
        except ValueError:
            continue  # a multiline shell quote, not an executable command on this line
        segments, segment = [], []
        for token in [*tokens, ';']:
            if token in (';', '&&', '||', '|', '(', ')'):
                if segment:
                    segments.append(segment)
                segment = []
            else:
                segment.append(token)
        for vector in segments:
            while vector and (vector[0] in ('if', 'then', 'do', '!', 'exec', 'command') or '=' in vector[0]):
                vector = vector[1:]
            if not vector:
                continue
            if vector[0] == 'trap' and len(vector) >= 3:
                for _, hits, age in shell_inventory(vector[1]):
                    grouped.setdefault('<' + vector[-1] + ' trap>', [[], False])[0].extend(
                        (number, primitive) for _, primitive in hits)
                continue
            hits = set()
            if vector[0] == 'mktemp' and '-d' in vector:
                hits.add('create:temporary folder')
            if vector[0] == 'rm':
                hits.add('remove:shell recursive remove' if any(
                    flag.startswith('-') and ('r' in flag or flag == '--recursive') for flag in vector[1:])
                         else 'delete:single path')
            if vector[0] in {'git', 'docker'}:
                call = ast.Call(func=ast.Name(id=vector[0]), args=[ast.Constant(value=word) for word in vector[1:]],
                                keywords=[])
                hits |= primitives(call, {})
            group = grouped.setdefault(function, [[], False])
            group[0].extend((number, primitive) for primitive in sorted(hits))
            group[1] |= bool(re.search(r'\b(?:mtime|mmin|ctime|cmin|atime|amin)\b|%[YZX]', line))
    for function, (hits, age) in grouped.items():
        yield function, hits, age


def problems(source, path, creators=None, reviewed=None, removers=None):
    creators = CREATORS if creators is None else creators
    reviewed = REVIEWED if reviewed is None else reviewed
    removers = REMOVERS if removers is None else removers
    path = canonical(path)
    errors, matched = [], set()
    for function, hits, age in (shell_inventory(source) if path.endswith('.sh') else inventory(source)):
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
        yield from sorted((root / directory).glob('*.sh'))
    for directory in ('scripts/runners', 'engine/scripts/runners'):
        yield from sorted((root / directory).rglob('*.py'))


def check(root, read=None):
    errors = []
    present = set()
    for path in sources(root):
        relative = str(path.relative_to(root))
        present.add(canonical(relative))
        try:
            errors.extend(problems(read(path) if read else path.read_text(), relative))
        except (SyntaxError, ValueError) as error:
            errors.append(f'{relative}: unreadable syntax: {error}')
    errors.extend(f'{path}: {function}: stale reviewed entry, file absent'
                  for path, function in REVIEWED if path not in present)
    return errors


if __name__ == '__main__':
    errors = check(Path(__file__).resolve().parents[1])
    print('\n'.join(errors) if errors else 'Space boundary: pass')
    raise SystemExit(bool(errors))
