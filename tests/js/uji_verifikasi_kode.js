const { JSDOM } = require('jsdom');
const fs = require('fs'); const path = require('path');
const kode = fs.readFileSync(path.join(__dirname, '../../app/static/js/verifikasi_kode.js'), 'utf8');
let gagal = 0; const cek = (n, ok, i = '') => { console.log((ok ? 'OK   ' : 'GAGAL') + ' ' + n + (ok ? '' : ' -> ' + i)); if (!ok) gagal++; };
const html = sisa => `<form id="formKode"><input id="kode" data-digit="6" maxlength="6"><button id="tombolLanjut" disabled></button></form>
<form id="formUlang" data-sisa="${sisa}"><span id="teksUlang"></span><button id="tombolUlang" hidden></button></form>`;
const tidur = ms => new Promise(r => setTimeout(r, ms));
(async () => {
  const dom = new JSDOM(html(2), { runScripts: 'outside-only' }); const w = dom.window; w.eval(kode);
  const d = w.document, input = d.getElementById('kode'), lanjut = d.getElementById('tombolLanjut');
  cek('awal: Lanjutkan nonaktif', lanjut.disabled === true);
  input.value = '12ab3'; input.dispatchEvent(new w.Event('input'));
  cek('huruf dibuang, 3 digit belum cukup', input.value === '123' && lanjut.disabled === true, input.value);
  input.value = '1234567'; input.dispatchEvent(new w.Event('input'));
  cek('maksimal 6 digit, tombol aktif', input.value === '123456' && lanjut.disabled === false, input.value);
  input.value = '12345'; input.dispatchEvent(new w.Event('input'));
  cek('kurang dari 6 -> nonaktif lagi', lanjut.disabled === true);
  cek('hitung mundur tampil "0:02", tombol kirim ulang tersembunyi', d.getElementById('teksUlang').textContent === 'Kirim ulang dalam 0:02' && d.getElementById('tombolUlang').hidden === true, d.getElementById('teksUlang').textContent);
  await tidur(2300);
  cek('setelah habis: teks kosong, tombol Kirim ulang muncul', d.getElementById('teksUlang').textContent === '' && d.getElementById('tombolUlang').hidden === false, d.getElementById('teksUlang').textContent);
  const w2 = new JSDOM(html(0), { runScripts: 'outside-only' }).window; w2.eval(kode);
  cek('sisa 0: langsung bisa kirim ulang', w2.document.getElementById('tombolUlang').hidden === false);
  console.log(gagal ? `\n${gagal} GAGAL` : '\nSEMUA OK'); process.exit(gagal ? 1 : 0);
})();
