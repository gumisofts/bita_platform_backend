import io
from decimal import Decimal

from django.utils import timezone
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    HRFlowable,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

# ── Branding ──────────────────────────────────────────────────────────────────
# Edit these to change what appears in the footer of every generated receipt.
BITA_BRAND = "Powered by Bita"
BITA_TAGLINE = "Smart business & inventory management"
BITA_WEBSITE = "www.bita.et"
BITA_SUPPORT = "support@bita.et"


def _draw_returned_watermark(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFont("Helvetica-Bold", 72)
    canvas.setFillColor(colors.Color(0.85, 0.1, 0.1, alpha=0.18))
    canvas.translate(width / 2, height / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "RETURNED")
    canvas.restoreState()


def _draw_footer(canvas, doc):
    """Pinned branding footer drawn at the bottom of every page."""
    canvas.saveState()
    width, _ = A4
    center_x = width / 2

    # Separator line above the footer.
    canvas.setStrokeColor(colors.HexColor("#cccccc"))
    canvas.setLineWidth(0.5)
    canvas.line(15 * mm, 16 * mm, width - 15 * mm, 16 * mm)

    # "Powered by Bita" brand line.
    canvas.setFont("Helvetica-Bold", 8)
    canvas.setFillColor(colors.HexColor("#333333"))
    canvas.drawCentredString(center_x, 12 * mm, BITA_BRAND)

    # Tagline + contact details.
    canvas.setFont("Helvetica", 7)
    canvas.setFillColor(colors.HexColor("#888888"))
    canvas.drawCentredString(center_x, 8.5 * mm, BITA_TAGLINE)
    contact = "  |  ".join(p for p in [BITA_WEBSITE, BITA_SUPPORT] if p)
    if contact:
        canvas.drawCentredString(center_x, 5.5 * mm, contact)

    # Generation timestamp (left) and page number (right).
    generated_at = timezone.localtime(timezone.now()).strftime("%d %b %Y %H:%M")
    canvas.drawString(15 * mm, 5.5 * mm, f"Generated {generated_at}")
    canvas.drawRightString(width - 15 * mm, 5.5 * mm, f"Page {doc.page}")

    canvas.restoreState()


def _draw_footer_with_watermark(canvas, doc):
    _draw_returned_watermark(canvas, doc)
    _draw_footer(canvas, doc)


def generate_order_receipt(order) -> bytes:
    """Return PDF bytes for a given Order instance."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=22 * mm,  # leave room for the pinned branding footer
    )

    styles = getSampleStyleSheet()

    heading = ParagraphStyle(
        "Heading",
        parent=styles["Normal"],
        fontSize=18,
        fontName="Helvetica-Bold",
        spaceAfter=2 * mm,
    )
    subheading = ParagraphStyle(
        "SubHeading",
        parent=styles["Normal"],
        fontSize=11,
        fontName="Helvetica-Bold",
        spaceAfter=1 * mm,
    )
    normal = ParagraphStyle(
        "Body",
        parent=styles["Normal"],
        fontSize=9,
        leading=13,
    )
    small = ParagraphStyle(
        "Small",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.grey,
        leading=12,
    )
    right_align = ParagraphStyle(
        "Right",
        parent=styles["Normal"],
        fontSize=9,
        alignment=2,
    )

    story = []

    # ── Business header ──────────────────────────────────────────────────────
    business = order.business
    branch = order.branch

    story.append(Paragraph(business.name, heading))

    address = getattr(business, "address", None)
    if address:
        addr_parts = [
            p
            for p in [
                address.sublocality,
                address.locality,
                address.admin_1,
                address.country,
            ]
            if p
        ]
        story.append(Paragraph(", ".join(addr_parts), small))

    if branch:
        story.append(Paragraph(f"Branch: {branch.name}", small))

    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.black))
    story.append(Spacer(1, 3 * mm))

    # ── Receipt title + meta ─────────────────────────────────────────────────
    story.append(Paragraph("SALES RECEIPT", subheading))

    receipt_date = order.created_at
    if timezone.is_aware(receipt_date):
        receipt_date = timezone.localtime(receipt_date)

    meta_data = [
        ["Receipt #:", str(order.id)[:8].upper()],
        ["Date:", receipt_date.strftime("%d %b %Y  %H:%M")],
        ["Status:", order.status],
    ]

    if order.customer:
        meta_data.append(["Customer:", order.customer.full_name or "—"])
        if getattr(order.customer, "phone_number", None):
            meta_data.append(["Phone:", order.customer.phone_number])

    if order.employee:
        meta_data.append(["Served by:", order.employee.full_name])

    if order.payment_method:
        meta_data.append(["Payment:", order.payment_method.display_name])

    meta_table = Table(meta_data, colWidths=[35 * mm, None])
    meta_table.setStyle(
        TableStyle(
            [
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TEXTCOLOR", (0, 0), (0, -1), colors.HexColor("#555555")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 1.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
            ]
        )
    )
    story.append(meta_table)

    story.append(Spacer(1, 4 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 3 * mm))

    # ── Order items table ────────────────────────────────────────────────────
    story.append(Paragraph("Items", subheading))
    story.append(Spacer(1, 2 * mm))

    col_widths = [None, 20 * mm, 30 * mm, 30 * mm]
    header_row = [
        Paragraph("<b>Item</b>", normal),
        Paragraph("<b>Qty</b>", normal),
        Paragraph("<b>Unit Price</b>", normal),
        Paragraph("<b>Total</b>", normal),
    ]
    rows = [header_row]

    items = order.items.select_related("variant__item").all()
    for item in items:
        unit_price = item.price or Decimal("0")
        line_total = unit_price * item.quantity
        item_name = item.variant.item.name
        variant_name = item.variant.name
        display_name = (
            item_name if item_name == variant_name else f"{item_name} — {variant_name}"
        )
        rows.append(
            [
                Paragraph(display_name, normal),
                Paragraph(str(item.quantity), normal),
                Paragraph(f"{unit_price:,.2f}", normal),
                Paragraph(f"{line_total:,.2f}", normal),
            ]
        )

    items_table = Table(rows, colWidths=col_widths, repeatRows=1)
    items_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#f0f0f0")),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.grey),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, colors.HexColor("#fafafa")],
                ),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("ALIGN", (1, 0), (-1, -1), "RIGHT"),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("LINEBELOW", (0, -1), (-1, -1), 0.5, colors.grey),
            ]
        )
    )
    story.append(items_table)

    story.append(Spacer(1, 3 * mm))

    # ── Totals ───────────────────────────────────────────────────────────────
    VAT_RATE = Decimal("0.00")  # 0% — update when VAT is applicable

    subtotal = order.total_payable or Decimal("0")
    vat_amount = (subtotal * VAT_RATE).quantize(Decimal("0.01"))
    total_payable = subtotal + vat_amount

    totals_data = [
        [Paragraph("Subtotal", normal), Paragraph(f"{subtotal:,.2f} ETB", right_align)],
        [
            Paragraph(f"VAT ({int(VAT_RATE * 100)}%)", normal),
            Paragraph(f"{vat_amount:,.2f} ETB", right_align),
        ],
        [
            Paragraph("<b>Total Payable</b>", normal),
            Paragraph(f"<b>{total_payable:,.2f} ETB</b>", right_align),
        ],
    ]
    totals_table = Table(totals_data, colWidths=[None, 50 * mm])
    totals_table.setStyle(
        TableStyle(
            [
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
                ("LINEABOVE", (0, 0), (-1, 0), 0.5, colors.grey),
                ("LINEABOVE", (0, -1), (-1, -1), 1, colors.black),
                ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, -1), (-1, -1), 10),
                ("ALIGN", (1, 0), (1, -1), "RIGHT"),
            ]
        )
    )
    story.append(totals_table)

    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=colors.grey))
    story.append(Spacer(1, 3 * mm))

    story.append(Paragraph("Thank you for your business!", small))

    is_returned = order.status == "RETURNED"
    if is_returned:
        doc.build(
            story,
            onFirstPage=_draw_footer_with_watermark,
            onLaterPages=_draw_footer_with_watermark,
        )
    else:
        doc.build(story, onFirstPage=_draw_footer, onLaterPages=_draw_footer)
    return buffer.getvalue()
