"""Pengelolaan akun customer oleh admin (status, detail audit, soft delete)."""
from __future__ import annotations
import secrets
from datetime import datetime, timezone
from sqlalchemy import func, or_, select
from app.extensions import db
from app.models import Address, AuditLog, Order, Review, User
from app.utils import audit


class ErrorPelanggan(Exception):
    def __init__(self, pesan: str, kode: int = 422):
        super().__init__(pesan)
        self.pesan, self.kode = pesan, kode


def status_akun(u: User) -> str:
    if u.deleted_at is not None:
        return "Dihapus"
    return "Aktif" if u.is_active else "Nonaktif"


class LayananPelangganAdmin:
    @staticmethod
    def _ambil_customer(user_id: int, kunci: bool = False) -> User:
        """Hanya role customer yang bisa dikelola; admin lain tidak tersentuh (least privilege)."""
        stmt = select(User).where(User.id == user_id)
        if kunci:
            stmt = stmt.with_for_update()
        user = db.session.scalar(stmt)
        if user is None or user.role != "customer":
            raise ErrorPelanggan("Customer tidak ditemukan.", 404)
        return user

    @staticmethod
    def _ringkas(u: User, jumlah_pesanan: int = 0) -> dict:
        return {
            "id": u.id, "nama": u.nama, "email": u.email, "telepon": u.telepon, "role": u.role,
            "status": status_akun(u), "terverifikasi": bool(u.is_verified), "alasan": u.status_reason or "",
            "bergabung": u.created_at.isoformat() if u.created_at else "", "jumlahPesanan": jumlah_pesanan,
        }

    def daftar(self, q: str = "", status: str = "") -> list[dict]:
        stmt = select(User, func.count(Order.id)).outerjoin(Order, Order.user_id == User.id).where(User.role == "customer")
        q = " ".join((q or "").split())[:100]
        if q:
            pola = f"%{q.replace(chr(92), chr(92) * 2).replace('%', chr(92) + '%').replace('_', chr(92) + '_')}%"
            stmt = stmt.where(or_(User.nama.ilike(pola, escape="\\"), User.email.ilike(pola, escape="\\")))
        if status == "Dihapus":
            stmt = stmt.where(User.deleted_at.is_not(None))
        elif status == "Aktif":
            stmt = stmt.where(User.deleted_at.is_(None), User.is_active.is_(True))
        elif status == "Nonaktif":
            stmt = stmt.where(User.deleted_at.is_(None), User.is_active.is_(False))
        stmt = stmt.group_by(User.id).order_by(User.created_at.desc())
        return [self._ringkas(u, n) for u, n in db.session.execute(stmt).all()]

    def detail(self, user_id: int) -> dict:
        u = self._ambil_customer(user_id)
        data = self._ringkas(u, Order.query.filter_by(user_id=u.id).count())
        data["jumlahUlasan"] = Review.query.filter_by(user_id=u.id).count()
        data["jumlahAlamat"] = Address.query.filter_by(user_id=u.id).count()
        data["dihapusPada"] = u.deleted_at.isoformat() if u.deleted_at else ""
        # Aktivitas audit: tindakan akun ini sendiri + tindakan admin terhadap akun ini. Tanpa rahasia (audit tidak menyimpannya).
        rows = AuditLog.query.filter(or_(AuditLog.actor_id == u.id, (AuditLog.target_type == "user") & (AuditLog.target_id == str(u.id)))) \
            .order_by(AuditLog.created_at.desc()).limit(15).all()
        data["aktivitas"] = [{"waktu": r.created_at.isoformat(), "aksi": r.action, "aktor": r.actor_email or "—", "detail": r.detail} for r in rows]
        return data

    def ubah_status(self, user_id: int, aksi: str, alasan: str = "") -> dict:
        if aksi not in {"aktifkan", "nonaktifkan", "blokir"}:
            raise ErrorPelanggan("Aksi tidak dikenal.")
        alasan = " ".join((alasan or "").split())[:300]
        if aksi != "aktifkan" and len(alasan) < 5:
            raise ErrorPelanggan("Alasan wajib diisi (minimal 5 karakter).")
        u = self._ambil_customer(user_id, kunci=True)
        if u.deleted_at is not None:
            raise ErrorPelanggan("Akun sudah dihapus dan tidak dapat diubah.", 409)
        if aksi == "aktifkan":
            u.is_active, u.status_reason = True, None
        else:
            u.is_active, u.status_reason = False, alasan
            u.auth_version = (u.auth_version or 1) + 1  # cabut semua sesi/remember-me yang masih aktif
        audit.catat(f"akun_{aksi}", "user", u.id, f"{u.email}: {alasan}"[:500])
        db.session.commit()
        return self._ringkas(u, Order.query.filter_by(user_id=u.id).count())

    def hapus_lunak(self, user_id: int, konfirmasi_email: str, alasan: str = "") -> dict:
        u = self._ambil_customer(user_id, kunci=True)
        if u.deleted_at is not None:
            raise ErrorPelanggan("Akun sudah dihapus.", 409)
        if (konfirmasi_email or "").strip().lower() != u.email:
            raise ErrorPelanggan("Konfirmasi email tidak cocok.")
        email_lama = u.email
        # Pesanan/pembayaran tetap utuh (FK RESTRICT + snapshot alamat). Data pribadi dianonimkan.
        u.deleted_at = datetime.now(timezone.utc)
        u.is_active = False
        u.status_reason = " ".join((alasan or "dihapus oleh admin").split())[:300]
        u.email = f"dihapus-{u.id}@akun.invalid"
        u.nama, u.telepon, u.avatar_data, u.alamat_registrasi = "Akun Dihapus", "", None, None
        u.auth_version = (u.auth_version or 1) + 1
        u.set_password(secrets.token_urlsafe(32))  # hash acak: login mustahil
        Address.query.filter_by(user_id=u.id).delete(synchronize_session=False)
        audit.catat("akun_dihapus", "user", u.id, f"soft delete {email_lama}"[:500])
        db.session.commit()
        return self._ringkas(u, Order.query.filter_by(user_id=u.id).count())
