# Business Decision & Operationalization
## Olist Repeat Purchase Prediction — Fase 13 (Revisi v3 — Threshold Fix Applied & Validated)

> **Cara baca dokumen ini:** setiap klaim ditandai sumbernya. Angka yang diawali "✅ **Evidence**" berasal langsung dari data/model. Angka atau rencana yang diawali "🔵 **Proposed/Assumption**" adalah skenario/asumsi yang **belum diimplementasikan** dan wajib diverifikasi dengan data riil perusahaan sebelum dieksekusi. Angka yang diawali "🟢 **Open Item**" adalah temuan baru yang sudah terisolasi dengan jelas tapi belum ditelusuri akar penyebabnya sampai tuntas — bukan blocker, tapi perlu dicatat jujur.

> **Perubahan dari v2:** fix threshold di 13.10 sudah diimplementasikan dan divalidasi (lihat 13.10.5). Semua angka 🟣 *Pending Fix* di v2 sudah diganti dengan angka final ✅, termasuk angka finansial di 13.3 yang sudah diverifikasi langsung dari print output notebook 11 (bukan dari card Power BI). Ditambahkan temuan baru: pola precision monotonik antar split (train < val < test) yang di luar ekspektasi normal — dicatat sebagai open item di 13.10.6, bukan disembunyikan.
>
> **⚠️ Satu action item operasional tersisa (bukan soal dokumen):** Dashboard Power BI (Dashboard 5) masih menampilkan angka lama (Net Benefit 1.16K / Uplift 9.43K) karena belum di-refresh dari `customer_predictions.csv` versi terbaru. Refresh Power BI sebelum dashboard dipresentasikan bersamaan dengan dokumen ini.

---

## 13.1 Executive Summary

**Problem:** Olist tidak punya sistem untuk mengidentifikasi customer mana yang berpotensi melakukan repeat purchase, sehingga campaign retensi cenderung dilakukan secara massal/tidak terarah.

**Model:** Logistic Regression memprediksi `repeat_purchase_probability` — kemungkinan seorang customer melakukan order baru dalam 6 bulan ke depan, berdasarkan histori transaksi 12 bulan observation window. ✅ **Evidence**: 54,738 customer eligible di-score, model dipilih berdasarkan PR-AUC & lift (bukan ROC-AUC tertinggi).

**Business impact:** Model tidak akurat secara keseluruhan populasi (ROC-AUC 0.59), tapi **sangat efektif untuk menyaring kandidat prioritas**. Ada dua angka precision yang perlu dibedakan konteksnya (✅ **Evidence**, sudah divalidasi konsisten di 13.10):

- **Benchmark model (test set, data yang belum pernah dilihat model):** Top 5% → precision 4.39%, lift 3.61x.
- **Scoring production (seluruh 54,738 customer eligible):** Top 5% → precision 3.22%, lift 2.65x.

Kedua angka ini **sengaja berbeda** — bukan bug. Detail penyebab dan validasinya ada di 13.10.

**Positioning:** Ini bukan "model yang memprediksi semua customer dengan akurat", melainkan **sistem prioritization** — menjawab *"siapa yang layak menerima intervensi marketing lebih dulu, berdasarkan kemungkinan repeat DAN nilai customer?"*

---

## 13.2 Model Performance

✅ **Evidence** (test set, notebook 09):

| Metrik | Nilai |
|---|---|
| ROC-AUC | 0.591 |
| PR-AUC | 0.085 (baseline random ≈ 0.012) |
| Precision@Top 1% | 12.84% (lift 10.57x) |
| Precision@Top 5% | 4.39% (lift 3.61x) |
| Precision@Top 10% | 2.65% (lift 2.18x) |
| Precision@Top 20% | 2.01% (lift 1.65x) |

**Interpretasi:** sinyal prediktif model terkonsentrasi di ujung ranking (confidence tertinggi), melemah signifikan setelah Top 10-20%. Model paling tepat dipakai untuk campaign terfokus, bukan targeting massal.

