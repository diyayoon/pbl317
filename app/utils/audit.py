"""Application audit trail + JSONL event stream untuk Wazuh.

Satu event dicatat ke PostgreSQL dan (setelah transaksi DB commit) ke file JSONL.
Jangan pernah masukkan password, hash, token, cookie, Server Key, atau signature mentah.
"""
from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from flask import current_app, g, has_app_context, has_request_context
from flask_login import current_user
from sqlalchemy import event
from sqlalchemy.orm import Session

from app.extensions import db
from app.models import AuditLog
from .network import client_ip

_PENDING_KEY = "_albis_audit_jsonl_pending"

# action lama tetap dipertahankan untuk kompatibilitas, event_action baru konsisten untuk Wazuh.
_ACTIONS = {
    "login_berhasil": ("authentication", "auth.login.success", "success", "info"),
    "login_admin_berhasil": ("authentication", "auth.login.admin_success", "success", "info"),
    "login_gagal": ("authentication", "auth.login.failed", "failure", "medium"),
    "login_diblokir": ("authentication", "auth.login.rate_limited", "blocked", "high"),
    "logout": ("authentication", "auth.logout", "success", "info"),
    "registrasi": ("authentication", "auth.register.success", "success", "info"),
    "registrasi_gagal": ("authentication", "auth.register.failed", "rejected", "low"),
    "registrasi_diblokir": ("authentication", "auth.register.rate_limited", "blocked", "high"),
    "verifikasi_email_dikirim": ("authentication", "auth.email_verification.sent", "success", "info"),
    "verifikasi_email_gagal_kirim": ("authentication", "auth.email_verification.delivery_failed", "failure", "medium"),
    "email_terverifikasi": ("authentication", "auth.email_verification.success", "success", "info"),
    "verifikasi_kode_salah": ("authentication", "auth.email_verification.failed", "failure", "medium"),
    "akses_ditolak": ("authorization", "auth.access.denied", "blocked", "medium"),
    "ganti_password": ("authentication", "auth.password.changed", "success", "info"),
    "ganti_password_gagal": ("authentication", "auth.password.change_failed", "failure", "medium"),
    "produk_dibuat": ("administration", "admin.product.created", "success", "low"),
    "sertifikat_produk_diunggah": ("administration", "admin.product.certificate_uploaded", "success", "medium"),
    "sertifikat_produk_dihapus": ("administration", "admin.product.certificate_removed", "success", "medium"),
    "upload_ditolak": ("application", "file.upload.rejected", "rejected", "medium"),
    "produk_diubah": ("administration", "admin.product.updated", "success", "low"),
    "produk_diaktifkan": ("administration", "admin.product.activated", "success", "low"),
    "produk_dinonaktifkan": ("administration", "admin.product.deactivated", "success", "medium"),
    "produk_dihapus": ("administration", "admin.product.deleted", "success", "medium"),
    "kategori_dibuat": ("administration", "admin.category.created", "success", "low"),
    "kategori_diubah": ("administration", "admin.category.updated", "success", "low"),
    "kategori_dihapus": ("administration", "admin.category.deleted", "success", "medium"),
    "kategori_dinonaktifkan": ("administration", "admin.category.deactivated", "success", "medium"),
    "status_pesanan": ("administration", "admin.order.status_changed", "success", "medium"),
    "pembayaran_disetujui": ("administration", "admin.payment.approved", "success", "medium"),
    "pembayaran_ditolak": ("administration", "admin.payment.rejected", "success", "medium"),
    "ulasan_disembunyikan": ("administration", "admin.review.hidden", "success", "low"),
    "ulasan_ditampilkan": ("administration", "admin.review.restored", "success", "low"),
    "akun_aktifkan": ("administration", "admin.customer.activated", "success", "medium"),
    "akun_nonaktifkan": ("administration", "admin.customer.deactivated", "success", "medium"),
    "akun_blokir": ("administration", "admin.customer.blocked", "success", "high"),
    "akun_dihapus": ("administration", "admin.customer.soft_deleted", "success", "medium"),
    "pesanan_dibuat": ("commerce", "order.created", "success", "info"),
    "pesanan_dibatalkan_pelanggan": ("commerce", "order.cancelled", "success", "info"),
    "bukti_bayar_diunggah": ("payment", "payment.proof_uploaded", "success", "info"),
    "ulasan_disimpan": ("commerce", "review.created", "success", "info"),
    "profil_diubah": ("commerce", "customer.profile.updated", "success", "info"),
    "alamat_diperbarui": ("commerce", "customer.addresses.updated", "success", "info"),
    "midtrans_transaksi_dibuat": ("payment", "payment.transaction.created", "success", "info"),
    "midtrans_jumlah_tidak_cocok": ("payment", "payment.amount_mismatch", "rejected", "high"),
    "midtrans_signature_invalid": ("payment", "payment.signature_invalid", "rejected", "high"),
    "midtrans_order_not_found": ("payment", "payment.order_not_found", "rejected", "high"),
    "midtrans_payload_invalid": ("payment", "payment.notification.invalid_payload", "rejected", "medium"),
    "midtrans_notifikasi_duplikat": ("payment", "payment.notification.duplicate", "duplicate", "low"),
    "midtrans_status_tidak_valid": ("payment", "payment.invalid_transition", "rejected", "high"),
    "midtrans_persetujuan_manual_diblokir": ("payment", "payment.manual_approval.blocked", "rejected", "high"),
    "midtrans_fraud_status_tidak_diterima": ("payment", "payment.fraud_status_not_accepted", "flagged", "high"),
    "midtrans_lunas": ("payment", "payment.settled", "success", "info"),
    "midtrans_bayar_setelah_batal": ("payment", "payment.settled_after_cancel", "flagged", "high"),
    "midtrans_cancel": ("payment", "payment.cancelled", "success", "info"),
    "midtrans_expire": ("payment", "payment.expired", "success", "info"),
    "refund_diajukan": ("payment", "refund.requested", "success", "info"),
    "refund_ditolak": ("payment", "refund.rejected", "success", "medium"),
    "refund_gateway_gagal": ("payment", "refund.gateway_failed", "failure", "high"),
    "refund_dikirim_ke_gateway": ("payment", "refund.sent_to_gateway", "success", "info"),
    "refund_terkonfirmasi": ("payment", "refund.confirmed", "success", "info"),
}

