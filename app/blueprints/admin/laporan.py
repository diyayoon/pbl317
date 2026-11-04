"""Dashboard dan laporan penjualan admin, termasuk ekspor PDF/Excel."""
from __future__ import annotations

from datetime import date
from io import BytesIO

from flask import abort, jsonify, make_response, render_template, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle

from app.services.report_service import LayananLaporan
from . import admin_bp
from app.utils.decorators import admin_required


def _nilai_excel(value):
    """Cegah formula injection dari nama/email/teks yang berasal dari pengguna."""
    if isinstance(value, str) and value.startswith(("=", "+", "-", "@")):
        return "'" + value
    return value


def _rentang():
    try:
        awal = date.fromisoformat(request.args["tanggal_awal"]) if request.args.get("tanggal_awal") else None
        akhir = date.fromisoformat(request.args["tanggal_akhir"]) if request.args.get("tanggal_akhir") else None
    except ValueError:
        abort(400, description="Format tanggal harus YYYY-MM-DD.")
    if awal and akhir and awal > akhir:
        abort(400, description="Tanggal awal tidak boleh setelah tanggal akhir.")
    if awal and akhir and (akhir - awal).days > 3660:
        abort(400, description="Rentang laporan maksimal 10 tahun.")
    return awal, akhir


@admin_bp.get("/laporan")
@admin_required
def laporan():
    awal, akhir = _rentang()
    return render_template("admin/reports.html", laporan=LayananLaporan().buat_ringkasan(awal, akhir), tanggal_awal=awal, tanggal_akhir=akhir)


@admin_bp.get("/api/laporan")
@admin_required
def api_laporan():
    awal, akhir = _rentang()
    return jsonify(LayananLaporan().buat_ringkasan(awal, akhir, include_transactions=False))


@admin_bp.get("/laporan/export.xlsx")
@admin_required
def ekspor_laporan_excel():
    awal, akhir = _rentang()
    data = LayananLaporan().buat_ringkasan(awal, akhir)
    wb = Workbook()
    ws = wb.active
    ws.title = "Penjualan"
    ws.append(["LAPORAN PENJUALAN ALBIS ANTIQUE"])
    ws.append(["Periode", f"{awal or 'Awal data'} sampai {akhir or 'Hari ini'}"])
    ws.append([])
    ws.append(["Nomor Pesanan", "Tanggal (WIB)", "Customer", "Email", "Status", "Metode Pembayaran", "Total (IDR)"])
    for cell in ws[4]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="24566A")
        cell.alignment = Alignment(horizontal="center")
    for row in data["transaksi_selesai"]:
        ws.append([_nilai_excel(row["order_number"]), _nilai_excel(row["tanggal"]),
                   _nilai_excel(row["customer"]), _nilai_excel(row["email"]),
                   _nilai_excel(row["status"]), _nilai_excel(row["metode"]), row["total"]])
    ws.append([])
    ws.append(["Total pendapatan", data["pendapatan"]])
    ws.append(["Pesanan selesai", data["selesai"]])
    ws.append(["Produk terjual", data["produk_terjual"]])
    widths = [24, 20, 26, 32, 18, 22, 20]
    for idx, width in enumerate(widths, 1):
        ws.column_dimensions[chr(64 + idx)].width = width
    ws.freeze_panes = "A5"
    ws.auto_filter.ref = f"A4:G{max(4, 4 + len(data['transaksi_selesai']))}"
    output = BytesIO()
    wb.save(output)
    output.seek(0)
    return send_file(output, mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", as_attachment=True, download_name="laporan-penjualan-albis-antique.xlsx")


@admin_bp.get("/laporan/export.pdf")
@admin_required
def ekspor_laporan_pdf():
    awal, akhir = _rentang()
    data = LayananLaporan().buat_ringkasan(awal, akhir)
    output = BytesIO()
    doc = SimpleDocTemplate(output, pagesize=landscape(A4), rightMargin=12*mm, leftMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
    styles = getSampleStyleSheet()
    title = ParagraphStyle("ReportTitle", parent=styles["Title"], textColor=colors.HexColor("#20495B"), alignment=TA_CENTER)
    story = [Paragraph("Laporan Penjualan Albis Antique", title), Spacer(1, 5*mm),
             Paragraph(f"Periode: {awal or 'Awal data'} sampai {akhir or 'Hari ini'} (WIB)", styles["Normal"]),
             Paragraph(f"Pendapatan: Rp{data['pendapatan']:,} | Pesanan selesai: {data['selesai']} | Produk terjual: {data['produk_terjual']}", styles["Normal"]), Spacer(1, 5*mm)]
    rows = [["Nomor Pesanan", "Tanggal (WIB)", "Customer", "Email", "Metode", "Total (IDR)"]]
    for row in data["transaksi_selesai"]:
        rows.append([row["order_number"], row["tanggal"], row["customer"], row["email"], row["metode"], f"Rp{row['total']:,}"])
    if len(rows) == 1:
        rows.append(["Tidak ada transaksi selesai pada periode ini.", "", "", "", "", ""])
    table = Table(rows, repeatRows=1, colWidths=[37*mm, 29*mm, 36*mm, 55*mm, 30*mm, 30*mm])
    table.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,0), colors.HexColor("#24566A")),
        ("TEXTCOLOR", (0,0), (-1,0), colors.white),
        ("FONTNAME", (0,0), (-1,0), "Helvetica-Bold"),
        ("GRID", (0,0), (-1,-1), .35, colors.HexColor("#CBDDE5")),
        ("ROWBACKGROUNDS", (0,1), (-1,-1), [colors.white, colors.HexColor("#F1F8FB")]),
        ("VALIGN", (0,0), (-1,-1), "MIDDLE"),
        ("FONTSIZE", (0,0), (-1,-1), 8),
        ("TOPPADDING", (0,0), (-1,-1), 6), ("BOTTOMPADDING", (0,0), (-1,-1), 6),
    ]))
    story.append(table)
    doc.build(story)
    output.seek(0)
    return send_file(output, mimetype="application/pdf", as_attachment=True, download_name="laporan-penjualan-albis-antique.pdf")
