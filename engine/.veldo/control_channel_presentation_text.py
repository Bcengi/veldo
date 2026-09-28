"""Plain Telegram text, renderer versions and content-free rendering counters (VELDO-0168)."""
import unicodedata

VERSION = 2
CLASSES = ('Cf', 'Cc', 'Zl', 'Zp', 'Zs', 'literal')
CUT = '[cut inside a word, continues in the next part]'
CONTINUED = '[continued]'


def counters():
    return dict(escaped={key: 0 for key in CLASSES}, hard_cuts=0)


def visible(text, stats=None):
    """Normalize CRLF only; escape invisible characters and literal escape introducers once."""
    text = str(text).replace('\r\n', '\n')
    shown = []
    for i, ch in enumerate(text):
        category = unicodedata.category(ch)
        invisible = (category in ('Cf', 'Zl', 'Zp') or category == 'Cc' and ch != '\n'
                     or category == 'Zs' and ch != ' ')
        literal = text.startswith('<U+', i)
        if invisible or literal:
            shown.append('<U+%04X>' % ord(ch))
            if stats is not None:
                stats['escaped']['literal' if literal else category] += 1
        else:
            shown.append(ch)
    return ''.join(shown)


def edges(shown, stats=None):
    """`shown` (already visible) with the spaces and line breaks that begin or end it shown escaped.

    Telegram trims the whitespace at both ends of a message, so a message ending in it would come back
    as other bytes than the receipt binds, and two values differing only there would look alike."""
    start = len(shown) - len(shown.lstrip(' \n'))
    end = len(shown.rstrip(' \n'))
    if end <= start:
        start, end = len(shown), len(shown)
    out = []
    for i, ch in enumerate(shown):
        if (i < start or i >= end) and ch in ' \n':
            out.append('<U+%04X>' % ord(ch))
            if stats is not None:
                stats['escaped'][unicodedata.category(ch)] += 1
        else:
            out.append(ch)
    return ''.join(out)


def message(text, stats=None):
    """One whole Telegram message: every invisible character escaped, and its trimmed ends kept."""
    return edges(visible(text, stats), stats)


def add(stats, more):
    """Add the counters `more` into `stats` (None is no stats kept)."""
    if stats is not None:
        stats['hard_cuts'] += more['hard_cuts']
        for key in CLASSES:
            stats['escaped'][key] += more['escaped'][key]


def totals(records, outcome):
    result = counters()
    sent = [r for r in records if r.get('outcome') == outcome]
    for record in sent:
        stats = record.get('render_stats') or counters()
        result['hard_cuts'] += stats['hard_cuts']
        for key in CLASSES:
            result['escaped'][key] += stats['escaped'].get(key, 0)
    return dict(result, sent=len(sent))
