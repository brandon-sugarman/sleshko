# Abacus Interview Challenge

Welcome to the Abacus Interview Challenge! This is your chance to demonstrate how you'd approach building a robust data extraction pipeline.

## 🗂️ What’s in this repo?

We've provided the following files to get you started:

- **`pdfs/`**  
  This folder contains **three tax forms** in PDF format. These are your input files.

- **`eval_set.csv`**  
  This CSV contains the **expected field names and extracted values** for each PDF. Each column corresponds to one of the provided K-1 forms.

- **`main.py`**  
  This is where you’ll write your **extraction logic**. Your pipeline should process each PDF and output structured data in accordance with the provided schema.

- **`pydantic_model.py`**  
  This defines a **Pydantic schema** for the two key sections we care about:
  - The **cover page**
  - The **footnotes** (the supplemental materials following the cover page)  
  
  It also includes a helper function to **chunk the schema** for easier parsing.

## 🎯 Your Goal

Build a data extraction pipeline that:

1. **Reads each PDF** from the `pdfs/` directory.
2. **Extracts structured data** for the cover page and footnotes, matching the Pydantic schema in `pydantic_model.py`.
3. **Compares** your extracted data against the reference values in `eval_set.csv`.

Your logic should live in `main.py`.

## ✅ Evaluation

We'll assess your solution based on:

- **Accuracy** of extraction
- **Code clarity and structure**
- **Use of the provided schema**
- **Comparison results against the eval set**

Feel free to use any libraries or tooling you like—just be sure to document what you use.

---

Good luck, and happy parsing! 🧮

— The Abacus Team

---

## Running the pipeline

### Setup

```bash
uv sync
```

Add your Gemini API key to a `.env` file at the repo root:

```
GEMINI_API_KEY=your_key_here
```

### Run the eval harness

```bash
uv run python main.py
```

This runs every registered extraction/analysis strategy pair against all three PDFs and prints a leaderboard ranked by **non-zero recall** (the primary metric), false positives, and exact accuracy, with a letter grade for each.

Example output:

```
PIPELINE                                       NZ RECALL   FALSE+    EXACT   GRADE
----------------------------------------------------------------------------------
acroform + acroform_cover                          53.1%        0    96.2%       D
```

A second table below the leaderboard breaks down each pipeline's scores per document.

### Metrics explained

| Metric | What it measures |
|---|---|
| **NZ Recall** | Of the fields that actually have a non-zero value, how many did we find? This is the primary metric — the eval set has ~180 zero fields per doc, so "predict all zeros" would score ~90% exact but 0% NZ recall. |
| **False+** | Non-zero values we emitted where the answer was actually zero. Penalizes hallucination. |
| **Exact** | Fraction of all 200 fields that matched exactly (inflated by the sea of zeros). |
| **Grade** | A–F computed from NZ recall minus a 2%/false-positive penalty. |

### Adding a new strategy

Every strategy is a Python file in `src/extraction/` or `src/analysis/` plus one line in `src/strategies.py`. See `docs/PLANNING.md` for the full extension guide with worked examples.

Quick version — to add a new extractor:

1. Create `src/extraction/my_extractor.py` with a class that has `name = "my_extractor"` and an `extract(doc_name, pdf_bytes) -> ExtractedDocument` method, plus a `build(settings)` factory.
2. Add to `src/strategies.py`:
   ```python
   from extraction import my_extractor
   register_extraction(my_extractor.MyExtractor.name, my_extractor.build)
   ```
3. Run `uv run python main.py` — your extractor will appear in the leaderboard paired with every registered analyzer.

### Project layout

```
src/
  domain/          # value types — ExtractedDocument, ExtractionResult, scoring
  extraction/      # ExtractionStrategy implementations (AcroForm, PyMuPDF, ...)
  analysis/        # AnalysisStrategy implementations (deterministic, Gemini, ...)
  infra/           # external SDK adapters (Gemini client)
  eval/            # harness — runner, scorer, reporter
  prompts/         # LLM prompt builders
  registry.py      # strategy registry + Pipeline + build_matrix()
  strategies.py    # manifest: one register_* line per strategy
  config.py        # Settings dataclass and load_settings() factory (paths)
docs/
  PLANNING.md      # architecture deep-dive and extension guide
```
