#!/usr/bin/env python3
"""The wall-clock census (VELDO-0358, AC6 and AC7): a gate stage that reads source and nothing else.

A gate's verdict must not depend on how busy the machine is, so a suite may not sleep, read the
clock, give a short timeout or put an upper bound on a duration. This stage finds every such site
by reading the source. It runs no candidate code, measures nothing and has no notion of load.

THE RULES (design, section 9.2). Python is read on its syntax tree, with every call resolved
through the file's own imports and aliases and every name resolved to a numeric constant of the
file where it is one; TypeScript and shell are read on their text.

  R1 sleep     a call that resolves to time.sleep or asyncio.sleep; a command list whose program
               is sleep; the word sleep followed by a number inside a string; waitForTimeout; a
               setTimeout whose callback rejects or fails; a sleep command in a shell script
  R2 clock     a call that resolves to a wall or monotonic clock
  R3 timeout   a timeout other than zero, None or a named hang constant, given as the keyword
               timeout or at a position of the closed table POSITIONS below. The process constant
               is accepted only on a call whose command is a heavy child
  R4 bound     an upper bound, against a number, on a value named or derived as a duration

THE KEY AND THE LISTS (design, section 9.3). A site's key is (file, rule, normalized text of its
source line, qualified name of the enclosing function). Both lists are multisets: a key carries a
count. scripts/suites/wallclock_baseline.json records every unconverted site, with its class;
scripts/suites/wallclock.json records the sites that are right to keep, each with a kind, a reason
and a specification. The exceptions are read from the authority checkout only. The baseline is
read from the authority and from the candidate, and for each key:

  wallclock_site   the candidate has more sites than the authority's baseline count plus its
                   exceptions count
  baseline_stale   the candidate's baseline count is not the smaller of the authority's baseline
                   count and the candidate's sites less the authority's exceptions

So a conversion lowers its entry in the same change with no approval, and the baseline grows only
by an owner-approved change to the protected file. While the authority has no baseline file the
stage reports what it found and judges nothing.

THE SCOPE (design, section 9.1) is observed, not inferred: every file under scripts/ and proof/
that the authority's last opened-files record lists for any suite; every file the candidate
changed under scripts/, proof/ and engine/ui/e2e; engine/ui/e2e, engine/ui/playwright.config.ts
and the gate tooling, always; and for R3 only the engine files of the design's section 4.8.
Until a record exists the scope is every file under scripts/ and proof/. A baseline entry of a
file outside the scope is carried unchanged: such a file is the authority's own, byte for byte.

  python3 scripts/check_wallclock.py                       the stage, over this checkout
  python3 scripts/check_wallclock.py --root C --authority A --record R
  python3 scripts/check_wallclock.py --write-baseline PATH  write the baseline of what is found
  python3 scripts/check_wallclock.py --sites                print every site found, one per line
"""
import argparse
import ast
import hashlib
import json
import os
from pathlib import Path
import re
import sys

BASELINE = 'scripts/suites/wallclock_baseline.json'
EXCEPTIONS = 'scripts/suites/wallclock.json'
RECORD = '.veldo/opened_files.json'
AUTHORITY_ENV = 'VELDO_GATE_AUTHORITY'
BASELINE_SCHEMA = 'veldo.wallclock-baseline/v1'
EXCEPTIONS_SCHEMA = 'veldo.wallclock-exceptions/v1'
RULES = ('R1', 'R2', 'R3', 'R4')
KINDS = ('lower_bound', 'timer_fires', 'subject', 'supplied_clock')
# The use classes of the design's section 3, as far as source alone tells them apart; ST is a
# sleep inside a string.
CLASSES = ('S1', 'S2', 'S3', 'ST', 'P', 'D1', 'D2', 'T', 'A')
WAIT_HANG, PROCESS_HANG = 'WAIT_HANG_SECONDS', 'PROCESS_HANG_SECONDS'
CONTRACT_HANG = {WAIT_HANG: 600, PROCESS_HANG: 3600}  # the hang constants' values, contracts.md
# The one module R1 to R3 do not apply to: the wait primitive and its stamp.
SUPPORT = 'scripts/suites/support/waits.py'
# The engine files of the design's section 4.8, read for R3 only: a numeric timeout there is a
# site, and a value read from the timers table is not.
ENGINE_R3 = tuple('engine/.veldo/' + name for name in (
    'control_launch.py', 'control_containment.py', 'control_heartbeat.py', 'control_service.py',
    'control_client.py', 'control_client_api.py', 'control_store.py', 'control_engine_claude.py',
    'control_engine_codex.py', 'control_factory_setup_upgrade.py', 'control_workflow_cycle_pm.py',
    'policy_contract.py'))
ALWAYS_TREES = ('engine/ui/e2e',)
ALWAYS_FILES = ('engine/ui/playwright.config.ts',)
SCOPE_TREES = ('scripts', 'proof')
CHANGED_TREES = ('scripts', 'proof', 'engine/ui/e2e')
SKIP_DIRECTORIES = ('__pycache__', 'node_modules', '.git', 'test-results', 'playwright-report')
SCRIPT_SUFFIXES = ('.ts', '.tsx', '.js', '.mjs', '.cjs')
TEXT_LIMIT = 200

