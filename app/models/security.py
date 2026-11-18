"""Jejak audit dan pencatat percobaan (anti brute-force)."""
from datetime import datetime, timezone
from app.extensions import db


def utcnow():
    return datetime.now(timezone.utc)


class AuditLog(db.Model):
    """Catatan aktivitas penting (OWASP A09 / deteksi MITRE ATT&CK)."""
    __tablename__ = "audit_logs"

    id = db.Column(db.Integer, primary_key=True)
    actor_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    actor_email = db.Column(db.String(254), nullable=False, default="")
    action = db.Column(db.String(60), nullable=False, index=True)
    target_type = db.Column(db.String(40), nullable=False, default="")
    target_id = db.Column(db.String(60), nullable=False, default="")
    detail = db.Column(db.String(500), nullable=False, default="")
    ip = db.Column(db.String(45), nullable=False, default="")
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow, index=True)

    def to_dict(self):
        return {
            "id": self.id, "waktu": self.created_at.isoformat(), "aktor": self.actor_email or "—",
            "aksi": self.action, "target": f"{self.target_type} {self.target_id}".strip(),
            "detail": self.detail, "ip": self.ip,
        }


class RateLimitEvent(db.Model):
    """Satu kejadian (mis. login gagal) untuk menghitung batas per email/IP."""
    __tablename__ = "rate_limit_events"
    __table_args__ = (db.Index("ix_rate_limit_lookup", "kind", "key", "created_at"),)

    id = db.Column(db.Integer, primary_key=True)
    kind = db.Column(db.String(30), nullable=False)
    key = db.Column(db.String(254), nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)


class EmailVerificationToken(db.Model):
    """Token verifikasi email. Yang disimpan hanya hash SHA-256; token mentah hanya ada di email."""
    __tablename__ = "email_verification_tokens"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token_hash = db.Column(db.String(64), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    expires_at = db.Column(db.DateTime(timezone=True), nullable=False)
    used_at = db.Column(db.DateTime(timezone=True), nullable=True)
    code_hash = db.Column(db.String(64), nullable=True)
    attempts = db.Column(db.Integer, nullable=False, default=0)


class UserSession(db.Model):
    """Sesi login sisi server: dasar timeout inaktivitas dan pencabutan nyata saat logout. Hanya hash ID sesi yang disimpan."""
    __tablename__ = "user_sessions"

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    sid_hash = db.Column(db.String(64), nullable=False, unique=True)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    last_activity_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utcnow)
    revoked_at = db.Column(db.DateTime(timezone=True), nullable=True)
    revoke_reason = db.Column(db.String(30), nullable=True)
