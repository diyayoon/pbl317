"""Pengiriman sertifikat produk ke email customer setelah pembayaran benar-benar disetujui."""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

from flask import current_app
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.extensions import db
from app.models import Order, OrderItem
from app.models.commerce import CertificateEmailDelivery
from app.utils import audit
from app.utils.email import kirim_email_dengan_lampiran, smtp_terkonfigurasi
from werkzeug.utils import secure_filename


class KesalahanSertifikatEmail(Exception):
    """Kesalahan terkontrol saat menyiapkan lampiran sertifikat."""


def _siapkan_lampiran(order: Order) -> list[dict]:
    base = Path(current_app.config["PRODUCT_CERTIFICATE_UPLOAD_FOLDER"]).resolve()
    seen_product_ids: set[int] = set()
    lampiran: list[dict] = []
    total_bytes = 0
    max_files = int(current_app.config.get("CERTIFICATE_EMAIL_MAX_ATTACHMENTS", 10))
    max_total = int(current_app.config.get("CERTIFICATE_EMAIL_MAX_TOTAL_BYTES", 18 * 1024 * 1024))

    for item in order.items:
        product = item.product
        if not product or not product.certificate_path or product.id in seen_product_ids:
            continue
        seen_product_ids.add(product.id)
        target = Path(product.certificate_path).resolve()
        if base not in target.parents or not target.is_file():
            raise KesalahanSertifikatEmail("Dokumen sertifikat salah satu produk tidak ditemukan pada penyimpanan privat.")
        if len(lampiran) >= max_files:
            raise KesalahanSertifikatEmail(f"Maksimal {max_files} dokumen sertifikat dapat dikirim dalam satu email.")
        raw = target.read_bytes()
        original_name = secure_filename(product.certificate_original_filename or target.name)
        ext = Path(original_name).suffix.lower() or target.suffix.lower()
        if ext != ".pdf":
            raise KesalahanSertifikatEmail("Sertifikat produk harus berupa file PDF.")
        if not raw.startswith(b"%PDF-"):
            raise KesalahanSertifikatEmail("Konten dokumen PDF tidak valid.")
        # Kirim dokumen PDF asli yang diunggah admin tanpa konversi atau perubahan isi.
        pdf_data = raw

        total_bytes += len(pdf_data)
        if total_bytes > max_total:
            raise KesalahanSertifikatEmail("Total ukuran sertifikat melebihi batas email.")
        nama_produk = secure_filename(product.name) or f"produk-{product.id}"
        lampiran.append({
            "filename": f"Sertifikat-{nama_produk}.pdf",
            "data": pdf_data,
            "maintype": "application",
            "subtype": "pdf",
        })
    return lampiran


