"""Alamat klien. X-Real-IP hanya dipercaya bila aplikasi memang berada di belakang proxy."""
from flask import current_app, request


def client_ip() -> str:
    # Perintah CLI (mis. create-admin) tidak memiliki request context dan tidak punya IP HTTP.
    try:
        ip = request.remote_addr or ""
    except RuntimeError:
        return ""
    if current_app.config.get("TRUSTED_PROXY_COUNT", 0) > 0:
        ip = request.headers.get("X-Real-IP", "").strip() or ip
    return ip[:45]
