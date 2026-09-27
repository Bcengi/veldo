"""VELDO-0169: the census of every engine writer of a claim or a station contract, read from the syntax tree.

What it finds, in every module it is given (the engine's .veldo sources):

- every reference to a callable named `transition`: an attribute of that name on any receiver
  expression, getattr(obj, 'transition'), a name bound to one of those, and in control_claim the
  claim organ's own function. A reference that is called with arguments that can bind the organ's
  signature (read from control_claim's own tree) is a claim writer; one that cannot bind it (the
  entity contract's four-argument transition, a transaction transition's three) is not the organ;
  one that escapes (stored, passed, returned or registered bare) is refused, since what calls it is
  not visible here.
- every reference to the station contract's one writer, `issue_station_contract`, and every entity
  mapping written with the kind that writer writes, which is refused outside it.
- every getattr, attrgetter or methodcaller whose attribute name is not resolved to a set of
  constants: it could name either, so it is refused.
- every receipt made outside the Gate's project check (control_claim.project_check_receipt called
  anywhere but control_eligibility's Gate.project_problems, or its schema used elsewhere).

How it classifies a writer: by the function that encloses it and by the claim action it can carry.
The action is followed to where the parameters are built: a literal at the call; the assignment of
the same key (params['resume'] = dict(action='resume', ...)); or, for a registered transition, the
commit of its operation and the parameters that commit carries. The action set is narrowed by the
guards on the path (`if params['action'] in HANDOUTS`, an early return, a refusal of every
operation outside a constant). A writer whose action is not resolved hands out work. A writer that
hands out work (an action in control_claim.HANDOUTS, or any station contract) must obtain the
receipt before the write on every path through its function: a call of the Gate's project_problems,
directly or through a helper of the same class or module that makes it unconditionally, in a
statement that precedes the write in its block or an enclosing one (not inside a branch beside it).
Every place that builds the parameters of such a writer must do the same, so the project and owner
versions the check read are the ones the transaction pins. Nothing is classified from a list of
writers or of receiver names.
"""
import ast

ORGAN_MODULE = 'control_claim'
ORGAN = 'transition'
CONSTRUCTOR = 'issue_station_contract'
CHECK = 'project_problems'
RECEIPT = 'project_check_receipt'
RECEIPT_SCHEMA = 'PROJECT_CHECK_SCHEMA'
RECEIPT_MAKER = ('control_eligibility', 'Gate.project_problems')
DYNAMIC = ('getattr', 'attrgetter', 'methodcaller')
NOVALUE = object()
DEPTH = 6


class All:
    """Every action but `excluded`: what an unresolved action can be."""
    def __init__(self, excluded=frozenset()):
        self.excluded = frozenset(excluded)

    def __repr__(self):
        return 'any' + ('-' + ','.join(sorted(self.excluded)) if self.excluded else '')


def union(a, b):
    if isinstance(a, All) or isinstance(b, All):
        excluded = [s.excluded if isinstance(s, All) else None for s in (a, b)]
        values = set().union(*(s for s in (a, b) if not isinstance(s, All)))
        kept = frozenset.intersection(*[e for e in excluded if e is not None])
        return All(kept - values)
    return frozenset(a) | frozenset(b)


def restrict(values, allowed=None, excluded=()):
    if allowed is not None:
        allowed = frozenset(allowed)
        values = allowed - values.excluded if isinstance(values, All) else values & allowed
    if isinstance(values, All):
        return All(values.excluded | frozenset(excluded))
    return frozenset(values) - frozenset(excluded)


def hands_out(values, handouts):
    if isinstance(values, All):
        return not frozenset(handouts) <= values.excluded
    return bool(frozenset(values) & frozenset(handouts))


def shown(values):
    return repr(values) if isinstance(values, All) else sorted(values)


