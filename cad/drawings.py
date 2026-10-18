#!/usr/bin/env python3
"""ManipMasta - tavole costruttive 2D (A3) + DXF per taglio laser.

Output:
  cad/drawings/ManipMasta_tavole.pdf     tutte le tavole, A3 orizzontale
  cad/drawings/png/Txx_*.png             anteprime
  cad/dxf/*.dxf                          profili lamiere per taglio laser (quote reali, mm)

Le quote dipendono da cad/params.json (stesso modello di cad/model.py).
Le forature per componenti commerciali (pattini, supporti, chiocciole) sono marcate [V]:
vanno verificate sul datasheet del pezzo effettivamente acquistato prima di lavorare.
"""
import datetime
import math
import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from matplotlib.patches import Rectangle, Circle, Ellipse, Polygon, FancyBboxPatch

import model as M

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "drawings")
DXF = os.path.join(HERE, "dxf")
A3 = (420, 297)
INK = "#111111"
THIN, MED, THICK = 0.25, 0.45, 0.8
DATE = datetime.date.today().isoformat()
REV = "A"


# ------------------------------------------------------------------ foglio
class Sheet:
    def __init__(self, num, title, scale="1:5", material="", qty="", mass="", fornitura=""):
        self.fig = plt.figure(figsize=(A3[0] / 25.4, A3[1] / 25.4))
        ax = self.fig.add_axes([0, 0, 1, 1])
        ax.set_xlim(0, A3[0]); ax.set_ylim(0, A3[1]); ax.set_aspect("equal"); ax.axis("off")
        self.ax = ax
        self.num, self.title = num, title
        # cornice
        ax.add_patch(Rectangle((10, 10), 400, 277, fill=False, lw=THICK, ec=INK))
        # cartiglio 180 x 36
        x0, y0 = 230, 10
        ax.add_patch(Rectangle((x0, y0), 180, 36, fill=False, lw=MED, ec=INK))
        for yy in (22, 34):
            ax.plot([x0, x0 + 180], [y0 + yy - 10 + (0 if yy == 22 else 0), y0 + yy - 10], lw=THIN, c=INK) if False else None
        ax.plot([x0, x0 + 180], [y0 + 12, y0 + 12], lw=THIN, c=INK)
        ax.plot([x0, x0 + 180], [y0 + 24, y0 + 24], lw=THIN, c=INK)
        for xx in (60, 120):
            ax.plot([x0 + xx, x0 + xx], [y0, y0 + 24], lw=THIN, c=INK)
        self.t(x0 + 3, y0 + 30, "MANIPMASTA", 9, weight="bold")
        self.t(x0 + 55, y0 + 30, title, 8.5, weight="bold")
        self.t(x0 + 157, y0 + 30, f"Tav. {num}", 9, weight="bold")
        cells = [("Materiale", material), ("Quantità", qty), ("Fornitura", fornitura),
                 ("Scala", scale), ("Data / Rev.", f"{DATE} / {REV}"), ("Toll. gen.", "ISO 2768-mK")]
        for i, (k, v) in enumerate(cells):
            cx = x0 + (i % 3) * 60 + 2
            cy = y0 + 20 - (i // 3) * 12
            self.t(cx, cy, k, 4.8, color="#555")
            self.t(cx, cy - 5.5, v, 6.2)
        self.t(14, 13, "Quote in mm. Spigoli vivi smussati 0,5×45°. Parti a contatto alimentare: AISI 304, finitura Ra ≤ 0,8 µm, saldature TIG passivate. [V] = verificare su datasheet del componente acquistato.", 5.2, color="#333")

    def t(self, x, y, s, size=6, **kw):
        kw.setdefault("color", INK)
        self.ax.text(x, y, s, fontsize=size, family="DejaVu Sans", va="center", **kw)

    def save(self, pdf):
        os.makedirs(os.path.join(OUT, "png"), exist_ok=True)
        slug = "".join(ch if ch.isalnum() else "_" for ch in self.title)[:40]
        self.fig.savefig(os.path.join(OUT, "png", f"T{self.num}_{slug}.png"), dpi=110)
        pdf.savefig(self.fig)
        plt.close(self.fig)


class View:
    """Vista in scala: coordinate pezzo (mm) -> foglio (mm)."""
    def __init__(self, sh, ox, oy, s, label=None):
        self.sh, self.ox, self.oy, self.s = sh, ox, oy, s
        self.ax = sh.ax
        if label:
            sh.t(ox, oy - 9, label, 6.5, weight="bold")

    def P(self, x, y):
        return self.ox + x * self.s, self.oy + y * self.s

    def rect(self, x, y, w, h, lw=THICK, ls="-", fc="none", ec=INK, z=2):
        X, Y = self.P(x, y)
        self.ax.add_patch(Rectangle((X, Y), w * self.s, h * self.s, fill=fc != "none", fc=fc, ec=ec, lw=lw, ls=ls, zorder=z))

    def line(self, x1, y1, x2, y2, lw=MED, ls="-", c=INK):
        a, b = self.P(x1, y1), self.P(x2, y2)
        self.ax.plot([a[0], b[0]], [a[1], b[1]], lw=lw, ls=ls, c=c, zorder=3)

    def poly(self, pts, lw=THICK, fc="none", ls="-"):
        self.ax.add_patch(Polygon([self.P(*p) for p in pts], closed=True, fill=fc != "none", fc=fc, ec=INK, lw=lw, ls=ls, zorder=2))

    def circle(self, x, y, d, lw=MED, ls="-", center=True):
        X, Y = self.P(x, y)
        self.ax.add_patch(Circle((X, Y), d / 2 * self.s, fill=False, ec=INK, lw=lw, ls=ls, zorder=3))
        if center:
            e = d / 2 * self.s + 1.5
            self.ax.plot([X - e, X + e], [Y, Y], lw=0.15, c=INK, ls=(0, (6, 1.5, 1, 1.5)))
            self.ax.plot([X, X], [Y - e, Y + e], lw=0.15, c=INK, ls=(0, (6, 1.5, 1, 1.5)))

    def axis_line(self, x1, y1, x2, y2):
        a, b = self.P(x1, y1), self.P(x2, y2)
        self.ax.plot([a[0], b[0]], [a[1], b[1]], lw=0.18, c=INK, ls=(0, (8, 2, 1.5, 2)))

    def dim_h(self, x1, x2, y, off, text=None, size=5.5):
        X1, Y = self.P(x1, y); X2, _ = self.P(x2, y)
        Yd = Y + off
        self.ax.plot([X1, X1], [Y, Yd + (1.5 if off > 0 else -1.5)], lw=0.15, c=INK)
        self.ax.plot([X2, X2], [Y, Yd + (1.5 if off > 0 else -1.5)], lw=0.15, c=INK)
        self.ax.annotate("", (X1, Yd), (X2, Yd), arrowprops=dict(arrowstyle="<|-|>", lw=0.25, color=INK, shrinkA=0, shrinkB=0, mutation_scale=4))
        self.ax.text((X1 + X2) / 2, Yd + 1.4, text or f"{abs(x2 - x1):g}", fontsize=size, ha="center", va="bottom", color=INK)

    def dim_v(self, y1, y2, x, off, text=None, size=5.5):
        X, Y1 = self.P(x, y1); _, Y2 = self.P(x, y2)
        Xd = X + off
        self.ax.plot([X, Xd + (1.5 if off > 0 else -1.5)], [Y1, Y1], lw=0.15, c=INK)
        self.ax.plot([X, Xd + (1.5 if off > 0 else -1.5)], [Y2, Y2], lw=0.15, c=INK)
        self.ax.annotate("", (Xd, Y1), (Xd, Y2), arrowprops=dict(arrowstyle="<|-|>", lw=0.25, color=INK, shrinkA=0, shrinkB=0, mutation_scale=4))
        self.ax.text(Xd - 1.4, (Y1 + Y2) / 2, text or f"{abs(y2 - y1):g}", fontsize=size, ha="center", va="center", rotation=90, color=INK)

    def note(self, x, y, tx, ty, text, size=5.5):
        a = self.P(x, y)
        self.ax.annotate(text, a, (tx, ty), fontsize=size, color=INK, va="center",
                         arrowprops=dict(arrowstyle="-|>", lw=0.25, color=INK, mutation_scale=4, shrinkA=0, shrinkB=0))


def table(sh, x, y, cols, rows, widths, size=5.6, rh=5.2, title=None):
    ax = sh.ax
    if title:
        sh.t(x, y + 4, title, 6.5, weight="bold")
    allrows = [cols] + rows
    W = sum(widths)
    for i, r in enumerate(allrows):
        yy = y - i * rh
        ax.add_patch(Rectangle((x, yy - rh), W, rh, fill=i == 0, fc="#e8e8e8", ec=INK, lw=THIN))
        cx = x
        for w, v in zip(widths, r):
            ax.text(cx + 1.2, yy - rh / 2, str(v), fontsize=size, va="center", color=INK, weight="bold" if i == 0 else "normal")
            cx += w
    cx = x
    for w in widths[:-1]:
        cx += w
        ax.plot([cx, cx], [y, y - len(allrows) * rh], lw=THIN, c=INK)
    return y - len(allrows) * rh


# ------------------------------------------------------------------ lamiere (piastre)
def plate_specs(P):
    """Piastre da taglio laser: contorno + fori (x, y, d, etichetta) con origine in basso a sinistra."""
    nema = lambda cx, cy, tag: [(cx, cy, 38.5, f"{tag} centraggio NEMA23")] + \
        [(cx + sx * 23.57, cy + sy * 23.57, 5.5, f"{tag} M5 passante") for sx in (-1, 1) for sy in (-1, 1)]
    plates = []

    # quote dal modello 3D
    ay = P["anchor_y"]; zy = ay - 90; sh_y = zy - 27; s_out = zy - 47
    gdx, sdx = P["guide_dx"], P["screw_dx"]
    car_z0 = P["beam_top"] + 18 + 35

    # piastra carrello X: y locale 0 = bordo interno (y mondo = s_out - 23)
    cl, cw = P["car_len"], P["car_w"]
    y_in = s_out - 23
    cx = cl / 2
    h = []
    for bx in (cx - 75, cx + 75):            # pattini SBR20UU centrati sulla guida
        for dx in (-17.5, 17.5):
            for dy in (-18, 18):
                h.append((bx + dx, ay - y_in + dy, 6.6, "M6 pattino SBR20UU [V]"))
    for x in (cx - 100, cx - 35, cx + 35, cx + 100):
        h.append((x, (zy + P["zplate_t"] + 24) - y_in, 9, "M8 squadra piastra Z"))
    for gx in (-gdx, gdx):
        h.append((cx + gx, sh_y - y_in, 17, "Ø17 passaggio albero Ø16 (inserimento dall'alto)"))
    h.append((cx + sdx, sh_y - y_in, 30, "Ø30 passaggio vite/giunto Z"))
    for ddx in (-23.6, 23.6):
        for ddy in (-23.6, 23.6):
            h.append((cx + sdx + ddx, sh_y - y_in + ddy, 5.5, "M5 distanziale motore Z"))
    h += [(cx + 100, cw - 30, 9, "M8 traversa ponte"), (cx + 100, cw - 70, 9, "M8 traversa ponte")]
    h += [(cx + 60 + dx, cw - 8, 5.5, "M5 attacco cinghia") for dx in (-12, 12)]
    plates.append(dict(code="CAR-01", name="Piastra carrello X", qty="2 (speculari)", t=12, w=cl, h=cw, holes=h,
                       material="AISI 304 sp. 12", note="Y=0 = bordo interno (verso il rullo). Rettificare le facce di appoggio pattini: planarità 0,05."))

    # piastra Z fissa: y locale 0 = bordo inferiore
    zh = car_z0 - P["zplate_bottom"]
    zw = P["zplate_w"]
    cx = zw / 2
    h = []
    for gx in (-gdx, gdx):
        for gz in (12, car_z0 - 30 - P["zplate_bottom"]):
            for dx in (-16, 16):
                h.append((cx + gx + dx, gz, 5.5, "M5 supporto SK16 [V]"))
    h += [(cx + sdx + dx, 18, 5.5, "M5 supporto BF12 [V]") for dx in (-20, 20)]
    h += [(cx + sdx + dx, car_z0 - 40 - P["zplate_bottom"], 5.5, "M5 supporto BK12 [V]") for dx in (-23, 23)]
    for x in (cx - 50, cx, cx + 50):
        h.append((x, zh - 13, 9, "M8 squadra carrello"))
    plates.append(dict(code="ZPL-01", name="Piastra Z fissa", qty="2 (speculari)", t=P["zplate_t"], w=zw, h=round(zh), holes=h,
                       material="AISI 304 sp. 15", note="Fori supporti SK16 e BK/BF lavorati in un unico piazzamento: parallelismo guide 0,05/400."))

    # slitta Z: y locale 0 = bordo inferiore; asse rullo a slide_below
    sw, sh_ = P["slide_w"], P["slide_h"]
    c0 = sw / 2
    rl = P["slide_below"]
    base = [(c0, rl, 47, "sede cuscinetto Ø47 H7 (S6204-2RS), passante con battuta")]
    for a in range(4):
        ang = math.radians(45 + 90 * a)
        base.append((c0 + 30 * math.cos(ang), rl + 30 * math.sin(ang), 5.5, "M5 coperchio cuscinetto Ø72"))
    for gx in (-gdx, gdx):
        for dz in (120, 180):
            for dx in (-12, 12):
                for dy in (-15, 15):
                    base.append((c0 + gx + dx, rl + dz + dy, 5.5, "M5 pattino SC16UU [V]"))
    for a in range(4):
        ang = math.radians(45 + 90 * a)
        base.append((c0 + sdx + 19 * math.cos(ang), rl + 150 + 19 * math.sin(ang), 5.5, "M5 chiocciola TR16 [V]"))
    base.append((c0 + sdx, rl + 150, 30, "passaggio vite TR16"))
    base += [(c0 + 70, rl + 20, 6.6, "M6 barra raschietto")]
    plates.append(dict(code="ZSL-02", name="Slitta Z lato Y+ (Z2)", qty="1", t=P["slide_t"], w=sw, h=sh_, holes=list(base),
                       material="AISI 304 sp. 16", note="Sede cuscinetto alesata H7 dopo il taglio. Bandierina sensori 16×14 saldata sul lato destro in alto."))
    z1 = list(base) + nema(c0, rl + 135, "Motore R")
    plates.append(dict(code="ZSL-01", name="Slitta Z lato Y− (Z1, con motore R)", qty="1", t=P["slide_t"], w=sw, h=sh_, holes=z1,
                       material="AISI 304 sp. 16", note="Fori M5 motore R asolati 6 mm in verticale (tensione cinghia). Bandierina sensori come ZSL-02."))

    # coperchio cuscinetto
    h = [(36, 36, 22, "Ø22 passaggio perno")] + [(36 + 30 * math.cos(math.radians(45 + 90 * a)), 36 + 30 * math.sin(math.radians(45 + 90 * a)), 5.5, "M5 passante") for a in range(4)]
    plates.append(dict(code="COP-01", name="Coperchio cuscinetto Ø72 (disegnato quadro 72, tornire Ø72)", qty="2", t=5, w=72, h=72, holes=h,
                       material="AISI 304 sp. 5", note="Tornire il contorno Ø72 dopo il taglio; spallamento Ø47×1 che preme l'anello esterno del cuscinetto."))

    # piastra piede
    f = P["foot"]
    h = [(f / 2, f / 2, 20, "Ø20 H7 perno (piantato + saldato)")]
    h.append((f / 2 + 45, f / 2 - 45 + 0, 12.2, "M12×1 sensore SEAT (solo A1, A2)"))
    plates.append(dict(code="PIE-01", name="Piastra piede montante", qty="4", t=P["foot_t"], w=f, h=f, holes=h,
                       material="AISI 304 sp. 10", note="Saldata TIG in testa al montante 60×60 coassiale al perno: tolleranza 0,2."))

    # staffa motore X / Z
    h = nema(40, 40, "Motore")
    h += [(8, 8, 6.6, "M6 fissaggio"), (72, 8, 6.6, "M6 fissaggio"), (8, 72, 6.6, "M6 fissaggio"), (72, 72, 6.6, "M6 fissaggio")]
    plates.append(dict(code="STM-01", name="Flangia motore NEMA23", qty="4 (X, Z1, Z2 + ricambio)", t=10, w=80, h=80, holes=h,
                       material="AISI 304 sp. 10", note="Per Z: montata su colonnine 40 mm sopra la piastra Z con giunto elastico 8→12 [V]."))
    return plates


def draw_plate(pdf, num, sp):
    w, h = sp["w"], sp["h"]
    s = min(190 / w, 175 / h, 1.0)
    for cand in (1.0, 0.5, 0.4, 0.25, 0.2):
        if cand <= s:
            s = cand
            break
    sh = Sheet(num, f"{sp['code']} {sp['name']}", scale=f"1:{round(1 / s, 2):g}", material=sp["material"], qty=sp["qty"], fornitura="Taglio laser + foratura/maschiatura")
    v = View(sh, 30, 245 - h * s, s)
    sh.t(v.ox, v.oy - 12, f"VISTA FRONTALE  (scala 1:{round(1 / s, 2):g})", 6.5, weight="bold")
    v.rect(0, 0, w, h)
    labels = {}
    rows = []
    for i, (x, y, d, lab) in enumerate(sp["holes"]):
        v.circle(x, y, d, center=d >= 10)
        hid = chr(65 + len(labels)) if lab not in labels else labels[lab]
        labels.setdefault(lab, hid)
        rows.append((labels[lab] + str(sum(1 for r in rows if r[0].startswith(labels[lab])) + 1), f"{x:.1f}", f"{y:.1f}", lab))
    for r in rows:
        X, Y = v.P(float(r[1]), float(r[2]))
        sh.ax.text(X + 1.2, Y + 1.6, r[0], fontsize=3.8, color="#0b4f9c", zorder=5)
    v.dim_h(0, w, h, 8)
    v.dim_v(0, h, 0, -8)
    sh.t(v.ox, v.oy - 18, "Origine 0,0 = spigolo in basso a sinistra", 5, color="#333")
    # vista laterale (spessore)
    vs = View(sh, v.ox + w * s + 18, v.oy, s)
    vs.rect(0, 0, sp["t"], h)
    vs.dim_h(0, sp["t"], 0, -6, text=f"{sp['t']}")
    # tabella fori
    rows_tab = [(r[0], r[1], r[2], r[3]) for r in rows]
    y = 270
    xt = 250
    chunk = 44
    table(sh, xt, y, ("Foro", "X", "Y", "Tipo"), rows_tab[:chunk], (12, 16, 16, 108), size=4.8, rh=4.0, title="TABELLA FORI")
    if len(rows_tab) > chunk:
        sh.t(xt, 270 - (chunk + 1) * 4.0 - 6, f"... altri {len(rows_tab) - chunk} fori: vedere DXF {sp['code']}.dxf", 5.5)
    sh.t(30, 52, "Note: " + sp["note"], 6)
    sh.t(30, 58, f"File di taglio: cad/dxf/{sp['code']}.dxf (contorno su layer TAGLIO, fori filettati su layer FORI_FILETTARE a diametro di preforo)", 5.5)
    sh.save(pdf)


def write_dxf(sp):
    import ezdxf
    os.makedirs(DXF, exist_ok=True)
    doc = ezdxf.new("R2010", setup=True)
    doc.units = ezdxf.units.MM
    for name, col in (("TAGLIO", 7), ("FORI_FILETTARE", 1), ("TESTI", 3)):
        doc.layers.add(name, color=col)
    msp = doc.modelspace()
    w, h = sp["w"], sp["h"]
    msp.add_lwpolyline([(0, 0), (w, 0), (w, h), (0, h)], close=True, dxfattribs={"layer": "TAGLIO"})
    tap = {6.6: 5.0, 5.5: 4.2, 9: 6.8, 12.5: 10.2, 12.2: 10.9}
    for x, y, d, lab in sp["holes"]:
        threaded = lab.startswith("M") and "passante" not in lab
        dd = tap.get(d, d) if threaded else d
        msp.add_circle((x, y), dd / 2, dxfattribs={"layer": "FORI_FILETTARE" if threaded else "TAGLIO"})
    msp.add_text(f"{sp['code']} {sp['material']} qty {sp['qty']}", height=4, dxfattribs={"layer": "TESTI"}).set_placement((0, -10))
    doc.saveas(os.path.join(DXF, f"{sp['code']}.dxf"))


# ------------------------------------------------------------------ tavole specifiche
def sheet_anchor(pdf, num, P):
    A, Ah = P["anchor_size"], P["anchor_h"]
    sh = Sheet(num, "ANC-01/02/03 Ancoraggi fissi al tavolo", scale="1:1", material="AISI 304 pieno (barra quadra 100)",
               qty="A1×1, A2×1, A3×2", fornitura="Fresatore / tornitore")
    variants = [("ANC-01 (A1) riferimento", "hole20"), ("ANC-02 (A2) asola", "slot"), ("ANC-03 (A3, A4) appoggio", "hole26")]
    for i, (lab, kind) in enumerate(variants):
        v = View(sh, 25 + i * 130, 160, 1.0, label=lab + " — vista dall'alto")
        v.rect(0, 0, A, A)
        c = A / 2
        if kind == "hole20":
            v.circle(c, c, 20, lw=THICK); v.circle(c, c, 26, lw=THIN, ls="--", center=False)
            v.note(c + 10, c + 10, v.ox + 70, v.oy + 112, "Ø20 H7 prof. 40\nsvasatura 3×45°")
        elif kind == "slot":
            v.poly([(c - 13, c - 10), (c + 13, c - 10), (c + 13, c + 10), (c - 13, c + 10)], lw=THICK)
            v.axis_line(c - 20, c, c + 20, c); v.axis_line(c, c - 16, c, c + 16)
            v.note(c + 13, c + 6, v.ox + 70, v.oy + 112, "asola 20 H7 × 26 (lungo X)\nprof. 40, svasatura 3×45°")
        else:
            v.circle(c, c, 26, lw=THICK)
            v.note(c + 10, c + 10, v.ox + 70, v.oy + 112, "Ø26 prof. 40 (solo appoggio)")
        for sx in (-35, 35):
            for sy in (-35, 35):
                v.circle(c + sx, c + sy, 8, lw=THIN, ls="--", center=False)
        v.dim_h(0, A, A, 6); v.dim_v(0, A, 0, -6)
        v.dim_h(c - 35, c + 35, 0, -6, text="70")
        # sezione
        s = View(sh, v.ox, 70, 1.0)
        s.rect(0, 0, A, Ah)
        bw = 20 if kind != "hole26" else 26
        if kind == "slot":
            bw = 26
        s.rect(c - bw / 2, Ah - 40, bw, 40, lw=MED, fc="#ffffff")
        for sx in (-35, 35):
            s.rect(c + sx - 3.4, 0, 6.8, 16, lw=THIN, ls="--")
        if kind in ("hole20", "slot"):
            s.rect(0, Ah - 25 - 4, A, 8, lw=THIN, ls="--")
            s.note(A - 5, Ah - 25, s.ox + 70, s.oy + 64, "Ø8 H8 passante (perno a sfere)\na 25 dal piano superiore")
        s.dim_v(0, Ah, 0, -6); s.dim_v(Ah - 40, Ah, A, 6, text="40")
        sh.t(s.ox, s.oy - 7, "Sezione mediana — 4× M8 prof. 16 sul fondo (interasse 70×70)", 5.5)
    sh.t(25, 44, "Fissaggio al tavolo: viti M8 da sotto il piano attraverso contropiastra inox 140×140×5; in alternativa staffa a C sul bordo tavolo.", 6.2)
    sh.t(25, 38, "Posizione centri: (±%d, ±%d) dal centro del tavolo. Posare con dima (barra di riscontro) e serrare dopo aver inserito il portale." % (P["anchor_x"], P["anchor_y"]), 6.2)
    sh.save(pdf)


def sheet_pin(pdf, num, P):
    sh = Sheet(num, "PER-01 Perno di centraggio", scale="2:1", material="AISI 420 temprato 50 HRC (o 304)", qty="4", fornitura="Tornitore")
    s = 2.0
    v = View(sh, 60, 150, s)
    sh.t(40, 272, "PERNO — vista laterale (scala 2:1)", 6.5, weight="bold")
    L1, L2 = 35, 10      # sporgenza sotto piastra, tratto nella piastra
    # corpo: y verticale = asse
    v.poly([(-10, 5), (-10, L1), (10, L1), (10, 5), (5, 0), (-5, 0)])
    v.rect(-10, L1, 20, L2, lw=THICK)
    v.rect(-15, L1 + L2, 30, 4, lw=THICK)
    v.axis_line(0, -5, 0, L1 + L2 + 10)
    v.rect(-10, 10 - 4, 20, 8, lw=THIN, ls="--")
    v.dim_v(0, L1, -10, -10, text="35 (sporgenza)")
    v.dim_v(L1, L1 + L2, 15, 10, text="10")
    v.dim_h(-10, 10, L1, 30, text="Ø20 g6")
    v.dim_h(-15, 15, L1 + L2 + 4, 8, text="Ø30")
    v.note(5, 2, 190, 140, "punta conica 30° — invito")
    v.note(10, 10, 190, 165, "Ø8 H8 passante a 10 dalla punta\n(allineato al foro dell'ancoraggio, solo A1/A2)")
    sh.t(40, 70, "Montaggio: piantato nella piastra piede PIE-01 dal sopra (battuta Ø30) e saldato a punti; coassialità con il montante 0,2.", 6.2)
    sh.t(40, 63, "Perno a sfere per bloccaggio: Ø8 × 110 utile con anello (tipo GN 113 / KIPP K0790) — acquisto.", 6.2)
    sh.save(pdf)


def sheet_roller(pdf, num, P):
    D, Lr = P["roller_d"], P["roller_len"]
    zy = P["anchor_y"] - 90
    stub = (zy - 47 + 30) - Lr / 2          # perno lato Y− (puleggia 40T)
    stub2 = (zy - 47 + 8) - Lr / 2          # perno lato Y+
    sh = Sheet(num, "RUL-01 Rullo di laminazione", scale="1:2", material="Tubo AISI 304 Ø100×3 + perni 304", qty="1", fornitura="Tornitore (rettifica)")
    s = 0.5
    v = View(sh, 40, 165, s)
    sh.t(40, 220, "RULLO — vista e sezione (scala 1:2)", 6.5, weight="bold")
    tot = Lr + stub + stub2
    x0 = 0
    v.rect(stub, -D / 2, Lr, D)
    v.rect(stub, -D / 2 + 3, Lr, D - 6, lw=THIN, ls="--")
    v.rect(stub, -D / 2 + 3, 10, D - 6, lw=THIN, fc="#dddddd")
    v.rect(stub + Lr - 10, -D / 2 + 3, 10, D - 6, lw=THIN, fc="#dddddd")
    v.rect(0, -10, stub, 20)
    v.rect(stub + Lr, -10, stub2, 20)
    v.axis_line(-10, 0, tot + 10, 0)
    v.rect(4, 7, 22, 3, lw=THIN)
    v.dim_h(stub + Lr, tot, -10, -12, text=f"{stub2:g}")
    v.dim_h(0, tot, D / 2, 12, text=f"{tot:g}")
    v.dim_h(stub, stub + Lr, D / 2, 5, text=f"{Lr:g} (tavola utile)")
    v.dim_h(0, stub, -10, -12, text=f"{stub:g}")
    v.dim_v(-D / 2, D / 2, stub + Lr, 10, text=f"Ø{D:g} h8")
    v.dim_v(-10, 10, 0, -8, text="Ø20 h6")
    v.note(15, 10, v.ox + 20, v.oy + 50, "cava linguetta 6×6×22 (lato Y−, puleggia 40T) · sedi cuscinetto Ø20 k6 + gola seeger")
    v.note(stub + 5, D / 2 - 15, v.ox + 100, v.oy + 52, "testate sp. 10 saldate TIG a tenuta, passivate")
    sh.t(40, 95, "Superficie di lavoro: rettificata e lucidata Ra ≤ 0,8 µm, nessuna porosità; eccentricità 0,03; equilibratura statica.", 6.2)
    sh.t(40, 88, "Perni: tornire dopo saldatura testate, in un'unica presa tra le punte (coassialità perni/superficie 0,02).", 6.2)
    sh.t(40, 81, "Alternativa alimentare leggera: barra piena POM-C Ø100 con perni inox passanti incollati e spinati.", 6.2)
    sh.t(40, 74, "Montaggio: cuscinetti inox S6204-2RS nelle sedi delle slitte ZSL-01/02, chiusi dai coperchi COP-01. Raschietto RAS-01 in POM-C.", 6.2)
    sh.save(pdf)


def sheet_frame(pdf, num, P):
    ax_, ay_ = P["anchor_x"], P["anchor_y"]
    leg, bh, bw, btop = P["leg"], P["beam_h"], P["beam_w"], P["beam_top"]
    Ah, ft = P["anchor_h"], P["foot_t"]
    sh = Sheet(num, "TEL-01 Telaio portale saldato", scale="1:10", material="AISI 304 tubolari", qty="1", fornitura="Carpenteria inox (TIG)")
    s = 0.1
    v = View(sh, 115, 175, s)
    sh.t(25, 232, "VISTA DALL'ALTO (scala 1:10)", 6.5, weight="bold")
    for sy in (-1, 1):
        v.rect(-ax_ - leg / 2, sy * ay_ - bw / 2, 2 * ax_ + leg, bw)
    for sx in (-1, 1):
        v.rect(sx * ax_ - 20, -ay_ + bw / 2, 40, 2 * ay_ - bw)
        for sy in (-1, 1):
            v.rect(sx * ax_ - leg / 2, sy * ay_ - leg / 2, leg, leg, lw=THIN, ls="--")
            v.rect(sx * ax_ - P["foot"] / 2, sy * ay_ - P["foot"] / 2, P["foot"], P["foot"], lw=THIN)
    v.dim_h(-ax_, ax_, ay_ + leg / 2, 8, text=f"{2 * ax_} (interasse ancoraggi)")
    v.dim_v(-ay_, ay_, -ax_ - leg / 2, -8, text=f"{2 * ay_}")
    v.dim_h(-ax_ - leg / 2, ax_ + leg / 2, -ay_ - P["foot"] / 2, -8, text=f"{2 * ax_ + leg}")
    f = View(sh, 115, 75, s)
    sh.t(25, 62, "VISTA FRONTALE lato Y− (scala 1:10)", 6.5, weight="bold")
    f.rect(-ax_ - leg / 2, btop - bh, 2 * ax_ + leg, bh)
    for sx in (-1, 1):
        f.rect(sx * ax_ - leg / 2, Ah + ft, leg, btop - bh - Ah - ft)
        f.rect(sx * ax_ - P["foot"] / 2, Ah, P["foot"], ft)
        f.rect(sx * ax_ - 10, Ah - 35, 20, 35, lw=THIN)
    f.line(-ax_ - 200, 0, ax_ + 200, 0, lw=THIN, ls="--")
    f.dim_v(0, btop, ax_ + leg / 2, 10, text=f"{btop} (piano guide)")
    f.dim_v(btop - bh, btop, -ax_ - leg / 2, -8, text=f"{bh}")
    sh.t(f.ox + (ax_ + 210) * s, f.oy + 2, "piano tavolo", 5.2)
    rows = [("Montanti", "tubo quadro 60×60×3", f"{btop - bh - Ah - ft}", "4"),
            ("Longheroni X", "tubo rett. 80×40×3", f"{2 * ax_ + leg}", "2"),
            ("Traversi Y", "tubo rett. 60×40×3", f"{2 * ay_ - bw}", "2"),
            ("Piastre piede", "PIE-01 sp. 10", "120×120", "4"),
            ("Maniglie", "tondo Ø16 piegato", "120 utile", "4"),
            ("Fazzoletti", "lamiera sp. 5 tri. 60×60", "-", "8"),
            ("Supporti albero X", "piatto 60×60×8 forato KFL001 [V]", "-", "4")]
    table(sh, 250, 262, ("Elemento", "Profilo", "Lungh.", "Q.tà"), rows, (32, 60, 22, 12), title="DISTINTA TELAIO")
    notes = ["Saldatura TIG continua, passivazione e decapaggio finali; nessuna cavità aperta (tappi saldati alle estremità).",
             "Planarità faccia superiore longheroni (appoggio guide SBR20): 0,1 su 1800 — fresare o spessorare dopo saldatura.",
             "Parallelismo tra i due longheroni: 0,1. Diagonali del rettangolo dei perni: differenza ≤ 0,5.",
             "Saldare i piedi con perni infilati negli ancoraggi già posati (dima) per garantire la posizione.",
             "Fori Ø17 passanti nei longheroni (asse a quota 430, x = −870) per l'albero di sincronismo Ø16.",
             "Peso stimato telaio ~32 kg; portale completo ~50 kg: sollevare in due con le 4 maniglie."]
    for i, n in enumerate(notes):
        sh.t(250, 200 - i * 7, "• " + n, 5.4, wrap=False)
    sh.save(pdf)


def sheet_shaft_misc(pdf, num, P):
    sh = Sheet(num, "Particolari torniti e plastici", scale="1:2 / 1:5", material="vedi tabella", qty="vedi tabella", fornitura="Tornitore / fresatura plastica")
    # albero sincronismo
    L = 2 * (P["anchor_y"] + P["beam_w"] / 2 + 15) + 120
    v = View(sh, 30, 230, 0.25, label=f"ASS-X Albero di sincronismo Ø16 h7 × {L:g} (scala 1:4)")
    v.rect(0, -8, L, 16)
    v.axis_line(-10, 0, L + 10, 0)
    for x in (60, L - 60):
        v.rect(x - 15, 3, 30, 5, lw=THIN)
    v.rect(L - 30, -6, 30, 12, lw=THIN, ls="--")
    v.dim_h(0, L, 8, 8, text=f"{L:g}")
    sh.t(30, 205, "Cave linguetta 5×5×30 per pulegge HTD-5M 20T; sedi cuscinetti KFL002 Ø15 k6; estremità lato motore Ø14 × 30 per giunto elastico. AISI 304 rettificato.", 5.8)
    # raschietto
    r = View(sh, 30, 160, 0.4, label="RAS-01 Raschietto POM-C (scala 1:2,5)")
    Lr = P["roller_len"] - 10
    r.rect(0, 0, Lr, 40)
    r.poly([(0, 0), (Lr, 0), (Lr, 3), (0, 3)], lw=THIN, fc="#dddddd")
    for x in (40, Lr - 40):
        r.rect(x - 10, 22, 20, 7, lw=MED)
    r.dim_h(0, Lr, 40, 6, text=f"{Lr:g}")
    r.dim_v(0, 40, 0, -6, text="40")
    sh.t(30, 140, "Spessore 10, spigolo di contatto smussato a 20° (lama). 2 asole 20×7 per regolazione; molla a lamina inox su perno della slitta.", 5.8)
    # contropiastra
    c = View(sh, 260, 175, 0.5, label="CTP-01 Contropiastra sotto piano (×4)")
    c.rect(0, 0, 140, 140)
    for sx in (-35, 35):
        for sy in (-35, 35):
            c.circle(70 + sx, 70 + sy, 9)
    c.dim_h(0, 140, 140, 6, text="140"); c.dim_v(0, 140, 0, -6, text="140")
    sh.t(260, 100, "AISI 304 sp. 5; 4 fori Ø9 su 70×70 (viti M8 nel fondo ancoraggio).", 5.8)
    rows = [("ASS-X", "Albero sincronismo", "AISI 304 Ø16 h7", "1"), ("RAS-01", "Raschietto", "POM-C alimentare sp.10", "2 (1 + ricambio)"),
            ("CTP-01", "Contropiastra", "AISI 304 sp.5", "4"), ("DIS-01", "Distanziali motore Z 40 mm", "AISI 304 Ø12 forato M5", "8")]
    table(sh, 30, 95, ("Codice", "Descrizione", "Materiale", "Q.tà"), rows, (24, 60, 60, 30), title="RIEPILOGO")
    sh.save(pdf)


# ------------------------------------------------------------------ assieme (proiezione modello)
def project(prim, view):
    """Ritorna (patch_type, params, depth) per vista: 'top' (X,Y, profondità -Z), 'front' (X,Z, prof. Y), 'side' (Y,Z, prof. -X)."""
    if prim["t"] == "tube":
        return None
    c = prim["c"]
    if view == "top":
        u, w, d, ia, ib, axn = c[0], c[1], -c[2], 0, 1, "z"
    elif view == "front":
        u, w, d, ia, ib, axn = c[0], c[2], c[1], 0, 2, "y"
    else:
        u, w, d, ia, ib, axn = c[1], c[2], -c[0], 1, 2, "x"
    if prim["t"] == "box":
        s = prim["s"]
        return ("rect", (u - abs(s[ia]) / 2, w - abs(s[ib]) / 2, abs(s[ia]), abs(s[ib])), d)
    if prim["t"] == "ell":
        r = prim["r"]
        return ("ell", (u, w, 2 * r[ia], 2 * r[ib]), d)
    r, l, ax = prim["r"], prim["l"], prim["ax"]
    if ax == axn:
        return ("circ", (u, w, r), d)
    idx = {"x": 0, "y": 1, "z": 2}[ax]
    a = l if idx == ia else 2 * r
    b = l if idx == ib else 2 * r
    return ("rect", (u - a / 2, w - b / 2, a, b), d)


def sheet_assembly(pdf, num, P, mdl):
    sh = Sheet(num, "Assieme generale — viste", scale="1:20", material="—", qty="1", fornitura="—")
    s = 0.05
    cfg = [("top", 30, 200, "VISTA DALL'ALTO"), ("front", 30, 85, "VISTA FRONTALE (da Y−)"), ("side", 175, 85, "VISTA LATERALE (da X−)")]
    for view, ox, oy, lab in cfg:
        vw = View(sh, ox + 1000 * s + (0 if view != "side" else -1000 * s + 600 * s), oy, s)
        if view == "side":
            vw.ox = ox + 500 * s + 40
        else:
            vw.ox = ox + 1100 * s
        sh.t(ox, oy + (60 if view == "top" else 75), lab, 6.5, weight="bold")
        items = []
        for p in mdl.parts:
            if p["code"] == "TAV" and view == "top":
                pass
            for q in p["prims"]:
                if p["code"] == "TAV" and q["c"][2] < -60:
                    continue
                pr = project(q, view)
                if pr:
                    items.append((p, q, pr))
        items.sort(key=lambda it: -it[2][2])
        for p, q, (kind, prm, dep) in items:
            col = q["col"]
            if kind == "rect":
                X, Y = vw.P(prm[0], prm[1])
                sh.ax.add_patch(Rectangle((X, Y), prm[2] * s, prm[3] * s, fc=col, ec=INK, lw=0.12, alpha=0.95))
            elif kind == "circ":
                X, Y = vw.P(prm[0], prm[1])
                sh.ax.add_patch(Circle((X, Y), prm[2] * s, fc=col, ec=INK, lw=0.12))
            else:
                X, Y = vw.P(prm[0], prm[1])
                sh.ax.add_patch(Ellipse((X, Y), prm[2] * s, prm[3] * s, fc=col, ec=INK, lw=0.12))
        if view == "top":
            vw.dim_h(-P["table_L"] / 2, P["table_L"] / 2, P["table_W"] / 2, 6, text=f"{P['table_L']} tavolo")
            vw.dim_v(-P["table_W"] / 2, P["table_W"] / 2, P["table_L"] / 2, 6, text=f"{P['table_W']}")
            vw.dim_h(-P["x_travel"], P["x_travel"], -P["table_W"] / 2, -6, text=f"corsa rullo {2 * P['x_travel']}")
        elif view == "front":
            top = P["beam_top"] + 18 + 35 + 12 + 112
            vw.dim_v(0, P["beam_top"], P["table_L"] / 2, 6, text=f"{P['beam_top']}")
            vw.dim_v(0, top, -P["table_L"] / 2 - 280, -6, text=f"≈{top}")
        else:
            vw.dim_h(-P["anchor_y"], P["anchor_y"], 0, -6, text=f"{2 * P['anchor_y']}")
            vw.dim_v(0, P["gap_ref"], 0, 6, text=f"luce {P['gap_ref']}")
    rows = [(p["code"], p["name"][:52], p["info"].get("Fornitura", "")[:30]) for p in mdl.parts if p["code"] not in ("TAV", "IMP") and not p["code"].startswith("QE-") or p["code"] == "QE-01"]
    seen, uniq = set(), []
    for r in rows:
        if r[0] not in seen:
            seen.add(r[0]); uniq.append(r)
    table(sh, 250, 270, ("Codice", "Descrizione", "Fornitura"), uniq, (20, 88, 50), size=4.6, rh=4.2, title="ELENCO PARTI")
    sh.save(pdf)


def sheet_cover(pdf, P):
    sh = Sheet("00", "Copertina e indice", scale="—", material="—", qty="—", fornitura="—")
    sh.t(20, 270, "MANIPMASTA", 30, weight="bold")
    sh.t(20, 258, "Sfogliatrice a portale per tavolo da pasticceria — tavole costruttive", 11)
    sh.t(20, 250, f"Tavolo di riferimento {P['table_L']}×{P['table_W']} mm (ipotesi). Rigenerare con le misure reali: cad/params.json", 7)
    img = os.path.join(os.path.dirname(HERE), "docs", "img")
    for i, (fn, lab) in enumerate((("assieme_iso.png", "Assieme"), ("esploso_iso.png", "Esploso"))):
        pth = os.path.join(img, fn)
        if os.path.exists(pth):
            im = plt.imread(pth)
            h = 150 * im.shape[0] / im.shape[1]
            sh.ax.imshow(im, extent=(20 + i * 160, 170 + i * 160, 235 - h, 235), zorder=1)
            sh.t(20 + i * 160, 238 - 0, lab, 7, weight="bold")
    idx = [("00", "Copertina e indice"), ("01", "Assieme generale — viste"), ("02", "TEL-01 Telaio portale"),
           ("03", "ANC Ancoraggi fissi"), ("04", "PER-01 Perno di centraggio"), ("05", "RUL-01 Rullo"),
           ("06-12", "Piastre laser: CAR-01, ZPL-01, ZSL-02, ZSL-01, COP-01, PIE-01, STM-01"), ("13", "Particolari torniti e plastici")]
    table(sh, 20, 112 - 0, ("Tav.", "Contenuto"), idx, (18, 120), title="INDICE")
    sh.t(170, 100, "Elettrico: wiring/out/schemi_elettrici.pdf  ·  Distinta: bom/ManipMasta_distinta.xlsx", 6.5)
    sh.t(170, 92, "Modello 3D (esploso, come funziona, montaggio): cad/build/manipmasta_3d.html  ·  Istruzioni: cad/drawings/ManipMasta_montaggio.pdf", 6.5)
    sh.save(pdf)


def main():
    P = M.load_params()
    mdl = M.build(P)
    os.makedirs(OUT, exist_ok=True)
    plates = plate_specs(P)
    with PdfPages(os.path.join(OUT, "ManipMasta_tavole.pdf")) as pdf:
        sheet_cover(pdf, P)
        sheet_assembly(pdf, "01", P, mdl)
        sheet_frame(pdf, "02", P)
        sheet_anchor(pdf, "03", P)
        sheet_pin(pdf, "04", P)
        sheet_roller(pdf, "05", P)
        for i, sp in enumerate(plates):
            draw_plate(pdf, f"{6 + i:02d}", sp)
            write_dxf(sp)
        sheet_shaft_misc(pdf, f"{6 + len(plates):02d}", P)
    print("ok", len(plates), "piastre")


if __name__ == "__main__":
    main()
