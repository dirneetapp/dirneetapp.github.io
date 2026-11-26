"""
exportar_imprimir.py  -  Bar Sergios  -  Carta para Imprimir
=============================================================
Genera Carta_Imprimir.docx con layout de pagina especifico
por seccion, segun las indicaciones del bar.

Paginas:
  1  Portada
  2  Desayunos                     (1 pagina, 1 col)
  3  Bocadillos + MiniBocadillos   (1 pagina, 2 col)
  4  Vermuts + Oferta Vermut       (1 pagina, 1 col)
  5  Tapeo Clasico                 (1 pagina, 1 col)
  6  Tapas + Tapa de Arroz         (1 pagina, 2 col)
  7  Torradas                      (1 pagina, 2 col)
  8  Tablas + Platos Especiales    (1 pagina, 1 col)
  9  Croquetas Sergio's            (1 pagina, 1 col)
 10  Croquetrio's Sergio's         (1 pagina, centrado, tarjetas 2x2)
 11  Postres                       (1 pagina, 1 col)
"""

import os, json, sys, subprocess, re

# ── Auto-instalar dependencias ──────────────────────────────────────────────────
def _install(pkg):
    subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

for _pkg, _mod in [("python-docx", "docx"), ("Pillow", "PIL")]:
    try:
        __import__(_mod)
    except ImportError:
        print(f"Instalando {_pkg}...")
        _install(_pkg)

from docx import Document
from docx.shared import Pt, Cm, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ── Rutas ───────────────────────────────────────────────────────────────────────
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
MENU_FILE = os.path.join(BASE_DIR, "menu.json")
WORD_OUT  = os.path.join(BASE_DIR, "Carta_Imprimir.docx")
LOGO_PATH = os.path.join(BASE_DIR, "assets", "sergios_logo.png")

# ── Paleta corporativa Bar Sergios (Blanco y Negro) ─────────────────────────────
C_RED   = RGBColor(0x1C, 0x1C, 0x1C)
C_GOLD  = RGBColor(0x44, 0x44, 0x44)
C_DARK  = RGBColor(0x1C, 0x1C, 0x1C)
C_MID   = RGBColor(0x44, 0x44, 0x44)
C_SOFT  = RGBColor(0x77, 0x77, 0x77)
C_WHITE = RGBColor(0xFF, 0xFF, 0xFF)

# ── Dimensiones de columna (cm) ─────────────────────────────────────────────────
# Ancho util total: 21 - 2*2 margenes = 17 cm
PAGE_W  = 17.0

# 1 columna: nombre | precio
C1_N, C1_P = 14.5, 2.5                       # 14.5 + 2.5 = 17.0

# 2 columnas: nombreIzq | precioIzq | nombreDer | precioDer
C2_N, C2_P, C2_P2 = 6.2, 2.0, 2.6           # 6.2+2.0+6.2+2.6 = 17.0


# ══════════════════════════════════════════════════════════════════════
#  Utilidades OXML
# ══════════════════════════════════════════════════════════════════════

def cell_bg(cell, hex6: str):
    """Color de fondo de celda."""
    tcPr = cell._tc.get_or_add_tcPr()
    shd  = OxmlElement("w:shd")
    shd.set(qn("w:val"),   "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"),  hex6)
    tcPr.append(shd)


def cell_borders(cell, sides: dict):
    """
    Aplica bordes a una celda.
    sides: dict con claves "top","bottom","left","right".
      - ausente / "none"  -> borde oculto (nil)
      - "single"          -> linea fina gris claro (E8E0D8)
      - dict con val/sz/color -> personalizado
    """
    tcPr = cell._tc.get_or_add_tcPr()
    bd   = OxmlElement("w:tcBorders")
    for s in ("top", "bottom", "left", "right"):
        spec = sides.get(s, "none")
        el   = OxmlElement(f"w:{s}")
        if isinstance(spec, dict):
            el.set(qn("w:val"),    spec.get("val",   "single"))
            el.set(qn("w:sz"),     str(spec.get("sz", 4)))
            el.set(qn("w:space"),  "0")
            el.set(qn("w:color"),  spec.get("color", "000000"))
        elif spec == "none":
            el.set(qn("w:val"), "nil")
        else:                              # "single" -> fina gris
            el.set(qn("w:val"),   "single")
            el.set(qn("w:sz"),    "2")
            el.set(qn("w:space"), "0")
            el.set(qn("w:color"), "D3D3D3")
        bd.append(el)
    tcPr.append(bd)


