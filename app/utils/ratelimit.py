"""Pembatas percobaan berbasis database (aman untuk banyak worker gunicorn)."""
from datetime import datetime, timedelta, timezone
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError
from app.extensions import db
from app.models import RateLimitEvent


def _batas(menit: int):
    return datetime.now(timezone.utc) - timedelta(minutes=menit)


def jumlah(kind: str, key: str, menit: int) -> int:
    return db.session.scalar(
        db.select(func.count(RateLimitEvent.id)).where(
            RateLimitEvent.kind == kind, RateLimitEvent.key == key, RateLimitEvent.created_at >= _batas(menit)
        )
    ) or 0


def terblokir(kind: str, key: str, maksimum: int, menit: int) -> bool:
    return bool(key) and jumlah(kind, key, menit) >= maksimum


def catat(kind: str, key: str) -> None:
    if not key:
        return
    try:
        db.session.add(RateLimitEvent(kind=kind, key=key[:254]))
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


def bersihkan(kind: str, key: str) -> None:
    try:
        db.session.query(RateLimitEvent).filter_by(kind=kind, key=key).delete()
        db.session.commit()
    except SQLAlchemyError:
        db.session.rollback()


def pangkas_lama(hari: int = 2) -> int:
    """Hapus kejadian lama; dipanggil oleh `flask purge-security-events`."""
    batas = datetime.now(timezone.utc) - timedelta(days=hari)
    n = db.session.query(RateLimitEvent).filter(RateLimitEvent.created_at < batas).delete()
    db.session.commit()
    return n
