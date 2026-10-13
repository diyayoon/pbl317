"""Route customer prototipe yang membutuhkan sesi akun demo."""
from flask import render_template
from flask_login import login_required
from app.utils.decorators import role_required
from . import customer_bp

@customer_bp.get('/akun')
@login_required
@role_required('customer')
def dashboard():
    return render_template('customer/dashboard.html')

@customer_bp.get('/keranjang')
@login_required
@role_required('customer')
def keranjang():
    return render_template('customer/cart.html')

@customer_bp.get('/wishlist')
@login_required
@role_required('customer')
def wishlist():
    return render_template('customer/wishlist.html')

@customer_bp.get('/checkout')
@login_required
@role_required('customer')
def checkout():
    return render_template('customer/checkout.html')

@customer_bp.get('/pesanan')
@login_required
@role_required('customer')
def pesanan():
    return render_template('customer/orders.html')

@customer_bp.get('/profil')
@login_required
@role_required('customer')
def profil():
    return render_template('customer/profile.html')
