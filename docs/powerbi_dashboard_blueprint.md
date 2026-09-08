# Power BI Dashboard Blueprint — Olist Repeat Purchase Prediction

> Sumber data: 8 tabel di `data_mart/` (`Dim_Customer`, `Dim_Product`, `Dim_Seller`, `Dim_Date`, `Dim_Geolocation`, `Fact_Orders`, `Fact_Order_Items`, `Fact_Payments`). Relasi mengikuti `docs/star_schema.md`.

---

## DAX Measures — Buat Semua Ini Dulu Sebelum Bikin Visual

Taruh semua measure di satu tabel khusus (disarankan bikin dulu: Modeling → New Table → ketik `Measures = {}` untuk bikin tabel kosong sebagai "rumah" measure, lalu klik kanan → New Measure di dalam tabel itu).

### Measures Dasar (Sheet 1 & 2)

```dax
Total Transaction Value = SUM ( Fact_Orders[transaction_value] )

Total Orders = DISTINCTCOUNT ( Fact_Orders[order_id] )

Total Customers = DISTINCTCOUNT ( Fact_Orders[customer_unique_id] )

Average Order Value = DIVIDE ( [Total Transaction Value], [Total Orders] )

Avg Review Score = AVERAGE ( Fact_Orders[review_score] )

Total Item Value = SUM ( Fact_Order_Items[price] )
```

### Measures Customer Behavior (Sheet 2)

```dax
Orders per Customer Table =
SUMMARIZE (
    Fact_Orders,
    Dim_Customer[customer_unique_id],
    "OrderCount", DISTINCTCOUNT ( Fact_Orders[order_id] ),
    "Spending", SUM ( Fact_Orders[transaction_value] )
)

Repeat Customer Rate =
VAR CustomerOrders = [Orders per Customer Table]
VAR RepeatCustomers = COUNTROWS ( FILTER ( CustomerOrders, [OrderCount] > 1 ) )
VAR TotalCust = COUNTROWS ( CustomerOrders )
RETURN
    DIVIDE ( RepeatCustomers, TotalCust )

Avg Order Count per Customer =
AVERAGEX (
    VALUES ( Dim_Customer[customer_unique_id] ),
    CALCULATE ( DISTINCTCOUNT ( Fact_Orders[order_id] ) )
)

Avg Spending per Customer =
AVERAGEX (
    VALUES ( Dim_Customer[customer_unique_id] ),
    CALCULATE ( SUM ( Fact_Orders[transaction_value] ) )
)

Max Order Date (Global) =
CALCULATE ( MAX ( Fact_Orders[order_purchase_date] ), ALL ( Fact_Orders ) )

Avg Recency Days =
AVERAGEX (
    VALUES ( Dim_Customer[customer_unique_id] ),
    DATEDIFF ( CALCULATE ( MAX ( Fact_Orders[order_purchase_date] ) ), [Max Order Date (Global)], DAY )
)
```

### Measures Predictive Analytics (Sheet 3) — dari `docs/dax_measures.md`

```dax
Customer Rank =
RANKX ( ALL ( Dim_Customer ), Dim_Customer[repeat_purchase_probability], , DESC, DENSE )

TopK Threshold Count =
VAR TotalEligible =
    CALCULATE ( COUNTROWS ( Dim_Customer ), NOT ( ISBLANK ( Dim_Customer[prediction] ) ) )
VAR PctValue = SELECTEDVALUE ( 'TopK_Percent'[TopK_Percent Value], 5 )
RETURN
    ROUNDUP ( TotalEligible * PctValue / 100, 0 )

Precision@TopK =
VAR Threshold = [TopK Threshold Count]
VAR TopKCustomers =
    TOPN (
        Threshold,
        FILTER ( ALL ( Dim_Customer ), NOT ( ISBLANK ( Dim_Customer[prediction] ) ) ),
        Dim_Customer[repeat_purchase_probability], DESC
    )
VAR ActualPositiveInTopK =
    COUNTROWS ( FILTER ( TopKCustomers, [actual_repeat] = TRUE ) )
RETURN
    DIVIDE ( ActualPositiveInTopK, Threshold )

Baseline Repeat Rate =
CALCULATE (
    AVERAGE ( Dim_Customer[actual_repeat] ),
    NOT ( ISBLANK ( Dim_Customer[prediction] ) )
)

Lift@TopK = DIVIDE ( [Precision@TopK], [Baseline Repeat Rate] )

Total Eligible Customers =
CALCULATE ( COUNTROWS ( Dim_Customer ), NOT ( ISBLANK ( Dim_Customer[prediction] ) ) )
```

