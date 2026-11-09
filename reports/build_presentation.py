"""Genera la presentación de Rolulabo en .pptx, lista para Google Slides.

    python reports/build_presentation.py

Sale entregables/Presentacion_Rolulabo.pptx. Al subirla a Google Drive se abre
como Google Slides. Todas las cifras se leen de reports/metrics.
Paleta amarillo y negro, tipografía Montserrat, gráficas nativas editables.
"""
from pptx import Presentation
from pptx.chart.data import CategoryChartData
from pptx.dml.color import RGBColor
from pptx.enum.chart import XL_CHART_TYPE, XL_LABEL_POSITION
from pptx.enum.shapes import MSO_CONNECTOR, MSO_SHAPE
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.oxml.ns import qn
from pptx.util import Inches, Pt

from build_report import (ATS, AUC_RANGE, AUTOR, BEST, CH, COST, ERR, REAL_MARGIN, REP, RULES, AV, CAPS, CROSS, CZ, DD, DEC,
                          DEC_HIGH, DL, GB, GROUPS, HERE, HYP, L, MOD, MODES, PROF, Q, RULE, S, SEGK, SIM, SIM_MARGIN, SIMSUB,
                          THR_SENS, WORST, X, money, parts, pct, sens)

FONT = "Montserrat"
BLACK, YELLOW, WHITE = RGBColor(0x11, 0x11, 0x11), RGBColor(0xF5, 0xC4, 0x00), RGBColor(0xFF, 0xFF, 0xFF)
CARD, GRAY, MID, SOFT, DARK2 = (RGBColor(0xF2, 0xF2, 0xF2), RGBColor(0x5E, 0x5E, 0x5E), RGBColor(0xA6, 0xA6, 0xA6),
                                RGBColor(0xD9, 0xD9, 0xD9), RGBColor(0x26, 0x26, 0x26))
W, H = 13.333, 7.5
LM = 0.6
CW = W - 2 * LM

prs = Presentation()
prs.slide_width, prs.slide_height = Inches(W), Inches(H)
BLANK = prs.slide_layouts[6]
PAGE = [1]
OPENERS, STATEMENTS = set(), set()   # láminas que abren bloque y láminas de impacto


# ---------------------------------------------------------------- helpers
def new_slide(bg=WHITE):
    s = prs.slides.add_slide(BLANK)
    s.background.fill.solid()
    s.background.fill.fore_color.rgb = bg
    PAGE[0] += 1
    return s


def rect(s, x, y, w, h, fill, shape=MSO_SHAPE.RECTANGLE, line=None):
    r = s.shapes.add_shape(shape, Inches(x), Inches(y), Inches(w), Inches(h))
    r.fill.solid()
    r.fill.fore_color.rgb = fill
    if line is None:
        r.line.fill.background()
    else:
        r.line.color.rgb = line
    r.shadow.inherit = False
    return r


