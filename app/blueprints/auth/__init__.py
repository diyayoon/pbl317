"""Blueprint autentikasi Albis Antique."""
import importlib
import pkgutil

from flask import Blueprint

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')

# Semua modul route di folder ini dimuat otomatis. Tiap modul dimiliki satu orang,
# jadi file ini tidak perlu diubah saat menambah/menghapus modul.
for _modul in pkgutil.iter_modules(__path__):
    if not _modul.name.startswith('_'):
        importlib.import_module(f'{__name__}.{_modul.name}')
