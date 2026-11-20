# Wazuh integration — Albis Antique Application Audit

Aplikasi menghasilkan satu JSON object per baris di:

```text
/app/instance/logs/albis_audit.jsonl
```

File berada di volume persisten `instance_data` yang juga dipakai untuk upload aplikasi. Event yang sama tetap dicatat ke tabel PostgreSQL `audit_logs` untuk halaman Admin → Audit Log.

## 1. Migrasi database

Backup database terlebih dahulu, lalu jalankan migrasi terbaru menggunakan role migration/owner:

```bash
python -m flask --app run db upgrade
```

Versi skema terbaru menambahkan `event_id`, `event_category`, `event_action`, `outcome`, `severity`, `actor_role`, `request_id`, dan `context_data` ke `audit_logs`. Kolom lama tetap dipertahankan.

## 2. Temukan path Docker volume pada host

Di Docker host yang menjalankan Albis Antique. Wazuh Agent harus dipasang pada host yang dapat membaca named volume tersebut (dan terhubung ke Wazuh Manager). Menjalankan Manager di VM SOC yang berbeda tidak otomatis memberinya akses filesystem ke volume Docker host.

```bash
docker volume ls
# Ganti dengan nama volume yang muncul untuk stack Albis Antique:
docker volume inspect <NAMA_VOLUME_INSTANCE_DATA> --format '{{ .Mountpoint }}'
```

Tambahkan `/logs/albis_audit.jsonl` ke path mountpoint yang dikembalikan. Contoh:

```text
/var/lib/docker/volumes/albis_instance_data/_data/logs/albis_audit.jsonl
```

Pastikan file dapat dibaca oleh Wazuh Agent (umumnya Agent berjalan sebagai root). Jangan membuka file audit ke web server publik. Jika Docker host berada di Windows/Docker Desktop atau Agent hanya terpasang di VM SOC yang terpisah, jangan menyalin contoh path Linux ini mentah-mentah: gunakan path yang benar-benar terlihat dari host Agent atau siapkan forwarding log yang aman ke Agent/collector.

## 3. Konfigurasi Wazuh Agent

Merge isi `agent-localfile.conf` ke `/var/ossec/etc/ossec.conf` di Docker host. Ganti path placeholder dengan path aktual dari langkah sebelumnya. Jangan menimpa seluruh `ossec.conf`.

Restart agent:

```bash
sudo systemctl restart wazuh-agent
sudo systemctl status wazuh-agent --no-pager
```

## 4. Pasang custom rules pada Wazuh Manager

Salin atau merge isi `albis_antique_rules.xml` ke file custom rule manager, misalnya:

```text
/var/ossec/etc/rules/albis_antique_rules.xml
```

Jika memakai file terpisah, pastikan rule file terdaftar/terbaca oleh Wazuh Manager sesuai konfigurasi instalasi kalian. Jangan mengganti `local_rules.xml` yang sudah berisi rule milik tim. Rule ID 100500–100599 disediakan untuk Albis Antique; pastikan tidak bentrok dengan ID custom tim lain.

Validasi dan restart:

```bash
sudo /var/ossec/bin/wazuh-analysisd -t
sudo systemctl restart wazuh-manager
```

## 5. Uji penerimaan

Buat aktivitas uji pada website, lalu pastikan baris JSON baru muncul di file. Contoh event anomali yang bisa diuji hanya di environment sandbox/test:

- Login gagal berulang dari satu IP.
- Callback Midtrans dengan signature tidak valid.
- Gross amount callback sandbox tidak cocok dengan total order.
- Customer mencoba membuka endpoint pembayaran untuk order milik customer lain.
- Admin membuat/mengubah/menghapus produk.
- Email sertifikat berhasil/gagal dikirim setelah pembayaran disetujui (rules 100537–100539).
- Admin mencoba menyetujui pembayaran Midtrans secara manual (harus diblokir dan memunculkan rule 100536).

Periksa `alerts.json`/Wazuh Dashboard setelah agent dan manager tersambung. Aktivitas rutin memakai level 3 agar melewati ambang default Wazuh (`log_alert_level=3`) dan terlihat di alerts; anomali pembayaran dan korelasi brute force memiliki level lebih tinggi. Jika konfigurasi Manager kalian mengubah ambang alert, sesuaikan level ini. Untuk menguji rule tanpa menunggu aktivitas aplikasi, jalankan di Manager setelah rule dipasang:

```bash
sudo /var/ossec/bin/wazuh-logtest < wazuh/sample-payment-anomaly.jsonl
sudo /var/ossec/bin/wazuh-logtest < wazuh/sample-auth-bruteforce.jsonl
```

Jalankan dari folder repository yang juga tersedia pada Manager, atau salin file sampel ke Manager dan sesuaikan path-nya. Contoh file di folder ini adalah data sintetis, bukan event dari pengguna nyata.

## Event JSON utama

Setiap event minimal memuat `timestamp`, `app`, `event_id`, `request_id`, `event_category`, `event_action`, `severity`, `outcome`, `actor_id`, `actor_role`, `target_type`, `target_id`, `detail`, `source_ip`, dan `context`.

Tidak ada password, password hash, session token, cookie, Midtrans Server Key, atau signature mentah dalam event JSON. `event_id` yang sama tersedia di database dan JSONL untuk korelasi silang.

## Batasan operasional

- Halaman website adalah Application Audit Trail, bukan pengganti Wazuh Dashboard.
- JSONL ditulis setelah transaksi SQLAlchemy commit. Jika database commit gagal, event sukses tidak dikeluarkan ke JSONL.
- Backup dan retensi volume log perlu ditetapkan pada server. Pertimbangkan log rotation/retention agar volume tidak tumbuh tanpa batas.
- Untuk deployment non-Docker, set `AUDIT_LOG_FILE` ke lokasi yang dapat dibaca Wazuh Agent.
