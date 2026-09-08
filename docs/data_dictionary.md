# Data Dictionary — Olist Raw Dataset

## Ringkasan Tabel

| Tabel | Grain (1 baris = ) | Primary Key | Jumlah Baris |
|---|---|---|---|
| `olist_customers_dataset` | 1 customer record per order | `customer_id` | 99,441 |
| `olist_orders_dataset` | 1 order | `order_id` | 99,441 |
| `olist_order_items_dataset` | 1 produk dalam 1 order | `order_id` + `order_item_id` | 112,650 |
| `olist_order_payments_dataset` | 1 payment record (order bisa >1, misal cicilan) | `order_id` + `payment_sequential` | 103,886 |
| `olist_order_reviews_dataset` | 1 review | `review_id` | 99,224 |
| `olist_products_dataset` | 1 produk | `product_id` | 32,951 |
| `olist_sellers_dataset` | 1 seller | `seller_id` | 3,095 |
| `olist_geolocation_dataset` | banyak baris per zip code prefix (TIDAK 1:1) | — | 1,000,163 |
| `product_category_name_translation` | 1 kategori (lookup PT→EN) | `product_category_name` | 71 |

---

## `olist_customers_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `customer_id` | string | Identifier customer **per order** (primary key tabel ini). Berbeda tiap order, meski dilakukan customer yang sama. |
| `customer_unique_id` | string | Identifier customer sebenarnya, konsisten lintas order. **Wajib dipakai untuk analisis level customer** (repeat purchase, segmentasi, dst). |
| `customer_zip_code_prefix` | string | 5 digit awal kode pos, penghubung ke `Dim_Geolocation`. |
| `customer_city`, `customer_state` | string | Lokasi customer. |

> ⚠️ **Relasi penting:** satu `customer_unique_id` bisa punya banyak `customer_id` (satu per order). Salah pakai `customer_id` untuk analisis customer-level membuat tiap customer terlihat cuma order sekali.

---

## `olist_orders_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `order_id` | string | Primary key. |
| `customer_id` | string | FK ke `olist_customers_dataset`. |
| `order_status` | string | `delivered`, `shipped`, `canceled`, `unavailable`, `invoiced`, `processing`, `created`, `approved`. |
| `order_purchase_timestamp` | datetime | Waktu order dibuat. |
| `order_approved_at` | datetime | Waktu pembayaran disetujui. Bisa NULL (order belum diapprove). |
| `order_delivered_carrier_date` | datetime | Waktu diserahkan ke kurir. Bisa NULL. |
| `order_delivered_customer_date` | datetime | Waktu diterima customer. **Bisa NULL** untuk order yang belum/tidak delivered — ini valid, bukan error data (2.98% dari total order). |
| `order_estimated_delivery_date` | datetime | Estimasi tanggal terima. |

---

## `olist_order_items_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `order_id` | string | FK ke `orders`. Satu order bisa punya banyak baris di sini (1 baris = 1 produk). |
| `order_item_id` | int | Nomor urut item dalam order. |
| `product_id` | string | FK ke `products`. |
| `seller_id` | string | FK ke `sellers`. |
| `price` | float | Harga produk (belum termasuk ongkir). |
| `freight_value` | float | Biaya ongkos kirim. |

---

## `olist_order_payments_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `order_id` | string | FK ke `orders`. Satu order bisa punya >1 baris (cicilan). |
| `payment_sequential` | int | Urutan pembayaran dalam order. |
| `payment_type` | string | `credit_card`, `boleto`, `voucher`, `debit_card`. |
| `payment_installments` | int | Jumlah cicilan. |
| `payment_value` | float | Nilai pembayaran per baris — dijumlahkan per `order_id` untuk dapat `transaction_value` per order. |

---

## `olist_order_reviews_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `review_id` | string | Primary key. |
| `order_id` | string | FK ke `orders`. |
| `review_score` | int | 1–5. |

---

## `olist_products_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `product_id` | string | Primary key. |
| `product_category_name` | string | Nama kategori (Bahasa Portugis) — join ke `product_category_name_translation` untuk versi Inggris. |

---

## `olist_sellers_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `seller_id` | string | Primary key. |
| `seller_zip_code_prefix` | string | Penghubung ke `Dim_Geolocation`. |
| `seller_city`, `seller_state` | string | Lokasi seller. |

---

## `olist_geolocation_dataset`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `geolocation_zip_code_prefix` | string | **Bukan primary key** — satu prefix bisa punya banyak baris koordinat berbeda. |
| `geolocation_lat`, `geolocation_lng` | float | Koordinat. |
| `geolocation_city`, `geolocation_state` | string | Lokasi. |

> ⚠️ **Wajib diagregasi** (median lat/lng, mode city/state per prefix) sebelum dipakai join — kalau tidak, menyebabkan row multiplication. Hasil agregasi: 1,000,163 baris → 19,015 baris (1 baris = 1 prefix).

---

## `product_category_name_translation`

| Kolom | Tipe | Deskripsi |
|---|---|---|
| `product_category_name` | string | Kategori versi Portugis (PK, join key ke `products`). |
| `product_category_name_english` | string | Versi Inggris, dipakai di semua dashboard/analisis. |

---

## Diagram Relasi Inti

```
customers (customer_id) ──< orders (order_id) ──< order_items ──> products
                                    │                    │
                                    │                    └──> sellers
                                    ├──< payments
                                    └──< reviews

customer_unique_id
        │
        ├── customer_id ── order
        ├── customer_id ── order
        └── customer_id ── order
```

**Validasi foreign key (notebook 02):** 0 orphan record ditemukan di 6 relasi yang dicek (`orders↔customers`, `order_items↔orders/products/sellers`, `payments↔orders`, `reviews↔orders`) — kualitas relational integrity dataset ini bersih.