# A bare module name a suite fragment uses without importing it is the shared namespace's.
MODULES = ('time', 'asyncio', 'datetime', 'subprocess', 'threading', 'queue', 'socket', 'select',
           'selectors', 'signal', 'multiprocessing')
SLEEPS = ('time.sleep', 'asyncio.sleep')
CLOCKS = tuple('time.' + name for name in ('time', 'monotonic', 'perf_counter', 'time_ns', 'monotonic_ns',
                                           'perf_counter_ns')) + (
    'datetime.datetime.now', 'datetime.datetime.utcnow', 'datetime.now', 'datetime.utcnow')
# THE CLOSED TABLE OF POSITIONAL TIMEOUTS. A callable resolved through the imports:
QUALIFIED = {'socket.create_connection': 1, 'select.select': 3, 'signal.alarm': 0, 'signal.setitimer': 1,
             'threading.Timer': 0, 'asyncio.wait_for': 1, 'threading.Barrier': 2}
# a method of an object whose constructor the file shows:
TYPED = {
    'threading.Thread': {'join': 0}, 'multiprocessing.Process': {'join': 0},
    'threading.Event': {'wait': 0}, 'threading.Condition': {'wait': 0, 'wait_for': 1},
    'threading.Barrier': {'wait': 0},
    'queue.Queue': {'get': 1, 'put': 2}, 'queue.LifoQueue': {'get': 1, 'put': 2},
    'queue.PriorityQueue': {'get': 1, 'put': 2}, 'multiprocessing.Queue': {'get': 1, 'put': 2},
    'subprocess.Popen': {'wait': 0, 'communicate': 1},
    'socket.socket': {'settimeout': 0},
    'selectors.DefaultSelector': {'select': 0}, 'selectors.EpollSelector': {'select': 0},
    'selectors.PollSelector': {'select': 0}, 'selectors.SelectSelector': {'select': 0},
    'select.poll': {'poll': 0}, 'select.epoll': {'poll': 0},
}
# and a method of an object the file does not show the making of, matched by name and position
# only when the argument there is numeric. String join takes an iterable and dict get a key, so
# neither is ever a site.
METHODS = {'join': 0, 'wait': 0, 'wait_for': 1, 'get': 1, 'put': 2, 'communicate': 1, 'settimeout': 0,
           'select': 0, 'poll': 0}
BLOCK_FLAG = {'get': 0, 'put': 1}
# A heavy child (design, section 6) runs a suite or a selftest, a gate stage, a browser run, a
# package install or qualify. It is told by what its command names, never by how long it takes.
HEAVY_FILES = ('selftest.py', 'verify.sh', 'check_first_use.py', 'check_gate_mutations.py',
               'check_teeth_mutations.py', 'check_review_mutations.py', 'check_install_and_run.py',
               'suite_equiv.py', 'suite_slice.py', 'suite_labels.py')
HEAVY_WORDS = re.compile(r'(?<![\w.-])(?:pip3?|npm|npx|pnpm|playwright|qualify|--suite|--upto)(?![\w-])')
CHILD_CALLS = ('subprocess.run', 'subprocess.call', 'subprocess.check_call', 'subprocess.check_output',
               'subprocess.Popen')

TEXT_SLEEP = re.compile(r'(?<![\w])sleep\s*\(?\s*(?:\d+\.?\d*|\.\d+)')
SHELL_SLEEP = re.compile(r'(?:^|[;&|(`{]|\s)sleep\s+(?:\d+\.?\d*|\.\d+)')
DURATION = re.compile(r'(?:^|_)(?:elapsed|took|waited|seconds|duration|latency|window)(?:_|$)')
SCRIPT_HANG = re.compile(r'^(?:[\w.]+\.)?(?:WAIT|PROCESS)_HANG_(?:SECONDS|MS)(?:\s*\*\s*1000)?$')


class Refused(ValueError):
    pass


def normalized(line):
    """One source line as a key: its whitespace collapsed, and a long line cut with its digest."""
    text = ' '.join(line.split())
    if len(text) > TEXT_LIMIT:
        text = text[:TEXT_LIMIT] + '#' + hashlib.sha256(text.encode()).hexdigest()[:12]
    return text


def site(found, rel, rule, line, text, function, form, cls):
    found.append({'file': rel, 'rule': rule, 'line': line, 'text': normalized(text), 'function': function,
                  'form': form, 'class': cls})


