"""Unit test (unittest) untuk logika kasir - tanpa UI.

Jalankan dari folder proyek:  python -m unittest discover -s tests -v
"""
import json
import os
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from kasir.algoritma import binary_search, cari_linear, merge_sort  # noqa: E402
from kasir.models import Keranjang  # noqa: E402
from kasir.services import TokoService, hitung_total  # noqa: E402
from kasir.storage import Storage  # noqa: E402
from kasir.validasi import ValidasiError, validasi_produk  # noqa: E402
from kasir.web import AplikasiWeb  # noqa: E402


class TestAlgoritma(unittest.TestCase):
    """Pengujian sorting & searching, terpisah dari UI."""

    def test_merge_sort_naik_dan_turun(self):
        self.assertEqual(merge_sort([5, 2, 9, 1]), [1, 2, 5, 9])
        self.assertEqual(merge_sort([5, 2, 9, 1], reverse=True), [9, 5, 2, 1])

    def test_merge_sort_stabil_dan_key(self):
        data = [("b", 1), ("a", 1), ("c", 0)]
        self.assertEqual(merge_sort(data, key=lambda x: x[1]),
                         [("c", 0), ("b", 1), ("a", 1)])

    def test_binary_search(self):
        data = [1, 3, 5, 7, 9]
        self.assertEqual(binary_search(data, 7), 3)
        self.assertEqual(binary_search(data, 4), -1)

    def test_cari_linear_tidak_peka_huruf(self):
        data = ["Mentai Keju", "Es Teh", "mentai pedas"]
        self.assertEqual(cari_linear(data, "MENTAI", lambda x: x),
                         ["Mentai Keju", "mentai pedas"])


class TestLayanan(unittest.TestCase):
    """Pengujian pengolahan data: validasi, filter, checkout, penyimpanan."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.service = TokoService(Storage(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    def test_validasi_harga_negatif_raise(self):
        with self.assertRaises(ValidasiError):
            validasi_produk("X1", "Tes", "Dimsum", -1000, 0, 5)

    def test_validasi_field_wajib(self):
        with self.assertRaises(ValidasiError):
            validasi_produk("", "Tes", "Dimsum", 1000, 500, 5)

    def test_filter_dengan_kwargs(self):
        hasil = self.service.filter_produk(kata="mentai", kategori="Dimsum", harga_maks=17000)
        self.assertTrue(hasil)
        self.assertTrue(all(p.kategori == "Dimsum" and p.harga <= 17000 for p in hasil))
        with self.assertRaises(ValidasiError):
            self.service.filter_produk(warna="merah")

    def test_hitung_total_args(self):
        self.assertEqual(hitung_total(1000, 2500, 500), 4000)
        self.assertEqual(hitung_total(), 0)

    def test_cari_sku_binary_search(self):
        self.assertEqual(self.service.cari_sku("dm001").nama, "Dimsum Mentai Original")
        self.assertIsNone(self.service.cari_sku("TIDAKADA"))

    def test_keranjang_melebihi_stok(self):
        k = Keranjang()
        produk = self.service.cari_sku("DM005")  # stok 8
        with self.assertRaises(ValidasiError):
            k.tambah(produk, produk.stok + 1)

    def test_checkout_kurangi_stok_dan_kembalian(self):
        k = Keranjang()
        produk = self.service.cari_sku("DM001")
        stok_awal = produk.stok
        k.tambah(produk, 2)  # 2 x 15.000 = 30.000
        trx, kembali = self.service.checkout(k, "Tunai", diskon_persen=10, uang=50000)
        self.assertEqual(trx.total, 27000)
        self.assertEqual(kembali, 23000)
        self.assertEqual(produk.stok, stok_awal - 2)
        self.assertEqual(self.service.ringkasan_total()["pendapatan"], 27000)

    def test_checkout_uang_kurang_raise(self):
        k = Keranjang()
        k.tambah(self.service.cari_sku("DM001"), 1)
        with self.assertRaises(ValidasiError):
            self.service.checkout(k, "Tunai", uang=1000)

    def test_data_tersimpan_permanen(self):
        k = Keranjang()
        k.tambah(self.service.cari_sku("MN001"), 1)
        self.service.checkout(k, "QRIS")
        service_baru = TokoService(Storage(self.tmp.name))  # simulasi buka aplikasi lagi
        self.assertEqual(len(service_baru.transaksi), 1)
        self.assertEqual(service_baru.cari_sku("MN001").stok, 49)

    def test_daftar_produk_terurut_harga(self):
        naik = [p.harga for p in self.service.daftar_produk(urut="harga")]
        turun = [p.harga for p in self.service.daftar_produk(urut="harga", terbalik=True)]
        self.assertEqual(naik, sorted(naik))
        self.assertEqual(turun, sorted(naik, reverse=True))
        with self.assertRaises(ValidasiError):
            self.service.daftar_produk(urut="password")

    def test_file_rusak_tidak_crash(self):
        with tempfile.TemporaryDirectory() as folder:
            with open(os.path.join(folder, "produk.csv"), "w", encoding="utf-8") as f:
                f.write("sku,nama,kategori,harga,hpp,stok\nX1,Tes,Dimsum,abc,1,2\n")
            service = TokoService(Storage(folder))
            self.assertTrue(service.peringatan)   # ada peringatan baris rusak
            self.assertTrue(service.produk)       # jatuh ke data awal, tidak kosong


class TestApiWeb(unittest.TestCase):
    """Uji lapisan HTTP (server standar) memakai request sungguhan ke port lokal acak."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        cls.app = AplikasiWeb(TokoService(Storage(cls.tmp.name)), port=0)
        threading.Thread(target=cls.app.server.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.app.server.shutdown()
        cls.app.server.server_close()
        cls.tmp.cleanup()

    def panggil(self, jalur, metode="GET", body=None):
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.app.url + jalur, data=data, method=metode,
                                     headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req) as res:
                return res.status, res.read()
        except urllib.error.HTTPError as e:
            return e.code, e.read()

    def test_halaman_utama_dan_path_traversal(self):
        status, isi = self.panggil("/")
        self.assertEqual(status, 200)
        self.assertIn(b"UniCashier", isi)
        self.assertEqual(self.panggil("/..%2Fmain.py")[0], 404)

    def test_produk_urut_dan_validasi(self):
        status, isi = self.panggil("/api/produk?urut=harga&arah=desc")
        harga = [p["harga"] for p in json.loads(isi)["produk"]]
        self.assertEqual(status, 200)
        self.assertEqual(harga, sorted(harga, reverse=True))
        status, isi = self.panggil("/api/produk", "POST", dict(
            sku="X9", nama="Tes", kategori="Dimsum", harga="-5", hpp="1", stok="1"))
        self.assertEqual(status, 400)
        self.assertIn("negatif", json.loads(isi)["error"])

    def test_checkout_lewat_api(self):
        status, isi = self.panggil("/api/checkout", "POST", dict(
            items=[{"sku": "MN002", "qty": 2}], metode="Tunai", diskon=0, uang=20000))
        hasil = json.loads(isi)
        self.assertEqual(status, 200)
        self.assertEqual(hasil["transaksi"]["total"], 18000)
        self.assertEqual(hasil["kembalian"], 2000)
        status, _ = self.panggil("/api/checkout", "POST", dict(items=[], metode="Tunai"))
        self.assertEqual(status, 400)


if __name__ == "__main__":
    unittest.main()
