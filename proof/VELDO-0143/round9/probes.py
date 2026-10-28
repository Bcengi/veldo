"""VELDO-0143 round 9: pure-function probes of control_project_proposal against one module.

picks   R8-1: for every set of two or three ids from POOL that fold apart (what control_git_identity.validate
        requires), every mode of each (create or adopt) and every shown identity and visibility, whether two of
        choices() fold alike under control_channel_presentation._fold, and whether a typed creation pick of a
        creation identity matches an offered choice that binds another identity.
words   R8-3: the round 8 review's phrasings, under identity bcengi and project shoal: whether the module's
        nothing-asked words present the message (a word of visibility, a negator, or, from round 9, a word the
        rule has not read).

Prints one JSON line per finding and a summary line; exits 1 when the module folds two choices alike, binds
another identity, or settles a phrasing. Not a gate result.

    python3 -I proof/VELDO-0143/round9/probes.py <directory holding control_project_proposal.py>
"""
import importlib.util
import itertools
import json
from pathlib import Path
import sys

here = Path(sys.argv[1])


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PP = load('v143_probe_proposal', here / 'control_project_proposal.py')
fold = load('v143_probe_presentation', here / 'control_channel_presentation.py')._fold
POOL = ['bcengi', 'bcengi-private', 'bcengi_public', 'bcengi-adopt', 'bcengi-private-adopt', 'x', 'x.private',
        'x-public-private', 'private', 'public', 'adopt', 'accept']
VISIBILITY = getattr(PP, 'AS_ON_REMOTE', None)


def entry(identity, mode, visibility):
    return {'identity': identity, 'mode': mode,
            'remote': {'visibility': VISIBILITY if mode == 'adopt' else visibility}}


collisions, misbinds, layouts = [], [], 0
for size in (2, 3):
    for ids in itertools.combinations(POOL, size):
        if len({fold(i) for i in ids}) != size:
            continue
        for modes in itertools.product(('create', 'adopt'), repeat=size):
            for shown in (None,) + ids:
                for visibility in ('private', 'public'):
                    offered = [entry(i, m, visibility) for i, m in zip(ids, modes)]
                    proposal = {'identity': shown, 'offered': offered,
                                'remote': next((e['remote'] for e in offered if e['identity'] == shown), None)}
                    layouts += 1
                    offered_choices = PP.choices(proposal)
                    folded = [fold(c) for c in offered_choices]
                    if len(set(folded)) != len(folded):
                        collisions.append({'ids': ids, 'modes': modes, 'shown': shown, 'choices': offered_choices})
                        continue
                    picks = PP.picks(proposal)
                    for identity, mode in zip(ids, modes):
                        if mode != 'create':
                            continue
                        for typed_visibility in ('private', 'public'):
                            typed = 'accept %s %s' % (identity, typed_visibility)
                            match = next((c for c in offered_choices if fold(c) == fold(typed)), None)
                            bound = picks.get(match, (identity,))[0] if match else identity
                            if bound != identity:
                                misbinds.append({'ids': ids, 'modes': modes, 'shown': shown, 'typed': typed,
                                                 'bound': bound})
print(json.dumps({'probe': 'picks', 'layouts': layouts, 'collisions': len(collisions), 'misbinds': len(misbinds),
                  'first_collision': collisions[:1], 'first_misbind': misbinds[:1]}))

PHRASINGS = {
    'presented in round 8': ['open source it', 'open-source it', 'in the open', 'visible to all',
                             'make it public-facing', 'privately', 'nobody else should see it'],
    'settled private in round 8 (R8-3)': ['share it with everyone', 'publish it', 'make it opensource', 'OSS please',
                                          'everyone can see it', 'on my github profile for all to see',
                                          'releasing it to the community', 'free software', 'publically'],
    'settled private in round 8, what he asked': ['keep it to ourselves', 'for the team only', 'just for me',
                                                   'keep it confidential', 'restricted access'],
}
words = getattr(PP, 'unread_words', None)
settled = []
for group, tails in PHRASINGS.items():
    for tail in tails:
        text = 'start a new bcengi project called shoal and ' + tail
        unread = words(text, ['shoal', 'bcengi', 'Bcengi']) if words else []
        presented = PP.says_visibility(text) or PP.negates(text) or bool(unread)
        if not presented:
            settled.append(text)
        print(json.dumps({'probe': 'words', 'group': group, 'text': text, 'unread': unread, 'presented': presented}))
for text in ('start a new bcengi project called shoal', 'Start a new project called shoal under Bcengi please',
             'create a repo named shoal for my bcengi account'):
    unread = words(text, ['shoal', 'bcengi', 'Bcengi']) if words else []
    print(json.dumps({'probe': 'words', 'group': 'plain, settles unasked', 'text': text, 'unread': unread,
                      'presented': bool(unread) or PP.says_visibility(text) or PP.negates(text)}))
print(json.dumps({'summary': {'collisions': len(collisions), 'misbinds': len(misbinds), 'phrasings_settled': settled}}))
sys.exit(1 if collisions or misbinds or settled else 0)