_SENSITIVE_KEYS = re.compile(r"password|passwd|secret|token|cookie|authorization|server.?key|signature|credential|session", re.I)
_SENSITIVE_TEXT = re.compile(r"(?i)\b(password|passwd|secret|token|server[_ -]?key|signature|authorization|cookie)\b(\s*[:=]\s*)([^,;\s]+)")


def _bersihkan_context(value, depth: int = 0):
    """Whitelist data JSON secara rekursif dan buang nama field yang berpotensi rahasia."""
    if depth > 4:
        return "[truncated]"
    if isinstance(value, dict):
        return {
            str(key)[:60]: _bersihkan_context(item, depth + 1)
            for key, item in value.items()
            if not _SENSITIVE_KEYS.search(str(key))
        }
    if isinstance(value, (list, tuple)):
        return [_bersihkan_context(item, depth + 1) for item in value[:30]]
    if value is None or isinstance(value, (bool, int, float)):
        return value
    return str(value).replace("\r", " ").replace("\n", " ")[:500]


def _append_jsonl(path_value: str, payload: dict) -> None:
    """Append satu JSON object per baris agar mudah dikoleksi Wazuh."""
    try:
        path = Path(path_value)
        path.parent.mkdir(parents=True, exist_ok=True, mode=0o750)
        flags = os.O_APPEND | os.O_CREAT | os.O_WRONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(str(path), flags, 0o640)
        try:
            if hasattr(os, "fchmod"):
                os.fchmod(fd, 0o640)
            encoded = memoryview((json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str) + "\n").encode("utf-8"))
            while encoded:
                written = os.write(fd, encoded)
                if written <= 0:
                    raise OSError("Tidak ada byte audit yang berhasil ditulis.")
                encoded = encoded[written:]
        finally:
            os.close(fd)
    except OSError:
        if has_app_context():
            current_app.logger.exception("Gagal menulis application audit JSONL.")


