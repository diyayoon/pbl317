"""Frontend preview runtime for Albis Antique; no business backend or database."""
from types import SimpleNamespace
from flask import Flask, Blueprint, redirect, render_template, url_for, request
from flask_login import LoginManager, current_user
from flask_wtf.csrf import CSRFProtect

login_manager = LoginManager()
csrf = CSRFProtect()

# Preview-only data to render the existing FE templates. No persistence or business logic.
def obj(**kwargs):
    return SimpleNamespace(**kwargs)

SLIDES = [
    obj(nama="Jam Saku Klasik", gambar="https://images.unsplash.com/photo-1509048191080-d2984bad6f3a?auto=format&fit=crop&w=900&q=80", alt_gambar="Jam klasik", kategori="Jam Antik", era="Vintage", asal="Eropa", material="Logam", kondisi="Koleksi"),
    obj(nama="Kamera Analog", gambar="https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=900&q=80", alt_gambar="Kamera analog", kategori="Kamera", era="Retro", asal="Jepang", material="Logam", kondisi="Koleksi"),
]
CATEGORIES = [
    obj(slug="jam", gambar="https://images.unsplash.com/photo-1509048191080-d2984bad6f3a?auto=format&fit=crop&w=400&q=80", ikon="⌚", nama="Jam Antik", jumlah=12),
    obj(slug="kamera", gambar="https://images.unsplash.com/photo-1516035069371-29a1b244cc32?auto=format&fit=crop&w=400&q=80", ikon="📷", nama="Kamera Vintage", jumlah=8),
    obj(slug="dekorasi", gambar="https://images.unsplash.com/photo-1577083552431-6e5fd01aa342?auto=format&fit=crop&w=400&q=80", ikon="✧", nama="Dekorasi", jumlah=16),
    obj(slug="koleksi", gambar="https://images.unsplash.com/photo-1513364776144-60967b0f800f?auto=format&fit=crop&w=400&q=80", ikon="♔", nama="Barang Koleksi", jumlah=10),
]
PRODUCTS = [
    obj(id=1,nama="Jam Saku Klasik",kategori="Jam Antik",slug_kategori="jam",era="Vintage",asal="Eropa",kondisi="Baik",material="Logam",deskripsi="Jam saku klasik untuk kolektor.",harga=450000,stok=1,rating=4.9,ulasan=12,autentikasi="Deskripsi koleksi",sumber_gambar="",gambar=SLIDES[0].gambar,alt_gambar="Jam saku klasik"),
    obj(id=2,nama="Kamera Analog",kategori="Kamera Vintage",slug_kategori="kamera",era="Retro",asal="Jepang",kondisi="Baik",material="Logam",deskripsi="Kamera analog dengan karakter klasik.",harga=675000,stok=1,rating=4.8,ulasan=8,autentikasi="Deskripsi koleksi",sumber_gambar="",gambar=SLIDES[1].gambar,alt_gambar="Kamera analog"),
    obj(id=3,nama="Pajangan Artistik",kategori="Dekorasi",slug_kategori="dekorasi",era="Antik",asal="Indonesia",kondisi="Koleksi",material="Keramik",deskripsi="Pajangan untuk melengkapi ruang.",harga=325000,stok=1,rating=4.7,ulasan=3,autentikasi="Deskripsi koleksi",sumber_gambar="",gambar="https://images.unsplash.com/photo-1577083552431-6e5fd01aa342?auto=format&fit=crop&w=900&q=80",alt_gambar="Pajangan artistik"),
]

main = Blueprint('main', __name__)
auth = Blueprint('auth', __name__, url_prefix='/auth')
customer = Blueprint('customer', __name__, url_prefix='/customer')
admin = Blueprint('admin', __name__, url_prefix='/admin')

@main.get('/')
def beranda():
    return render_template('main/index.html', produk_slide=SLIDES, kategori_unggulan=CATEGORIES,
                           produk_unggulan=PRODUCTS[:2], produk_terbaru=PRODUCTS[1:])

