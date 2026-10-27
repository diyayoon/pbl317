'use strict';

/* ===== KELAS PENGELOLA BAHASA ===== */
class PengelolaBahasa {
    constructor() {
        this.kunciPenyimpanan = 'albis_antique_bahasa';
        this.bahasaAktif = localStorage.getItem(this.kunciPenyimpanan) || 'id';

        /* ===== KAMUS ANTARMUKA ===== */
        this.kamus = {
            /* ===== BAHASA INDONESIA ===== */
            id: {
                /* ----- Navigasi (navbar) ----- */
                nav_home: 'Beranda',
                nav_shop: 'Katalog',
                nav_categories: 'Kategori',
                nav_about: 'Tentang',
                nav_login: 'Masuk',

                /* ----- Hero beranda ----- */
                hero_eyebrow: 'Kurasi Barang Antik Pilihan',
                hero_title: 'Kisah dari masa lalu, hadir kembali dalam koleksi yang anggun.',
                hero_desc: 'Jelajahi jam antik, kamera vintage, porselen, buku lama, perhiasan, dan benda koleksi yang dipilih dengan cermat dalam suasana frost yang elegan.',

                /* ----- Tombol hero ----- */
                shop_now: 'Belanja Sekarang',
                explore_collection: 'Jelajahi Koleksi',

                /* ----- Angka ringkas hero ----- */
                metric_piece: 'koleksi',
                metric_category: 'kategori',
                metric_unique: 'stok unik',

                /* ----- Section kategori ----- */
                category_eyebrow: 'Kategori Pilihan',
                category_title: 'Temukan koleksi berdasarkan karakter dan era',
                category_desc: 'Setiap kategori dirancang untuk memudahkan penelusuran tanpa menghilangkan kesan galeri antik.',
                view_all: 'Lihat semua →',

                /* ----- Section produk populer ----- */
                popular_eyebrow: 'Koleksi Terpopuler',
                popular_title: 'Benda yang paling banyak menarik perhatian',

                /* ----- Section produk baru ----- */
                new_eyebrow: 'Koleksi Terbaru',
                new_title: 'Temuan baru dari berbagai era',

                /* ----- Banner promo ----- */
                promo_eyebrow: 'Kurasi Musim Dingin',
                promo_title: 'Potongan sejarah yang pantas menjadi pusat perhatian.',
                promo_desc: 'Tampilan bernuansa es, aksen monarki, dan informasi produk yang jelas menyatu dalam pengalaman belanja modern.',
                promo_cta: 'Lihat Katalog',

                /* ----- Section rekomendasi ----- */
                recommended_eyebrow: 'Rekomendasi Kurator',
                recommended_title: 'Pilihan untuk kolektor yang menyukai detail',

                /* ----- Highlight toko ----- */
                highlight_1_title: 'Detail dan Asal-usul Terang' ,
                highlight_1_desc: 'Informasi era, asal, material, kondisi, dan status autentikasi ditampilkan dengan jelas.',
                highlight_2_title: 'Koleksi Unik dan Terbatas',
                highlight_2_desc: 'Sebagian besar barang antik bersifat unik sehingga stok dapat dibatasi secara realistis.',
                highlight_3_title: 'Kondisi Barang Transparan',
                highlight_3_desc: 'Foto dan catatan kondisi membantu kolektor menilai setiap benda sebelum memutuskan membeli.',

                /* ----- Halaman katalog ----- */
                catalog_eyebrow: 'Galeri Antik',
                catalog_title: 'Katalog Barang Antik',
                catalog_desc: 'Cari dan saring koleksi berdasarkan kata kunci, kategori, era, kondisi, dan rentang harga.',
                filter_title: 'Filter Koleksi',
                filter_button: 'Tampilkan Filter',
                search_label: 'Cari produk',

                /* ----- Section kategori ----- */
                category_label: 'Kategori',

                /* ----- Halaman katalog ----- */
                era_label: 'Era',
                condition_label: 'Kondisi',
                all_option: 'Semua',
                sort_label: 'Urutkan',
                sort_popular: 'Paling populer',
                sort_new: 'Terbaru',
                sort_low: 'Harga terendah',
                sort_high: 'Harga tertinggi',

                /* ----- Detail produk ----- */
                product_found: 'produk ditemukan',
                detail_eyebrow: 'Detail Koleksi',
                detail_add: 'Tambah ke Keranjang',
                detail_buy: 'Beli Sekarang',
                related_title: 'Koleksi terkait',
                spec_era: 'Era',
                spec_origin: 'Asal',
                spec_condition: 'Kondisi',
                spec_material: 'Material',
                spec_authenticity: 'Autentikasi',
                spec_stock: 'Stok',

                /* ----- Login dan daftar ----- */
                login_eyebrow: 'Akses Kolektor',
                login_visual_title: 'Masuk ke ruang koleksi pribadi Anda.',
                login_visual_desc: 'Kelola keranjang, riwayat pesanan, alamat, dan profil dalam satu tempat.',
                login_title: 'Selamat datang kembali',
                login_desc: 'Masuk menggunakan akun yang telah terdaftar.',
                email: 'Email',
                password: 'Kata sandi',
                remember: 'Ingat saya',
                forgot: 'Lupa kata sandi?',
                login_button: 'Masuk',
                no_account: 'Belum punya akun?',
                register_link: 'Daftar',
                register_title: 'Buat akun baru',
                register_desc: 'Daftar untuk mengelola profil dan melanjutkan checkout.',
                name: 'Nama lengkap',
                confirm_password: 'Konfirmasi kata sandi',
                register_button: 'Daftar',
                have_account: 'Sudah punya akun?',
                username: 'Username',
                birthdate: 'Tanggal lahir',
                address: 'Alamat',
                phone: 'Nomor telepon',
                username_placeholder: 'Contoh: albis_collector',
                password_placeholder: 'Minimal 16 karakter',
                name_placeholder: 'Masukkan nama lengkap',
                address_placeholder: 'Jalan, nomor, kelurahan, kota, kode pos',
                phone_placeholder: 'Contoh: 628123456789',
                phone_hint: 'Awalan 0 atau +62 otomatis jadi 62',
                login_link: 'Masuk',

                /* ----- Keranjang ----- */
                cart_title: 'Keranjang Belanja',
                cart_desc: 'Tinjau barang pilihan sebelum melanjutkan ke checkout.',
                cart_empty: 'Keranjang Anda masih kosong.',
                continue_shop: 'Lanjut Belanja',

                /* ----- Dashboard ----- */
                dashboard_title: 'Dashboard Pelanggan',
                dashboard_desc: 'Ringkasan akun, keranjang, dan riwayat pesanan.',
                admin_title: 'Dashboard Admin',
                admin_desc: 'Kelola produk, pengguna, pesanan, pembayaran, dan ringkasan transaksi.',

                /* ----- Footer ----- */
                footer_desc: 'Galeri digital untuk menjelajahi benda antik, cerita, dan koleksi lintas era.',
                footer_explore: 'Jelajahi',
                footer_help: 'Bantuan',
                footer_project: 'Proyek',
                footer_catalog: 'Katalog',
                footer_categories: 'Kategori',
                footer_orders: 'Pesanan',
                footer_payment: 'Pembayaran',
                footer_security: 'Keamanan',
                footer_note: 'Toko barang antik terkurasi dengan keaslian yang dapat dipertanggungjawabkan.',
            },

            /* ===== BAHASA INGGRIS ===== */
            en: {
                /* ----- Navigasi (navbar) ----- */
                nav_home: 'Home',
                nav_shop: 'Shop',
                nav_categories: 'Categories',
                nav_about: 'About',
                nav_login: 'Sign In',

                /* ----- Hero beranda ----- */
                hero_eyebrow: 'Curated Antique Collection',
                hero_title: 'Stories from the past, brought forward through an elegant collection.',
                hero_desc: 'Explore antique timepieces, vintage cameras, porcelain, old books, jewelry, and collectibles carefully selected within a refined frost-inspired atmosphere.',

                /* ----- Tombol hero ----- */
                shop_now: 'Shop Now',
                explore_collection: 'Explore Collection',

                /* ----- Angka ringkas hero ----- */
                metric_piece: 'pieces',
                metric_category: 'categories',
                metric_unique: 'unique stock',

                /* ----- Section kategori ----- */
                category_eyebrow: 'Featured Categories',
                category_title: 'Discover collections by character and era',
                category_desc: 'Each category is designed to make browsing effortless while preserving the feel of an antique gallery.',
                view_all: 'View all →',

                /* ----- Section produk populer ----- */
                popular_eyebrow: 'Most Coveted',
                popular_title: 'Pieces drawing the most attention',

                /* ----- Section produk baru ----- */
                new_eyebrow: 'New Arrivals',
                new_title: 'Recent finds from different eras',

                /* ----- Banner promo ----- */
                promo_eyebrow: 'Winter Curation',
                promo_title: 'Historic pieces worthy of becoming the center of attention.',
                promo_desc: 'Frost-inspired visuals, subtle royal accents, and clear product information come together in a modern shopping experience.',
                promo_cta: 'Browse Catalog',

                /* ----- Section rekomendasi ----- */
                recommended_eyebrow: 'Curator Picks',
                recommended_title: 'Selected for collectors who appreciate detail',

                /* ----- Highlight toko ----- */
                highlight_1_title: 'Clear Provenance Details',
                highlight_1_desc: 'Era, origin, material, condition, and authentication status are presented clearly.',
                highlight_2_title: 'Unique, Limited Pieces',
                highlight_2_desc: 'Many antiques are one-of-a-kind, making realistic limited stock a natural part of the catalog.',
                highlight_3_title: 'Transparent Condition Notes',
                highlight_3_desc: 'Photos and condition notes help collectors evaluate each piece before deciding to purchase.',

                /* ----- Halaman katalog ----- */
                catalog_eyebrow: 'Antique Gallery',
                catalog_title: 'Antique Catalog',
                catalog_desc: 'Search and filter collections by keyword, category, era, condition, and price range.',
                filter_title: 'Collection Filters',
                filter_button: 'Show Filters',
                search_label: 'Search products',

                /* ----- Section kategori ----- */
                category_label: 'Category',

                /* ----- Halaman katalog ----- */
                era_label: 'Era',
                condition_label: 'Condition',
                all_option: 'All',
                sort_label: 'Sort by',
                sort_popular: 'Most popular',
                sort_new: 'Newest',
                sort_low: 'Lowest price',
                sort_high: 'Highest price',

                /* ----- Detail produk ----- */
                product_found: 'products found',
                detail_eyebrow: 'Collection Details',
                detail_add: 'Add to Cart',
                detail_buy: 'Buy Now',
                related_title: 'Related collections',
                spec_era: 'Era',
                spec_origin: 'Origin',
                spec_condition: 'Condition',
                spec_material: 'Material',
                spec_authenticity: 'Authenticity',
                spec_stock: 'Stock',

                /* ----- Login dan daftar ----- */
                login_eyebrow: 'Collector Access',
                login_visual_title: 'Enter your personal collection space.',
                login_visual_desc: 'Manage your cart, order history, addresses, and profile in one place.',
                login_title: 'Welcome back',
                login_desc: 'Sign in using your registered account.',
                email: 'Email',
                password: 'Password',
                remember: 'Remember me',
                forgot: 'Forgot password?',
                login_button: 'Sign In',
                no_account: 'No account yet?',
                register_link: 'Register',
                register_title: 'Create an account',
                register_desc: 'Register to manage your profile and continue to checkout.',
                name: 'Full name',
                confirm_password: 'Confirm password',
                register_button: 'Register',
                have_account: 'Already have an account?',
                username: 'Username',
                birthdate: 'Date of birth',
                address: 'Address',
                phone: 'Phone number',
                username_placeholder: 'Example: albis_collector',
                password_placeholder: 'At least 16 characters',
                name_placeholder: 'Enter your full name',
                address_placeholder: 'Street, number, district, city, postal code',
                phone_placeholder: 'Example: 628123456789',
                phone_hint: 'A leading 0 or +62 becomes 62',
                login_link: 'Sign In',

                /* ----- Keranjang ----- */
                cart_title: 'Shopping Cart',
                cart_desc: 'Review your selected pieces before continuing to checkout.',
                cart_empty: 'Your cart is still empty.',
                continue_shop: 'Continue Shopping',

                /* ----- Dashboard ----- */
                dashboard_title: 'Customer Dashboard',
                dashboard_desc: 'A summary of your account, cart, and order history.',
                admin_title: 'Admin Dashboard',
                admin_desc: 'Manage products, users, orders, payments, and transaction summaries.',

                /* ----- Footer ----- */
                footer_desc: 'A digital gallery to explore antiques, stories, and collections across eras.',
                footer_explore: 'Explore',
                footer_help: 'Help',
                footer_project: 'Project',
                footer_catalog: 'Catalog',
                footer_categories: 'Categories',
                footer_orders: 'Orders',
                footer_payment: 'Payment',
                footer_note: 'A curated antiques store with authenticity you can rely on.',
            },
        };
    }

