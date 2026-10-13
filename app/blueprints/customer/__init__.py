"""Blueprint area customer Albis Antique."""
from flask import Blueprint

customer_bp = Blueprint('customer', __name__, url_prefix='/customer')

from . import routes  # noqa: E402,F401
