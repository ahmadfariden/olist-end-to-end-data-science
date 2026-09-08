# MongoDB Schema — Olist Data Pipeline

## Database: `olist_db`

MongoDB dipakai sebagai **dua layer**: Raw Storage Layer (data mentah, tidak dimodifikasi) dan Prediction Layer (hasil scoring model). Koneksi: `mongodb://localhost:27017/`.

```
olist_db
│
├── RAW LAYER (9 collections, dari notebook 01)
│   ├── customers_raw
│   ├── orders_raw
│   ├── order_items_raw
│   ├── payments_raw
│   ├── reviews_raw
│   ├── products_raw
│   ├── sellers_raw
│   ├── geolocation_raw
│   └── category_translation_raw
│
└── PREDICTION LAYER (1 collection, dari notebook 11)
    └── customer_predictions
```

---

## RAW LAYER

**Prinsip:** raw collection **tidak pernah dimodifikasi** setelah ingestion (Fase 0, Aturan #1). Semua cleaning/transformasi dilakukan di Python (Pandas), bukan di MongoDB. Insert dilakukan lewat `insert_many()`, dengan `drop()` collection dulu di awal supaya notebook ingestion idempotent (bisa di-run ulang tanpa duplikat).

| Collection | Jumlah Dokumen | Sumber CSV | Field Kunci |
|---|---:|---|---|
| `customers_raw` | 99,441 | `olist_customers_dataset.csv` | `customer_id`, `customer_unique_id` |
| `orders_raw` | 99,441 | `olist_orders_dataset.csv` | `order_id`, `customer_id` |
| `order_items_raw` | 112,650 | `olist_order_items_dataset.csv` | `order_id`, `product_id`, `seller_id` |
| `payments_raw` | 103,886 | `olist_order_payments_dataset.csv` | `order_id` |
| `reviews_raw` | 99,224 | `olist_order_reviews_dataset.csv` | `order_id` |
| `products_raw` | 32,951 | `olist_products_dataset.csv` | `product_id` |
| `sellers_raw` | 3,095 | `olist_sellers_dataset.csv` | `seller_id` |
| `geolocation_raw` | 1,000,163 | `olist_geolocation_dataset.csv` | `geolocation_zip_code_prefix` |
| `category_translation_raw` | 71 | `product_category_name_translation.csv` | `product_category_name` |

**Validasi ingestion (Fase 1.4):** CSV row count vs MongoDB document count — semua 9 collection **match, 0 selisih**.

**Contoh dokumen `orders_raw`:**
```json
{
  "_id": ObjectId("..."),
  "order_id": "e481f51cbdc54678b7cc49136f2d6af7",
  "customer_id": "9ef432eb6251297304e76186b10a928d",
  "order_status": "delivered",
  "order_purchase_timestamp": "2017-10-02 10:56:33",
  "order_approved_at": "2017-10-02 11:07:15",
  "order_delivered_carrier_date": "2017-10-04 19:55:00",
  "order_delivered_customer_date": "2017-10-10 21:25:13",
  "order_estimated_delivery_date": "2017-10-18 00:00:00"
}
```

---

## PREDICTION LAYER

**Collection:** `customer_predictions`

Dibuat di notebook 11, di-drop & re-insert tiap kali notebook dijalankan ulang (idempotent). Berisi hasil scoring model untuk seluruh eligible population (54,738 customer, dari Decision Gate Fase 7).

**Skema dokumen (final, setelah threshold-lock fix):**
```json
{
  "_id": ObjectId("..."),
  "customer_unique_id": "3e43e6105506432c953e165fb2acf44c",
  "repeat_purchase_probability": 0.998548,
  "prediction": 1,
  "threshold_used": 0.5971,
  "threshold_method": "top_5_percent_locked_from_test_set",
  "customer_value_observation": 1172.66,
  "value_band": "High Value",
  "model": "LogisticRegression",
  "scoring_date": "2026-09-03"
}
```

| Field | Tipe | Deskripsi |
|---|---|---|
| `customer_unique_id` | string | Key penghubung ke `customers_raw`. |
| `repeat_purchase_probability` | float | Output model, **ranking score** (bukan probabilitas terkalibrasi — model dilatih `class_weight="balanced"`). |
| `prediction` | int (0/1) | Label biner, diturunkan dari `threshold_used`. |
| `threshold_used` | float | Nilai cutoff probability. **Dikunci dari evaluasi test-set** (notebook 09 section 6.1), disimpan di `models/threshold_top_k.json`, di-load ulang di notebook 10 — bukan dihitung ulang dari populasi scoring. |
| `threshold_method` | string | Deskripsi cara threshold ditentukan, untuk audit trail. |
| `customer_value_observation` | float | Total spending customer dalam observation window (bukan `customer_value_full` — information set harus sama dengan feature model, lihat `assumptions_and_limitations.md`). |
| `value_band` | string | `"High Value"` / `"Low Value"`, dari median split `customer_value_observation`. |
| `model` | string | Nama model yang dipakai scoring. |
| `scoring_date` | string | Tanggal batch scoring dijalankan. |

**Validasi:** 2,857 dokumen (5.22% dari 54,738 eligible customer), CSV row count vs MongoDB document count match.

---

## Query Contoh

```python
from pymongo import MongoClient
client = MongoClient("mongodb://localhost:27017/")
db = client["olist_db"]

# Cek dua layer
print("RAW:", [c for c in db.list_collection_names() if c.endswith("_raw")])
print("PREDICTION:", [c for c in db.list_collection_names() if c == "customer_predictions"])

# Ambil semua customer prioritas (prediction=1), urut probability tertinggi
top_customers = list(
    db.customer_predictions.find({"prediction": 1})
    .sort("repeat_purchase_probability", -1)
)
```

## Catatan Operasional

- **Batch scoring saat ini manual** (notebook-based) — bukan real-time/scheduled. Lihat `docs/business_recommendations.md` section 13.6 untuk proposed production schedule.
- Kalau model di-retrain di masa depan, `threshold_top_k.json` **harus dikunci ulang** dari evaluasi test-set model versi baru — jangan mewariskan threshold lama begitu saja.