class Module:
    def __init__(self, stem, source):
        self.stem = stem
        self.source = source
        self.tree = ast.parse(source)
        self.nodes = list(ast.walk(self.tree))
        self.parents = {}
        for node in self.nodes:
            for child in ast.iter_child_nodes(node):
                self.parents[child] = node
        self.functions = {}
        for node in self.nodes:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions[self.qualname(node)] = node
        self.defined = {n.name for n in self.tree.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))}
        self.constants = {}
        for node in self.tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    self._bind(target, node.value)

    def _bind(self, target, value):
        if isinstance(target, ast.Name):
            resolved = self.const(value)
            if resolved is not NOVALUE:
                self.constants[target.id] = resolved
        elif isinstance(target, (ast.Tuple, ast.List)) and isinstance(value, (ast.Tuple, ast.List)) \
                and len(target.elts) == len(value.elts):
            for t, v in zip(target.elts, value.elts):
                self._bind(t, v)

    def const(self, node, scope=None):
        """The constant value of `node` (strings, numbers, None, tuples of them), or NOVALUE."""
        if isinstance(node, ast.Constant):
            return node.value
        if isinstance(node, ast.Name):
            return self.constants.get(node.id, NOVALUE)
        if isinstance(node, (ast.Tuple, ast.List, ast.Set)):
            values = tuple(self.const(e) for e in node.elts)
            return NOVALUE if any(v is NOVALUE for v in values) else values
        if isinstance(node, ast.Attribute) and node.attr == '__slots__' and scope is not None:
            cls = self.cls_of(scope)
            for stmt in (cls.body if cls is not None else ()):
                if isinstance(stmt, ast.Assign) and any(isinstance(t, ast.Name) and t.id == '__slots__' for t in stmt.targets):
                    return self.const(stmt.value)
        return NOVALUE

    def qualname(self, node):
        names = [node.name] if hasattr(node, 'name') else ['<lambda>']
        while node in self.parents:
            node = self.parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(node.name)
            elif isinstance(node, ast.Lambda):
                names.append('<lambda>')
        return '.'.join(reversed(names))

    def enclosing(self, node):
        while node in self.parents:
            node = self.parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return node
        return None

    def cls_of(self, fn):
        parent = self.parents.get(fn)
        while parent is not None and not isinstance(parent, ast.ClassDef):
            if isinstance(parent, (ast.FunctionDef, ast.AsyncFunctionDef)):
                return None
            parent = self.parents.get(parent)
        return parent

    def name_of(self, fn):
        return self.qualname(fn) if fn is not None else '<module>'

    def statement(self, node):
        while not isinstance(node, ast.stmt):
            node = self.parents[node]
        return node


_PARSED, _SCANNED = {}, {}


def parsed(stem, text):
    """One parse per module source: a census reads its modules and never changes them."""
    key = (stem, text)
    if key not in _PARSED:
        _PARSED[key] = Module(stem, text)
    return _PARSED[key]


def params_of(fn):
    return [a.arg for a in fn.args.posonlyargs + fn.args.args]


def method_params(module, fn):
    """Positional parameter names after self for a method, all of them for a function."""
    names = params_of(fn)
    if module.cls_of(fn) is not None and names and names[0] in ('self', 'cls'):
        names = names[1:]
    return names


def callee(node):
    """The attribute or plain name a call is made through, and getattr's literal name."""
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return None


