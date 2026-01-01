# Payroll Payment Features Plan

## Goals
Design payment-generation capabilities for ACH/direct deposit files and printable checks while tracking employee payment methods, run-level overrides, and void/reissue workflows. Outputs are for export only (no upstream submission).

## Data Model Additions
- **EmployeePaymentMethod**
  - `employee_id`
  - `default_method` enum: `ach` | `check`
  - `ach_account_number`, `ach_routing_number`, `ach_account_type`
  - `check_mailing_address`
  - `status` and timestamps for auditing
- **PayrollRunPayment** (per employee per payroll run)
  - `payroll_run_id`, `employee_id`
  - `method_used` enum (resolves default + override)
  - `gross_amount`, `net_amount`, `deductions`, `remittance_detail` (line items)
  - `status` enum: `pending`, `generated`, `voided`, `reissued`
  - `export_reference` (file/run identifier)
  - `void_reason`, `reissue_of_payment_id`
- **PaymentExportRun**
  - `id`, `run_type` (`ach_csv`, `nacha_like`, `check_pdf`)
  - `status`: `draft`, `generated`, `downloaded`
  - `generated_at`, `generated_by`
  - `file_path` or blob reference for download

## ACH/Direct-Deposit Export
- Support two flavors: **CSV** and **NACHA-like** (flat-file with header/batch/entry summary but not sent to bank).
- Generation flow:
  1. Select payroll run + employees with `method_used=ach` and `status=pending`.
  2. Build export lines from `net_amount`, routing/account numbers.
  3. Persist `PaymentExportRun` with links to included `PayrollRunPayment` records; mark payment status `generated`.
  4. Allow re-download using stored file reference.
- Sample CSV schema: `employee_id,employee_name,routing_number,account_number,account_type,amount,currency,description,pay_date`.
- NACHA-like rules:
  - Construct File Header, Company/Batch Header, Entry Detail records, Batch Control, File Control.
  - Use zero-filled routing/account placeholders where data is missing but flag validation errors before file creation.
  - Maintain trace numbers via `export_run_id + line counter`.
  - No transmission—provide a downloadable text file only.
- Status tracking: each payment marked `generated` after file is written; exporting again creates a new `PaymentExportRun` and updates `export_reference`.

## Check PDF Generator
- Generate check PDFs with MICR line placeholders (e.g., `XXXX ROUTING XXXX ACCOUNT XXXX CHECKNO XXXX`).
- Layout:
  - Check stub with company info, employee info, pay period, net pay, taxes/deductions listed as remittance detail.
  - Check body with amount in numbers + words, date, signature line, MICR placeholder.
  - Multi-check batch: paginate with one check per page; include a first-page summary of batch total and count.
- Generation flow:
  1. Resolve payments with `method_used=check` for the payroll run and `status=pending`.
  2. Build PDF using server-side renderer (e.g., WeasyPrint/PDFKit); render remittance table from `remittance_detail`.
  3. Store PDF in `PaymentExportRun` (`run_type=check_pdf`); mark included payments `generated`.
  4. Batch download: `/exports/{export_run_id}/download` streams the stored PDF.

## Payment Method Overrides per Run
- UI/API allows selecting payment method per employee for a given payroll run. Resolution order:
  1. Run-level override if present.
  2. Employee default method.
  3. Fallback to `check` with manual review flag if neither is set.
- Validation: ACH requires routing/account + account type; check requires mailing address or pickup flag.

## Void/Reissue Workflow
- Payments in `generated` can be voided with a reason; file artifacts remain for audit but are excluded from totals on new exports.
- Reissue creates a new `PayrollRunPayment` linked via `reissue_of_payment_id`, copying remittance detail and enabling method change (e.g., voided check reissued as ACH).
- Export runs skip voided payments and include reissued ones according to their resolved method.
- Audit log captures status transitions with user/time stamps.

## API/Service Outline
- `POST /payroll-runs/{id}/exports` with `type=ach_csv|nacha_like|check_pdf` generates the file and returns `export_run_id` + download URL.
- `GET /exports/{export_run_id}/download` streams the stored artifact.
- `POST /payroll-runs/{run_id}/payments/{payment_id}/void` marks void with reason.
- `POST /payroll-runs/{run_id}/payments/{payment_id}/reissue` creates replacement payment with optional method override.

## Reporting & Tracking
- Export runs list shows run type, created by, created at, file size, and download count.
- Payments listing displays method source (default/override), status, export reference, and void/reissue history.
- Optional flags: validation errors for missing banking data, warnings for duplicate account numbers.

## Implementation Notes
- Keep bank account data encrypted at rest; mask account numbers in UI and exports where appropriate (except NACHA which needs full numbers).
- Store rendered files in object storage or database blobs with integrity hashes for re-download.
- For testing, use deterministic trace/check numbers for reproducibility.