class Python:
    """The sites of one Python file."""

    def __init__(self, rel, text, rules, engine=False):
        self.rel, self.rules, self.engine = rel, rules, engine
        self.lines = text.splitlines()
        self.tree = ast.parse(text)
        self.found = []
        self.parents = {}
        for node in ast.walk(self.tree):
            for child in ast.iter_child_nodes(node):
                self.parents[child] = node
        self.aliases = {name: name for name in MODULES}
        self.numbers, self.types, self.strings = {}, {}, {}
        self.read_bindings()

    # ---- what the file's own names mean ---------------------------------------------------

    def read_bindings(self):
        assigned = {}
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.asname:
                        self.aliases[alias.asname] = alias.name
                    else:
                        self.aliases[alias.name.split('.')[0]] = alias.name.split('.')[0]
            elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
                for alias in node.names:
                    self.aliases[alias.asname or alias.name] = node.module + '.' + alias.name
            elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                assigned.setdefault(self.dotted(node.targets[0]), []).append(node.value)
            elif isinstance(node, ast.withitem) and node.optional_vars is not None:
                assigned.setdefault(self.dotted(node.optional_vars), []).append(node.context_expr)
        assigned.pop(None, None)
        # A name bound once to a module, a callable or a constructor's result keeps that meaning.
        for _ in range(3):
            for name, values in assigned.items():
                if len(values) != 1:
                    continue
                value = values[0]
                resolved = self.resolve(value)
                if resolved and '.' not in name:
                    self.aliases.setdefault(name, resolved)
                if isinstance(value, ast.Call):
                    made = self.resolve(value.func)
                    if made in TYPED:
                        self.types[name] = made
                number = self.number(value)
                if number is not None and '.' not in name:
                    self.numbers[name] = number
        for name, values in assigned.items():
            self.strings[name] = [n.value for value in values for n in ast.walk(value)
                                  if isinstance(n, ast.Constant) and isinstance(n.value, str)]

    @staticmethod
    def dotted(node):
        parts = []
        while isinstance(node, ast.Attribute):
            parts.append(node.attr)
            node = node.value
        if isinstance(node, ast.Name):
            return '.'.join([node.id] + parts[::-1])
        return None

    def resolve(self, node):
        """The qualified name an expression stands for through this file's imports, or None."""
        if isinstance(node, ast.Name):
            return self.aliases.get(node.id)
        if isinstance(node, ast.Attribute):
            base = self.resolve(node.value)
            return base + '.' + node.attr if base else None
        if isinstance(node, ast.Call) and node.args and isinstance(node.args[0], ast.Constant) \
                and isinstance(node.args[0].value, str):
            called = node.func
            if isinstance(called, ast.Name) and called.id == '__import__':
                return node.args[0].value
            if isinstance(called, ast.Attribute) and called.attr == 'import_module':
                return node.args[0].value
        return None

    def number(self, node):
        """The value of a numeric literal, a numeric constant name or arithmetic over them, or None."""
        if isinstance(node, ast.Constant):
            return node.value if type(node.value) in (int, float) else None
        if isinstance(node, ast.Name):
            return self.numbers.get(node.id)
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.USub, ast.UAdd)):
            value = self.number(node.operand)
            return None if value is None else (-value if isinstance(node.op, ast.USub) else value)
        if isinstance(node, ast.BinOp):
            left, right = self.number(node.left), self.number(node.right)
            if left is None or right is None:
                return None
            try:
                if isinstance(node.op, ast.Add):
                    return left + right
                if isinstance(node.op, ast.Sub):
                    return left - right
                if isinstance(node.op, ast.Mult):
                    return left * right
                if isinstance(node.op, ast.Div):
                    return left / right
            except (ZeroDivisionError, OverflowError):
                return None
        return None

    # ---- where a node stands --------------------------------------------------------------

    def function(self, node):
        names = []
        while node in self.parents:
            node = self.parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.append(node.name)
        return '.'.join(reversed(names)) or '<module>'

    def owner(self, node):
        """The function, or the module, a node belongs to."""
        while node in self.parents:
            node = self.parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return node
        return self.tree

    def within(self, node, kinds):
        """Whether a node stands inside one of `kinds`, looking no further than its own function."""
        while node in self.parents:
            child, node = node, self.parents[node]
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
                return False
            if isinstance(node, kinds):
                return not (isinstance(node, (ast.For, ast.AsyncFor)) and child is node.iter)
        return False

    def add(self, rule, node, form, cls, line=None, text=None):
        if rule not in self.rules:
            return
        line = node.lineno if line is None else line
        if text is None:
            text = self.lines[line - 1] if 0 < line <= len(self.lines) else ''
        site(self.found, self.rel, rule, line, text, self.function(node), form, cls)

    # ---- the rules ------------------------------------------------------------------------

    def scan(self):
        skip_strings = set()
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Expr) and isinstance(node.value, ast.Constant):
                skip_strings.add(node.value)  # a docstring or a bare string is not run
            elif isinstance(node, ast.Call):
                self.call(node)
            elif isinstance(node, (ast.List, ast.Tuple)):
                self.command(node, skip_strings)
            elif isinstance(node, ast.Compare):
                self.bound(node)
        for node in ast.walk(self.tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and node not in skip_strings:
                self.string(node)
        self.found.sort(key=lambda s: (s['line'], s['rule'], s['form']))
        return self.found

    def call(self, node):
        resolved = self.resolve(node.func)
        if resolved in SLEEPS:
            length = self.number(node.args[0]) if node.args else None
            cls = 'S2' if self.within(node, (ast.While, ast.For, ast.AsyncFor)) else \
                'S3' if length is not None and length >= 30 else 'S1'
            self.add('R1', node, 'call ' + resolved, cls)
        if resolved in CLOCKS:
            self.add('R2', node, 'read ' + resolved, self.clock_class(node))
        for keyword in node.keywords:
            if keyword.arg == 'timeout':
                self.timeout(node, keyword.value, 'keyword timeout', True)
        for position, value, form, strict in self.positional(node, resolved):
            self.timeout(node, value, form, strict)

    def positional(self, node, resolved):
        """The arguments of a call that stand at a timeout position of the closed table."""
        if resolved in QUALIFIED:
            position = QUALIFIED[resolved]
            if len(node.args) > position:
                yield position, node.args[position], '%s argument %d' % (resolved, position), True
            return
        if resolved is not None:
            return  # some other callable of a module: os.path.join and its like
        called = node.func
        if isinstance(called, ast.Name):
            # shared.wait_for(condition, bound, what): the bound of a suite's own wait.
            if called.id == 'wait_for' and len(node.args) > 1 and self.number(node.args[1]) is not None:
                yield 1, node.args[1], 'wait_for argument 1', False
            return
        if not isinstance(called, ast.Attribute) or isinstance(called.value, (ast.Constant, ast.JoinedStr)):
            return  # ", ".join(parts)
        made = self.types.get(self.dotted(called.value) or '')
        if made is None and isinstance(called.value, ast.Call):
            made = self.resolve(called.value.func) if self.resolve(called.value.func) in TYPED else None
        table, strict = (TYPED[made], True) if made else (METHODS, False)
        position = table.get(called.attr)
        if position is None or len(node.args) <= position:
            return
        if called.attr in BLOCK_FLAG:
            flag = node.args[BLOCK_FLAG[called.attr]]
            if not (isinstance(flag, ast.Constant) and isinstance(flag.value, bool)):
                return  # d.get(k, 5): argument 0 is a key, not a block flag
        kind = (made or '').split('.')[-1] or 'method'
        yield position, node.args[position], '%s.%s argument %d' % (kind, called.attr, position), strict

    def timeout(self, node, value, form, strict):
        if isinstance(value, ast.Constant) and value.value is None:
            return
        # A hang constant by its name, also when the file defines it (and the name then resolves to a
        # number): it is the hang bound only at the contract's value (VELDO-0358 contracts.md).
        named = (self.dotted(value) or '').split('.')[-1]
        if named in CONTRACT_HANG and self.number(value) in (None, CONTRACT_HANG[named]):
            if named == PROCESS_HANG and not self.heavy(node):
                self.add('R3', node, form + ' %s on a child that is not heavy' % named, 'T')
            return
        number = self.number(value)
        if number is not None:
            if number != 0:
                self.add('R3', node, form + ' %s' % self.shown(value), 'T')
            return
        name = (self.dotted(value) or '').split('.')[-1]
        if name == WAIT_HANG:
            return
        if name == PROCESS_HANG:
            if not self.heavy(node):
                self.add('R3', node, form + ' %s on a child that is not heavy' % name, 'T')
            return
        if strict and not self.engine:
            self.add('R3', node, form + ' %s, not a named hang constant' % self.shown(value), 'T')

    def shown(self, value):
        text = ast.get_source_segment('\n'.join(self.lines), value) or ''
        return ' '.join(text.split())[:40]

    def heavy(self, node):
        """Whether a call's command names one of the heavy kinds of child."""
        texts = [n.value for n in ast.walk(node) if isinstance(n, ast.Constant) and isinstance(n.value, str)]
        names = {self.dotted(n) for n in ast.walk(node) if isinstance(n, (ast.Name, ast.Attribute))}
        for name in names - {None}:
            texts.extend(self.strings.get(name, ()))
        return any(HEAVY_WORDS.search(text) or any(name in text for name in HEAVY_FILES) for text in texts)

    def clock_class(self, node):
        """P, a read compared inside a loop; D2, a read handed to the product as its deadline; D1,
        a read that is stored."""
        loops = (ast.While, ast.For, ast.AsyncFor)
        if self.within(node, ast.Compare) and self.within(node, loops):
            return 'P'
        climb = node
        while climb in self.parents and not isinstance(climb, ast.stmt):
            child, climb = climb, self.parents[climb]
            if isinstance(climb, ast.While) and child is climb.test:
                return 'P'
            if isinstance(climb, ast.keyword) and climb.arg and re.search(
                    r'deadline|expire|expiry|until|not_after|timeout', climb.arg):
                return 'D2'
            if isinstance(climb, ast.Call) and child is not climb.func:
                name = (self.dotted(climb.func) or '').split('.')[-1]
                if name[:1].isupper():
                    return 'D2'
        if isinstance(climb, ast.Assign) and len(climb.targets) == 1 and isinstance(climb.targets[0], ast.Name):
            target = climb.targets[0].id
            for other in ast.walk(self.owner(node)):
                if isinstance(other, ast.Compare) and any(
                        isinstance(n, ast.Name) and n.id == target for n in ast.walk(other)):
                    parent = self.parents.get(other)
                    if self.within(other, loops) or (isinstance(parent, ast.While) and parent.test is other):
                        return 'P'
        return 'D1'

    def command(self, node, skip_strings):
        """A command list whose program is sleep with a number, wherever in the list the program
        stands: ['sleep', '2'] and [flock, '-x', lock, 'sleep', '60']."""
        for index, (program, length) in enumerate(zip(node.elts, node.elts[1:])):
            if not (isinstance(program, ast.Constant) and isinstance(program.value, str)
                    and (program.value == 'sleep' or program.value.endswith('/sleep'))):
                continue
            numeric = isinstance(length, ast.Constant) and re.fullmatch(r'\d+\.?\d*|\.\d+', str(length.value))
            if numeric or (index == 0 and not isinstance(length, ast.Constant)):
                self.add('R1', node, 'command list sleep %s' % self.shown(length), 'S3', line=program.lineno)
                skip_strings.update(e for e in (program, length) if isinstance(e, ast.Constant))

    def string(self, node):
        value = node.value
        if 'sleep' not in value:
            return
        spans_lines = getattr(node, 'end_lineno', node.lineno) != node.lineno
        for index, line in enumerate(value.split('\n')):
            for _ in TEXT_SLEEP.finditer(line):
                self.add('R1', node, 'sleep in a string', 'ST',
                         line=node.lineno + (index if spans_lines else 0), text=line)

    def bound(self, node):
        operands = [node.left] + list(node.comparators)
        for index, op in enumerate(node.ops):
            left, right = operands[index], operands[index + 1]
            if isinstance(op, (ast.Lt, ast.LtE)):
                value, limit = left, right
            elif isinstance(op, (ast.Gt, ast.GtE)):
                value, limit = right, left
            else:
                continue
            how = self.duration(value)
            if how and self.limit(limit):
                self.add('R4', node, 'upper bound on %s' % how, 'A')

    def duration(self, node):
        while isinstance(node, ast.Call) and isinstance(node.func, ast.Name) \
                and node.func.id in ('abs', 'round', 'float', 'int') and node.args:
            node = node.args[0]
        name = None
        if isinstance(node, ast.Name):
            name = node.id
        elif isinstance(node, ast.Attribute):
            name = node.attr
        elif isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            name = node.slice.value
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr == 'get' \
                and node.args and isinstance(node.args[0], ast.Constant):
            name = node.args[0].value
        if isinstance(name, str) and DURATION.search(name.lower()) and name != name.upper():
            return 'the duration ' + name
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Sub):
            if any(self.stamp(side) for side in (node.left, node.right)) \
                    and all(self.stamp(side) or self.number(side) is not None or isinstance(side, ast.Subscript)
                            for side in (node.left, node.right)):
                return 'a difference of _at values'
            if isinstance(node.left, ast.Call) and self.resolve(node.left.func) in CLOCKS:
                return 'a difference from a clock read'
        return None

    def stamp(self, node):
        """Whether a value is named as a moment: its name, attribute or key is at or ends in _at."""
        if isinstance(node, ast.Subscript) and isinstance(node.slice, ast.Constant):
            name = node.slice.value
        else:
            name = (self.dotted(node) or '').split('.')[-1]
        return isinstance(name, str) and (name == 'at' or name.endswith('_at'))

    def limit(self, node):
        """Whether an expression is a number above zero: a literal, a constant, or arithmetic that
        holds one."""
        number = self.number(node)
        if number is not None:
            return number > 0
        if isinstance(node, (ast.Name, ast.Attribute)):
            name = (self.dotted(node) or '').split('.')[-1]
            return bool(name) and name == name.upper() and any(c.isalpha() for c in name)
        if isinstance(node, ast.BinOp):
            leaves = [n for n in ast.walk(node) if not isinstance(n, (ast.BinOp, ast.operator, ast.expr_context,
                                                                      ast.UnaryOp, ast.unaryop))]
            return all(isinstance(n, (ast.Constant, ast.Name, ast.Attribute)) for n in leaves) \
                and any(self.number(n) is not None or self.limit(n) for n in leaves
                        if isinstance(n, (ast.Constant, ast.Name)))
        return False


