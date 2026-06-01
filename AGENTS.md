# Abacus K-1 Extraction Challenge Agent Rules

This file defines repository standards for agents working on this codebase. It is not an implementation plan. Keep changes focused, small, reproducible, and aligned with the K-1 extraction/evaluation task.

---

## 1. Repository Scope

- This repo exists to extract structured data from the provided K-1 PDFs and compare it against `eval_set.csv`.
- Do not turn the challenge into a general document-processing platform.
- Do not introduce broad abstractions, service layers, plugin systems, queues, databases, web servers, or UI code unless explicitly requested.
- The two sanctioned abstractions, because the challenge explicitly asks us to compare extraction approaches, are the `ExtractionStrategy` / `AnalysisStrategy` layers and the eval harness that benchmarks their pairings (see `docs/PLANNING.md`). Everything else stays concrete.
- Prefer boring, inspectable Python over clever framework-heavy designs. The strategy "registry" is a plain dict of name→factory, not a dynamic plugin loader.
- The canonical schema is `pydantic_model.py` (kept at the repo root). The canonical evaluation target is `eval_set.csv`.

---

## 2. Code Organization

- Keep `main.py` as a thin entry point: it wires settings, builds the strategy matrix, runs the eval harness, and prints the report. Logic lives in `src/`, never in `main.py`.
- Add supporting modules only when they make the code easier to read or test.
- Name modules after their concrete responsibility, for example `pymupdf_text.py`, `normalize.py`, `scorer.py`, or `gemini_client.py`.
- Avoid speculative folders. Promote a concern to a folder only when it outgrows one file — hence `src/domain/` and `src/eval/`, while single concerns stay single files (`config.py`, `ports.py`, `logger.py`, `registry.py`).
- One file should have one clear responsibility, kept under ~200 lines. Similarly, functions should also follow the single responsibility policy.
- Keep orchestration separate from low-level helpers when the code grows:
  - orchestration: load PDFs, call extractors, run eval, print report
  - extraction: PDF text/image processing and model calls
  - normalization: value cleanup and type conversion
  - evaluation: expected/actual comparison and reporting
- **File layout order**: imports → module-level constants → main class → `build()` factory → private helpers at the bottom. Helpers are underscore-prefixed and live below everything else so readers land on the important logic first.
- Shared helpers used by more than one module belong in the module closest to their concern (e.g. `parse_gemini_fields` lives in `infra/gemini_client.py`), not copy-pasted into each caller.
- Do not duplicate large parts of the schema manually. Use `pydantic_model.py` as the source of truth.

---

## 3. Extraction Code Standards

- Extraction logic must be deterministic where practical, especially for normalization and evaluation.
- Treat LLM output as untrusted external data. Parse, validate, normalize, and compare it explicitly.
- Keep provider-specific Gemini code isolated from core extraction and evaluation logic.
- Do not bury important extraction assumptions inside prompts only. If behavior matters, represent it in code or named constants too.
- Missing fields, blank fields, and zero-valued fields are different states until the normalization boundary.
- Never silently swallow extraction failures and report them as successful zeros.

---

## 4. Configuration

- Required configuration must be explicit. If a required file path, API key, model name, or option is missing, fail clearly.
- Read secrets from environment variables. Do not commit API keys, sample secrets, or local credential files.
- Put behavior-influencing constants at module level with descriptive names.
- Avoid magic numbers inside functions. Constants like render DPI, retry count, timeout, or text-quality thresholds must be named.
- Do not add hidden defaults that materially change extraction behavior.

---

## 5. Data Normalization

- Normalize values in one clear place, not scattered across extractors.
- Numeric normalization should handle commas, currency symbols, whitespace, decimals when appropriate, and parentheses negatives.
- String normalization should be conservative. Do not destroy information needed for debugging.
- EIN handling must be consistent between extracted and expected values.
- Defaulting absent numeric fields to `0` should happen only at a deliberate boundary, not deep inside OCR/model parsing.

---

## 6. Evaluation Discipline

- Evaluation code should make mismatches easy to inspect by document and field.
- Track nonzero-field performance separately from total-field accuracy because most schema fields are zero.
- Do not overfit logic to the visible answers in `eval_set.csv` in a way that would obviously fail on a fourth similar K-1.
- Keep generated outputs, debug dumps, rendered page images, and model responses out of git unless explicitly requested.
- If adding tests, prefer small tests for normalization, schema handling, and eval comparison.

---

## 7. Error Handling

- Validate at boundaries: file reads, PDF parsing, external API calls, JSON parsing, and Pydantic validation.
- Fail loudly on malformed model responses or unreadable PDFs.
- Retry transient external API failures with bounded backoff.
- Do not add broad `except Exception` blocks that hide root causes.
- If a fallback strategy is used, make that visible in the returned metadata or report.

---

## 8. Logging and Output

- Keep command-line output concise and useful.
- `main.py` may print a summary report. Reusable helper functions should not print casually.
- Prefer structured debug information over free-form noise.
- Include enough context in errors to identify the document, page, field, and strategy involved.
- Avoid committing verbose logs or local debug artifacts.

---

## 9. Comments and Readability

- Use clear names instead of explanatory comments whenever possible.
- Add comments only for non-obvious constraints, third-party quirks, or extraction assumptions that future maintainers need to know.
- Do not comment what the code mechanically does.
- Keep functions small enough that their control flow is obvious.
- Prefer explicit intermediate variables over dense one-liners when parsing or normalizing financial values.

---

## 10. Dependencies

- Add dependencies only when they materially improve extraction quality, reliability, or clarity.
- Document any new runtime dependency in the README or equivalent setup notes.
- Keep dependency usage localized so libraries can be replaced if needed.
- When integrating a fast-moving external API such as Gemini, verify current official usage before coding against it.

---

## 11. Quality Gate

Before handing off changes:

- Run the pipeline or the relevant subset of it.
- Run `python -m compileall .` if there is no more specific test suite.
- Review the diff for accidental generated files, credentials, or debug artifacts.
- Report what was run and what was not run.