**Catatan konsistensi (✅ Resolved, sebelumnya 🟣 di v2 — lihat 13.10):** tabel di atas adalah benchmark resmi model dari test set. Threshold Top-5% yang dipakai untuk scoring seluruh populasi (13.10) sekarang **dikunci dari nilai probability yang sama persis dengan tabel ini** (`threshold_value = 0.5971`), bukan dihitung ulang dari populasi lain. Validasi ulang di test-subset (13.10.5) mengonfirmasi angka 4.39% ini reproducible sampai 2 desimal — fix sudah bekerja dengan benar.

**Catatan kalibrasi probability:** ✅ **Evidence** (notebook 08): karena model dilatih dengan `class_weight="balanced"` untuk menangani imbalance 81:1, `repeat_purchase_probability` adalah **ranking score, bukan probabilitas terkalibrasi**. Mean predicted probability di validation set adalah 48.18%, jauh di atas actual positive rate (1.21%). Implikasinya:
- Angka probability individual (mis. "customer X: 0.76") tidak boleh dibaca sebagai "76% kemungkinan repeat" secara harfiah — itu murni skor ranking relatif terhadap customer lain.
- Threshold Top-K jatuh di zona terpadat dari distribusi skor (40-60%), sehingga sensitif terhadap definisi populasi mana yang dipakai menghitungnya — inilah yang mendasari temuan 13.10.

---

## 13.3 Financial Impact

🔵 **Proposed/Assumption** — dataset Olist tidak menyediakan biaya campaign riil (cost per kontak, biaya CRM/customer service) maupun profit margin aktual. Angka di bawah memakai **asumsi ilustratif** (`COST_PER_CONTACT=5.0`, `VALUE_PER_REPEAT_CUSTOMER=163.08`) yang harus diganti dengan data riil perusahaan.

✅ **Evidence** (notebook 11, hasil re-run setelah threshold-lock — diverifikasi langsung dari print output notebook, bukan dari card Dashboard Power BI):

| Skenario | N Contacted | Conversion Rate | Expected Conversions | Total Cost | Expected Revenue | Net Benefit | Cost per Acquisition |
|---|---:|---:|---:|---:|---:|---:|---:|
| Random Targeting (tanpa model) | 2,857 | 1.21% | 34.66 | 14,285 | 5,651.94 | **-8,633.06** | 412.18 |
| Model-based Targeting (Top 5%) | 2,857 | 3.22% | 92.00 | 14,285 | 15,003.60 | **+718.60** | 155.27 |

| Ringkasan | Nilai |
|---|---:|
| Selisih expected conversions (Model vs Random) | +57.3 customer |
| Selisih net benefit (Model vs Random) / Uplift | **+9,351.67** |
| Penurunan cost per acquisition | 62.3% |

**✅ Verifikasi selesai (sebelumnya 🟡 open item di v3):** `N_CONTACTED` dikonfirmasi memang dihitung dinamis dari jumlah customer ter-flag aktual (2,857), **bukan** hardcode 2,737 — kode notebook 11 sudah benar dari awal, tidak perlu diperbaiki. Yang jadi sumber selisih angka bukan basis kontak, melainkan **Dashboard Power BI yang belum di-refresh** dari `customer_predictions.csv` versi terbaru — Net Benefit +1,160 / Uplift +9,430 yang sempat muncul di card dashboard adalah **data lama sebelum threshold-lock diterapkan**, bukan angka final. Angka yang benar dan final adalah tabel di atas, diambil langsung dari print output notebook (ground truth), bukan dari card Power BI. **Tindak lanjut:** refresh Dashboard 5 di Power BI supaya card KPI menampilkan +718.60 / +9,351.67, bukan angka lama.

**Interpretasi:** dengan jumlah kontak dan budget yang sama (2,857 customer, cost 14,285), model-based targeting mengubah net benefit dari **rugi -8,633.06** menjadi **untung +718.60** — uplift +9,351.67 murni dari precision model yang 2.65x lebih baik dari random. Angka net benefit model (+718.60) ini **jauh lebih rendah** dari proyeksi v1 yang sempat memakai precision test-set (4.39%) untuk menghitung skenario ini — mengonfirmasi kekhawatiran di 13.10: **klaim finansial yang mencampur precision benchmark dengan precision production akan overstate manfaat riil secara signifikan** (v1 mengklaim +1,156, realitas production hanya +718.60 — selisih ~38%).

