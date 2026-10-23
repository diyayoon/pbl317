"""Blueprint admin Albis Antique."""
import importlib
import pkgutil

from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

# Semua modul route di folder ini dimuat otomatis. Tiap modul dimiliki satu orang,
# jadi file ini tidak perlu diubah saat menambah/menghapus modul.
for _modul in pkgutil.iter_modules(__path__):
    if not _modul.name.startswith('_'):
        importlib.import_module(f'{__name__}.{_modul.name}')
