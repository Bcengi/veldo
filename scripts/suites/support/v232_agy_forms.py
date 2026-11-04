"""VELDO-0232: the stream-json forms the suites' fake agy prints (init, step_update, result), one place for suite
127's fake and suite 128's comparison with the recorded real run (VELDO-0172's rule)."""

CONVERSATION = 'conversation-232'


def init(tools):
    return {'line': {'type': 'init', 'session_id': 'session-232', 'conversation_id': CONVERSATION,
                     'model': 'fixture-model', 'cwd': '/fixture', 'tools': list(tools)}}


def step(index, kind, tool=None, **extra):
    line = {'type': 'step_update', 'conversation_id': CONVERSATION, 'step_index': index, 'step_type': kind,
            'status': 'done'}
    if tool is not None:
        line['tool_info'] = {'name': tool, 'parameters': {'path': 'README'}, 'output': 'fixture'}
    line.update(extra)
    return {'line': line}


def result(inp, out, cache=0, text='done', reason=None):
    line = {'type': 'result', 'conversation_id': CONVERSATION, 'result': text,
            'usage': {'input_tokens': inp, 'output_tokens': out, 'cache_read_tokens': cache}}
    if reason is not None:
        line['finished_reason'] = reason
    return {'line': line}


def form(event):
    """A line's form: its type, its step type, and the names of its fields."""
    return (event.get('type'), event.get('step_type') if event.get('type') == 'step_update' else None,
            tuple(sorted(event)))


def fake_forms(tools):
    """Every form the suites' fake prints."""
    lines = [init(tools), step(0, 'planner_response'), step(1, 'view_file', 'view_file'),
             step(0, 'search_web', 'search_web'), result(1, 1), result(1, 1, reason='error')]
    return {form(item['line']) for item in lines}
