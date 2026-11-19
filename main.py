"""main.py - titik masuk aplikasi UniCashier Dimsum Mentai.

Jalankan:  python main.py   (browser terbuka otomatis)
"""
import os

from kasir.services import TokoService
from kasir.storage import Storage
from kasir.web import AplikasiWeb


def main():
    """Siapkan penyimpanan & service, lalu jalankan server web lokal."""
    folder_data = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
    service = TokoService(Storage(folder_data))
    AplikasiWeb(service).jalankan()


if __name__ == "__main__":
    main()
