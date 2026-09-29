"""Renderer 1 retained byte for byte in behavior for existing presentation receipts."""
MESSAGE_LIMIT = 4096
PART_LINE_ROOM = 64


def _words(text):
    return ' '.join(str(text).split())


def utf16_units(text):
    """The length Telegram's text limit counts: UTF-16 code units."""
    return len(text.encode('utf-16-le')) // 2


def _chunks(text, room):
    """`text` cut into pieces of at most `room` UTF-16 units, at whitespace where there is any in
    reach. Only the whitespace at a cut is dropped: nothing is truncated."""
    pieces = []
    while utf16_units(text) > room:
        used, cut = 0, 0
        for i, ch in enumerate(text):
            used += utf16_units(ch)
            if used > room:
                break
            cut = i + 1
        space = max(text.rfind(' ', 0, cut), text.rfind('\n', 0, cut))
        at = space if space > 0 else cut
        pieces.append(text[:at].rstrip())
        text = text[at:].lstrip()
    pieces.append(text)
    return pieces


def render(record):
    """The exact bytes shown, as the list of Telegram messages that show them, from the receipt's
    own bound fields: plain text, no markup. A presentation that fits one message is one message.
    A longer one is consecutive messages, each within the platform limit and numbered, the whole
    brief in order across them, and the last carrying the choices and how to answer. Nothing is
    truncated or replaced by a link: the owner reads decisions on Telegram and cannot open links
    there. Raises ValueError when the choices and answer instruction alone do not fit one part."""
    c = record['request']
    budget = ', '.join('%s=%s' % (unit, c['budget'][unit]) for unit in sorted(c['budget']))
    head = ['Veldo needs your %s' % c['kind'].replace('_', ' '),
            'Request: %s' % record['request_id'],
            'Request version: %d' % record['request_version'],
            'Request digest: %s' % record['request_digest'],
            'Presentation version: %d' % record['presentation_version']]
    prior = record.get('supersedes')
    if prior and prior.get('notices'):
        named = ['the notice message %s' % n['message_id'] if n['message_id'] is not None
                 else 'an earlier notice of this request whose delivery is not confirmed' for n in prior['notices']]
        head.append('Supersedes: %s. Only this message can be answered.' % ' and '.join(named))
    elif prior:
        head.append('Supersedes: presentation version %s, message %s. Only this message can be answered.'
                    % (prior['presentation_version'], prior['message_id']))
    head += ['Owner: %s' % c['owner'],
             'Scope: %s' % ', '.join(c['scope']),
             'Deadline: %s' % c['deadline'],
             'Budget: %s' % budget,
             'Subject: %s' % '; '.join('%s %s %s' % (s['kind'], s['ref'], s['digest']) for s in record['subject_digests']),
             'Risk (stated by %s): %s' % (record['framed_by'], _words(record['risk_statement'])),
             'Authority: %s' % record['authority_statement']]
    body = '\n'.join(line.rstrip() for line in head + ['', _words(c['brief'])])
    tail = '\n'.join(['Choices: %s' % ' | '.join(record['choices']),
                      'Answer by replying to this message: <choice>: <your reason>'])
    whole = body + '\n\n' + tail
    if utf16_units(whole) <= MESSAGE_LIMIT:
        return [whole]
    room = MESSAGE_LIMIT - PART_LINE_ROOM
    if utf16_units(tail) > room:
        raise ValueError('presentation_too_long')
    pieces = _chunks(body, room)
    if utf16_units(pieces[-1] + '\n\n' + tail) <= room:
        pieces[-1] = pieces[-1] + '\n\n' + tail
    else:
        pieces.append(tail)
    return ['Part %d of %d, presentation version %d\n%s' % (i + 1, len(pieces), record['presentation_version'], piece)
            for i, piece in enumerate(pieces)]