def strip_comments(text):
    """TypeScript text with its comments blanked, line numbers kept."""
    text = re.sub(r'/\*.*?\*/', lambda m: re.sub(r'[^\n]', ' ', m.group(0)), text, flags=re.S)
    return re.sub(r'(^|\s)//[^\n]*', lambda m: m.group(1), text)


def scan_script(rel, text, rules):
    """The sites of one TypeScript or JavaScript file, read on its text."""
    found = []
    lines = text.splitlines()
    for number, line in enumerate(strip_comments(text).splitlines(), 1):
        original = lines[number - 1] if number <= len(lines) else line
        if 'R1' in rules:
            for _ in re.finditer(r'\bwaitForTimeout\s*\(', line):
                site(found, rel, 'R1', number, original, '<module>', 'waitForTimeout', 'S1')
            for match in re.finditer(r'(?<![.\w])setTimeout\s*\(', line):
                tail = ' '.join(lines[number - 1:number + 3])
                if re.search(r'\b(?:reject|throw|fail)\b', tail[tail.find('setTimeout'):][:400]):
                    site(found, rel, 'R1', number, original, '<module>', 'setTimeout that rejects or fails', 'S1')
        if 'R2' in rules:
            for match in re.finditer(r'\b(Date\.now|performance\.now)\s*\(', line):
                site(found, rel, 'R2', number, original, '<module>', 'read ' + match.group(1), 'D1')
        if 'R3' in rules:
            values = [('timeout option', m.group(1)) for m in re.finditer(r'\btimeout\s*:\s*([^,}\n]+)', line)]
            values += [(m.group(1), m.group(2)) for m in re.finditer(
                r'\.(setTimeout|setDefaultTimeout|setDefaultNavigationTimeout|setSlow)\s*\(\s*([^)\n]*)\)', line)]
            for form, value in values:
                value = value.strip().rstrip(';').strip()
                if value in ('0', 'undefined') or SCRIPT_HANG.match(value):
                    continue
                site(found, rel, 'R3', number, original, '<module>', '%s %s' % (form, value[:40]), 'T')
    return found


