"""Konfigurasi aplikasi. Secret tidak memiliki fallback production yang mudah ditebak."""
import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / '.env')

class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'hanya-untuk-development-lokal-ganti-di-env')
    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///:memory:')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # Akun demo hanya untuk pengembangan lokal; matikan saat autentikasi DB aktif.
    DEMO_AUTH_ENABLED = os.getenv('DEMO_AUTH_ENABLED', '1').lower() in {'1', 'true', 'yes'}
    MAX_CONTENT_LENGTH = 5 * 1024 * 1024
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    WTF_CSRF_TIME_LIMIT = 3600

class DevelopmentConfig(Config):
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    DEBUG = False
    SESSION_COOKIE_SECURE = True
