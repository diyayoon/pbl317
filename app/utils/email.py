"""Pengiriman email via SMTP (mis. Gmail + App Password). Tidak ada simulasi: tanpa konfigurasi, tidak terkirim."""
from __future__ import annotations
import smtplib
import ssl
from email.message import EmailMessage
from flask import current_app


def smtp_terkonfigurasi() -> bool:
    c = current_app.config
    return bool(c.get("MAIL_SERVER") and c.get("MAIL_USERNAME") and c.get("MAIL_PASSWORD") and c.get("MAIL_FROM"))


def kirim_email(tujuan: str, subjek: str, isi: str) -> bool:
    """Mengembalikan True hanya bila server SMTP menerima pesan. Isi/kredensial tidak pernah dicatat ke log."""
    if not smtp_terkonfigurasi():
        current_app.logger.warning("Email tidak dikirim: SMTP belum dikonfigurasi (MAIL_*).")
        return False
    c = current_app.config
    pesan = EmailMessage()
    pesan["From"], pesan["To"], pesan["Subject"] = c["MAIL_FROM"], tujuan, subjek
    pesan.set_content(isi)
    konteks = ssl.create_default_context()
    try:
        if c["MAIL_SECURITY"] == "ssl":
            server = smtplib.SMTP_SSL(c["MAIL_SERVER"], c["MAIL_PORT"], timeout=10, context=konteks)
        else:
            server = smtplib.SMTP(c["MAIL_SERVER"], c["MAIL_PORT"], timeout=10)
            server.starttls(context=konteks)
        with server:
            server.login(c["MAIL_USERNAME"], c["MAIL_PASSWORD"])
            server.send_message(pesan)
        return True
    except (smtplib.SMTPException, OSError) as exc:
        current_app.logger.error("Gagal mengirim email verifikasi (%s).", type(exc).__name__)
        return False
