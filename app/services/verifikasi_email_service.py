"""Verifikasi email: token acak, disimpan sebagai hash, kedaluwarsa, sekali pakai."""
from __future__ import annotations
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app, request, url_for
from sqlalchemy import update
from app.extensions import db
from app.models import EmailVerificationToken, User
from app.utils import audit, ratelimit
from app.utils import email as mailer


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def _hash_kode(user_id: int, kode: str) -> str:
    """HMAC dengan SECRET_KEY + id user: kode pendek tidak bisa ditebak offline dari dump database."""
    kunci = current_app.config["SECRET_KEY"].encode()
    return hmac.new(kunci, f"{user_id}:{kode}".encode(), hashlib.sha256).hexdigest()


def samarkan_email(email: str) -> str:
    """m***********17@gmail.com: tampilkan hanya awal dan akhir bagian lokal."""
    lokal, _, domain = email.partition("@")
    if len(lokal) <= 3:
        return lokal[:1] + "*" * max(len(lokal) - 1, 1) + "@" + domain
    return lokal[0] + "*" * (len(lokal) - 3) + lokal[-2:] + "@" + domain


def _tautan(token: str) -> str:
    path = url_for("auth.verifikasi_konfirmasi", token=token)
    dasar = current_app.config.get("APP_BASE_URL")
    if not dasar:
        if current_app.config.get("APP_ENV") == "production":
            raise RuntimeError("APP_BASE_URL belum diisi.")  # tidak pernah memakai header Host di produksi
        dasar = request.url_root.rstrip("/")  # hanya development/test
    return dasar + path