def text(s, x, y, w, h, paras, size=14, color=BLACK, bold=False, align=PP_ALIGN.LEFT,
         anchor=MSO_ANCHOR.TOP, spacing=1.15, after=6, shape=None):
    """paras es un texto o una lista de textos; **negritas** en línea."""
    if isinstance(paras, str):
        paras = [paras]
    box = shape or s.shapes.add_textbox(Inches(x), Inches(y), Inches(w), Inches(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.vertical_anchor = anchor
    for i, ptxt in enumerate(paras):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        p.alignment = align
        p.line_spacing = spacing
        p.space_after = Pt(after)
        for t, b in parts(ptxt):
            r = p.add_run()
            r.text = t
            r.font.name, r.font.size, r.font.bold = FONT, Pt(size), b or bold
            r.font.color.rgb = color
    return box


def boxed(s, x, y, w, h, fill, paras, pad=0.25, **kw):
    r = rect(s, x, y, w, h, fill)
    tf = r.text_frame
    text(s, 0, 0, 0, 0, paras, shape=r, **kw)
    tf.margin_left = tf.margin_right = Inches(pad)
    tf.margin_top = tf.margin_bottom = Inches(pad * 0.8)
    return r


def header(s, eyebrow, title, dark=False):
    rect(s, LM, 0.6, 0.32, 0.09, YELLOW)
    text(s, LM + 0.45, 0.5, 9, 0.3, eyebrow.upper(), size=11, bold=True, color=MID if dark else GRAY)
    text(s, LM, 0.85, CW, 1.1, title, size=28, bold=True, color=WHITE if dark else BLACK, spacing=1.05)


def footer(s, src="", dark=False):
    c = MID if dark else GRAY
    if src:
        text(s, LM, 6.95, 10.8, 0.3, src, size=10, color=c)
    text(s, W - LM - 0.8, 6.95, 0.8, 0.3, str(PAGE[0]), size=10, bold=True,
         color=YELLOW if dark else BLACK, align=PP_ALIGN.RIGHT)


ICONS = HERE / "assets" / "icons"


def icon(s, name, tone, x, y, size):
    """Ícono Lucide pre-renderizado. tone k negro, y amarillo, w blanco."""
    return s.shapes.add_picture(str(ICONS / f"{name}_{tone}.png"), Inches(x), Inches(y), Inches(size), Inches(size))


ILLUS = HERE / "assets" / "illustrations"


def illus(s, name, x, y, w, h, align="center"):
    """Ilustración de unDraw (licencia libre) ajustada a una caja sin deformarla."""
    from PIL import Image
    path = ILLUS / f"{name}.png"
    iw, ih = Image.open(path).size
    k = min(w / iw, h / ih)
    pw, ph = iw * k, ih * k
    px = x + (w - pw) / 2 if align == "center" else (x + w - pw if align == "right" else x)
    py = y + (h - ph) / 2
    return s.shapes.add_picture(str(path), Inches(px), Inches(py), Inches(pw), Inches(ph))


def notes(s, t):
    s.notes_slide.notes_text_frame.text = t


def table(s, x, y, widths, rows, size=12, row_h=0.42, highlight=(), dark_rows=(), align_right_from=1, bold_first_col=False):
    nrows, ncols = len(rows), len(rows[0])
    gf = s.shapes.add_table(nrows, ncols, Inches(x), Inches(y), Inches(sum(widths)), Inches(row_h * nrows))
    tbl = gf.table
    sid = tbl._tbl.tblPr.find(qn("a:tableStyleId"))
    if sid is None:
        sid = tbl._tbl.tblPr.makeelement(qn("a:tableStyleId"), {})
        tbl._tbl.tblPr.append(sid)
    sid.text = "{2D5ABB26-0587-4C30-8999-92F81FD0307C}"
    for k, w in enumerate(widths):
        tbl.columns[k].width = Inches(w)
    for i, row in enumerate(rows):
        tbl.rows[i].height = Inches(row_h)
        for k, val in enumerate(row):
            cell = tbl.cell(i, k)
            cell.margin_left = cell.margin_right = Inches(0.08)
            cell.margin_top = cell.margin_bottom = Inches(0.03)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            if i == 0:
                fill, col, b = BLACK, YELLOW, True
            elif i in highlight:
                fill, col, b = YELLOW, BLACK, False
            elif i in dark_rows:
                fill, col, b = DARK2, WHITE, False
            else:
                fill, col, b = (WHITE if i % 2 else CARD), BLACK, False
            cell.fill.solid()
            cell.fill.fore_color.rgb = fill
            tf = cell.text_frame
            tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT if (align_right_from is not None and k >= align_right_from and i > 0) else PP_ALIGN.LEFT
            for t, bb in parts(str(val)):
                r = p.add_run()
                r.text = t
                r.font.name, r.font.size = FONT, Pt(size)
                r.font.bold = b or bb or (bold_first_col and k == 0) or (i in highlight)
                r.font.color.rgb = col
    return tbl


def chip(cell, label):
    """Pinta una celda como etiqueta de resultado."""
    confirm = label.startswith("Confirm")
    cell.fill.solid()
    cell.fill.fore_color.rgb = YELLOW if confirm else BLACK
    for r in cell.text_frame.paragraphs[0].runs:
        r.font.color.rgb = BLACK if confirm else YELLOW
        r.font.bold = True


def column_chart(s, x, y, w, h, cats, vals, colors, fmt, label_color, axis_color, font_size=11):
    cd = CategoryChartData()
    cd.categories = cats
    cd.add_series("Serie", vals)
    gf = s.shapes.add_chart(XL_CHART_TYPE.COLUMN_CLUSTERED, Inches(x), Inches(y), Inches(w), Inches(h), cd)
    ch = gf.chart
    ch.has_legend = False
    ch.has_title = False
    ch.font.name = FONT
    ch.font.size = Pt(font_size)
    plot = ch.plots[0]
    plot.gap_width = 45
    plot.has_data_labels = True
    dl = plot.data_labels
    dl.number_format, dl.number_format_is_linked = fmt, False
    dl.position = XL_LABEL_POSITION.OUTSIDE_END
    dl.font.size, dl.font.bold, dl.font.name = Pt(font_size), True, FONT
    dl.font.color.rgb = label_color
    ser = plot.series[0]
    for i, c in enumerate(colors):
        pt = ser.points[i]
        pt.format.fill.solid()
        pt.format.fill.fore_color.rgb = c
        pt.format.line.fill.background()
    va = ch.value_axis
    va.visible = False
    va.has_major_gridlines = False
    va.minimum_scale = 0
    ca = ch.category_axis
    ca.tick_labels.font.size, ca.tick_labels.font.name = Pt(font_size), FONT
    ca.tick_labels.font.color.rgb = axis_color
    ca.format.line.color.rgb = axis_color
    ca.has_major_gridlines = False
    return ch


def arrow(s, x1, y1, x2, y2, color=BLACK):
    c = s.shapes.add_connector(MSO_CONNECTOR.STRAIGHT, Inches(x1), Inches(y1), Inches(x2), Inches(y2))
    c.line.color.rgb = color
    c.line.width = Pt(2.25)
    ln = c.line._get_or_add_ln()
    tail = ln.makeelement(qn("a:tailEnd"), {"type": "triangle", "w": "med", "len": "med"})
    ln.append(tail)
    return c


# ---------------------------------------------------------------- datos
HY = {h["id"]: h for h in HYP["hipotesis"]}
SHORT = {
    "H1": f"{Q['combinaciones_con_un_solo_descuento']} de {Q['combinaciones_estado_subcategoria']} combinaciones estado y subcategoría tienen un solo descuento",
    "H2": f"rho = {HY['H2']['stats']['rho']:.3f}, p = {HY['H2']['stats']['p']:.2f}. Misma cantidad con 0% y con 80%",
    "H3": f"Pérdida de {pct(HY['H3']['stats']['min'])} a {pct(HY['H3']['stats']['max'])} por segmento, p = {HY['H3']['stats']['p']:.2f}, V = {HY['H3']['stats']['v']:.2f}",
    "H4": f"Pérdida de {pct(HY['H4']['stats']['min'])} a {pct(HY['H4']['stats']['max'])} por trimestre, p = {HY['H4']['stats']['p']:.2f}",
    "H5": f"{DL['pruebas_significativas']} de {len(DL['pruebas_chi2'])} pruebas significativas, AUC de {AUC_RANGE}",
    "H6": f"Inactivos {pct(HY['H6']['stats']['inactivos'], 0)} de pedidos tarde contra {pct(HY['H6']['stats']['activos'], 0)} de los activos, p una cola = {HY['H6']['stats']['p_una_cola']:.2f}",
    "H7": f"Ventas contra margen rho = {HY['H7']['stats']['rho_ventas']:.2f}. Descuento contra margen rho = {HY['H7']['stats']['rho_descuento']:.2f}",
    "H8": f"F1 {GB['f1']:.3f} contra {RULE['f1']:.3f}, intervalos de 95% sin traslape",
}
import csv  # noqa: E402

qty = {}
with open(HERE.parent / "data" / "processed" / "lines.csv", encoding="utf-8") as f:
    for r in csv.DictReader(f):
        d = float(r["discount"])
        n, s_, k = qty.get(d, (0, 0, 0))
        qty[d] = (n + 1, s_ + int(r["quantity"]), k + int(r["is_loss"]))
DISC = sorted(qty)

# ---------------------------------------------------------------- 1 portada
s = prs.slides.add_slide(BLANK)
s.background.fill.solid()
s.background.fill.fore_color.rgb = BLACK
rect(s, LM, 0.75, 0.45, 0.12, YELLOW)
text(s, LM + 0.65, 0.66, 10, 0.3, "PROYECTO INTEGRADOR · APRENDIZAJE DE MÁQUINA", size=12, bold=True, color=YELLOW)
text(s, LM, 2.1, CW, 1.4, "Rolulabo", size=80, bold=True, color=WHITE)
rect(s, LM, 3.85, 1.6, 0.14, YELLOW)
text(s, LM, 4.2, 6.6, 1.2, "Vendemos más, pero cada venta deja menos de lo que podría. Diagnóstico y decisión con BI y aprendizaje de máquina", size=20, color=SOFT)
s.shapes.add_picture(str(HERE / "assets" / "portada.png"), Inches(7.75), Inches(1.35), height=Inches(4.75))
text(s, LM, 6.55, 8, 0.4, "Gabriel Álvarez · Eduardo Gutiérrez · Emiliano Luna · Rodrigo Naranjo", size=13, color=SOFT)
text(s, W - LM - 5, 6.55, 5, 0.4, "Universidad Panamericana · Noviembre 2026", size=13, color=SOFT, align=PP_ALIGN.RIGHT)
notes(s, "Presentación del equipo. Rolulabo es una cadena ficticia de artículos de oficina, muebles y tecnología en Estados Unidos. Datos de 2014 a 2017. La pregunta de fondo es por qué las ventas crecen 52% y el margen se queda estancado. La imagen muestra ventas por trimestre en gris y el margen en amarillo.")

# ---------------------------------------------------------------- 2 resumen
s = new_slide()
header(s, "Resumen ejecutivo", f"Recomendamos topes de descuento en 10 estados, que capturan el {pct(DEC_HIGH['delta_pct_del_total'], 0)} del beneficio posible")
boxed(s, LM, 2.15, 5.9, 4.45, BLACK, [
    "**DECISIÓN**",
    "Aplicar topes de descuento por subcategoría en los 10 estados de descuento alto, en dos olas de cinco estados que funcionan como experimento controlado.",
    "Extender al resto del país solo si se cumplen los criterios de éxito en la semana 15.",
], size=17, color=WHITE, after=14, pad=0.4)
r = s.shapes[-1]
r.text_frame.paragraphs[0].runs[0].font.color.rgb = YELLOW
r.text_frame.paragraphs[0].runs[0].font.size = Pt(13)
kp = [(f"{money(DEC_HIGH['utilidad_real'])}  a  {money(DEC_HIGH['utilidad_con_topes'])}", "utilidad 2017 de los 10 estados con topes, simulada con el costo real"),
      (f"{HYP['refutadas']} de 8", "creencias del negocio refutadas con datos antes de modelar"),
      (f"{GB['f1']:.3f} vs {RULE['f1']:.3f}", "F1 del modelo contra la regla actual para detectar líneas con pérdida")]
for i, (big, lab) in enumerate(kp):
    yy = 2.15 + i * 1.5
    rect(s, 6.9, yy, 0.1, 1.25, YELLOW)
    text(s, 7.2, yy, 5.5, 0.7, big, size=30, bold=True)
    text(s, 7.2, yy + 0.72, 5.5, 0.6, lab, size=13, color=GRAY)
footer(s, "Fuente. Sample Superstore 2014 a 2017, simulación sobre 2017")
notes(s, "Empezamos por la conclusión. La decisión es corregir una tabla de descuentos en 10 estados. Todo lo que sigue es la evidencia que la sostiene.")

# ---------------------------------------------------------------- 3 problema
s = new_slide()
OPENERS.add(PAGE[0])
header(s, "01 · Comprensión del negocio", "Rolulabo vende más de $2 millones, pero casi una de cada cinco líneas pierde dinero")
cards = [("12.5%", "margen sobre $2.3M de ventas entre 2014 y 2017", CARD),
         (pct(Q["lineas_con_perdida_pct"]), "de las líneas de venta cerró con pérdida", YELLOW),
         ("$156K", "perdidos en esas líneas, el 35% de lo que ganaron las rentables", CARD)]
cw = (CW - 0.6) / 3
for i, (big, lab, fill) in enumerate(cards):
    xx = LM + i * (cw + 0.3)
    rect(s, xx, 2.2, cw, 2.6, fill)
    icon(s, ["CircleDollarSign", "TriangleAlert", "TrendingDown"][i], "k", xx + cw - 0.95, 2.45, 0.6)
    text(s, xx + 0.35, 2.5, cw - 0.7, 1.1, big, size=54, bold=True)
    text(s, xx + 0.35, 3.75, cw - 0.7, 0.9, lab, size=15, color=BLACK if fill == YELLOW else GRAY)
illus(s, "discount", 8.9, 4.95, 3.83, 1.85, align="right")
text(s, LM, 5.2, 7.9, 1.2, "Además, uno de cada tres pedidos llega después de lo prometido y la empresa trata igual a todos sus clientes. El objetivo es elevar la utilidad por transacción sin quitarle a Comercial el descuento como palanca de venta.", size=16)
footer(s, "Fuente. Sample Superstore, 9,994 líneas, 5,009 pedidos, 793 clientes")
notes(s, "Tres síntomas. Pérdidas por línea, entregas fuera de tiempo y una política comercial que no distingue clientes. Las pérdidas se detectan hasta el cierre contable.")

# ---------------------------------------------------------------- planteamiento y ODS
s = new_slide()
header(s, "01 · Planteamiento", "Un objetivo medible, con dueño en cada área y ligado al ODS 8")
sem_p95 = min(r["cumplimiento"] for r in DL["sensibilidad_promesa"] if r["escenario"] == "p95")
table(s, LM, 2.1, [3.2, 1.35, 1.55, 1.4], [
    ["KPI del objetivo", "Línea base", "Meta a un año", "Dueño"],
    ["Líneas con pérdida", pct(Q["lineas_con_perdida_pct"]), "Menos de 5%", "Finanzas"],
    ["Margen neto", pct(REAL_MARGIN), "Más de 20%", "Dirección"],
    ["Promesa de entrega cumplida", pct(1 - DD["global_fuera_de_tiempo_pct"]), "Más de 95%", "Operaciones"],
    ["Pedidos por cliente contra control", "Base", "Caída menor a 10%", "Comercial"]],
    size=13, row_h=0.52, align_right_from=None, bold_first_col=True)
text(s, LM, 4.95, 7.5, 1.7, [
    "**A quién beneficia.** Comercial y Finanzas deciden los descuentos, Operaciones la promesa de entrega, Marketing el presupuesto por cliente y Dirección aprueba la política.",
    f"**Por qué importa.** Las pérdidas se ven hasta el cierre contable. En simulación, los topes llevarían el margen de 2017 a {pct(SIM_MARGIN)}."], size=14, after=10)
boxed(s, 8.55, 2.1, W - LM - 8.55, 4.55, YELLOW, [
    "**ODS 8**", "**Trabajo decente y crecimiento económico, meta 8.2**",
    "La meta busca elevar la productividad con modernización tecnológica e innovación. El proyecto sube la utilidad por transacción con datos que la empresa ya tiene.",
    "La relación es indirecta y a nivel empresa. No usamos ODS ambientales porque los datos no traen consumo de recursos."], size=13, pad=0.3, after=8)
r = s.shapes[-1]
r.text_frame.paragraphs[0].runs[0].font.size = Pt(40)
footer(s, "Línea base de reports/metrics, margen de 2017 y el resto de 2014 a 2017. El piloto de la decisión verifica las metas")
notes(s, "La rúbrica pide un objetivo medible y ligarlo a un ODS solo si la relación es real. Nuestro objetivo son cuatro KPIs con dueño. El ODS 8.2 aplica porque mejoramos productividad de una empresa con analítica. Decimos con honestidad que la relación es indirecta y por qué no usamos ODS ambientales.")

# ---------------------------------------------------------------- 4 metodologia
s = new_slide()
header(s, "Metodología", "Seguimos CRISP-DM en tres iteraciones ágiles, cada una con un entregable que funciona")
phases = [("Negocio", "KPIs e historias de usuario"), ("Datos", "EDA y 8 hipótesis probadas"),
          ("Preparación", "ETL validado y modelo estrella"), ("Modelado", "Tres modelos, validación temporal"),
          ("Evaluación", "Contra línea base y simulación"), ("Despliegue", "Dashboard por área y monitoreo")]
bw = (CW - 5 * 0.15) / 6
for i, (ph, dl) in enumerate(phases):
    xx = LM + i * (bw + 0.15)
    rect(s, xx, 2.15, bw, 1.75, CARD)
    rect(s, xx + 0.2, 2.32, 0.52, 0.52, YELLOW, shape=MSO_SHAPE.OVAL)
    icon(s, ["Briefcase", "Search", "Wrench", "BrainCircuit", "ClipboardCheck", "Rocket"][i], "k", xx + 0.31, 2.43, 0.3)
    text(s, xx + 0.85, 2.42, 0.5, 0.35, str(i + 1), size=13, bold=True, color=GRAY)
    text(s, xx + 0.2, 2.95, bw - 0.35, 0.35, ph, size=14, bold=True)
    text(s, xx + 0.2, 3.3, bw - 0.35, 0.55, dl, size=11, color=GRAY, spacing=1.0)
tb = table(s, LM, 4.25, [2.4, 2.3, 3.1, 4.33], [
    ["Iteración", "Fases", "Entregable", "Qué cambió al cerrar"],
    ["1. Negocio y datos", "1, 2, 3", "ETL validado, EDA, hipótesis", "H1 cayó. Ya no es capacitar vendedores, es corregir una tabla"],
    ["2. Modelos", "4, 5", "Tres modelos contra línea base", "H5 cayó. Operaciones pasó de priorizar pedidos a ajustar la promesa"],
    ["3. Decisión y despliegue", "5, 6", "Simulación, dashboard, decisión", "H2 cayó. El riesgo de perder volumen con topes resultó bajo"]],
    size=11, row_h=0.5, align_right_from=None, bold_first_col=True)
footer(s, "Definición de terminado. Se regenera con un comando, se compara contra una línea base y está ligado a una decisión")
notes(s, "CRISP-DM nos dio las fases y el enfoque ágil el ritmo. Cada iteración termina con algo que funciona, y al cerrarla revisamos hipótesis. Cuando una cae, ajustamos el backlog. Eso pasó tres veces y cambió el proyecto.")

# ---------------------------------------------------------------- 5 backlog
s = new_slide()
header(s, "Metodología · Backlog", "Cada pregunta analítica nace de una historia de usuario de un área")
illus(s, "scrum-board", 10.0, 2.3, 2.73, 4.2)
tb = table(s, LM, 2.1, [4.5, 3.3, 1.4], [
    ["Historia de usuario", "Criterio de aceptación", "Estado"],
    ["Como gerente comercial quiero saber antes de cerrar si una línea perderá dinero, para ajustar el descuento", "Modelo mejor que la regla actual en F1, con intervalo de confianza", "Terminada"],
    ["Como director de finanzas quiero un tope de descuento por subcategoría con su impacto, para aprobar la política", "Topes calculados sin usar 2017 y simulados sobre 2017", "Terminada"],
    ["Como gerente de operaciones quiero saber qué pedidos llegarán tarde, para priorizarlos", "AUC mayor a 0.65 en 2017", "Replanteada"],
    ["Como gerente de marketing quiero grupos de clientes con su rentabilidad, para asignar presupuesto", "Grupos estables y con perfil accionable", "Terminada"],
    ["Como director general quiero una sola lectura de las causas, para decidir dónde actuar", "Decisión con opciones, impacto y criterios", "Terminada"]],
    size=11, row_h=0.72, align_right_from=None, highlight=(3,))
footer(s, "La historia de Operaciones se replanteó porque el AUC fue 0.5. Se entrega una promesa realista en su lugar")
notes(s, "Trabajamos como un equipo de producto. Cada área es un usuario con una historia y un criterio de aceptación. La de Operaciones no se cumplió y lo decimos tal cual, se replanteó con base en evidencia.")

# ---------------------------------------------------------------- datos y calidad
s = new_slide()
OPENERS.add(PAGE[0])
header(s, "02 · Datos y calidad", "Datos públicos y limpios, con sus atípicos y sesgos a la vista")
table(s, LM, 2.1, [3.7, 2.3], [
    ["Validación", "Resultado"],
    ["Fuente", "Superstore, Kaggle"],
    ["Líneas y columnas", f"{Q['filas_crudas']:,} y 21"],
    ["Valores faltantes", str(Q["nulos_totales"])],
    ["Duplicados exactos", f"{Q['duplicados_exactos_eliminados']}, eliminado"],
    ["Pedidos inconsistentes", str(Q["pedidos_inconsistentes"])],
    ["Product ID para dos productos", f"{Q['product_id_reutilizados']}, llave ID y nombre"],
    ["Costo constante por producto", "Sí, pérdida determinista"]],
    size=13, row_h=0.5, align_right_from=None, bold_first_col=True)
at = ATS["atipicos_iqr"]
boxed(s, 7.0, 2.1, W - LM - 7.0, 1.95, CARD, [
    "**ATÍPICOS**",
    f"{pct(at['sales']['atipicos_pct'])} de las ventas y {pct(at['profit']['atipicos_pct'])} de las utilidades por línea están fuera del rango de Tukey. Son ventas reales y no se eliminan. Precio en logaritmo, modelos de árboles y margen recortado en p1 y p99."],
    size=13, pad=0.3, after=6)
boxed(s, 7.0, 4.25, W - LM - 7.0, 2.35, BLACK, [
    "**SESGOS**",
    f"Representatividad, West {pct(REP['region']['West'], 0)} de las líneas y South {pct(REP['region']['South'], 0)}. Confusión, el descuento es fijo por estado y subcategoría. Selección, solo hay ventas cerradas y no se ve a quien no compró. Datos sintéticos."],
    size=13, color=WHITE, pad=0.3, after=6)
r = s.shapes[-1]
r.text_frame.paragraphs[0].runs[0].font.color.rgb = YELLOW
footer(s, "Validaciones en src/etl.py, resultado en reports/metrics/data_quality.json. Fuente kaggle.com/datasets/vivek468/superstore-dataset-final")
notes(s, "Antes de modelar validamos los datos. Casi no hay que limpiar, pero hay dos hallazgos que importan. La pérdida es determinista porque el costo es fijo por producto, y el descuento es una tabla por estado. Los atípicos son ventas reales, por eso se manejan con transformaciones y no se borran. Los sesgos limitan qué podemos afirmar, sobre todo el de selección, que impide medir elasticidad.")

# ---------------------------------------------------------------- 6 hipotesis
s = new_slide()
header(s, "Comprensión de los datos · Hipótesis", f"{HYP['refutadas']} de 8 creencias del negocio resultaron falsas al probarlas con datos")
rows = [["", "Creencia del negocio", "Evidencia", "Resultado"]]
for hid in ["H1", "H2", "H3", "H4", "H5", "H6", "H7", "H8"]:
    rows.append([hid, HY[hid]["creencia"], SHORT[hid], HY[hid]["resultado"]])
tb = table(s, LM, 1.95, [0.6, 5.1, 5.0, 1.43], rows, size=11, row_h=0.52, align_right_from=None, bold_first_col=True)
for i in range(1, 9):
    chip(tb.cell(i, 3), rows[i][3])
footer(s, "Cada veredicto sale de un criterio fijado antes, alfa 0.05. Spearman, Kruskal-Wallis, chi-cuadrada, Mann-Whitney, Bonferroni y bootstrap")
notes(s, "Antes de modelar escribimos lo que el negocio daba por cierto y lo probamos. Una hipótesis refutada vale tanto como una confirmada porque evita invertir en la solución equivocada. La única que se confirmó es que el modelo sí le gana a la regla.")

# ---------------------------------------------------------------- 7 politica (dark)
s = new_slide(BLACK)
STATEMENTS.add(PAGE[0])
header(s, "Insight 1 · H1 refutada", "La pérdida es una política, no un error del vendedor", dark=True)
for i, (lab, big, sub) in enumerate([
        ("EL DESCUENTO ES UNA TABLA", "656 de 656 combinaciones de estado y subcategoría tienen un solo descuento", "El vendedor no decide, hereda. Illinois, Texas, Pennsylvania y Ohio promedian de 32% a 39%."),
        ("LA PÉRDIDA ES DETERMINISTA", "Una línea pierde cuando el descuento supera 1 menos costo entre precio", "Esa regla explica el 100% de las pérdidas y permite simular cualquier política.")]):
    yy = 2.1 + i * 1.95
    rect(s, LM, yy, 0.1, 1.75, YELLOW)
    text(s, LM + 0.35, yy, 5.6, 0.3, lab, size=11, bold=True, color=YELLOW)
    text(s, LM + 0.35, yy + 0.35, 5.6, 0.8, big, size=18, bold=True, color=WHITE)
    text(s, LM + 0.35, yy + 1.15, 5.6, 0.6, sub, size=13, color=SOFT)
text(s, LM, 6.05, 6.0, 0.7, f"Los 10 estados en amarillo concentran el **{pct(X['perdida_en_estados_alto_descuento_pct'], 0)}** de las pérdidas con {pct(X['lineas_en_estados_alto_descuento_pct'], 0)} de las líneas.", size=14, color=WHITE)
s.shapes.add_picture(str(HERE / "assets" / "mapa_estados.png"), Inches(6.85), Inches(2.05), width=Inches(5.85))
footer(s, "En amarillo, estados con descuento promedio mayor a 25% y su pérdida bruta 2014 a 2017", dark=True)
notes(s, "Este es el giro del proyecto. Pensábamos que los vendedores daban descuentos a criterio. Los datos dicen que el descuento viene de una tabla regional. La recomendación se vuelve muy concreta, reescribir la tabla.")

# ---------------------------------------------------------------- 8 chart loss (dark)
s = new_slide(BLACK)
STATEMENTS.add(PAGE[0])
header(s, "Insight 1 · Evidencia", "Arriba de 20% de descuento casi todas las líneas pierden dinero", dark=True)
cats = [pct(d, 0) for d in DISC]
vals = [qty[d][2] / qty[d][0] for d in DISC]
column_chart(s, LM, 2.05, CW, 4.6, cats, vals, [YELLOW if d >= 0.3 else RGBColor(0x5A, 0x5A, 0x5A) for d in DISC],
             "0%", WHITE, MID, font_size=13)
footer(s, "Proporción de líneas con pérdida por nivel de descuento, 2014 a 2017. Eje horizontal, descuento aplicado", dark=True)
notes(s, "Con 0% ninguna línea pierde. Con 20% pierde el 14%, la zona gris que depende del producto. De 30% en adelante pierden entre 87% y 100%.")

# ---------------------------------------------------------------- 9 H2
s = new_slide()
header(s, "Insight 2 · H2 refutada", "El descuento no compra volumen, el cliente lleva lo mismo con 0% que con 80%")
qv = [qty[d][1] / qty[d][0] for d in DISC]
column_chart(s, LM, 2.05, 8.3, 4.55, cats, qv, [BLACK] * len(DISC), "0.0", BLACK, GRAY, font_size=12)
rect(s, 9.3, 2.15, 3.43, 4.4, YELLOW)
text(s, 9.6, 2.45, 2.9, 0.4, "CORRELACIÓN DE SPEARMAN", size=11, bold=True)
text(s, 9.6, 2.85, 2.9, 0.9, f"rho = {HY['H2']['stats']['rho']:.3f}", size=30, bold=True)
text(s, 9.6, 3.75, 2.9, 0.5, f"p = {HY['H2']['stats']['p']:.2f}, Kruskal-Wallis p = {HY['H2']['stats']['kruskal_p']:.2f}", size=12)
text(s, 9.6, 4.45, 2.9, 1.9, "Quitar descuento donde genera pérdida tiene poco riesgo de perder ventas. Es la objeción principal a los topes y los datos no la sostienen.", size=13)
footer(s, "Unidades promedio por línea según nivel de descuento, 2014 a 2017")
notes(s, "La objeción natural a los topes es que vamos a vender menos. Los datos dicen que la cantidad por línea no cambia con el descuento. Ojo, el dataset no registra a quien no compró, por eso la decisión incluye un piloto con grupo de control.")

# ---------------------------------------------------------------- 10 modelos
s = new_slide()
OPENERS.add(PAGE[0])
header(s, "03 · Modelado y evaluación", f"El {BEST.lower()} supera a la regla de negocio en F1 y PR-AUC")
text(s, LM, 1.95, 9.2, 0.6, "Sin utilidad, margen ni costo para evitar fuga. Entrenamiento 2014 a 2016, prueba 2017. Hiperparámetros y umbral con validación cruzada temporal.", size=13, color=GRAY)
mr = lambda n, lab: [lab, f"{MOD[n]['pr_auc']:.3f}", f"{MOD[n]['f1']:.3f}", f"{MOD[n]['precision']:.3f}", f"{MOD[n]['recall']:.3f}", pct(MOD[n]['perdida_detectada_pct'], 0)]
illus(s, "predictive-analytics", 9.95, 2.5, 2.78, 4.2)
table(s, LM, 2.6, [3.3, 1.1, 1.1, 1.2, 1.1, 1.2], [
    ["Modelo", "PR-AUC", "F1", "Precisión", "Recall", "Pérdida detectada"],
    mr("Regla descuento > 20%", "Regla descuento mayor a 20%"),
    mr("Regresion logistica", "Regresión logística"),
    mr("Arbol de decision", "Árbol de decisión"),
    mr("Random forest", "Random forest"),
    mr(BEST, f"{BEST}, elegido"),
    mr("Regla costo histórico", "Regla con costo histórico, sin ML")], size=12, row_h=0.5, highlight=(5,), dark_rows=(6,))
footer(s, f"IC 95% de F1 por bootstrap. Modelo {L['ic95_modelo_elegido']['f1_ic95'][0]:.3f} a {L['ic95_modelo_elegido']['f1_ic95'][1]:.3f}, regla {L['ic95_regla']['f1_ic95'][0]:.3f} a {L['ic95_regla']['f1_ic95'][1]:.3f}. La última fila es referencia, usa el costo del producto")
notes(s, f"La línea base importante es la regla de negocio, no el azar. El {BEST.lower()} se eligió por PR-AUC en validación cruzada, sin ver la prueba, y también gana en prueba. Validación {GB['cv_pr_auc']:.3f}, prueba {GB['pr_auc']:.3f}, sin sobreajuste. Los intervalos no se traslapan. La última fila es honesta, una regla que usa el costo de cada producto le gana a todos los modelos porque la pérdida es determinista. La explicamos en la lámina de errores.")

# ---------------------------------------------------------------- 11 donde
s = new_slide()
header(s, "Insight 3 · H8 confirmada", "El modelo encuentra las pérdidas que la regla no ve con 20% de descuento")
d20 = L["descuento_20"]
for i, (big, lab, fill, col) in enumerate([
        (str(d20["perdidas"]), f"pérdidas en 2017 con exactamente 20% de descuento, de {d20['lineas']:,} líneas", CARD, BLACK),
        ("0", "detectadas por la regla de negocio", CARD, MID),
        (str(d20["modelo_detecta"]), f"detectadas por el modelo, con {d20['modelo_falsos_positivos']} falsas alarmas", YELLOW, BLACK)]):
    xx = LM + i * (cw + 0.3)
    rect(s, xx, 2.2, cw, 2.7, fill)
    text(s, xx + 0.35, 2.5, cw - 0.7, 1.2, big, size=66, bold=True, color=col)
    text(s, xx + 0.35, 3.85, cw - 0.7, 0.9, lab, size=15, color=BLACK if fill == YELLOW else GRAY)
text(s, LM, 5.25, CW, 0.9, f"Importancia por permutación. Descuento {L['importancia_permutacion']['discount']:.2f}, subcategoría {L['importancia_permutacion']['sub_category']:.2f}, precio {L['importancia_permutacion']['log_list_price']:.2f}. Región, segmento y envío no aportan, la pérdida depende del producto y del descuento.", size=15)
footer(s, "Fuente. reports/metrics/loss_model.json, prueba 2017")
notes(s, "Con 20% pierden Storage, Bookcases, Supplies y Tables, pero no Paper, Binders ni Art. Eso es lo que la regla no puede capturar.")

# ---------------------------------------------------------------- errores y robustez
s = new_slide()
header(s, "Evaluación · Errores y robustez", "Dónde falla el modelo, qué tan firme es y cuándo no hace falta")
cols3 = [("DÓNDE SE EQUIVOCA", str(ERR["falsos_negativos"]),
          f"pérdidas no detectadas, el {pct(ERR['falsos_negativos_en_20_pct'], 0)} con 20% de descuento. Suman el {pct(ERR['falsos_negativos_monto_pct'])} del monto perdido. Las {ERR['falsos_positivos']} falsas alarmas tenían {money(ERR['falsos_positivos_utilidad'])} de utilidad.", CARD, BLACK, GRAY),
         ("QUÉ TAN FIRME ES", f"{THR_SENS['f1_min_umbral_mas_menos_010']:.3f} a {THR_SENS['f1_max_umbral_mas_menos_010']:.3f}",
          f"F1 si el umbral se mueve 0.10. Intervalo bootstrap de {L['ic95_modelo_elegido']['f1_ic95'][0]:.3f} a {L['ic95_modelo_elegido']['f1_ic95'][1]:.3f}. Los mismos números en cada corrida, una prueba automática lo exige.", CARD, BLACK, GRAY),
         ("CUÁNDO NO HACE FALTA", f"{COST['f1']:.3f}",
          f"F1 de una regla con el costo histórico de cada producto, sin ML. El {pct(CH['lineas_con_historial_pct'], 0)} de las líneas de 2017 tiene historial. Si el sistema expone el costo, se usa la regla.", BLACK, YELLOW, SOFT)]
for i, (lab, big, sub, bg, c1, c2) in enumerate(cols3):
    xx = LM + i * (cw + 0.3)
    rect(s, xx, 2.1, cw, 3.65, bg)
    text(s, xx + 0.35, 2.35, cw - 0.7, 0.3, lab, size=11, bold=True, color=c1 if bg == BLACK else GRAY)
    text(s, xx + 0.35, 2.75, cw - 0.7, 0.9, big, size=40 if len(big) < 8 else 30, bold=True, color=c1 if bg == BLACK else BLACK)
    text(s, xx + 0.35, 3.75, cw - 0.7, 1.9, sub, size=13, color=c2)
text(s, LM, 6.0, CW, 0.8, "**Lectura.** El modelo sirve donde no hay costo, como segundo método para fijar topes y para confirmar sin costo que la pérdida depende del descuento y la subcategoría. La decisión no depende del clasificador.", size=14)
footer(s, "Errores y sensibilidad en reports/metrics/loss_model.json, prueba 2017")
notes(s, f"Esta lámina responde la pregunta difícil. Un modelo puede tener excelente precisión y no ser lo más útil. Como la pérdida es determinista, una tabla con el costo de cada producto detecta casi todo. Lo decimos nosotros antes de que nos lo pregunten. El modelo se equivoca sobre todo con 20% de descuento y en montos chicos. Y la conclusión no depende del umbral exacto, el F1 casi no se mueve. En productos sin historial solo hubo {CH['perdidas_sin_historial']} pérdidas, muy pocas para afirmar que ahí el modelo gane.")

# ---------------------------------------------------------------- 12 topes
s = new_slide()
header(s, "Entregable para Comercial y Finanzas", "Ocho subcategorías concentran la utilidad que se recupera con topes")
cs = sorted(CAPS, key=lambda r: -float(SIMSUB[r["sub_category"]]["delta"]))[:8]
illus(s, "revenue-analysis", 9.85, 2.3, 2.88, 4.2)
table(s, LM, 2.0, [2.1, 1.35, 1.35, 1.5, 0.9, 1.8], [["Subcategoría", "Desc. promedio", "Desc. máximo", "Líneas con pérdida", "Tope", "Recupera 2017"]] +
      [[r["sub_category"], pct(float(r["descuento_prom_actual"]), 0), pct(float(r["descuento_max_actual"]), 0), pct(float(r["perdida_pct_hist"]), 0),
        "**" + pct(float(r["tope_recomendado"]), 0) + "**", money(float(SIMSUB[r["sub_category"]]["delta"]))] for r in cs],
      size=13, row_h=0.5)
footer(s, "Tope = menor entre el percentil 10 del descuento de equilibrio y el tope del modelo. Calculado solo con 2014 a 2016")
notes(s, "Dos métodos independientes, uno contable y otro aprendido por el modelo. Que coincidan en orden de magnitud es una prueba de consistencia. Las subcategorías con tope de 0% tienen productos que se venden casi al costo.")

# ---------------------------------------------------------------- 13 simulacion
s = new_slide()
header(s, "Evaluación de negocio", "Con topes, la utilidad de 2017 casi se duplica y conviene aun perdiendo volumen")
for i, (lab, a, b) in enumerate([("Utilidad 2017", "$93K", "$183K"), ("Líneas con pérdida", str(SIM["lineas_perdida_actual"]), str(SIM["lineas_perdida_simulada"]))]):
    yy = 2.2 + i * 1.8
    text(s, LM, yy, 5, 0.35, lab, size=13, bold=True, color=GRAY)
    text(s, LM, yy + 0.45, 2.1, 0.9, a, size=44, bold=True, color=MID)
    arrow(s, LM + 2.2, yy + 0.92, LM + 2.95, yy + 0.92)
    boxed(s, LM + 3.15, yy + 0.4, 2.5, 1.0, YELLOW, b, size=44, bold=True, pad=0.15, anchor=MSO_ANCHOR.MIDDLE, align=PP_ALIGN.CENTER)
text(s, LM, 5.95, 5.8, 0.5, f"El tope cambia {SIM['lineas_afectadas']} líneas, el {pct(SIM['lineas_afectadas_pct'], 0)} del año.", size=13, color=GRAY)
text(s, 7.0, 2.2, 5.7, 0.4, "Sensibilidad a pérdida de volumen", size=15, bold=True)
table(s, 7.0, 2.7, [3.4, 2.33], [["Volumen perdido en líneas afectadas", "Utilidad extra"]] +
      [[pct(e["perdida_volumen"], 0), "+" + money(e["delta_utilidad"])] for e in SIM["escenarios"]], size=13, row_h=0.5, highlight=(len(SIM["escenarios"]),))
text(s, 7.0, 5.85, 5.7, 0.7, f"Las líneas afectadas perdían {money(-SIM['utilidad_afectadas_antes'])} en conjunto. Aun perdiéndolas todas, la política conviene.", size=13, color=GRAY)
footer(s, "Utilidad recalculada con el costo unitario real de cada producto. Supuesto principal, volumen constante")
notes(s, "Como el costo es fijo por producto, la utilidad con otro descuento se calcula exacta. El supuesto débil es que la gente compra lo mismo con un precio neto más alto. H2 y la tabla de sensibilidad lo atacan.")

# ---------------------------------------------------------------- score regla decision
s = new_slide()
header(s, "Cómo se usa el modelo", "El modelo calcula, la regla recomienda y una persona decide")
steps3 = [("1 · SCORE", "Probabilidad de pérdida", "El gradient boosting la calcula al capturar el pedido", CARD, BLACK, GRAY),
          ("2 · REGLA", "Semáforo auditable", f"Rojo si supera el tope. Amarillo si el score pasa {RULES['umbral_score']:.2f}. Verde en otro caso", BLACK, YELLOW, SOFT),
          ("3 · DECISIÓN HUMANA", "Gerente comercial", "Ajusta, aprueba una excepción con justificación o rechaza. Queda en bitácora", YELLOW, BLACK, BLACK)]
bw3 = (CW - 2 * 0.6) / 3
for i, (lab, big, sub, bg, c1, c2) in enumerate(steps3):
    xx = LM + i * (bw3 + 0.6)
    rect(s, xx, 2.05, bw3, 2.3, bg)
    text(s, xx + 0.3, 2.25, bw3 - 0.6, 0.3, lab, size=11, bold=True, color=c1 if bg != CARD else GRAY)
    icon(s, ["Cpu", "ListChecks", "UserCheck"][i], "y" if bg == BLACK else "k", xx + bw3 - 0.85, 2.2, 0.55)
    text(s, xx + 0.3, 2.6, bw3 - 1.2, 0.8, big, size=18, bold=True, color=WHITE if bg == BLACK else BLACK, spacing=1.0)
    text(s, xx + 0.3, 3.45, bw3 - 0.6, 0.8, sub, size=12, color=c2)
    if i < 2:
        arrow(s, xx + bw3 + 0.08, 3.15, xx + bw3 + 0.52, 3.15)
sem = {r["semaforo"]: r for r in RULES["semaforo_2017"]}
illus(s, "informed-decision", 9.55, 4.6, 3.18, 2.2)
tb = table(s, LM, 4.65, [1.9, 1.6, 1.4, 1.8, 1.9], [["Semáforo 2017", "Líneas", "Por mes", "Tasa de pérdida", "Monto perdido"]] +
           [[k, f"{sem[k]['lineas']:,}", f"{sem[k]['lineas_por_mes']:.0f}", pct(sem[k]["tasa_perdida"], 0), pct(sem[k]["monto_perdida_pct"])] for k in ("Rojo", "Amarillo", "Verde")],
           size=13, row_h=0.45, bold_first_col=True)
footer(s, f"Revisión humana en {pct(RULES['decisiones_humanas_pct'], 0)} de las líneas, unas {RULES['decisiones_humanas_por_mes']:.0f} al mes, que cubren el {pct(RULES['perdida_cubierta_por_revision_pct'])} del monto perdido")
notes(s, f"Este punto es central. El modelo no decide nada. Da un score, una regla escrita lo traduce en semáforo y una persona decide. La carga es razonable, unas {RULES['decisiones_humanas_por_mes']:.0f} líneas al mes, y ahí está el {pct(RULES['perdida_cubierta_por_revision_pct'], 0)} del dinero perdido. Cada decisión queda registrada en el dashboard con responsable y justificación, lo que permite auditar excepciones. La misma lógica aplica a la política de descuentos, que aprueba Finanzas, y a la extensión nacional, que decide Dirección.")

# ---------------------------------------------------------------- 14 entregas
s = new_slide()
header(s, "Insight 4 · H5 y H6 refutadas", "El retraso no se puede predecir, el problema está en la promesa")
boxed(s, LM, 2.1, 4.2, 2.1, BLACK, [f"{DL['pruebas_significativas']} de {len(DL['pruebas_chi2'])}", f"pruebas chi-cuadrada significativas con Bonferroni. AUC de {AUC_RANGE} dentro de cada modalidad"], size=14, color=SOFT, pad=0.3)
r = s.shapes[-1]
r.text_frame.paragraphs[0].runs[0].font.size = Pt(44)
r.text_frame.paragraphs[0].runs[0].font.bold = True
r.text_frame.paragraphs[0].runs[0].font.color.rgb = YELLOW
icon(s, "Truck", "y", LM + 4.2 - 0.8, 2.3, 0.5)
text(s, LM, 4.4, 4.2, 1.1, f"Tampoco explica el abandono. Los clientes inactivos tuvieron menos retrasos ({pct(HY['H6']['stats']['inactivos'], 0)}) que los activos ({pct(HY['H6']['stats']['activos'], 0)}). Mejorar envíos no recupera clientes.", size=13)
illus(s, "delivery-truck", LM, 5.55, 4.2, 1.25, align="left")
table(s, 5.3, 2.1, [2.0, 1.35, 1.35, 1.4, 1.33], [["Modalidad", "Promesa hoy", "Cumple hoy", "Promesa nueva", "Cumpliría"]] +
      [[m, f"{DL['promesa_supuesta'][m]} días", pct(sens(m, 'actual'), 0), f"{int(-(-DD[m]['dias_p95'] // 1))} días", pct(sens(m, 'p95'), 0)] for m in MODES],
      size=13, row_h=0.55, highlight=(3,))
text(s, 5.3, 5.1, 7.4, 1.3, "Second Class tarda 4 o 5 días el 41% de las veces, lo que hoy se espera de Standard Class. Para poder predecir después hay que registrar transportista, almacén y fecha real de entrega.", size=14)
footer(s, "Promesa nueva = percentil 95 de días de envío por modalidad. Promesa actual es un supuesto del equipo")
notes(s, "Es un resultado negativo y lo presentamos como tal. Un modelo con AUC de 0.5 no sirve para priorizar pedidos. La recomendación para Operaciones es prometer lo que de hecho se cumple.")

# ---------------------------------------------------------------- 15 clientes
s = new_slide()
header(s, "Insight 5 · H7 refutada", "Vender mucho no es ser rentable, cuatro grupos y uno destruye margen")
gw = (CW - 0.6) / 4
styles = {"Alto valor rentable": (BLACK, YELLOW, WHITE, SOFT), "Cazadores de descuento": (YELLOW, BLACK, BLACK, BLACK),
          "Compradores ocasionales": (CARD, BLACK, BLACK, GRAY), "Inactivos": (CARD, BLACK, BLACK, GRAY)}
for i, g in enumerate(GROUPS):
    p = PROF[g]
    bg, numc, tc, sc = styles[g]
    xx = LM + i * (gw + 0.2)
    rect(s, xx, 2.1, gw, 4.45, bg)
    icon(s, {"Alto valor rentable": "Crown", "Cazadores de descuento": "Tag", "Compradores ocasionales": "ShoppingBag", "Inactivos": "Moon"}[g],
         "y" if bg == BLACK else "k", xx + gw - 0.8, 2.35, 0.5)
    text(s, xx + 0.3, 2.35, gw - 1.2, 0.8, g, size=17, bold=True, color=tc)
    text(s, xx + 0.3, 3.15, gw - 0.6, 0.8, str(p["clientes"]), size=44, bold=True, color=numc)
    text(s, xx + 0.3, 3.95, gw - 0.6, 0.3, "clientes", size=12, color=sc)
    text(s, xx + 0.3, 4.45, gw - 0.6, 2.0, [f"Margen {pct(p['margin'])}", f"Descuento {pct(p['avg_discount'])}",
                                         f"{pct(p['ventas_pct'], 0)} de las ventas", f"{pct(p['perdidas_pct'], 0)} de las pérdidas"], size=13, color=sc, after=4)
footer(s, f"K-Means sobre recencia, frecuencia, monto, margen y descuento. k = 4, silueta {SEGK[4]['silueta']:.2f}, ARI bootstrap {S['estabilidad']['ari_bootstrap_media']:.2f}")
notes(s, "El margen del cliente no se relaciona con cuánto compra, sino con el descuento que recibe. Los Cazadores compran casi tan seguido como el grupo de alto valor pero con el doble de descuento. Hacen el 60% de sus compras en los 10 estados de descuento alto.")

# ---------------------------------------------------------------- 16 insights
s = new_slide()
header(s, "Síntesis", "Seis insights, cada uno con su acción")
ins = [("La pérdida es una política", "Reescribir la tabla de descuentos de 10 estados"),
       ("El descuento no compra volumen", "Aplicar topes con un piloto que mida el efecto real"),
       ("Vender mucho no es ser rentable", "Ofrecer servicio y no precio a los Cazadores"),
       ("El modelo ve la zona gris del 20%", "Usarlo donde no hay costo del producto"),
       ("El retraso es un problema de promesa", "Prometer 3, 5 y 7 días y registrar entregas"),
       ("La segmentación oficial no sirve", "Presupuestar marketing con los cuatro grupos")]
iw, ih = (CW - 0.6) / 3, 2.1
for i, (t, a) in enumerate(ins):
    xx, yy = LM + (i % 3) * (iw + 0.3), 2.1 + (i // 3) * (ih + 0.25)
    rect(s, xx, yy, iw, ih, CARD)
    rect(s, xx + 0.3, yy + 0.3, 0.55, 0.55, YELLOW, shape=MSO_SHAPE.OVAL)
    icon(s, ["Table", "Percent", "ShoppingBag", "Target", "Truck", "Users"][i], "k", xx + 0.415, yy + 0.415, 0.32)
    text(s, xx + 1.0, yy + 0.32, iw - 1.25, 0.8, t, size=16, bold=True)
    text(s, xx + 1.0, yy + 1.15, iw - 1.25, 0.8, a, size=13, color=GRAY)
footer(s, "Cada insight sale de una hipótesis probada o de un modelo evaluado contra línea base")
notes(s, "Aquí juntamos todo. Seis insights, cada uno con una acción concreta y un responsable. Los primeros tres son los que mueven la utilidad.")

# ---------------------------------------------------------------- 17 opciones
s = new_slide()
OPENERS.add(PAGE[0])
header(s, "04 · Decisión de negocio", "Evaluamos tres opciones y recomendamos la C")
opts = DEC["opciones"]
table(s, LM, 2.05, [5.4, 2.6, 4.13], [["Opción", "Utilidad 2017 simulada", "Riesgo"]] +
      [[o["opcion"], money(o["utilidad_2017"]), o["riesgo"]] for o in opts], size=14, row_h=0.7, highlight=(3,), align_right_from=None)
illus(s, "business-decisions", 9.3, 5.0, 3.43, 1.8, align="right")
text(s, LM, 5.0, 8.4, 1.7, [f"**Por qué C y no B.** Captura el {pct(DEC_HIGH['delta_pct_del_total'], 0)} del beneficio con {DEC_HIGH['lineas_afectadas']} de las {SIM['lineas_afectadas']} líneas afectadas, y mide el efecto real en volumen antes de escalar. Mientras corre la primera ola, la segunda funciona como grupo de control. Es reversible porque solo cambia una tabla."], size=15)
footer(s, "Utilidad simulada con el costo real de 2017 y volumen constante")
notes(s, "La opción B da un poco más en papel, pero apuesta todo a un supuesto que no podemos verificar con estos datos. La C resuelve esa limitación con un experimento natural y conserva el 91% del beneficio.")

# ---------------------------------------------------------------- 18 decision (yellow)
s = new_slide(YELLOW)
STATEMENTS.add(PAGE[0])
rect(s, LM, 0.6, 0.32, 0.09, BLACK)
text(s, LM + 0.45, 0.5, 9, 0.3, "DECISIÓN", size=11, bold=True)
text(s, LM, 0.9, CW, 1.6, "Topes de descuento en los 10 estados de descuento alto, en dos olas, a partir del siguiente trimestre", size=32, bold=True, spacing=1.05)
steps = [("Semanas 1 a 2", "Finanzas aprueba la tabla y se carga en el sistema"), ("Semanas 3 a 8", "Ola 1 en cinco estados, los otros cinco de control"),
         ("Semanas 9 a 14", "Ola 2 en los cinco restantes"), ("Semana 15", "Dirección revisa y decide extender al país")]
sw = (CW - 0.6) / 4
for i, (t, d) in enumerate(steps):
    xx = LM + i * (sw + 0.2)
    boxed(s, xx, 2.85, sw, 1.65, BLACK, [f"**{t}**", d], size=13, color=WHITE, pad=0.25, after=6)
    r = s.shapes[-1]
    for run in r.text_frame.paragraphs[0].runs:
        run.font.color.rgb = YELLOW
text(s, LM, 4.85, CW / 2 - 0.2, 1.8, ["**Criterios de éxito**", "Líneas con pérdida menores a 5% en estados tratados. Pedidos por cliente sin caer más de 10% contra control. Margen positivo en los 10 estados."], size=14, after=6)
text(s, LM + CW / 2 + 0.2, 4.85, CW / 2 - 0.2, 1.8, ["**Criterio de alto**", "Si los pedidos por cliente caen más de 25% contra el control, se revisan los topes antes de la segunda ola. En paralelo, nueva promesa de entrega y campañas por grupo."], size=14, after=6)
text(s, W - LM - 0.8, 6.95, 0.8, 0.3, str(PAGE[0]), size=10, bold=True, align=PP_ALIGN.RIGHT)
notes(s, "Esta es la decisión que le pedimos a Dirección. Es concreta, tiene responsables, fechas, criterios de éxito y un criterio de alto. Si algo sale mal se detecta en la ola 1 y se corrige antes de escalar.")

# ---------------------------------------------------------------- 19 BI
s = new_slide()
OPENERS.add(PAGE[0])
header(s, "05 · Despliegue", "La solución vive como producto de BI con modelos integrados")
layers = [("Fuente", "Ventas del ERP, hoy el CSV"), ("ETL en Python", "Validación, limpieza y variables"),
          ("Modelo estrella", "fact_lineas y 4 dimensiones"), ("Modelos ML", "scikit-learn versionados"),
          ("Dashboard", "Una pestaña por área")]
lw = (CW - 4 * 0.45) / 5
for i, (t, d) in enumerate(layers):
    xx = LM + i * (lw + 0.45)
    rect(s, xx + lw / 2 - 0.3, 2.0, 0.6, 0.6, YELLOW, shape=MSO_SHAPE.OVAL)
    icon(s, ["Server", "RefreshCw", "Network", "BrainCircuit", "LayoutDashboard"][i], "k", xx + lw / 2 - 0.18, 2.12, 0.36)
    boxed(s, xx, 2.75, lw, 1.35, BLACK if i in (2, 4) else CARD, [f"**{t}**", d], size=13,
          color=WHITE if i in (2, 4) else BLACK, pad=0.2, after=6)
    if i < 4:
        arrow(s, xx + lw + 0.05, 3.42, xx + lw + 0.4, 3.42)
table(s, LM, 4.35, [3.0, 9.13], [["Monitoreo", "Regla"],
      ["Reentrenamiento", "Cada trimestre con datos nuevos, recalculando los topes"],
      ["Deriva", "Vigilar la distribución del descuento y del precio de lista"],
      ["Alerta de negocio", "Líneas con pérdida mayores a 5% en cualquier estado"],
      ["Alerta de modelo", "F1 del trimestre por debajo del de la regla simple"]], size=13, row_h=0.47, align_right_from=None, bold_first_col=True)
footer(s, "El modelo estrella se conecta igual a Power BI, Looker Studio o Tableau. data/processed/bi")
notes(s, "No entregamos un notebook aislado. Entregamos un flujo de BI con ML. ETL validado, modelo estrella, modelos versionados y un dashboard por área, más reglas de monitoreo para que el modelo no se degrade sin que nadie se entere.")

# ---------------------------------------------------------------- 20 limites
s = new_slide()
header(s, "Limitaciones y reproducibilidad", "Los límites están acotados y todo se regenera con un comando")
text(s, LM, 2.1, 6.5, 4.6, [
    "**Datos sintéticos.** La utilidad sale de una fórmula con costo fijo. Con fletes y devoluciones las métricas bajarían.",
    f"**El costo explica la pérdida.** Con el costo del producto una regla llega a F1 {COST['f1']:.3f}, el modelo no es indispensable.",
    "**Volumen por línea.** No vemos a quien no compró, por eso el piloto con grupo de control.",
    "**Promesa supuesta.** La recomendación usa la distribución real de días, no la tasa.",
    f"**Grupos con frontera difusa.** Silueta {SEGK[4]['silueta']:.2f}, los perfiles son tendencias.",
    "**Un país, cuatro años.** No se valida en otro mercado."], size=13, after=9)
boxed(s, 7.4, 2.1, 5.33, 4.4, BLACK, ["**Se regenera en 35 segundos**", "uv sync", "uv run python src/run_all.py",
                                       "uv run pytest -q", "Versiones fijas en uv.lock y una prueba que exige los mismos números en cada corrida. El notebook corre en Google Colab."],
      size=14, color=WHITE, pad=0.35, after=12)
r = s.shapes[-1]
r.text_frame.paragraphs[0].runs[0].font.color.rgb = YELLOW
for k in (1, 2, 3):
    for run in r.text_frame.paragraphs[k].runs:
        run.font.name = "Courier New"
footer(s, "Detalle en la sección 3.2 del reporte técnico")
notes(s, "Reconocemos que las métricas de clasificación son altas porque el dataset es sintético. El método se traslada, el nivel de desempeño no. Todo el pipeline se puede correr en vivo si el profesor lo pide.")

# ---------------------------------------------------------------- 21 cierre
s = new_slide(BLACK)
rect(s, LM, 0.75, 0.45, 0.12, YELLOW)
text(s, LM + 0.65, 0.66, 6, 0.3, "ROLULABO", size=12, bold=True, color=YELLOW)
text(s, LM, 2.2, CW, 1.2, "Preguntas", size=66, bold=True, color=WHITE)
rect(s, LM, 3.7, 1.6, 0.14, YELLOW)
rect(s, 7.55, 1.25, 5.18, 4.45, WHITE)
illus(s, "questions", 7.8, 1.5, 4.68, 3.95)
text(s, LM, 4.05, 6.5, 1.2, "Menos descuento donde no se paga, una promesa de entrega honesta y una estrategia distinta para cada grupo de clientes.", size=20, color=SOFT)
text(s, LM, 5.5, CW, 0.4, f"Elaborado por {AUTOR}", size=14, bold=True, color=YELLOW)
text(s, LM, 6.3, CW, 0.7, "Herramientas e IA. Python, scikit-learn y uv. Claude (Anthropic) como asistente para código, revisión metodológica y borradores. Las decisiones, la ejecución y la interpretación son del equipo, y las verificaciones están en la Declaración de herramientas. Datos, Sample Superstore, Kaggle.", size=11, color=MID)
notes(s, "Cerrar con la idea central y abrir a preguntas. Tener a la mano el dashboard y el notebook.")

# ---------------------------------------------------------------- movimiento
from pptx_motion import animate, transition  # noqa: E402

for n, sl in enumerate(prs.slides, 1):
    if n == 1:
        transition(sl, "fade_black")
    elif n in OPENERS:
        transition(sl, "push")
    elif n in STATEMENTS:
        transition(sl, "wipe")
    else:
        transition(sl, "fade")
    animate(sl)

out = HERE.parent / "entregables" / "Presentacion_Rolulabo.pptx"
out.parent.mkdir(exist_ok=True)
prs.save(out)
print("Presentación lista", out, len(prs.slides), "diapositivas")