@main.get('/katalog')
def katalog():
    # Preview catalog page; uses only sample presentation data.
    return render_template('main/explore.html', produk=PRODUCTS, produk_list=PRODUCTS,
                           produk_katalog=PRODUCTS, kategori_unggulan=CATEGORIES,
                           kategori=CATEGORIES, kategori_aktif=None, q=request.args.get('q',''),
                           halaman=1, total_halaman=1, total_produk=len(PRODUCTS))

@main.get('/produk/<int:produk_id>')
def detail_produk(produk_id):
    item = next((p for p in PRODUCTS if p.id == produk_id), PRODUCTS[0])
    return render_template('main/product.html', produk=item, produk_terkait=PRODUCTS, terkait=PRODUCTS, daftar_ulasan=[])

@auth.route('/login', methods=['GET','POST'])
def login(): return _placeholder('Login', 'Tampilan login tersedia; autentikasi belum diaktifkan pada paket FE-only.')
@auth.route('/register', methods=['GET','POST'])
def register(): return _placeholder('Registrasi', 'Tampilan registrasi tersedia; pembuatan akun belum diaktifkan pada paket FE-only.')
@auth.route('/logout', methods=['GET','POST'])
def logout(): return redirect(url_for('main.beranda'))

@customer.get('/<path:halaman>')
def customer_pages(halaman): return _placeholder('Area Customer', 'Halaman akun memerlukan backend untuk data dan autentikasi.')
@admin.get('/<path:halaman>')
def admin_pages(halaman): return _placeholder('Area Admin', 'Panel admin memerlukan backend untuk data dan operasi CRUD.')

# Endpoint names referenced by existing templates and JavaScript; no CRUD/data actions.
def _register_compat_endpoints(app):
    names = ['akun','api_produk','api_ubah_produk','audit_log','dashboard','kategori','laporan','pembayaran','pengguna','pesanan','produk','ulasan']
    for name in names:
        endpoint = 'admin.' + name
        if endpoint not in app.view_functions:
            app.add_url_rule('/_preview/admin/' + name, endpoint=endpoint,
                             view_func=lambda name=name: _placeholder('Preview Admin', 'Backend admin tidak disertakan.'), methods=['GET','POST','PATCH','DELETE'])
    customer_names = ['checkout','dashboard','keamanan','keranjang','pesanan','profil']
    for name in customer_names:
        endpoint = 'customer.' + name
        if endpoint not in app.view_functions:
            app.add_url_rule('/_preview/customer/' + name, endpoint=endpoint,
                             view_func=lambda name=name: _placeholder('Preview Customer', 'Backend customer tidak disertakan.'), methods=['GET','POST'])

def _placeholder(judul, pesan):
    from flask import render_template_string
    return render_template_string("""<!doctype html><html lang="id"><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>{{judul}} — Albis Antique</title><style>body{font:16px Manrope,Arial,sans-serif;background:#f3fbff;color:#183b50;display:grid;place-items:center;min-height:90vh;margin:0}.card{max-width:560px;margin:24px;padding:32px;border:1px solid #c9e7f4;border-radius:20px;background:white;box-shadow:0 12px 40px #234c6615}a{color:#24658a}</style><div class="card"><h1>{{judul}}</h1><p>{{pesan}}</p><p><a href="{{url_for('main.beranda')}}">← Kembali ke beranda</a></p></div></html>""", judul=judul, pesan=pesan)

def buat_app():
    app = Flask(__name__)
    app.config.update(SECRET_KEY=__import__('os').environ.get('SECRET_KEY', 'dev-preview-only-change-before-deploy'), WTF_CSRF_TIME_LIMIT=28800)
    login_manager.init_app(app)
    csrf.init_app(app)
    @login_manager.user_loader
    def load_user(_user_id): return None
    app.register_blueprint(main); app.register_blueprint(auth); app.register_blueprint(customer); app.register_blueprint(admin)
    _register_compat_endpoints(app)
    @app.get('/health')
    def health(): return {'status':'ok','mode':'frontend-preview'}, 200
    @app.context_processor
    def template_context():
        return {'is_customer_workspace':False,'is_admin_workspace':False,'workspace_body_classes':'', 'sebagai_customer':False}
    @app.errorhandler(404)
    def not_found(_error): return redirect(url_for('main.beranda'))
    return app