def gold_card_borders(cell, sz=8):
    """Borde dorado para tarjetas de Croquetrio's."""
    tcPr = cell._tc.get_or_add_tcPr()
    bd   = OxmlElement("w:tcBorders")
    for side in ("top", "bottom", "left", "right"):
        el = OxmlElement(f"w:{side}")
        el.set(qn("w:val"),   "single")
        el.set(qn("w:sz"),    str(sz))
        el.set(qn("w:space"), "0")
        el.set(qn("w:color"), "444444")
        bd.append(el)
    tcPr.append(bd)


def para_line_bottom(para, color: str, sz: int = 6):
    """Linea horizontal en el borde inferior del parrafo."""
    pPr  = para._p.get_or_add_pPr()
    pBdr = OxmlElement("w:pBdr")
    b    = OxmlElement("w:bottom")
    b.set(qn("w:val"),   "single")
    b.set(qn("w:sz"),    str(sz))
    b.set(qn("w:space"), "1")
    b.set(qn("w:color"), color)
    pBdr.append(b)
    pPr.append(pBdr)


def run(para, text, size, bold=False, italic=False,
        color: RGBColor = None, font="Arial"):
    r = para.add_run(text)
    r.font.name   = font
    r.font.size   = Pt(size)
    r.font.bold   = bold
    r.font.italic = italic
    if color:
        r.font.color.rgb = color
    return r


def ns(para):
    """Sin espacio antes/despues."""
    para.paragraph_format.space_before = Pt(0)
    para.paragraph_format.space_after  = Pt(0)


def clean(s: str) -> str:
    """Normaliza espacios multiples y tabulaciones."""
    return re.sub(r"[ \t]+", " ", s or "").strip()


def split_lines(s: str) -> list:
    """Divide descripcion en lineas separadas por 2+ espacios."""
    return [p.strip() for p in re.split(r"\s{2,}", s) if p.strip()]


# ══════════════════════════════════════════════════════════════════════
#  Cabecera y pie de pagina
# ══════════════════════════════════════════════════════════════════════

def build_header(doc: Document):
    hdr = doc.sections[0].header

    # Tabla 3 columnas: logo | titulo | vacio
    ht = hdr.add_table(1, 3, Cm(PAGE_W))
    ht.style = "Table Grid"

    widths = [Cm(3.0), Cm(10.5), Cm(3.5)]
    for ci, cell in enumerate(ht.rows[0].cells):
        cell.width = widths[ci]
        cell_borders(cell, {})                    # sin bordes
        cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER

    # Logo
    pl = ht.cell(0, 0).paragraphs[0]
    ns(pl)
    if os.path.exists(LOGO_PATH):
        pl.add_run().add_picture(LOGO_PATH, height=Cm(1.7))

    # Nombre del bar
    ct = ht.cell(0, 1)
    p1 = ct.paragraphs[0]
    p1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(p1)
    run(p1, "BAR SERGIOS", 15, bold=True, color=C_RED, font="Georgia")
    p2 = ct.add_paragraph()
    p2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(p2)
    run(p2, "Carta de Productos", 8, italic=True, color=C_SOFT)

    # Separador dorado (Gris en B&N)
    sep = hdr.add_paragraph()
    ns(sep)
    para_line_bottom(sep, "444444", sz=8)


def build_footer(doc: Document):
    ftr = doc.sections[0].footer
    p   = ftr.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(p)
    para_line_bottom(p, "444444", sz=4)
    run(p, "Bar Sergios  |  carta digital  |  2026",
        7, color=C_SOFT)


# ══════════════════════════════════════════════════════════════════════
#  Encabezados de seccion
# ══════════════════════════════════════════════════════════════════════

