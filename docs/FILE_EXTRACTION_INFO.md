# Page-by-page description of K-1 sample PDFs

## File 1: doc_1.pdf, 4 pages

### Page 1

Main IRS Schedule K-1 Form 1065 cover page for tax year 2024.
Contains the official K-1 summary fields: partnership info, partner info, ownership percentages, K1 liability section, capital account analysis, and Part III income/deduction/credit boxes. Several boxes reference attached statements, especially Box 13, Box 18, and Box 20. This is the actual K-1 cover page.

### Page 2

Attached statement page.
Contains detailed support for K-1 statement items:

* Box 13 Code ZZ: other deductions, Section 754 amortization
* Box 18 Code B: other tax-exempt income
* Box 18 Code C: nondeductible expenses
* Box 20 Code N: business interest expense

### Page 3

Attached statement page.
Contains detailed support for:

* Box 20 Code AJ: excess business loss limitation
* Box 20 Code Z: Section 199A information
* Additional Section 199A explanatory text about QBI deduction calculations and tax advisor review

### Page 4

Attached statement page.
Contains:

* Box 20 Code AG: gross receipts for Section 448(c)
* Schedule K-3 notification stating Schedule K-3 was not prepared and will only be provided if requested

## File 2: doc_2.pdf, 2 pages

### Page 1

Main IRS Schedule K-1 Form 1065 cover page for tax year 2024.
Contains the official K-1 summary fields. Partnership info is filled with Test Partnership and EIN 12-3456789. Part III contains summary amounts and “SEE STMT” references for items explained on page 2. This is the actual K-1 cover page. The K1 liabilities section appears on this page but is blank.

### Page 2

Attached statement page.
Contains detailed breakdowns for K-1 lines:

* Line 5: interest income
* Line 6A: ordinary dividends
* Line 6B: qualified dividends
* Line 11A: other portfolio income/loss
* Line 11C: Section 1256 contracts and straddles
* Line 11ZZ: other income/loss items
* Line 13H: other deductions, investment interest expense

## File 3: doc_3.pdf, 7 pages

### Page 1

Mailing or transmittal cover sheet.
Shows partnership name, partnership address, recipient name and address, and “SAMPLE.” This is not the K-1 form itself.

### Page 2

Cover letter.
Explains that the attached document is a corrected 2019 Partnership Form 1065 Schedule K-1. Tells the recipient to replace the previously received K-1, consult a tax advisor, and not contact the Trust for tax advice or further explanation.

### Page 3

Actual IRS Schedule K-1 Form 1065 cover page for tax year 2019.
Contains partnership info, partner info, partner type, ownership percentages, K1 liability section, capital account summary, and Part III K-1 boxes. This is the actual K-1 cover page. Some entries have asterisks pointing to attached statements or footnotes.

### Page 4

Attached statement page.
Contains detailed support for:

* Box 11 Code A: other portfolio income
* Box 13 Code L: other portfolio deductions
* Box 20 Code V: unrelated business taxable income
* Current year net income/loss and other increases/decreases summary

### Page 5

Capital account statement and beginning of formal K-1 footnotes.
Contains:

* Continuation of net income/loss total
* Item L partner capital account analysis, GAAP basis
* Start of “Schedule K-1 Footnotes”
* Texas franchise tax discussion
* Schedule E reporting guidance
* Notes that certain income is not self-employment income and not passive activity income
* Legal/professional fee deduction guidance
* Investment interest expense and Form 4952 guidance

### Page 6

Continuation of formal K-1 footnotes.
Contains:

* Warning that taxable K-1 amounts must be reported even if no matching cash distribution was received
* Note that distributions may not match K-1 taxable amounts
* Warning that tax software entry may be difficult
* Direction to consult a tax adviser or software support
* UBTI additional information for Form 990-T, including debt-financed property calculations

### Page 7

Generic IRS Schedule K-1 code/instruction page for 2019.
This is not personalized taxpayer data. It is the standard K-1 Page 2 instruction/code guide showing what various box codes mean and where they may be reported on a tax return.

# Important review implications

1. The actual K-1 cover page is not always page 1.

   * doc_1: K-1 cover page is page 1.
   * doc_2: K-1 cover page is page 1.
   * doc_3: K-1 cover page is page 3.

2. Attached statements and footnotes can contain information not present on the K-1 cover page.

   * doc_1: pages 2-4 contain additional statement details.
   * doc_2: page 2 contains additional statement details.
   * doc_3: pages 4-6 contain additional statement details and substantive footnotes.

3. “Footnotes” can mean different things depending on the file.

   * In doc_1 and doc_2, the extra pages are mostly supporting statements.
   * In doc_3, pages 5-6 contain actual narrative footnotes under the heading “Schedule K-1 Footnotes.”

4. A parser should not assume the K-1 cover page contains all tax-relevant information.
   The cover page often contains summary amounts, codes, asterisks, or “SEE STMT,” while the attached pages contain breakdowns, explanations, and reporting instructions.

5. A parser should distinguish these page types:

   * mailing/transmittal page
   * cover letter
   * actual K-1 cover page
   * attached statement page
   * formal footnote page
   * generic IRS instruction/code page
