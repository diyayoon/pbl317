"""Dashboard dan laporan penjualan admin, termasuk ekspor PDF/Excel."""
from __future__ import annotations

from datetime import date
from io import BytesIO

from flask import abort, jsonify, make_response, render_template, request, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.worksheet.table import Table as ExcelTable, TableStyleInfo
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table as PDFTable, TableStyle

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
    ws.sheet_view.showGridLines = False
    ws.sheet_view.zoomScale = 90

    headers = ["Nomor Pesanan", "Tanggal (WIB)", "Customer", "Email", "Status", "Metode Pembayaran", "Total (IDR)"]
    ws.merge_cells("A1:G1")
    title = ws["A1"]
    title.value = "LAPORAN PENJUALAN ALBIS ANTIQUE"
    title.font = Font(name="Aptos Display", size=16, bold=True, color="20495B")
    title.alignment = Alignment(vertical="center")
    ws.row_dimensions[1].height = 30

    ws.merge_cells("A2:G2")
    ws["A2"] = f"Periode: {awal.isoformat() if awal else 'Awal data'} sampai {akhir.isoformat() if akhir else 'Hari ini'} (WIB)"
    ws["A2"].font = Font(name="Aptos", size=10, color="557487")
    ws["A2"].alignment = Alignment(vertical="center")
    ws.row_dimensions[2].height = 22
    ws.row_dimensions[3].height = 10

    for col, value in enumerate(headers, 1):
        cell = ws.cell(row=4, column=col, value=value)
        cell.font = Font(name="Aptos", bold=True, color="FFFFFF", size=10)
        cell.fill = PatternFill("solid", fgColor="24566A")
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    ws.row_dimensions[4].height = 28

    transaksi = data["transaksi_selesai"]
    for row_index, row in enumerate(transaksi, 5):
        values = [
            _nilai_excel(row["order_number"]), _nilai_excel(row["tanggal"]),
            _nilai_excel(row["customer"]), _nilai_excel(row["email"]),
            _nilai_excel(row["status"]), _nilai_excel(row["metode"]), int(row["total"] or 0),
        ]
        for col, value in enumerate(values, 1):
            cell = ws.cell(row=row_index, column=col, value=value)
            cell.font = Font(name="Aptos", size=10, color="203B4A")
            cell.alignment = Alignment(vertical="center", wrap_text=(col in (1, 3, 4, 6)))
            cell.border = Border(bottom=Side(style="hair", color="D8E8EF"))
            if col == 7:
                cell.number_format = '"Rp" #,##0;[Red]-"Rp" #,##0'
                cell.alignment = Alignment(horizontal="right", vertical="center")
        ws.row_dimensions[row_index].height = 22

    data_end = max(5, 4 + len(transaksi))
    if not transaksi:
        ws.merge_cells(start_row=5, start_column=1, end_row=5, end_column=7)
        ws.cell(5, 1, "Tidak ada transaksi selesai pada periode ini.")
        ws.cell(5, 1).font = Font(name="Aptos", italic=True, color="6B8492")
        ws.cell(5, 1).alignment = Alignment(vertical="center")
        ws.row_dimensions[5].height = 25
        table_ref = "A4:G4"
        data_end = 5
    else:
        table_ref = f"A4:G{data_end}"

    table = ExcelTable(displayName="PenjualanAlbisAntique", ref=table_ref)
    table.tableStyleInfo = TableStyleInfo(
        name="TableStyleMedium2", showFirstColumn=False, showLastColumn=False,
        showRowStripes=True, showColumnStripes=False,
    )
    ws.add_table(table)

    summary_start = data_end + 3
    ws.merge_cells(start_row=summary_start, start_column=1, end_row=summary_start, end_column=7)
    ws.cell(summary_start, 1, "RINGKASAN")
    ws.cell(summary_start, 1).font = Font(name="Aptos", bold=True, color="24566A", size=11)
    summary_rows = [
        ("Total pendapatan", int(data["pendapatan"] or 0), True),
        ("Pesanan selesai", int(data["selesai"] or 0), False),
        ("Produk terjual", int(data["produk_terjual"] or 0), False),
    ]
    for offset, (label, value, currency) in enumerate(summary_rows, 1):
        row_no = summary_start + offset
        ws.merge_cells(start_row=row_no, start_column=1, end_row=row_no, end_column=6)
        ws.cell(row_no, 1, label)
        ws.cell(row_no, 7, value)
        ws.cell(row_no, 1).font = Font(name="Aptos", size=10, color="405E6D")
        ws.cell(row_no, 7).font = Font(name="Aptos", size=10, bold=True, color="203B4A")
        ws.cell(row_no, 7).alignment = Alignment(horizontal="right")
        if currency:
            ws.cell(row_no, 7).number_format = '"Rp" #,##0;[Red]-"Rp" #,##0'

    widths = [18, 16, 18, 22, 13, 17, 16]
    for idx, width in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = width
    ws.freeze_panes = None
    ws.auto_filter.ref = None
    ws.sheet_properties.pageSetUpPr.fitToPage = True
    ws.page_setup.orientation = "landscape"
    ws.page_setup.fitToWidth = 1
    ws.page_setup.fitToHeight = 0
    ws.print_title_rows = "1:4"
    ws.print_area = f"A1:G{summary_start + len(summary_rows)}"
    ws.sheet_properties.pageSetUpPr.autoPageBreaks = False
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
    table = PDFTable(rows, repeatRows=1, colWidths=[37*mm, 29*mm, 36*mm, 55*mm, 30*mm, 30*mm])
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
