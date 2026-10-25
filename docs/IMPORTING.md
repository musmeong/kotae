# Importing a book into Kotae

This guide is written for an AI coding assistant (Claude Code, Codex, Cursor…) asked to "import my book into
Kotae", and for humans who want to do it by hand. Follow the steps in order. The demo book in
`tools/src/demo-n3/` is a complete, working example of every format below.

## Ground rules

1. **Never commit book content.** Questions, scans, audio, covers and explanations of a real book stay local.
   `.gitignore` already excludes `data/*`, `tools/src/*`, `tools/expl/*`, `tools/*.extracted.json`,
   `tools/*.keys.json` (except the demo). Don't weaken it, and never push a user's book anywhere.
2. **Never commit `local/gemini-keys.js`** or print the keys in it.
3. **Use the user's resources as they are.** Don't downsample audio (no mono, no lower bitrate, no re-encode),
   don't shrink or recompress images, don't render scans at a lower resolution. Copy bytes; cut images from
   the native pixels. If a change would lower quality, ask first.
4. **Agree on the scope before transcribing.** Show the user the book's structure (tabs, parts, sets, number of
   questions) and which parts you will import. For a big book, do one part, let the user check it, then go on.
5. **Explanations are your own words**, in the language of the user (the UI is Indonesian, so Indonesian unless
   the user asks otherwise). Don't copy the book's own commentary.
6. **The answer key is typed separately** from the book's answer pages and checked by `tools/audit.py`. Your own
   solving must agree with the book's key; where they differ, look again; if the book is wrong, record an
   erratum (see below).
7. AI features in the app run **only on a user click**. Don't add automatic AI calls.

## Step 1: read the PDF

```bash
pip install pymupdf
```

- Check for a usable text layer: `page.get_text()` on a few pages. Many scanned workbooks have none, or an OCR
  layer that is garbage for Japanese. If the text is unreliable, transcribe by reading the page images.
- For scans, extract the embedded page images at their native resolution instead of rendering:

  ```python
  import io, pymupdf
  from PIL import Image
  doc = pymupdf.open("book.pdf")
  xref = doc[10].get_images(full=True)[0][0]
  img = Image.open(io.BytesIO(doc.extract_image(xref)["image"]))   # rotate losslessly with transpose() if needed
  ```

  Two-page spreads: split at the gutter (the darkest vertical band near the middle).
- Read at a size where furigana and small print are clear. **Similar-looking kanji in options** (待/侍, 輪/輸,
  末/未, 濯/擢…) need a closer look: crop the option line from the full-resolution page and enlarge it 4–5×.
  Books sometimes misprint two identical options; note those.
- Find the answer pages (解答, 正答, こたえ…) and their page numbers.

## Step 2: plan the structure

Mirror the book:

- **section** = a tab (e.g. 文字・語彙, 文法, 読解, 聴解, 模擬試験)
- **part** = a group inside the tab (e.g. 問題1 漢字読み)
- **set** = one practice block the user does in one go (a page, a 練習, a day)
- **question id** = `<group>-<n>`, where the group (the part before `-`) is also the key used in the answer-key
  file. Keep ids unique within the book, and preferably across books (prefix them if two books could clash).

Pick a book id like `try-n3`, `bio-grade10` (lowercase, digits, dashes).

## Step 3: write the source files

`tools/src/<book>/book.json`:

```json
{
  "title": "My Workbook N3 — Bunpou, Goi",
  "author": "Author / Publisher",
  "level": "N3",
  "types": {
    "dochira": { "tag": "正しいほう", "id": "Pilih yang benar",
                 "jp": "文中の（　　）から正しいほうをえらびなさい。",
                 "how": "Pilih bentuk yang benar dari dua pilihan dalam kurung." }
  }
}
```

`title` is the readable title the app shows (romaji for Japanese books); the original title goes into
`data/books.js` as `jp`. `types` is optional (see question types below).

`tools/src/<book>/*.txt` are read **in file-name order**, so name them in book order (`1v.txt`, `2g.txt`,
`3r.txt`, or `01-…`, `02-…`). Lines starting with `#` are comments.

### Structure lines

```text
% section v 文字・語彙 | Kosakata      tab id, title | subtitle
% part v1 問題1 漢字読み              part id, title
% set v1-1 練習                       set id, label (e.g. 練習 ①〜⑯)
% passage r1p 図書館からのお知らせ     passage id, label; lines until "% end"
I: intro line (instruction above the text)
C: centred line
P: paragraph
R: right-aligned line
IMG: picture.png                     a picture inside the passage (from data/img/<book>/)
% end
```

### A question