def scan_shell(rel, text, rules):
    found = []
    if 'R1' in rules:
        for number, line in enumerate(text.splitlines(), 1):
            if line.lstrip().startswith('#'):
                continue
            for _ in SHELL_SLEEP.finditer(line):
                site(found, rel, 'R1', number, line, '<module>', 'sleep command', 'S1')
    return found


def kind_of(path, rel):
    if rel.endswith('.py'):
        return 'python'
    if rel.endswith(SCRIPT_SUFFIXES):
        return 'script'
    if rel.endswith('.sh'):
        return 'shell'
    return None


def scan_file(root, rel, rules):
    """(sites, note): the sites of one file under the given rules."""
    kind = kind_of(root / rel, rel)
    if kind is None:
        return [], None
    try:
        text = (root / rel).read_text()
    except (OSError, UnicodeDecodeError) as error:
        return [], '%s: not read (%s)' % (rel, type(error).__name__)
    if rel == SUPPORT:
        rules = tuple(rule for rule in rules if rule == 'R4')
    if kind == 'script':
        return scan_script(rel, text, rules), None
    if kind == 'shell':
        return scan_shell(rel, text, rules), None
    try:
        return Python(rel, text, rules, engine=rel in ENGINE_R3).scan(), None
    except (SyntaxError, ValueError, RecursionError) as error:
        # A file that is no Python this interpreter reads is read as text for its sleeps.
        found = []
        if 'R1' in rules:
            for number, line in enumerate(text.splitlines(), 1):
                for _ in TEXT_SLEEP.finditer(line):
                    site(found, rel, 'R1', number, line, '<module>', 'sleep in unparsed text', 'ST')
        return found, '%s: not parsed (%s), read as text' % (rel, type(error).__name__)


