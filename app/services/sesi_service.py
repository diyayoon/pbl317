"""Sesi login sisi server: timeout inaktivitas, batas mutlak, dan pencabutan nyata (logout/ganti password)."""
from __future__ import annotations
import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from flask import current_app, session
from sqlalchemy import update
from app.extensions import db
from app.models import User, UserSession


def _hash(sid: str) -> str:
    return hashlib.sha256(sid.encode()).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _sekarang() -> datetime:
    return datetime.now(timezone.utc)


class LayananSesi:
    @staticmethod
    def batas_inaktif(role: str) -> timedelta:
        kunci = "SESI_INAKTIF_MENIT_ADMIN" if role == "admin" else "SESI_INAKTIF_MENIT_CUSTOMER"
        return timedelta(minutes=current_app.config[kunci])

    @staticmethod
    def mulai(user: User) -> None:
        """Buat record sesi baru dan simpan ID acaknya di cookie sesi (setelah login)."""
        sid = secrets.token_urlsafe(32)
        db.session.add(UserSession(user_id=user.id, sid_hash=_hash(sid)))
        db.session.commit()
        session["sid"] = sid

    @staticmethod
    def validasi(user: User) -> str | None:
        """None bila sesi sah; selain itu alasan penolakan. Sesi yang melewati batas dicabut permanen."""
        sid = session.get("sid")
        if not sid:
            return "tidak_ada"
        rec = db.session.scalar(db.select(UserSession).where(UserSession.sid_hash == _hash(str(sid))))
        if rec is None or rec.user_id != user.id:
            return "tidak_ada"
        if rec.revoked_at is not None:
            return "dicabut"
        sekarang = _sekarang()
        alasan = None
        if sekarang - _aware(rec.last_activity_at) > LayananSesi.batas_inaktif(user.role):
            alasan = "tidak_aktif"
        elif sekarang - _aware(rec.created_at) > timedelta(minutes=current_app.config["SESI_MAKS_MENIT"]):
            alasan = "terlalu_lama"
        if alasan:
            rec.revoked_at, rec.revoke_reason = sekarang, alasan
            db.session.commit()
        return alasan

    @staticmethod
    def sentuh() -> None:
        """Catat aktivitas user; ditulis paling sering sekali per SESI_SENTUH_DETIK agar murah."""
        sid = session.get("sid")
        if not sid:
            return
        sekarang = _sekarang()
        batas = sekarang - timedelta(seconds=current_app.config["SESI_SENTUH_DETIK"])
        db.session.execute(update(UserSession).where(
            UserSession.sid_hash == _hash(str(sid)), UserSession.revoked_at.is_(None), UserSession.last_activity_at < batas
        ).values(last_activity_at=sekarang), execution_options={"synchronize_session": False})
        db.session.commit()

    @staticmethod
    def cabut_saat_ini(alasan: str = "logout") -> None:
        sid = session.get("sid")
        if sid:
            db.session.execute(update(UserSession).where(UserSession.sid_hash == _hash(str(sid)), UserSession.revoked_at.is_(None))
                               .values(revoked_at=_sekarang(), revoke_reason=alasan), execution_options={"synchronize_session": False})
            db.session.commit()

    @staticmethod
    def cabut_semua(user_id: int, alasan: str = "ganti_password") -> None:
        db.session.execute(update(UserSession).where(UserSession.user_id == user_id, UserSession.revoked_at.is_(None))
                           .values(revoked_at=_sekarang(), revoke_reason=alasan), execution_options={"synchronize_session": False})
        db.session.commit()

    @staticmethod
    def pangkas(hari: int = 2) -> int:
        batas = _sekarang() - timedelta(days=hari)
        n = db.session.query(UserSession).filter(UserSession.revoked_at.is_not(None), UserSession.revoked_at < batas).delete()
        db.session.commit()
        return n
