# Suryaa Sales Investigation — Analytical Findings Report

## Executive Summary

This report presents findings from the Suryaa Consumer Products Ltd FMCG sales data analysis. We analysed primary sales data (Jul 2025 – Jun 2026) across 15 brands, 4 product categories, 12 territories, and 24 distributors, augmented by 30 unstructured documents (emails, visit notes, circulars, policies). The analysis answers What / Why / What-to-do questions using a multi-agent AI assistant.

---

## 1. WHAT Analysis: GlucoJoy Monthly Sales vs Target — North Region, November 2025

### Query
> "What were GlucoJoy's monthly primary sales vs target in the North region in November 2025?"

### Result
| Metric | Value |
|---|---|
| Primary sales value | INR 861,938.25 |
| Primary sales units | 43,147 units |
| Target value | INR 1,026,116.06 |
| Variance | **-16.0%** (below target) |

### Interpretation
GlucoJoy underperformed against its North region target by 16% in November 2025. The North region comprises Delhi, Lucknow, and Jaipur territories. The shortfall suggests potential issues in distribution execution, competitor activity, or demand softness during this period.

### Data Sources
- `fact_primary_sales`: Weekly primary sales aggregated to monthly grain
- `fact_targets`: Monthly target values
- `dim_sku`: Brand mapping (GlucoJoy SKUs: GJ-001 through GJ-009)
- `dim_geo`: Region hierarchy (North → Delhi, Lucknow, Jaipur)

---

## 2. WHY Analysis: SparkClean 1kg Sales Spike — Mumbai, September 2025

### Query
> "Why did SparkClean 1kg primary sales spike in Mumbai in the week of 16 Sep 2025?"

### Finding
The sales spike is causally explained by a **price-off promotion** documented in the internal trade circular.

### Evidence
| Evidence Source | Content |
|---|---|
| `promo_circular_01` | "SparkClean 1kg price-off promo in Mumbai w/c 16 Sep" |
| `promotions` table | Confirms: SC-004 (SparkClean Regular 1kg), territory Mumbai, promo_type=PriceOff, discount=15%, week_start=2025-09-16 |

### Sales Data Correlation
SparkClean 1kg (SKUs SC-004, SC-005, SC-006) in Mumbai recorded INR 176,779 in sales during the promo month (September 2025) across 2,773 units, representing a significant uplift from baseline weeks.

---

## 3. WHY Analysis: GlucoJoy Choco 120g Stockout — Delhi

### Query
> "Why did GlucoJoy Choco 120g stockout in Delhi?"

### Finding
The stockout was caused by a **supplier delay**, compounded by a **Diwali supply shortfall** in the North region.

### Evidence
| Evidence Source | Content |
|---|---|
| `email_01` | "supplier delay caused GlucoJoy Choco 120g stockout in Delhi" |
| `email_02` | "GlucoJoy Choco 120g supply shortfall during Diwali peak in North" |

### Supporting Data
The stockout record (`stockouts` table) shows GJ-003 (GlucoJoy Choco 120g) in Delhi with a stockout_flag=1 and stockout_days=5 for the week of 2025-11-11. Per SOP policy_01, stockouts exceeding 3 days require escalation.

---

## 4. WHAT_TO_DO: Stockout in Chennai

### Query
> "What should we do about the stockout in Chennai?"

### Recommendations

**Recommendation 1 (Confidence: 85%)**
- **Action**: Escalate stockout for CO-004 (CrunchO Choco 120g) in Chennai (4.0 days). Per SOP policy, stockouts exceeding 3 days require escalation.
- **Evidence**: Stockout record confirms CO-004 in Chennai for 4.0 days. SOP policy_01 mandates escalation for stockouts >3 days.

**Recommendation 2 (Confidence: 75%)**
- **Action**: Identify alternate suppliers to mitigate supplier delay risks.
- **Evidence**: Historical pattern — supplier delay caused GlucoJoy Choco 120g stockout in Delhi (email_01).

---

## 5. WHAT_TO_DO: Improve SparkClean Sales

### Query
> "Recommend actions to improve SparkClean sales"

### Recommendations

**Recommendation 1 (Confidence: 80%)**
- **Action**: Extend or replicate the price-off promotion to boost sales in similar territories.
- **Evidence**: The SparkClean 1kg price-off promo in Mumbai (promo_circular_01) successfully drove a sales spike.

**Recommendation 2 (Confidence: 65%)**
- **Action**: Analyze current brand performance: SparkClean generated INR 109,127,781 in sales. Review distribution coverage and retailer feedback.
- **Evidence**: Sales data shows strong overall brand performance; potential for further growth via distribution expansion.

---

## 6. Cross-Cutting Observations

### Data Quality Issues Identified
1. **Date format inconsistencies**: fact_primary_sales uses ISO (2025-07-01), US-style (07/01/25), European (01-07-2025), and text (01 Jul 2025) formats in the same column
2. **Column name inconsistencies**: The same product identifier is called `sku_code`, `material_no`, `item_code`, and `sku` across different tables
3. **Sentinel values**: `#N/A`, `-1`, `9999` used as sentinels for missing/invalid data
4. **Currency formatting**: Values appear as plain numbers, comma-separated ("4,792"), Rs-prefixed ("Rs 4,582"), and quoted ("Rs 3,589")
5. **Territory aliases**: "Bombay" and "BLR" used interchangeably with "Mumbai" and "Bengaluru"
6. **Duplicate SKU entries**: gj-001 and gj-002 appear in both lowercase and uppercase in dim_sku

### Analytical Coverage
- **Time period**: July 2025 – June 2026 (12 months)
- **Product categories**: Biscuits, Tea, Detergent, Shampoo, Snacks
- **Brands**: 15 brands across 5 categories
- **Territories**: 12 territories in 4 regions (North, South, East, West)
- **Unstructured documents**: 30 documents, of which ~7 contained actionable sales intelligence (promotions, stockouts, competitor activity, pricing changes)

---

## Methodology

Data was loaded from 8 CSV files into pandas DataFrames, cleaned through a pipeline that normalizes column names, dates, sentinel values, and geographical aliases. The cleaned data was then queried by intent-specific agents:

1. **WHAT Agent**: Parses questions for entities (brand, geography, time), filters and aggregates sales data, computes target comparisons
2. **WHY Agent**: Retrieves relevant documents via keyword search, correlates findings with sales data, returns evidence-grounded explanations
3. **WHAT_TO_DO Agent**: Gathers evidence from docs and data, generates recommendations with per-item confidence scores

All answers are grounded exclusively in the provided data. Confidence thresholds determine response status: OK (≥0.7), PENDING_APPROVAL (0.3–0.7), ABSTAINED (<0.3).

---

*Report generated by the Suryaa Sales Assistant AI — August 2026*