# Methodology — Olist Repeat Purchase Prediction

## 1. Problem Framing

**Business question:** *"Customer mana yang berpotensi melakukan repeat purchase, sehingga tim marketing bisa memprioritaskan intervensi retensi secara terarah — bukan massal?"*

**Kenapa bukan "churn prediction":** dataset Olist tidak menyediakan label churn eksplisit (tidak ada definisi "customer dianggap churn setelah X hari tidak order"). Target yang dipilih — **Repeat Purchase Classification** — lebih realistis karena bisa didefinisikan presisi dari data yang tersedia, tanpa asumsi tambahan yang tidak terverifikasi.

**Definisi target (presisi):**
> Target = 1 jika customer (`customer_unique_id`) melakukan ≥1 order baru selama prediction window, setelah memiliki ≥1 order pada observation window.
> Target = 0 jika tidak.

Populasi target dibatasi pada **eligible customer** — yang punya histori order di observation window (bukan semua `customer_unique_id` di dataset).

---

## 2. Observation & Prediction Window — Data-Driven, Bukan Asumsi

Prinsip: *"Roadmap = baseline, data aktual = hakimnya."* Window ditentukan lewat proses berikut, bukan angka tebak-tebakan:

```
Plot distribusi order_purchase_timestamp
        ↓
Deteksi bulan tidak lengkap (volume < 50% median) → exclude
        ↓
Sensitivity analysis: coba beberapa panjang prediction window (3, 4, 6 bulan)
        ↓
Bandingkan positive cases & rate tiap window
        ↓
Pilih window berdasarkan BUSINESS HORIZON, bukan window yang imbalance-nya "paling enak"
```

**Hasil sensitivity analysis:**

| Prediction Window | Eligible Customer | Positive Cases | Rate | Imbalance |
|---|---|---|---|---|
| 3 bulan | 75,047 | 431 | 0.57% | 173:1 |
| 4 bulan | 68,420 | 547 | 0.80% | 124:1 |
| **6 bulan (final)** | **54,738** | **664** | **1.21%** | **81:1** |

**Window final:** Observation Mar 2017–Mar 2018, Prediction Mar–Aug 2018. Dipilih karena horizon 6 bulan tetap actionable untuk campaign retensi jangka menengah — bukan karena imbalance-nya paling ringan.

---

## 3. Data Leakage Prevention

Checkpoint eksplisit sebelum feature engineering — bukan langkah opsional:

```
Observation Window → FEATURES → [Prediction Cutoff] → TARGET (Prediction Window)
```

**Aturan:** semua feature dihitung **hanya** dari data sampai observation cutoff. Fitur seperti `total_spending`, `days_since_last_order`, `last_order_date` **tidak boleh** dihitung dari tabel `customer_analytics_full` (yang mencakup seluruh histori dataset) — harus dibangun ulang sebagai `customer_features_observation`, dipotong sampai cutoff.

**Validasi otomatis (bukan manual):**
```python
assert obs_orders["order_purchase_timestamp"].max() < observation_end
assert obs_orders["order_purchase_timestamp"].min() >= observation_start
```
Kalau ada leakage, notebook langsung gagal dengan error — bukan lolos diam-diam.

---

## 4. Eligible Population

Customer yang dimasukkan ke populasi modeling **dibatasi** pada yang punya ≥1 order di observation window. Customer yang order pertamanya baru muncul setelah observation cutoff otomatis di-exclude — mereka tidak punya feature untuk diprediksi, dan menyertakan mereka akan mengaburkan definisi target.

---

## 5. Feature Engineering

Fitur dibangun dari observation period saja: `order_count`, `total_spending`, `avg_order_value`, `days_since_last_order`, `avg_review_score`, `avg_delivery_days`, `unique_categories`.

**Catatan `avg_delivery_days`:** bisa missing untuk customer yang order-nya belum/tidak delivered saat cutoff — ditangani lewat **imputasi median eksplisit** (bukan `fillna(0)`, yang akan menyiratkan makna "delivered instan" secara keliru).

---

## 6. Model Selection — Lift, Bukan ROC-AUC

3 model dilatih dengan `class_weight="balanced"` (Logistic Regression, Random Forest) / `scale_pos_weight` (XGBoost) untuk menangani imbalance 81:1 — **SMOTE tidak dipakai** secara default.

