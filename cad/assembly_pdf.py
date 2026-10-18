#!/usr/bin/env python3
"""Istruzioni di montaggio ManipMasta -> cad/drawings/ManipMasta_montaggio.pdf (A4 orizzontale).

Richiede le immagini prodotte da: python3 cad/build_viewer.py --render
"""
import datetime
import json
import os

import matplotlib
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (Frame, Image, KeepInFrame, PageTemplate, BaseDocTemplate, Paragraph, Spacer, Table,
                                TableStyle, FrameBreak, NextPageTemplate, PageBreak, ListFlowable, ListItem)

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
IMG = os.path.join(ROOT, "docs", "img")
STP = os.path.join(HERE, "build", "steps")
OUT = os.path.join(HERE, "drawings", "ManipMasta_montaggio.pdf")

fd = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
pdfmetrics.registerFont(TTFont("DV", os.path.join(fd, "DejaVuSans.ttf")))
pdfmetrics.registerFont(TTFont("DVB", os.path.join(fd, "DejaVuSans-Bold.ttf")))
_cond = "/usr/share/fonts/truetype/dejavu/DejaVuSansCondensed-Bold.ttf"
pdfmetrics.registerFont(TTFont("DVC", _cond if os.path.exists(_cond) else os.path.join(fd, "DejaVuSans-Bold.ttf")))

INK = colors.HexColor("#1d242c")
MUTED = colors.HexColor("#5d6874")
ACC = colors.HexColor("#c98a00")
LINE = colors.HexColor("#cfd6dd")
OK = colors.HexColor("#2a9a3a")

S = {
    "h1": ParagraphStyle("h1", fontName="DVC", fontSize=26, leading=30, textColor=INK),
    "h2": ParagraphStyle("h2", fontName="DVC", fontSize=17, leading=21, textColor=INK, spaceAfter=4),
    "h3": ParagraphStyle("h3", fontName="DVB", fontSize=8.5, leading=11, textColor=MUTED, spaceBefore=6, spaceAfter=2),
    "p": ParagraphStyle("p", fontName="DV", fontSize=9.6, leading=13.2, textColor=INK, alignment=TA_LEFT),
    "s": ParagraphStyle("s", fontName="DV", fontSize=8.4, leading=11, textColor=INK),
    "cap": ParagraphStyle("cap", fontName="DV", fontSize=7.6, leading=9.5, textColor=MUTED),
    "chk": ParagraphStyle("chk", fontName="DV", fontSize=9, leading=12, textColor=INK, borderPadding=(4, 4, 4, 6),
                          leftIndent=6, borderColor=OK, borderWidth=0),
}
PW, PH = landscape(A4)
M = 12 * mm
TODAY = datetime.date.today().isoformat()


def header_footer(c, doc):
    c.saveState()
    c.setFillColor(ACC)
    c.rect(0, PH - 6 * mm, PW, 6 * mm, stroke=0, fill=1)
    c.setFont("DVB", 8)
    c.setFillColor(colors.white)
    c.drawString(M, PH - 4.2 * mm, "MANIPMASTA · ISTRUZIONI DI MONTAGGIO")
    c.drawRightString(PW - M, PH - 4.2 * mm, f"Rev. A · {TODAY}")
    c.setFillColor(MUTED)
    c.setFont("DV", 7)
    c.drawString(M, 6 * mm, "Modello concettuale su tavolo 2000×800 ipotetico. Viteria inox A2/A4; coppie per A2-70 su filetto lubrificato. Forature [V] da verificare sui pezzi acquistati.")
    c.drawRightString(PW - M, 6 * mm, f"pag. {doc.page}")
    c.restoreState()


def img(path, w):
    from PIL import Image as PI
    iw, ih = PI.open(path).size
    return Image(path, width=w, height=w * ih / iw)


def bullets(items, style="p"):
    return ListFlowable([ListItem(Paragraph(t, S[style]), leftIndent=10, value="circle") for t in items],
                        bulletType="bullet", start="•", leftIndent=10, bulletFontName="DV", bulletFontSize=8)


def numbered(items):
    return ListFlowable([ListItem(Paragraph(t, S["p"]), leftIndent=14) for t in items],
                        bulletType="1", leftIndent=14, bulletFontName="DVB", bulletFontSize=9, bulletColor=ACC)


