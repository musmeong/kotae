"""Audit a transcribed book: answers vs an answer key typed SEPARATELY from the book's answer pages,
explanation completeness, and the "Benar." marker on the keyed option.

Usage: python tools/audit.py <book-id>     (after transcribe2json.py; reads tools/<book>.extracted.json + expl)
Key file tools/<book>.keys.json: one list per question group (the id prefix before "-": "v1" for v1-1, v1-2 ...)
    {"v1": [3, 1, 4, 2], "g1": ["なって", "合格できる"]}   number = option number, text = answer text as printed
    "_errata": {"v1-3": {"printed": 2, "correct": 4, "why": "..."}}   the book's key is misprinted: the question
               must carry the correct answer plus a J: note saying so
Positive control: KOTAE_KEYS=<copy with a few keys changed> python tools/audit.py <book> must report them.
"""
import json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import build

if len(sys.argv) < 2:
    sys.exit('usage: python tools/audit.py <book-id>')
BOOK = sys.argv[1]
data = json.load(open(os.path.join(HERE, f'{BOOK}.extracted.json'), encoding='utf-8'))
keys = json.load(open(os.environ.get('KOTAE_KEYS', os.path.join(HERE, f'{BOOK}.keys.json')), encoding='utf-8'))
errata = keys.get('_errata', {})
expl = build.load_expl(BOOK)


def plain(s):
    return re.sub(r'<rt>.*?</rt>|<[^>]+>', '', s)


probs, n = [], 0
by_group = {}
for sec in data['sections']:
    for part in sec['parts']:
        for st in part['sets']:
            for q in st['qs']:
                n += 1
                by_group.setdefault(re.match(r'^([a-z]+\d+)-', q['id']).group(1), []).append(q)
for grp, qs in by_group.items():
    want = keys.get(grp)
    if want is None:
        probs.append(f'{grp}: no 解答 row')
        continue
    if len(want) != len(qs):
        probs.append(f'{grp}: {len(qs)} questions, 解答 has {len(want)}')
    for q, w in zip(qs, want):
        got = plain(q['opts'][q['ans'] - 1]) if isinstance(w, str) else q['ans']
        fix = errata.get(q['id'])
        if fix:
            if w != fix['printed']:
                probs.append(f"{q['id']}: errata printed {fix['printed']} but 解答 row has {w}")
            if q['ans'] != fix['correct'] or 'ins' not in q:
                probs.append(f"{q['id']}: errata wants answer {fix['correct']} plus a J: note")
            continue
        if got != w:
            probs.append(f"{q['id']}: answer {got!r} != 解答 {w!r}")
for grp in keys:
    if not grp.startswith('_') and grp not in by_group:
        probs.append(f'{grp}: in 解答 but no questions')
for qid in errata:
    if not any(q['id'] == qid for qs in by_group.values() for q in qs):
        probs.append(f'{qid}: errata for a question that does not exist')
for qs in by_group.values():
    for q in qs:
        e = expl.get(q['id'])
        k = len(q['opts'])
        if not e:
            probs.append(f"{q['id']}: no explanation")
            continue
        if not e.get('tr') or not e.get('why'):
            probs.append(f"{q['id']}: missing T/W")
        if q['type'] == 'star':                     # ★: order is checked by transcribe2json; no per-option notes
            continue
        notes = [e.get(str(i), '') for i in range(1, 5)]
        have = [i for i in range(1, 5) if notes[i - 1]]
        if have != list(range(1, k + 1)):
            probs.append(f"{q['id']}: notes {have} for {k} options")
        marks = [i for i in range(1, 5) if re.search(r'Benar\.', notes[i - 1])]
        if marks != [q['ans']]:
            probs.append(f"{q['id']}: Benar on {marks}, key {q['ans']}")
print(f'{BOOK}: {n} questions audited; {len(probs)} problems')
for p in probs:
    print(' ', p)
sys.exit(1 if probs else 0)