    /* ===== FUNGSI: MENERAPKAN BAHASA KE DOM ===== */
    terapkanBahasa() {
        const kamusAktif = this.kamus[this.bahasaAktif] || this.kamus.id;
        document.documentElement.lang = this.bahasaAktif;

        document.querySelectorAll('[data-i18n]').forEach((elemen) => {
            const kunci = elemen.dataset.i18n;
            if (kamusAktif[kunci]) elemen.textContent = kamusAktif[kunci];
        });

        document.querySelectorAll('[data-i18n-placeholder]').forEach((elemen) => {
            const kunci = elemen.dataset.i18nPlaceholder;
            if (kamusAktif[kunci]) elemen.placeholder = kamusAktif[kunci];
        });

        const tombolBahasa = document.getElementById('languageToggle');
        if (tombolBahasa) {
            tombolBahasa.classList.toggle('is-en', this.bahasaAktif === 'en');
            tombolBahasa.setAttribute('aria-pressed', String(this.bahasaAktif === 'en'));
            tombolBahasa.setAttribute('aria-label', this.bahasaAktif === 'id' ? 'Ganti bahasa ke English' : 'Switch language to Indonesian');
        }
    }

    /* ===== FUNGSI: MENGGANTI BAHASA ===== */
    gantiBahasa() {
        this.bahasaAktif = this.bahasaAktif === 'id' ? 'en' : 'id';
        localStorage.setItem(this.kunciPenyimpanan, this.bahasaAktif);
        this.terapkanBahasa();
    }
}

window.PengelolaBahasa = PengelolaBahasa;
