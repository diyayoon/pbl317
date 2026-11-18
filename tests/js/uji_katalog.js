const { JSDOM } = require('jsdom');
const fs = require('fs');
const fx = JSON.parse(fs.readFileSync('/tmp/albis_fixtures.json', 'utf8'));
const kode = fs.readFileSync(require('path').join(__dirname, '../../app/static/js/catalog.js'), 'utf8');
const tidur = ms => new Promise(r => setTimeout(r, ms));
let gagal = 0;
const cek = (nama, ok, info = '') => { console.log((ok ? 'OK   ' : 'GAGAL') + ' ' + nama + (ok ? '' : ' -> ' + info)); if (!ok) gagal++; };

async function buat({ fetchGagal = false } = {}) {
  const dom = new JSDOM(fx['/katalog'], { runScripts: 'outside-only', url: 'http://localhost/katalog' });
  const w = dom.window;
  w.scrollTo = () => {}; w.HTMLElement.prototype.scrollIntoView = () => {};
  w.fetch = async (url) => {
    if (fetchGagal) throw new Error('offline');
    const kunci = url.replace('http://localhost', '');
    return fx[kunci] !== undefined ? { ok: true, text: async () => fx[kunci] } : { ok: false, status: 404, text: async () => '' };
  };
  w.eval(kode); w.eval('window.F = new FilterKatalog(); window.F.pasang();');
  return w;
}
const terlihat = w => [...w.document.querySelectorAll('#catalogGrid [data-product]')].filter(k => !k.hidden).map(k => k.dataset.name);
const jumlah = w => Number(w.document.getElementById('productCount').textContent);
const ketik = async (w, teks) => { const i = w.document.getElementById('catalogSearch'); i.value = teks; i.dispatchEvent(new w.Event('input')); await tidur(450); };
const set = (w, id, v) => { const e = w.document.getElementById(id); e.value = v; e.dispatchEvent(new w.Event('change')); };

(async () => {
  let w = await buat();
  cek('awal: 10 produk, 8 tampil (paginasi)', jumlah(w) === 10 && terlihat(w).length === 8, `${jumlah(w)}/${terlihat(w).length}`);

  await ketik(w, 'kursi');
  cek('cari "kursi" -> 3 hasil dari server', jumlah(w) === 3, jumlah(w));
  cek('url ikut ?q=kursi', w.location.search === '?q=kursi', w.location.search);

  await ketik(w, 'KURSI');
  cek('huruf besar sama hasilnya', jumlah(w) === 3, jumlah(w));

  await ketik(w, 'meja vintage');
  const t = terlihat(w);
  cek('multi-kata: yang cocok dua kata paling atas', t[0] === 'meja marmer vintage' && t.includes('kursi kayu vintage'), t.join('|'));

  await ketik(w, 'kayu');
  const awal = jumlah(w);
  set(w, 'catalogCategory', 'jam');
  cek('pencarian + filter kategori', jumlah(w) === 1 && terlihat(w)[0] === 'jam dinding kayu', terlihat(w).join('|'));
  set(w, 'catalogCategory', '');
  cek('kategori dilepas -> kembali', jumlah(w) === awal, jumlah(w));

  set(w, 'catalogPriceMin', '500000');
  cek('pencarian + harga min', terlihat(w).every(n => ['lemari hias', 'kursi goyang kayu'].includes(n)) && jumlah(w) === 2, terlihat(w).join('|'));
  set(w, 'catalogPriceMin', ''); 
  set(w, 'catalogSort', 'price-low');
  const urut = [...w.document.querySelectorAll('#catalogGrid [data-product]')].filter(k => !k.hidden).map(k => Number(k.dataset.price));
  cek('pencarian + sort harga terendah', urut.every((h, i) => i === 0 || urut[i - 1] <= h), urut.join(','));
  set(w, 'catalogSort', 'popular');
  const rel = terlihat(w);
  const rank = [...w.document.querySelectorAll('#catalogGrid [data-product]')].filter(k => !k.hidden).map(k => Number(k.dataset.rank));
  cek('sort populer saat mencari = urutan relevansi server', rank.length === jumlah(w) && rank.every((r, i) => i === 0 || rank[i - 1] < r), rank.join(','));

  await ketik(w, 'tidakada');
  cek('tanpa hasil: hitungan 0 dan pesan kosong tampil', jumlah(w) === 0 && w.document.getElementById('catalogEmpty').style.display === 'block');
  w.document.getElementById('catalogEmptyReset').click(); await tidur(450);
  cek('tombol "Hapus pencarian dan filter" memulihkan semua', jumlah(w) === 10 && w.document.getElementById('catalogSearch').value === '', jumlah(w));

  await ketik(w, '   ');
  cek('hanya spasi = tampil semua', jumlah(w) === 10, jumlah(w));

  const w2 = await buat({ fetchGagal: true });
  await ketik(w2, 'kursi');
  cek('cadangan bila server gagal: filter klien tetap jalan', jumlah(w2) === 3, jumlah(w2));
  console.log(gagal ? `\n${gagal} GAGAL` : '\nSEMUA OK');
  process.exit(gagal ? 1 : 0);
})();
