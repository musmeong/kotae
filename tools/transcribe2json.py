"""Hand-transcribed book -> tools/<book>.extracted.json + tools/expl/<book>/src.txt (then run build.py).

Usage: python tools/transcribe2json.py <book-id>

Book metadata: tools/src/<book>/book.json, e.g.
    {"title": "My Book N3", "author": "Author / Publisher", "level": "N3",
     "types": {"dochira": {"tag": "正しいほう", "id": "Pilih yang benar", "jp": "...", "how": "..."}}}
("types" is optional: book-level question types on top of Kotae's built-ins.)

Source files: tools/src/<book>/*.txt, read in name order (name them so they sort in book order):

    % section v 文字・語彙 | Kosakata          tab
    % part v1 問題1 漢字読み                  group of sets inside the tab
    % set v1-1 練習                           one practice set
    % passage g3-1p 文章 3-1                   reading text, until "% end"
    I: intro line   C: centred title   P: paragraph   R: right-aligned   IMG: file
    % end

    @v1-1 kanji p46 [n=1]          (p0 = page unknown) [passage=g3-1p] [audio=01.mp3] [img=x.png]
    Q: ここが大事な[場面]だ。
    O: じょうめん | じょめん | ばめん | ばあめん
    A: 3
    R: 3214            (★ questions: order of the four pieces; A must be the piece in the ★ slot)
    S: script line     (listening; repeatable)
    J: own instruction line, e.g. a note about a misprint in the book (-> q.ins)
    T: translation  W: why the key is right  1:-4: a note per option ("Benar." on the right one)

Markup in Q/O/S/P: {漢字|かんじ} = furigana, [..] = underline, ＿＿ = blank, {_} = ★-question slot,
{★} = the ★ slot, 〔3〕 = numbered cloze slot in a passage, " / " = line break.
Pictures: data/img/<book>/ (img=...). Audio: data/audio/<book>/ (audio=...).
"""
import glob, html, json, os, re, sys

HERE = os.path.dirname(os.path.abspath(__file__))
if len(sys.argv) < 2:
    sys.exit('usage: python tools/transcribe2json.py <book-id>')
BOOK = sys.argv[1]
IMG = f'data/img/{BOOK}/'
AUD = f'data/audio/{BOOK}/'
META = json.load(open(os.path.join(HERE, 'src', BOOK, 'book.json'), encoding='utf-8'))
# question types index.html knows (TYPES there); anything else must be declared in book.json "types"
BUILTIN = {'kanji', 'hyouki', 'bunmyaku', 'iikae', 'youhou', 'bunpou', 'star', 'cloze', 'dokkai', 'erabu', 'yomi',
           'kaki', 'maru', 'setsumei', 'gokei', 'narabe', 'kiku', 'kadai', 'point', 'gaiyou', 'hatsuwa', 'sokuji'}
TYPES = META.get('types', {})


def markup(s):
    s = html.escape(s.strip(), quote=False)
    s = s.replace('{_}', '<span class="slot"></span>').replace('{★}', '<span class="slot star">★</span>')
    s = re.sub(r'\{([^|{}]+)\|([^{}]+)\}', r'<ruby>\1<rt>\2</rt></ruby>', s)
    s = re.sub(r'\[([^\]]+)\]', r'<u>\1</u>', s)
    s = re.sub(r'＿+', '<span class="blank"></span>', s)
    s = re.sub(r'〔(\d+)〕', r'<span class="slot num">\1</span>', s)
    # second box of a two-part blank (book prints 2-a … 2-b): fixed label; the main 〔2〕 box holds the answer
    s = re.sub(r'〔(\d+)-b〕', r'<span class="slot num" data-part="b">\1-b</span>', s)
    return s.replace(' / ', '<br>')


def img_tag(f, alt=''):
    return (f'<img src="{IMG}{f}" alt="{html.escape(alt)}" loading="lazy" '
            'style="display:block;width:100%;height:auto;margin:8px 0;border-radius:10px;background:#fff">')