### Tabel Tambahan untuk Lift Curve (Sheet 3)

Bikin **calculated table** baru (Modeling → New Table):
```dax
TopK_Curve_Points = { 1, 2, 5, 10, 15, 20, 25, 30 }
```
Lalu rename kolom hasilnya jadi `K_Percent` (klik kanan kolom → Rename).

Measure khusus untuk chart Lift Curve (pakai baris `TopK_Curve_Points`, bukan parameter slider):
```dax
Precision@K (Curve) =
VAR Threshold =
    ROUNDUP ( [Total Eligible Customers] * SELECTEDVALUE ( TopK_Curve_Points[K_Percent] ) / 100, 0 )
VAR TopKCustomers =
    TOPN (
        Threshold,
        FILTER ( ALL ( Dim_Customer ), NOT ( ISBLANK ( Dim_Customer[prediction] ) ) ),
        Dim_Customer[repeat_purchase_probability], DESC
    )
RETURN
    DIVIDE ( COUNTROWS ( FILTER ( TopKCustomers, [actual_repeat] = TRUE ) ), Threshold )

Lift@K (Curve) = DIVIDE ( [Precision@K (Curve)], [Baseline Repeat Rate] )
```

### Measures Financial Impact (Sheet 3) — dari Fase 13, notebook 11

```dax
Cost Per Contact = 5.0          -- ASUMSI ILUSTRATIF, ganti dengan angka riil
Value Per Repeat Customer = 163.08   -- ASUMSI ILUSTRATIF (proxy avg customer_value_observation)

N Contacted (TopK) = [TopK Threshold Count]

Net Benefit Random =
VAR ExpectedConv = [N Contacted (TopK)] * [Baseline Repeat Rate]
VAR Revenue = ExpectedConv * [Value Per Repeat Customer]
VAR Cost = [N Contacted (TopK)] * [Cost Per Contact]
RETURN
    Revenue - Cost

Net Benefit Model =
VAR ExpectedConv = [N Contacted (TopK)] * [Precision@TopK]
VAR Revenue = ExpectedConv * [Value Per Repeat Customer]
VAR Cost = [N Contacted (TopK)] * [Cost Per Contact]
RETURN
    Revenue - Cost

Net Benefit Uplift = [Net Benefit Model] - [Net Benefit Random]
```

---

## Parameter — Buat Sebelum Sheet 3

**Modeling → New Parameter → Numeric range:**
```
Nama       : TopK_Percent
Data type  : Decimal number
Minimum    : 1
Maximum    : 50
Increment  : 1
Default    : 5
```
(Ini otomatis bikin tabel `TopK_Percent` dan measure `TopK_Percent Value` — dipakai di beberapa measure atas.)

---

## SHEET 1 — Business Overview

**Judul layout (text box paling atas):** `Business Overview — Olist E-Commerce Performance`

### Cards (baris atas, 5 card berjajar)
| Card | Measure |
|---|---|
| Total Transaction Value | `[Total Transaction Value]` |
| Total Orders | `[Total Orders]` |
| Total Customers | `[Total Customers]` |
| Average Order Value | `[Average Order Value]` |
| Avg Review Score | `[Avg Review Score]` |

### Charts
| Chart | Tipe | Judul | X-Axis | Y-Axis |
|---|---|---|---|---|
| 1 | Line chart | "Transaction Value Trend by Month" | `Dim_Date[year_month]` | `[Total Transaction Value]` |
| 2 | Bar chart (horizontal) | "Top 10 Product Categories by Transaction Value" | `Dim_Product[category]` (Top N filter = 10, by `[Total Item Value]`) | `[Total Item Value]` |
| 3 | Bar chart | "Orders by Customer State" | `Dim_Customer[customer_state]` | `[Total Orders]` |
| 4 | Donut chart | "Order Status Distribution" | Legend: `Fact_Orders[order_status]` | Values: `[Total Orders]` |

### Slicers
- `Dim_Date[year]` (atau `year_month` sebagai range slider)
- `Dim_Customer[customer_state]`

### Tabel
Tidak ada tabel detail di sheet ini (murni summary/overview).

---

## SHEET 2 — Customer Behavior

**Judul layout (text box paling atas):** `Customer Behavior — RFM & Segmentation`