def cat_heading(doc: Document, name: str):
    """Banda roja de anchura completa con nombre en blanco."""
    tbl  = doc.add_table(1, 1)
    tbl.style = "Table Grid"
    cell = tbl.cell(0, 0)
    cell_bg(cell, "1C1C1C")
    cell_borders(cell, {})
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.paragraph_format.space_before = Pt(5)
    p.paragraph_format.space_after  = Pt(5)
    run(p, name.upper(), 12, bold=True, color=C_WHITE, font="Georgia")

    sep = doc.add_paragraph()
    ns(sep)
    sep.paragraph_format.space_after = Pt(3)
    para_line_bottom(sep, "444444", sz=4)


def sub_heading(doc: Document, name: str, before: int = 8):
    """Titulo de subcategoria en dorado (Gris en B&N)."""
    p = doc.add_paragraph()
    p.paragraph_format.space_before  = Pt(before)
    p.paragraph_format.space_after   = Pt(4)
    p.paragraph_format.keep_with_next = True
    run(p, f"  {name.upper()}  ", 9.5, bold=True, color=C_GOLD)
    para_line_bottom(p, "444444", sz=2)


# ══════════════════════════════════════════════════════════════════════
#  Relleno de celdas de items
# ══════════════════════════════════════════════════════════════════════

def fill_name(cell, item: dict, fn: float, fd: float, pad: float = 0.2):
    """Nombre + etiqueta NUEVO + descripcion."""
    p = cell.paragraphs[0]
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(0)
    p.paragraph_format.left_indent  = Cm(pad)
    run(p, item["name"], fn, bold=True, color=C_DARK)

    if item.get("tag_novedad"):
        r = p.add_run("  NUEVO")
        r.font.name = "Arial"
        r.font.size = Pt(7)
        r.font.bold = True
        r.font.color.rgb = C_RED

    desc = clean(item.get("description", ""))
    if desc:
        pd = cell.add_paragraph()
        pd.paragraph_format.space_before = Pt(0)
        pd.paragraph_format.space_after  = Pt(2)
        pd.paragraph_format.left_indent  = Cm(pad)
        run(pd, desc, fd, italic=True, color=C_SOFT)
    else:
        p.paragraph_format.space_after = Pt(2)


def fill_price(cell, item: dict, fn: float):
    """Precio alineado a la derecha."""
    cell.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
    p = cell.paragraphs[0]
    p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    p.paragraph_format.space_before = Pt(2)
    p.paragraph_format.space_after  = Pt(2)
    p.paragraph_format.right_indent = Cm(0.15)

    if item.get("multi_prices"):
        txt = "\n".join(
            f"{mp['name']}: {mp['price']:.2f} €"
            for mp in item["multi_prices"]
        )
        run(p, txt, fn - 1.5, color=C_MID)
    else:
        run(p, f"{item.get('price', 0):.2f} €", fn, bold=True, color=C_RED)


def row_style(row, fill: str):
    """Aplica fondo y borde inferior a todas las celdas del row."""
    for cell in row.cells:
        cell_bg(cell, fill)
        cell_borders(cell, {"bottom": "single"})


# ══════════════════════════════════════════════════════════════════════
#  Tablas de items: 1 columna
# ══════════════════════════════════════════════════════════════════════

def items_1col(doc: Document, items: list, fn: float = 10.5, fd: float = 8.5):
    vis = [i for i in items if not i.get("hidden")]
    if not vis:
        return

    tbl = doc.add_table(rows=0, cols=2)
    tbl.style = "Table Grid"
    tbl.autofit = False
    tbl.allow_autofit = False

    for idx, item in enumerate(vis):
        row = tbl.add_row()
        row.cells[0].width = Cm(C1_N)
        row.cells[1].width = Cm(C1_P)
        row_style(row, "F2F2F2" if idx % 2 == 0 else "FFFFFF")
        fill_name(row.cells[0], item, fn, fd)
        fill_price(row.cells[1], item, fn)

    gap = doc.add_paragraph()
    gap.paragraph_format.space_after = Pt(4)


# ══════════════════════════════════════════════════════════════════════
#  Tablas de items: 2 columnas
# ══════════════════════════════════════════════════════════════════════

