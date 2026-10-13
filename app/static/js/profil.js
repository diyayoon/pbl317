'use strict';

/* ======================================================================
   FILE   : profil.js
   ISI    : Halaman Profil Pribadi (prototipe frontend)
   CATATAN: Data disimpan di localStorage browser, sama seperti keranjang.
            Validasi di sini hanya untuk kenyamanan pengguna. Saat backend
            aktif, aturan yang sama WAJIB diperiksa ulang di server
            (app/utils/validasi.py), karena browser tidak boleh dipercaya.
   DAFTAR BAGIAN (cari dengan Ctrl+F: "=====" + nama):
      1. KONSTANTA
      2. KELAS PENYIMPAN LOKAL
      3. KELAS VALIDATOR FORM
      4. KELAS EDITOR FOTO
      5. KELAS HALAMAN PROFIL
      6. INISIALISASI
   ==================================================================== */

/* ===== KONSTANTA ===== */
const KUNCI_PROFIL = 'albis_antique_profil_demo';
const KUNCI_ALAMAT = 'albis_antique_alamat_demo';
const UKURAN_FOTO_MAKS = 5 * 1024 * 1024; /* sama dengan MAX_CONTENT_LENGTH di config.py */
const TIPE_FOTO_BOLEH = ['image/png', 'image/jpeg', 'image/webp'];
const PROFIL_BAWAAN = { nama: 'Demo Customer', email: 'customer@example.test', foto: null };
const ALAMAT_BAWAAN = { daftar: [], utamaId: null };

/* Peta kolom form alamat: kunci -> [id kolom, id pesan galat] */
const KOLOM_ALAMAT = {
    label: ['alamatLabel', 'galatLabel'],
    penerima: ['alamatPenerima', 'galatPenerima'],
    telepon: ['alamatTelepon', 'galatTelepon'],
    kodePos: ['alamatKodePos', 'galatKodePos'],
    provinsi: ['alamatProvinsi', 'galatProvinsi'],
    kota: ['alamatKota', 'galatKota'],
    kecamatan: ['alamatKecamatan', 'galatKecamatan'],
    lengkap: ['alamatLengkap', 'galatLengkap'],
};

/* ===== KELAS PENYIMPAN LOKAL ===== */
class PenyimpanLokal {
    constructor(kunci, bawaan) {
        this.kunci = kunci;
        this.bawaan = bawaan;
    }

    /* ===== FUNGSI: MEMBACA DATA (JIKA RUSAK / KOSONG, PAKAI NILAI BAWAAN) ===== */
    baca() {
        const salinanBawaan = JSON.parse(JSON.stringify(this.bawaan));
        try {
            const mentah = localStorage.getItem(this.kunci);
            if (!mentah) return salinanBawaan;
            const data = JSON.parse(mentah);
            return data && typeof data === 'object' ? { ...salinanBawaan, ...data } : salinanBawaan;
        } catch {
            return salinanBawaan;
        }
    }

    /* ===== FUNGSI: MENULIS DATA; MENGEMBALIKAN false JIKA GAGAL (PENUH / DIBLOKIR) ===== */
    simpan(data) {
        try {
            localStorage.setItem(this.kunci, JSON.stringify(data));
            return true;
        } catch {
            return false;
        }
    }
}

/* ===== KELAS VALIDATOR FORM ===== */
/* Aturan dibuat sama dengan validasi register (app/utils/validasi.py). */
class ValidatorForm {
    /* ===== FUNGSI: MERAPIKAN SPASI BERLEBIH DI DALAM TEKS ===== */
    static rapikan(teks) {
        return teks.replace(/\s+/g, ' ').trim();
    }

    /* ===== FUNGSI: MERAPIKAN NOMOR TELEPON (08xx / +62xx -> 62xx, hanya angka) ===== */
    static normalisasiTelepon(teks) {
        let angka = teks.replace(/[^\d+]/g, '').replace(/^\+/, '').replace(/\+/g, '');
        if (angka.startsWith('0')) angka = `62${angka.slice(1)}`;
        return angka;
    }

