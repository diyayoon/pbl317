"""Tes registrasi: validasi server, CSRF, dan form yang tampil."""
import re
from datetime import date

import pytest

from app import buat_app
from app.utils.validasi import ValidasiRegistrasi


@pytest.fixture()
def klien():
    app = buat_app()
    app.config['TESTING'] = True
    return app.test_client()


def data_valid(**ubah):
    data = {
        'username': 'albis_collector',
        'password': 'kisah-masa-lalu-antik',
        'nama': "Mahdiya O'Neil-Putri",
        'tanggal_lahir': '2006-05-17',
        'alamat': 'Jl. Ahmad Yani No. 10, Batam Kota',
        'telepon': '081234567890',
    }
    data.update(ubah)
    return data


def periksa(**ubah):
    return ValidasiRegistrasi(data_valid(**ubah)).periksa()


# ===== ATURAN PER KOLOM =====
def test_data_valid_lolos_dan_telepon_dinormalisasi():
    nilai, galat = periksa()
    assert galat == {}
    assert nilai['telepon'] == '6281234567890'


@pytest.mark.parametrize('kolom,isi,kunci', [
    ('username', '', 'username'),
    ('username', 'ab', 'username'),
    ('username', 'a b c', 'username'),
    ('username', 'x' * 31, 'username'),
    ('password', 'pendek1', 'password'),
    ('password', 'x' * 15, 'password'),
    ('password', 'x' * 129, 'password'),
    ('password', ' ' * 20, 'password'),
    ('password', '', 'password'),
    ('nama', '', 'nama'),
    ('nama', 'Budi123', 'nama'),
    ('nama', '<script>', 'nama'),
    ('tanggal_lahir', '', 'tanggal_lahir'),
    ('tanggal_lahir', 'bukan-tanggal', 'tanggal_lahir'),
    ('tanggal_lahir', '1800-01-01', 'tanggal_lahir'),
    ('alamat', '', 'alamat'),
    ('alamat', 'pendek', 'alamat'),
    ('alamat', 'x' * 256, 'alamat'),
    ('telepon', '', 'telepon'),
    ('telepon', '12345', 'telepon'),
    ('telepon', '6212abc', 'telepon'),
])
def test_input_salah_ditolak(kolom, isi, kunci):
    _, galat = periksa(**{kolom: isi})
    assert kunci in galat


def test_tanggal_masa_depan_ditolak():
    depan = date.today().replace(year=date.today().year + 1).isoformat()
    assert 'tanggal_lahir' in periksa(tanggal_lahir=depan)[1]


@pytest.mark.parametrize('sandi', [
    'abcdefghijklmnop',          # 16 huruf kecil saja
    '1234567890123456',          # 16 angka saja
    'kalimat sandi dengan spasi',  # frasa panjang
    'x' * 128,                   # batas atas
])
def test_password_16_karakter_diterima_tanpa_syarat_huruf_besar_atau_simbol(sandi):
    assert 'password' not in periksa(password=sandi)[1]


def test_password_tidak_pernah_masuk_ke_nilai_balikan():
    nilai, _ = periksa()
    assert 'password' not in nilai


@pytest.mark.parametrize('mentah,hasil', [
    ('08123456789', '628123456789'),
    ('+62 812-3456-789', '628123456789'),
    ('0812 3456 789', '628123456789'),
    ('628123456789', '628123456789'),
])
def test_normalisasi_telepon(mentah, hasil):
    assert ValidasiRegistrasi.normalisasi_telepon(mentah) == hasil


def test_input_bukan_string_tidak_membuat_error_server():
    _, galat = ValidasiRegistrasi({'username': ['a'], 'password': None}).periksa()
    assert 'username' in galat and 'password' in galat


# ===== ROUTE =====
def ambil_token(klien):
    html = klien.get('/auth/register').get_data(as_text=True)
    return re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)


def test_form_register_punya_enam_kolom_dan_token(klien):
    html = klien.get('/auth/register').get_data(as_text=True)
    for nama in ('username', 'password', 'nama', 'tanggal_lahir', 'alamat', 'telepon'):
        assert f'name="{nama}"' in html
    assert 'name="csrf_token"' in html


def test_post_tanpa_token_csrf_ditolak(klien):
    assert klien.post('/auth/register', data=data_valid()).status_code == 400


def test_post_valid_dengan_token_diarahkan_ke_login(klien):
    token = ambil_token(klien)
    resp = klien.post('/auth/register', data={**data_valid(), 'csrf_token': token})
    assert resp.status_code == 302 and '/auth/login' in resp.headers['Location']


def test_post_salah_menampilkan_error_dan_menjaga_isian_tanpa_password(klien):
    token = ambil_token(klien)
    resp = klien.post('/auth/register', data={**data_valid(username='ab', password='rahasia123'), 'csrf_token': token})
    html = resp.get_data(as_text=True)
    assert resp.status_code == 422
    assert 'Username minimal 3 karakter.' in html
    assert 'value="ab"' in html
    assert 'rahasia123' not in html          # password tidak boleh dikembalikan ke browser
    assert 'Mahdiya' in html                 # isian lain dipertahankan


def test_input_berisi_html_di_escape(klien):
    token = ambil_token(klien)
    html = klien.post('/auth/register', data={**data_valid(nama='<script>alert(1)</script>'), 'csrf_token': token}).get_data(as_text=True)
    assert '<script>alert(1)</script>' not in html
    assert '&lt;script&gt;' in html


def test_login_post_tidak_lagi_400_karena_token(klien):
    html = klien.get('/auth/login').get_data(as_text=True)
    token = re.search(r'name="csrf_token" value="([^"]+)"', html).group(1)
    assert klien.post('/auth/login', data={'email': 'a@b.c', 'password': 'x', 'csrf_token': token}).status_code == 302