class LayananVerifikasiEmail:
    @staticmethod
    def buat_token(user: User) -> tuple[str, str]:
        sekarang = datetime.now(timezone.utc)
        # Token lama yang belum dipakai dibatalkan: hanya tautan terbaru yang berlaku.
        db.session.execute(update(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.id, EmailVerificationToken.used_at.is_(None)).values(used_at=sekarang),
            execution_options={"synchronize_session": False})
        mentah = secrets.token_urlsafe(32)
        digit = min(max(current_app.config["EMAIL_VERIFY_KODE_DIGIT"], 4), 8)
        kode = "".join(secrets.choice("0123456789") for _ in range(digit))
        db.session.add(EmailVerificationToken(
            user_id=user.id, token_hash=_hash(mentah), code_hash=_hash_kode(user.id, kode),
            expires_at=sekarang + timedelta(hours=current_app.config["EMAIL_VERIFY_TTL_JAM"])))
        db.session.commit()
        return mentah, kode

    def kirim(self, user: User) -> bool:
        token, kode = self.buat_token(user)
        jam = current_app.config["EMAIL_VERIFY_TTL_JAM"]
        isi = (f"Halo {user.nama},\n\nKode verifikasi: {kode}\n\n"
               f"Masukkan kode itu di halaman verifikasi, atau klik tautan berikut "
               f"(berlaku {jam} jam, hanya sekali pakai):\n\n{_tautan(token)}\n\n"
               "Jangan bagikan kode ini kepada siapa pun. Jika Anda tidak merasa mendaftar, abaikan email ini.\n")
        terkirim = mailer.kirim_email(user.email, "Verifikasi email Albis Antique", isi)
        audit.catat("verifikasi_email_dikirim" if terkirim else "verifikasi_email_gagal_kirim", "user", user.id, commit=True)
        return terkirim

    @staticmethod
    def sisa_cooldown(user: User) -> int:
        terakhir = db.session.scalar(db.select(EmailVerificationToken.created_at).where(
            EmailVerificationToken.user_id == user.id).order_by(EmailVerificationToken.created_at.desc()).limit(1))
        if terakhir is None:
            return 0
        if terakhir.tzinfo is None:
            terakhir = terakhir.replace(tzinfo=timezone.utc)
        sisa = current_app.config["EMAIL_VERIFY_COOLDOWN_DETIK"] - (datetime.now(timezone.utc) - terakhir).total_seconds()
        return max(0, int(sisa) + (1 if sisa > 0 else 0))

    def kirim_ulang(self, user: User, ip: str) -> tuple[bool, str]:
        """Mengembalikan (berhasil, pesan). Dibatasi cooldown per akun, kuota per jam per akun dan per IP."""
        cfg = current_app.config
        if user.is_verified:
            return False, "Email Anda sudah terverifikasi."
        terakhir = db.session.scalar(db.select(EmailVerificationToken.created_at).where(
            EmailVerificationToken.user_id == user.id).order_by(EmailVerificationToken.created_at.desc()).limit(1))
        if terakhir is not None:
            if terakhir.tzinfo is None:
                terakhir = terakhir.replace(tzinfo=timezone.utc)
            sisa = cfg["EMAIL_VERIFY_COOLDOWN_DETIK"] - (datetime.now(timezone.utc) - terakhir).total_seconds()
            if sisa > 0:
                return False, f"Tunggu {int(sisa) + 1} detik sebelum mengirim ulang."
        if ratelimit.terblokir("verif_kirim_user", str(user.id), cfg["EMAIL_VERIFY_MAX_PER_JAM"], 60) \
                or ratelimit.terblokir("verif_kirim_ip", ip, cfg["EMAIL_VERIFY_MAX_PER_JAM"] * 4, 60):
            return False, "Terlalu banyak permintaan. Coba lagi dalam satu jam."
        ratelimit.catat("verif_kirim_user", str(user.id))
        ratelimit.catat("verif_kirim_ip", ip)
        if self.kirim(user):
            return True, "Email verifikasi dikirim. Periksa kotak masuk dan folder spam."
        return False, "Email belum dapat dikirim saat ini. Coba lagi nanti atau hubungi admin."

    @staticmethod
    def verifikasi(token: str) -> bool:
        """Klaim token secara atomik (UPDATE ... WHERE used_at IS NULL), sehingga dua klik bersamaan tidak lolos keduanya."""
        sekarang = datetime.now(timezone.utc)
        baris = db.session.execute(db.select(EmailVerificationToken).where(EmailVerificationToken.token_hash == _hash(token or ""))).scalar_one_or_none()
        if baris is None:
            return False
        klaim = db.session.execute(update(EmailVerificationToken).where(
            EmailVerificationToken.id == baris.id, EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > sekarang).values(used_at=sekarang),
            execution_options={"synchronize_session": False})
        if klaim.rowcount != 1:
            db.session.rollback()
            return False
        user = db.session.get(User, baris.user_id)
        if user is None or user.deleted_at is not None or not user.is_active:
            db.session.rollback()
            return False
        user.is_verified, user.email_verified_at = True, sekarang
        audit.catat("email_terverifikasi", "user", user.id, actor=user)
        db.session.commit()
        return True

    @staticmethod
    def verifikasi_kode(user: User, kode: str) -> str:
        """Hasil: 'ok', 'salah', atau 'mati' (kedaluwarsa/habis percobaan/tidak ada kode aktif; minta kirim ulang)."""
        cfg = current_app.config
        sekarang = datetime.now(timezone.utc)
        if user.is_verified or user.deleted_at is not None or not user.is_active:
            return "mati"
        baris = db.session.execute(db.select(EmailVerificationToken).where(
            EmailVerificationToken.user_id == user.id, EmailVerificationToken.used_at.is_(None),
            EmailVerificationToken.expires_at > sekarang, EmailVerificationToken.code_hash.is_not(None))
            .order_by(EmailVerificationToken.created_at.desc()).limit(1).with_for_update()).scalar_one_or_none()
        if baris is None or baris.attempts >= cfg["EMAIL_VERIFY_KODE_MAX_SALAH"]:
            db.session.rollback()
            return "mati"
        if not hmac.compare_digest(baris.code_hash, _hash_kode(user.id, kode)):
            baris.attempts += 1
            if baris.attempts >= cfg["EMAIL_VERIFY_KODE_MAX_SALAH"]:
                baris.used_at = sekarang  # habis percobaan: kode dimatikan, wajib kirim ulang
            audit.catat("verifikasi_kode_salah", "user", user.id, f"percobaan ke-{baris.attempts}")
            db.session.commit()
            return "mati" if baris.attempts >= cfg["EMAIL_VERIFY_KODE_MAX_SALAH"] else "salah"
        baris.used_at = sekarang
        user.is_verified, user.email_verified_at = True, sekarang
        audit.catat("email_terverifikasi", "user", user.id, "lewat kode", actor=user)
        db.session.commit()
        return "ok"