def kirim_sertifikat_untuk_order(order_id: int, *, retry_failed: bool = False) -> str:
    """Kirim sertifikat sekali per pesanan; dapat dicoba ulang oleh admin bila pengiriman gagal.

    Pemanggil menjalankan fungsi ini setelah transaksi pembayaran sudah commit.
    Status 'sending' dicommit lebih dulu sehingga callback paralel tidak mengirim duplikat.
    """
    try:
        order = db.session.scalar(
            select(Order)
            .where(Order.id == order_id)
            .options(
                selectinload(Order.user),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.payment),
                selectinload(Order.certificate_delivery),
            )
            .with_for_update()
        )
        if not order or not order.payment or order.payment.status != "Disetujui":
            return "belum_dibayar"
        if order.status not in {"Diproses", "Dikirim", "Selesai"}:
            return "pesanan_tidak_aktif"

        delivery = db.session.scalar(
            select(CertificateEmailDelivery)
            .where(CertificateEmailDelivery.order_id == order.id)
            .with_for_update()
        )
        if delivery is None:
            delivery = CertificateEmailDelivery(order_id=order.id, status="pending")
            db.session.add(delivery)
            db.session.flush()
        if delivery.status == "sent":
            db.session.commit()
            return "sudah_dikirim"
        if delivery.status == "sending":
            terakhir = delivery.updated_at
            if terakhir and terakhir.tzinfo is None:
                terakhir = terakhir.replace(tzinfo=timezone.utc)
            masih_aktif = bool(terakhir and datetime.now(timezone.utc) - terakhir < timedelta(minutes=15))
            if not retry_failed or masih_aktif:
                db.session.commit()
                return "sedang_dikirim"
        if delivery.status == "failed" and not retry_failed:
            db.session.commit()
            return "gagal_perlu_retry_admin"
        if delivery.status == "no_certificate" and not retry_failed:
            db.session.commit()
            return "sertifikat_belum_tersedia"

        try:
            lampiran = _siapkan_lampiran(order)
        except Exception as exc:
            # File dapat hilang/rusak atau gagal diproses; status harus terlihat di Admin agar bisa ditindaklanjuti.
            current_app.logger.warning(
                "Lampiran sertifikat pesanan %s gagal disiapkan (%s).", order.id, type(exc).__name__
            )
            alasan = str(exc) if isinstance(exc, (KesalahanSertifikatEmail, OSError)) else type(exc).__name__
            delivery.status = "failed"
            delivery.last_error = (alasan or type(exc).__name__)[:300]
            delivery.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            audit.catat(
                "certificate_email_failed", "order", order.id, "Lampiran sertifikat gagal disiapkan.",
                category="certificate", event_action="certificate.email.failed", outcome="failure", severity="medium",
                context={"reason": (alasan or type(exc).__name__)[:180]}, commit=True,
            )
            return "gagal_menyiapkan_lampiran"

        if not lampiran:
            delivery.status = "no_certificate"
            delivery.attachment_count = 0
            delivery.last_error = "Tidak ada produk dalam pesanan yang memiliki dokumen sertifikat."
            delivery.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            audit.catat(
                "certificate_email_skipped", "order", order.id, "Email sertifikat dilewati karena tidak ada dokumen produk.",
                category="certificate", event_action="certificate.email.skipped_no_certificate", outcome="skipped", severity="info",
                commit=True,
            )
            return "sertifikat_belum_tersedia"

        if not smtp_terkonfigurasi():
            delivery.status = "failed"
            delivery.attachment_count = len(lampiran)
            delivery.last_error = "SMTP belum dikonfigurasi."
            delivery.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            audit.catat(
                "certificate_email_failed", "order", order.id, "Email sertifikat tidak dikirim karena SMTP belum dikonfigurasi.",
                category="certificate", event_action="certificate.email.failed", outcome="failure", severity="medium",
                context={"reason": "smtp_not_configured"}, commit=True,
            )
            return "smtp_belum_dikonfigurasi"

        tujuan = order.user.email.strip() if order.user and order.user.email else ""
        if not tujuan or "@" not in tujuan or tujuan.startswith("@") or tujuan.endswith("@"):
            delivery.status = "failed"
            delivery.attachment_count = len(lampiran)
            delivery.last_error = "Alamat email customer tidak tersedia atau tidak valid."
            delivery.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            audit.catat(
                "certificate_email_failed", "order", order.id, "Email sertifikat tidak dikirim karena alamat customer tidak valid.",
                category="certificate", event_action="certificate.email.failed", outcome="failure", severity="medium",
                context={"reason": "customer_email_missing_or_invalid"}, commit=True,
            )
            return "email_customer_tidak_valid"

        delivery.status = "sending"
        delivery.attempt_count = int(delivery.attempt_count or 0) + 1
        delivery.attachment_count = len(lampiran)
        delivery.last_error = None
        delivery.updated_at = datetime.now(timezone.utc)
        db.session.commit()

        customer_name = order.user.nama if order.user else "Pelanggan Albis Antique"
        nama_produk = sorted({item.product.name for item in order.items if item.product and item.product.certificate_path})
        daftar_nama = "\n".join(f"- {nama}" for nama in nama_produk)
        isi = (
            f"Halo {customer_name},\n\n"
            f"Terima kasih telah melakukan pembayaran untuk pesanan {order.order_number} di Albis Antique.\n"
            "Terlampir dokumen sertifikat yang tersedia untuk produk dalam pesanan Anda. "
            "Simpan dokumen ini sebagai arsip pembelian.\n\n"
            f"Produk:\n{daftar_nama}\n\n"
            "Catatan: sertifikat merupakan dokumen yang disediakan oleh penjual. "
            "Keabsahan klaim autentikasi mengikuti pemeriksaan dan informasi yang dicantumkan pada dokumen.\n\n"
            "Salam hangat,\nAlbis Antique"
        )
        try:
            terkirim = kirim_email_dengan_lampiran(
                tujuan,
                f"Sertifikat Produk — Pesanan {order.order_number} | Albis Antique",
                isi,
                lampiran,
            )
        except Exception as exc:
            current_app.logger.error("Pemanggilan SMTP sertifikat gagal (%s).", type(exc).__name__)
            terkirim = False

        # Reload record setelah proses SMTP karena commit 'sending' sudah menutup transaksi sebelumnya.
        delivery = db.session.scalar(select(CertificateEmailDelivery).where(CertificateEmailDelivery.order_id == order.id))
        if terkirim:
            delivery.status = "sent"
            delivery.sent_at = datetime.now(timezone.utc)
            delivery.last_error = None
            delivery.updated_at = datetime.now(timezone.utc)
            db.session.commit()
            audit.catat(
                "certificate_email_sent", "order", order.id, "Sertifikat produk berhasil dikirim ke email customer.",
                category="certificate", event_action="certificate.email.sent", outcome="success", severity="info",
                context={"attachment_count": len(lampiran)}, commit=True,
            )
            return "terkirim"

        delivery.status = "failed"
        delivery.last_error = "Server SMTP tidak menerima email sertifikat."
        delivery.updated_at = datetime.now(timezone.utc)
        db.session.commit()
        audit.catat(
            "certificate_email_failed", "order", order.id, "Server SMTP tidak menerima email sertifikat.",
            category="certificate", event_action="certificate.email.failed", outcome="failure", severity="medium",
            context={"attachment_count": len(lampiran)}, commit=True,
        )
        return "gagal_dikirim"
    except Exception:
        db.session.rollback()
        current_app.logger.exception("Proses pengiriman sertifikat untuk pesanan gagal (%s).", order_id)
        return "gagal_diproses"