### Cards (baris atas, 4 card berjajar)
| Card | Measure |
|---|---|
| Total Customers | `[Total Customers]` |
| Repeat Customer Rate | `[Repeat Customer Rate]` (format: percentage) |
| Avg Order Count per Customer | `[Avg Order Count per Customer]` |
| Avg Spending per Customer | `[Avg Spending per Customer]` |

### Charts
| Chart | Tipe | Judul | X-Axis | Y-Axis |
|---|---|---|---|---|
| 1 | Donut chart | "Customer Segment Distribution" | Legend: `Dim_Customer[segment]` | Values: `[Total Customers]` |
| 2 | Bar chart (clustered) | "Avg Spending & Order Count by Segment" | `Dim_Customer[segment]` | `[Avg Spending per Customer]` dan `[Avg Order Count per Customer]` (2 measure di satu chart) |
| 3 | Bar chart | "Avg Recency by Segment" | `Dim_Customer[segment]` | `[Avg Recency Days]` |

### Slicers
- `Dim_Customer[segment]`
- `Dim_Customer[customer_state]`

### Tabel
| Tabel | Kolom | Sumber |
|---|---|---|
| "Customer Segment Summary" | Segment, Total Customers, Avg Order Count, Avg Spending, Avg Recency | `Dim_Customer[segment]` + measures `[Total Customers]`, `[Avg Order Count per Customer]`, `[Avg Spending per Customer]`, `[Avg Recency Days]` |

---

## SHEET 3 — Predictive Analytics (DASHBOARD UTAMA)

**Judul layout (text box paling atas):** `Predictive Analytics — Repeat Purchase Prioritization`

### Slicer utama (taruh paling atas/menonjol, bukan di sidebar biasa)
- **`TopK_Percent` parameter** (slider) — ini kontrol utama seluruh sheet

### Cards (baris atas, 5 card berjajar)
| Card | Measure |
|---|---|
| Total Eligible Customers (Scored) | `[Total Eligible Customers]` |
| Precision@TopK | `[Precision@TopK]` (format: percentage) |
| Lift@TopK | `[Lift@TopK]` (format: "0.00x") |
| Net Benefit (Model-based) | `[Net Benefit Model]` |
| Net Benefit Uplift vs Random | `[Net Benefit Uplift]` |

### Charts
| Chart | Tipe | Judul | X-Axis | Y-Axis |
|---|---|---|---|---|
| 1 | Histogram | "Repeat Purchase Probability Distribution" | `Dim_Customer[repeat_purchase_probability]` (binned, ~20 bins) | Count of `Dim_Customer[customer_unique_id]` |
| 2 | Bar chart | "Priority Quadrant Distribution" | `Dim_Customer[priority_quadrant]` | Count of `Dim_Customer[customer_unique_id]` |
| 3 | Line chart | "Lift Curve by Top-K%" | `TopK_Curve_Points[K_Percent]` | `[Lift@K (Curve)]` |
| 4 | Line chart (opsional, gabung dgn chart 3 pakai dual axis) | "Precision Curve by Top-K%" | `TopK_Curve_Points[K_Percent]` | `[Precision@K (Curve)]` |

### Slicers Tambahan
- `Dim_Customer[priority_quadrant]`
- `Dim_Customer[value_band]`

### Tabel
| Tabel | Kolom | Sumber |
|---|---|---|
| "Top Customers to Target" | Customer ID, Probability, Priority Quadrant, Value Band, Total Spending | `Dim_Customer[customer_unique_id]`, `Dim_Customer[repeat_purchase_probability]`, `Dim_Customer[priority_quadrant]`, `Dim_Customer[value_band]`, measure `[Total Transaction Value]` (via relasi ke Fact_Orders) — **filter**: `Dim_Customer[prediction] = TRUE`, sort descending by probability |

---

## Catatan Terakhir Sebelum Mulai

1. Bikin **Measures dulu semua** (bagian paling atas dokumen ini) sebelum mulai drag visual — supaya pas bikin chart, measure-nya udah tersedia di panel Fields.
2. Parameter `TopK_Percent` harus dibuat **sebelum** measure yang mereferensikannya (`TopK Threshold Count`, dst).
3. Tabel `TopK_Curve_Points` (calculated table) juga harus dibuat sebelum measure `Precision@K (Curve)` / `Lift@K (Curve)`.
4. Kalau ada measure yang error pas dibuat karena referensi measure lain belum ada — urutannya emang harus: Parameter → Measures dasar → TopK_Curve_Points table → Measures yang bergantung ke situ.