def parse():
    data = dict(id=BOOK, title=META['title'], author=META.get('author', ''), level=META.get('level', 'N3'),
                types=TYPES, passages={}, sections=[])
    expl, errors = [], []
    sec = part = st = cur = psg = None
    seen = set()
    for path in sorted(glob.glob(os.path.join(HERE, 'src', BOOK, '*.txt'))):
        fn = os.path.basename(path)
        for no, raw in enumerate(open(path, encoding='utf-8'), 1):
            line = raw.rstrip('\n')
            if not line.strip() or line.startswith('#'):
                continue
            where = f'{fn}:{no}'
            if line.startswith('% '):
                kw, _, rest = line[2:].partition(' ')
                pid, _, title = rest.partition(' ')
                cur = None
                if kw == 'section':
                    title, _, sub = title.partition(' | ')
                    sec = next((s for s in data['sections'] if s['id'] == pid), None)
                    if not sec:
                        sec = dict(id=pid, title=title, parts=[])
                        if sub:
                            sec['sub'] = sub
                        data['sections'].append(sec)
                elif kw == 'part':
                    part = next((p for p in sec['parts'] if p['id'] == pid), None)
                    if not part:
                        part = dict(id=pid, title=title, sets=[])
                        sec['parts'].append(part)
                elif kw == 'set':
                    st = dict(id=pid, label=title, pages=[], qs=[])
                    part['sets'].append(st)
                elif kw == 'passage':
                    psg = dict(label=title, html='')
                    data['passages'][pid] = psg
                elif kw == 'end':
                    psg = None
                else:
                    errors.append(f'{where}: bad directive {line[:40]}')
                continue
            if psg is not None:
                k, _, v = line.partition(':')
                v = v.strip()
                if k == 'I':
                    psg['intro'] = psg.get('intro', '') + markup(v)
                elif k == 'IMG':
                    psg['html'] += f'<p class="img">{img_tag(v)}</p>'
                elif k in ('P', 'C', 'R'):
                    cls = {'P': '', 'C': ' class="c"', 'R': ' class="r"'}[k]
                    psg['html'] += f'<p{cls}>{markup(v)}</p>'
                else:
                    errors.append(f'{where}: bad passage line {line[:40]}')
                continue
            m = re.match(r'^@(\S+)\s+(\w+)\s+p(\d+)((?:\s+\w+=\S+)*)\s*$', line)
            if m:
                qid, typ, page, kv = m.group(1), m.group(2), int(m.group(3)), m.group(4)
                if qid in seen:
                    errors.append(f'{where}: duplicate {qid}')
                seen.add(qid)
                if st is None:
                    errors.append(f'{where}: question before any set')
                    continue
                cur = dict(id=qid, n=len(st['qs']) + 1, kind='star' if typ == 'star' else 'mc', type=typ)
                if page:                                    # p0 = page not in the scan (問題3・5 聴解)
                    cur['page'] = page
                for k, v in re.findall(r'(\w+)=(\S+)', kv):
                    cur[k] = int(v) if k == 'n' else v
                st['qs'].append(cur)
                if page and page not in st['pages']:
                    st['pages'].append(page)
                expl.append(f'@{qid}')
                continue
            k, _, v = line.partition(':')
            if cur is None or k not in ('Q', 'O', 'A', 'R', 'S', 'J', 'T', 'W', '1', '2', '3', '4'):
                if cur is not None and not re.match(r'^[A-Z0-9]:', line) and expl and not expl[-1].startswith('@'):
                    expl.append(line)                       # continuation of T/W/1-4
                    continue
                errors.append(f'{where}: bad line {line[:50]}')
                continue
            v = v.strip()
            if k == 'Q':
                cur['stem'] = (cur['stem'] + '<br>' if 'stem' in cur else '') + markup(v)
            elif k == 'O':
                cur['opts'] = [markup(o) for o in v.split(' | ')]
            elif k == 'A':
                cur['ans'] = int(v)
            elif k == 'R':
                cur['order'] = v
            elif k == 'S':
                cur['script'] = (cur['script'] + '<br>' if 'script' in cur else '') + markup(v)
            elif k == 'J':
                cur['ins'] = markup(v)
            else:
                expl.append(f'{k}: {v}')
    for sec in data['sections']:
        for part in sec['parts']:
            for st in part['sets']:
                st['pages'].sort()
                for q in st['qs']:
                    qid = q['id']
                    if q['type'] not in BUILTIN and q['type'] not in TYPES:
                        errors.append(f'{qid}: unknown type {q["type"]}')
                    if not q.get('stem') or not q.get('opts') or not q.get('ans'):
                        errors.append(f'{qid}: incomplete')
                        continue
                    if not 1 <= q['ans'] <= len(q['opts']) or len(q['opts']) > 4:
                        errors.append(f'{qid}: answer out of range / too many options')
                    if q['type'] == 'star':
                        slots = re.findall(r'<span class="slot( star)?">', q['stem'])
                        o = q.get('order', '')
                        if len(slots) != 4 or [s for s in slots if s].__len__() != 1 or sorted(o) != list('1234'):
                            errors.append(f'{qid}: ★ needs 4 slots (one ★) and an order like 3214')
                        elif int(o[[i for i, s in enumerate(slots) if s][0]]) != q['ans']:
                            errors.append(f'{qid}: answer {q["ans"]} is not the piece in the ★ slot ({o})')
                    for k, d in (('audio', AUD), ('img', IMG)):
                        if k in q:
                            q[k] = d + q[k]
                            if not os.path.exists(os.path.join(os.path.dirname(HERE), q[k])):
                                errors.append(f'{qid}: missing file {q[k]}')
                    if 'passage' in q and q['passage'] not in data['passages']:
                        errors.append(f'{qid}: unknown passage {q["passage"]}')
    return data, expl, errors


def main():
    data, expl, errors = parse()
    out = os.path.join(HERE, f'{BOOK}.extracted.json')
    json.dump(data, open(out + '.tmp', 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    os.replace(out + '.tmp', out)
    os.makedirs(os.path.join(HERE, 'expl', BOOK), exist_ok=True)
    ep = os.path.join(HERE, 'expl', BOOK, 'src.txt')
    open(ep + '.tmp', 'w', encoding='utf-8').write(f'# generated by transcribe2json.py — edit tools/src/{BOOK}/ instead\n'
                                                    + '\n'.join(expl) + '\n')
    os.replace(ep + '.tmp', ep)
    n = sum(len(st['qs']) for s in data['sections'] for p in s['parts'] for st in p['sets'])
    print(f'{BOOK}: {n} questions in {len(data["sections"])} sections, {len(data["passages"])} passages')
    for e in errors:
        print('ERROR', e)
    return 1 if errors else 0


if __name__ == '__main__':
    sys.exit(main())
