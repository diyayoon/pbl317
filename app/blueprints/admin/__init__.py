"""Blueprint admin untuk e-commerce single-store."""
from flask import Blueprint

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

from . import routes  # noqa: E402,F401
