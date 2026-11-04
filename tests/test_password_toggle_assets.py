from pathlib import Path
import re

ROOT = Path(__file__).resolve().parents[1]


def test_shared_components_styles_password_toggle_globally():
    base = (ROOT / "app/templates/base.html").read_text(encoding="utf-8")
    css = (ROOT / "app/static/css/components.css").read_text(encoding="utf-8")

    assert 'filename=\'css/components.css\'' in base
    assert ".password-toggle-icon" in css
    assert "max-width: 21px" in css
    assert "max-height: 21px" in css


def test_password_eye_svgs_have_small_intrinsic_dimensions():
    icons = ROOT / "app/static/images/icons"
    for name in ("eye-open.svg", "eye-close.svg"):
        svg = (icons / name).read_text(encoding="utf-8")
        root = re.search(r"<svg\b[^>]*>", svg)
        assert root, f"Elemen SVG tidak ditemukan: {name}"
        assert re.search(r'\bwidth="24"', root.group(0)), name
        assert re.search(r'\bheight="24"', root.group(0)), name


def test_customer_and_admin_password_pages_use_global_base_template():
    for relative in (
        "app/templates/customer/security.html",
        "app/templates/admin/account.html",
    ):
        template = (ROOT / relative).read_text(encoding="utf-8")
        assert "extends 'base.html'" in template
        assert 'class="password-toggle"' in template
