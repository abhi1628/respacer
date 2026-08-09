# respacer

Fix missing spaces in text mangled by PDF-to-Word conversion — while preserving formatting.

```
ThisisaparagraphaboutAI  -->  This is a paragraph about AI
```

If you've ever converted a PDF to Word and gotten a wall of `ThisIsWhatItLooksLikeInsteadOfNormalText`,
this tool fixes it — for the whole document, in one pass, without wrecking your headings, bold text, or tables.

## Why this happens

PDFs don't store "words" — they store individual characters positioned at exact X/Y
coordinates on the page. Converters have to *guess* where word boundaries are from the
gaps between characters. Certain fonts, tight kerning, justified text, or PDFs generated
by non-standard tools make word gaps look identical to letter gaps, so the converter
merges everything together.

## How it works

`respacer` uses a two-stage pipeline:

**Stage 1 — Dictionary segmentation (free, fast, always on)**
Uses frequency-based Viterbi word segmentation (via [`wordninja`](https://github.com/keredson/wordninja))
to propose splits, then runs every candidate through a **confidence gate** before accepting it:

- Only touches tokens that look genuinely broken (long, pure-alphabetic, no digits/underscores)
- **Never touches** URLs, emails, or `snake_case`/`kebab-case`/code-like identifiers
- Rejects any split that loses or changes characters
- Rejects splits that produce junk single-letter fragments
- Merges runs like `A` + `I` back into `AI` (mis-split acronyms)

**Stage 2 — LLM enhancement (optional, requires your own Groq API key)**
Anything Stage 1 isn't confident about (ambiguous proper nouns, unusual jargon) can
optionally be sent to an LLM for a context-aware second opinion. This is opt-in only —
`respacer` never makes a network call unless you explicitly provide an API key.

**Formatting preservation**
For `.docx` input, `respacer` never rebuilds the document. It walks each paragraph's
existing `runs` (Word's internal unit of "text with one consistent style") and rewrites
only the text inside each run, in place. Since a run's *style* is never touched, bold
stays bold, headings stay headings, fonts/colors/tables are all untouched.

For `.pdf` input, there's no equivalent of a "run" to preserve, so `respacer` extracts
text and rebuilds a clean `.docx` with basic structure (paragraphs, guessed headings).
**If you already have a converted `.docx` that looks wrong, fix that file directly —
it preserves 100% of the original formatting, which a fresh PDF extraction cannot.**

## Installation

```bash
git clone https://github.com/abhi1628/respacer.git
cd respacer
pip install -r requirements.txt
pip install -e .
```

Or once published to PyPI:
```bash
pip install respacer
```

## Usage

### Command line

```bash
# Fix a broken docx
respacer fix input.docx -o output.docx

# Fix directly from a PDF
respacer fix input.pdf -o output.docx

# See exactly what changed
respacer fix input.docx -o output.docx --verbose

# Only touch tokens 15+ characters long (default is 12)
respacer fix input.docx -o output.docx --min-length 15
```

### Python API

```python
from respacer import respace_text

text = "ThisisaparagraphaboutAI and machine learning."
print(respace_text(text))
# -> "This is a paragraph about AI and machine learning."
```

```python
from respacer.docx_handler import fix_docx

# Fixes formatting-preserving, returns a report of every change made
report = fix_docx("input.docx", "output.docx")
for change in report:
    print(change["original"], "->", change["fixed"], change["confidence"])
```

```python
from respacer.pdf_handler import fix_pdf

fix_pdf("input.pdf", "output.docx")
```

### Optional: LLM-enhanced mode

```python
from respacer.llm_enhancer import respace_text_with_llm

fixed = respace_text_with_llm(
    text,
    api_key="your-groq-api-key",   # or os.environ["GROQ_API_KEY"]
)
```

This only calls the LLM on paragraphs the dictionary pass couldn't confidently resolve,
so API usage scales with how ambiguous your document actually is — not its total length.

## What it will NOT touch (by design)

- URLs and email addresses
- `snake_case`, `kebab-case`, and anything containing digits (looks code-like)
- Words shorter than `min_length` (default 12 chars) — too risky to guess on short strings
- Any split where the confidence score comes back low (better to leave a word broken than corrupt a correct one)

## Known limitations

- **CamelCase ambiguity**: `CamelCaseVariable` (a code identifier) and `BaderiaInstitute`
  (a broken Title Case heading) look identical to the algorithm. Stage 1 will attempt to
  split both. If your document mixes prose and code identifiers, review the `--verbose`
  report or use LLM-enhanced mode, which uses surrounding context to tell them apart.
- Very short glued words (e.g., `"ofthe"`) below `min_length` are intentionally left alone,
  since short strings are far more likely to produce false-positive splits.
- PDF input rebuilds the document structure from scratch — it does not preserve the
  original PDF's fonts/styling, only paragraph-level structure.

## Running tests

```bash
pip install -e ".[dev]"
pytest tests/ -v
```

## Project structure

```
respacer/
├── respacer/
│   ├── __init__.py        # public API
│   ├── detector.py         # decides which tokens are safe to touch
│   ├── segmenter.py         # dictionary-based segmentation + confidence gate
│   ├── docx_handler.py     # in-place run-level fixing for .docx
│   ├── pdf_handler.py      # extraction + rebuild for .pdf
│   ├── llm_enhancer.py     # optional Groq-based second pass
│   └── cli.py              # command-line interface
├── tests/
│   └── test_segmenter.py
├── examples/
├── requirements.txt
├── pyproject.toml
└── LICENSE
```

## Roadmap

- [ ] Batch mode (fix an entire folder of files)
- [ ] Preserve font/style info when extracting directly from PDF (via character-level bounding boxes)
- [ ] Web demo / hosted API
- [ ] Support for `.pptx` (same problem shows up in slide decks)
- [ ] Multi-language dictionary support (currently English-only)

## Contributing

Issues and PRs welcome. If you hit a document where `respacer` makes a wrong call,
please open an issue with the (anonymized) before/after text — real failure cases are
the best way to improve the confidence heuristics.

## License

MIT — see [LICENSE](LICENSE).
