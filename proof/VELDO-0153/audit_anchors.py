"""Read mutation registration data with a restricted AST interpreter, without running a driver.

By default VELDO-0028, 0056, 0057 and 0153 registrations are collected. Production
anchors can be audited for all registrations; suite-copy anchors are checked for
those four findings. This checks anchors and syntax, not mutant kills. No suite or mutation driver is imported or invoked.
"""
import ast
from functools import lru_cache
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = None if sys.argv[2:] == ['all'] else (28, 56, 57, 153)


def factory_registrations(source):
    """Cross-check the trusted registry's data factory, never its driver or imports.

    Only literal globals and the cases definition are compiled. No suite, worker,
    driver entry point or other top-level executable statement is evaluated.
    """
    tree = ast.parse(source)
    namespace = {'ROOT': ROOT, 'json': json, '__builtins__': {
        'dict': dict, 'list': list, 'repr': repr, 'set': set, 'sorted': sorted, 'tuple': tuple}}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError):
                continue
            for target in node.targets:
                if isinstance(target, ast.Name):
                    namespace[target.id] = value
    factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'cases')
    exec(compile(ast.Module(body=[factory], type_ignores=[]), '<registry data factory>', 'exec'), namespace)
    return namespace['cases']()


def registrations(source, findings=FINDINGS, read_text=None):
    result, environment, helpers = [], {'ROOT': ROOT}, {}
    read_text = read_text or (lambda path: path.read_text())

    def evaluate(node, env):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -evaluate(node.operand, env)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.Not):
            return not evaluate(node.operand, env)
        if isinstance(node, ast.IfExp):
            return evaluate(node.body if evaluate(node.test, env) else node.orelse, env)
        if isinstance(node, ast.BoolOp):
            for item in node.values:
                value = evaluate(item, env)
                if bool(value) == isinstance(node.op, ast.Or):
                    return value
            return value
        if isinstance(node, ast.Compare) and len(node.ops) == 1:
            left, right = evaluate(node.left, env), evaluate(node.comparators[0], env)
            if isinstance(node.ops[0], ast.NotEq):
                return left != right
            if isinstance(node.ops[0], ast.Eq):
                return left == right
            if isinstance(node.ops[0], ast.In):
                return left in right
            if isinstance(node.ops[0], ast.NotIn):
                return left not in right
        if isinstance(node, ast.Dict):
            return {evaluate(key, env): evaluate(value, env) for key, value in zip(node.keys, node.values)}
        if isinstance(node, (ast.List, ast.Tuple)):
            items = []
            for item in node.elts:
                if isinstance(item, ast.Starred):
                    items.extend(evaluate(item.value, env))
                else:
                    items.append(evaluate(item, env))
            return tuple(items) if isinstance(node, ast.Tuple) else items
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left, env), evaluate(node.right, env)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Mod):
                return left % right
            if isinstance(node.op, ast.Div) and isinstance(left, Path):
                return left / right
        if isinstance(node, ast.Subscript):
            return evaluate(node.value, env)[evaluate(node.slice, env)]
        if isinstance(node, ast.Slice):
            return slice(*(evaluate(item, env) if item else None for item in (node.lower, node.upper, node.step)))
        if isinstance(node, (ast.ListComp, ast.GeneratorExp)) and len(node.generators) == 1:
            generator = node.generators[0]
            items = []
            for value in evaluate(generator.iter, env):
                local = dict(env)
                bind(generator.target, value, local)
                if all(evaluate(condition, local) for condition in generator.ifs):
                    items.append(evaluate(node.elt, local))
            return items
        if isinstance(node, ast.Call):
            args = [evaluate(arg, env) for arg in node.args]
            kwargs = {item.arg: evaluate(item.value, env) for item in node.keywords}
            if isinstance(node.func, ast.Attribute):
                if isinstance(node.func.value, ast.Name):
                    owner = node.func.value.id
                    if (owner, node.func.attr) == ('json', 'loads'):
                        return json.loads(*args, **kwargs)
                    if (owner, node.func.attr) == ('dict', 'fromkeys'):
                        return dict.fromkeys(*args, **kwargs)
                value = evaluate(node.func.value, env)
                if isinstance(value, Path) and node.func.attr == 'read_text':
                    path = value.resolve()
                    if not path.is_relative_to(ROOT):
                        raise ValueError('data path outside repository')
                    return read_text(path)
                allowed = ((str, ('replace', 'join', 'format', 'rstrip')),
                           (dict, ('get', 'items')), (set, ('update',)))
                if any(isinstance(value, kind) and node.func.attr in methods for kind, methods in allowed):
                    return getattr(value, node.func.attr)(*args, **kwargs)
                raise ValueError('unsupported method: ' + node.func.attr)
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name in ('list', 'tuple', 'str', 'range', 'enumerate', 'zip', 'dict', 'repr', 'set', 'sorted'):
                    return {'list': list, 'tuple': tuple, 'str': str, 'range': range,
                            'enumerate': enumerate, 'zip': zip, 'dict': dict, 'repr': repr,
                            'set': set, 'sorted': sorted}[name](*args, **kwargs)
                if name == 'add':
                    finding, case, suite, module, old, new, rows, *extra = args
                    result.append(dict(finding=finding, name=case, suite=suite, module=module,
                                       old=old, new=new, rows=rows,
                                       also=extra[0] if extra else kwargs.get('also', ())))
                    return None
                if name in helpers:
                    function = helpers[name]
                    local = dict(environment)
                    parameters = [arg.arg for arg in function.args.args]
                    for key, default in zip(parameters[-len(function.args.defaults):], function.args.defaults):
                        local[key] = evaluate(default, environment)
                    local.update(zip(parameters, args))
                    if function.args.vararg:
                        local[function.args.vararg.arg] = tuple(args[len(parameters):])
                    local.update(kwargs)
                    for statement in function.body:
                        if isinstance(statement, ast.Return):
                            return evaluate(statement.value, local)
                        visit(statement, local)
                    return None
        raise ValueError(type(node).__name__)

    def bind(target, value, env):
        if isinstance(target, ast.Name):
            env[target.id] = result if target.id == 'result' and value == [] else value
        elif isinstance(target, (ast.List, ast.Tuple)):
            for child, item in zip(target.elts, value):
                bind(child, item, env)
        elif isinstance(target, ast.Subscript):
            evaluate(target.value, env)[evaluate(target.slice, env)] = value
        else:
            raise ValueError('assignment target')

    def visit(node, env):
        if isinstance(node, ast.FunctionDef):
            if node.name != 'add':
                helpers[node.name] = node
        elif isinstance(node, ast.Assign):
            value = evaluate(node.value, env)
            for target in node.targets:
                bind(target, value, env)
        elif isinstance(node, ast.Expr):
            evaluate(node.value, env)
        elif isinstance(node, ast.For):
            for value in evaluate(node.iter, env):
                bind(node.target, value, env)
                for statement in node.body:
                    visit(statement, env)
        elif isinstance(node, ast.If):
            for statement in node.body if evaluate(node.test, env) else node.orelse:
                visit(statement, env)
        elif isinstance(node, ast.Return) and isinstance(node.value, ast.Name) and node.value.id == 'result':
            pass
        else:
            raise ValueError('unsupported statement: ' + type(node).__name__)

    tree = ast.parse(source)
    for node in tree.body:
        if isinstance(node, ast.Assign):
            try:
                visit(node, environment)
            except (KeyError, ValueError, TypeError, IndexError):
                pass
    factory = next(node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == 'cases')
    unresolved = []
    for statement in factory.body:
        try:
            visit(statement, environment)
        except (KeyError, ValueError, TypeError, IndexError) as error:
            text = ast.unparse(statement)
            unresolved.append(dict(line=statement.lineno, expression=text[:140], error=str(error)))
    return [case for case in result if findings is None or case['finding'] in findings], unresolved