```text
@v1-1 kanji p12
Q: {駅|えき}の[改札]で{友|とも}だちを{待|ま}っている。
O: かいざつ | かいさつ | がいさつ | かいさく
A: 2
T: Aku sedang menunggu teman di gerbang tiket stasiun.
W: **改札（かいさつ）** = gerbang tiket. 札 dibaca さつ (tidak bersuara).
1: かいざつ — さつ tidak bersuara.
2: かいさつ. Benar.
3: がいさつ — かい tidak bersuara.
4: かいさく — 札 dibaca さつ, bukan さく.
```

- Header: `@<id> <type> p<page>`, then optional `key=value` pairs:
  `passage=<pid>`, `n=<number>` (number shown/used for cloze slots), `audio=<file>` (in `data/audio/<book>/`),
  `t=<seconds>` (start time inside the audio file), `img=<file>` (in `data/img/<book>/`).
  `p0` = no page number.
- `Q:` stem (several `Q:` lines are joined with a line break).
- `O:` options separated by ` | ` (2–4 options).
- `A:` the number of the correct option.
- `R:` ★ questions only: the order of the pieces, e.g. `2143`.
- `S:` listening script line (repeatable; shown after answering).
- `J:` replaces the instruction line for this question. Use it for notes such as a misprint in the book.
- Explanation: `T:` translation, `W:` why the key is right, `1:`–`4:` one note per option.
  - The note of the correct option must contain **`Benar.`** (the audit checks this).
  - `**text**` becomes bold. A line without a prefix continues the previous field.
  - ★ questions don't need per-option notes; put the full sentence and the order in `W:`.

### Markup (in Q, O, S, P lines)

| Write | Meaning |
|---|---|
| `{漢字|かんじ}` | furigana |
| `[改札]` | underline (the target word) |
| `＿＿` | an empty blank; a two-blank option is written `A／B` |
| `{_}` and `{★}` | the four slots of a ★ question, exactly one `{★}` |
| `〔3〕` | numbered box inside a passage (cloze); `〔2-b〕` = second box of a two-part blank |
| ` / ` | line break |

⚠ Don't write `〔1〕から〔5〕` in a passage intro: it becomes live boxes. Write `1から5`.

### Built-in question types

