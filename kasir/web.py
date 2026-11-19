"""web.py - server HTTP lokal untuk antarmuka HTML/CSS/JS.

Memakai library standar `http.server` (tanpa instalasi tambahan).
  - File tampilan dilayani dari folder `static/`.
  - Semua data & logika tetap diproses Python lewat TokoService (JSON API /api/...).
"""
import json
import mimetypes
import os
import webbrowser
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs, unquote, urlparse

from .models import BATAS_STOK_MENIPIS, Keranjang
from .services import struk_teks
from .validasi import KATEGORI, METODE, ValidasiError, ke_int

FOLDER_STATIC = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "static")
FIELD_PRODUK = ("sku", "nama", "kategori", "harga", "hpp", "stok")


class PenangananRequest(BaseHTTPRequestHandler):
    """Menangani satu request HTTP: rute /api/... atau berkas statis."""

    layanan = None  # diisi AplikasiWeb dengan TokoService

    def log_message(self, format, *args):  # noqa: A002 - sunyikan log bawaan
        pass

    # ---------- helper respons ----------
    def _kirim(self, status, isi, tipe):
        self.send_response(status)
        self.send_header("Content-Type", tipe)
        self.send_header("Content-Length", str(len(isi)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(isi)

    def _kirim_json(self, data, status=200):
        self._kirim(status, json.dumps(data, ensure_ascii=False).encode("utf-8"),
                    "application/json; charset=utf-8")

    def _baca_json(self):
        """Baca body JSON request; raise ValidasiError bila bukan objek JSON."""
        panjang = int(self.headers.get("Content-Length") or 0)
        mentah = self.rfile.read(panjang) if panjang else b"{}"
        try:
            data = json.loads(mentah.decode("utf-8"))
        except ValueError:  # JSONDecodeError & UnicodeDecodeError turunan ValueError
            raise ValidasiError("Data yang dikirim bukan JSON yang valid") from None
        if not isinstance(data, dict):
            raise ValidasiError("Data harus berupa objek JSON")
        return data

    # ---------- routing ----------
    def _tangani_api(self, metode):
        """Jalankan rute API; ubah error menjadi respons JSON yang rapi."""
        url = urlparse(self.path)
        query = {k: v[0] for k, v in parse_qs(url.query).items()}
        bagian = [unquote(b) for b in url.path.strip("/").split("/")]
        try:
            self._kirim_json(self._rute_api(metode, bagian, query))
        except ValueError as e:  # termasuk ValidasiError
            self._kirim_json({"error": str(e)}, 400)
        except LookupError:
            self._kirim_json({"error": "Rute tidak ditemukan"}, 404)
        except Exception:  # server tidak boleh mati karena satu request
            self._kirim_json({"error": "Terjadi kesalahan pada server"}, 500)

    def _rute_api(self, metode, bagian, q):
        """Peta rute: (metode, /api/<sumber>[/<id>]) -> pemanggilan service."""
        s = self.layanan
        sumber = bagian[1] if len(bagian) > 1 else ""
        id_ = bagian[2] if len(bagian) > 2 else None

        if sumber == "meta" and metode == "GET":
            return {"kategori": list(KATEGORI), "metode": list(METODE),
                    "batas_menipis": BATAS_STOK_MENIPIS, "peringatan": s.peringatan}

        if sumber == "produk":
            if metode == "GET" and id_ is None:
                hasil = s.daftar_produk(
                    urut=q.get("urut") or None, terbalik=q.get("arah") == "desc",
                    kata=q.get("kata", ""), kategori=q.get("kategori") or None,
                    stok_maks=BATAS_STOK_MENIPIS if q.get("menipis") == "1" else None)
                return {"produk": [asdict(p) for p in hasil],
                        "menipis": len(s.stok_menipis()), "total": len(s.produk)}
            if metode == "POST" and id_ is None:
                body = self._baca_json()
                s.tambah_produk(**{k: body.get(k, "") for k in FIELD_PRODUK})
                return {"ok": True}
            if metode == "PUT" and id_:
                body = self._baca_json()
                s.ubah_produk(id_, **{k: body.get(k, "") for k in FIELD_PRODUK})
                return {"ok": True}
            if metode == "DELETE" and id_:
                s.hapus_produk(id_)
                return {"ok": True}

        if sumber == "checkout" and metode == "POST":
            body = self._baca_json()
            items = body.get("items")
            if not isinstance(items, list):
                raise ValidasiError("Daftar item tidak valid")
            keranjang = Keranjang()
            for it in items:
                produk = s.cari_sku(it.get("sku", "")) if isinstance(it, dict) else None
                if produk is None:
                    raise ValidasiError("Ada produk yang tidak ditemukan")
                keranjang.tambah(produk, ke_int(it.get("qty", 0), "Jumlah"))
            uang = ke_int(body.get("uang", 0), "Uang diterima")
            trx, kembalian = s.checkout(keranjang, body.get("metode", ""),
                                        ke_int(body.get("diskon", 0), "Diskon"), uang)
            return {"transaksi": asdict(trx), "kembalian": kembalian,
                    "struk": struk_teks(trx, uang, kembalian)}

        if sumber == "transaksi" and metode == "GET":
            hasil = s.daftar_transaksi(kata=q.get("kata", ""), urut=q.get("urut") or "waktu",
                                       terbalik=q.get("arah", "desc") == "desc")
            return {"transaksi": [asdict(t) for t in hasil]}

        if sumber == "struk" and metode == "GET" and id_:
            trx = s.ambil_transaksi(id_)
            if trx is None:
                raise LookupError("Transaksi tidak ada")
            return {"struk": struk_teks(trx)}

        if sumber == "laporan" and metode == "GET":
            harian = [dict(tanggal=t, jumlah=n, pendapatan=p, hpp=h, laba=l)
                      for t, n, p, h, l in s.ringkasan_harian()]
            return {"total": s.ringkasan_total(), "harian": harian,
                    "menipis": len(s.stok_menipis())}

        raise LookupError("Rute tidak dikenal")

    # ---------- berkas statis ----------
    def _kirim_statis(self):
        jalur = unquote(urlparse(self.path).path)
        if jalur in ("", "/"):
            jalur = "/index.html"
        lokasi = os.path.normpath(os.path.join(FOLDER_STATIC, jalur.lstrip("/")))
        # cegah path traversal (../) keluar dari folder static
        if not lokasi.startswith(FOLDER_STATIC + os.sep):
            return self._kirim(404, b"Tidak ditemukan", "text/plain; charset=utf-8")
        try:
            with open(lokasi, "rb") as f:
                isi = f.read()
        except OSError:  # file tidak ada / tidak bisa dibaca
            return self._kirim(404, b"Tidak ditemukan", "text/plain; charset=utf-8")
        tipe = mimetypes.guess_type(lokasi)[0] or "application/octet-stream"
        if tipe.startswith("text/") or tipe.endswith("javascript"):
            tipe += "; charset=utf-8"
        self._kirim(200, isi, tipe)

    def _arahkan(self, metode):
        if urlparse(self.path).path.startswith("/api/"):
            self._tangani_api(metode)
        elif metode == "GET":
            self._kirim_statis()
        else:
            self._kirim(405, b"Metode tidak diizinkan", "text/plain; charset=utf-8")

    def do_GET(self):
        self._arahkan("GET")

    def do_POST(self):
        self._arahkan("POST")

    def do_PUT(self):
        self._arahkan("PUT")

    def do_DELETE(self):
        self._arahkan("DELETE")


class AplikasiWeb:
    """Membungkus HTTPServer; mencoba port berikutnya bila port sedang dipakai."""

    def __init__(self, service, host="127.0.0.1", port=8000):
        class Handler(PenangananRequest):
            layanan = service

        for p in range(port, port + 10):
            try:
                self.server = HTTPServer((host, p), Handler)
                break
            except OSError:  # port sibuk -> coba port lain
                continue
        else:
            raise OSError(f"Port {port}-{port + 9} semuanya sedang dipakai")
        self.url = f"http://{host}:{self.server.server_address[1]}"

    def jalankan(self, buka_browser=True):
        """Mulai melayani request sampai Ctrl+C."""
        print(f"UniCashier Dimsum Mentai berjalan di {self.url}  (Ctrl+C untuk berhenti)")
        if buka_browser:
            webbrowser.open(self.url)
        try:
            self.server.serve_forever()
        except KeyboardInterrupt:
            print("\nServer dihentikan.")
        finally:
            self.server.server_close()
