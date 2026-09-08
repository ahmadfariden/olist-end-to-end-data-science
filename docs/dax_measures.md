# DAX Measures — Dashboard 3 (Predictive Analytics)

## Prasyarat

`Dim_Customer` harus punya kolom:
- `repeat_purchase_probability` (dari model)
- `actual_repeat` (ground truth historis — **hanya untuk evaluasi retrospektif**, lihat disclaimer di `star_schema.md` / notebook 13)

## 1. Parameter "Top K%" (Disconnected Table)

Supaya user bisa geser slider buat pilih Top 1%, 5%, 10%, dst secara interaktif.

**Buat di Power BI:** Modeling → New Parameter → Numeric range
```
Nama: TopK_Percent
Data type: Decimal number
Minimum: 1
Maximum: 50
Increment: 1
Default: 5
```
Ini otomatis bikin tabel baru bernama `TopK_Percent` dengan measure `TopK_Percent Value`.

## 2. Measure: Rank Customer by Probability

```dax
Customer Rank =
RANKX (
    ALL ( Dim_Customer ),
    Dim_Customer[repeat_purchase_probability],
    ,
    DESC,
    DENSE
)
```

## 3. Measure: Threshold Count (jumlah customer di Top K%)

```dax
TopK Threshold Count =
VAR TotalEligible =
    CALCULATE (
        COUNTROWS ( Dim_Customer ),
        NOT ( ISBLANK ( Dim_Customer[prediction] ) )
    )
VAR PctValue = SELECTEDVALUE ( 'TopK_Percent'[TopK_Percent Value], 5 )
RETURN
    ROUNDUP ( TotalEligible * PctValue / 100, 0 )
```

## 4. Measure: Precision@Top-K (dinamis)

```dax
Precision@TopK =
VAR Threshold = [TopK Threshold Count]
VAR TopKCustomers =
    TOPN (
        Threshold,
        FILTER ( ALL ( Dim_Customer ), NOT ( ISBLANK ( Dim_Customer[prediction] ) ) ),
        Dim_Customer[repeat_purchase_probability],
        DESC
    )
VAR ActualPositiveInTopK =
    COUNTROWS ( FILTER ( TopKCustomers, [actual_repeat] = TRUE ) )
RETURN
    DIVIDE ( ActualPositiveInTopK, Threshold )
```

> Catatan: `[actual_repeat]` di dalam `FILTER` merujuk ke kolom row-context dari `TopKCustomers` (hasil `TOPN`), bukan measure — sesuaikan penulisan jadi `Dim_Customer[actual_repeat]` kalau IntelliSense Power BI menandai error konteks.

## 5. Measure: Baseline Rate

```dax
Baseline Repeat Rate =
CALCULATE (
    AVERAGE ( Dim_Customer[actual_repeat] ),
    NOT ( ISBLANK ( Dim_Customer[prediction] ) )
)
```

## 6. Measure: Lift@Top-K (dinamis)

```dax
Lift@TopK =
DIVIDE ( [Precision@TopK], [Baseline Repeat Rate] )
```

## 7. Visual yang Disarankan di Dashboard 3

| Visual | Sumber |
|---|---|
| Slicer "Top K%" | `TopK_Percent` parameter table |
| Card: Precision@TopK | Measure `[Precision@TopK]` |
| Card: Lift@TopK | Measure `[Lift@TopK]` |
| Histogram Probability Distribution | `Dim_Customer[repeat_purchase_probability]` (binned) |
| Bar chart Priority Quadrant | `Dim_Customer[priority_quadrant]`, Count of customers |
| Table "Top Customers to Target" | `Dim_Customer` di-filter Top N by `repeat_purchase_probability`, tampilkan `customer_unique_id`, `repeat_purchase_probability`, `priority_quadrant`, kolom value dari `Fact_Orders` (via measure `SUM(transaction_value)`) |

## Catatan Penting — Batasan yang Harus Disampaikan

- **`actual_repeat` cuma ada karena dataset historis.** Precision@Top-K dan Lift yang dihitung di sini adalah **evaluasi retrospektif** (menguji model terhadap outcome yang sudah diketahui), BUKAN simulasi real-time scoring produksi. Ini harus dijelaskan eksplisit kalau ditanya saat presentasi/interview.
- **Evaluasi model utama tetap di Python** (ROC-AUC, PR-AUC, threshold analysis, calibration, model comparison — notebook 09). DAX measure di atas adalah **lapisan interaktif tambahan** untuk eksplorasi bisnis, bukan pengganti evaluasi teknis yang sudah dilakukan di Python.
- Kalau nanti model dipakai untuk scoring customer benar-benar baru (belum ada di training), kolom `actual_repeat` mereka akan `BLANK` — Precision@Top-K/Lift dinamis di atas otomatis hanya berlaku untuk populasi yang punya ground truth (populasi evaluasi/backtest), bukan seluruh populasi scoring produksi.
