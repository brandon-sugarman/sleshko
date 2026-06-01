from __future__ import annotations

from domain.document import ExtractedDocument
from domain.extraction_result import ExtractionResult, FieldValue
from eval.normalize import normalize_int
from logger import make_logger

log = make_logger("analysis.acroform_cover")

# ---------------------------------------------------------------------------
# Direct 1-to-1 mappings: AcroForm field short name → schema field name.
# Only the numeric/text fields whose position is unambiguous on the IRS
# Schedule K-1 (Form 1065) template (the field ordering is the same on every
# fillable copy because the XFA template is standardised).
# ---------------------------------------------------------------------------
_DIRECT: dict[str, str] = {
    # Lines 1–10 (Part III right column, continuous numeric boxes)
    "f1_34[0]": "line_1_ordinary_business_income_loss",
    "f1_35[0]": "line_2_net_rental_real_estate_income_loss",
    "f1_36[0]": "line_3_other_rental_income_loss",
    "f1_37[0]": "line_4a_guaranteed_payments_for_services",
    "f1_38[0]": "line_4b_guaranteed_payments_for_capital",
    "f1_39[0]": "line_4c_total_guaranteed_payments",
    "f1_40[0]": "line_5_interest_income",
    "f1_41[0]": "line_6a_ordinary_dividends",
    "f1_42[0]": "line_6b_qualified_dividends",
    "f1_43[0]": "line_6c_dividend_equivalents",
    "f1_44[0]": "line_7_royalties",
    "f1_45[0]": "line_8_net_short_term_capital_gain_loss",
    "f1_46[0]": "line_9a_net_long_term_capital_gain_loss",
    "f1_47[0]": "line_9b_collectibles_28_percent_gain_loss",
    "f1_48[0]": "line_9c_uncaptured_section_1250_gain",
    "f1_49[0]": "line_10_net_section_1231_gain_loss",
    # Line 12 (section 179, single value – no code field)
    "f1_54[0]": "line_12_section_179_deduction",
    # Capital account analysis (Part L)
    "f1_27[0]": "capital_contributions_during_year",
    "f1_29[0]": "other_increase_decrease_income_items",
    "f1_31[0]": "ending_capital_account",
}

# Withdrawals are recorded as a positive number on the form (it is subtracted
# from the capital account). We negate before emitting.
_WITHDRAWAL_FIELD = "f1_30[0]"

# ---------------------------------------------------------------------------
# Code + value pairs for lines that carry a letter code.
# Each entry is (code_field_name, value_field_name).  The code_field holds a
# letter like "O" or "AA"; the value_field holds the dollar amount.
# Rows that contain "SEE STMT" are non-numeric and will be skipped by
# _is_numeric(), leaving those fields at their zero-default at scoring time.
# ---------------------------------------------------------------------------
_LINE15_PAIRS: list[tuple[str, str]] = [
    ("Line15[0]", "f1_63[0]"),
    ("f1_64[0]", "f1_65[0]"),
]
_LINE15_CODE_MAP: dict[str, str] = {
    "O": "line_15o_backup_withholding",
}

_LINE20_PAIRS: list[tuple[str, str]] = [
    ("Line20[0]", "f1_92[0]"),
    ("f1_93[0]", "f1_94[0]"),
    ("f1_95[0]", "f1_96[0]"),
    ("f1_97[0]", "f1_98[0]"),
]
_LINE20_CODE_MAP: dict[str, str] = {
    "AA": "line_20AA_section_704c_information",
    "AB": "line_20AB_section_751_gain_loss",
    "AD": "line_20AD_deemed_section_1250_unrecaptured_gain",
    "AE": "line_20AE_excess_taxable_income",
    "AF": "line_20AF_excess_business_interest_income",
    "AG": "line_20AG_gross_receipts_section_448_c",
    "AM": "line_20AM_section_1061_information",
    "N": "line_20N_interest_expense_for_corporate_partners",
    "O": "line_20O_453I3_information",
    "P": "line_20P_452Ac_information",
    "V": "line_20V_unrelated_business_taxable_income",
}


class AcroFormCoverAnalyzer:
    """Deterministic field-map over AcroForm widgets for the K-1 cover page.

    Works for fillable PDFs (doc_1, doc_2). Flattened PDFs produce no form
    fields, so this returns an empty result (all fields score as zero-default).
    """

    name = "acroform_cover"

    def analyze(self, document: ExtractedDocument) -> ExtractionResult:
        field_map = {f.name: f.value for f in document.form_fields}

        if not field_map:
            log.info("no form fields", {"doc": document.doc_name})
            return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields={})

        emitted: dict[str, FieldValue] = {}

        # Partnership name (first line of the potentially multi-line field)
        name_raw = field_map.get("f1_7[0]", "")
        first_line = name_raw.split("\n")[0].strip()
        if first_line:
            emitted["partnership_name"] = FieldValue(
                field="partnership_name", value=first_line, source="acroform:f1_7[0]"
            )

        # EIN
        ein_raw = field_map.get("f1_6[0]", "").strip()
        if ein_raw:
            emitted["partnership_employer_identification_number"] = FieldValue(
                field="partnership_employer_identification_number",
                value=ein_raw,
                source="acroform:f1_6[0]",
            )

        # Direct numeric fields
        for form_name, schema_name in _DIRECT.items():
            raw = field_map.get(form_name, "")
            if raw and _is_numeric(raw):
                emitted[schema_name] = FieldValue(
                    field=schema_name, value=raw, source=f"acroform:{form_name}"
                )

        # Withdrawals (negate: form shows a positive withdrawal amount)
        wd_raw = field_map.get(_WITHDRAWAL_FIELD, "")
        if wd_raw and _is_numeric(wd_raw):
            pos_val = normalize_int(wd_raw)
            if pos_val != 0:
                emitted["withdrawals_and_distributions_cash"] = FieldValue(
                    field="withdrawals_and_distributions_cash",
                    value=-pos_val,
                    source=f"acroform:{_WITHDRAWAL_FIELD}",
                )

        # Line 15 + Line 20 code+value rows
        _apply_coded_rows(field_map, _LINE15_PAIRS, _LINE15_CODE_MAP, emitted)
        _apply_coded_rows(field_map, _LINE20_PAIRS, _LINE20_CODE_MAP, emitted)

        log.info(
            "acroform_cover analyze done",
            {"doc": document.doc_name, "fields_emitted": len(emitted)},
        )
        return ExtractionResult(doc_name=document.doc_name, pipeline=self.name, fields=emitted)


def build(settings: object) -> AcroFormCoverAnalyzer:
    return AcroFormCoverAnalyzer()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_numeric(raw: str) -> bool:
    """True only if raw can be meaningfully parsed as an integer.

    Mirrors normalize_int's tolerance for commas, parentheses, and trailing
    whitespace while rejecting plain-text annotations like "SEE STMT".
    """
    text = raw.strip().strip("()").replace(",", "").replace("$", "").replace(" ", "")
    if not text or text == "-":
        return False
    try:
        int(float(text))
        return True
    except (ValueError, OverflowError):
        return False


def _apply_coded_rows(
    field_map: dict[str, str],
    pairs: list[tuple[str, str]],
    code_map: dict[str, str],
    emitted: dict[str, FieldValue],
) -> None:
    for code_field, val_field in pairs:
        code = field_map.get(code_field, "").strip()
        raw = field_map.get(val_field, "").strip()
        schema_name = code_map.get(code)
        if schema_name and raw and _is_numeric(raw):
            emitted[schema_name] = FieldValue(
                field=schema_name, value=raw, source=f"acroform:{code_field}={code}"
            )