**Kriteria pemilihan model final:** PR-AUC dan **Precision@Top-K / Lift**, bukan ROC-AUC tertinggi. Alasan: pada imbalance ekstrem, ROC-AUC bisa terlihat "lumayan" (0.55-0.59 untuk ketiga model) padahal model sebenarnya tidak berguna untuk aksi bisnis. Precision@Top-K menjawab pertanyaan bisnis nyata: *"kalau tim marketing cuma bisa follow-up N customer, apakah model membantu memilih yang lebih baik dari random?"*

**Hasil:** Logistic Regression menang telak di lift (Top 1%: 10.57x, Top 5%: 3.61x di test-set) — mengungguli Random Forest dan XGBoost yang jatuh ke lift ~1.0x setelah Top 5-10%. Pola ini umum terjadi saat sinyal lemah dan model tree-based belum di-tuning intensif.

---

## 7. Evaluation Framework

- **Train/Validation/Test split** 3 arah — test set **disentuh sekali, di akhir**.
- **PR-AUC** sebagai metrik utama (bukan pelengkap).
- **Precision@Top-K & Lift** untuk menjawab pertanyaan bisnis langsung.
- **Probability calibration check** (reliability curve, Brier Score) — dilakukan, ditemukan model **tidak terkalibrasi** (`class_weight="balanced"` membuat probability jadi ranking score, mean 48% jauh dari actual rate 1.21%). Kalibrasi ulang **tidak dilakukan** karena tujuan pemakaian probability adalah ranking (Top-K selection), bukan menampilkan angka probability mentah ke user.
- **Feature importance** dicek konsisten di 3 model + SHAP (stretch goal) — hanya insight yang konsisten lintas metode yang diterjemahkan jadi rekomendasi bisnis.

---

## 8. Threshold Locking — Metodologi Kunci untuk Konsistensi Production

**Masalah yang ditemukan:** versi awal pipeline menghitung threshold Top-K secara independen di tiap tahap (evaluasi test-set vs scoring populasi penuh), menghasilkan definisi "Top 5%" yang berbeda populasi dan precision yang tidak match.

**Metodologi fix:**
1. Threshold probability dikunci **satu kali**, dari ranking Top-K% **di test set** (populasi yang paling representatif terhadap kondisi "belum pernah dilihat model").
2. Nilai threshold disimpan sebagai artifact (`models/threshold_top_k.json`).
3. Semua scoring berikutnya (populasi penuh, atau batch scoring baru) **me-reuse** nilai ini — tidak menghitung ulang persentil dari populasi yang sedang di-score.
4. Kalau model di-retrain, threshold **harus dikunci ulang** dari evaluasi test-set model baru — bukan mewariskan nilai lama.

**Validasi metodologi ini:** precision test-subset yang dihitung ulang dengan threshold yang di-load = 4.39%, identik dengan benchmark asli — mengonfirmasi metodologi bekerja benar. Gap yang tersisa (3.22% di full population vs 4.39% di test-set) sekarang **murni fungsi cakupan populasi** (weighted average dari train+val+test), bukan lagi karena definisi yang tidak konsisten — dibuktikan lewat perhitungan matematis di `docs/business_recommendations.md` section 13.10.5.

---

## 9. Business Translation

Output probability diterjemahkan jadi keputusan lewat **dua lapis**: Top-K selection (dari model) × Customer Value (dari observation window) → Priority Quadrant (VIP/RETAIN, WIN-BACK, GROW, LOW PRIORITY). Financial impact dihitung dengan asumsi eksplisit (bukan angka riil perusahaan), untuk menunjukkan **kerangka perhitungan**, bukan klaim ROI final.

---

## 10. Batasan Metodologis (Ringkas — detail lengkap di `assumptions_and_limitations.md`)

- Dataset observational — semua hubungan fitur-target adalah asosiasi, bukan kausalitas.
- Probability adalah ranking score, bukan probabilitas terkalibrasi.
- Rentang data terbatas (~2 tahun, akhir dataset parsial).
- Belum ada eksperimen intervensi nyata untuk validasi causal impact — direkomendasikan A/B testing sebagai next step.