def build():
    model = json.load(open(os.path.join(HERE, "build", "model.json")))
    steps, tours, parts = model["steps"], model["tours"], model["parts"]
    doc = BaseDocTemplate(OUT, pagesize=landscape(A4), leftMargin=M, rightMargin=M, topMargin=M, bottomMargin=M,
                          title="ManipMasta - istruzioni di montaggio", author="ManipMasta")
    top = PH - 10 * mm
    left_w = 162 * mm
    fl = Frame(M, 12 * mm, left_w, top - 12 * mm - 4 * mm, id="L", showBoundary=0, leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    fr = Frame(M + left_w + 8 * mm, 12 * mm, PW - 2 * M - left_w - 8 * mm, top - 12 * mm - 4 * mm, id="R", showBoundary=0,
               leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    ff = Frame(M, 12 * mm, PW - 2 * M, top - 16 * mm, id="F", leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate("two", [fl, fr], onPage=header_footer), PageTemplate("full", [ff], onPage=header_footer)])
    rw = PW - 2 * M - left_w - 8 * mm
    story = []

    # ---------- copertina e indice
    story += [Paragraph("ManipMasta", S["h1"]), Paragraph("Istruzioni di montaggio e funzionamento", S["h2"]),
              Spacer(1, 4), img(os.path.join(IMG, "esploso_iso.png"), left_w * 0.98), FrameBreak()]
    rows = [[Paragraph("<b>Fase</b>", S["s"]), Paragraph("<b>Contenuto</b>", S["s"])]]
    for i, s in enumerate(steps):
        if i:
            rows.append([Paragraph(str(i), S["s"]), Paragraph(s["t"], S["s"])])
    t = Table(rows, colWidths=[12 * mm, rw - 12 * mm])
    t.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e9ee")),
                           ("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 2), ("BOTTOMPADDING", (0, 0), (-1, -1), 2)]))
    tools = ["Chiavi a brugola 2,5–10 e chiave dinamometrica 2–25 Nm", "Comparatore con base magnetica, riga 1 m, squadra",
             "Spessimetro 0,05–1 mm", "Grasso alimentare NSF H1, frenafiletti medio", "Due persone per sollevare il portale (~50 kg)"]
    cpl = [["M4", "2,5 Nm"], ["M5", "5 Nm"], ["M6", "8 Nm"], ["M8", "20 Nm"], ["M12", "68 Nm"]]
    tc = Table([[Paragraph("<b>Vite A2-70</b>", S["s"]), Paragraph("<b>Coppia</b>", S["s"])]] + [[Paragraph(a, S["s"]), Paragraph(b, S["s"])] for a, b in cpl],
               colWidths=[30 * mm, 30 * mm])
    tc.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e9ee"))]))
    story += [KeepInFrame(rw, PH, [Paragraph("Sequenza", S["h3"]), t, Paragraph("Attrezzi", S["h3"]), bullets(tools, "s"),
                                   Paragraph("Coppie di serraggio", S["h3"]), tc], mode="shrink"), NextPageTemplate("two"), PageBreak()]

    # ---------- come funziona
    for tr in tours:
        p = os.path.join(IMG, f"funziona_{tr['id']}.png")
        if not os.path.exists(p):
            continue
        story += [img(p, left_w), FrameBreak()]
        body = [Paragraph("Come funziona", S["h3"]), Paragraph(tr["t"], S["h2"])] + [Paragraph(x, S["p"]) for x in tr["p"]]
        if tr["id"] == "servo":
            body += [Paragraph("Catena di comando", S["h3"]),
                     bullets(["Arduino → driver: STEP (un impulso per passo), DIR (verso), ENA (abilitazione).",
                              "Driver → motore: corrente nelle fasi A e B.",
                              "Encoder → driver: posizione reale dell'albero; il driver corregge.",
                              "Driver → Arduino: ALM se l'errore supera la soglia (macchina in ALLARME)."], "s")]
        if tr["id"] == "motori":
            rows = [["Motore", "Asse", "Dove", "Trasmissione", "Driver"],
                    ["M1", "X", "portale, X− lato Y+ (fisso)", "giunto + albero + cinghie HTD-5M, 100 mm/giro", "U11 · 1600 imp/giro"],
                    ["M2", "Z1", "sopra carrello Y− (mobile)", "giunto + vite TR16×4, 4 mm/giro", "U12 · 800 imp/giro"],
                    ["M3", "Z2", "sopra carrello Y+ (mobile)", "giunto + vite TR16×4, 4 mm/giro", "U13 · 800 imp/giro"],
                    ["M4", "R", "slitta Z lato Y− (sale con il rullo)", "cinghia 20T→40T sul rullo", "U14 · 800 imp/giro"]]
            tt = Table([[Paragraph(c, S["s"]) for c in r] for r in rows], colWidths=[11 * mm, 9 * mm, 28 * mm, 30 * mm, rw - 78 * mm])
            tt.setStyle(TableStyle([("LINEBELOW", (0, 0), (-1, -1), 0.3, LINE), ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e4e9ee")),
                                    ("VALIGN", (0, 0), (-1, -1), "TOP")]))
            body += [Spacer(1, 6), tt]
        story += [KeepInFrame(rw, PH, body, mode="shrink"), PageBreak()]

    # ---------- fasi
    names = {}
    for p in parts:
        names.setdefault(p["step"], [])
        k = f"{p['code']} — {p['name']}"
        if k not in names[p["step"]]:
            names[p["step"]].append(k)
    for i, s in enumerate(steps):
        if not i:
            continue
        a = os.path.join(STP, f"step_{i:02d}_a.png")
        b = os.path.join(STP, f"step_{i:02d}_b.png")
        story += [img(a, left_w), Paragraph("Frecce: direzione di montaggio dei pezzi della fase (evidenziati in giallo).", S["cap"]), FrameBreak()]
        body = [Paragraph(f"FASE {i} DI {len(steps) - 1}", S["h3"]), Paragraph(s["t"], S["h2"]), numbered(s["ops"])]
        if names.get(i):
            body += [Paragraph("Pezzi", S["h3"]), bullets(names[i], "s")]
        if s.get("vit"):
            body += [Paragraph("Viteria", S["h3"]), bullets(s["vit"], "s")]
        if s.get("cpl"):
            body += [Paragraph(f"<b>Coppie:</b> {s['cpl']}", S["s"])]
        body += [Spacer(1, 4), Table([[Paragraph(f"<b>Controllo</b> · {s['chk']}", S["s"])]], colWidths=[rw],
                                     style=[("LINEBEFORE", (0, 0), (0, 0), 2.5, OK), ("LEFTPADDING", (0, 0), (-1, -1), 6)])]
        if os.path.exists(b):
            body += [Spacer(1, 6), Paragraph("Risultato della fase", S["h3"]), img(b, rw * 0.78)]
        story += [KeepInFrame(rw, PH - 30 * mm, body, mode="shrink"), PageBreak()]
    doc.build(story)
    print(OUT)


if __name__ == "__main__":
    build()