@event.listens_for(Session, "after_commit")
def _tulis_event_setelah_commit(session: Session) -> None:
    pending = session.info.pop(_PENDING_KEY, [])
    for path_value, payload in pending:
        if path_value:
            _append_jsonl(path_value, payload)


@event.listens_for(Session, "after_rollback")
def _buang_event_setelah_rollback(session: Session) -> None:
    # Event yang berada pada transaksi gagal tidak boleh mengklaim tindakan berhasil.
    session.info.pop(_PENDING_KEY, None)


def catat(
    aksi: str,
    target_type: str = "",
    target_id="",
    detail: str = "",
    actor=None,
    email: str = "",
    commit: bool = False,
    *,
    event_action: str | None = None,
    category: str | None = None,
    outcome: str | None = None,
    severity: str | None = None,
    context: dict | None = None,
    actor_role: str | None = None,
):
    """Tambahkan audit row dan antrikan event JSONL sampai transaksi berhasil commit.

    Parameter lama tetap didukung agar pemanggil yang sudah ada tidak rusak.
    """
    user = actor
    if user is None:
        try:
            if getattr(current_user, "is_authenticated", False):
                user = current_user
        except RuntimeError:  # CLI task: tidak ada request/login context
            user = None

    mapped = _ACTIONS.get(aksi, ("application", f"application.{aksi}", "success", "info"))
    kategori, tindakan, hasil, tingkat = mapped
    kategori = category or kategori
    tindakan = event_action or tindakan
    hasil = outcome or hasil
    tingkat = severity or tingkat

    actor_id = getattr(user, "id", None)
    role = actor_role or getattr(user, "role", None) or ("anonymous" if has_request_context() else "system")
    actor_email = (getattr(user, "email", "") or email or "")[:254]
    detail_aman = str(detail or "").replace("\r", " ").replace("\n", " ")[:500]
    detail_aman = _SENSITIVE_TEXT.sub(r"\1\2[REDACTED]", detail_aman)
    target_aman = str(target_id or "")[:60]
    created_at = datetime.now(timezone.utc)
    event_id = str(uuid4())
    try:
        request_id = str(getattr(g, "request_id", "") or "")[:36]
    except RuntimeError:
        request_id = ""
    if not request_id:
        request_id = str(uuid4())

    entry = AuditLog(
        event_id=event_id,
        event_category=kategori[:40],
        event_action=tindakan[:100],
        outcome=hasil[:20],
        severity=tingkat[:12],
        actor_id=actor_id,
        actor_email=actor_email,
        actor_role=role[:20],
        action=aksi[:60],
        target_type=str(target_type or "")[:40],
        target_id=target_aman,
        detail=detail_aman,
        ip=client_ip(),
        request_id=request_id,
        context_data=_bersihkan_context(context or {}),
        created_at=created_at,
    )
    db.session.add(entry)

    payload = {
        "timestamp": created_at.isoformat().replace("+00:00", "Z"),
        "app": "albis-antique",
        "event_id": event_id,
        "request_id": request_id,
        "event_category": kategori,
        "event_action": tindakan,
        "severity": tingkat,
        "outcome": hasil,
        "actor_id": actor_id,
        "actor_role": role,
        "target_type": str(target_type or "")[:40],
        "target_id": target_aman,
        "detail": detail_aman,
        "source_ip": entry.ip,
        "context": _bersihkan_context(context or {}),
    }
    path_value = current_app.config.get("AUDIT_LOG_FILE")
    db.session().info.setdefault(_PENDING_KEY, []).append((path_value, payload))

    if commit:
        try:
            db.session.commit()
        except Exception:
            db.session.rollback()
            current_app.logger.exception("Audit log gagal disimpan ke PostgreSQL.")
            raise
    return entry
