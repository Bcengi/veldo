"""VELDO-0143 round 7: control_project_proposal.correction_problems against one module, with the suite's two
identities, over every phrasing of the round 3 to 6 reviews. Round 7's claim: a correction never changes the
identity or the visibility, so for every phrasing exactly the four readings that keep what he was shown settle
(16 readings each: every shown identity and visibility, every reading of the PM's), and no other.

Works on the round-6 module (correction_problems takes the configured identities) and the round-7 one (it does
not). Prints one JSON line per phrasing and a summary; exits 1 when any phrasing settles another reading. Not a
gate result.

    python3 proof/VELDO-0143/round7/phrasings.py <path to control_project_proposal.py>
"""
import importlib.util
import inspect
import json
import sys

spec = importlib.util.spec_from_file_location('v143_phrasings7', sys.argv[1])
PP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PP)
RECORDS = [{'id': 'personal', 'label': 'Personal'}, {'id': 'bcengi', 'label': 'Bcengi'}]
IDS, VIS = ('personal', 'bcengi'), ('private', 'public')
ROUND6 = len(inspect.signature(PP.correction_problems).parameters) == 4


def shown(si, sv):
    entries = [{'identity': i, 'mode': 'create', 'adoption': None, 'directory': '/p/' + i,
                'remote': {'name': 'x', 'owner': i, 'url': 'u', 'visibility': sv}} for i in IDS]
    if ROUND6:
        return {'project': 'x', 'identity': si, 'remote': {'visibility': sv}, 'mode': 'create'}
    return dict(next(e for e in entries if e['identity'] == si), project='x', offered=entries)


def problems(si, sv, ri, rv, words):
    terms = {'project': 'x', 'identity': ri, 'visibility': rv, 'mode': 'create'}
    if ROUND6:
        return PP.correction_problems(shown(si, sv), terms, words, RECORDS)
    return PP.correction_problems(shown(si, sv), terms, words)


KEPT = sorted('%s/%s->%s/%s' % (i, v, i, v) for i in IDS for v in VIS)
PHRASINGS = {
    'round 3': ['not under bcengi please, and keep it private, not public', 'not under bcengi, use personal',
                'not bcengi'],
    'round 4': ['Keep it private, not public.', 'Not under bcengi.', "don't host it publicly",
                'neither personal nor bcengi', "don't use bcengi and personal", "don't use bcengi and use personal",
                'dont use bcengi or personal', 'it cannot be public', 'dont make it public', 'nothing public please',
                'neither public', 'except public', 'other than public', 'anything but public', 'public? no',
                'it wont be public', 'cant be public', 'didnt want it public', 'avoid public', 'avoid bcengi',
                'cannot be bcengi', 'bcengi? no', 'nothing bcengi-owned', 'no, bcengi', 'bcengi not personal'],
    'round 5': ['not public!', 'not public, thanks', 'no bcengi', 'use personal (not bcengi)', 'not-public',
                'not-bcengi please, personal', 'not\npublic', 'public!? no', 'public?! no way', 'public. No.',
                "don't make it public and keep it private", "keep it private and don't make it public", 'not_public',
                'non-public', 'use personal', 'make it private', 'use personal and make it private', 'Make it public.',
                'put it under Bcengi, call it x, and make it public', 'Use personal. Keep it private.'],
    'round 6': ["Personally I'd make it private", "Let's publicly launch later; for now use personal",
                "I'd discuss it privately, but go with bcengi", 'make it private, my email is someone@bcengi.com',
                'like https://github.com/bcengi/shoal but make it private', 'my private account please',
                'not this account', "that's the wrong owner", 'wrong account, use the other one', 'keep it hidden',
                'under my own account', 'the other identity please', 'flip the visibility', 'use BCENGI',
                'use bc\u0435ngi', 'use bc\u0441engi', 'use \uff42cengi', 'n\u043et public', 'no\u200bt public',
                '\uff4e\uff4f\uff54 public', 'don\u02bct make it public', 'don\u2032t make it public',
                'use bc\u00a0engi', 'make it public \u274c', 'make it public \U0001f6ab', 'public lol jk',
                'make it public (kidding)', 'NOT PUBLIC', 'DO NOT make it public', 'never ever public',
                'public, not!', 'public: nah-uh', 'pas de public', 'use personal' + ' filler' * 20000,
                'make it public, no worries', "use personal, I'll remove the old one later",
                "use personal, it's a nonprofit thing", 'use personal, the bcengi one is for work',
                'use personal, please stop asking', 'I know, use personal', 'Personal, private.',
                "use personal and make it private, that's all"],
}
wrong = 0
for review, phrasings in PHRASINGS.items():
    for words in phrasings:
        settles = sorted('%s/%s->%s/%s' % (si, sv, ri, rv) for si in IDS for sv in VIS for ri in IDS for rv in VIS
                         if not problems(si, sv, ri, rv, words))
        ok = settles == KEPT
        wrong += not ok
        print(json.dumps({'review': review, 'words': words if len(words) < 200 else words[:40] + '... (%d characters)'
                          % len(words), 'as_claimed': ok, 'settles_beyond_kept': sorted(set(settles) - set(KEPT)),
                          'kept_refused': sorted(set(KEPT) - set(settles))}, ensure_ascii=True))
total = sum(len(p) for p in PHRASINGS.values())
print(json.dumps({'module': 'round 6' if ROUND6 else 'round 7', 'phrasings': total, 'not_as_claimed': wrong}))
sys.exit(1 if wrong else 0)