def items_2col(doc: Document, items: list, fn: float = 9.5, fd: float = 8.0):
    vis = [i for i in items if not i.get("hidden")]
    if not vis:
        return

    tbl = doc.add_table(rows=0, cols=4)
    tbl.style = "Table Grid"
    tbl.autofit = False
    tbl.allow_autofit = False

    for pair_idx, base in enumerate(range(0, len(vis), 2)):
        il = vis[base]
        ir = vis[base + 1] if base + 1 < len(vis) else None

        row = tbl.add_row()
        row.cells[0].width = Cm(C2_N)
        row.cells[1].width = Cm(C2_P)
        row.cells[2].width = Cm(C2_N)
        row.cells[3].width = Cm(C2_P2)

        fill = "F2F2F2" if pair_idx % 2 == 0 else "FFFFFF"
        row_style(row, fill)

        fill_name(row.cells[0], il, fn, fd, pad=0.15)
        fill_price(row.cells[1], il, fn)
        if ir:
            fill_name(row.cells[2], ir, fn, fd, pad=0.15)
            fill_price(row.cells[3], ir, fn)

    gap = doc.add_paragraph()
    gap.paragraph_format.space_after = Pt(4)


# ══════════════════════════════════════════════════════════════════════
#  Pagina especial: Croquetrio's  (centrada, tarjetas 2x2)
# ══════════════════════════════════════════════════════════════════════

def croquetrios_page(doc: Document, items: list):
    """4 surtidos en tarjetas de 1 columna centradas en la pagina."""
    vis = [i for i in items if not i.get("hidden")]

    # Espacio superior para centrar verticalmente el bloque
    for _ in range(3):
        p = doc.add_paragraph()
        ns(p)

    # Titulo principal
    pt = doc.add_paragraph()
    pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(pt)
    pt.paragraph_format.space_after = Pt(2)
    run(pt, "CROQUETRIO'S SERGIO'S", 18, bold=True, color=C_RED, font="Georgia")

    ps = doc.add_paragraph()
    ps.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(ps)
    ps.paragraph_format.space_after = Pt(3)
    run(ps, u"\u2015" * 28, 8, color=C_GOLD)

    pp = doc.add_paragraph()
    pp.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(pp)
    pp.paragraph_format.space_after = Pt(12)
    run(pp, "Combos de Croquetas Artesanas", 9.5, italic=True, color=C_SOFT)

    # Tarjetas 1 columna centrado
    card_w = Cm(11.0)

    for idx, item in enumerate(vis):
        tbl = doc.add_table(rows=1, cols=1)
        tbl.style = "Table Grid"
        tbl.autofit = False
        tbl.allow_autofit = False
        tbl.alignment = WD_TABLE_ALIGNMENT.CENTER

        cell = tbl.cell(0, 0)
        cell.width = card_w
        gold_card_borders(cell, sz=8)
        cell_bg(cell, "FFFFFF")

        # Nombre
        p_n = cell.paragraphs[0]
        p_n.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p_n.paragraph_format.space_before = Pt(8)
        p_n.paragraph_format.space_after  = Pt(4)
        run(p_n, item["name"].upper(), 10.5, bold=True,
            color=C_RED, font="Georgia")

        # Ingredientes (cada croqueta en su linea)
        for line in split_lines(item.get("description", "")):
            pd = cell.add_paragraph()
            pd.alignment = WD_ALIGN_PARAGRAPH.CENTER
            pd.paragraph_format.space_before = Pt(1)
            pd.paragraph_format.space_after  = Pt(1)
            run(pd, line, 9, italic=True, color=C_MID)

        # Precio
        pp2 = cell.add_paragraph()
        pp2.alignment = WD_ALIGN_PARAGRAPH.CENTER
        pp2.paragraph_format.space_before = Pt(4)
        pp2.paragraph_format.space_after  = Pt(8)
        run(pp2, f"{item.get('price', 0):.2f} €",
            12.5, bold=True, color=C_RED)

        # Añadir espacio entre tarjetas
        if idx < len(vis) - 1:
            p_space = doc.add_paragraph()
            ns(p_space)
            p_space.paragraph_format.space_after = Pt(8)

    # Espacio inferior
    for _ in range(2):
        p = doc.add_paragraph()
        ns(p)


# ══════════════════════════════════════════════════════════════════════
#  Portada
# ══════════════════════════════════════════════════════════════════════

