"""VELDO-0143 round 5: control_project_proposal.correction_problems over the phrasings of the round 4 review
(R4-1, R4-2, R4-4) and the limits DECISIONS entry 24 records, against one module, with the suite's two
identities. Prints one line per phrasing: what he was shown, what the PM's reading keeps or changes, his words,
whether the reading should be refused (expected) and the problems the module returns. Not a gate result.

    python3 proof/VELDO-0143/round5/phrasings.py <path to control_project_proposal.py>
"""
import importlib.util
import json
import sys

spec = importlib.util.spec_from_file_location('v143_phrasings', sys.argv[1])
PP = importlib.util.module_from_spec(spec)
spec.loader.exec_module(PP)
RECORDS = [{'id': 'personal', 'label': 'Personal'}, {'id': 'bcengi', 'label': 'Bcengi'}]
REFUSE, SETTLE, LIMIT = 'refused', 'settles', 'limit'
CASES = [
    # R4-1: a final period
    (('personal', 'public'), ('personal', 'public'), 'Keep it private, not public.', REFUSE),
    (('bcengi', 'private'), ('bcengi', 'private'), 'Not under bcengi.', REFUSE),
    (('personal', 'private'), ('personal', 'public'), 'Make it public.', SETTLE),
    (('bcengi', 'private'), ('personal', 'private'), 'Use personal.', SETTLE),
    (('personal', 'public'), ('personal', 'public'), "don't host it publicly", REFUSE),
    # R4-2: both ruled out, or one negated and another affirmed through a bare "and"
    (('bcengi', 'private'), ('personal', 'private'), 'neither personal nor bcengi', REFUSE),
    (('bcengi', 'private'), ('personal', 'private'), "don't use bcengi and personal", REFUSE),
    (('bcengi', 'private'), ('personal', 'private'), "don't use bcengi and use personal", REFUSE),
    (('bcengi', 'private'), ('personal', 'private'), "don't use bcengi and the personal one", REFUSE),
    # R4-4: the negators the review measured, and "? no"
    (('personal', 'public'), ('personal', 'public'), 'it cannot be public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'dont make it public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'nothing public please', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'neither public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'except public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'other than public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'anything but public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'public? no', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'it wont be public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'cant be public', REFUSE),
    (('personal', 'public'), ('personal', 'public'), 'didnt want public', REFUSE),
    (('bcengi', 'private'), ('bcengi', 'private'), 'avoid bcengi', REFUSE),
    (('personal', 'private'), ('personal', 'public'), 'it cannot be public', REFUSE),
    (('personal', 'private'), ('personal', 'public'), 'dont make it public', REFUSE),
    # what his words affirm still settles
    (('personal', 'public'), ('personal', 'private'), 'Keep it private, not public.', SETTLE),
    (('bcengi', 'private'), ('personal', 'private'), 'not under bcengi, use personal', SETTLE),
    (('personal', 'public'), ('personal', 'private'), 'under personal please, keep it private, not public', SETTLE),
    (('personal', 'private'), ('bcengi', 'public'), 'put it under Bcengi, call it x, and make it public', SETTLE),
    (('bcengi', 'private'), ('personal', 'private'), 'use personal and not bcengi', SETTLE),
    (('personal', 'private'), ('bcengi', 'private'), 'bcengi not personal', SETTLE),
    (('bcengi', 'private'), ('personal', 'private'), 'bcengi not personal', REFUSE),
    (('personal', 'private'), ('bcengi', 'private'), 'no, bcengi', SETTLE),
    (('bcengi', 'private'), ('personal', 'private'), 'not bcengi or personal', REFUSE),
    # the limits entry 24 records (what the module does with them is printed, not judged)
    (('personal', 'public'), ('personal', 'public'), 'public, no', LIMIT),
    (('personal', 'public'), ('personal', 'public'), 'public - no', LIMIT),
    (('personal', 'public'), ('personal', 'public'), 'public: no way', LIMIT),
    (('personal', 'public'), ('personal', 'public'), 'public is wrong', LIMIT),
    (('personal', 'public'), ('personal', 'public'), 'none of it public', LIMIT),
    (('personal', 'public'), ('personal', 'public'), 'skip public', LIMIT),
    (('personal', 'public'), ('personal', 'public'), 'nope, public is wrong', LIMIT),
    (('bcengi', 'private'), ('personal', 'private'), "don't use bcengi, and personal", LIMIT),
    (('personal', 'private'), ('personal', 'public'), 'not only private but public', LIMIT),
    (('personal', 'private'), ('personal', 'public'), 'no rush make it public', LIMIT),
]
wrong = 0
for shown, reading, words, expected in CASES:
    problems = PP.correction_problems(
        {'project': 'x', 'identity': shown[0], 'remote': {'visibility': shown[1]}, 'mode': 'create'},
        {'project': 'x', 'identity': reading[0], 'visibility': reading[1], 'mode': 'create'}, words, RECORDS)
    judged = REFUSE if problems else SETTLE
    ok = expected == LIMIT or judged == expected
    wrong += not ok
    print(json.dumps({'shown': '/'.join(shown), 'reading': '/'.join(reading), 'words': words, 'expected': expected,
                      'problems': problems, 'as_expected': ok if expected != LIMIT else None}))
print(json.dumps({'cases': len(CASES), 'not_as_expected': wrong}))
