# Oracle Financial Contract API

## Purpose

Phase X4D exposes Oracle financial truth through read-only, PII-minimized contracts for a future WordPress Billing import planner. It does not model WordPress tables, write to Oracle, or invent agreements, invoices, installments, payments, allocations, or balances.

All endpoints require the existing `X-API-Key` header.

## Endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /api/families/<family_id>/financial-summary` | Existing messaging summary plus additive sanitized contract fields |
| `GET /api/families/<family_id>/financial` | Family financial summary alias |
| `GET /api/families/<family_id>/balance` | Family financial summary alias |
| `GET /api/financial/families/<family_id>` | Family financial summary alias |
| `GET /api/families/<family_id>/financial-transactions` | Paginated Oracle student-ledger rows |
| `GET /api/families/<family_id>/transactions` | Transaction alias |
| `GET /api/families/<family_id>/dues` | Paginated family due allocations |
| `GET /api/families/<family_id>/receipts` | Paginated receipts aggregated by Oracle receipt ID |
| `GET /api/families/<family_id>/payments` | Explicit unavailable payment contract; Oracle receipts are not duplicated as payments |
| `GET /api/students/<family_id>:<student_id>/financial-summary` | Composite-key student financial summary |
| `GET /api/students/<family_id>:<student_id>/financial` | Student summary alias |
| `GET /api/financial/diagnostics` | Count-only financial readiness diagnostics |

The existing `GET /api/families/<family_id>/financial-card` remains unchanged for backward compatibility.

## Query Parameters

All endpoints accept `study_year`; the configured current year is used when it is omitted. Collection endpoints accept `limit` from 1 to 2000 and non-negative `offset`. Pagination uses Oracle 11g-compatible nested `ROWNUM`, not 12c offset/fetch syntax.

Example:

```text
GET /api/families/459/financial-transactions?study_year=2025%2F2026&limit=500&offset=0
```

## Identity Rules

Student-level records always expose:

```json
{
  "oracle_family_id": 459,
  "oracle_student_id": 3,
  "oracle_student_key": "459:3"
}
```

Student IDs are never treated as globally unique. Invalid composite keys return HTTP 400.

## Source Contracts

### Family Summary

The official family balance comes from `SCH_FIN_FAMILY_CARD`:

```text
BEGIN_DR - BEGIN_CR + YEAR_DR - YEAR_CR
```

The endpoint returns numeric debit, credit, total, balance, direction, and currency fields. Balances are marked `NOT_IMPORT_READY` because the proven table contract has no as-of snapshot key.

Student ledger totals come from `SCH_FIN_STUDENT_CARD`, linked through `SCH_STUDENT_CARD_YEAR`. Family due allocations are not assigned to students because no proven student link exists in `SCH_FAMILY_DUE_ALLOC`.

### Transactions

Transactions come from `SCH_FIN_STUDENT_CARD`. `serial_id` is preferred for `oracle_transaction_key`. A receipt key is used only when the receipt appears on exactly one source row. Rows without a stable key remain visible but are marked `NOT_IMPORT_READY` with missing requirements.

### Dues

Dues come from proven columns in `SCH_FAMILY_DUE_ALLOC`: family, study year, date, percent, due amount, paid amount, and receipt-paid amount. No dedicated due ID or student link is proven, so dues are currently `NOT_IMPORT_READY`. The API does not manufacture composite keys or installment schedules.

### Receipts and Payments

Receipts are credit rows from `SCH_FIN_STUDENT_CARD`, aggregated by `receipt_id` so one Oracle receipt is returned once. A student key is included only when all source lines belong to one student. Payment method is `unknown` because no method column is proven.

Oracle does not currently expose a distinct payment entity. The payments endpoint therefore returns an empty collection with `financial_available=false`; it does not duplicate receipt rows as payments.

## Stable Keys

- Transaction: `serial:<serial_id>` when available and expected unique.
- Transaction fallback: `receipt:<receipt_id>` only for a single-line receipt.
- Receipt: `receipt:<receipt_id>` after aggregation.
- Due: unavailable.
- Payment: unavailable as a distinct entity.
- Balance: unavailable without an as-of snapshot key.

Financial diagnostics report duplicate serial/receipt IDs and rows missing both key candidates. Uniqueness must be validated before any import plan.

## Import Readiness

Applicable records include:

```json
{
  "import_readiness": "IMPORT_READY",
  "missing_requirements": []
}
```

A record is ready only when it has a stable key, family identity, amount, date, and study year. Missing requirements are explicit. Status and type fields are passed through only from proven Oracle columns.

## PII Policy

New endpoints do not select or expose student names, family names, parent names, phones, mobile numbers, email addresses, addresses, national numbers, or Oracle free-form notes. Contract `source.notes` contains API-authored technical limitations only and never Oracle row content.

SQL aliases are at most 30 characters. All caller inputs use bind parameters. All financial-contract SQL is SELECT-only.

## Known Unavailable Entities

- Distinct payments and payment methods
- Agreements/contracts
- Invoices/bills
- Installments
- Settlements
- Discounts and refunds as independent entities
- Stable family/student balance snapshots
- Stable due keys and student-level due allocation

## WordPress Verification

After deployment and service restart, rerun:

```bash
php wp-content/plugins/olama-invoice/tools/discover-oracle-financial-contract.php --study-year=2025/2026 --family-id=459 --sample-limit=5 --export-summary
```

The summary, transactions, dues, receipts, payments, diagnostics, and student-summary routes should become available. X4C may remain `WARN` because agreement/invoice contracts are intentionally unavailable.
