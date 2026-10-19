-- Data awal: versi migrasi (alembic_version), kategori, dan koleksi pembuka.
-- Admin TIDAK ada di sini; buat lewat: python -m flask --app run create-admin

--
-- PostgreSQL database dump
--


-- Dumped from database version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)
-- Dumped by pg_dump version 16.15 (Ubuntu 16.15-0ubuntu0.24.04.1)

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

--
-- Data for Name: alembic_version; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.alembic_version VALUES ('20261017_0003');


--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.categories VALUES (1, 'Jam & Timepiece', 'timepiece', '⌚', '2026-10-17 16:29:27.730683+00', true);
INSERT INTO public.categories VALUES (2, 'Kamera Vintage', 'camera', '📷', '2026-10-17 16:29:27.733323+00', true);
INSERT INTO public.categories VALUES (3, 'Porselen & Keramik', 'porcelain', '🏺', '2026-10-17 16:29:27.734684+00', true);
INSERT INTO public.categories VALUES (4, 'Buku & Manuskrip', 'books', '📚', '2026-10-17 16:29:27.735997+00', true);
INSERT INTO public.categories VALUES (5, 'Perhiasan Antik', 'jewelry', '💍', '2026-10-17 16:29:27.737136+00', true);
INSERT INTO public.categories VALUES (6, 'Musik Vintage', 'music', '🎼', '2026-10-17 16:29:27.738315+00', true);
INSERT INTO public.categories VALUES (7, 'Dekorasi & Interior', 'decor', '🪞', '2026-10-17 16:29:27.739456+00', true);
INSERT INTO public.categories VALUES (8, 'Travel Collectibles', 'travel', '🧭', '2026-10-17 16:29:27.740365+00', true);


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.products VALUES (1, 1, 'Brass Pocket Watch', 'brass-pocket-watch', 'Jam saku bergaya Art Deco dengan karakter patina alami dan detail mekanis klasik.', 1850000, 1, '1900–1949', 'France', 'Brass', 'Good', 'Verified', 'Foto Brass Pocket Watch', 'https://commons.wikimedia.org/wiki/File:Pocket_watch_MET_SF1979_498_1_img1.jpg', true, '2026-10-17 16:29:27.752407+00', '2026-10-17 16:29:27.752415+00');
INSERT INTO public.products VALUES (2, 2, 'Kodak Folding Camera', 'kodak-folding-camera', 'Kamera lipat vintage dengan konstruksi metal dan leather bellows untuk kolektor fotografi analog.', 2400000, 1, '1900–1949', 'USA', 'Metal & Leather', 'Fair', 'Documented', 'Foto Kodak Folding Camera', 'https://commons.wikimedia.org/wiki/File:Kokak_Pocket,_1896_-_Musée_Nicéphore_Niépce_-_DSC06071.JPG', true, '2026-10-17 16:29:27.759372+00', '2026-10-17 16:29:27.759379+00');
INSERT INTO public.products VALUES (3, 3, 'Blue Porcelain Vase', 'blue-porcelain-vase', 'Vas porselen bernuansa biru-putih dengan motif klasik dan glasir yang masih terjaga.', 1325000, 1, '1950–1999', 'Japan', 'Porcelain', 'Excellent', 'Verified', 'Foto Blue Porcelain Vase', 'https://commons.wikimedia.org/wiki/File:Blue_and_white_vase_1271_1368_Jingdezhen_unearthed_in_Jiangxi_Province.jpg', true, '2026-10-17 16:29:27.762506+00', '2026-10-17 16:29:27.762512+00');
INSERT INTO public.products VALUES (4, 5, 'Victorian Cameo Brooch', 'victorian-cameo-brooch', 'Bros cameo dengan siluet klasik, frame berornamen, dan karakter Victorian yang kuat.', 2750000, 1, '1800s', 'England', 'Silver', 'Good', 'Verified', 'Foto Victorian Cameo Brooch', 'https://commons.wikimedia.org/wiki/File:Firm_of_Fortunato_Pio_Castellani_-_Brooch_with_Cameo_Bust_of_Ellen_Walters_-_Walters_572001.jpg', true, '2026-10-17 16:29:27.765179+00', '2026-10-17 16:29:27.765184+00');
INSERT INTO public.products VALUES (5, 4, 'Leather Bound Journal', 'leather-bound-journal', 'Jurnal lama berkulit dengan detail emboss dan halaman berpatina yang menampilkan usia alaminya.', 980000, 1, '1900–1949', 'Italy', 'Leather & Paper', 'Fair', 'Documented', 'Foto Leather Bound Journal', 'https://commons.wikimedia.org/wiki/File:Jfisher_journal_18160712.jpg', true, '2026-10-17 16:29:27.767722+00', '2026-10-17 16:29:27.767727+00');
INSERT INTO public.products VALUES (6, 8, 'Brass Telescope', 'brass-telescope', 'Teleskop kuningan bergaya nautikal dengan optik dekoratif, ideal untuk display dan koleksi.', 2100000, 2, '1950–1999', 'Germany', 'Brass & Glass', 'Good', 'Inspected', 'Foto Brass Telescope', 'https://commons.wikimedia.org/wiki/File:Newton_telescope_replica_1668.jpg', true, '2026-10-17 16:29:27.770319+00', '2026-10-17 16:29:27.770322+00');
INSERT INTO public.products VALUES (7, 6, 'Vintage Music Box', 'vintage-music-box', 'Kotak musik mekanik vintage dengan ukiran lembut dan karakter suara yang hangat.', 1675000, 1, '1950–1999', 'Switzerland', 'Wood & Metal', 'Excellent', 'Verified', 'Foto Vintage Music Box', 'https://commons.wikimedia.org/wiki/File:Music_Box_And_Key,_late_19th_century_(CH_18416829-2).jpg', true, '2026-10-17 16:29:27.772766+00', '2026-10-17 16:29:27.77277+00');
INSERT INTO public.products VALUES (8, 7, 'Ornamental Hand Mirror', 'ornamental-hand-mirror', 'Cermin tangan ornamental dengan frame perak klasik dan detail ukiran yang halus.', 1450000, 1, '1900–1949', 'France', 'Silver & Glass', 'Good', 'Inspected', 'Foto Ornamental Hand Mirror', 'https://commons.wikimedia.org/wiki/File:Hand_Mirror,_ca._1890_(CH_18660743).jpg', true, '2026-10-17 16:29:27.774646+00', '2026-10-17 16:29:27.77465+00');