def cover_page(doc: Document):
    for _ in range(5):
        p = doc.add_paragraph()
        ns(p)

    if os.path.exists(LOGO_PATH):
        pl = doc.add_paragraph()
        pl.alignment = WD_ALIGN_PARAGRAPH.CENTER
        ns(pl)
        pl.paragraph_format.space_after = Pt(16)
        pl.add_run().add_picture(LOGO_PATH, height=Cm(5.2))

    pt = doc.add_paragraph()
    pt.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(pt)
    pt.paragraph_format.space_after = Pt(6)
    run(pt, "BAR SERGIOS", 38, bold=True, color=C_RED, font="Georgia")

    ps = doc.add_paragraph()
    ps.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(ps)
    ps.paragraph_format.space_after = Pt(18)
    run(ps, "Carta de Productos", 14, italic=True, color=C_GOLD)

    pl2 = doc.add_paragraph()
    pl2.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(pl2)
    pl2.paragraph_format.space_after = Pt(8)
    run(pl2, u"\u2015" * 32, 9, color=C_GOLD)

    ptg = doc.add_paragraph()
    ptg.alignment = WD_ALIGN_PARAGRAPH.CENTER
    ns(ptg)
    run(ptg, "Sabor autentico  -  Experiencia unica", 11,
        italic=True, color=C_SOFT)

    doc.add_page_break()


# ══════════════════════════════════════════════════════════════════════
#  Helpers de acceso al menu
# ══════════════════════════════════════════════════════════════════════

def get_cat(menu: dict, cat_id: str) -> dict:
    for c in menu.get("categories", []):
        if c["id"] == cat_id:
            return c
    print(f"  [AVISO] Categoria no encontrada: {cat_id}")
    return {}


def get_sub(cat: dict, sub_id: str) -> dict:
    for s in cat.get("subcategories", []):
        if s["id"] == sub_id:
            return s
    print(f"  [AVISO] Subcategoria no encontrada: {sub_id}")
    return {}


# ══════════════════════════════════════════════════════════════════════
#  Generacion del documento
# ══════════════════════════════════════════════════════════════════════

