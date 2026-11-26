"""
generar_pdf_qr.py
=================
Flyer A4 con logo y QR del menu digital de Bar Sergios.
"""

import subprocess, sys, os

def instalar(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

for dep in ["reportlab", "Pillow"]:
    try:
        __import__("PIL" if dep == "Pillow" else dep.lower())
    except ImportError:
        print(f"Instalando {dep}...")
        instalar(dep)

from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib.colors import HexColor, white, black
from reportlab.pdfgen import canvas
from PIL import Image as PILImage
import math

# ── Rutas ─────────────────────────────────────────────────────────────────────
BASE    = os.path.dirname(os.path.abspath(__file__))
QR_IMG  = os.path.join(BASE, "qr.png")
LOGO    = os.path.join(BASE, "assets", "sergios_logo.png")
OUTPUT  = os.path.join(BASE, "Menu_QR_BarSergios.pdf")

# ── Paleta ────────────────────────────────────────────────────────────────────
C_BG        = HexColor("#FAFAF7")   # fondo crema calido
C_WHITE     = HexColor("#FFFFFF")
C_RED       = HexColor("#9B2335")   # rojo Sergio's
C_RED_DARK  = HexColor("#6E1825")   # rojo oscuro sombra
C_GREEN     = HexColor("#5A7A35")   # verde Sergio's
C_BORDER    = HexColor("#E2D9D0")   # borde suave
C_GOLD      = HexColor("#C9A84C")   # acento dorado
C_DARK      = HexColor("#1C1C1C")   # texto oscuro
C_MID       = HexColor("#555555")   # texto medio
C_SOFT      = HexColor("#999999")   # texto suave
C_PINK      = HexColor("#FFCCD5")   # texto pie

W, H = A4  # pts: 595.27 x 841.89


# ── Canvas personalizado ───────────────────────────────────────────────────────
class Flyer(canvas.Canvas):

    def __init__(self, path):
        super().__init__(path, pagesize=A4)
        self.setTitle("Bar Sergios - Carta Digital QR")
        self.setAuthor("Bar Sergios")
        self.setSubject("Escanea el QR para acceder a la carta digital")

    # ── Primitivas ─────────────────────────────────────────────────────────
    def fill(self, color):   self.setFillColor(color)
    def stroke(self, color): self.setStrokeColor(color)

    def centered_text(self, x, y, text, font, size, color):
        self.fill(color)
        self.setFont(font, size)
        self.drawCentredString(x, y, text)

    def hline(self, x0, x1, y, color, width=0.5):
        self.stroke(color)
        self.setLineWidth(width)
        self.line(x0, y, x1, y)

    def diamond(self, cx, cy, r, color):
        self.fill(color)
        p = self.beginPath()
        p.moveTo(cx, cy + r); p.lineTo(cx + r, cy)
        p.lineTo(cx, cy - r); p.lineTo(cx - r, cy)
        p.close()
        self.drawPath(p, fill=1, stroke=0)

    def ornamental_line(self, cy, half_w, color, dot_r=1.5):
        """Linea con rombo central y dos puntos laterales."""
        cx = W / 2
        self.hline(cx - half_w, cx - 16*mm, cy, color, 0.6)
        self.hline(cx + 16*mm, cx + half_w, cy, color, 0.6)
        self.diamond(cx, cy, 3.5, color)
        self.fill(color)
        self.circle(cx - 10*mm, cy, dot_r, fill=1, stroke=0)
        self.circle(cx + 10*mm, cy, dot_r, fill=1, stroke=0)

    def star(self, cx, cy, r_out, r_in, pts, color):
        self.fill(color)
        path = self.beginPath()
        for i in range(pts * 2):
            a = math.pi / pts * i - math.pi / 2
            r = r_out if i % 2 == 0 else r_in
            x, y = cx + r * math.cos(a), cy + r * math.sin(a)
            path.moveTo(x, y) if i == 0 else path.lineTo(x, y)
        path.close()
        self.drawPath(path, fill=1, stroke=0)

    def corner_bracket(self, x, y, arm, flip_x=False, flip_y=False):
        sx = -1 if flip_x else 1
        sy = -1 if flip_y else 1
        self.stroke(C_RED)
        self.setLineWidth(1.2)
        self.line(x, y, x + sx * arm, y)
        self.line(x, y, x, y + sy * arm)
        # Punto de esquina
        self.fill(C_RED)
        self.circle(x, y, 2.2, fill=1, stroke=0)

    # ── Fondo ───────────────────────────────────────────────────────────────
    def draw_background(self):
        self.fill(C_BG)
        self.rect(0, 0, W, H, fill=1, stroke=0)

        # Cabecera coloreada (banda superior fina)
        self.fill(C_RED)
        self.rect(0, H - 8*mm, W, 8*mm, fill=1, stroke=0)

        # Marco exterior doble
        for m, lw, col in [(9*mm, 0.9, C_BORDER), (12*mm, 0.35, C_GOLD)]:
            self.stroke(col)
            self.setLineWidth(lw)
            self.rect(m, m, W - 2*m, H - 2*m, fill=0, stroke=1)

    # ── QR card ─────────────────────────────────────────────────────────────
    def draw_qr_card(self, cx, cy, qr_sz):
        pad = 11 * mm
        x = cx - qr_sz/2 - pad
        y = cy - qr_sz/2 - pad
        w = qr_sz + 2*pad
        h = qr_sz + 2*pad
        r = 14
        # Sombra (3 capas)
        for i, (dx, dy, alpha) in enumerate([(5, -5, .04), (3, -3, .06), (1.5, -1.5, .05)]):
            self.setFillColorRGB(.55, .48, .44, alpha)
            self.roundRect(x + dx, y + dy, w, h, r, fill=1, stroke=0)
        # Fondo blanco
        self.fill(C_WHITE)
        self.stroke(C_BORDER)
        self.setLineWidth(1.0)
        self.roundRect(x, y, w, h, r, fill=1, stroke=1)
        # Borde interior dorado
        ip = 3
        self.stroke(C_GOLD)
        self.setLineWidth(0.5)
        self.roundRect(x+ip, y+ip, w-2*ip, h-2*ip, r-2, fill=0, stroke=1)

    # ── Pagina ───────────────────────────────────────────────────────────────
    def build(self):
        # ── Constantes de layout (en puntos, origen = abajo) ───────────────
        FOOT_H   = 26 * mm   # banda roja del pie
        FOOT_LBL = 7  * mm   # espacio entre elementos del pie

        # Zona logo (la anchura del logo determina la posición vertical)
        LOGO_H   = 82 * mm
        LOGO_TOP = H - 10*mm - 8*mm   # debajo de la banda roja y el padding
        LOGO_BOT = LOGO_TOP - LOGO_H  # y inferior del logo

        # Zona central
        DIVIDER1_Y  = LOGO_BOT - 9  * mm
        TAGLINE_Y   = DIVIDER1_Y - 13 * mm
        SUBLABEL_Y  = TAGLINE_Y - 10 * mm

        QR_SIZE  = 78 * mm
        # El QR se centra en el espacio disponible entre SUBLABEL y el footer
        avail    = SUBLABEL_Y - FOOT_H - 4*mm
        QR_CY    = FOOT_H + 4*mm + avail / 2

        TITLE_Y  = QR_CY + QR_SIZE/2 + 15 * mm
        INST_Y   = QR_CY - QR_SIZE/2 - 12 * mm
        DIVIDER2_Y = QR_CY - QR_SIZE/2 - 24 * mm

        cx = W / 2

        # ── Dibuja ──────────────────────────────────────────────────────────
        self.draw_background()

        # Texto en la banda roja superior
        self.centered_text(cx, H - 5.5*mm, "BAR SERGIOS", "Helvetica-Bold", 7.5, C_WHITE)

        # Esquinas decorativas
        cm, arm = 16*mm, 14*mm
        self.corner_bracket(cm, H - 10*mm - cm, arm)
        self.corner_bracket(W - cm, H - 10*mm - cm, arm, flip_x=True)
        self.corner_bracket(cm, cm, arm, flip_y=True)
        self.corner_bracket(W - cm, cm, arm, flip_x=True, flip_y=True)

        # ── LOGO ────────────────────────────────────────────────────────────
        # Estrellitas flanqueando
        star_y = LOGO_BOT + LOGO_H * 0.5
        for sx in [-65*mm, 65*mm]:
            self.star(cx + sx, star_y, 4, 1.8, 5, C_GOLD)

        if os.path.exists(LOGO):
            with PILImage.open(LOGO) as img:
                iw, ih = img.size
            lw = LOGO_H * (iw / ih)
            self.drawImage(LOGO, cx - lw/2, LOGO_BOT,
                           width=lw, height=LOGO_H,
                           preserveAspectRatio=True, mask='auto')
        else:
            self.centered_text(cx, LOGO_BOT + LOGO_H*0.4, "Sergio's",
                               "Helvetica-BoldOblique", 52, C_RED)

        # ── DIVISOR 1 + TAGLINE ─────────────────────────────────────────────
        self.ornamental_line(DIVIDER1_Y, 65*mm, C_GOLD)

        self.centered_text(cx, TAGLINE_Y,
                           "Sabor autentico  ·  Experiencia unica",
                           "Helvetica-Oblique", 11, C_MID)

        self.centered_text(cx, SUBLABEL_Y,
                           "Descubre toda nuestra carta desde tu movil",
                           "Helvetica", 9, C_SOFT)

        # ── TITULO QR ───────────────────────────────────────────────────────
        self.centered_text(cx, TITLE_Y, "ESCANEA NUESTRA CARTA DIGITAL",
                           "Helvetica-Bold", 12, C_RED)
        # Subrayado dorado
        ul_y = TITLE_Y - 4*mm
        self.hline(cx - 46*mm, cx + 46*mm, ul_y, C_GOLD, 0.7)

        # ── TARJETA QR ──────────────────────────────────────────────────────
        self.draw_qr_card(cx, QR_CY, QR_SIZE)

        if os.path.exists(QR_IMG):
            self.drawImage(QR_IMG, cx - QR_SIZE/2, QR_CY - QR_SIZE/2,
                           width=QR_SIZE, height=QR_SIZE,
                           preserveAspectRatio=True, mask='auto')
        else:
            self.centered_text(cx, QR_CY, "[ QR no disponible ]",
                               "Helvetica", 10, C_SOFT)

        # ── DIVISOR 2 + INSTRUCCION ─────────────────────────────────────────
        self.ornamental_line(DIVIDER2_Y, 55*mm, C_RED)

        self.centered_text(cx, INST_Y,
                           "Apunta la camara de tu movil · Compatible iOS y Android",
                           "Helvetica", 8.5, C_SOFT)

        # ── PIE ─────────────────────────────────────────────────────────────
        # Linea dorada sobre la banda
        self.hline(18*mm, W - 18*mm, FOOT_H, C_GOLD, 0.8)

        # Banda roja
        self.fill(C_RED)
        self.rect(0, 0, W, FOOT_H, fill=1, stroke=0)

        # Textos del pie
        self.centered_text(cx, FOOT_H * 0.62, "!TE ESPERAMOS!",
                           "Helvetica-Bold", 11.5, C_WHITE)
        self.centered_text(cx, FOOT_H * 0.26,
                           "Carta Digital  ·  Bar Sergios  ·  Siguenos en redes",
                           "Helvetica", 7.5, C_PINK)

        self.showPage()
        self.save()


# ── Main ──────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("[*] Generando PDF...")
    flyer = Flyer(OUTPUT)
    flyer.build()
    print("[OK]", OUTPUT)
    if sys.platform == "win32":
        os.startfile(OUTPUT)
    elif sys.platform == "darwin":
        subprocess.run(["open", OUTPUT])
    else:
        subprocess.run(["xdg-open", OUTPUT])