**Sensitivity analysis (masih disarankan sebelum eksekusi):** hitung ulang net benefit dengan rentang `COST_PER_CONTACT` dan `VALUE_PER_REPEAT_CUSTOMER` yang lebih realistis dari margin riil perusahaan, memakai precision production (3.22%) sebagai basis — bukan precision test-set.

---

## 13.4 Customer Action Matrix

✅ **Evidence** (notebook 10-11, hasil re-run setelah threshold-lock, 54,738 customer scored):

| Quadrant | Customer | Priority | Business Action |
|---|---:|---|---|
| **HIGH VALUE + HIGH PROBABILITY** (VIP/RETAIN) | 1,496 | 🔴 Highest | Retain & encourage next purchase |
| **HIGH VALUE + LOW PROBABILITY** (WIN-BACK) | 25,878 | 🟠 High | Win-back / reactivation campaign |
| **LOW VALUE + HIGH PROBABILITY** (GROW) | 1,361 | 🟡 Medium | Cross-sell / upsell untuk naikkan value |
| **LOW VALUE + LOW PROBABILITY** (LOW PRIORITY) | 26,003 | 🟢 Low | Standard automated nurturing |

Dibanding v1 (sebelum fix): VIP/RETAIN naik dari 1,471→1,496 (+25), GROW naik dari 1,266→1,361 (+95), WIN-BACK turun dari 25,903→25,878, LOW PRIORITY turun dari 26,098→26,003. Pergeseran ini konsisten dengan jumlah customer ter-flag yang naik sedikit (2,737→2,857) akibat threshold terkunci.

**Dua lapis keputusan:**
```
MODEL PROBABILITY
       ↓
  Top-K Selection
       ↓
  CUSTOMER VALUE
       ↓
  ┌────┴────┐
  ↓         ↓
HIGH VALUE  LOW VALUE
  ↓         ↓
RETAIN/GROW GROW/NURTURE
```

Model tidak cuma menjawab *"siapa yang kemungkinan repeat?"*, tapi *"siapa yang harus diprioritaskan untuk tindakan marketing, berdasarkan kemungkinan repeat DAN nilai customer?"*

---

## 13.5 Risk & Mitigation

**False Positive:** Customer yang diprediksi berpotensi repeat tetapi ternyata tidak melakukan repeat order dapat menerima intervensi yang tidak menghasilkan conversion. *Mitigasi:* membatasi intervensi pada Top-K (bukan seluruh populasi) dan melakukan cost-benefit analysis sebelum campaign deployment.

**False Negative:** Customer yang sebenarnya berpotensi repeat tetapi tidak terdeteksi model dapat kehilangan kesempatan mendapatkan intervensi prioritas. *Mitigasi:* tetap mempertahankan baseline/organic campaign untuk customer di luar Top-K, bukan mengabaikan mereka sepenuhnya.

**Model drift:** Perilaku customer bisa berubah seiring waktu (musim, kompetitor, kondisi ekonomi) sehingga performa model bisa menurun. *Mitigasi:* monitoring performa berkala dan re-training terjadwal (lihat 13.6).

**Data quality:** Model bergantung pada kelengkapan data transaksi (`avg_delivery_days`, `avg_review_score` bisa missing). *Mitigasi:* imputasi eksplisit sudah diterapkan (notebook 08), tetap perlu monitoring proporsi missing value dari waktu ke waktu.

**Campaign fatigue:** Customer yang berulang kali masuk Top-K di scoring periode berturut-turut berisiko over-contacted. *Mitigasi:* frequency capping (mis. maksimal 1 campaign per customer per periode scoring).

**Threshold inconsistency (✅ Resolved di v3):** sebelumnya threshold Top-K dihitung ulang dari populasi scoring, menyebabkan gap precision yang tidak terjelaskan dengan `benchmark` model. *Fix diterapkan:* `threshold_value` dikunci dari test-set evaluation (notebook 09) dan direuse di notebook 10, divalidasi cocok sampai 2 desimal (13.10.5).