def generar_word(menu: dict, out_path: str):
    print("[*] Generando Carta_Imprimir.docx ...")
    doc = Document()

    # A4 vertical
    sec = doc.sections[0]
    sec.page_width      = Cm(21)
    sec.page_height     = Cm(29.7)
    sec.top_margin      = Cm(2.0)
    sec.bottom_margin   = Cm(1.8)
    sec.left_margin     = Cm(2.0)
    sec.right_margin    = Cm(2.0)
    sec.header_distance = Cm(0.7)
    sec.footer_distance = Cm(0.7)

    # Estilo base
    style = doc.styles["Normal"]
    style.font.name = "Arial"
    style.font.size = Pt(10)
    style.font.color.rgb = C_DARK

    build_header(doc)
    build_footer(doc)

    # ── Portada ─────────────────────────────────────────────────────────
    cover_page(doc)

    # ── Pagina 1: DESAYUNOS ─────────────────────────────────────────────
    # 24 items, nombres largos -> 1 columna compacta
    cat = get_cat(menu, "Desayunos")
    cat_heading(doc, "Desayunos")
    items_1col(doc, cat.get("items", []), fn=9.5, fd=8.0)
    doc.add_page_break()

    # ── Pagina 2: BOCADILLOS + MINIBOCADILLOS ───────────────────────────
    # 19 + 18 items -> 1 columna
    cat_b = get_cat(menu, "Bocadillos")
    sub_mb = get_sub(cat_b, "MiniBocadillos")
    cat_heading(doc, "Bocadillos")
    items_1col(doc, cat_b.get("items", []), fn=9.0, fd=7.5)
    sub_heading(doc, "MiniBocadillos", before=6)
    items_1col(doc, sub_mb.get("items", []), fn=9.0, fd=7.5)
    doc.add_page_break()

    # ── Pagina 3: VERMUTS + OFERTA ESPECIAL ─────────────────────────────
    # 12 items con descripciones + 1 oferta -> 1 columna
    cat_v  = get_cat(menu, "Vermuts")
    sub_of = get_sub(cat_v, "OFERTA VERMUT")
    cat_heading(doc, "Vermuts")
    items_1col(doc, cat_v.get("items", []), fn=10.0, fd=8.5)
    sub_heading(doc, "Oferta Especial Vermut", before=6)
    items_1col(doc, sub_of.get("items", []), fn=10.0, fd=8.5)
    doc.add_page_break()

    # ── Pagina 4: TAPEO CLASICO ──────────────────────────────────────────
    # 11 items -> 1 columna con fuente mayor
    sub_tc = get_sub(cat_v, "Tapeo Clasico")
    cat_heading(doc, "Tapeo Clasico")
    items_1col(doc, sub_tc.get("items", []), fn=10.5, fd=8.5)
    doc.add_page_break()

    # ── Pagina 5: TAPAS + TAPA DE ARROZ ─────────────────────────────────
    # 26 + 3 items -> 1 columna
    cat_t  = get_cat(menu, "Tapas")
    cat_ar = get_cat(menu, "Arroz")
    cat_heading(doc, "Tapas")
    items_1col(doc, cat_t.get("items", []), fn=9.0, fd=7.5)
    sub_heading(doc, "Tapa de Arroz", before=6)
    items_1col(doc, cat_ar.get("items", []), fn=9.0, fd=7.5)
    doc.add_page_break()

    # ── Pagina 6: TORRADAS ───────────────────────────────────────────────
    # 22 items sin descripcion -> 1 columna
    cat_tor = get_cat(menu, "Torradas")
    cat_heading(doc, "Torradas")
    items_1col(doc, cat_tor.get("items", []), fn=9.5, fd=8.0)
    doc.add_page_break()

    # ── Pagina 7: TABLAS + PLATOS ESPECIALES ─────────────────────────────
    # 4 + 3 items -> 1 columna con fuente mayor
    cat_tab = get_cat(menu, "Tablas")
    cat_pe  = get_cat(menu, "Platos Especiales")
    cat_heading(doc, "Tablas y Platos Especiales")
    sub_heading(doc, "Tablas", before=4)
    items_1col(doc, cat_tab.get("items", []), fn=10.5, fd=8.5)
    sub_heading(doc, "Platos Especiales", before=6)
    items_1col(doc, cat_pe.get("items", []), fn=10.5, fd=8.5)
    doc.add_page_break()

    # ── Pagina 8: CROQUETAS SERGIO'S ─────────────────────────────────────
    # 17 items, nombres largos -> 1 columna compacta
    cat_cq = get_cat(menu, "Croquetas")
    cat_heading(doc, "Croquetas Sergio's")
    items_1col(doc, cat_cq.get("items", []), fn=9.5, fd=8.0)
    doc.add_page_break()

    # ── Pagina 9: CROQUETRIO'S SERGIO'S ─────────────────────────────────
    # 4 surtidos -> layout centrado con tarjetas 2x2
    sub_cqt = get_sub(cat_cq, "Croquetrio's Sergio's")
    croquetrios_page(doc, sub_cqt.get("items", []))
    doc.add_page_break()

    # ── Pagina 10: POSTRES ───────────────────────────────────────────────
    # 6 items -> 1 columna con fuente mayor
    cat_pos = get_cat(menu, "Postres")
    cat_heading(doc, "Postres")
    items_1col(doc, cat_pos.get("items", []), fn=10.5, fd=8.5)

    # Guardar
    doc.save(out_path)
    print(f"[OK] Guardado en: {out_path}")


# ══════════════════════════════════════════════════════════════════════
#  Entry point
# ══════════════════════════════════════════════════════════════════════

def main():
    if not os.path.exists(MENU_FILE):
        print(f"[ERROR] No se encuentra menu.json en: {MENU_FILE}")
        sys.exit(1)

    try:
        with open(MENU_FILE, "r", encoding="utf-8") as f:
            menu = json.load(f)
    except Exception as e:
        print(f"[ERROR] Leyendo menu.json: {e}")
        sys.exit(1)

    generar_word(menu, WORD_OUT)

    # Abrir automaticamente
    if sys.platform == "win32":
        os.startfile(WORD_OUT)
    elif sys.platform == "darwin":
        subprocess.run(["open", WORD_OUT])
    else:
        subprocess.run(["xdg-open", WORD_OUT])


if __name__ == "__main__":
    main()