--
-- Data for Name: product_images; Type: TABLE DATA; Schema: public; Owner: -
--

INSERT INTO public.product_images VALUES (1, 1, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Pocket%20watch%20MET%20SF1979%20498%201%20img1.jpg', 'Foto Brass Pocket Watch', true, 0);
INSERT INTO public.product_images VALUES (2, 2, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Kokak%20Pocket%2C%201896%20-%20Mus%C3%A9e%20Nic%C3%A9phore%20Ni%C3%A9pce%20-%20DSC06071.JPG', 'Foto Kodak Folding Camera', true, 0);
INSERT INTO public.product_images VALUES (3, 3, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Blue%20and%20white%20vase%201271%201368%20Jingdezhen%20unearthed%20in%20Jiangxi%20Province.jpg', 'Foto Blue Porcelain Vase', true, 0);
INSERT INTO public.product_images VALUES (4, 4, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Firm%20of%20Fortunato%20Pio%20Castellani%20-%20Brooch%20with%20Cameo%20Bust%20of%20Ellen%20Walters%20-%20Walters%20572001.jpg', 'Foto Victorian Cameo Brooch', true, 0);
INSERT INTO public.product_images VALUES (5, 5, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Jfisher%20journal%2018160712.jpg', 'Foto Leather Bound Journal', true, 0);
INSERT INTO public.product_images VALUES (6, 6, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Newton%20telescope%20replica%201668.jpg', 'Foto Brass Telescope', true, 0);
INSERT INTO public.product_images VALUES (7, 7, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Music%20Box%20And%20Key%2C%20late%2019th%20century%20%28CH%2018416829-2%29.jpg', 'Foto Vintage Music Box', true, 0);
INSERT INTO public.product_images VALUES (8, 8, 'https://commons.wikimedia.org/wiki/Special:Redirect/file/Hand%20Mirror%2C%20ca.%201890%20%28CH%2018660743%29.jpg', 'Foto Ornamental Hand Mirror', true, 0);


--
-- Name: categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--



--
-- Name: product_images_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--



--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--



--
-- PostgreSQL database dump complete
--



-- Samakan urutan ID agar INSERT berikutnya tidak bentrok.
SELECT setval(pg_get_serial_sequence('public.categories','id'), (SELECT COALESCE(MAX(id),1) FROM public.categories));
SELECT setval(pg_get_serial_sequence('public.products','id'), (SELECT COALESCE(MAX(id),1) FROM public.products));
SELECT setval(pg_get_serial_sequence('public.product_images','id'), (SELECT COALESCE(MAX(id),1) FROM public.product_images));