def walk(root, tree):
    base = root / tree
    if base.is_file():
        yield tree
        return
    for directory, names, files in os.walk(base):
        names[:] = sorted(n for n in names if n not in SKIP_DIRECTORIES)
        for name in sorted(files):
            yield os.path.relpath(os.path.join(directory, name), root)


def read_record(path):
    """The opened-files record: suite name to the repository-relative paths it opened. None when
    there is none; a record of another shape is refused."""
    if path is None or not Path(path).exists():
        return None
    try:
        record = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise Refused('opened-files record %s is not readable JSON: %s' % (path, error))
    if not isinstance(record, dict) or not all(
            isinstance(k, str) and isinstance(v, list) and all(isinstance(p, str) for p in v)
            for k, v in record.items()):
        raise Refused('opened-files record %s is not suite name to a list of paths' % path)
    return record


def same(left, right):
    try:
        return left.stat().st_size == right.stat().st_size and left.read_bytes() == right.read_bytes()
    except OSError:
        return False


def scope(root, authority, record):
    """({file: rules}, how the scope was made)."""
    chosen = {}

    def take(rel, rules=RULES):
        if kind_of(root / rel, rel) and (root / rel).is_file():
            chosen.setdefault(rel, set()).update(rules)

    if record is None:
        how = 'no opened-files record: every file under scripts/ and proof/'
        for tree in SCOPE_TREES:
            for rel in walk(root, tree):
                take(rel)
    else:
        how = 'the opened-files record of %d suite(s)' % len(record)
        for paths in record.values():
            for rel in paths:
                rel = os.path.normpath(rel)
                if rel.startswith(tuple(tree + '/' for tree in SCOPE_TREES)):
                    take(rel)
        if root.resolve() != authority.resolve():
            changed = 0
            for tree in CHANGED_TREES:
                for rel in walk(root, tree):
                    if rel not in chosen and kind_of(root / rel, rel) and not same(root / rel, authority / rel):
                        take(rel)
                        changed += 1
            how += ', %d changed file(s)' % changed
    for tree in ALWAYS_TREES:
        for rel in walk(root, tree):
            take(rel)
    for rel in ALWAYS_FILES:
        take(rel)
    for rel in sorted(os.listdir(root / 'scripts')) if (root / 'scripts').is_dir() else ():
        take('scripts/' + rel)  # the gate and mutation tooling
    for rel in ENGINE_R3:
        take(rel, ('R3',))
    return chosen, how


