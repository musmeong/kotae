# Kotae — notes for AI coding assistants

Kotae is a single-file quiz app (`index.html`) that turns practice books the user owns into interactive
questions with explanations. The repo contains only the app, the import tools and an original demo book.

- **Importing a book:** follow [docs/IMPORTING.md](docs/IMPORTING.md) step by step. The demo book
  (`tools/src/demo-n3/`, `tools/demo-n3.keys.json`) is the reference example of every format.
- **Never commit book content** (questions, scans, audio, covers, explanations of a real book) and never commit
  `local/gemini-keys.js`. `.gitignore` already excludes them; keep it that way and check `git status` before
  any commit.
- **Use the user's resources as they are**: no audio re-encoding or downsampling, no image downscaling.
- **AI calls only on a user click.** All Gemini calls go through `gemini()` in `index.html`, reachable only from
  the `[data-ai]` and `[data-aiq]` buttons. Don't add automatic calls.
- The UI language is Indonesian; explanations are written in the user's language.
- Tools: `python tools/transcribe2json.py <book>` → `python tools/build.py <book>` → `python tools/audit.py <book>`.