**🟢 Model overconfidence pada sebagian training data (Open Item baru, v3):** ditemukan pola precision monotonik train (2.79%) < val (3.61%) < test (4.39%) pada threshold yang sama — di luar ekspektasi normal (biasanya training precision lebih tinggi karena in-sample fit). *Mitigasi sementara:* tidak mengubah keputusan threshold atau model saat ini, karena precision production (3.22%) tetap terbukti mengungguli baseline random (1.21%) secara signifikan. *Rencana lanjutan:* investigasi subgroup customer training yang mendapat skor tinggi tapi `target=0`, untuk memastikan tidak ada leakage atau miskalibrasi sistematis yang lebih dalam (lihat 13.10.6).

---

## 13.6 Operational Rollout

🔵 **Proposed operational scenario** — belum diimplementasikan sebagai sistem produksi, ini rekomendasi skema deployment.

| Priority | Action | Channel |
|---|---|---|
| **Top 1%** | High-touch retention / personalized offer | CRM / direct outreach |
| **Top 2-5%** | Targeted promotional campaign | Email / push notification / CRM |
| **95% lainnya** | Standard nurturing | Automated campaign |

**Current implementation:** batch scoring dijalankan manual, notebook-based (`09_model_evaluation.ipynb` → `10_customer_scoring.ipynb` → `11_export_for_powerbi.ipynb`), dengan threshold Top-K terkunci di `models/threshold_top_k.json` (✅ diterapkan di v3).

**Proposed production schedule:** batch scoring berkala (mis. bulanan, mengikuti prediction window 6 bulan yang dipakai model) — bukan real-time, karena sinyal behavioral (order history) tidak berubah signifikan dalam hitungan jam/hari.

**Aturan threshold untuk batch scoring berikutnya:** `threshold_value` yang dikunci dari evaluasi test-set **tidak boleh dihitung ulang** setiap batch scoring baru berjalan. Kalau di masa depan model di-retrain, threshold baru harus dikunci ulang dari test-set evaluation model versi baru tersebut (ulangi proses notebook 09 section 6.1) — bukan otomatis mengikuti distribusi scoring batch terbaru.

---

## 13.7 Feature → Actionability

✅ Hanya feature yang **benar-benar dikonfirmasi penting** di model (konsisten di Logistic Regression, Random Forest, dan XGBoost — notebook 09) yang diterjemahkan jadi rekomendasi aksi:

| Model Driver | Business Interpretation |
|---|---|
| `days_since_last_order` (asosiasi negatif) | Customer dengan waktu sejak pembelian terakhir yang lebih lama harus menerima intervensi re-engagement lebih awal, karena recency yang menurun berasosiasi dengan probability repeat yang lebih rendah. |
| `avg_order_value` (asosiasi negatif) | Customer dengan nilai transaksi rata-rata besar (belanja besar sekali) cenderung tidak repeat — kandidat kuat untuk win-back campaign, bukan diasumsikan otomatis loyal karena nilainya tinggi. |
| `total_spending` (asosiasi positif) | Customer dengan total spending tinggi lewat banyak transaksi kecil cenderung lebih repeat — kandidat baik untuk program loyalty berkelanjutan. |
| `avg_delivery_days` (asosiasi negatif) | Delivery yang lebih lama berasosiasi dengan probability repeat yang lebih rendah. Perbaikan SLA pengiriman (terutama di wilayah dengan avg delivery time tinggi — lihat Fase 5) berpotensi berkontribusi pada retensi, meski ini **asosiasi, bukan bukti kausal** — perlu diverifikasi lewat eksperimen terpisah (lihat 13.9). |

**Catatan disiplin:** interpretasi di atas dibatasi hanya pada fitur yang benar-benar jadi temuan model — tidak ada insight yang "dipaksakan masuk" supaya terlihat lebih lengkap. `order_count` termasuk sebagai salah satu dari 7 feature model, tapi **tidak** termasuk driver yang dikonfirmasi konsisten di 3 model — sengaja tidak dimasukkan ke tabel rekomendasi aksi di atas.

