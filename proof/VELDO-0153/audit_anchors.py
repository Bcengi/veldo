"""Read mutation registration data with a restricted AST interpreter, without running a driver.

Only the VELDO-0028, 0056 and 0057 registrations are collected. This checks anchor
uniqueness, not mutant kills. No suite or mutation driver is imported or invoked.
"""
import ast
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
FINDINGS = None if sys.argv[2:] == ['all'] else (28, 56, 57)


def registrations(source):
    result, environment, helpers = [], {}, {}

    def evaluate(node, env):
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return env[node.id]
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
            return -evaluate(node.operand, env)
        if isinstance(node, ast.BoolOp):
            values = [evaluate(value, env) for value in node.values]
            return any(values) if isinstance(node.op, ast.Or) else all(values)
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
            items = [evaluate(item, env) for item in node.elts]
            return tuple(items) if isinstance(node, ast.Tuple) else items
        if isinstance(node, ast.BinOp):
            left, right = evaluate(node.left, env), evaluate(node.right, env)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Mod):
                return left % right
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
            if isinstance(node.func, ast.Attribute) and node.func.attr in ('replace', 'join', 'format'):
                value = evaluate(node.func.value, env)
                if not isinstance(value, str):
                    raise ValueError('non-string method')
                return getattr(value, node.func.attr)(*args, **kwargs)
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name in ('list', 'tuple', 'str', 'range', 'enumerate', 'zip', 'dict'):
                    return {'list': list, 'tuple': tuple, 'str': str, 'range': range,
                            'enumerate': enumerate, 'zip': zip, 'dict': dict}[name](*args, **kwargs)
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
            if text.startswith(('publication(', 'candidate(', 'landing(', 'effects(', 'add(28,', 'add(56,', 'add(57,')):
                unresolved.append(dict(line=statement.lineno, expression=text[:140], error=str(error)))
    return [case for case in result if FINDINGS is None or case['finding'] in FINDINGS], unresolved


def git_text(commit, path):
    return subprocess.check_output(['git', 'show', commit + ':' + path], cwd=ROOT, text=True,
                                   stderr=subprocess.DEVNULL)


def audit(commit=None):
    source = git_text(commit, 'scripts/check_teeth_mutations.py') if commit else (ROOT / 'scripts/check_teeth_mutations.py').read_text()
    cases, unresolved = registrations(source)
    missing = []
    for case in cases:
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
    return dict(cases=len(cases), unresolved=unresolved, missing=missing)


if __name__ == '__main__':
    result = {'prior_review_49ed8bfd': audit('49ed8bfd'), 'base_9763249e': audit('9763249e'),
              'seed_bb1538f2': audit('bb1538f2'), 'current': audit()}
    Path(sys.argv[1]).write_text(json.dumps(result, indent=2) + '\n')
    for name, record in result.items():
        print('%s: %d registrations, %d unresolved, %d missing anchors' % (
            name, record['cases'], len(record['unresolved']), len(record['missing'])))
        for case in record['missing']:
            print('  ' + case['name'])
