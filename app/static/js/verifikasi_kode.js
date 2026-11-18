'use strict';

/* Tombol Lanjutkan aktif setelah kode lengkap; hitung mundur kirim ulang (server tetap menegakkan batasnya). */
(() => {
    const input = document.getElementById('kode');
    const lanjut = document.getElementById('tombolLanjut');
    const formUlang = document.getElementById('formUlang');
    const teks = document.getElementById('teksUlang');
    const ulang = document.getElementById('tombolUlang');
    if (!input || !lanjut) return;

    const digit = Number(input.dataset.digit || 6);
    const periksa = () => {
        input.value = input.value.replace(/\D/g, '').slice(0, digit);
        lanjut.disabled = input.value.length !== digit;
    };
    input.addEventListener('input', periksa);
    periksa();

    let sisa = Number(formUlang?.dataset.sisa || 0);
    const format = detik => `${Math.floor(detik / 60)}:${String(detik % 60).padStart(2, '0')}`;
    const gambar = () => {
        if (!teks || !ulang) return;
        const aktif = sisa > 0;
        teks.textContent = aktif ? `Kirim ulang dalam ${format(sisa)}` : '';
        ulang.hidden = aktif;
    };
    gambar();
    if (sisa > 0) {
        const timer = window.setInterval(() => { sisa -= 1; gambar(); if (sisa <= 0) window.clearInterval(timer); }, 1000);
    }
})();
