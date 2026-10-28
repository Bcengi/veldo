"""VELDO-0143 round 6: control_project_proposal.correction_problems against one module, with the suite's two
identities, over every claim DECISIONS entries 24 and 26 make. Each case is judged; nothing is printed unjudged.

    guarantee  words with a negator anywhere: no reading (16: every shown identity and visibility, every reading)
               that sets or keeps a value the words name settles; words with none: exactly the listed readings
               settle (`want`); a kept value is refused wherever the words name any value of its field.
    refusal    an honest correction the rule refuses by choice (DECISIONS 26): the reading he means is refused.
    limit      a reading the rule lets through that he may not mean: it settles, as recorded.

Prints one JSON line per case and a summary; exits 1 when any case is not as recorded. Not a gate result.

    python3 proof/VELDO-0143/round6/phrasings.py <path to control_project_proposal.py>
"""
import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location('v143_phrasings6', sys.argv[1])
PP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PP)
RECORDS = [{'id': 'personal', 'label': 'Personal'}, {'id': 'bcengi', 'label': 'Bcengi'}]
IDS, VIS = ('personal', 'bcengi'), ('private', 'public')
VALUES = IDS + VIS


def problems(shown, reading, words, records=RECORDS, project=('x', 'x')):
    return PP.correction_problems(
        {'project': project[0], 'identity': shown[0], 'remote': {'visibility': shown[1]}, 'mode': 'create'},
        {'project': project[1], 'identity': reading[0], 'visibility': reading[1], 'mode': 'create'}, words, records)


def negator(words):
    """The module's own answer, where it has one (the round-5 module has none: None)."""
    return PP.negates(words) if hasattr(PP, 'negates') else None


def settling(words):
    return sorted('%s/%s->%s/%s' % (si, sv, ri, rv) for si in IDS for sv in VIS for ri in IDS for rv in VIS
                  if not problems((si, sv), (ri, rv), words))


def said(words):
    """The values the words name, anywhere in them (independent of the module's reading)."""
    return {v for v in VALUES if v in words.lower()}


# Words with a negator: the round 3, 4 and 5 reviews' phrasings, and the forms the round 6 rule names.
NEGATED = [
    'not under bcengi please, and keep it private, not public', 'not under bcengi, use personal', 'not bcengi',
    'Keep it private, not public.', 'Not under bcengi.', "don't host it publicly", 'neither personal nor bcengi',
    "don't use bcengi and personal", "don't use bcengi and use personal", 'dont use bcengi or personal',
    "don't use bcengi, and personal", 'it cannot be public', 'dont make it public', 'nothing public please',
    'neither public', 'except public', 'other than public', 'anything but public', 'public? no', 'it wont be public',
    'cant be public', 'didnt want it public', 'avoid public', 'avoid bcengi', 'cannot be bcengi', 'bcengi? no',
    'nothing bcengi-owned', 'no, bcengi', 'bcengi not personal', 'use personal and not bcengi',
    'not public!', 'not public, thanks', 'no bcengi', 'use personal (not bcengi)', 'not-public',
    'not-bcengi please, personal', 'not\npublic', 'public!? no', 'public?! no way', 'public. No.',
    "don't make it public and keep it private", "keep it private and don't make it public",
    'public, no', 'public - no', 'public: no way', 'public is wrong', 'none of it public', 'skip public',
    'nope, public is wrong', 'not only private but public', 'no rush make it public', 'not not public',
    'not_public', 'non-public', 'nonpublic', 'nonpublic... no', 'unpublic? none', 'public\u2019s a no', 'don\u2019t make it public', 'isn`t public',
    'nicht public', 'kein public', '\u043d\u0435 public', 'make it public instead of private', 'rather than bcengi, personal',
    'drop bcengi, use personal', 'remove public', 'stop: public', 'I hate public', 'forget bcengi',
    'public would be a mistake', 'against public', 'nah public',
]
# Words with no negator: exactly these readings settle.
PLAIN = {
    'use personal': ['bcengi/private->personal/private', 'bcengi/public->personal/public'],
    'make it private': ['bcengi/public->bcengi/private', 'personal/public->personal/private'],
    'use personal and make it private': ['bcengi/public->personal/private'],
    'Use personal. Keep it private.': ['bcengi/public->personal/private'],
    'Make it public.': ['bcengi/private->bcengi/public', 'personal/private->personal/public'],
    'put it under Bcengi, call it x, and make it public': ['personal/private->bcengi/public'],
    'use personal\nand make it private': ['bcengi/public->personal/private'],
    'personal please': ['bcengi/private->personal/private', 'bcengi/public->personal/public'],
    'call it x-two': ['bcengi/private->bcengi/private', 'bcengi/public->bcengi/public',
                      'personal/private->personal/private', 'personal/public->personal/public'],
}
# Honest corrections refused by choice (DECISIONS 26): (shown, the reading he means, words).
REFUSED = [
    (('personal', 'public'), ('personal', 'private'), 'Keep it private, not public.'),
    (('bcengi', 'private'), ('personal', 'private'), 'not under bcengi, use personal'),
    (('personal', 'private'), ('bcengi', 'private'), 'no, bcengi'),
    (('bcengi', 'private'), ('personal', 'private'), 'use personal instead of bcengi'),
    (('personal', 'private'), ('personal', 'public'), 'make it public, I don\'t mind'),
    (('personal', 'private'), ('personal', 'public'), 'no rush, make it public'),
    (('bcengi', 'public'), ('bcengi', 'private'), 'keep bcengi but make it private'),
    (('personal', 'private'), ('personal', 'private'), 'keep it private'),
    (('bcengi', 'private'), ('bcengi', 'private'), 'call it personal-site'),
    (('personal', 'private'), ('personal', 'private'), 'call it public-api'),
]
# A short identity word refuses more than he means: shown `me`, kept, words that name nothing he chose.
SHORT = [{'id': 'me', 'label': 'Me'}, {'id': 'bcengi', 'label': 'Bcengi'}]
# What passes that he may not mean: (shown, reading, words, project shown and read).
LIMITS = [
    (('personal', 'private'), ('personal', 'public'), 'public would be awful', ('x', 'x')),
    (('personal', 'private'), ('personal', 'public'), 'steer clear of public', ('x', 'x')),
    (('personal', 'private'), ('personal', 'public'), 'yeah right, public', ('x', 'x')),
    (('personal', 'private'), ('personal', 'public'), 'public is a terrible idea', ('x', 'x')),
    (('bcengi', 'private'), ('personal', 'private'), 'personal? nunca', ('x', 'x')),
    (('personal', 'private'), ('personal', 'private'), 'call it reef-watch', ('x', 'x')),
    (('bcengi', 'private'), ('personal', 'private'), 'impersonal', ('x', 'x')),
]