---

## 13.8 Data Product Architecture

```
Raw Olist Data
      ↓
Data Cleaning / Feature Engineering (notebook 01-07)
      ↓
Trained ML Model (notebook 08, Logistic Regression)
      ↓
Test-Set Evaluation & Threshold Lock (notebook 09) ── models/threshold_top_k.json
      ↓
Customer Probability Score + Threshold Terkunci (notebook 10)
      ↓
Priority / Value Matrix (notebook 11)
      ↓
MongoDB [customer_predictions collection]
      ↓
Power BI [Dashboard 5 - Predictive Analytics]
      ↓
Marketing Action (proposed, lihat 13.6)
```

**Perubahan dari v2:** diagram sekarang eksplisit menampilkan bahwa threshold mengalir dari notebook 09 (test-set evaluation) ke notebook 10 (scoring), bukan dihitung ulang di notebook 10 secara independen. Ini bukan cuma dokumentasi — sudah diimplementasikan dan divalidasi (13.10.5).

**Current implementation:** seluruh pipeline di atas sampai MongoDB + export CSV untuk Power BI sudah berjalan dan tervalidasi. Konsumsi oleh tim marketing (langkah terakhir) masih **proposed**, belum ada integrasi sistem CRM riil.

---

## 13.9 Limitations & Next Steps

**Keterbatasan yang harus disampaikan secara jujur:**

- **Observational dataset** — Olist adalah data historis transaksi, bukan hasil eksperimen terkontrol. Semua hubungan fitur-target adalah **asosiasi**, bukan **kausalitas**.
- **Asumsi finansial hipotetis** — `COST_PER_CONTACT` dan `VALUE_PER_REPEAT_CUSTOMER` di 13.3 bersifat ilustratif, belum divalidasi dengan data biaya/profit riil perusahaan.
- **Belum ada eksperimen intervensi nyata** — model memprediksi probability, belum membuktikan bahwa intervensi (voucher, email, dst) benar-benar **menyebabkan** peningkatan repeat purchase.
- **Rentang data terbatas** (~2 tahun, dan bagian akhir dataset parsial) — pola musiman jangka panjang belum tentu tertangkap penuh.
- **Probability tidak terkalibrasi** — `class_weight="balanced"` membuat `repeat_purchase_probability` jadi ranking score, bukan probabilitas literal yang bisa dibaca harfiah.
- **🟢 Pola precision monotonik antar split (baru, v3)** — precision di training data (2.79%) lebih rendah dari validation (3.61%) dan test (4.39%) pada threshold yang sama. Ini di luar ekspektasi normal dan penyebab pastinya belum ditelusuri tuntas (lihat 13.10.6). Tidak mengubah kelayakan model untuk dipakai (precision production tetap jauh di atas baseline), tapi didokumentasikan sebagai area investigasi lanjutan.
- ~~🟡 Verifikasi basis kontak di simulasi finansial~~ — **✅ Selesai diverifikasi.** `N_CONTACTED` terkonfirmasi dinamis (2,857), bukan hardcode lama. Selisih angka yang sempat terlihat berasal dari Dashboard Power BI yang belum di-refresh, bukan dari kesalahan kode notebook 11.

**Next step yang direkomendasikan — A/B Testing / Experimentation:**

Model hanya menjawab *"siapa yang berpotensi repeat?"*, belum menjawab *"apakah intervensi yang diberikan benar-benar menyebabkan mereka repeat?"* — pertanyaan yang pasti muncul dari stakeholder.

```
Model selects Top 5% (2,857 customer, threshold terkunci)
        ↓
    Random split
   ┌────┴────┐
   ↓         ↓
Treatment   Control
   ↓         ↓
 Promo      No Promo
   └────┬────┘
        ↓
Compare Repeat Rate
        ↓
Incremental Lift
        ↓
ROI (berbasis causal evidence, bukan cuma predictive lift)
```