| type | tag | use for |
|---|---|---|
| `kanji` | 漢字読み | reading of an underlined word |
| `hyouki` | 表記 | kanji for an underlined kana word |
| `bunmyaku` | 文脈規定 | word that fits the blank |
| `iikae` | 言い換え類義 | closest meaning to the underlined part |
| `youhou` | 用法 | which sentence uses the word correctly (`Q:` = the word, options = sentences with `[word]`) |
| `bunpou` | 文法形式 | grammar form for the blank |
| `star` | 並べ替え ★ | put 4 pieces in order, answer = piece in ★ |
| `cloze` | 文章の文法 | a numbered box in a passage (`passage=… n=…`, `Q: 〔n〕`) |
| `dokkai` | 読解 | question about a passage |
| `erabu` | れんしゅう | pick the right one of two (options labelled a/b) |
| `yomi` / `kaki` | 読み / 書き | pick the reading / the kanji |
| `maru` | ○× | true/false about a passage |
| `setsumei`, `gokei` | 説明, 語形成 | word for a definition, word formation |
| `narabe` | 並べ替え | tap the pieces in order; needs `ans` = `order` = the order string, so only from a custom converter (the text format doesn't support it yet) |
| `kiku`, `kadai`, `point`, `gaiyou`, `hatsuwa`, `sokuji` | 聴解 | listening (with `audio=`, `S:` script) |

Anything else (or a different instruction for one of these) goes into `book.json` → `types`:
`tag` (short label), `id` (name in the UI language), `jp` (instruction line), `how` (one-line hint),
optional `"ab": 1` to label options a/b. This is also how non-Japanese books define their own types.

### Listening and pictures

- Audio files go to `data/audio/<book>/`. Copy them byte for byte. If one track holds several questions, either
  point several questions at the same file with `t=` start times, or cut with `ffmpeg -ss … -to … -c copy`
  (no re-encode). Browsers can't play WMA; convert those to FLAC (lossless).
- Pictures go to `data/img/<book>/`, cropped from the native scan pixels and saved as PNG.
- Covers (optional) go to `data/covers/<book>.jpg|png|webp`: the embedded cover image, untouched.

## Step 4: the answer key

Type the book's answer pages into `tools/<book>.keys.json`, **without looking at your source files**:

```json
{
  "v1": [2, 3, 4, 1],
  "g3": ["慣れる", "そう", "開いて"],
  "_errata": { "n1-29": { "printed": 4, "correct": 1, "why": "key prints 4, the book's own explanation is about option 1" } }
}
```

- One list per group (the id prefix before `-`), in question order.
- A number = option number. Text = the answer as printed (useful for two-choice exercises whose key shows the
  word, not a number).
- `_errata`: the book's key is wrong. The question gets the correct answer plus a `J:` line explaining the
  misprint; the audit checks both.

## Step 5: build and audit

```bash
python tools/transcribe2json.py <book>   # errors name the file and line
python tools/build.py <book>             # reports questions without explanations
python tools/audit.py <book>             # must print "0 problems"
```

Then prove the audit works (positive control): copy the keys file, change three answers, and run
`KOTAE_KEYS=<copy> python tools/audit.py <book>` (PowerShell: `$env:KOTAE_KEYS="<copy>"`). All three must be
reported. Delete the copy.

## Step 6: register the book

Add an entry to `data/books.js`:

```js
{
  id: 'my-book',
  title: 'Readable Title N3',          // romaji for Japanese books
  jp: '原題 N3',                        // original title (tooltip); optional
  author: 'Author / Publisher',
  short: 'Short',                      // shown on the spine when there is no cover
  level: 'N3',
  file: 'data/my-book.js',
  v: 1,                                // bump after every rebuild (browser cache)
  count: 640,                          // number of questions
  color: ['#45b8ff', '#7444d6'],       // spine gradient
  cover: 'data/covers/my-book.jpg',    // optional
  blurb: 'One line about what is inside.'
}
```

## Step 7: check it in the app

Open `index.html`, go through the new book, and look at every kind of question: furigana, underlines, ★ slots,
cloze boxes, passages, pictures, audio, the explanation of each option, and a phone-width window (375 px).

Answering every question quickly (paste in the browser console on the page). It writes fake answers into the
browser's progress, so **back up first and restore afterwards with a full reload**:

```js
const backup = localStorage.getItem('kotae:v1');            // 1. back up
const sleep = ms => new Promise(r => setTimeout(r, ms));
const BOOK = 'my-book';
location.hash = '#/b/' + BOOK; await sleep(800);
const D = window.KOTAE_DATA[BOOK], problems = [];
for (const st of D.sections.flatMap(s => s.parts.flatMap(p => p.sets))) {
  location.hash = `#/s/${BOOK}/${st.id}`; await sleep(300);
  for (const q of st.qs) {
    for (let k = 0; k < 30 && document.querySelector('.qnum')?.textContent != String(q.n); k++) await sleep(40);
    if (document.querySelectorAll('.opts button.opt').length !== q.opts.length) problems.push(q.id + ' buttons');
    document.querySelector(`.opts button[data-pick="${q.ans}"]`)?.click(); await sleep(60);
    if (!document.querySelector('#exwrap .verdict.ok')) problems.push(q.id + ' not ok');
    document.querySelector('[data-act="next"]')?.click(); await sleep(40);
  }
}
console.log(problems);
backup === null ? localStorage.removeItem('kotae:v1') : localStorage.setItem('kotae:v1', backup);
location.reload();                                          // 2. restore + full reload
```

Restoring without a full reload is not enough: the open page keeps the fake answers in memory and writes them
back on the next click.

## Done checklist

- [ ] `audit.py` prints 0 problems, and the positive control catches the changed keys.
- [ ] Every question has `T`, `W` and a note per option; the right option's note says `Benar.`
- [ ] Misprints in the book are noted with `J:` (and `_errata` when the printed key is wrong).
- [ ] Audio and pictures are the original files or native-pixel crops.
- [ ] The book is registered in `data/books.js` with the right `count` and a bumped `v`.
- [ ] Clicked through in the app, desktop and phone width; the user's progress was restored.
- [ ] Nothing from the book is staged in git (`git status` shows no `data/<book>.js`, `tools/src/<book>/` …).

## Data format reference

`tools/build.py` writes `data/<book>.js`:

```js
window.KOTAE_DATA = window.KOTAE_DATA || {};
KOTAE_DATA["my-book"] = {
  id, title, author, level,
  types: { <type>: { tag, id, jp, how, ab? } },          // book-level question types (optional)
  passages: { <pid>: { label, intro?, html } },           // html: <p>…</p> with <ruby>, <span class="slot num">3</span>
  sections: [{ id, title, sub?, mock?, parts: [{ id, title, sets: [{ id, label, pages: [12, 13], qs: [{
    id, n, type, page?,
    stem, opts: [html, …], ans,                            // ans: 1-based option number
    alt?: [n, …],                                           // other accepted options
    order?: "2143",                                         // ★ / narabe
    passage?, audio?, t?, img?, script?, ins?,
    ex: { tr, why, opt: [note1, note2, note3, note4] }
  }] }] }] }]
};
```

If a book is easier to convert another way (a text-layer PDF, a CSV, an existing app export), write your own
converter that produces this structure, then reuse `build.py` and `audit.py`. Set `mock: true` on a section whose
page numbers belong to a separate test booklet (the app then says "Buklet ujian hlm.").
