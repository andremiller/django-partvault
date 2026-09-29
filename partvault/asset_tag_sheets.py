"""Printable asset tags with a compact A4 cutting grid."""

from io import BytesIO
from pathlib import Path

import qrcode
from PIL import Image
from reportlab.lib.pagesizes import A4
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont, TTFError
from reportlab.pdfgen import canvas

MM_TO_PT = 2.83465
QR_SIZE_MM = 10.0
FONT_SIZE_PT = 7.0
MARGIN_MM = 10.0
SPACING_MM = 1.0


def _register_font():
    font_path = Path(__file__).parent / "fonts" / "CascadiaMono-VariableFont_wght.ttf"
    try:
        pdfmetrics.registerFont(TTFont("CascadiaMono", str(font_path)))
    except OSError, TTFError:
        return "Courier"
    return "CascadiaMono"


FONT_NAME = _register_font()


def asset_tag_sheet_pdf(tags: list[str], prefix: str, url_prefix: str) -> bytes:
    """Render validated tags, preserving their order and duplicates across pages."""
    page_width, page_height = A4
    qr_size = QR_SIZE_MM * MM_TO_PT
    spacing = SPACING_MM * MM_TO_PT
    margin = MARGIN_MM * MM_TO_PT
    cell_width = qr_size + 2 * spacing
    # The label baseline is one font size below the QR code. Allow for the
    # font's descent, then leave the same padding as the top and sides.
    text_descent = pdfmetrics.getDescent(FONT_NAME, FONT_SIZE_PT)
    cell_height = qr_size + FONT_SIZE_PT - text_descent + 2 * spacing
    columns = int((page_width - 2 * margin) // cell_width)
    rows = int((page_height - 2 * margin) // cell_height)
    per_page = rows * columns
    start_x = (page_width - columns * cell_width) / 2
    start_y = page_height - (page_height - rows * cell_height) / 2

    output = BytesIO()
    pdf = canvas.Canvas(output, pagesize=A4)
    pdf.setTitle("PartVault asset tags")
    for index, tag in enumerate(tags):
        position = index % per_page
        if index and position == 0:
            pdf.showPage()
        row, column = divmod(position, columns)
        cell_x = start_x + column * cell_width
        cell_y = start_y - row * cell_height
        qr_x = cell_x + spacing
        qr_y = cell_y - spacing - qr_size

        # Cut around the whole sticker, leaving the QR code and label together.
        pdf.saveState()
        pdf.setStrokeGray(0.8)
        pdf.setLineWidth(0.25)
        pdf.rect(
            cell_x, cell_y - cell_height, cell_width, cell_height, stroke=1, fill=0
        )
        pdf.restoreState()

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=1,
        )
        qr.add_data(f"{url_prefix}{tag}")
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        size_px = int(QR_SIZE_MM * 11.811)
        image = image.resize((size_px, size_px), Image.Resampling.LANCZOS)
        pdf.drawImage(
            ImageReader(image),
            qr_x,
            qr_y,
            width=qr_size,
            height=qr_size,
            preserveAspectRatio=True,
        )
        pdf.setFont(FONT_NAME, FONT_SIZE_PT)
        pdf.drawCentredString(qr_x + qr_size / 2, qr_y - FONT_SIZE_PT, f"{prefix}{tag}")

    pdf.save()
    return output.getvalue()
