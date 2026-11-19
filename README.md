# UniCashier Dimsum Mentai (Python + HTML/CSS/JS)

Aplikasi kasir untuk UMKM dimsum mentai. UAS Pemrograman Terstruktur (SIF625204).
Semua logika berjalan di **Python**; tampilan memakai **HTML/CSS/JS** yang dilayani server lokal `http.server`
(library standar, tanpa instalasi). Desain 3 kolom (sidebar, menu, panel pesanan) mengikuti referensi POS,
dengan palet hangat: Madder `#A41623`, Orange `#F85E00`, Sandy Brown `#FFB563`, Sunset `#FFD29D`, Olive `#918450`.

## Menjalankan
```
python main.py                              # browser terbuka di http://127.0.0.1:8000
python -m unittest discover -s tests -v     # unit test (18 test)
```
Butuh Python 3.9+. Data tersimpan di folder `data/` (`produk.csv`, `transaksi.csv`), dibuat otomatis saat pertama jalan.

## Struktur
| Berkas | Isi |
|---|---|
| `main.py` | titik masuk |
| `kasir/web.py` | class `PenangananRequest` (rute JSON API + berkas statis) dan `AplikasiWeb` |
| `kasir/services.py` | class `TokoService` (produk, checkout, laporan), `hitung_total(*args)`, `filter_produk(**kwargs)` |
| `kasir/storage.py` | class `Storage` - baca/tulis CSV dengan `with open()` mode r/w/a/x |
| `kasir/models.py` | `Produk`, `Transaksi`, `Keranjang` |
| `kasir/algoritma.py` | merge sort, binary search, pencarian linear (buatan sendiri) |
| `kasir/validasi.py` | validasi input, `raise ValidasiError` |
| `static/` | `index.html`, `styles.css`, `app.js` (tampilan) |
| `tests/test_kasir.py` | 18 test (3 class) |

## Alur
Browser (JS) -> `fetch('/api/...')` -> `web.py` -> `TokoService` -> `Storage` (CSV).
Sorting, searching, validasi, dan perhitungan transaksi dilakukan di Python; JS hanya menampilkan.

## Pemetaan ke rubrik
- **UI & data**: sidebar menu, tombol, tabel data, kartu produk, baris kuning untuk stok menipis, laporan.
- **Sorting & searching**: klik judul kolom -> `merge_sort` (Python); kotak cari -> `cari_linear`; cari SKU -> `binary_search`.
- **File handling**: `storage.py` (r/w/a/x); `*args` di `hitung_total`, `**kwargs` + `lambda` di `filter_produk`.
- **Modularitas**: 6 modul dalam package `kasir`, >2 class utama.
- **Error handling**: `try/except` (`FileNotFoundError`, `ValueError`, `csv.Error`) di storage dan server; `raise ValidasiError` di validasi; `assert` di `merge_sort`.

## Tabel refactoring (untuk laporan)
| No | Sebelum | Sesudah | Manfaat |
|---|---|---|---|
| 1 | Pengurutan tiap kolom ditulis terpisah | Satu `merge_sort(data, key, reverse)` generik di `algoritma.py` | Satu algoritma O(n log n), stabil, dipakai semua tabel, mudah diuji |
| 2 | Cari produk per SKU dengan loop linear O(n) tiap kali | `binary_search` pada indeks SKU terurut yang di-cache di `TokoService` | Pencarian SKU O(log n); cache dibuang saat data berubah |
| 3 | Validasi input tersebar di form | Dipusatkan di `validasi.py` (`validasi_produk`, `ke_int`) | Tampilan tidak perlu tahu aturan; bisa diuji tanpa UI |
| 4 | Logika saring + urut ada di handler HTTP | Dipindah ke `TokoService.daftar_produk` / `daftar_transaksi` | Handler tipis; logika bisa diuji tanpa server |
| 5 | Filter produk berupa deretan `if` | Dict `ATURAN_FILTER` berisi `lambda` + `**kwargs` | Menambah filter cukup satu baris |