**Desain eksperimen yang diusulkan:**
1. Ambil Top 5% customer hasil scoring dengan threshold terkunci (2,857 customer — angka final setelah fix, bukan lagi 2,737).
2. Random split jadi **Treatment** (dapat intervensi/promo) dan **Control** (tidak dapat apa-apa, business-as-usual).
3. Bandingkan actual repeat rate kedua grup setelah periode observasi yang sama.
4. Selisih repeat rate = **incremental lift** yang benar-benar disebabkan oleh intervensi (bukan cuma korelasi dari probability tinggi).
5. Hitung ROI berdasarkan incremental lift ini — jauh lebih defensible dibanding ROI yang cuma berbasis predictive lift di 13.3.

**Kesimpulan positioning proyek:** bukan sekadar *"saya membuat model repeat-purchase"*, melainkan *"saya membangun sistem prioritization untuk menentukan customer mana yang layak mendapatkan intervensi marketing — lengkap dengan kesadaran akan batas antara prediction, causation, dan business impact, kemampuan mengaudit dan memperbaiki inkonsistensi pipeline sendiri (13.10), dan kejujuran mendokumentasikan temuan yang belum sepenuhnya terjelaskan (13.10.6) alih-alih menyembunyikannya."*

---

## 13.10 Audit Temuan — Inkonsistensi Threshold Top-K (RESOLVED)

**Status: ✅ Fix diimplementasikan dan divalidasi.** Bagian ini didokumentasikan lengkap (gejala → penyebab → fix → validasi → temuan baru) sebagai jejak audit, bukan dihapus setelah diperbaiki — supaya proses berpikirnya tetap terlihat.

### 13.10.1 Gejala (ditemukan pertama kali)

Precision@Top5% berbeda antara dua sumber, padahal baseline (positive rate) identik (~1.21%) di keduanya:

| Sumber | Precision@Top5% | Lift@Top5% |
|---|---:|---:|
| Notebook 09 (test set) | 4.39% | 3.61x |
| Dashboard / notebook 10-11 (full population, sebelum fix) | 3.32% | 2.74x |

### 13.10.2 Akar Penyebab

1. Model dilatih dengan `class_weight="balanced"` (notebook 08) — `repeat_purchase_probability` jadi ranking score yang terkonsentrasi rapat di 40-60%, bukan probabilitas kalibrasi literal.
2. Notebook 09 menghitung threshold Top-5% dari ranking **di dalam test set saja**.
3. Notebook 10 (sebelum fix) menghitung ulang threshold dari **persentil populasi scoring penuh** (train+val+test digabung) — populasi yang berbeda dari poin 2.
4. Karena skor customer terkonsentrasi rapat di sekitar cutoff, dua populasi berbeda ini menghasilkan nilai threshold yang sedikit berbeda, menukar ribuan customer di sekitar batas, sehingga precision terukur berbeda.

### 13.10.3 Fix yang Diterapkan

1. `09_model_evaluation.ipynb` — ditambah section 6.1: mengunci `threshold_value` dari ranking test set, disimpan sebagai `models/threshold_top_k.json`.
2. `10_customer_scoring.ipynb` — section 2 diubah untuk **load** `threshold_top_k.json`, bukan menghitung ulang persentil dari `ml_dataset` sendiri.
3. `11_export_for_powerbi.ipynb` — tidak ada perubahan kode, otomatis reflect angka baru dari `customer_predictions.csv` yang di-generate ulang.

### 13.10.4 Threshold Final

```json
{
  "model_name": "Logistic Regression",
  "top_n_percent": 5,
  "threshold_value": 0.5970663308248289,
  "computed_from": "test_set",
  "test_set_size": 10948,
  "test_set_precision_at_threshold": 0.0438756855575868,
  "test_set_lift_at_threshold": 3.61661695371885
}
```

### 13.10.5 Validasi Fix — Breakdown Precision per Split

✅ **Evidence** (notebook 10, section 2.1, dijalankan setelah fix): pada `threshold_value = 0.5971` yang sama, precision dihitung terpisah per split menggunakan index asli dari `train_val_test_split.pkl`:

