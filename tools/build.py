"""Merge extracted questions + hand-written explanations into data/<book>.js.

Explanation files: tools/expl/<book>/<anything>.txt, blocks like

    @v1-01-1
    T: terjemahan kalimat
    W: kenapa jawaban benar
    1: catatan pilihan 1
    2: ...

Inline **teks** becomes <b>teks</b>. Lines starting with '#' are comments.
Usage: python tools/build.py <book-id>
"""
import json, os, re, sys, glob, html

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def fmt(s):
    s = html.escape(s.strip(), quote=False)
    return re.sub(r'\*\*(.+?)\*\*', r'<b>\1</b>', s)


def load_expl(book):
    out = {}
    for path in sorted(glob.glob(os.path.join(HERE, 'expl', book, '*.txt'))):
        cur = None
        for raw in open(path, encoding='utf-8'):
            line = raw.rstrip('\n')
            if not line.strip() or line.lstrip().startswith('#'):
                continue
            if line.startswith('@'):
                cur = line[1:].strip()
                if cur in out:
                    print('WARN duplicate explanation', cur, os.path.basename(path))
                out[cur] = {}
                continue
            m = re.match(r'^([TW1-4]):\s?(.*)$', line)
            if not m or cur is None:
                if cur and out[cur]:                       # continuation of previous field
                    k = list(out[cur])[-1]
                    out[cur][k] += '<br>' + fmt(line)
                    continue
                print('WARN bad line', os.path.basename(path), line[:60])
                continue
            k, v = m.groups()
            key = {'T': 'tr', 'W': 'why'}.get(k, k)
            out[cur][key] = fmt(v)
    return out


def main(book):
    data = json.load(open(os.path.join(HERE, f'{book}.extracted.json'), encoding='utf-8'))
    expl = load_expl(book)
    total = have = 0
    seen = set()
    for sec in data['sections']:
        for part in sec['parts']:
            for st in part['sets']:
                for q in st['qs']:
                    total += 1
                    e = expl.get(q['id'])
                    if e:
                        have += 1
                        seen.add(q['id'])
                        q['ex'] = {'tr': e.get('tr', ''), 'why': e.get('why', ''),
                                   'opt': [e.get(str(i), '') for i in range(1, 5)]}
    unknown = sorted(set(expl) - seen)
    if unknown:
        print('WARN explanations for unknown ids:', unknown[:10])
    out = os.path.join(ROOT, 'data', f'{book}.js')
    js = 'window.KOTAE_DATA=window.KOTAE_DATA||{};KOTAE_DATA[%s]=%s;\n' % (
        json.dumps(book), json.dumps(data, ensure_ascii=False, separators=(',', ':')))
    open(out + '.tmp', 'w', encoding='utf-8').write(js)
    os.replace(out + '.tmp', out)
    print(f'{book}: {total} questions, {have} with explanations -> {os.path.relpath(out, ROOT)} ({len(js)//1024} KB)')


if __name__ == '__main__':
    if len(sys.argv) < 2:
        sys.exit('usage: python tools/build.py <book-id>')
    main(sys.argv[1])
