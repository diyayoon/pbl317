"""Validasi autentikasi harus dijalankan di server melalui Flask-WTF/WTForms."""

from app.models import AuditLog
from tests.conftest import PASSWORD


def test_login_menolak_email_tidak_valid_dengan_form_wtforms(client, app):
    response = client.post("/auth/login", data={"email": "bukan-email", "password": PASSWORD})
    assert response.status_code == 422
    assert b"Format email tidak valid" in response.data
    with app.app_context():
        event = AuditLog.query.filter_by(event_action="auth.login.failed").one()
        assert event.outcome == "rejected"
        assert event.context_data["reason"] == "invalid_input"


def test_register_menolak_konfirmasi_password_tidak_cocok(client):
    response = client.post("/auth/register", data={
        "email": "wtforms@example.test",
        "nama": "Pengguna WTForms",
        "password": PASSWORD,
        "konfirmasi_password": "PasswordBerbeda456",
    })
    assert response.status_code == 422
    assert b"Konfirmasi kata sandi tidak cocok" in response.data


def test_form_register_mengikuti_urutan_field_yang_diminta(client):
    response = client.get("/auth/register")
    html = response.get_data(as_text=True)
    positions = [html.index(f'name="{field}"') for field in (
        "email", "nama", "password", "konfirmasi_password"
    )]
    assert positions == sorted(positions)
