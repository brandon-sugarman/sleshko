# Retrospective — K-1 Extraction Challenge

A short record of how I approached this challenge.

## Philosophy
- **Agent-first from the start.** Goal was to *guide*, not type — encode strong standards in `AGENTS.md` so agents handle implementation while I steer scope and direction.
- Front-loaded the rules (scope guardrails, code org, normalization/eval discipline) so quality was enforced structurally rather than reviewed line-by-line.

## Recon
- Did an overview of each PDF to map capabilities (`docs/FILE_EXTRACTION_INFO.md`): which docs had AcroForm fields, which were images, per-page structure.
- Early conviction: **lean on AcroForm** where present to see how far clean form data alone could go.
- Knew LLMs / OCR were unavoidable — `doc_2` page 2 is an image, and `doc_3` lacked out-of-the-box AcroForm.

## Strategies tried
- **Hybrid max-fidelity** — pushed toward 100%, but judged it overfit to the three visible docs, so I searched for something more generalized.
- **Gemini vision + pymupdf** — the "clean generalizable" bet; proved fruitful when tested on other example documents I pulled from the internet compared to the hybrid approach

## Eval pipeline
- Built a harness to benchmark strategy pairings and **run multiple model configs**, with per-run log folders, rubric/snapshot dumps, and a report.
