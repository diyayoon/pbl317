"""Form autentikasi berbasis Flask-WTF / WTForms.

CSRF juga dilindungi secara global oleh CSRFProtect pada application factory.
Field dan validator di sini memastikan validasi server-side konsisten.
"""
from __future__ import annotations
import re

from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp, ValidationError

_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_NAME_ALLOWED = set(" .'-")


def _normalize_name(value: str | None) -> str:
    return re.sub(r"\s+", " ", (value or "").strip())


def valid_name(_form, field) -> None:
    value = _normalize_name(field.data)
    field.data = value
    if len(value) < 3 or len(value) > 100:
        raise ValidationError("Nama lengkap harus terdiri dari 3–100 karakter.")
    if not value or not value[0].isalpha() or not all(ch.isalpha() or ch in _NAME_ALLOWED for ch in value):
        raise ValidationError("Nama hanya boleh berisi huruf, spasi, titik, apostrof, dan tanda hubung.")


class LoginForm(FlaskForm):
    email = StringField(
        "Email",
        filters=[lambda value: value.strip().lower() if isinstance(value, str) else value],
        validators=[
            DataRequired(message="Email wajib diisi."),
            Length(max=254, message="Email maksimal 254 karakter."),
            Regexp(_EMAIL_RE, message="Format email tidak valid."),
        ],
    )
    password = PasswordField(
        "Kata sandi",
        validators=[DataRequired(message="Kata sandi wajib diisi."), Length(max=128, message="Kata sandi terlalu panjang.")],
    )


class RegisterForm(FlaskForm):
    email = StringField(
        "Email",
        filters=[lambda value: value.strip().lower() if isinstance(value, str) else value],
        validators=[
            DataRequired(message="Email tidak boleh kosong."),
            Length(max=254, message="Email maksimal 254 karakter."),
            Regexp(_EMAIL_RE, message="Format email tidak valid."),
        ],
    )
    nama = StringField("Nama lengkap", filters=[_normalize_name], validators=[DataRequired(message="Nama lengkap wajib diisi."), valid_name])
    password = PasswordField(
        "Kata sandi",
        validators=[
            DataRequired(message="Kata sandi tidak boleh kosong."),
            Length(min=16, max=128, message="Kata sandi harus terdiri dari 16–128 karakter."),
        ],
    )
    konfirmasi_password = PasswordField(
        "Konfirmasi kata sandi",
        validators=[
            DataRequired(message="Konfirmasi kata sandi wajib diisi."),
            EqualTo("password", message="Konfirmasi kata sandi tidak cocok."),
        ],
    )