@lru_cache(maxsize=None)
def git_text(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT, text=True,
                                   stderr=subprocess.DEVNULL)


def audit(commit=None):
    source = git_text(commit, 'scripts/check_teeth_mutations.py') if commit else (ROOT / 'scripts/check_teeth_mutations.py').read_text()
    reader = (lambda path: git_text(commit, str(path.relative_to(ROOT)))) if commit else None
    cases, unresolved = registrations(source, read_text=reader)
    factory_count = None
    if commit is None:
        actual = factory_registrations(source)
        factory_count = len(actual)
        expected = [dict(case, also=case.get('also', ())) for case in actual
                    if FINDINGS is None or case['finding'] in FINDINGS]
        # Normalize list/tuple representations; compare every field, not just counts.
        if json.dumps(cases, sort_keys=True) != json.dumps(expected, sort_keys=True):
            unresolved.append(dict(error='AST registrations differ from isolated cases() data factory'))
    missing = []
    suite_missing = []
    for case in cases:
        if case['finding'] in (28, 56, 57, 153) and not case.get('fixture'):
            suite_path = 'scripts/suites/' + case['suite']
            suite = git_text(commit, suite_path) if commit else (ROOT / suite_path).read_text()
            anchor = 'ROOT / "' + case.get('dir', '.veldo') + '" / "' + case['module'] + '"'
            if anchor not in suite:
                suite_missing.append(dict(name=case['name'], suite=case['suite'], anchor=anchor))
        path = case.get('dir', 'scripts/fixtures' if case.get('fixture') else '.veldo') + '/' + case['module']
        try:
            text = git_text(commit, path) if commit else (ROOT / path).read_text()
        except (subprocess.CalledProcessError, OSError) as error:
            unresolved.append(dict(case=case['name'], path=path, error=type(error).__name__))
            continue
        for old, new in [(case['old'], case['new']), *case['also']]:
            if not isinstance(old, str) or not isinstance(new, str):
                unresolved.append(dict(case=case['name'], error='non-literal replacement'))
                break
            count = text.count(old)
            if count != 1:
                missing.append(dict(name=case['name'], finding=case['finding'], module=case['module'],
                                    count=count, anchor=old))
                break
            text = text.replace(old, new)
        else:
            if case['module'].endswith('.py'):
                try:
                    compile(text, path, 'exec')
                except SyntaxError as error:
                    unresolved.append(dict(case=case['name'], error='mutant syntax: ' + str(error)))
    return dict(cases=len(cases), factory_cases=factory_count, unresolved=unresolved, missing=missing,
                suite_anchor_findings=[28, 56, 57, 153], suite_missing=suite_missing)


if __name__ == '__main__':
    result = {'prior_review_49ed8bfd': audit('49ed8bfd'), 'base_9763249e': audit('9763249e'),
              'seed_bb1538f2': audit('bb1538f2'), 'current': audit()}
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n')
    for name, record in result.items():
        print('%s: %d registrations, %d unresolved, %d missing anchors' % (
            name, record['cases'], len(record['unresolved']), len(record['missing'])))
        for case in record['missing']:
            print('  ' + case['name'])
        print('  %d missing scoped suite-copy anchors' % len(record['suite_missing']))
    current = result['current']
    raise SystemExit(bool(current['missing'] or current['unresolved'] or current['suite_missing']))