class Census:
    def __init__(self, sources):
        self.modules = {stem: parsed(stem, text) for stem, text in sorted(sources.items())}
        self.failures, self.records = [], []
        organ = self.modules.get(ORGAN_MODULE)
        fn = next((n for n in (organ.tree.body if organ else ()) if isinstance(n, ast.FunctionDef) and n.name == ORGAN), None)
        if fn is None or fn.args.vararg or fn.args.kwarg or fn.args.defaults or fn.args.kwonlyargs:
            self.fail(ORGAN_MODULE, None, 0, 'the claim organ %s(params, before) is not found as a plain function' % ORGAN)
            self.signature, self.handouts = ('params', 'before'), ()
        else:
            self.signature = tuple(params_of(fn))
            self.handouts = organ.constants.get('HANDOUTS', NOVALUE)
            if not isinstance(self.handouts, tuple) or not self.handouts:
                self.fail(ORGAN_MODULE, None, 0, 'control_claim.HANDOUTS does not name the transitions that hand out work')
                self.handouts = ()
        self.schema = organ.constants.get(RECEIPT_SCHEMA, NOVALUE) if organ else NOVALUE

    # -- reporting ------------------------------------------------------------------------------

    def fail(self, stem, fn, line, why):
        failure = '%s.%s:%s %s' % (stem, fn or '<module>', line, why)
        if failure not in self.failures:
            self.failures.append(failure)

    # -- discovery ------------------------------------------------------------------------------

    def run(self):
        kinds = self.constructor_kinds()
        for module in self.modules.values():
            # What a module contributes depends only on its own source and on what the organ and the
            # station contract writer declare, so an unchanged module is not read twice.
            key = (module.stem, module.source, self.signature, self.handouts, self.schema, frozenset(kinds))
            if key not in _SCANNED:
                records, failures = self.records, self.failures
                self.records, self.failures = [], []
                self.scan(module, kinds)
                _SCANNED[key] = (self.records, self.failures)
                self.records, self.failures = records, failures
            self.records += _SCANNED[key][0]
            for failure in _SCANNED[key][1]:
                if failure not in self.failures:
                    self.failures.append(failure)
        return self

    def scan(self, module, kinds):
        self.dynamic(module)
        self.receipts(module)
        for name, kind in ((ORGAN, 'claim'), (CONSTRUCTOR, 'station')):
            for ref in self.references(module, name):
                for site in self.calls(module, ref, name):
                    if kind == 'claim':
                        self.claim_site(module, site)
                    else:
                        self.station_site(module, site)
        self.station_bypass(module, kinds)

    def references(self, module, name):
        """Every expression that can evaluate to a callable called `name` in this module."""
        imported = set()
        for node in module.nodes:
            if isinstance(node, ast.ImportFrom):
                imported.update(a.asname or a.name for a in node.names if a.name == name)
        for node in module.nodes:
            if isinstance(node, ast.Attribute) and node.attr == name:
                yield node
            elif (isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'getattr'
                  and len(node.args) >= 2 and isinstance(node.args[1], ast.Constant) and node.args[1].value == name):
                yield node
            elif isinstance(node, ast.Name) and isinstance(node.ctx, ast.Load) and (
                    node.id in imported or (node.id == name and name in module.defined and self.unshadowed(module, node))):
                yield node

    def unshadowed(self, module, node):
        fn = module.enclosing(node)
        while fn is not None:
            if node.id in params_of(fn) or any(isinstance(t, ast.Name) and t.id == node.id
                                               for n in ast.walk(fn) if isinstance(n, ast.Assign) for t in n.targets):
                return False
            fn = module.enclosing(fn)
        return True

    def calls(self, module, ref, name):
        """The calls made through `ref`: directly, or through a name it is bound to in the same scope.
        Anything else it is used for is refused: its caller is not visible here."""
        parent = module.parents.get(ref)
        fn = module.enclosing(ref)
        where = module.name_of(fn)
        if isinstance(ref, ast.Attribute) and not isinstance(ref.ctx, ast.Load):
            self.fail(module.stem, where, ref.lineno, 'rebinds an attribute named %s' % name)
            return []
        if isinstance(parent, ast.Call) and parent.func is ref:
            return [parent]
        if isinstance(parent, ast.Dict) and ref in parent.values:
            key = parent.keys[parent.values.index(ref)]
            if isinstance(key, ast.Constant) and key.value == 'transaction_transition' and len(self.signature) != 3:
                # The store calls a transaction transition with (conn, parameters, before): the organ
                # cannot bind three arguments, so this is some other registered transition.
                self.records.append(dict(module=module.stem, function=where, line=ref.lineno, writer='registered',
                                         classification='not the claim organ',
                                         reason='a transaction transition is called with three arguments'))
                return []
            self.fail(module.stem, where, ref.lineno, 'registers %s bare: the store calls it with no receipt read in the transaction' % name)
            return []
        if isinstance(parent, ast.Assign) and parent.value is ref and len(parent.targets) == 1 \
                and isinstance(parent.targets[0], ast.Name):
            alias = parent.targets[0].id
            scope = fn if fn is not None else module.tree
            found = []
            for node in ast.walk(scope):
                if isinstance(node, ast.Name) and node.id == alias and isinstance(node.ctx, ast.Load):
                    use = module.parents.get(node)
                    if isinstance(use, ast.Call) and use.func is node:
                        found.append(use)
                    else:
                        self.fail(module.stem, where, node.lineno, 'the alias %s of %s escapes' % (alias, name))
            return found
        self.fail(module.stem, where, ref.lineno, 'a reference to %s escapes: what calls it is not visible' % name)
        return []

    # -- the claim organ ------------------------------------------------------------------------

    def binds(self, call):
        """Whether `call` can bind the organ's positional signature."""
        if any(isinstance(a, ast.Starred) for a in call.args) or any(k.arg is None for k in call.keywords):
            return None
        names = list(self.signature)
        if len(call.args) > len(names):
            return False
        rest = names[len(call.args):]
        given = [k.arg for k in call.keywords]
        return sorted(given) == sorted(rest)

    def argument(self, call, position, name):
        if len(call.args) > position:
            return call.args[position]
        for k in call.keywords:
            if k.arg == name:
                return k.value
        return None

    def claim_site(self, module, call):
        fn = module.enclosing(call)
        where = module.name_of(fn)
        bound = self.binds(call)
        if bound is None:
            self.fail(module.stem, where, call.lineno, 'calls %s with unpacked arguments that cannot be resolved' % ORGAN)
            return
        if not bound:
            self.records.append(dict(module=module.stem, function=where, line=call.lineno, writer=ORGAN,
                                     classification='not the claim organ',
                                     reason='%d arguments cannot bind %s(%s)' % (len(call.args) + len(call.keywords),
                                                                                  ORGAN, ', '.join(self.signature))))
            return
        params = self.argument(call, 0, self.signature[0])
        constructions, unresolved = self.constructions(module, fn, params, 0)
        values = All() if unresolved else frozenset()
        for c in constructions:
            values = union(values, c['actions'])
        values = self.narrow(module, fn, call, self.action_expressions(module, fn, params), values)
        handout = hands_out(values, self.handouts)
        record = dict(module=module.stem, function=where, line=call.lineno, writer=ORGAN, actions=shown(values),
                      classification='handout' if handout else 'nothing',
                      built_at=['%s.%s:%s' % (module.stem, module.name_of(c['function']), c['node'].lineno)
                                for c in constructions],
                      reason=('its action can be ' + ', '.join(sorted(set(self.handouts) & set(values)))
                              if handout and not isinstance(values, All) else
                              'its action is not resolved, so it hands out work' if handout else
                              'it can only ' + ', '.join(sorted(values)) + ' a claim already held or parked'))
        self.records.append(record)
        if handout:
            self.require(module, fn, call, 'the claim write')
            for c in constructions:
                if c['node'] is not call and not self.within(module, c['node'], call) and hands_out(c['actions'], self.handouts):
                    self.require(c['module'], c['function'], c['node'], 'the handout parameters it writes')

    def within(self, module, node, call):
        while node in module.parents:
            if node is call:
                return True
            node = module.parents[node]
        return False

    def action_expressions(self, module, fn, params):
        """The expressions that stand for the claim action of `params` inside `fn`."""
        base = params
        if isinstance(base, ast.Call) and isinstance(base.func, ast.Name) and base.func.id == 'dict' and base.args:
            base = base.args[0]
        if not isinstance(base, ast.Name):
            return []
        forms = [ast.dump(ast.Subscript(value=ast.Name(id=base.id, ctx=ast.Load()), slice=ast.Constant(value='action'), ctx=ast.Load())),
                 ast.dump(ast.Call(func=ast.Attribute(value=ast.Name(id=base.id, ctx=ast.Load()), attr='get', ctx=ast.Load()),
                                   args=[ast.Constant(value='action')], keywords=[]))]
        if fn is not None:
            for node in ast.walk(fn):
                if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name) \
                        and self.strip(node.value) in forms:
                    forms.append(ast.dump(ast.Name(id=node.targets[0].id, ctx=ast.Load())))
        return forms

    @staticmethod
    def strip(node):
        return ast.dump(node, annotate_fields=True, include_attributes=False)

    def constructions(self, module, fn, expr, depth):
        """([{module, function, node, actions}], unresolved): where the parameters `expr` stands for are
        built, with the claim actions each can carry."""
        if depth > DEPTH or expr is None:
            return [], True
        if isinstance(expr, ast.Call) and isinstance(expr.func, ast.Name) and expr.func.id == 'dict':
            overridden = next((k.value for k in expr.keywords if k.arg == 'action'), None)
            if overridden is not None:
                return [dict(module=module, function=fn, node=expr, actions=self.values(module, fn, expr, overridden))], False
            if not expr.args:
                return [dict(module=module, function=fn, node=expr, actions=All())], False
            return self.constructions(module, fn, expr.args[0], depth + 1)
        if isinstance(expr, ast.Dict):
            for k, v in zip(expr.keys, expr.values):
                if isinstance(k, ast.Constant) and k.value == 'action':
                    return [dict(module=module, function=fn, node=expr, actions=self.values(module, fn, expr, v))], False
            return [dict(module=module, function=fn, node=expr, actions=All())], False
        if isinstance(expr, ast.Subscript) and isinstance(expr.slice, ast.Constant) and isinstance(expr.slice.value, str):
            return self.keyed(module, expr.slice.value, depth)
        if isinstance(expr, ast.Name) and fn is not None:
            assigned = [n for n in ast.walk(fn) if isinstance(n, ast.Assign) and len(n.targets) == 1
                        and isinstance(n.targets[0], ast.Name) and n.targets[0].id == expr.id]
            if assigned:
                found, unresolved = [], False
                for n in assigned:
                    more, missing = self.constructions(module, fn, n.value, depth + 1)
                    found += more
                    unresolved = unresolved or missing
                return found, unresolved
            if expr.id in params_of(fn):
                return self.committed(module, fn, expr.id, depth)
        return [], True

    def keyed(self, module, key, depth):
        """Every place this module builds a mapping entry `key`: an item assignment, a dict() keyword or a
        dict display, with the value it stores there."""
        found, unresolved = [], False
        for node in module.nodes:
            values = []
            if isinstance(node, ast.Assign):
                for t in node.targets:
                    if isinstance(t, ast.Subscript) and isinstance(t.slice, ast.Constant) and t.slice.value == key:
                        values.append(node.value)
            elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dict':
                values += [k.value for k in node.keywords if k.arg == key]
            elif isinstance(node, ast.Dict):
                values += [v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and k.value == key]
            for value in values:
                owner = module.enclosing(node)
                more, missing = self.constructions(module, owner, value, depth + 1)
                if missing and not more:
                    # The entry is stored here, whatever it holds: this is where it is built.
                    found.append(dict(module=module, function=owner, node=node, actions=All()))
                    unresolved = True
                found += more
                unresolved = unresolved or missing
        return found, unresolved or not found

    def committed(self, module, fn, param, depth):
        """For a transition the store runs (registered in this module): the parameters every commit of
        its operation carries."""
        cls = module.cls_of(fn)
        operations = []
        for node in module.nodes:
            if not isinstance(node, ast.Dict):
                continue
            for k, v in zip(node.keys, node.values):
                if not (isinstance(k, ast.Constant) and k.value in ('transition', 'transaction_transition')):
                    continue
                named = (isinstance(v, ast.Name) and cls is None and v.id == fn.name) or (
                    isinstance(v, ast.Attribute) and cls is not None and v.attr == getattr(fn, 'name', None)
                    and isinstance(v.value, ast.Name) and v.value.id == 'self')
                if not named:
                    continue
                index = 0 if k.value == 'transition' else 1
                names = method_params(module, fn)
                if len(names) <= index or names[index] != param:
                    continue
                assign = module.parents.get(node)
                if isinstance(assign, ast.Assign) and len(assign.targets) == 1 and isinstance(assign.targets[0], ast.Subscript):
                    op = module.const(assign.targets[0].slice)
                    if isinstance(op, str):
                        operations.append(op)
                        continue
                return [], True
        if not operations:
            return [], True
        found, unresolved = [], False
        for node in module.nodes:
            carried = None
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dict':
                entries = {k.arg: k.value for k in node.keywords if k.arg}
            elif isinstance(node, ast.Dict):
                entries = {k.value: v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant)}
            else:
                continue
            if 'operation' not in entries or module.const(entries['operation']) not in operations:
                continue
            carried = entries.get('parameters')
            owner = module.enclosing(node)
            more, missing = self.constructions(module, owner, carried, depth + 1)
            found += more
            unresolved = unresolved or missing
        return found, unresolved or not found

    def values(self, module, fn, node, expr):
        """The claim actions `expr` can hold where `node` builds them."""
        value = module.const(expr)
        if isinstance(value, str):
            return frozenset([value])
        return self.narrow(module, fn, node, [self.strip(expr)], All())

    # -- guards ---------------------------------------------------------------------------------

    def narrow(self, module, fn, node, forms, values):
        """`values` narrowed by the conditions every path to `node` inside `fn` has passed, on any of
        the expressions `forms` (dumped)."""
        if not forms or fn is None:
            return values
        current = module.statement(node)
        while current is not fn and current in module.parents:
            parent = module.parents[current]
            for field in ('body', 'orelse', 'finalbody', 'handlers'):
                block = getattr(parent, field, None)
                if isinstance(block, list) and current in block:
                    for earlier in block[:block.index(current)]:
                        if isinstance(earlier, ast.If) and not earlier.orelse and self.exits(earlier.body):
                            values = self.apply(module, earlier.test, False, forms, values)
                    if isinstance(parent, ast.If) and field == 'body':
                        values = self.apply(module, parent.test, True, forms, values)
                    elif isinstance(parent, ast.If) and field == 'orelse':
                        values = self.apply(module, parent.test, False, forms, values)
            current = parent
        return values

    @staticmethod
    def exits(body):
        return bool(body) and isinstance(body[-1], (ast.Raise, ast.Return))

    def apply(self, module, test, holds, forms, values):
        if isinstance(test, ast.UnaryOp) and isinstance(test.op, ast.Not):
            return self.apply(module, test.operand, not holds, forms, values)
        if isinstance(test, ast.BoolOp):
            if isinstance(test.op, ast.And) and holds or isinstance(test.op, ast.Or) and not holds:
                for part in test.values:
                    values = self.apply(module, part, holds, forms, values)
            return values
        if isinstance(test, ast.Compare) and len(test.ops) == 1 and self.strip(test.left) in forms:
            op, right = test.ops[0], module.const(test.comparators[0])
            if right is NOVALUE:
                return values
            if isinstance(op, (ast.Eq, ast.NotEq)) and isinstance(right, str):
                positive = holds == isinstance(op, ast.Eq)
                return restrict(values, allowed=[right]) if positive else restrict(values, excluded=[right])
            if isinstance(op, (ast.In, ast.NotIn)) and isinstance(right, tuple):
                positive = holds == isinstance(op, ast.In)
                return restrict(values, allowed=right) if positive else restrict(values, excluded=right)
        return values

    # -- the receipt ----------------------------------------------------------------------------

    def obtains(self, module, fn, depth=0, seen=()):
        """Whether calling `fn` makes the Gate's project check unconditionally before it returns."""
        if fn is None or depth > DEPTH or fn in seen or isinstance(fn, ast.Lambda):
            return False
        for stmt in fn.body:
            if self.simple_obtains(module, fn, stmt, depth, seen + (fn,)):
                return True
            if any(isinstance(n, ast.Return) for n in ast.walk(stmt)):
                return False
        return False

    def simple_obtains(self, module, fn, stmt, depth, seen):
        if isinstance(stmt, (ast.If, ast.For, ast.AsyncFor, ast.While, ast.Try, ast.FunctionDef,
                             ast.AsyncFunctionDef, ast.ClassDef, ast.Match)):
            return False
        if isinstance(stmt, (ast.With, ast.AsyncWith)):
            return any(self.simple_obtains(module, fn, s, depth, seen) for s in stmt.body)
        return any(self.is_check(module, fn, call, depth, seen) for call in ast.walk(stmt)
                   if isinstance(call, ast.Call) and not self.deferred(module, call, stmt))

    @staticmethod
    def deferred(module, call, stmt):
        node = call
        while node is not stmt:
            node = module.parents[node]
            if isinstance(node, (ast.Lambda, ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp, ast.IfExp, ast.BoolOp)):
                return True
        return False

    def is_check(self, module, fn, call, depth, seen):
        name = callee(call)
        if name == CHECK:
            return True
        helper = None
        if isinstance(call.func, ast.Attribute) and isinstance(call.func.value, ast.Name) and call.func.value.id == 'self':
            cls = module.cls_of(fn) if not isinstance(fn, ast.Lambda) else None
            if cls is not None:
                helper = module.functions.get(module.qualname(cls) + '.' + call.func.attr)
        elif isinstance(call.func, ast.Name):
            helper = module.functions.get(call.func.id)
        return helper is not None and self.obtains(module, helper, depth + 1, seen)

    def require(self, module, fn, node, what):
        """Refuse unless the Gate's project check is made before `node` on every path through `fn`."""
        if not self.dominated(module, fn, node):
            self.fail(module.stem, module.name_of(fn), node.lineno,
                      '%s hands out work without obtaining the Gate\'s project-check receipt before it' % what)

    def dominated(self, module, fn, node):
        if fn is None or isinstance(fn, ast.Lambda):
            return False
        stmt = module.statement(node)
        # The arguments of the write itself are evaluated before it.
        if isinstance(node, ast.Call):
            for arg in list(node.args) + [k.value for k in node.keywords]:
                for call in ast.walk(arg):
                    if isinstance(call, ast.Call) and self.is_check(module, fn, call, 0, ()) \
                            and not self.deferred(module, call, stmt):
                        return True
        current = stmt
        while current is not fn and current in module.parents:
            parent = module.parents[current]
            if isinstance(parent, (ast.If, ast.While)) and current in parent.body + parent.orelse:
                if any(isinstance(c, ast.Call) and self.is_check(module, fn, c, 0, ()) for c in ast.walk(parent.test)):
                    return True
            for field in ('body', 'orelse', 'finalbody'):
                block = getattr(parent, field, None)
                if isinstance(block, list) and current in block:
                    for earlier in block[:block.index(current)]:
                        if self.simple_obtains(module, fn, earlier, 0, ()):
                            return True
            current = parent
        return False

    def receipts(self, module):
        """A receipt is made only by the Gate's check; its schema is written only by the claim organ."""
        for ref in self.references(module, RECEIPT):
            fn = module.enclosing(ref)
            parent = module.parents.get(ref)
            if not (isinstance(parent, ast.Call) and parent.func is ref) or (module.stem, module.name_of(fn)) != RECEIPT_MAKER:
                self.fail(module.stem, module.name_of(fn), ref.lineno, 'makes a project-check receipt outside the Gate\'s check')
        for node in module.nodes:
            if ((isinstance(node, ast.Name) and node.id == RECEIPT_SCHEMA or isinstance(node, ast.Attribute) and node.attr == RECEIPT_SCHEMA)
                  and module.stem != ORGAN_MODULE):
                self.fail(module.stem, module.name_of(module.enclosing(node)), node.lineno, 'uses the receipt schema outside the claim organ')
            elif (isinstance(node, ast.Constant) and self.schema is not NOVALUE and node.value == self.schema
                  and not (module.stem == ORGAN_MODULE and isinstance(module.parents.get(node), ast.Assign))):
                self.fail(module.stem, module.name_of(module.enclosing(node)), node.lineno, 'writes the receipt schema by hand')

    # -- station contracts ----------------------------------------------------------------------

    def constructor_kinds(self):
        """The entity kinds the station contract's writer writes, read from its own body."""
        kinds = set()
        for module in self.modules.values():
            for name, fn in module.functions.items():
                if name.rsplit('.', 1)[-1] != CONSTRUCTOR:
                    continue
                for node in ast.walk(fn):
                    kind = self.kind_of(module, node)
                    if kind is not NOVALUE:
                        kinds.add(kind)
        if not kinds:
            self.fail('<engine>', None, 0, 'the station contract writer %s is not found' % CONSTRUCTOR)
        return kinds

    def kind_of(self, module, node):
        value = None
        if isinstance(node, ast.Dict):
            value = next((v for k, v in zip(node.keys, node.values) if isinstance(k, ast.Constant) and k.value == 'kind'), None)
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == 'dict':
            value = next((k.value for k in node.keywords if k.arg == 'kind'), None)
        return NOVALUE if value is None else module.const(value)

    def station_bypass(self, module, kinds):
        for node in module.nodes:
            kind = self.kind_of(module, node)
            if kind is NOVALUE or kind not in kinds:
                continue
            fn = module.enclosing(node)
            if fn is None or fn.name != CONSTRUCTOR:
                self.fail(module.stem, module.name_of(fn), node.lineno, 'writes an entity of kind %s without %s' % (kind, CONSTRUCTOR))

    def station_site(self, module, call):
        fn = module.enclosing(call)
        where = module.name_of(fn)
        contract = self.argument(call, 0, 'contract')
        constructions, unresolved = self.constructions(module, fn, contract, 0) if contract is not None else ([], True)
        self.records.append(dict(module=module.stem, function=where, line=call.lineno, writer=CONSTRUCTOR,
                                 classification='handout', reason='a fresh station contract',
                                 built_at=['%s.%s:%s' % (module.stem, module.name_of(c['function']), c['node'].lineno)
                                           for c in constructions]))
        self.require(module, fn, call, 'the station contract write')
        for c in constructions:
            if not self.within(module, c['node'], call):
                self.require(c['module'], c['function'], c['node'], 'the station contract it commits')

    # -- dynamic attribute access ---------------------------------------------------------------

    def dynamic(self, module):
        tracked = (ORGAN, CONSTRUCTOR, RECEIPT)
        for node in module.nodes:
            if not isinstance(node, ast.Call) or callee(node) not in DYNAMIC:
                continue
            name = callee(node)
            if name == 'getattr' and (not isinstance(node.func, ast.Name) or len(node.args) >= 2
                                      and isinstance(node.args[1], ast.Constant)):
                # A literal getattr is a reference like an attribute, found where references are.
                continue
            argument = node.args[1] if name == 'getattr' and len(node.args) >= 2 else node.args[0] if node.args and name != 'getattr' else None
            fn = module.enclosing(node)
            if argument is None:
                self.fail(module.stem, module.name_of(fn), node.lineno, '%s names no attribute that can be resolved' % name)
                continue
            names = self.attribute_names(module, fn, argument, 0)
            if names is None or any(self.may_be(names, t) for t in tracked):
                self.fail(module.stem, module.name_of(fn), node.lineno,
                          '%s(%s) may name a claim or station contract writer: not resolved' % (name, ast.unparse(argument)))

    @staticmethod
    def may_be(names, target):
        if isinstance(names, tuple) and names and names[0] == 'prefix':
            return target.startswith(names[1])
        return target in names

    def attribute_names(self, module, fn, expr, depth):
        """The attribute names `expr` can hold: a frozenset, ('prefix', p), or None when not resolved."""
        if depth > DEPTH:
            return None
        value = module.const(expr, fn)
        if isinstance(value, str):
            return frozenset([value])
        if isinstance(value, tuple) and all(isinstance(v, str) for v in value):
            return frozenset(value)
        if isinstance(expr, ast.BinOp) and isinstance(expr.op, ast.Add) and isinstance(module.const(expr.left), str):
            return ('prefix', module.const(expr.left))
        if not isinstance(expr, ast.Name) or fn is None:
            return None
        # A loop or comprehension over a constant collection, element by element.
        for node in ast.walk(fn):
            loops = [(node.target, node.iter)] if isinstance(node, (ast.For, ast.AsyncFor)) else \
                [(g.target, g.iter) for g in node.generators] if isinstance(node, (ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)) else []
            for target, source in loops:
                position = self.position(target, expr.id)
                if position is None:
                    continue
                items = module.const(source, fn)
                if not isinstance(items, tuple):
                    return None
                picked = set()
                for item in items:
                    element = item
                    for index in position:
                        if not isinstance(element, tuple) or len(element) <= index:
                            return None
                        element = element[index]
                    if not isinstance(element, str):
                        return None
                    picked.add(element)
                return frozenset(picked)
        if isinstance(fn, ast.Lambda) or expr.id not in params_of(fn):
            return None
        if fn.name == '__getattr__' and params_of(fn)[1:2] == [expr.id]:
            # Forwarding a lookup: the attribute is named where it is looked up, and counted there.
            return frozenset()
        index = method_params(module, fn).index(expr.id) if expr.id in method_params(module, fn) else None
        if index is None:
            return None
        names, found = set(), False
        scope = module.enclosing(fn) or module.tree
        method = module.cls_of(fn) is not None
        for node in ast.walk(module.tree if method else scope):
            if not isinstance(node, ast.Call):
                continue
            direct = isinstance(node.func, ast.Name) and node.func.id == fn.name and not method
            bound = isinstance(node.func, ast.Attribute) and node.func.attr == fn.name and method
            if not (direct or bound):
                continue
            if any(isinstance(a, ast.Starred) for a in node.args[:index + 1]):
                return None
            argument = node.args[index] if len(node.args) > index else next(
                (k.value for k in node.keywords if k.arg == expr.id), None)
            if argument is None:
                return None
            more = self.attribute_names(module, module.enclosing(node), argument, depth + 1)
            if more is None or isinstance(more, tuple):
                return None
            names |= more
            found = True
        return frozenset(names) if found else None

    @staticmethod
    def position(target, name):
        if isinstance(target, ast.Name):
            return () if target.id == name else None
        if isinstance(target, (ast.Tuple, ast.List)):
            for i, element in enumerate(target.elts):
                inner = Census.position(element, name)
                if inner is not None:
                    return (i,) + inner
        return None


def census(sources):
    """(records, failures) over {module stem: source}."""
    run = Census(sources).run()
    return run.records, run.failures
