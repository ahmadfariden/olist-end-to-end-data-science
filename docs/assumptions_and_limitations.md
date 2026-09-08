# Assumptions & Limitations — Olist Repeat Purchase Prediction

> Dokumen ini konsolidasi semua asumsi dan keterbatasan yang muncul sepanjang proyek. Tujuannya supaya siapa pun yang membaca hasil analisis ini — termasuk diri sendiri di masa depan — tahu persis batas kepercayaan tiap angka.

---

## 1. Batasan Dataset

- **Observational, bukan eksperimental.** Olist adalah data historis transaksi. Semua hubungan fitur-target (mis. `avg_delivery_days` vs repeat purchase) adalah **asosiasi/korelasi**, bukan **kausalitas**. Tidak bisa disimpulkan "delivery lambat MENYEBABKAN customer tidak repeat" — hanya "berasosiasi dengan".
- **Rentang waktu pendek** (~Sep 2016–Okt 2018, traffic signifikan baru mulai awal 2017). Pola musiman jangka panjang (multi-tahun) belum tentu tertangkap.
- **2 bulan terakhir dataset (Sep–Okt 2018) parsial** — data collection berhenti, bukan penurunan bisnis. Di-exclude dari chart trend Power BI, harus dikomunikasikan eksplisit kalau dashboard dipresentasikan.
- **`customer_id` ≠ `customer_unique_id`** — kalau salah pakai, semua analisis customer-level rusak dari akar.
- **`geolocation` tidak 1:1 dengan zip code prefix** — sudah diagregasi (median/mode), tapi presisi lokasi tetap perkiraan tingkat prefix, bukan alamat presisi.

## 2. Batasan Terminologi Finansial

- **"Revenue" sebenarnya `transaction_value`** — proxy dari `payment_value` (mendekati GMV). Dataset **tidak menyediakan** cost, refund, atau profit margin riil. Semua metrik "revenue" di proyek ini harus dibaca sebagai transaction-value proxy, bukan revenue akuntansi.
- **`COST_PER_CONTACT` dan `VALUE_PER_REPEAT_CUSTOMER`** (dipakai di financial impact analysis) adalah **asumsi ilustratif**, bukan angka riil perusahaan. Net benefit/ROI yang dihitung menunjukkan **kerangka perhitungan**, bukan angka final yang bisa langsung dieksekusi. Perusahaan yang memakai analisis ini wajib mengganti dengan data biaya/margin riil.

## 3. Batasan Target & Populasi ML

- **Repeat Purchase (bukan Churn)** — dipilih karena dataset tidak punya label churn eksplisit. Target ini punya definisi presisi (≥1 order baru di prediction window, setelah ≥1 order di observation window), tapi tetap merupakan proxy dari niat bisnis "retensi" yang lebih luas.
- **Eligible population terbatas** (54,738 dari 96,096 total customer) — customer yang order pertamanya di luar observation window otomatis tidak masuk model. Business dashboard (full-history) dan ML scoring (observation-window) sengaja punya cakupan populasi berbeda — jangan dicampur tanpa disadari.
- **Imbalance ekstrem (81:1)** — bahkan setelah window final dipilih berdasarkan business horizon (bukan window paling "enak" imbalance-nya), rasio ini tetap ekstrem dibanding kasus klasifikasi pada umumnya. Ditangani lewat `class_weight`/`scale_pos_weight`, bukan SMOTE.

## 4. Batasan Model & Probability

- **`repeat_purchase_probability` adalah ranking score, bukan probabilitas terkalibrasi.** Model dilatih dengan `class_weight="balanced"` untuk menangani imbalance, efek sampingnya distribusi probability terkonsentrasi rapat di 40-60% (mean 48.18%, jauh dari actual rate 1.21%). **Angka individual (mis. "customer X: 0.76") tidak boleh dibaca sebagai "76% kemungkinan repeat" secara harfiah** — hanya valid sebagai urutan ranking relatif.
- **ROC-AUC rendah (0.591)** secara absolut — tapi ini **bukan berarti model tidak berguna**. Model tetap punya lift signifikan (3.61x di Top 5%, test-set) karena sinyal prediktif terkonsentrasi di ujung ranking (confidence tertinggi), bukan merata di seluruh populasi.
- **Feature importance adalah predictive association, bukan causal driver** — konsisten di 3 model (Logistic, RF, XGBoost) sehingga cukup dipercaya sebagai sinyal, tapi tetap tidak membuktikan hubungan sebab-akibat.

