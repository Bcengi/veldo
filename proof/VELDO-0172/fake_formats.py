"""Shared fake-event constructors. Frozen defaults are independent of the comparison capture.

Complete normal fixtures before their suites deliberately perturb them. The executable carries this
code and its defaults, so contained runs need no access to the repository's proof directory.
"""
import copy
import json
from pathlib import Path

TEMPLATES = json.loads((Path(__file__).resolve().parent / 'fake_templates.json').read_text())


def complete_event(event):
    event = copy.deepcopy(event)
    name = event.get('type')
    if name in ('system', 'result'):
        name += '/' + event.get('subtype', '')
    template = TEMPLATES['claude'].get(name) or TEMPLATES['codex'].get(name)
    if template is None:
        return event
    if name == 'item.completed' and (event.get('item') or {}).get('type') != 'agent_message':
        return event

    def fill(value, defaults, path=()):
        if isinstance(value, dict) and isinstance(defaults, dict):
            for key, default in defaults.items():
                if path == ('modelUsage',):
                    for item in value.values():
                        fill(item, default, path + ('*',))
                    break
                # These are deliberately absent in non-subscription logins and no-reset limit fixtures.
                if key not in value and (path == ('response', 'response', 'account') and key != 'email'
                                         or key == 'resetsAt'):
                    continue
                if key not in value:
                    value[key] = copy.deepcopy(default)
                else:
                    fill(value[key], default, path + (key,))
        elif isinstance(value, list) and not value and defaults and path[-1:] in (('content',), ('plugins',), ('agents',)):
            value.extend(copy.deepcopy(defaults))
    fill(event, template)
    if name == 'assistant':
        event['message']['usage'].pop('server_tool_use', None)
    return event


def live_step(fn):
    def build(*args, **kwargs):
        step = fn(*args, **kwargs)
        return dict(step, line=complete_event(step['line']))
    return build


def embed(source):
    """Put just the event constructor and its frozen defaults inside a fake executable."""
    import inspect
    prelude = ('import copy\nTEMPLATES = ' + repr(TEMPLATES) + '\n' + inspect.getsource(complete_event) + '\n')
    first, rest = source.split('\n', 1)
    return first + '\n' + prelude + rest