def key_of(entry):
    return entry['file'], entry['rule'], entry['text'], entry['function']


def load_list(path, exceptions):
    """A list as {key: count} and {key: entry}; an entry of any other shape is refused."""
    what = 'exceptions' if exceptions else 'baseline'
    try:
        document = json.loads(Path(path).read_text())
    except (OSError, ValueError) as error:
        raise Refused('%s %s is not readable JSON: %s' % (what, path, error))
    schema = EXCEPTIONS_SCHEMA if exceptions else BASELINE_SCHEMA
    if not isinstance(document, dict) or set(document) - {'schema', 'note', 'entries'} \
            or document.get('schema') != schema or not isinstance(document.get('entries'), list):
        raise Refused('%s %s is not a %s document' % (what, path, schema))
    fields = {'file', 'rule', 'text', 'function', 'count'} | (
        {'kind', 'reason', 'specification'} if exceptions else {'class'})
    counts, entries = {}, {}
    for index, entry in enumerate(document['entries']):
        where = '%s %s entry %d' % (what, path, index)
        if not isinstance(entry, dict) or set(entry) != fields:
            raise Refused('%s does not have exactly the fields %s' % (where, ', '.join(sorted(fields))))
        if not all(isinstance(entry[f], str) and entry[f] for f in fields - {'count'}):
            raise Refused('%s has an empty or non-text field' % where)
        if type(entry['count']) is not int or entry['count'] < 1:
            raise Refused('%s has a count that is not a positive whole number' % where)
        if entry['rule'] not in RULES:
            raise Refused('%s names no rule: %r' % (where, entry['rule']))
        if exceptions and entry['kind'] not in KINDS:
            raise Refused('%s has the unknown kind %r (the kinds are %s)' % (where, entry['kind'], ', '.join(KINDS)))
        if exceptions and not re.fullmatch(r'(?:VELDO|WARP)-\d{4}', entry['specification']):
            raise Refused('%s names no specification: %r' % (where, entry['specification']))
        if not exceptions and entry['class'] not in CLASSES:
            raise Refused('%s has the unknown class %r' % (where, entry['class']))
        key = key_of(entry)
        if key in counts:
            raise Refused('%s repeats the key of an earlier entry' % where)
        counts[key], entries[key] = entry['count'], entry
    return counts, entries


def census(root, files):
    sites, notes = [], []
    for rel in sorted(files):
        found, note = scan_file(root, rel, tuple(sorted(files[rel])))
        sites.extend(found)
        if note:
            notes.append(note)
    return sites, notes


def counted(sites):
    counts, first = {}, {}
    for one in sites:
        key = key_of(one)
        counts[key] = counts.get(key, 0) + 1
        first.setdefault(key, one)
    return counts, first


def judge(counts, files, root, authority_baseline, authority_exceptions, candidate_baseline):
    """The red findings: (error, key, sites, allowed or required, candidate's baseline count)."""
    problems = []
    for key in sorted(set(counts) | set(authority_baseline) | set(authority_exceptions) | set(candidate_baseline)):
        have = counts.get(key, 0)
        base, excepted = authority_baseline.get(key, 0), authority_exceptions.get(key, 0)
        recorded = candidate_baseline.get(key, 0)
        allowed = base + excepted
        if have > allowed:
            problems.append(('wallclock_site', key, have, allowed, recorded))
        if key[0] in files or not (root / key[0]).is_file():
            required = min(max(have - excepted, 0), base)
        else:
            required = base  # a file outside the scope is the authority's own: its entry is carried
        if recorded != required:
            problems.append(('baseline_stale', key, have, required, recorded))
    return problems


def baseline_document(counts, first, exceptions):
    entries = []
    for key in sorted(counts):
        count = counts[key] - exceptions.get(key, 0)
        if count > 0:
            entries.append({'file': key[0], 'rule': key[1], 'text': key[2], 'function': key[3], 'count': count,
                            'class': first[key]['class']})
    return {'schema': BASELINE_SCHEMA,
            'note': 'Every unconverted wall-clock site (VELDO-0358). Written by scripts/check_wallclock.py '
                    '--write-baseline. An entry is lowered or removed by the change that converts its site; '
                    'it is never raised or added without the owner.',
            'entries': entries}