| Split | N flagged | % of split | Precision |
|---|---:|---:|---:|
| Train | 1,867 | 5.33% | 2.79% |
| Val | 443 | 5.06% | 3.61% |
| Test | 547 | 5.00% | **4.39%** |
| **Full population** | **2,857** | **5.22%** | **3.22%** |

**Validasi kunci:** precision test-subset (dihitung ulang di notebook 10 dengan threshold yang di-load) = **4.39%** — identik persis dengan benchmark asli notebook 09. Ini mengonfirmasi fix bekerja dengan benar: gap yang tersisa sekarang murni fungsi dari cakupan populasi (rata-rata tertimbang train+val+test), bukan lagi karena definisi threshold yang tidak konsisten.

Cek matematis: `(1,867×2.79% + 443×3.61% + 547×4.39%) / 2,857 = 3.22%` — cocok persis dengan precision full-population, mengonfirmasi tidak ada bug tersembunyi lain di kalkulasi.

### 13.10.6 🟢 Temuan Tambahan (Open Item) — Pola Precision Monotonik Antar Split

Breakdown di 13.10.5 memunculkan pola yang **di luar ekspektasi normal**:

```
train (2.79%) < val (3.61%) < test (4.39%)
```

**Kenapa ini di luar ekspektasi:** secara umum, precision di data yang dipakai untuk fitting model (train) diharapkan **lebih tinggi atau sama** dengan data yang belum pernah dilihat model (test), karena in-sample fit biasanya lebih optimis. Di sini urutannya justru terbalik sempurna.

**Hipotesis (belum tervalidasi, jangan dianggap kesimpulan final):** `class_weight="balanced"` mereweight loss function agar model agresif mengenali tiap kasus positif di training data. Efek sampingnya, sejumlah customer `target=0` di training yang secara fitur mirip dengan pola positive yang sedang "dipelajari" model, ikut terdorong skornya melewati threshold — spesifik terjadi di training set karena di situlah pembelajaran pola itu berlangsung. Di val/test, dorongan serupa tidak sekuat itu karena tidak sepenuhnya general.

**Kenapa ini tidak menghalangi model tetap dipakai:** precision production keseluruhan (3.22%) tetap 2.65x lebih baik dari random targeting (1.21%) — pola ini tidak mengubah kesimpulan bahwa model bermanfaat untuk prioritization, hanya menunjukkan bagian dari performa itu (kontribusi dari training-set customer) sedikit lebih lemah dari yang terlihat di benchmark test-set saja.

**Rencana investigasi lanjutan (belum dieksekusi):**
1. Ambil subgroup customer training yang `prediction=1` tapi `target=0` — cek apakah mereka punya kombinasi fitur ekstrem tertentu (mis. `days_since_last_order` sangat rendah tapi tidak repeat) yang mengindikasikan model overfit ke noise spesifik training set.
2. Bandingkan distribusi fitur subgroup ini vs subgroup customer test set dengan `prediction=1, target=0` — kalau polanya beda signifikan, itu memperkuat hipotesis di atas.
3. Pertimbangkan apakah regularisasi tambahan (`C` lebih kecil di Logistic Regression) perlu dicoba di iterasi model berikutnya untuk mengurangi gap ini — bukan revisi mendesak, tapi catatan untuk fase re-training berikutnya.

### 13.10.7 Dampak ke Klaim Bisnis

- **13.2 (Model Performance):** tabel test-set tetap valid sebagai benchmark resmi — tidak berubah.
- **13.3 (Financial Impact):** dihitung ulang dengan precision production (3.22%), bukan 3.32% (lama) atau 4.39% (benchmark). Net benefit final terverifikasi dari print output notebook 11 langsung: **+718.60** (model) vs **-8,633.06** (random), uplift **+9,351.67**. Selisih sempat terlihat karena Dashboard Power BI belum di-refresh dari data terbaru — bukan bug kode.
- **13.4 (Customer Action Matrix):** jumlah customer per kuadran diupdate mengikuti threshold baru.
- **13.9 (Limitations):** ditambah 2 limitation baru (pola monotonik split, verifikasi basis kontak) — memperkuat, bukan melemahkan, positioning proyek sebagai sistem yang diaudit dengan jujur.