wrong, out = 0, []
for words in NEGATED:
    names = said(words)
    bad = [c for c in settling(words) if c.split('->')[1].split('/')[0] in names or c.split('->')[1].split('/')[1] in names]
    ok = bool(names) and negator(words) is not False and not bad
    out.append({'kind': 'guarantee', 'words': words, 'negator': negator(words), 'names': sorted(names),
                'settling_with_a_named_value': bad, 'as_recorded': ok})
for words, want in PLAIN.items():
    got = settling(words)
    out.append({'kind': 'guarantee', 'words': words, 'negator': negator(words), 'settling': got,
                'as_recorded': got == sorted(want) and not negator(words)})
for si in IDS:
    for sv in VIS:
        for words in ('use %s' % [i for i in IDS if i != si][0], 'make it %s' % [v for v in VIS if v != sv][0],
                      'use %s' % si, 'make it %s' % sv):
            p = problems((si, sv), (si, sv), words)
            field = 'identity' if words.startswith('use') else 'visibility'
            out.append({'kind': 'guarantee', 'words': words, 'shown_kept': '%s/%s' % (si, sv), 'problems': p,
                        'as_recorded': 'invalid_input:correction:' + field in p})
for shown, reading, words in REFUSED:
    p = problems(shown, reading, words)
    out.append({'kind': 'refusal', 'words': words, 'shown': '/'.join(shown), 'reading': '/'.join(reading),
                'problems': p, 'as_recorded': bool(p)})
p = problems(('me', 'private'), ('me', 'public'), 'make it public, meanwhile', SHORT)
out.append({'kind': 'refusal', 'words': 'make it public, meanwhile', 'identity_word': 'me', 'shown': 'me/private',
            'reading': 'me/public', 'problems': p, 'as_recorded': p == ['invalid_input:correction:identity']})
for shown, reading, words, project in LIMITS:
    p = problems(shown, reading, words, project=project)
    out.append({'kind': 'limit', 'words': words, 'shown': '/'.join(shown), 'reading': '/'.join(reading),
                'problems': p, 'as_recorded': not p})
for line in out:
    wrong += not line['as_recorded']
    print(json.dumps(line))
summary = {'cases': len(out), 'not_as_recorded': wrong,
           'by_kind': {k: sum(1 for x in out if x['kind'] == k) for k in ('guarantee', 'refusal', 'limit')}}
print(json.dumps(summary))
sys.exit(1 if wrong else 0)
