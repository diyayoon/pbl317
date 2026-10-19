'use strict';

/* Validasi sisi klien formulir ganti kata sandi (server tetap memvalidasi ulang). */
document.addEventListener("DOMContentLoaded", () => {
    const form = document.getElementById("formUbahPassword");
    if (!form) return;

    const current = document.getElementById("passwordLama");
    const fresh = document.getElementById("passwordBaru");
    const confirm = document.getElementById("konfirmasiPasswordBaru");

    const showError = (field, message) => {
        const node = document.getElementById(`${field.id}Error`);
        if (!node) return;
        node.textContent = message;
        node.hidden = !message;
        field.setAttribute("aria-invalid", String(Boolean(message)));
    };

    const newPasswordError = () => {
        if (fresh.value.length < 16) return "Kata sandi baru minimal 16 karakter.";
        if (fresh.value.length > 128) return "Maksimal 128 karakter.";
        if (!fresh.value.trim()) return "Kata sandi tidak boleh hanya berisi spasi.";
        if (fresh.value === current.value) {
            return "Kata sandi baru harus berbeda dari kata sandi saat ini.";
        }
        return "";
    };

    [current, fresh, confirm].forEach(field => {
        field.addEventListener("input", () => showError(field, ""));
    });

    form.addEventListener("submit", event => {
        const errors = [
            [current, current.value ? "" : "Kata sandi saat ini wajib diisi."],
            [fresh, newPasswordError()],
            [
                confirm,
                !confirm.value
                    ? "Konfirmasi wajib diisi."
                    : confirm.value !== fresh.value
                        ? "Konfirmasi kata sandi tidak cocok."
                        : "",
            ],
        ];

        errors.forEach(([field, message]) => showError(field, message));
        const firstError = errors.find(([, message]) => message);
        if (firstError) {
            event.preventDefault();
            firstError[0].focus();
        }
    });
});