def rendered(document):
    """A list as text with one entry to a line, so that a change to one site is a change to one line."""
    lines = ['{', ' "schema": %s,' % json.dumps(document['schema']), ' "note": %s,' % json.dumps(document['note']),
             ' "entries": [']
    entries = [json.dumps(entry, sort_keys=True) for entry in document['entries']]
    lines += ['  ' + entry + (',' if index + 1 < len(entries) else '') for index, entry in enumerate(entries)]
    return '\n'.join(lines + [' ]', '}']) + '\n'


def summary(counts, first):
    by_rule = {rule: 0 for rule in RULES}
    by_class = {}
    for key, count in counts.items():
        by_rule[key[1]] += count
        by_class[first[key]['class']] = by_class.get(first[key]['class'], 0) + count
    return by_rule, by_class


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--root', help='the candidate checkout (default: the checkout this script is in)')
    parser.add_argument('--authority', help='the authority checkout (default: $%s, else the candidate)' % AUTHORITY_ENV)
    parser.add_argument('--record', help='the opened-files record (default: %s of the authority)' % RECORD)
    parser.add_argument('--write-baseline', metavar='PATH', help='write the baseline of the sites found and stop')
    parser.add_argument('--sites', action='store_true', help='print every site found')
    args = parser.parse_args(argv)
    root = Path(args.root).resolve() if args.root else Path(__file__).resolve().parent.parent
    authority = Path(args.authority or os.environ.get(AUTHORITY_ENV) or root).resolve()
    try:
        record = read_record(args.record if args.record else authority / RECORD)
        files, how = scope(root, authority, record)
        sites, notes = census(root, files)
        counts, first = counted(sites)
        exceptions_path, baseline_path = authority / EXCEPTIONS, authority / BASELINE
        exceptions = load_list(exceptions_path, True)[0] if exceptions_path.exists() else {}
        by_rule, by_class = summary(counts, first)
        print('wallclock: scope: %s; %d file(s) read, %d with a site' % (
            how, len(files), len({key[0] for key in counts})))
        for note in notes:
            print('wallclock: note: ' + note)
        print('wallclock: sites: %d (%s); by class: %s; excepted by the authority: %d' % (
            sum(counts.values()), ', '.join('%s %d' % item for item in sorted(by_rule.items())),
            ', '.join('%s %d' % item for item in sorted(by_class.items())) or 'none',
            sum(min(count, exceptions.get(key, 0)) for key, count in counts.items())))
        if args.sites:
            for one in sites:
                print('wallclock: site %s %s:%d in %s [%s] (%s): %s' % (
                    one['rule'], one['file'], one['line'], one['function'], one['class'], one['form'], one['text']))
        if args.write_baseline:
            document = baseline_document(counts, first, exceptions)
            Path(args.write_baseline).write_text(rendered(document))
            print('wallclock: baseline of %d entry(ies), %d site(s), written to %s' % (
                len(document['entries']), sum(e['count'] for e in document['entries']), args.write_baseline))
            return 0
        if not baseline_path.exists():
            print('wallclock: report mode: the authority has no %s, so nothing is judged' % BASELINE)
            return 0
        authority_baseline = load_list(baseline_path, False)[0]
        candidate_path = root / BASELINE
        candidate_baseline = load_list(candidate_path, False)[0] if candidate_path.exists() else {}
    except Refused as error:
        print('wallclock: list_refused: %s' % error)
        print('wallclock: RED (a list or the record is refused)')
        return 1
    by_file = {}
    for key, count in candidate_baseline.items():
        by_file[key[0]] = by_file.get(key[0], 0) + count
    print('wallclock: baseline: %d entry(ies), %d site(s) in %d file(s); by rule: %s' % (
        len(candidate_baseline), sum(candidate_baseline.values()), len(by_file),
        ', '.join('%s %d' % (rule, sum(c for k, c in candidate_baseline.items() if k[1] == rule)) for rule in RULES)))
    problems = judge(counts, files, root, authority_baseline, exceptions, candidate_baseline)
    for error, key, have, wanted, recorded in problems:
        seen = first.get(key)
        where = '%s:%d' % (key[0], seen['line']) if seen else key[0]
        form = seen['form'] if seen else 'no site left'
        if error == 'wallclock_site':
            print('wallclock: wallclock_site %s (%s) %s in %s: %d site(s), the authority allows %d: %s' % (
                key[1], form, where, key[3], have, wanted, key[2]))
        else:
            print('wallclock: baseline_stale %s (%s) %s in %s: the baseline says %d, required %d (%d site(s)): %s' % (
                key[1], form, where, key[3], recorded, wanted, have, key[2]))
    if problems:
        print('wallclock: RED (%d wallclock_site, %d baseline_stale)' % (
            sum(1 for p in problems if p[0] == 'wallclock_site'),
            sum(1 for p in problems if p[0] == 'baseline_stale')))
        return 1
    print('wallclock: pass (no site over its allowed count, every baseline entry at its required count)')
    return 0


if __name__ == '__main__':
    sys.exit(main())