    /* ===== ATURAN: NAMA (2-100 KARAKTER, HURUF / SPASI / . ' -) ===== */
    static nama(teks, sebutan = 'Nama') {
        const nilai = ValidatorForm.rapikan(teks);
        if (!nilai) return `${sebutan} tidak boleh kosong.`;
        if (nilai.length < 2) return `${sebutan} minimal 2 karakter.`;
        if (nilai.length > 100 || !/^\p{L}[\p{L} .'-]*$/u.test(nilai)) {
            return `${sebutan} hanya boleh berisi huruf, spasi, titik, apostrof, dan tanda hubung.`;
        }
        return '';
    }

    /* ===== ATURAN: EMAIL ===== */
    static email(teks) {
        const nilai = teks.trim();
        if (!nilai) return 'Email tidak boleh kosong.';
        if (nilai.length > 254 || !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(nilai)) return 'Format email tidak valid.';
        return '';
    }

    /* ===== ATURAN: NOMOR TELEPON (AWALAN 62, 10-15 ANGKA) ===== */
    static telepon(teks) {
        const nilai = ValidatorForm.normalisasiTelepon(teks);
        if (!nilai) return 'Nomor telepon tidak boleh kosong.';
        if (!/^62\d{8,13}$/.test(nilai)) return 'Nomor telepon harus diawali 62 dan berisi 10-15 angka.';
        return '';
    }

    /* ===== ATURAN: KODE POS (5 ANGKA) ===== */
    static kodePos(teks) {
        if (!teks.trim()) return 'Kode pos tidak boleh kosong.';
        if (!/^\d{5}$/.test(teks.trim())) return 'Kode pos harus 5 angka.';
        return '';
    }

    /* ===== ATURAN: NAMA WILAYAH (PROVINSI / KOTA / KECAMATAN) ===== */
    static wilayah(teks, sebutan) {
        const nilai = ValidatorForm.rapikan(teks);
        if (!nilai) return `${sebutan} tidak boleh kosong.`;
        if (nilai.length < 2) return `${sebutan} minimal 2 karakter.`;
        if (nilai.length > 100 || !/^[\p{L}\p{N} .,'/-]+$/u.test(nilai)) {
            return `${sebutan} berisi karakter yang tidak diizinkan.`;
        }
        return '';
    }

    /* ===== ATURAN: ALAMAT LENGKAP (10-255 KARAKTER) ===== */
    static alamatLengkap(teks) {
        const nilai = teks.replace(/[ \t]+/g, ' ').trim();
        if (!nilai) return 'Alamat lengkap tidak boleh kosong.';
        if (nilai.length < 10) return 'Alamat terlalu singkat, tuliskan minimal 10 karakter.';
        if (nilai.length > 255) return 'Alamat maksimal 255 karakter.';
        return '';
    }

    /* ===== FUNGSI: MEMERIKSA SATU FORM ALAMAT; MENGEMBALIKAN { bersih, galat } ===== */
    static alamat(mentah) {
        const label = ValidatorForm.rapikan(mentah.label);
        const galat = {};
        const atur = (kunci, pesan) => {
            if (pesan) galat[kunci] = pesan;
        };

        if (label && (label.length > 30 || !/^[\p{L}\p{N} .,'/-]+$/u.test(label))) {
            galat.label = 'Label maksimal 30 karakter dan tidak boleh berisi simbol aneh.';
        }
        atur('penerima', ValidatorForm.nama(mentah.penerima, 'Nama penerima'));
        atur('telepon', ValidatorForm.telepon(mentah.telepon));
        atur('kodePos', ValidatorForm.kodePos(mentah.kodePos));
        atur('provinsi', ValidatorForm.wilayah(mentah.provinsi, 'Provinsi'));
        atur('kota', ValidatorForm.wilayah(mentah.kota, 'Kota / kabupaten'));
        atur('kecamatan', ValidatorForm.wilayah(mentah.kecamatan, 'Kecamatan / kelurahan'));
        atur('lengkap', ValidatorForm.alamatLengkap(mentah.lengkap));

        const bersih = {
            label: label || 'Alamat',
            penerima: ValidatorForm.rapikan(mentah.penerima),
            telepon: ValidatorForm.normalisasiTelepon(mentah.telepon),
            kodePos: mentah.kodePos.trim(),
            provinsi: ValidatorForm.rapikan(mentah.provinsi),
            kota: ValidatorForm.rapikan(mentah.kota),
            kecamatan: ValidatorForm.rapikan(mentah.kecamatan),
            lengkap: mentah.lengkap.replace(/[ \t]+/g, ' ').trim(),
        };
        return { bersih, galat };
    }
}

/* ===== KELAS EDITOR FOTO ===== */
/* Modal untuk menggeser dan zoom foto (mouse: seret + scroll, sentuh: seret + cubit). */
class EditorFoto {
    constructor() {
        this.modal = document.getElementById('editorFoto');
        this.panggung = document.getElementById('panggungFoto');
        this.gambarEl = document.getElementById('gambarFoto');
        this.zoomInput = document.getElementById('zoomFoto');
        this.nilaiZoom = document.getElementById('nilaiZoom');
        this.ukuranKeluaran = 420;
        this.kualitas = 0.88;
        this.zoomMaks = 3;
        this.gambar = null;
        this.selesai = null;
        this.fokusSebelumnya = null;
        this.saatUbahUkuran = () => this.sesuaikan();
        this.setelUlang();
        this.pasangPeristiwa();
    }

    /* ===== FUNGSI: MENGEMBALIKAN ZOOM DAN POSISI KE AWAL ===== */
    setelUlang() {
        this.zoom = 1;
        this.offsetX = 0;
        this.offsetY = 0;
        this.skalaDasar = 1;
        this.pointer = new Map();
        this.jarakCubitAwal = 0;
        this.zoomCubitAwal = 1;
        this.awalGeser = null;
    }

    /* ===== FUNGSI: MEMBUKA EDITOR; MENGEMBALIKAN Promise<dataURL | null> ===== */
    async buka(file) {
        if (!file || !TIPE_FOTO_BOLEH.includes(file.type)) throw new Error('Foto harus berformat PNG, JPG, atau WEBP.');
        if (file.size > UKURAN_FOTO_MAKS) throw new Error('Ukuran foto maksimal 5 MB.');

        const sumber = await this.bacaFile(file);
        const gambar = await this.muatGambar(sumber);

        return new Promise((selesai) => {
            this.selesai = selesai;
            this.gambar = gambar;
            this.setelUlang();
            this.gambarEl.src = sumber;
            this.fokusSebelumnya = document.activeElement;
            this.modal.hidden = false;
            document.body.style.overflow = 'hidden';
            window.addEventListener('resize', this.saatUbahUkuran);
            requestAnimationFrame(() => {
                this.sesuaikan();
                document.getElementById('tutupEditorFoto').focus();
            });
        });
    }

    /* ===== FUNGSI: MEMBACA FILE MENJADI DATA URL ===== */
    bacaFile(file) {
        return new Promise((selesai, gagal) => {
            const pembaca = new FileReader();
            pembaca.onload = () => selesai(pembaca.result);
            pembaca.onerror = () => gagal(new Error('File tidak dapat dibaca.'));
            pembaca.readAsDataURL(file);
        });
    }

    /* ===== FUNGSI: MEMUAT DATA URL MENJADI ELEMEN GAMBAR ===== */
    muatGambar(sumber) {
        return new Promise((selesai, gagal) => {
            const gambar = new Image();
            gambar.onload = () => selesai(gambar);
            gambar.onerror = () => gagal(new Error('Gambar tidak dapat dibaca.'));
            gambar.src = sumber;
        });
    }

    /* ===== FUNGSI: MENUTUP EDITOR DAN MENGIRIM HASIL (null = dibatalkan) ===== */
    tutup(hasil) {
        if (!this.selesai) return;
        this.modal.hidden = true;
        document.body.style.overflow = '';
        window.removeEventListener('resize', this.saatUbahUkuran);
        this.fokusSebelumnya?.focus?.();
        const selesai = this.selesai;
        this.selesai = null;
        this.gambar = null;
        selesai(hasil);
    }

    /* ===== FUNGSI: MENYESUAIKAN FOTO AGAR MENUTUPI PANGGUNG ===== */
    sesuaikan() {
        if (!this.gambar) return;
        const kotak = this.panggung.getBoundingClientRect();
        if (kotak.width === 0) return;
        this.skalaDasar = Math.max(kotak.width / this.gambar.width, kotak.height / this.gambar.height);
        this.render();
    }

    /* ===== FUNGSI: MEMBATASI GESERAN AGAR TIDAK ADA RUANG KOSONG DI PANGGUNG ===== */
    batasi() {
        const kotak = this.panggung.getBoundingClientRect();
        const lebar = this.gambar.width * this.skalaDasar * this.zoom;
        const tinggi = this.gambar.height * this.skalaDasar * this.zoom;
        const maksX = Math.max(0, (lebar - kotak.width) / 2);
        const maksY = Math.max(0, (tinggi - kotak.height) / 2);
        this.offsetX = Math.max(-maksX, Math.min(maksX, this.offsetX));
        this.offsetY = Math.max(-maksY, Math.min(maksY, this.offsetY));
    }

    /* ===== FUNGSI: MENGGAMBAR ULANG POSISI DAN UKURAN FOTO ===== */
    render() {
        if (!this.gambar) return;
        this.batasi();
        const lebar = this.gambar.width * this.skalaDasar * this.zoom;
        const tinggi = this.gambar.height * this.skalaDasar * this.zoom;
        this.gambarEl.style.width = `${lebar}px`;
        this.gambarEl.style.height = `${tinggi}px`;
        this.gambarEl.style.transform = `translate(calc(-50% + ${this.offsetX}px), calc(-50% + ${this.offsetY}px))`;
        this.zoomInput.value = String(this.zoom);
        this.nilaiZoom.textContent = `${this.zoom.toFixed(2)}×`;
    }

    /* ===== FUNGSI: JARAK ANTARA DUA JARI (UNTUK CUBIT ZOOM) ===== */
    jarakDuaJari() {
        const titik = [...this.pointer.values()];
        if (titik.length < 2) return 0;
        return Math.hypot(titik[0].x - titik[1].x, titik[0].y - titik[1].y);
    }

    /* ===== FUNGSI: MEMPERBARUI ZOOM / POSISI DARI POSISI POINTER ===== */
    perbaruiDariPointer() {
        const titik = [...this.pointer.values()];
        if (titik.length >= 2 && this.jarakCubitAwal > 0) {
            const rasio = this.jarakDuaJari() / this.jarakCubitAwal;
            this.zoom = Math.max(1, Math.min(this.zoomMaks, this.zoomCubitAwal * rasio));
            this.render();
        } else if (titik.length === 1 && this.awalGeser) {
            this.offsetX = this.awalGeser.offsetX + titik[0].x - this.awalGeser.x;
            this.offsetY = this.awalGeser.offsetY + titik[0].y - this.awalGeser.y;
            this.render();
        }
    }

    /* ===== FUNGSI: MELEPAS POINTER (JARI / KURSOR DIANGKAT) ===== */
    lepas(peristiwa) {
        this.pointer.delete(peristiwa.pointerId);
        if (this.pointer.size === 1) {
            const sisa = [...this.pointer.values()][0];
            this.awalGeser = { x: sisa.x, y: sisa.y, offsetX: this.offsetX, offsetY: this.offsetY };
        } else {
            this.awalGeser = null;
            this.jarakCubitAwal = 0;
        }
    }

    /* ===== FUNGSI: MEMUTAR FOTO 90 DERAJAT TANPA MENGUBAH KUALITAS SUMBER ===== */
    async putar(arah) {
        if (!this.gambar) return;
        const sumber = this.gambar;
        const kanvas = document.createElement('canvas');
        kanvas.width = sumber.height;
        kanvas.height = sumber.width;
        const konteks = kanvas.getContext('2d');
        konteks.translate(kanvas.width / 2, kanvas.height / 2);
        konteks.rotate((arah * Math.PI) / 2);
        konteks.drawImage(sumber, -sumber.width / 2, -sumber.height / 2);
        try {
            const hasil = await this.muatGambar(kanvas.toDataURL('image/png'));
            this.gambar = hasil;
            this.gambarEl.src = hasil.src;
            this.offsetX = 0;
            this.offsetY = 0;
            this.zoom = 1;
            this.sesuaikan();
            this.render();
        } catch {
            /* Jika browser gagal membuat hasil putaran, biarkan gambar asli tetap dipakai. */
        }
    }

    /* ===== FUNGSI: MEMOTONG FOTO SESUAI PANGGUNG LALU MENGEMBALIKAN DATA URL JPEG ===== */
    terapkan() {
        if (!this.gambar) return;
        const ukuran = this.ukuranKeluaran;
        const kanvas = document.createElement('canvas');
        kanvas.width = ukuran;
        kanvas.height = ukuran;
        const konteks = kanvas.getContext('2d', { alpha: false });
        konteks.fillStyle = '#FFFFFF';
        konteks.fillRect(0, 0, ukuran, ukuran);

        const kotak = this.panggung.getBoundingClientRect();
        const skala = this.skalaDasar * this.zoom;
        const ukuranPotong = kotak.width / skala;
        const awalX = (this.gambar.width - ukuranPotong) / 2 - this.offsetX / skala;
        const awalY = (this.gambar.height - ukuranPotong) / 2 - this.offsetY / skala;
        const sumberX = Math.max(0, Math.min(this.gambar.width - ukuranPotong, awalX));
        const sumberY = Math.max(0, Math.min(this.gambar.height - ukuranPotong, awalY));

        konteks.imageSmoothingEnabled = true;
        konteks.imageSmoothingQuality = 'high';
        konteks.drawImage(this.gambar, sumberX, sumberY, ukuranPotong, ukuranPotong, 0, 0, ukuran, ukuran);
        this.tutup(kanvas.toDataURL('image/jpeg', this.kualitas));
    }

    /* ===== FUNGSI: MEMASANG SEMUA PERISTIWA EDITOR (SEKALI SAAT KELAS DIBUAT) ===== */
    pasangPeristiwa() {
        this.panggung.addEventListener('pointerdown', (peristiwa) => {
            if (!this.gambar) return;
            this.panggung.setPointerCapture(peristiwa.pointerId);
            this.pointer.set(peristiwa.pointerId, { x: peristiwa.clientX, y: peristiwa.clientY });
            if (this.pointer.size === 1) {
                this.awalGeser = { x: peristiwa.clientX, y: peristiwa.clientY, offsetX: this.offsetX, offsetY: this.offsetY };
            } else if (this.pointer.size === 2) {
                this.jarakCubitAwal = this.jarakDuaJari();
                this.zoomCubitAwal = this.zoom;
                this.awalGeser = null;
            }
        });

        this.panggung.addEventListener('pointermove', (peristiwa) => {
            if (!this.pointer.has(peristiwa.pointerId)) return;
            this.pointer.set(peristiwa.pointerId, { x: peristiwa.clientX, y: peristiwa.clientY });
            this.perbaruiDariPointer();
        });

        this.panggung.addEventListener('pointerup', (peristiwa) => this.lepas(peristiwa));
        this.panggung.addEventListener('pointercancel', (peristiwa) => this.lepas(peristiwa));

        this.panggung.addEventListener(
            'wheel',
            (peristiwa) => {
                if (!this.gambar) return;
                peristiwa.preventDefault();
                const faktor = peristiwa.deltaY < 0 ? 1.08 : 0.93;
                this.zoom = Math.max(1, Math.min(this.zoomMaks, this.zoom * faktor));
                this.render();
            },
            { passive: false },
        );

        this.zoomInput.addEventListener('input', () => {
            this.zoom = Number(this.zoomInput.value);
            this.render();
        });

        document.getElementById('resetEditorFoto').addEventListener('click', () => {
            this.zoom = 1;
            this.offsetX = 0;
            this.offsetY = 0;
            this.render();
        });
        document.getElementById('putarKiriFoto')?.addEventListener('click', () => this.putar(-1));
        document.getElementById('putarKananFoto')?.addEventListener('click', () => this.putar(1));
        document.getElementById('batalEditorFoto').addEventListener('click', () => this.tutup(null));
        document.getElementById('tutupEditorFoto').addEventListener('click', () => this.tutup(null));
        document.getElementById('pakaiFoto').addEventListener('click', () => this.terapkan());

        /* Escape menutup editor; Tab dikunci di dalam editor */
        this.modal.addEventListener('keydown', (peristiwa) => {
            if (peristiwa.key === 'Escape') {
                this.tutup(null);
                return;
            }
            if (peristiwa.key !== 'Tab') return;
            const bisaFokus = [...this.modal.querySelectorAll('button, input')].filter((el) => !el.disabled);
            const pertama = bisaFokus[0];
            const terakhir = bisaFokus[bisaFokus.length - 1];
            if (peristiwa.shiftKey && document.activeElement === pertama) {
                peristiwa.preventDefault();
                terakhir.focus();
            } else if (!peristiwa.shiftKey && document.activeElement === terakhir) {
                peristiwa.preventDefault();
                pertama.focus();
            }
        });
    }
}

/* ===== KELAS HALAMAN PROFIL ===== */
class HalamanProfil {
    constructor() {
        this.penyimpanProfil = new PenyimpanLokal(KUNCI_PROFIL, PROFIL_BAWAAN);
        this.penyimpanAlamat = new PenyimpanLokal(KUNCI_ALAMAT, ALAMAT_BAWAAN);
        this.editorFoto = new EditorFoto();

        this.tersimpan = this.muatProfil();
        this.draf = { ...this.tersimpan };
        this.alamat = this.muatAlamat();

        this.daftarTab = [...document.querySelectorAll('[data-tab]')];
        this.kunciTab = this.daftarTab.map((tombol) => tombol.dataset.tab);
        this.tabAktif = 'profil';
        this.tujuanTertunda = null;
        this.idSedangDiedit = null;
        this.penghitungToast = null;

        this.kolomNama = document.getElementById('namaLengkap');
        this.kolomEmail = document.getElementById('emailProfil');
        this.inputFoto = document.getElementById('inputFoto');
        this.tombolHapusFoto = document.getElementById('hapusFoto');
        this.avatar = document.getElementById('avatarBulat');
        this.bar = document.getElementById('barPerubahan');
        this.toast = document.getElementById('toastProfil');
        this.formAlamat = document.getElementById('formAlamat');
        this.daftarAlamat = document.getElementById('daftarAlamat');
    }

    /* ===== FUNGSI: MEMBACA PROFIL TERSIMPAN DAN MEMBERSIHKAN TIPE DATANYA ===== */
    muatProfil() {
        const data = this.penyimpanProfil.baca();
        const foto = typeof data.foto === 'string' && data.foto.startsWith('data:image/') ? data.foto : null;
        return {
            nama: typeof data.nama === 'string' ? data.nama : PROFIL_BAWAAN.nama,
            email: typeof data.email === 'string' ? data.email : PROFIL_BAWAAN.email,
            foto,
        };
    }

    /* ===== FUNGSI: MEMBACA ALAMAT TERSIMPAN DAN MEMBUANG DATA RUSAK ===== */
    muatAlamat() {
        const data = this.penyimpanAlamat.baca();
        const kunciTeks = ['label', 'penerima', 'telepon', 'kodePos', 'provinsi', 'kota', 'kecamatan', 'lengkap'];
        const daftar = (Array.isArray(data.daftar) ? data.daftar : []).filter(
            (a) => a && typeof a.id === 'string' && kunciTeks.every((kunci) => typeof a[kunci] === 'string'),
        );
        const utamaAda = daftar.some((a) => a.id === data.utamaId);
        return { daftar, utamaId: utamaAda ? data.utamaId : (daftar[0]?.id ?? null) };
    }

    /* ===== FUNGSI: MENJALANKAN HALAMAN ===== */
    mulai() {
        this.isiFormProfil();
        this.tampilkanFoto();
        this.pasangTab();
        this.pasangFormProfil();
        this.pasangBar();
        this.pasangAlamat();
        this.gambarDaftarAlamat();

        const awal = location.hash.slice(1);
        if (this.kunciTab.includes(awal)) this.pindahTab(awal);

        window.addEventListener('beforeunload', (peristiwa) => {
            if (!this.kotor()) return;
            peristiwa.preventDefault();
            peristiwa.returnValue = '';
        });
    }

    /* ===== FUNGSI: MENAMPILKAN PEMBERITAHUAN SINGKAT ===== */
    tampilkanToast(pesan, galat = false) {
        this.toast.textContent = pesan;
        this.toast.classList.toggle('is-galat', galat);
        this.toast.hidden = false;
        window.clearTimeout(this.penghitungToast);
        this.penghitungToast = window.setTimeout(() => {
            this.toast.hidden = true;
        }, 3200);
    }

    /* ===== FUNGSI: MENAMPILKAN / MENYEMBUNYIKAN PESAN GALAT PADA SATU KOLOM ===== */
    aturGalat(idKolom, idGalat, pesan) {
        const kolom = document.getElementById(idKolom);
        const elemenGalat = document.getElementById(idGalat);
        elemenGalat.textContent = pesan || '';
        elemenGalat.hidden = !pesan;
        kolom.classList.toggle('is-invalid', Boolean(pesan));
        kolom.setAttribute('aria-invalid', pesan ? 'true' : 'false');
    }

    /* ======================== TAB ======================== */

    /* ===== FUNGSI: MEMASANG KLIK DAN PANAH KEYBOARD PADA TAB ===== */
    pasangTab() {
        this.daftarTab.forEach((tombol, indeks) => {
            tombol.addEventListener('click', () => this.mintaPindahTab(tombol.dataset.tab));
            tombol.addEventListener('keydown', (peristiwa) => {
                const jumlah = this.daftarTab.length;
                let tujuan = null;
                if (peristiwa.key === 'ArrowRight') tujuan = (indeks + 1) % jumlah;
                else if (peristiwa.key === 'ArrowLeft') tujuan = (indeks - 1 + jumlah) % jumlah;
                else if (peristiwa.key === 'Home') tujuan = 0;
                else if (peristiwa.key === 'End') tujuan = jumlah - 1;
                if (tujuan === null) return;
                peristiwa.preventDefault();
                this.daftarTab[tujuan].focus();
                this.mintaPindahTab(this.daftarTab[tujuan].dataset.tab);
            });
        });
    }

    /* ===== FUNGSI: PINDAH TAB; DITAHAN JIKA PROFIL MASIH ADA PERUBAHAN BELUM DISIMPAN ===== */
    mintaPindahTab(kunci) {
        if (kunci === this.tabAktif) return;
        if (this.tabAktif === 'profil' && this.kotor()) {
            this.tujuanTertunda = kunci;
            this.bar.hidden = false;
            this.bar.classList.remove('is-goyang');
            void this.bar.offsetWidth; /* mulai ulang animasi */
            this.bar.classList.add('is-goyang');
            return;
        }
        this.pindahTab(kunci);
    }

    /* ===== FUNGSI: MENAMPILKAN PANEL TAB YANG DIPILIH ===== */
    pindahTab(kunci) {
        this.tabAktif = kunci;
        this.daftarTab.forEach((tombol) => {
            const aktif = tombol.dataset.tab === kunci;
            tombol.setAttribute('aria-selected', String(aktif));
            tombol.tabIndex = aktif ? 0 : -1;
            document.getElementById(`panel-${tombol.dataset.tab}`).hidden = !aktif;
        });
        history.replaceState(null, '', `#${kunci}`);
        this.perbaruiBar();
    }

    /* ======================== PROFIL ======================== */

    /* ===== FUNGSI: APAKAH ADA PERUBAHAN YANG BELUM DISIMPAN ===== */
    kotor() {
        return (
            this.draf.nama !== this.tersimpan.nama ||
            this.draf.email !== this.tersimpan.email ||
            this.draf.foto !== this.tersimpan.foto
        );
    }

    /* ===== FUNGSI: MENGISI KOLOM FORM DARI DRAF ===== */
    isiFormProfil() {
        document.getElementById('namaLengkap').value = this.draf.nama;
        document.getElementById('emailProfil').value = this.draf.email;
        this.aturGalat('namaLengkap', 'galatNama', '');
        this.aturGalat('emailProfil', 'galatEmail', '');
    }

    /* ===== FUNGSI: MENAMPILKAN FOTO (ATAU IKON BAWAAN) DI LINGKARAN ===== */
    tampilkanFoto() {
        this.avatar.replaceChildren();
        if (this.draf.foto) {
            const gambar = document.createElement('img');
            gambar.src = this.draf.foto;
            gambar.alt = 'Foto profil';
            this.avatar.append(gambar);
        } else {
            this.avatar.innerHTML =
                '<svg viewBox="0 0 48 48" fill="currentColor" aria-hidden="true">' +
                '<circle cx="24" cy="17" r="9"></circle>' +
                '<path d="M7 43c1.9-9.2 8.2-14 17-14s15.1 4.8 17 14H7Z"></path></svg>';
        }
        document.getElementById('hapusFoto').hidden = !this.draf.foto;
    }

    /* ===== FUNGSI: MENAMPILKAN BAR HANYA SAAT DI TAB PROFIL DAN ADA PERUBAHAN ===== */
    perbaruiBar() {
        this.bar.hidden = !(this.tabAktif === 'profil' && this.kotor());
    }

    /* ===== FUNGSI: MEMASANG PERISTIWA FORM PROFIL DAN FOTO ===== */
    pasangFormProfil() {
        this.kolomNama.addEventListener('input', () => {
            this.draf.nama = this.kolomNama.value;
            this.aturGalat('namaLengkap', 'galatNama', '');
            this.perbaruiBar();
        });
        this.kolomEmail.addEventListener('input', () => {
            this.draf.email = this.kolomEmail.value;
            this.aturGalat('emailProfil', 'galatEmail', '');
            this.perbaruiBar();
        });

        this.inputFoto.addEventListener('change', async () => {
            const file = this.inputFoto.files[0];
            if (!file) return;
            try {
                const hasil = await this.editorFoto.buka(file);
                if (hasil) {
                    this.draf.foto = hasil;
                    this.tampilkanFoto();
                    this.perbaruiBar();
                }
            } catch (galat) {
                this.tampilkanToast(galat.message || 'Foto tidak dapat diproses.', true);
            }
            this.inputFoto.value = ''; /* agar file yang sama bisa dipilih lagi */
        });

        this.tombolHapusFoto.addEventListener('click', () => {
            this.draf.foto = null;
            this.tampilkanFoto();
            this.perbaruiBar();
        });

        document.getElementById('formProfil').addEventListener('submit', (peristiwa) => {
            peristiwa.preventDefault();
            this.simpanProfil();
        });
    }

    /* ===== FUNGSI: MEMASANG TOMBOL RESET / SIMPAN PADA BAR PERUBAHAN ===== */
    pasangBar() {
        document.getElementById('resetProfil').addEventListener('click', () => {
            this.draf = { ...this.tersimpan };
            this.isiFormProfil();
            this.tampilkanFoto();
            this.perbaruiBar();
            this.lanjutkanTujuan();
        });

        document.getElementById('simpanDariBar').addEventListener('click', () => {
            if (this.simpanProfil()) this.lanjutkanTujuan();
        });
    }

    /* ===== FUNGSI: PINDAH KE TAB YANG TADI DITAHAN (JIKA ADA) ===== */
    lanjutkanTujuan() {
        const tujuan = this.tujuanTertunda;
        this.tujuanTertunda = null;
        if (tujuan) this.pindahTab(tujuan);
    }

    /* ===== FUNGSI: MEMERIKSA DAN MENYIMPAN PROFIL; MENGEMBALIKAN true JIKA BERHASIL ===== */
    simpanProfil() {
        const galatNama = ValidatorForm.nama(this.draf.nama, 'Nama lengkap');
        const galatEmail = ValidatorForm.email(this.draf.email);
        this.aturGalat('namaLengkap', 'galatNama', galatNama);
        this.aturGalat('emailProfil', 'galatEmail', galatEmail);

        if (galatNama || galatEmail) {
            (galatNama ? this.kolomNama : this.kolomEmail).focus();
            return false;
        }

        const bersih = {
            nama: ValidatorForm.rapikan(this.draf.nama),
            email: this.draf.email.trim(),
            foto: this.draf.foto,
        };
        if (!this.penyimpanProfil.simpan(bersih)) {
            this.tampilkanToast('Gagal menyimpan: penyimpanan browser penuh atau diblokir.', true);
            return false;
        }

        this.tersimpan = bersih;
        this.draf = { ...bersih };
        this.isiFormProfil();
        this.perbaruiBar();
        this.tampilkanToast('Profil berhasil diperbarui.');
        return true;
    }

    /* ======================== ALAMAT ======================== */

    /* ===== FUNGSI: MEMASANG PERISTIWA PANEL ALAMAT ===== */
    pasangAlamat() {
        document.getElementById('alamatBaru').addEventListener('click', () => this.bukaFormAlamat());
        document.getElementById('batalAlamat').addEventListener('click', () => this.tutupFormAlamat());

        this.formAlamat.addEventListener('submit', (peristiwa) => {
            peristiwa.preventDefault();
            this.simpanAlamat();
        });

        /* Hapus pesan galat saat kolom diketik ulang */
        Object.entries(KOLOM_ALAMAT).forEach(([, [idKolom, idGalat]]) => {
            document.getElementById(idKolom).addEventListener('input', () => this.aturGalat(idKolom, idGalat, ''));
        });

        /* Kode pos: buang non-angka dulu, baru potong ke 5 angka (maxlength akan memotong sebelum dibersihkan) */
        const kolomKodePos = document.getElementById('alamatKodePos');
        kolomKodePos.addEventListener('input', () => {
            kolomKodePos.value = kolomKodePos.value.replace(/\D/g, '').slice(0, 5);
        });

        /* Telepon: rapikan ke 62xx saat kolom ditinggalkan, sama seperti form register */
        const kolomTelepon = document.getElementById('alamatTelepon');
        kolomTelepon.addEventListener('blur', () => {
            if (kolomTelepon.value.trim()) kolomTelepon.value = ValidatorForm.normalisasiTelepon(kolomTelepon.value);
        });
    }

    /* ===== FUNGSI: MEMBUAT KARTU ALAMAT (MEMAKAI textContent, BUKAN innerHTML, AGAR AMAN DARI XSS) ===== */
    buatKartuAlamat(alamat) {
        const utama = alamat.id === this.alamat.utamaId;
        const kartu = document.createElement('article');
        kartu.className = `kartu-alamat${utama ? ' is-utama' : ''}`;

        const judul = document.createElement('div');
        judul.className = 'kartu-alamat-judul';
        const nama = document.createElement('strong');
        nama.textContent = alamat.label || 'Alamat';
        judul.append(nama);
        if (utama) {
            const lencana = document.createElement('span');
            lencana.className = 'lencana-utama';
            lencana.textContent = 'UTAMA';
            judul.append(lencana);
        }

        const penerima = document.createElement('p');
        penerima.className = 'kartu-alamat-penerima';
        penerima.textContent = `${alamat.penerima} · ${alamat.telepon}`;

        const lengkap = document.createElement('p');
        lengkap.textContent = alamat.lengkap;

        const wilayah = document.createElement('p');
        wilayah.textContent = [alamat.kecamatan, alamat.kota, alamat.provinsi, alamat.kodePos].filter(Boolean).join(', ');

        const aksi = document.createElement('div');
        aksi.className = 'kartu-alamat-aksi';
        const buatTombol = (teks, kelasTambahan, saatKlik) => {
            const tombol = document.createElement('button');
            tombol.type = 'button';
            tombol.className = `button button-secondary button-small ${kelasTambahan}`.trim();
            tombol.textContent = teks;
            tombol.addEventListener('click', saatKlik);
            return tombol;
        };
        if (!utama) aksi.append(buatTombol('Jadikan utama', '', () => this.jadikanUtama(alamat.id)));
        aksi.append(buatTombol('Edit', '', () => this.bukaFormAlamat(alamat)));
        aksi.append(buatTombol('Hapus', 'button-bahaya', () => this.hapusAlamat(alamat.id)));

        kartu.append(judul, penerima, lengkap, wilayah, aksi);
        return kartu;
    }

    /* ===== FUNGSI: MENGGAMBAR ULANG DAFTAR ALAMAT ===== */
    gambarDaftarAlamat() {
        this.daftarAlamat.replaceChildren();
        if (!this.alamat.daftar.length) {
            const kosong = document.createElement('div');
            kosong.className = 'alamat-kosong';
            kosong.textContent = 'Belum ada alamat tersimpan.';
            this.daftarAlamat.append(kosong);
            return;
        }
        this.alamat.daftar.forEach((alamat) => this.daftarAlamat.append(this.buatKartuAlamat(alamat)));
    }

    /* ===== FUNGSI: MENYIMPAN KEADAAN ALAMAT BARU; GAGAL = KEADAAN LAMA TIDAK DIUBAH ===== */
    terapkanAlamat(keadaanBaru) {
        if (!this.penyimpanAlamat.simpan(keadaanBaru)) {
            this.tampilkanToast('Gagal menyimpan: penyimpanan browser penuh atau diblokir.', true);
            return false;
        }
        this.alamat = keadaanBaru;
        this.gambarDaftarAlamat();
        return true;
    }

    /* ===== FUNGSI: MEMBUKA FORM ALAMAT (BARU, ATAU EDIT JIKA ADA DATA) ===== */
    bukaFormAlamat(alamat = null) {
        this.idSedangDiedit = alamat ? alamat.id : null;
        document.getElementById('judulFormAlamat').textContent = alamat ? 'Edit alamat' : 'Tambah alamat';

        const nilai = {
            label: alamat && alamat.label !== 'Alamat' ? alamat.label : '',
            penerima: alamat?.penerima ?? '',
            telepon: alamat?.telepon ?? '',
            kodePos: alamat?.kodePos ?? '',
            provinsi: alamat?.provinsi ?? '',
            kota: alamat?.kota ?? '',
            kecamatan: alamat?.kecamatan ?? '',
            lengkap: alamat?.lengkap ?? '',
        };
        Object.entries(KOLOM_ALAMAT).forEach(([kunci, [idKolom, idGalat]]) => {
            document.getElementById(idKolom).value = nilai[kunci];
            this.aturGalat(idKolom, idGalat, '');
        });

        this.formAlamat.hidden = false;
        this.formAlamat.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        document.getElementById('alamatPenerima').focus({ preventScroll: true });
    }

    /* ===== FUNGSI: MENUTUP FORM ALAMAT ===== */
    tutupFormAlamat() {
        this.idSedangDiedit = null;
        this.formAlamat.hidden = true;
        this.formAlamat.reset();
        Object.values(KOLOM_ALAMAT).forEach(([idKolom, idGalat]) => this.aturGalat(idKolom, idGalat, ''));
    }

    /* ===== FUNGSI: MEMERIKSA FORM ALAMAT LALU MENYIMPANNYA ===== */
    simpanAlamat() {
        const mentah = {};
        Object.entries(KOLOM_ALAMAT).forEach(([kunci, [idKolom]]) => {
            mentah[kunci] = document.getElementById(idKolom).value;
        });

        const { bersih, galat } = ValidatorForm.alamat(mentah);
        Object.entries(KOLOM_ALAMAT).forEach(([kunci, [idKolom, idGalat]]) => {
            this.aturGalat(idKolom, idGalat, galat[kunci] || '');
        });

        const kunciGalat = Object.keys(galat);
        if (kunciGalat.length) {
            document.getElementById(KOLOM_ALAMAT[kunciGalat[0]][0]).focus();
            return;
        }

        const daftar = [...this.alamat.daftar];
        let utamaId = this.alamat.utamaId;
        if (this.idSedangDiedit) {
            const indeks = daftar.findIndex((a) => a.id === this.idSedangDiedit);
            if (indeks >= 0) daftar[indeks] = { ...bersih, id: this.idSedangDiedit };
        } else {
            const idBaru = globalThis.crypto?.randomUUID?.() ?? `a${Date.now()}`;
            daftar.push({ ...bersih, id: idBaru });
            if (!utamaId) utamaId = idBaru;
        }

        if (!this.terapkanAlamat({ daftar, utamaId })) return;
        this.tutupFormAlamat();
        this.tampilkanToast('Alamat berhasil disimpan.');
    }

    /* ===== FUNGSI: MENJADIKAN SATU ALAMAT SEBAGAI ALAMAT UTAMA ===== */
    jadikanUtama(id) {
        this.terapkanAlamat({ daftar: [...this.alamat.daftar], utamaId: id });
    }

    /* ===== FUNGSI: MENGHAPUS ALAMAT SETELAH KONFIRMASI ===== */
    hapusAlamat(id) {
        if (!window.confirm('Hapus alamat ini dari daftar alamat tersimpan?')) return;
        const daftar = this.alamat.daftar.filter((a) => a.id !== id);
        const utamaId = this.alamat.utamaId === id ? (daftar[0]?.id ?? null) : this.alamat.utamaId;
        if (!this.terapkanAlamat({ daftar, utamaId })) return;
        if (this.idSedangDiedit === id) this.tutupFormAlamat();
        this.tampilkanToast('Alamat dihapus.');
    }
}

/* ===== INISIALISASI ===== */
document.addEventListener('DOMContentLoaded', () => {
    if (document.getElementById('halamanProfil')) new HalamanProfil().mulai();
});
