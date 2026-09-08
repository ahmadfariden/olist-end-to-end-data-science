# Star Schema — Olist Data Mart

## 1. Grain Definition

| Tabel | Tipe | Grain (1 baris = ) | Primary Key |
|---|---|---|---|
| `Dim_Customer` | Dimension | 1 customer | `customer_unique_id` |
| `Dim_Product` | Dimension | 1 produk | `product_id` |
| `Dim_Seller` | Dimension | 1 seller | `seller_id` |
| `Dim_Date` | Dimension | 1 tanggal kalender | `date_key` |
| `Dim_Geolocation` | Dimension | 1 zip code prefix | `zip_code_prefix` |
| `Fact_Orders` | Fact | 1 order | `order_id` |
| `Fact_Order_Items` | Fact | 1 baris produk dalam 1 order | `order_id` + `order_item_id` |
| `Fact_Payments` | Fact | 1 payment record (order bisa >1, misal cicilan) | `order_id` + `payment_sequential` |

---

## 2. Relationship Diagram

```
                              Dim_Date
                                 │
                    ┌────────────┼────────────┐
                    │            │            │
              Fact_Orders  Fact_Order_Items  Fact_Payments
                    │            │            │
                    └──────┬─────┴─────┬──────┘
                           │           │
                    Dim_Customer   (via customer_unique_id,
                           │        didenormalisasi di ketiga fact table)
                           │
                    Dim_Geolocation
                    (via zip_code_prefix,
                     role-playing: dipakai juga oleh Dim_Seller)


              Fact_Order_Items
                    │
          ┌─────────┼─────────┐
          ▼         ▼         ▼
     Dim_Product  Dim_Seller  (customer_unique_id → Dim_Customer,
                                order_purchase_date → Dim_Date)
                     │
              Dim_Geolocation
              (via zip_code_prefix, role-playing kedua)
```

**Kenapa `Fact_Order_Items` jadi tabel jembatan utama:** ini satu-satunya fact table yang punya `customer_unique_id`, `product_id`, `seller_id`, dan `order_purchase_date` sekaligus — sehingga slicer dari `Dim_Customer` bisa memfilter sampai ke `Dim_Product`/`Dim_Seller`, dan sebaliknya, tanpa perlu melalui tabel perantara lain.

---

## 3. Cardinality & Relasi per Tabel

| Dari | Ke | Kolom Kunci | Kardinalitas | Cross-filter Direction |
|---|---|---|---|---|
| `Dim_Customer` | `Fact_Orders` | `customer_unique_id` | 1 : Banyak | Both |
| `Dim_Customer` | `Fact_Order_Items` | `customer_unique_id` | 1 : Banyak | Both |
| `Dim_Customer` | `Fact_Payments` | `customer_unique_id` | 1 : Banyak | Both |
| `Dim_Product` | `Fact_Order_Items` | `product_id` | 1 : Banyak | Both |
| `Dim_Seller` | `Fact_Order_Items` | `seller_id` | 1 : Banyak | Both |
| `Dim_Date` | `Fact_Orders` | `date_key` ↔ `order_purchase_date` | 1 : Banyak | Single (Date → Fact) |
| `Dim_Date` | `Fact_Order_Items` | `date_key` ↔ `order_purchase_date` | 1 : Banyak | Single (Date → Fact) |
| `Dim_Date` | `Fact_Payments` | `date_key` ↔ `order_purchase_date` | 1 : Banyak | Single (Date → Fact) |
| `Dim_Geolocation` | `Dim_Customer` | `zip_code_prefix` | 1 : Banyak | Single (Geo → Customer) |
| `Dim_Geolocation` | `Dim_Seller` | `zip_code_prefix` | 1 : Banyak | **Inactive** (role-playing, lihat catatan) |

**Catatan role-playing dimension:** `Dim_Geolocation` dipakai oleh **dua** tabel berbeda (`Dim_Customer` untuk lokasi pembeli, `Dim_Seller` untuk lokasi penjual). Power BI tidak mengizinkan dua relationship aktif dari tabel yang sama ke tabel yang sama — jadi relasi kedua (`Dim_Geolocation` ↔ `Dim_Seller`) harus dibuat **Inactive**, dan diaktifkan secara kondisional lewat DAX `USERELATIONSHIP()` di measure yang butuh geo seller (misal "Avg Delivery Days by Seller Region").

---

## 4. Catatan Penting Sebelum Setup di Power BI

1. **Jangan denormalisasi ulang angka agregat** (`total_orders`, `total_spending`, dst) ke `Dim_Customer`. Angka-angka itu dihitung via **measure DAX** (`SUM`, `COUNT`, `AVERAGE`) dari `Fact_Orders`/`Fact_Order_Items` di Power BI — supaya angkanya otomatis ikut ter-filter oleh slicer apapun, bukan angka statis yang sudah "beku" dari notebook.

2. **`Dim_Customer` punya baris dengan `prediction`/`segment`/`priority_quadrant` = NULL.** Ini customer yang tidak eligible di observation window ML (Fase 7). Jangan di-exclude begitu saja dari model — mereka tetap valid untuk Dashboard 1-4 (business analytics), cuma nggak punya skor ML.

3. **`order_purchase_date` di tiap fact table sudah dinormalisasi ke tengah malam** (tanpa jam/menit/detik), supaya relasi ke `Dim_Date.date_key` presisi (Power BI relationship butuh exact match, bukan range).

4. **`Fact_Orders` vs `Fact_Order_Items` vs `Fact_Payments` — jangan dijumlahkan silang tanpa sadar grain-nya beda.** Misalnya `SUM(transaction_value)` dari `Fact_Orders` sudah benar per order, tapi kalau join ke `Fact_Order_Items` (grain lebih detail) lalu di-sum lagi, angkanya bisa salah kalau tidak hati-hati (potensi double counting kalau tidak pakai measure yang tepat).

---

## 5. Kaitan dengan Dashboard (Fase 12)

| Dashboard | Fact/Dimension Utama |
|---|---|
| 1 — Executive Overview | `Fact_Orders` + `Dim_Date` |
| 2 — Customer Analytics | `Dim_Customer` + `Fact_Orders` |
| 3 — Product & Seller Performance | `Fact_Order_Items` + `Dim_Product` + `Dim_Seller` |
| 4 — Delivery Performance | `Fact_Orders` + `Dim_Geolocation` (via `Dim_Customer`) |
| 5 — Predictive Analytics | `Dim_Customer` (kolom `prediction`, `priority_quadrant`, `value_band`) |
