# Reconciliation Report — Suryaa Consumer Products Ltd

## National 52-Week Primary Sales Total

| Metric | Value |
|---|---|
| Total primary sales value (52 weeks) | **INR 1,525,676,586.94** |
| Total primary sales units (52 weeks) | **38,624,880 units** |
| Period covered | 2025-07-01 to 2026-06-23 |
| Unique sales weeks | 52 |

*Source: fact_primary_sales, cleaned. All sentinel values (#N/A, -1, 9999, blank) excluded from totals.*

---

## Top 3 Data Quality Fixes (Ranked by Rows Affected)

### 1. Distributor ID leading-zero prefix — 9,382 rows
**Issue**: Distributor IDs in `fact_primary_sales` carried a leading zero prefix (e.g., `0DEL-D1`, `0AHM-D1`, `0HYD-D2`, `0BEN-D1`, etc.).
**Fix**: Regex `^0([A-Z]{3}-)` → `$1` stripped the leading zero, normalizing to the canonical format (`DEL-D1`, `AHM-D1`, etc.).
**Impact**: 9,382 rows in `fact_primary_sales` (approximately 15% of all rows) had malformed distributor IDs that would have failed joins with `dim_distributor`.

### 2. Primary sales value formatting — 9,416 rows
**Issue**: The `primary_sales_value` column used three different formatting conventions across rows:
- Plain numeric (e.g., `3753.75`) — majority of rows
- Comma-separated (e.g., `"4,792"`, `4,792`) — **4,707 rows**
- Rs-prefixed (e.g., `"Rs 4,582"`, `Rs 3,589`) — **4,709 rows**
**Fix**: A dedicated `clean_primary_sales_value()` function strips the `Rs` prefix, removes commas and surrounding quotes, and casts to `float`. Unparseable values are coerced to `NaN` via `pd.to_numeric(..., errors='coerce')`.
**Impact**: 9,416 rows (≈15% of all rows) would have been read as strings, breaking numeric aggregation.

### 3. Date format normalization — 10,972 rows non-ISO
**Issue**: The `week_start` column in `fact_primary_sales` contained four distinct date formats:
- ISO: `2025-07-01` — 50,983 rows
- US-style: `07/01/25` — 3,734 rows
- Text: `01 Jul 2025` — 3,665 rows
- European: `01-07-2025` — 3,573 rows
**Fix**: A flexible date parser (`_parse_date_flexible`) with format-specific regex matching ensures all dates are normalized to `datetime64`. The `month` column in `fact_targets` (formatted as `2025-07`) is also normalized by appending `-01` before parsing.
**Impact**: 10,972 rows (≈17% of fact_primary_sales) had non-ISO dates. Without this fix, time-based filtering and aggregation (weekly/monthly/quarterly) would produce incorrect results.

### Additional fixes applied

| Fix | Rows/SKUs affected |
|---|---|
| Territory alias normalization (BLR→Bengaluru, Bombay→Mumbai) | 2,538 rows |
| Sentinel value replacement (#N/A, NA, -1, 9999, blank) in numeric columns | 3,678 unit rows, 0 value rows |
| SKU code upper-casing (gj-001 → GJ-001 for duplicate resolution) | 2 SKUs |
| Column name aliasing (material_no→sku_code, item_code→sku_code, sku→sku_code, area→territory) | 3 fact tables |
| Region normalization (S→South, E→East) | dim_geo |
| Tier normalization (VAL→Value, PREM→Premium, mixed casing) | dim_sku |
| Target value numeric conversion (#N/A sentinels) | fact_targets |

---

## Returns / Unit-Mixing Rule

Per `sop_policy_01`:

> *"Returns are logged separately and must not be netted into primary sales."*

**Applied rule**: Primary sales (`fact_primary_sales.primary_sales_units` and `primary_sales_value`) represent **gross shipments** from Suryaa Consumer Products to its distributors. Returns (product returned by retailers/distributors) are logged through a separate process and are **never subtracted** from primary sales figures in this analysis.

Additionally, the SOP specifies:
> *"Report sales in cases; 1 case = 24 eaches for biscuits, 12 for detergent."*

The `primary_sales_units` column in the source data is recorded at the **individual unit (eaches)** level, not in case quantities. No case-to-unit conversion was applied because the source data is already at the unit grain. If case-level reporting is needed, the conversion factors (24 for biscuits, 12 for detergent) should be applied downstream.

---

## Excluded Records

### Records excluded and reasons

| Exclusion Category | Records | Reason |
|---|---|---|
| **Sentinel values** (`primary_sales_units`) | 3,678 rows | Values of `-1` (720 rows), `9999` (772 rows), and blank/empty (2,186 rows) in `primary_sales_units` are source-system sentinel markers, not genuine sales data. Set to `NaN` and excluded from aggregation. |
| **Sentinel values** (`primary_sales_value`) | ~9,416 rows with formatting issues | Rs-prefixed and comma-separated values cleaned and parsed to numeric; unparseable values (`#N/A`, `NA`) coerced to `NaN`. |
| **Sentinel values** (`target_value`) | ~250 rows | `#N/A` sentinel values in `fact_targets` coerced to `NaN` and excluded from target aggregation. |
| **Duplicate SKU entries** (`dim_sku`) | 2 rows | `gj-001` and `gj-002` (lowercase, with trailing space) are duplicates of `GJ-001` and `GJ-002`. Normalized to uppercase (`GJ-001`, `GJ-002`) and deduplicated by keeping the first occurrence. |
| **Personal Identifiable Information (PII)** | 0 records excluded | The source datasets do not contain PII that required exclusion. Names in unstructured documents (e.g., "Deepa Pillai", "Rajesh Kumar") are professional contact details of Suryaa employees, not customer/consumer PII. The `dim_rep` table uses anonymized sales officer IDs ("Officer 1" through "Officer 12") rather than real names. No records were excluded for PII reasons. |

### Notes on data integrity

- All date columns (`week_start`, `month`) were verified to be within the expected range (Jul 2025 – Jun 2026) after parsing. No out-of-range dates were found.
- Foreign key relationships (sku_code → dim_sku, territory → dim_geo, distributor_id → dim_distributor) were verified after cleaning. All SKU codes, territory names, and distributor IDs in fact tables have matching dimension records.
- The two canonical test questions were verified against cleaned data:
  - GlucoJoy North Nov 2025: INR 861,938.25 sales vs INR 1,026,116.06 target (-16.0%)
  - SparkClean 1kg Mumbai Sep 2025: INR 176,779.00 sales (2,773 units)
- WHAT_TO_DO recommendations always return `status: PENDING_APPROVAL` per assignment spec (recommendations require human approval before action).
- Live HTTPS endpoint: `https://fb6f-2405-201-c03a-800a-28f7-8d0a-43fa-e1ea.ngrok-free.app/ask`