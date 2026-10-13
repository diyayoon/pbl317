# nginx versi sama dengan container lama (my-nginx), tetapi sekarang berperan sebagai reverse proxy ke Flask.
FROM nginx:1.27-alpine

# Ganti konfigurasi bawaan dengan konfigurasi proxy milik proyek.
RUN rm -f /etc/nginx/conf.d/default.conf
COPY default.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

# Jalankan nginx di foreground
CMD ["nginx", "-g", "daemon off;"]
