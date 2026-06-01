from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class K1CodeField:
    box: str
    code: str
    field: str


# Box/code mappings that are represented directly in pydantic_model.py and can
# be resolved from coded K-1 rows or attached statements.
CODE_FIELDS: tuple[K1CodeField, ...] = (
    K1CodeField("11", "A", "line_11a_other_income_total"),
    K1CodeField("11", "C", "line_11c_section_1256_gain_loss"),
    K1CodeField("13", "L", "line_13l_deductions_portfolio_other"),
    K1CodeField("13", "ZZ", "line_13ZZ_other_deductions_total"),
    K1CodeField("15", "O", "line_15o_backup_withholding"),
    K1CodeField("18", "B", "line_18b_other_tax_exempt_income"),
    K1CodeField("18", "C", "line_18c_nondeductible_expenses"),
    K1CodeField("20", "AA", "line_20AA_section_704c_information"),
    K1CodeField("20", "AB", "line_20AB_section_751_gain_loss"),
    K1CodeField("20", "AD", "line_20AD_deemed_section_1250_unrecaptured_gain"),
    K1CodeField("20", "AE", "line_20AE_excess_taxable_income"),
    K1CodeField("20", "AF", "line_20AF_excess_business_interest_income"),
    K1CodeField("20", "AM", "line_20AM_section_1061_information"),
    K1CodeField("20", "N", "line_20N_interest_expense_for_corporate_partners"),
    K1CodeField("20", "O", "line_20O_453I3_information"),
    K1CodeField("20", "P", "line_20P_452Ac_information"),
    K1CodeField("20", "V", "line_20V_unrelated_business_taxable_income"),
)

# The challenge schema splits Box 13 Code H into reporting destinations. A
# fillable cover row has only the K-1 code and amount, so this map preserves the
# existing cover-page behavior while keeping that assumption auditable.
COVER_CODE_FIELDS: tuple[K1CodeField, ...] = CODE_FIELDS + (
    K1CodeField("13", "H", "line_13h_investment_interest_trading_schedule_E"),
    K1CodeField("20", "AG", "line_20AG_gross_receipts_section_448_c"),
)

# Fields that can reasonably appear only in supplemental statement detail for
# the current schema. This keeps image fallback narrow without placing the list
# inside the max-fidelity analyzer itself.
TEXTLESS_STATEMENT_FIELD_NAMES = frozenset(
    {
        "line_5_interest_income_us_government_interest",
        "line_11a_other_income_total",
        "line_11c_section_1256_gain_loss",
        "line_11ZZ_ordinary_income_section_475f",
        "line_11ZZ_other_income_loss",
        "line_11ZZ_pfic_qef_income",
        "line_11ZZ_section_988_total",
        "line_11ZZ_swap_net_income_loss",
        "line_13h_investment_interest_investing_schedule_A",
        "line_13h_investment_interest_trading_schedule_E",
    }
)

# Statement images can contain a more specific split than the K-1 cover row.
# These fields may replace an earlier cover-derived value from the same box/code.
TEXTLESS_STATEMENT_OVERRIDE_FIELD_NAMES = frozenset(
    {
        "line_13h_investment_interest_investing_schedule_A",
        "line_13h_investment_interest_trading_schedule_E",
    }
)


def field_for_code(box: str, code: str, *, cover: bool = False) -> str | None:
    normalized_box = box.strip().upper()
    normalized_code = code.strip().upper()
    fields = COVER_CODE_FIELDS if cover else CODE_FIELDS
    for item in fields:
        if item.box == normalized_box and item.code == normalized_code:
            return item.field
    return None
