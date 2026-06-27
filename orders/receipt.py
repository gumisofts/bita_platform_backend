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


def _draw_returned_watermark(canvas, doc):
    canvas.saveState()
    width, height = A4
    canvas.setFont("Helvetica-Bold", 72)
    canvas.setFillColor(colors.Color(0.85, 0.1, 0.1, alpha=0.18))
    canvas.translate(width / 2, height / 2)
    canvas.rotate(45)
    canvas.drawCentredString(0, 0, "RETURNED")
    canvas.restoreState()


def generate_order_receipt(order) -> bytes:
    """Return PDF bytes for a given Order instance."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=15 * mm,
        leftMargin=15 * mm,
        topMargin=15 * mm,
        bottomMargin=15 * mm,
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
            onFirstPage=_draw_returned_watermark,
            onLaterPages=_draw_returned_watermark,
        )
    else:
        doc.build(story)
    return buffer.getvalue()
