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


def totals(records, outcome):
    result = counters()
    sent = [r for r in records if r.get('outcome') == outcome]
    for record in sent:
        stats = record.get('render_stats') or counters()
        result['hard_cuts'] += stats['hard_cuts']
        for key in CLASSES:
            result['escaped'][key] += stats['escaped'].get(key, 0)
    return dict(result, sent=len(sent))
