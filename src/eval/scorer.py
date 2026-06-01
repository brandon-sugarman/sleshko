from __future__ import annotations

from domain.extraction_result import ExtractionResult
from domain.field_catalog import FieldSpec, FieldType
from domain.scoring import DocumentScore, FieldComparison, MatchKind
from eval.eval_set import ExpectedRecord
from eval.normalize import normalize_ein, normalize_int, normalize_text

_EIN_FIELD = "partnership_employer_identification_number"


def score_document(
    result: ExtractionResult,
    expected: ExpectedRecord,
    catalog: dict[str, FieldSpec],
) -> DocumentScore:
    """Compare one pipeline's result against the eval set for one document.

    Gradable fields are exactly the keys in `expected`. A field the pipeline did
    not emit is scored as its zero-default (the absent→0 rule), so a strategy is
    never rewarded for silence on a non-zero field.
    """

    comparisons: list[FieldComparison] = []
    for field_name, raw_expected in expected.items():
        spec = catalog[field_name]
        exp = _normalize(spec, raw_expected)
        emitted = result.get(field_name)
        pred = _normalize(spec, emitted.value) if emitted is not None else spec.zero_default
        comparisons.append(
            FieldComparison(field=field_name, expected=exp, predicted=pred, kind=_classify(exp, pred))
        )

    return DocumentScore(doc_name=result.doc_name, pipeline=result.pipeline, comparisons=tuple(comparisons))


def _normalize(spec: FieldSpec, raw: object) -> int | str:
    if spec.type is FieldType.integer:
        return normalize_int(raw)  # type: ignore[arg-type]
    if spec.name == _EIN_FIELD:
        return normalize_ein(raw)  # type: ignore[arg-type]
    return normalize_text(raw)  # type: ignore[arg-type]


def _classify(expected: int | str, predicted: int | str) -> MatchKind:
    if expected == predicted:
        return MatchKind.correct
    expected_zero = expected in (0, "")
    predicted_zero = predicted in (0, "")
    if expected_zero and not predicted_zero:
        return MatchKind.false_positive
    if not expected_zero and predicted_zero:
        return MatchKind.false_negative
    return MatchKind.wrong