## 5. Batasan Threshold & Scoring Production

- **Gap precision test-set (4.39%) vs full-population (3.22%) adalah by design**, bukan bug — dua populasi ini punya cakupan berbeda (test-set murni unseen data, full-population termasuk data yang "dilihat" model saat training). Sudah divalidasi matematis sebagai weighted average dari 3 split.
- **🟢 Open item belum tuntas:** breakdown precision per split menunjukkan pola monotonik tak terduga — `train (2.79%) < val (3.61%) < test (4.39%)`. Biasanya training precision lebih tinggi (in-sample fit), bukan lebih rendah. Hipotesis: `class_weight="balanced"` mendorong skor customer negative-mirip-positive khusus di training set — **belum divalidasi tuntas**, dicatat sebagai area investigasi lanjutan (lihat `business_recommendations.md` 13.10.6). Tidak mengubah kelayakan model dipakai (precision production tetap 2.65x lebih baik dari random).
- **Kolom `actual_repeat` di `Dim_Customer` (Power BI)** hanya ada karena dataset historis — "masa depan" yang diprediksi sudah terjadi di dalam data. Kolom ini **tidak akan tersedia** dalam skenario scoring produksi sungguhan terhadap customer benar-benar baru. Precision@Top-K yang dihitung dinamis di Power BI adalah **evaluasi retrospektif**, bukan simulasi real-time scoring.

## 6. Batasan Validasi Causal

- **Belum ada eksperimen intervensi nyata.** Model memprediksi probability, belum membuktikan bahwa intervensi (voucher, email, dst) benar-benar **menyebabkan** peningkatan repeat purchase. Financial impact di section 13.3 dokumen bisnis dihitung dari **predictive lift**, bukan **causal lift**.
- **Next step yang direkomendasikan:** A/B testing — split Top-K customer jadi Treatment (dapat intervensi) vs Control (business-as-usual), bandingkan actual repeat rate, hitung incremental lift yang benar-benar disebabkan intervensi. Ini yang akan membuat klaim ROI jauh lebih defensible dibanding hanya berbasis predictive lift.

## 7. Batasan Implementasi & Deployment

- **Batch scoring saat ini manual** (dijalankan notebook per notebook) — bukan sistem produksi terjadwal. Proposed production schedule (batch bulanan) belum diimplementasikan.
- **Belum ada integrasi CRM riil** — output scoring tersedia di MongoDB dan Power BI, tapi konsumsi oleh tim marketing (kontak customer secara aktual) masih proposed, bukan sistem yang berjalan.
- **Model drift belum dimonitor** — tidak ada mekanisme otomatis untuk mendeteksi penurunan performa model seiring waktu. Re-training terjadwal direkomendasikan tapi belum diimplementasikan.

---

## Ringkasan: Apa yang BOLEH dan TIDAK BOLEH Diklaim

| Boleh diklaim | Tidak boleh diklaim |
|---|---|
| Model membantu prioritization, lift 2.65x-10.57x tergantung Top-K | Model memprediksi "siapa yang pasti akan repeat" |
| Fitur X berasosiasi dengan repeat purchase | Fitur X menyebabkan repeat purchase |
| Dengan asumsi biaya tertentu, net benefit model > random | ROI final yang pasti tanpa validasi biaya riil |
| Threshold production konsisten dengan benchmark test-set (tervalidasi) | Precision full-population akan selalu identik dengan test-set |
| Sistem ini bisa dioperasionalkan sebagai proposed workflow | Sistem ini sudah berjalan otomatis di produksi |