#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ManipMasta - generatore tavole elettriche E01..E05.

Uso:
    python3 generate_wiring.py            # genera out/E0x.svg, out/E0x.png (150 dpi), out/schemi_elettrici.pdf
    python3 generate_wiring.py --md       # stampa anche le tabelle Markdown (fili, pinout, Harting) per il README

Dipendenze: solo matplotlib (>= 3.5). Coordinate in mm su foglio A3 orizzontale (420 x 297).
Riferimento unico: docs/SPEC.md par. 2 e 2.1 (pinout DEFINITIVO). Questo script NON modifica la SPEC.
"""
import csv
import math
import os
import sys

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
from matplotlib.backends.backend_pdf import PdfPages  # noqa: E402
from matplotlib.patches import Circle, Ellipse, Polygon, Rectangle  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, "out")

PROJECT = "ManipMasta"
DATE = "2026-10-18"
REV = "A"
N_SHEETS = 5

plt.rcParams["font.family"] = "DejaVu Sans"
plt.rcParams["svg.fonttype"] = "path"
plt.rcParams["pdf.fonttype"] = 42

# --------------------------------------------------------------------------------------
# DATI DI PROGETTO (da SPEC par. 2.1) - unica fonte per disegni e tabelle
# --------------------------------------------------------------------------------------
RESERVED = {4, 10, 50, 51, 52, 53}  # Ethernet Shield 2: SD CS, W5500 CS, SPI

AXES = [
    # asse, driver, motore, fusibile, pin (PUL, DIR, ENA, ALM), morsetto X6 per GND, impulsi/giro, coppia
    dict(ax="X", u="U11", m="M1", f="F11", pul=22, dir=23, ena=24, alm=25, gnd="X6:2", ppr=1600, wn=410,
         wp="W1", we="W2", mod_p="a", p0=1, mod_e="c", e0=1, desc="traslazione rullo, 16 step/mm"),
    dict(ax="Z1", u="U12", m="M2", f="F12", pul=26, dir=27, ena=28, alm=29, gnd="X6:3", ppr=800, wn=420,
         wp="W3", we="W4", mod_p="a", p0=5, mod_e="c", e0=7, desc="altezza lato Y-, 200 step/mm"),
    dict(ax="Z2", u="U13", m="M3", f="F13", pul=30, dir=31, ena=32, alm=33, gnd="X6:4", ppr=800, wn=430,
         wp="W5", we="W6", mod_p="b", p0=1, mod_e="d", e0=1, desc="altezza lato Y+, 200 step/mm"),
    dict(ax="R", u="U14", m="M4", f="F14", pul=34, dir=35, ena=36, alm=37, gnd="X6:5", ppr=800, wn=440,
         wp="W7", we="W8", mod_p="b", p0=5, mod_e="d", e0=7, desc="rotazione rullo, 5,093 step/mm"),
]

SENSORS = [  # sigla, segnale, pin, canale U6, pin XP2, posizione
    ("B1", "X_MIN", 38, "IN1", 3, "longherone Y-, lato X- (home)"),
    ("B2", "X_MAX", 39, "IN2", 4, "longherone Y-, lato X+ (extracorsa)"),
    ("B3", "Z1_HOME", 40, "IN3", 5, "piastra Z1, finecorsa alto"),
    ("B4", "Z2_HOME", 41, "IN4", 6, "piastra Z2, finecorsa alto"),
    ("B5", "Z1_LOW", 42, "IN5", 7, "piastra Z1, extracorsa basso"),
    ("B6", "Z2_LOW", 43, "IN6", 8, "piastra Z2, extracorsa basso"),
    ("B7", "SEAT_A", 44, "IN7", 9, "piede A1 (portale in sede)"),
    ("B8", "SEAT_B", 45, "IN8", 10, "piede A2 (portale in sede)"),
]

U7_INPUTS = [  # canale, segnale, pin, sorgente
    ("IN1", "ESTOP_OK", 2, "K1 43-44 (aux NO)"),
    ("IN2", "CURTAIN_OK", 3, "K2 11-14 + K3 11-14"),
    ("IN3", "BTN_START", 48, "S2 START (NO)"),
    ("IN4", "BTN_STOP", 49, "S3 STOP (NC)"),
]

OUTPUTS = [  # pin, canale U8, utenza, colore
    (5, "IN1", "H1", "lampada VERDE"),
    (6, "IN2", "H2", "lampada GIALLA"),
    (7, "IN3", "H3", "lampada ROSSA"),
    (8, "IN4", "H4", "BUZZER"),
]

MOTOR_COLORS = [("A+", "nero"), ("A-", "verde"), ("B+", "rosso"), ("B-", "blu")]
ENC_COLORS = [("EA+", "nero"), ("EA-", "blu"), ("EB+", "giallo"), ("EB-", "verde"), ("VCC", "rosso"),
              ("EGND", "bianco")]


def self_check():
    used = []
    for a in AXES:
        used += [a["pul"], a["dir"], a["ena"], a["alm"]]
    used += [s[2] for s in SENSORS] + [u[2] for u in U7_INPUTS] + [o[0] for o in OUTPUTS]
    assert len(used) == len(set(used)), "pin duplicato"
    assert not (set(used) & RESERVED), "pin riservato shield usato"
    expected = {
        "X": (22, 23, 24, 25), "Z1": (26, 27, 28, 29), "Z2": (30, 31, 32, 33), "R": (34, 35, 36, 37)}
    for a in AXES:
        assert (a["pul"], a["dir"], a["ena"], a["alm"]) == expected[a["ax"]]
    assert [s[2] for s in SENSORS] == [38, 39, 40, 41, 42, 43, 44, 45]
    assert [u[2] for u in U7_INPUTS] == [2, 3, 48, 49]
    assert [o[0] for o in OUTPUTS] == [5, 6, 7, 8]


def xp1_pins():
    """Restituisce lista (contatto, asse, segnale, colore, n.filo) per XP1 Han-Modular."""
    rows = []
    for a in AXES:
        for i, (sig, col) in enumerate(MOTOR_COLORS):
            rows.append((f"{a['mod_p']}{a['p0'] + i}", a["ax"], f"{a['m']} {sig}", col,
                         800 + AXES.index(a) * 4 + i + 1, a["wp"]))
        for i, (sig, col) in enumerate(ENC_COLORS):
            rows.append((f"{a['mod_e']}{a['e0'] + i}", a["ax"], f"{a['m']} enc {sig}", col,
                         820 + AXES.index(a) * 6 + i + 1, a["we"]))
    return rows


# --------------------------------------------------------------------------------------
# ELENCO FILI (morsetti) - usato per README e CSV
# --------------------------------------------------------------------------------------
def build_wires():
    W = []

    def w(n, a, b, sig, sez, col, note=""):
        W.append((str(n), a, b, sig, sez, col, note))

    # 230 V AC
    w(1, "X0:L", "Q1:1", "L 230 V", "1,5", "marrone", "ingresso rete da W0")
    w(2, "X0:N", "Q1:3", "N", "1,5", "blu chiaro", "")
    w(3, "Q1:2", "Q2:1", "L", "1,5", "marrone", "")
    w(4, "Q1:4", "Q2:N", "N", "1,5", "blu chiaro", "")
    w(5, "Q2:2", "X1:1", "L", "1,5", "marrone", "ponticello X1:1-3")
    w(6, "Q2:N", "X1:4", "N", "1,5", "blu chiaro", "ponticello X1:4-6")
    w(7, "X1:1", "F1:1", "L PSU1", "1,5", "marrone", "")
    w(8, "X1:2", "F2:1", "L PSU2", "1,5", "marrone", "")
    w(9, "X1:3", "F3:1", "L PSU3", "1,5", "marrone", "")
    w(10, "F1:2", "KM1:1", "L PSU1", "1,5", "marrone", "")
    w(11, "X1:4", "KM1:3", "N PSU1", "1,5", "blu chiaro", "")
    w(12, "KM1:2", "PSU1:L", "L PSU1 sotto sicurezza", "1,5", "marrone", "")
    w(13, "KM1:4", "PSU1:N", "N PSU1 sotto sicurezza", "1,5", "blu chiaro", "")
    w(14, "F2:2", "PSU2:L", "L PSU2", "1,5", "marrone", "")
    w(15, "X1:5", "PSU2:N", "N PSU2", "1,5", "blu chiaro", "")
    w(16, "F3:2", "PSU3:L", "L PSU3", "1,5", "marrone", "")
    w(17, "X1:6", "PSU3:N", "N PSU3", "1,5", "blu chiaro", "")
    # PE
    w("PE1", "X0:PE", "BPE", "PE rete", "2,5", "giallo-verde", "")
    w("PE2", "BPE", "PSU1:FG", "PE", "1,5", "giallo-verde", "PSU2/PSU3 HDR in classe II: senza FG")
    w("PE3", "BPE", "piastra di fondo", "PE", "2,5", "giallo-verde", "")
    w("PE4", "BPE", "porta quadro", "PE", "6 (treccia)", "giallo-verde / treccia Cu", "")
    w("PE5", "BPE", "XP1:PE", "PE portale", "2,5", "giallo-verde", "prosegue con W9 al telaio portale")
    w("PE6", "BPE", "XP2:PE", "PE", "1,5", "giallo-verde", "")
    w("PE7", "X2:5", "BPE", "ponte 0V48-PE", "1,5", "giallo-verde", "PELV, un solo punto, rimovibile per prova isolamento")
    w("PE8", "X4:1", "BPE", "ponte 0V24-PE", "1,5", "giallo-verde", "PELV, un solo punto, rimovibile per prova isolamento")
    w("PE9", "BPE", "staffa schermi", "PE schermi", "2,5", "giallo-verde", "schermi cavi a terra solo lato quadro")
    # 48 V
    w(201, "PSU1:+V", "X2:1", "+48 V", "2,5", "rosso", "ponticello X2:1-4")
    w(202, "PSU1:-V", "X2:5", "0V48", "2,5", "nero", "ponticello X2:5-9")
    for i, a in enumerate(AXES):
        w(203 + i, f"X2:{1 + i}", f"{a['f']}:1", f"+48 V driver {a['ax']}", "1,5", "rosso", "")
    for i, a in enumerate(AXES):
        w(207 + i, f"{a['f']}:2", f"{a['u']}:+Vdc", f"+48 V driver {a['ax']}", "1,5", "rosso",
          f"{a['f']} fusibile 5 A ritardato 5x20")
    for i, a in enumerate(AXES):
        w(211 + i, f"X2:{6 + i}", f"{a['u']}:GND", f"0V48 driver {a['ax']}", "1,5", "nero", "")
    # 24 V
    w(301, "PSU2:+V", "F4:1", "+24 V", "1,0", "blu scuro", "")
    w(302, "PSU2:+V", "F5:1", "+24 V", "1,0", "blu scuro", "")
    w(303, "PSU2:-V", "X4:1", "0V24", "1,0", "blu/bianco", "ponticello X4:1-12")
    w(304, "F4:2", "X3:1", "+24 V S (sicurezza)", "1,0", "blu scuro", "ponticello X3:1-4")
    w(305, "F5:2", "X3:5", "+24 V I/O", "1,0", "blu scuro", "ponticello X3:5-13")
    # Sicurezza
    w(310, "X3:2", "K1:A1", "+24 V S alim. K1", "0,75", "blu scuro", "")
    w(311, "X4:2", "K1:A2", "0V24 K1", "0,75", "blu/bianco", "")
    w(312, "K1:S11", "S0:11", "emergenza canale 1", "0,5", "blu scuro", "verso porta")
    w(313, "S0:12", "K1:S12", "emergenza canale 1", "0,5", "blu scuro", "")
    w(314, "K1:S21", "S0:21", "emergenza canale 2", "0,5", "blu scuro", "")
    w(315, "S0:22", "K1:S22", "emergenza canale 2", "0,5", "blu scuro", "")
    w(316, "K1:S33", "S1:13", "reset", "0,5", "blu scuro", "")
    w(317, "S1:14", "KM1:21", "reset + retroazione", "0,5", "blu scuro", "")
    w(318, "KM1:22", "K1:S34", "retroazione KM1 (NC)", "0,5", "blu scuro", "")
    w(319, "X3:3", "K1:13", "+24 V S", "0,75", "blu scuro", "")
    w(320, "K1:14", "K1:23", "serie contatti sicuri", "0,75", "blu scuro", "")
    w(321, "K1:24", "KM1:A1", "comando bobina KM1", "0,75", "blu scuro", "soppressore su bobina")
    w(322, "KM1:A2", "X4:3", "0V24", "0,75", "blu/bianco", "")
    w(323, "X3:4", "K1:43", "+24 V S", "0,5", "blu scuro", "")
    w(324, "K1:44", "U7:IN1", "ESTOP_OK (24 V = OK)", "0,5", "blu scuro", "-> D2")
    w(330, "X3:6", "LC1-TX:+24", "+24 V emettitore", "0,5", "blu scuro", "via W20")
    w(331, "X4:4", "LC1-TX:0V", "0V24", "0,5", "blu/bianco", "via W20")
    w(332, "X3:7", "LC1-RX:+24", "+24 V ricevitore", "0,5", "blu scuro", "via W21")
    w(333, "X4:5", "LC1-RX:0V", "0V24", "0,5", "blu/bianco", "via W21")
    w(334, "LC1-RX:OSSD1", "K2:A1", "OSSD1", "0,5", "blu scuro", "via W21")
    w(335, "K2:A2", "X4:6", "0V24", "0,5", "blu/bianco", "")
    w(336, "LC1-RX:OSSD2", "K3:A1", "OSSD2", "0,5", "blu scuro", "via W21")
    w(337, "K3:A2", "X4:7", "0V24", "0,5", "blu/bianco", "")
    w(338, "X3:8", "K2:11", "+24 V I/O", "0,5", "blu scuro", "")
    w(339, "K2:14", "K3:11", "serie K2-K3", "0,5", "blu scuro", "")
    w(340, "K3:14", "U7:IN2", "CURTAIN_OK (24 V = libera)", "0,5", "blu scuro", "-> D3")
    w(341, "X3:9", "S2:13", "+24 V I/O", "0,5", "blu scuro", "")
    w(342, "S2:14", "U7:IN3", "BTN_START", "0,5", "blu scuro", "-> D48")
    w(343, "X3:10", "S3:11", "+24 V I/O", "0,5", "blu scuro", "")
    w(344, "S3:12", "U7:IN4", "BTN_STOP (NC)", "0,5", "blu scuro", "-> D49")
    w(345, "X4:8", "U7:COM", "0V24 ingressi U7", "0,5", "blu/bianco", "")
    w(350, "X3:11", "XP2:1", "+24 V sensori", "0,75", "blu scuro", "")
    w(351, "X4:9", "XP2:2", "0V24 sensori", "0,75", "blu/bianco", "")
    for i, s in enumerate(SENSORS):
        w(352 + i, f"XP2:{s[4]}", f"U6:{s[3]}", f"{s[1]} ({s[0]})", "0,5", "blu scuro", f"-> D{s[2]}")
    w(360, "X4:10", "U6:COM", "0V24 ingressi U6", "0,5", "blu/bianco", "")
    w(370, "X3:12", "U8:COM1", "+24 V colonna", "0,5", "blu scuro", "ponticelli COM1-COM4")
    for i, o in enumerate(OUTPUTS):
        w(371 + i, f"U8:NO{i + 1}", f"{o[2]}", f"{o[3]}", "0,5", "blu scuro", "via W22")
    w(375, "X4:11", "H comune", "0V colonna luminosa", "0,5", "blu/bianco", "via W22")
    w(380, "X3:13", "U9:+Vin", "+24 V DC/DC", "0,5", "blu scuro", "")
    w(381, "X4:12", "U9:-Vin", "0V24 DC/DC", "0,5", "blu/bianco", "")
    w(382, "U9:+Vout", "U8:JD-VCC", "+5 V bobine rele", "0,5", "rosso", "togliere ponticello JD-VCC/VCC")
    w(383, "U9:-Vout", "U8:GND(JD)", "0 V bobine rele", "0,5", "nero", "")
    # Logica 5 V
    w(400, "A1:5V", "X7:1", "+5 V logica", "0,5", "rosso", "ponticello X7:1-4")
    w(401, "A1:GND", "X6:1", "GND logica", "0,5", "nero", "ponticello X6:1-8")
    for a in AXES:
        b = a["wn"]
        w(b + 1, f"A1:D{a['pul']}", f"{a['u']}:PUL+", f"{a['ax']}_PUL", "0,5", "viola", "")
        w(b + 2, f"A1:D{a['dir']}", f"{a['u']}:DIR+", f"{a['ax']}_DIR", "0,5", "viola", "")
        w(b + 3, f"A1:D{a['ena']}", f"{a['u']}:ENA+", f"{a['ax']}_ENA (ALTO=disabilitato)", "0,5", "viola", "")
        w(b + 4, f"{a['u']}:ALM+", f"A1:D{a['alm']}", f"{a['ax']}_ALM (BASSO=allarme)", "0,5", "grigio", "INPUT_PULLUP")
        w(b + 5, a["gnd"], f"{a['u']}:PUL-", f"GND logica {a['ax']}", "0,5", "nero",
          "ponticelli PUL-/DIR-/ENA-/ALM- sul driver")
    for i, s in enumerate(SENSORS):
        w(501 + i, f"U6:OUT{i + 1}", f"A1:D{s[2]}", s[1], "0,5", "grigio", "BASSO = attivo")
    w(509, "X7:2", "U6:VCC", "+5 V", "0,5", "rosso", "")
    w(510, "X6:6", "U6:GND", "GND logica", "0,5", "nero", "")
    for i, u in enumerate(U7_INPUTS):
        w(511 + i, f"U7:OUT{i + 1}", f"A1:D{u[2]}", u[1], "0,5", "grigio", "")
    w(515, "X7:3", "U7:VCC", "+5 V", "0,5", "rosso", "")
    w(516, "X6:7", "U7:GND", "GND logica", "0,5", "nero", "")
    for i, o in enumerate(OUTPUTS):
        w(601 + i, f"A1:D{o[0]}", f"U8:{o[1]}", f"{o[2]} {o[3]}", "0,5", "viola", "attivo ALTO")
    w(605, "X7:4", "U8:VCC", "+5 V ingressi rele", "0,5", "rosso", "")
    w(606, "X6:8", "U8:GND", "GND logica", "0,5", "nero", "")
    w(701, "PSU3:+V", "A1:Vin", "+12 V", "0,75", "rosso", "jack DC 5,5x2,1 o pin Vin")
    w(702, "PSU3:-V", "A1:GND", "0 V 12 V", "0,75", "nero", "")
    # Motori/encoder interno quadro (driver -> inserto XP1)
    for i, a in enumerate(AXES):
        for k, (sig, col) in enumerate(MOTOR_COLORS):
            pin = f"XP1:{a['mod_p']}{a['p0'] + k}"
            w(801 + i * 4 + k, f"{a['u']}:{sig}", pin, f"{a['m']} fase {sig}", "1,0", "nero (num.)",
              f"prosegue {a['wp']} ({col})")
    for i, a in enumerate(AXES):
        for k, (sig, col) in enumerate(ENC_COLORS):
            pin = f"XP1:{a['mod_e']}{a['e0'] + k}"
            w(821 + i * 6 + k, f"{a['u']}:{sig}", pin, f"{a['m']} encoder {sig}", "0,25 schermato",
              "come cavo", f"prosegue {a['we']} ({col})")
    return W


CABLES = [
    ("W0", "rete -> X0", "H07RN-F 3G1,5", "spina CEE 16 A 2P+T"),
    ("W1/W3/W5/W7", "XP1 -> motori M1..M4 (fasi)", "4x1,0 schermato per posa mobile (tipo Igus chainflex CF886/CF27)", "schermo a PE solo lato quadro"),
    ("W2/W4/W6/W8", "XP1 -> encoder M1..M4", "3x2x0,25 schermato a coppie per posa mobile (tipo chainflex CF11)", "coppie: EA+/EA-, EB+/EB-, VCC/EGND"),
    ("W9", "XP1:PE -> telaio portale", "1x2,5 giallo-verde (H07V-K o chainflex)", "capocorda ad occhio su perno saldato"),
    ("W10", "XP2 -> JB1 (scatola di derivazione portale)", "12G0,5 per posa mobile (tipo chainflex CF5)", "10 conduttori + PE + 1 riserva"),
    ("W11..W18", "JB1 -> sensori B1..B8", "3x0,34 PUR M12 (precablato)", "BN +24, BU 0V, BK segnale"),
    ("W20", "X3/X4 -> LC1-TX", "secondo costruttore barriera (M12 4/5 poli)", ""),
    ("W21", "X3/X4/K2/K3 -> LC1-RX", "secondo costruttore barriera (M12 5/8 poli)", "OSSD1/OSSD2"),
    ("W22", "U8/X4 -> colonna luminosa H1..H4", "7G0,5", "2 conduttori di riserva"),
    ("W23", "Ethernet Shield -> switch VLAN IoT", "Cat.6 S/FTP + passaparete RJ45 IP67", "IP 192.168.50.60"),
]


# --------------------------------------------------------------------------------------
# PRIMITIVE DI DISEGNO
# --------------------------------------------------------------------------------------
COL = dict(L="#8B4513", N="#1E88E5", PE="#2E7D32", PEY="#FBC02D", P48="#D32F2F", M48="#212121",
           P24="#1A237E", M24="#5C6BC0", SIG="#7B1FA2", ALM="#616161", GND="#212121", K="#000000",
           MOT="#00695C", ENC="#E65100", BN="#8B4513", BU="#1E88E5", BK="#000000", V5="#C62828",
           GREY="#9E9E9E")

LW = 0.75


class Sheet:
    def __init__(self, num, title, subtitle=""):
        self.num = num
        self.title = title
        self.subtitle = subtitle
        self.fig = plt.figure(figsize=(420 / 25.4, 297 / 25.4))
        self.ax = self.fig.add_axes([0, 0, 1, 1])
        self.ax.set_xlim(0, 420)
        self.ax.set_ylim(0, 297)
        self.ax.set_aspect("equal")
        self.ax.axis("off")
        self._frame()
        self._title_block()

    # --- base ---
    def line(self, pts, c=COL["K"], lw=LW, ls="-", z=3):
        xs = [p[0] for p in pts]
        ys = [p[1] for p in pts]
        self.ax.plot(xs, ys, color=c, lw=lw, ls=ls, zorder=z, solid_capstyle="butt",
                     solid_joinstyle="miter")

    def pe(self, pts, lw=1.3):
        self.line(pts, c=COL["PE"], lw=lw, z=3)
        self.line(pts, c=COL["PEY"], lw=lw * 0.55, ls=(0, (2, 2)), z=3.1)

    def text(self, x, y, s, fs=6, ha="center", va="center", rot=0, w="normal", c="k", bg=None, z=6,
             style="normal", family=None):
        kw = {}
        if bg:
            kw["bbox"] = dict(boxstyle="square,pad=0.12", fc=bg, ec="none")
        if family:
            kw["family"] = family
        self.ax.text(x, y, s, fontsize=fs, ha=ha, va=va, rotation=rot, weight=w, color=c, zorder=z,
                     style=style, linespacing=1.15, **kw)

    def dot(self, x, y, c=COL["K"], r=0.55):
        self.ax.add_patch(Circle((x, y), r, fc=c, ec=c, zorder=5))

    def term(self, x, y, r=0.65, c=COL["K"]):
        self.ax.add_patch(Circle((x, y), r, fc="white", ec=c, lw=0.6, zorder=5))

    def wn(self, x, y, s, rot=0):
        """numero filo"""
        self.ax.text(x, y, str(s), fontsize=4.6, ha="center", va="center", rotation=rot, color="#333333",
                     zorder=7, bbox=dict(boxstyle="square,pad=0.1", fc="white", ec="#888888", lw=0.3))

    def rect(self, x, y, w, h, lw=0.8, ls="-", fc="white", ec="k", z=2):
        self.ax.add_patch(Rectangle((x, y), w, h, lw=lw, ls=ls, fc=fc, ec=ec, zorder=z))

    def vhop(self, x, y1, y2, hops=(), c=COL["K"], lw=LW, r=1.1):
        """linea verticale con scavalchi (semicerchi verso destra) alle quote hops"""
        lo, hi = min(y1, y2), max(y1, y2)
        cur = lo
        for h in sorted(hops):
            self.line([(x, cur), (x, h - r)], c=c, lw=lw)
            pts = [(x + r * math.sin(t), h - r * math.cos(t)) for t in [i * math.pi / 16 for i in range(17)]]
            self.line(pts, c=c, lw=lw)
            cur = h + r
        self.line([(x, cur), (x, hi)], c=c, lw=lw)

    def hhop(self, y, x1, x2, hops=(), c=COL["K"], lw=LW, r=1.1):
        lo, hi = min(x1, x2), max(x1, x2)
        cur = lo
        for h in sorted(hops):
            self.line([(cur, y), (h - r, y)], c=c, lw=lw)
            pts = [(h - r * math.cos(t), y + r * math.sin(t)) for t in [i * math.pi / 16 for i in range(17)]]
            self.line(pts, c=c, lw=lw)
            cur = h + r
        self.line([(cur, y), (hi, y)], c=c, lw=lw)

    # --- simboli (coordinate locali: filo lungo v da -3 a +3, u perpendicolare) ---
    @staticmethod
    def _t(x, y, u, v, ori):
        return (x + u, y + v) if ori == "v" else (x + v, y - u)

    def _pl(self, x, y, pts, ori, c, lw=LW, ls="-"):
        self.line([self._t(x, y, u, v, ori) for (u, v) in pts], c=c, lw=lw, ls=ls)

    def sym(self, kind, x, y, ori="v", c=COL["K"], lw=LW):
        P = lambda pts, **k: self._pl(x, y, pts, ori, c, k.get("lw", lw), k.get("ls", "-"))  # noqa: E731
        if kind in ("no", "pb_no", "mcb"):
            P([(0, -3), (0, -1.8)])
            P([(0, -1.8), (-2.0, 2.1)])
            P([(0, 3), (0, 1.8)])
            if kind == "mcb":
                P([(-0.6, 1.2), (0.6, 2.4)])
                P([(-0.6, 2.4), (0.6, 1.2)])
            if kind == "pb_no":
                P([(-1.0, 0.15), (-4.2, 0.15)], ls=(0, (1.5, 1)))
                P([(-4.2, -1.2), (-4.2, 1.5)])
        elif kind in ("nc", "pb_nc", "mush_nc"):
            P([(0, -3), (0, -1.8)])
            P([(0, 3), (0, 1.8), (1.7, 1.8)])
            P([(0, -1.8), (1.7, 2.5)])
            if kind == "pb_nc":
                P([(0.85, 0.35), (-3.6, 0.35)], ls=(0, (1.5, 1)))
                P([(-3.6, -1.0), (-3.6, 1.7)])
            if kind == "mush_nc":
                P([(0.85, 0.35), (-3.4, 0.35)], ls=(0, (1.5, 1)))
                arc = [(-3.4 - 1.6 * math.sin(t), 0.35 + 1.6 * math.cos(t)) for t in
                       [i * math.pi / 12 for i in range(13)]]
                P(arc)
                P([(-3.4, -1.25), (-3.4, 1.95)])
        elif kind == "fuse":
            P([(0, -3), (0, 3)])
            P([(-1.0, -2.4), (1.0, -2.4), (1.0, 2.4), (-1.0, 2.4), (-1.0, -2.4)])
        elif kind == "coil":
            P([(0, -3), (0, -1.6)])
            P([(0, 3), (0, 1.6)])
            P([(-2.8, -1.6), (2.8, -1.6), (2.8, 1.6), (-2.8, 1.6), (-2.8, -1.6)], lw=lw * 1.2)
        elif kind == "lamp":
            P([(0, -3), (0, -2.2)])
            P([(0, 3), (0, 2.2)])
            cx, cy = self._t(x, y, 0, 0, ori)
            self.ax.add_patch(Circle((cx, cy), 2.2, fc="white", ec=c, lw=lw, zorder=4))
            d = 2.2 * 0.707
            P([(-d, -d), (d, d)])
            P([(-d, d), (d, -d)])
        elif kind == "buzzer":
            P([(0, -3), (0, -2.0)])
            P([(0, 3), (0, 2.0)])
            cx, cy = self._t(x, y, 0, 0, ori)
            self.ax.add_patch(Rectangle((cx - 2.2, cy - 2.0), 4.4, 4.0, fc="white", ec=c, lw=lw, zorder=4))
            self.text(cx, cy, "BZ", fs=4.2, z=6)

    def earth(self, x, y, label=None, pe=True, lab_dx=3.2, fs=4.8):
        """simbolo di terra di protezione; (x,y) = punto di collegamento in alto"""
        c = COL["PE"]
        self.line([(x, y), (x, y - 2.2)], c=c, lw=1.0)
        for i, wdt in enumerate([4.2, 2.8, 1.4]):
            self.line([(x - wdt / 2, y - 2.2 - i * 0.8), (x + wdt / 2, y - 2.2 - i * 0.8)], c=c, lw=0.9)
        if pe:
            self.ax.add_patch(Circle((x, y - 3.0), 2.7, fc="none", ec=c, lw=0.6, zorder=4))
        if label:
            self.text(x + lab_dx, y - 3.0, label, fs=fs, ha="left", c=COL["PE"])

    def gnd_logic(self, x, y, label=None):
        self.line([(x, y), (x, y - 2)], lw=0.8)
        self.ax.add_patch(Polygon([(x - 2, y - 2), (x + 2, y - 2), (x, y - 4)], closed=True, fc="white",
                                  ec="k", lw=0.7, zorder=4))
        if label:
            self.text(x + 3, y - 2.5, label, fs=4.8, ha="left")

    def legend(self, x, y, items, title="Legenda conduttori", w=70):
        h = 5 + len(items) * 3.6
        self.rect(x, y - h, w, h, lw=0.5)
        self.text(x + 2, y - 2.4, title, fs=5.5, ha="left", w="bold")
        for i, (key, lab) in enumerate(items):
            yy = y - 6 - i * 3.6
            if key == "PE":
                self.pe([(x + 3, yy), (x + 13, yy)], lw=1.2)
            else:
                ls = "-"
                self.line([(x + 3, yy), (x + 13, yy)], c=COL[key], lw=1.2, ls=ls)
            self.text(x + 15, yy, lab, fs=5, ha="left")

    def notes(self, x, y, w, lines, title="Note", fs=5.3, lh=3.15):
        h = 5.5 + len(lines) * lh
        self.rect(x, y - h, w, h, lw=0.5)
        self.text(x + 2, y - 2.6, title, fs=6, ha="left", w="bold")
        for i, s in enumerate(lines):
            self.text(x + 2, y - 6.6 - i * lh, s, fs=fs, ha="left")
        return y - h

    # --- cornice e cartiglio ---
    def _frame(self):
        self.rect(5, 5, 410, 287, lw=0.4, fc="none", z=1)
        self.rect(15, 10, 395, 277, lw=1.0, fc="none", z=1)
        # riferimenti di zona
        for i in range(8):
            xx = 15 + i * 395 / 8
            self.line([(xx, 287), (xx, 290)], lw=0.4)
            self.text(xx + 395 / 16, 289.2, str(i + 1), fs=5, c="#555")
        for i, L in enumerate("ABCDEF"):
            yy = 287 - i * 277 / 6
            self.line([(10, yy), (15, yy)], lw=0.4)
            self.text(12.5, yy - 277 / 12, L, fs=5, c="#555")

    def _title_block(self):
        x0, y0, w, h = 230, 10, 180, 36
        self.rect(x0, y0, w, h, lw=1.0, z=8)
        # righe
        self.line([(x0, y0 + 24), (x0 + w, y0 + 24)], lw=0.5, z=9)
        self.line([(x0, y0 + 12), (x0 + w, y0 + 12)], lw=0.5, z=9)
        self.line([(x0 + 120, y0), (x0 + 120, y0 + 24)], lw=0.5, z=9)
        self.line([(x0 + 150, y0), (x0 + 150, y0 + 24)], lw=0.5, z=9)
        self.line([(x0 + 135, y0 + 24), (x0 + 135, y0 + 36)], lw=0.5, z=9)

        def cell(x, y, lab, val, fs=7, w="normal"):
            self.text(x + 1.5, y + 9.6, lab, fs=4.3, ha="left", c="#555", z=10)
            self.text(x + 1.5, y + 4.3, val, fs=fs, ha="left", w=w, z=10)

        self.text(x0 + 2, y0 + 33, "PROGETTO", fs=4.3, ha="left", c="#555", z=10)
        self.text(x0 + 2, y0 + 28.2, f"{PROJECT} - sfogliatrice per pasticceria a portale", fs=8.5,
                  ha="left", w="bold", z=10)
        cell(x0 + 135, y0 + 24, "TAVOLA", f"E0{self.num}", fs=11, w="bold")
        # titolo
        self.text(x0 + 1.5, y0 + 21.6, "TITOLO", fs=4.3, ha="left", c="#555", z=10)
        self.text(x0 + 1.5, y0 + 17.0, self.title, fs=8, ha="left", w="bold", z=10)
        self.text(x0 + 1.5, y0 + 13.6, self.subtitle, fs=5, ha="left", z=10)
        cell(x0 + 120, y0 + 12, "REV.", REV, fs=8, w="bold")
        cell(x0 + 150, y0 + 12, "FOGLIO", f"{self.num} / {N_SHEETS}", fs=7)
        cell(x0, y0, "NORME / AVVERTENZE",
             "Schema indicativo - realizzazione e verifica a cura di elettricista qualificato (CEI EN 60204-1)",
             fs=4.6)
        cell(x0 + 120, y0, "DATA", DATE, fs=6.5)
        cell(x0 + 150, y0, "FORMATO", "A3 orizz.", fs=6.5)
        self.text(x0 + w - 1.5, y0 + 33.6, "rif. docs/SPEC.md par. 2 - 2.1", fs=4.3, ha="right", c="#555", z=10)

    def heading(self, s, sub=None):
        self.text(20, 281.5, s, fs=10, ha="left", w="bold")
        if sub:
            self.text(20, 277, sub, fs=5.8, ha="left", c="#333")

    def save(self, pdf):
        os.makedirs(OUT, exist_ok=True)
        base = os.path.join(OUT, f"E0{self.num}")
        self.fig.savefig(base + ".svg", format="svg")
        self.fig.savefig(base + ".png", dpi=150)
        pdf.savefig(self.fig)
        plt.close(self.fig)


# --------------------------------------------------------------------------------------
# E01 - POTENZA
# --------------------------------------------------------------------------------------
def sheet_e01(pdf):
    s = Sheet(1, "Alimentazione e potenza", "230 V AC, PSU 48/24/12 V, protezioni, distribuzione 48 V, terra PE")
    s.heading("E01 - Potenza", "Rete 230 V 1~ -> Q1 -> Q2 -> X1 -> F1/F2/F3 -> PSU1 (via KM1) / PSU2 / PSU3")
    yL, yN = 262, 252
    # ingresso
    s.text(21, 270, "W0  rete 230 V 50 Hz  H07RN-F 3G1,5\nspina CEE 16 A 2P+T", fs=5, ha="left")
    s.text(31.5, 258.3, "X0", fs=5.5, w="bold", ha="center")
    for yy, lab in ((yL, "L"), (yN, "N"), (242, "PE")):
        s.term(28, yy)
        s.text(25, yy, lab, fs=5, ha="right")
    s.pe([(28, 242), (36, 242), (36, 238)])
    s.earth(36, 238, "BPE")
    # Q1
    s.line([(28.65, yL), (47, yL)], c=COL["L"])
    s.line([(28.65, yN), (47, yN)], c=COL["N"])
    s.wn(38, yL, 1)
    s.wn(38, yN, 2)
    for yy in (yL, yN):
        s.sym("mcb", 50, yy, "h", c=COL["K"])
    s.line([(51.1, yN + 1.2), (51.1, yL + 1.2)], ls=(0, (1.5, 1)), lw=0.6)
    s.rect(44.5, 246.5, 11, 21, lw=0.5, ls=(0, (3, 1.5)), fc="none")
    s.text(50, 243.2, "Q1", fs=6, w="bold", va="top")
    s.text(50, 239.6, "2P C10\n6 kA", fs=4.8, va="top")
    s.text(46.2, yL - 1.8, "1", fs=4)
    s.text(53.8, yL - 1.8, "2", fs=4)
    s.text(46.2, yN - 1.8, "3", fs=4)
    s.text(53.8, yN - 1.8, "4", fs=4)
    # Q2 differenziale
    s.line([(53, yL), (77, yL)], c=COL["L"])
    s.line([(53, yN), (77, yN)], c=COL["N"])
    s.wn(62, yL, 3)
    s.wn(62, yN, 4)
    for yy in (yL, yN):
        s.sym("no", 80, yy, "h")
        s.line([(78.6, yy + 0.0), (81.0, yy)], lw=0.0)
    s.line([(81.1, yN + 1.2), (81.1, yL + 1.2)], ls=(0, (1.5, 1)), lw=0.6)
    s.ax.add_patch(Ellipse((70, 257), 3.2, 15, fc="none", ec="k", lw=0.7, zorder=4))
    s.line([(71.6, 257), (81.1, 257)], ls=(0, (1.5, 1)), lw=0.6)
    s.rect(66, 246.5, 19, 21, lw=0.5, ls=(0, (3, 1.5)), fc="none")
    s.text(75.5, 243.2, "Q2", fs=6, w="bold", va="top")
    s.text(75.5, 239.6, "ID 2P 25 A\n30 mA tipo A", fs=4.8, va="top")
    s.text(76.2, yL - 1.8, "1", fs=4)
    s.text(83.8, yL - 1.8, "2", fs=4)
    s.text(76.2, yN - 1.8, "N", fs=4)
    s.text(83.8, yN - 1.8, "N", fs=4)
    s.text(97, 238, "Se il laboratorio ha gia' a monte un\ndifferenziale 30 mA dedicato, Q2 e'\nfacoltativo (verifica elettricista).",
           fs=4.6, ha="left", style="italic", c="#444")
    # linee principali
    branches = [(130, 140, "PSU1", "1", "4", "F1", "6,3 A gG"), (250, 260, "PSU2", "2", "5", "F2", "2 A gG"),
                (330, 340, "PSU3", "3", "6", "F3", "1 A gG")]
    s.line([(83, yL), (130, yL)], c=COL["L"])
    s.line([(130, yL), (330, yL)], c=COL["L"])
    s.line([(83, yN), (340, yN)], c=COL["N"])
    s.wn(92, yL, 5)
    s.wn(92, yN, 6)
    wires = {"PSU1": (7, 10, 12, 11, 13), "PSU2": (8, 14, None, 15, None), "PSU3": (9, 16, None, 17, None)}
    for (xl, xn, name, t1, t2, fu, rating) in branches:
        if xl != 330:
            s.dot(xl, yL, c=COL["L"])
        s.dot(xn, yN, c=COL["N"]) if xn != 340 else None
        s.vhop(xl, 168, yL, hops=[yN], c=COL["L"])
        s.line([(xn, 168), (xn, yN)], c=COL["N"])
        s.term(xl, 245)
        s.term(xn, 245)
        s.text(xl - 1.5, 245, f"X1:{t1}", fs=4.5, ha="right")
        s.text(xn + 1.5, 245, f"X1:{t2}", fs=4.5, ha="left")
        s.sym("fuse", xl, 232, "v", c=COL["K"])
        s.text(xl - 2, 232, f"{fu}\n{rating}\n10x38", fs=4.6, ha="right")
        w = wires[name]
        s.wn(xl, 239.2, w[0])
        s.wn(xl, 224, w[1])
        s.wn(xn, 224 if name != "PSU1" else 229, w[3])
    # KM1 sul ramo PSU1
    s.sym("no", 130, 212, "v")
    s.sym("no", 140, 212, "v")
    s.line([(129.0, 212.2), (141, 212.2)], ls=(0, (1.5, 1)), lw=0.6)
    s.line([(141, 212.2), (146, 212.2)], ls=(0, (1.5, 1)), lw=0.6)
    s.text(147, 214.5, "KM1  contattore AC-3 >= 9 A", fs=5.2, ha="left", w="bold")
    s.text(147, 210.3, "bobina 24 V DC comandata da K1 (E02)\nsenza consenso sicurezza PSU1 spenta", fs=4.6,
           ha="left", va="top")
    s.text(128.3, 216.6, "1", fs=4)
    s.text(128.3, 207.4, "2", fs=4)
    s.text(138.3, 216.6, "3", fs=4)
    s.text(138.3, 207.4, "4", fs=4)
    s.wn(130, 201, 12)
    s.wn(140, 201, 13)
    # PSU boxes
    s.rect(120, 168 - 25, 85, 25, lw=0.9)
    s.text(162.5, 160, "PSU1  Mean Well SDR-480-48", fs=6, w="bold")
    s.text(162.5, 155.2, "48 V DC  10 A  480 W  (guida DIN)", fs=5)
    s.text(162.5, 151, "alimenta solo i driver U11...U14", fs=4.6, c="#444")
    for xx, lab in ((130, "L"), (140, "N"), (160, "FG")):
        s.term(xx, 168)
        s.text(xx + 1.3, 165.5, lab, fs=4.5, ha="left")
    s.pe([(160, 168.65), (160, 172), (172, 172), (172, 175)])
    s.text(173.5, 177, "-> BPE (PE2)", fs=4.6, ha="left", c=COL["PE"])
    s.line([(160, 168.6), (160, 168.7)])
    # PSU2
    s.rect(240, 143, 55, 25, lw=0.9)
    s.text(267.5, 160, "PSU2  Mean Well HDR-60-24", fs=6, w="bold")
    s.text(267.5, 155.2, "24 V DC  2,5 A  60 W", fs=5)
    s.text(267.5, 151, "classe II (senza morsetto FG)", fs=4.6, c="#444")
    for xx, lab in ((250, "L"), (260, "N")):
        s.term(xx, 168)
        s.text(xx + 1.3, 165.5, lab, fs=4.5, ha="left")

    # PSU3
    s.rect(320, 143, 50, 25, lw=0.9)
    s.text(345, 160, "PSU3  Mean Well HDR-15-12", fs=6, w="bold")
    s.text(345, 155.2, "12 V DC  1,25 A  15 W", fs=5)
    s.text(345, 151, "classe II - solo Arduino", fs=4.6, c="#444")
    for xx, lab in ((330, "L"), (340, "N")):
        s.term(xx, 168)
        s.text(xx + 1.3, 165.5, lab, fs=4.5, ha="left")


    # ---- distribuzione 48 V ----
    s.term(130, 143)
    s.term(150, 143)
    s.text(131.3, 145.3, "+V", fs=4.5, ha="left")
    s.text(151.3, 145.3, "-V", fs=4.5, ha="left")
    yP = 128
    xd = [45, 90, 135, 180]
    s.line([(130, 142.35), (130, yP)], c=COL["P48"], lw=1.1)
    s.dot(130, yP, c=COL["P48"])
    s.wn(130, 136, 201)
    s.line([(xd[0], yP), (xd[-1], yP)], c=COL["P48"], lw=1.1)
    s.text(xd[0] - 2, yP + 2.5, "+48 V  (X2:1-4 ponticellati)", fs=5, ha="left", c=COL["P48"])
    yM = 66
    s.line([(150, 142.35), (150, 139), (215, 139), (215, yM), (30, yM)], c=COL["M48"], lw=1.1)
    s.wn(215, 120, 202)
    s.term(215, 104)
    s.text(216.5, 104, "X2:5", fs=4.5, ha="left")
    s.text(140, yM - 2.6, "0V48  (X2:5-9 ponticellati)", fs=5, ha="left", c=COL["M48"])
    for i, (x, a) in enumerate(zip(xd, AXES)):
        if i not in (0, 3):
            s.dot(x, yP, c=COL["P48"])
        s.line([(x, yP), (x, 98)], c=COL["P48"])
        s.term(x, 122)
        s.text(x - 1.5, 122, f"X2:{1 + i}", fs=4.5, ha="right")
        s.wn(x, 116.5, 203 + i)
        s.sym("fuse", x, 109, "v")
        s.text(x - 2, 109, f"{a['f']}\n5 A T\n5x20", fs=4.6, ha="right")
        s.wn(x, 101.5, 207 + i)
        s.rect(x - 5, 80, 30, 18, lw=0.8)
        s.text(x + 10, 92.5, f"{a['u']}  CL57T", fs=5.4, w="bold")
        s.text(x + 10, 88.2, f"driver {a['ax']} ({a['m']})", fs=4.8)
        s.text(x + 10, 84.4, "segnali -> E03", fs=4.4, c="#444")
        s.term(x, 98)
        s.term(x + 18, 80)
        s.text(x + 1.3, 96, "+Vdc", fs=4.2, ha="left")
        s.text(x + 16.8, 82, "GND", fs=4.2, ha="right")
        s.line([(x + 18, 79.35), (x + 18, yM)], c=COL["M48"])
        s.dot(x + 18, yM, c=COL["M48"])
        s.term(x + 18, 73.5)
        s.text(x + 19.5, 73.5, f"X2:{6 + i}", fs=4.5, ha="left")
        s.wn(x + 18, 69.5, 211 + i)
    # ponte 0V48 - PE
    s.pe([(30, yM), (30, 51.2)])
    s.dot(30, yM, c=COL["M48"])
    s.dot(30, 50, c=COL["PE"])
    s.wn(30, 58, "PE7")
    s.text(31.8, 61.5, "ponte 0V48-PE (X2:5)", fs=4.5, ha="left", c=COL["PE"])

    # ---- distribuzione 24 V ----
    s.term(250, 143)
    s.term(285, 143)
    s.text(251.3, 145.3, "+V", fs=4.5, ha="left")
    s.text(286.3, 145.3, "-V", fs=4.5, ha="left")
    s.line([(250, 142.35), (250, 136)], c=COL["P24"])
    s.dot(250, 136, c=COL["P24"])
    s.line([(240, 136), (262, 136)], c=COL["P24"])
    for xx, f, n1, n2, xt, lab in ((240, "F4", 301, 304, "X3:1", "+24 V S\nsicurezza\n-> E02"),
                                   (262, "F5", 302, 305, "X3:5", "+24 V I/O\nsensori, rele',\ncolonna -> E02/E04")):
        s.line([(xx, 136), (xx, 104)], c=COL["P24"])
        s.wn(xx, 129.5, n1)
        s.sym("fuse", xx, 121, "v")
        s.text(xx - 2, 121, f"{f}\n2 A T", fs=4.6, ha="right")
        s.wn(xx, 112, n2)
        s.term(xx, 104)
        s.text(xx, 101.3, xt, fs=4.6, va="top", w="bold")
        s.text(xx, 97.6, lab, fs=4.4, va="top")
    s.line([(285, 142.35), (285, 104)], c=COL["M24"])
    s.wn(285, 129.5, 303)
    s.term(285, 104)
    s.text(285, 101.3, "X4:1", fs=4.6, va="top", w="bold")
    s.text(285, 97.6, "0V24\n-> E02/E04", fs=4.4, va="top")
    s.dot(285, 116, c=COL["M24"])
    s.pe([(285, 116), (296, 116), (296, 112)])
    s.earth(296, 112, "PE8 ponte\n0V24-PE", lab_dx=3.3)
    # ---- 12 V Arduino ----
    s.term(330, 143)
    s.term(350, 143)
    s.text(331.3, 145.3, "+V", fs=4.5, ha="left")
    s.text(351.3, 145.3, "-V", fs=4.5, ha="left")
    s.line([(330, 142.35), (330, 124)], c=COL["V5"])
    s.line([(350, 142.35), (350, 124)], c=COL["GND"])
    s.wn(330, 133, 701)
    s.wn(350, 133, 702)
    s.text(330, 122, "A1 Vin\n(jack DC)", fs=4.6, va="top")
    s.text(350, 122, "A1 GND\n-> E03", fs=4.6, va="top")

    # ---- barra PE ----
    yb = 50
    s.rect(22, yb - 1.2, 200, 2.4, lw=0.6, fc=COL["PE"], ec=COL["PE"], z=4)
    s.text(40, yb + 3.5, "BPE  barra di terra principale (PE) - morsetto di terra sulla piastra",
           fs=5.2, ha="left", w="bold", c=COL["PE"])
    items = [("PE1", "X0:PE\nrete"), ("PE3", "piastra di\nfondo"), ("PE4", "porta\n(treccia 6)"),
             ("PE2", "PSU1 FG"), ("PE5", "XP1 PE -> W9\ntelaio portale,\ncarcasse motori"),
             ("PE6", "XP2 PE\n(JB1 portale)"), ("PE8", "ponte 0V24\n(X4:1)"),
             ("PE9", "staffa schermi\ncavi motore/\nencoder")]
    for i, (n, lab) in enumerate(items):
        x = 50 + i * 21.5
        s.pe([(x, yb), (x, 44)])
        s.wn(x, 46.8, n)
        s.text(x, 41, lab, fs=4.4, va="top")
    # PE7 viene dal ponte 0V48 disegnato sopra (x=30). Ridisegno coerente: PE7 sta a x=30
    # note e legenda
    s.legend(318, 114, [("L", "L 230 V - marrone 1,5 mm2"), ("N", "N - blu chiaro 1,5 mm2"),
                        ("PE", "PE - giallo-verde"), ("P48", "+48 V - rosso 1,5 (2,5 PSU1-X2)"),
                        ("M48", "0V48 - nero 1,5 (2,5 PSU1-X2)"), ("P24", "+24 V - blu scuro"),
                        ("M24", "0V24 - blu/bianco"), ("V5", "+12 V Arduino - rosso"),
                        ], w=90)
    s.notes(300, 79, 108, [
        "Fusibili driver F11-F14: 5 A ritardati (T), uno per driver, sul +48 V.",
        "PSU1 alimentata solo con KM1 chiuso (catena di emergenza OK, E02).",
        "0V48 e 0V24 collegati a PE in un solo punto (PELV), ponti rimovibili.",
        "Telaio portale e carcasse motori a PE tramite XP1 + W9 (1x2,5).",
        "Taratura F1-F3 indicativa: verificare spunto PSU (curva gG/aM).",
        "Numeri in riquadro = numero filo (vedi README, tabella fili).",
    ], title="Note E01")
    s.save(pdf)


# --------------------------------------------------------------------------------------
# E02 - SICUREZZA
# --------------------------------------------------------------------------------------
def sheet_e02(pdf):
    s = Sheet(2, "Circuito di sicurezza", "Emergenza 2NC, relè di sicurezza K1, KM1 con retroazione, barriera LC1")
    s.heading("E02 - Sicurezza",
              "Emergenza e barriera: arresto cat. 0 per apertura di KM1 (48 V ai driver) + segnalazione all'Arduino (D2, D3)")
    yT, yB = 262, 62
    # binari
    s.line([(25, yT), (258, yT)], c=COL["P24"], lw=1.1)
    s.line([(268, yT), (405, yT)], c=COL["P24"], lw=1.1)
    s.line([(25, yB), (405, yB)], c=COL["M24"], lw=1.1)
    s.text(25, yT + 3, "+24 V S  (da F4 / X3:1, E01)", fs=5.5, ha="left", c=COL["P24"], w="bold")
    s.text(268, yT + 3, "+24 V I/O  (da F5 / X3:5, E01)", fs=5.5, ha="left", c=COL["P24"], w="bold")
    s.text(25, yB - 3, "0V24  (X4, collegato a PE tramite PE8)", fs=5.5, ha="left", c=COL["M24"], w="bold")
    # K1
    s.rect(34, 140, 161, 36, lw=1.0)
    s.text(114.5, 163, "K1  modulo relè di sicurezza 2 canali - cat. 3 / PL d (EN ISO 13849-1)", fs=6, w="bold")
    s.text(114.5, 157.5, "ingressi a 2 canali con rilevamento cortocircuito tra canali, reset manuale controllato S33-S34",
           fs=4.7)
    s.text(114.5, 153.5, "contatti di sicurezza 13-14, 23-24 (NO) - contatto ausiliario 43-44 (NO) per segnalazione",
           fs=4.7)
    s.text(114.5, 148.5, "es. Pilz PNOZ X2.8P, Schmersal SRB 301MC o equivalente 24 V DC  -  verificare morsetti sul manuale",
           fs=4.5, style="italic", c="#444")
    tops = [("A1", 42), ("S11", 62), ("S12", 84), ("S21", 104), ("S22", 126), ("S33", 146), ("S34", 188)]
    for lab, x in tops:
        s.term(x, 176)
        s.text(x + 1.2, 173.4, lab, fs=4.6, ha="left")
    s.term(42, 140)
    s.text(43.2, 142.6, "A2", fs=4.6, ha="left")
    # A1 / A2
    s.line([(42, yT), (42, 176.65)], c=COL["P24"])
    s.dot(42, yT, c=COL["P24"])
    s.term(42, 250)
    s.text(43.5, 250, "X3:2", fs=4.5, ha="left")
    s.wn(42, 236, 310)
    s.line([(42, 139.35), (42, yB)], c=COL["M24"])
    s.dot(42, yB, c=COL["M24"])
    s.wn(42, 100, 311)
    s.term(42, 70)
    s.text(43.5, 70, "X4:2", fs=4.5, ha="left")
    # S0 canali
    yl = 212
    for (xa, xb, n1, n2, c1, c2) in ((62, 84, 312, 313, "11", "12"), (104, 126, 314, 315, "21", "22")):
        xm = (xa + xb) / 2
        s.line([(xa, 176.65), (xa, yl), (xm - 3, yl)], c=COL["P24"])
        s.sym("mush_nc", xm, yl, "h") if xa == 62 else s.sym("nc", xm, yl, "h")
        s.line([(xm + 3, yl), (xb, yl), (xb, 176.65)], c=COL["P24"])
        s.wn(xa, 194, n1)
        s.wn(xb, 194, n2)
        s.text(xm - 3.2, yl - 2.2, c1, fs=4.2)
        s.text(xm + 3.2, yl - 2.2, c2, fs=4.2)
    # collegamento meccanico S0
    s.line([(73.35, yl + 3.4), (115.35, yl + 3.4)], ls=(0, (1.5, 1)), lw=0.6)
    s.line([(115.35, yl + 3.4), (115.35, yl - 0.85)], ls=(0, (1.5, 1)), lw=0.6)
    s.text(56, 227, "S0  fungo di emergenza 2NC, a ritenuta (porta quadro)", fs=5.4, ha="left", w="bold")
    s.text(56, 222.8, "canale 1: 11-12   canale 2: 21-22", fs=4.6, ha="left")
    # reset loop
    s.line([(146, 176.65), (146, yl), (154, yl)], c=COL["P24"])
    s.sym("pb_no", 157, yl, "h")
    s.line([(160, yl), (169, yl)], c=COL["P24"])
    s.sym("nc", 172, yl, "h")
    s.line([(175, yl), (188, yl), (188, 176.65)], c=COL["P24"])
    s.wn(146, 194, 316)
    s.wn(164.5, yl, 317)
    s.wn(188, 194, 318)
    s.text(153.8, yl - 2.2, "13", fs=4.2)
    s.text(160.2, yl - 2.2, "14", fs=4.2)
    s.text(168.8, yl - 2.2, "21", fs=4.2)
    s.text(175.2, yl - 2.2, "22", fs=4.2)
    s.text(150, 222.8, "S1 RESET\n(pulsante blu NO)", fs=4.8, ha="center", va="bottom", w="bold")
    s.text(176, 222.8, "KM1 21-22\nretroazione NC", fs=4.8, ha="center", va="bottom", w="bold")
    s.text(167, 201, "reset possibile solo con\nKM1 diseccitato (NC chiuso)", fs=4.4, style="italic", c="#444")
    # colonna KM1
    xk = 218
    s.dot(xk, yT, c=COL["P24"])
    s.line([(xk, yT), (xk, 243)], c=COL["P24"])
    s.term(xk, 252)
    s.text(xk + 1.5, 252, "X3:3", fs=4.5, ha="left")
    s.sym("no", xk, 240, "v")
    s.line([(xk, 237), (xk, 218)], c=COL["P24"])
    s.sym("no", xk, 215, "v")
    s.line([(xk, 212), (xk, 113)], c=COL["P24"])
    s.sym("coil", xk, 110, "v")
    s.line([(xk, 107), (xk, yB)], c=COL["M24"])
    s.dot(xk, yB, c=COL["M24"])
    s.wn(xk, 248, 319)
    s.wn(xk, 228, 320)
    s.wn(xk, 160, 321)
    s.wn(xk, 98, 322)
    s.term(xk, 70)
    s.text(xk + 1.5, 70, "X4:3", fs=4.5, ha="left")
    s.text(xk + 2.6, 241.5, "K1", fs=5, ha="left", w="bold")
    s.text(xk + 2.6, 238, "13-14", fs=4.5, ha="left")
    s.text(xk + 2.6, 216.5, "K1", fs=5, ha="left", w="bold")
    s.text(xk + 2.6, 213, "23-24", fs=4.5, ha="left")
    s.text(xk - 3.6, 112, "KM1", fs=5.5, ha="right", w="bold")
    s.text(xk - 3.6, 108, "A1-A2 24 V DC", fs=4.4, ha="right")
    s.text(xk - 3.6, 104.5, "+ soppressore", fs=4.4, ha="right")
    s.text(xk + 3.5, 101, "1-2  L PSU1 /E01\n3-4  N PSU1 /E01\n21-22 NC /E02", fs=4.3, ha="left", va="top",
           family="DejaVu Sans Mono")
    # colonna K1 43-44 -> U7 IN1
    xa = 245
    s.dot(xa, yT, c=COL["P24"])
    s.line([(xa, yT), (xa, 243)], c=COL["P24"])
    s.term(xa, 252)
    s.text(xa + 1.5, 252, "X3:4", fs=4.5, ha="left")
    s.sym("no", xa, 240, "v")
    s.line([(xa, 237), (xa, 132)], c=COL["P24"])
    s.wn(xa, 248, 323)
    s.wn(xa, 190, 324)
    s.text(xa + 2.6, 241.5, "K1", fs=5, ha="left", w="bold")
    s.text(xa + 2.6, 238, "43-44", fs=4.5, ha="left")
    s.rect(236, 116, 26, 16, lw=0.8)
    s.term(xa, 132)
    s.text(249, 127.5, "U7:IN1", fs=5, w="bold")
    s.text(249, 123.2, "-> D2 ESTOP_OK", fs=4.5)
    s.text(249, 119.4, "(vedi E04)", fs=4.3, c="#444")
    # barriera
    xt = 282
    s.dot(xt, yT, c=COL["P24"])
    s.line([(xt, yT), (xt, 222)], c=COL["P24"])
    s.term(xt, 255)
    s.text(xt + 1.5, 255, "X3:6", fs=4.5, ha="left")
    s.wn(xt, 232, 330)
    s.rect(274, 202, 18, 20, lw=0.8)
    s.text(283, 214, "LC1-TX", fs=5, w="bold")
    s.text(283, 209.5, "emettitore", fs=4.4)
    s.text(283, 206, "(W20)", fs=4.4, c="#444")
    s.line([(xt, 202), (xt, yB)], c=COL["M24"])
    s.dot(xt, yB, c=COL["M24"])
    s.wn(xt, 150, 331)
    s.term(xt, 70)
    s.text(xt + 1.5, 70, "X4:4", fs=4.5, ha="left")
    # ricevitore
    s.dot(312, yT, c=COL["P24"])
    s.line([(312, yT), (312, 222)], c=COL["P24"])
    s.term(312, 255)
    s.text(313.5, 255, "X3:7", fs=4.5, ha="left")
    s.wn(312, 232, 332)
    s.rect(303, 202, 52, 20, lw=0.8)
    s.text(329, 215.5, "LC1-RX  ricevitore (W21)", fs=5, w="bold")
    s.text(329, 211.6, "barriera di sicurezza tipo 4 (IEC 61496)", fs=4.3)
    s.text(329, 208.2, "OSSD1/OSSD2 PNP: 24 V = campo libero", fs=4.3)
    for xx, lab in ((312, "0V"), (330, "OSSD1"), (348, "OSSD2")):
        s.term(xx, 202)
        s.text(xx + 1.2, 199.6, lab, fs=4.2, ha="left")
    s.line([(312, 201.35), (312, yB)], c=COL["M24"])
    s.dot(312, yB, c=COL["M24"])
    s.wn(312, 150, 333)
    s.term(312, 70)
    s.text(313.5, 70, "X4:5", fs=4.5, ha="left")
    for xx, k, n1, n2, xt4 in ((330, "K2", 334, 335, "X4:6"), (348, "K3", 336, 337, "X4:7")):
        s.line([(xx, 201.35), (xx, 153)], c=COL["P24"])
        s.sym("coil", xx, 150, "v")
        s.line([(xx, 147), (xx, yB)], c=COL["M24"])
        s.dot(xx, yB, c=COL["M24"])
        s.wn(xx, 175, n1)
        s.wn(xx, 110, n2)
        s.text(xx + 3.6, 151.5, k, fs=5.5, ha="left", w="bold")
        s.text(xx + 3.6, 147.8, "24 V DC", fs=4.3, ha="left")
        s.term(xx, 70)
        s.text(xx + 1.5, 70, xt4, fs=4.5, ha="left")
    s.text(351.5, 138, "K2, K3: relè di\ninterfaccia 24 V DC\n1 contatto 11-14\nes. Finder 38.51", fs=4.3,
           c="#444", ha="left")
    # contatti K2 K3 in serie
    xc = 382
    s.dot(xc, yT, c=COL["P24"])
    s.line([(xc, yT), (xc, 218)], c=COL["P24"])
    s.term(xc, 255)
    s.text(xc + 1.5, 255, "X3:8", fs=4.5, ha="left")
    s.wn(xc, 236, 338)
    s.sym("no", xc, 215, "v")
    s.line([(xc, 212), (xc, 188)], c=COL["P24"])
    s.wn(xc, 200, 339)
    s.sym("no", xc, 185, "v")
    s.line([(xc, 182), (xc, 132)], c=COL["P24"])
    s.wn(xc, 160, 340)
    s.text(xc + 2.6, 216.5, "K2", fs=5, ha="left", w="bold")
    s.text(xc + 2.6, 213, "11-14", fs=4.5, ha="left")
    s.text(xc + 2.6, 186.5, "K3", fs=5, ha="left", w="bold")
    s.text(xc + 2.6, 183, "11-14", fs=4.5, ha="left")
    s.rect(369, 116, 32, 16, lw=0.8)
    s.term(xc, 132)
    s.text(385, 127.5, "U7:IN2", fs=5, w="bold")
    s.text(385, 123.2, "-> D3 CURTAIN_OK", fs=4.5)
    s.text(385, 119.4, "(vedi E04)", fs=4.3, c="#444")
    # note
    s.notes(50, 134, 156, [
        "Funzionamento: S0 e LC1 indipendenti. Con S0 rilasciato e KM1 diseccitato, premendo S1 K1 si arma:",
        "13-14 e 23-24 chiudono -> KM1 eccitato -> 230 V a PSU1 -> 48 V ai driver. 43-44 chiude -> D2 BASSO.",
        "Premendo S0: K1 apre -> KM1 cade -> driver senza potenza (arresto cat. 0) -> D2 ALTO (ESTOP).",
        "Z1/Z2 a vite trapezia autobloccante: il rullo non scende senza potenza. X si arresta per attrito.",
        "LC1 (come da SPEC) agisce SOLO via firmware (D3): non è una funzione di sicurezza cablata.",
        "Per PL d reale: portare OSSD1/OSSD2 in un secondo modulo di sicurezza (o K1 a 2 ingressi",
        "di tipo OSSD) che agisce su KM1, e raddoppiare KM1 con KM2 in serie (contatti a specchio",
        "in serie nel loop di retroazione S33-S34). Valutazione rischi e PL a cura del progettista",
        "della macchina (Direttiva Macchine / Reg. UE 2023/1230, EN ISO 13849-1, CEI EN 60204-1).",
        "Contatti disegnati a riposo, circuito non alimentato. Numeri in riquadro = n. filo.",
    ], title="Note E02 - logica di sicurezza", fs=4.9, lh=3.05)
    s.save(pdf)


# --------------------------------------------------------------------------------------
# E03 - ARDUINO E DRIVER
# --------------------------------------------------------------------------------------
def sheet_e03(pdf):
    s = Sheet(3, "Arduino Mega e driver CL57T", "Step/Dir/Enable/Alarm a catodo comune 5 V, fasi motore ed encoder")
    s.heading("E03 - Arduino e driver",
              "Ingressi CL57T optoisolati 5 V a catodo comune: X+ <- pin Arduino, X- -> GND logica (X6). "
              "ENA: pin ALTO = driver DISABILITATO. ALM: uscita opto -> pin INPUT_PULLUP, BASSO = allarme.")
    # Arduino
    ax0, ax1 = 25, 85
    s.rect(ax0, 50, ax1 - ax0, 222, lw=1.1)
    s.text(55, 268, "A1", fs=8, w="bold")
    s.text(55, 263.5, "Arduino Mega 2560 Rev3", fs=5.5, w="bold")
    s.text(55, 259.8, "+ Ethernet Shield 2 (W5500)", fs=5)
    s.text(55, 256.3, "connessioni via screw-shield", fs=4.4, c="#444")
    pitch = 4.2
    sec = 51.5
    for i, a in enumerate(AXES):
        yt = 250 - i * sec
        offs_sig = [0, 1, 2, 3]
        names = [("PUL+", a["pul"], COL["SIG"]), ("DIR+", a["dir"], COL["SIG"]), ("ENA+", a["ena"], COL["SIG"]),
                 ("ALM+", a["alm"], COL["ALM"])]
        minus = ["PUL-", "DIR-", "ENA-", "ALM-"]
        dx0, dx1 = 165, 215
        top = yt + 3.5
        bot = yt - 10 * pitch - 3.5
        s.rect(dx0, bot, dx1 - dx0, top - bot, lw=1.0)
        s.text(192, yt - 3.6 * pitch, f"{a['u']}", fs=8, w="bold")
        s.text(192, yt - 4.7 * pitch, "driver CL57T", fs=5, w="bold")
        s.text(192, yt - 5.6 * pitch, f"asse {a['ax']} ({a['m']})", fs=5)
        s.text(192, yt - 6.6 * pitch, f"{a['ppr']} imp/giro - SW: README", fs=4.2, c="#444")
        # pin arduino + linee
        for k, (nm, pin, cc) in enumerate(names):
            y = yt - k * pitch
            s.text(ax1 - 1.2, y, f"D{pin}", fs=5, ha="right", w="bold")
            s.text(ax0 + 1.5, y, f"{a['ax']}_{nm[:3]}", fs=4.6, ha="left", c="#333")
            s.term(ax1, y)
            s.term(dx0, y)
            s.line([(ax1 + 0.65, y), (dx0 - 0.65, y)], c=cc)
            s.text(dx0 + 1.3, y, nm, fs=4.4, ha="left")
            s.wn(118 + (k % 2) * 14, y, a["wn"] + k + 1)
            if nm == "ALM+":
                s.ax.annotate("", xy=(ax1 + 3.5, y), xytext=(ax1 + 8.5, y),
                              arrowprops=dict(arrowstyle="-|>", lw=0.5, color=cc, mutation_scale=5), zorder=6)
            else:
                s.ax.annotate("", xy=(dx0 - 3.5, y), xytext=(dx0 - 8.5, y),
                              arrowprops=dict(arrowstyle="-|>", lw=0.5, color=cc, mutation_scale=5), zorder=6)
        # GND comune
        ys = [yt - (4 + k) * pitch for k in range(4)]
        for k, y in enumerate(ys):
            s.term(dx0, y)
            s.text(dx0 + 1.3, y, minus[k], fs=4.4, ha="left")
            s.line([(158, y), (dx0 - 0.65, y)], c=COL["GND"])
            s.dot(158, y) if k not in (0, 3) else None
        s.line([(158, ys[0]), (158, ys[-1])], c=COL["GND"])
        s.dot(158, ys[0])
        s.line([(ax1 + 0.65, ys[0]), (158, ys[0])], c=COL["GND"])
        s.term(ax1, ys[0])
        s.text(ax1 - 1.2, ys[0], "GND", fs=5, ha="right", w="bold")
        s.term(140, ys[0])
        s.text(140, ys[0] + 2, a["gnd"], fs=4.4)
        s.wn(118, ys[0], a["wn"] + 5)
        s.text(156.8, ys[2], "ponticelli", fs=3.8, ha="right", c="#555")
        # alimentazione driver
        for k, (nm, cc, lab) in enumerate((("+Vdc", COL["P48"], f"+48 V da {a['f']} (E01) - filo {207 + i}"),
                                           ("GND", COL["M48"], f"0V48 da X2:{6 + i} (E01) - filo {211 + i}"))):
            y = yt - (8.4 + k * 1.15) * pitch
            s.term(dx0, y)
            s.text(dx0 + 1.3, y, nm, fs=4.4, ha="left")
            s.line([(146, y), (dx0 - 0.65, y)], c=cc, lw=1.0)
            s.text(145, y, lab, fs=4.3, ha="right", c=cc)
        # lato motore
        xr = dx1
        xh = 262
        xm = 345
        mp = []
        for k, (nm, col) in enumerate(MOTOR_COLORS):
            y = yt - k * pitch
            mp.append(y)
            s.term(xr, y)
            s.text(xr - 1.3, y, nm, fs=4.4, ha="right")
            pin = f"{a['mod_p']}{a['p0'] + k}"
            s.line([(xr + 0.65, y), (xh, y)], c=COL["MOT"])
            s.wn(237, y, 801 + i * 4 + k)
            s.text(xh + 1.5, y + 1.3, pin, fs=4.2, ha="left", w="bold")
            s.line([(xh, y), (xm - 12, y)], c=COL["MOT"])
            s.text(xh + 12, y + 1.3, col, fs=4.0, ha="left", c="#444")
        cy = (mp[0] + mp[-1]) / 2
        r = 7.3
        for y in mp:
            dy = y - cy
            xe = xm - math.sqrt(max(r * r - dy * dy, 0))
            s.line([(xm - 12, y), (xe, y)], c=COL["MOT"])
        s.ax.add_patch(Circle((xm, cy), r, fc="white", ec="k", lw=0.9, zorder=4))
        s.text(xm, cy + 0.8, "M", fs=8, w="bold")
        s.text(xm, cy - 3.2, a["m"], fs=4.6)
        # encoder
        ep = []
        for k, (nm, col) in enumerate(ENC_COLORS):
            y = yt - (4 + k * 0.97) * pitch - 1.2
            ep.append(y)
            s.term(xr, y)
            s.text(xr - 1.3, y, nm, fs=4.2, ha="right")
            pin = f"{a['mod_e']}{a['e0'] + k}"
            s.line([(xr + 0.65, y), (xm - 8, y)], c=COL["ENC"], lw=0.6)
            s.wn(229 + (k % 2) * 13, y, 821 + i * 6 + k)
            s.text(xh + 1.5, y + 1.2, pin, fs=4.0, ha="left", w="bold")
            s.text(xh + 12, y + 1.2, col, fs=3.8, ha="left", c="#444")
        s.rect(xm - 8, ep[-1] - 2, 16, ep[0] - ep[-1] + 4, lw=0.8, z=4)
        s.text(xm, (ep[0] + ep[-1]) / 2, "ENC\n1000 lin.", fs=4.4, z=6)
        s.line([(xm, ep[0] + 2), (xm, cy - r)], lw=1.4, c="#555")  # albero comune
        # schermi
        s.ax.add_patch(Ellipse((300, cy), 4, (mp[0] - mp[-1]) + 4.5, fc="none", ec="#444", lw=0.6, ls="--",
                               zorder=6))
        s.ax.add_patch(Ellipse((306, (ep[0] + ep[-1]) / 2), 4, (ep[0] - ep[-1]) + 4, fc="none", ec="#444",
                               lw=0.6, ls="--", zorder=6))
        s.text(300, mp[0] + 2.3, f"{a['wp']} 4x1,0 sch.", fs=4.2, c="#333")
        s.text(316, ep[-1] - 3.2, f"{a['we']} encoder sch.", fs=4.2, c="#333")
        # info motore
        s.text(356, cy + 3, f"{a['m']}  NEMA23 closed-loop", fs=5, ha="left", w="bold")
        s.text(356, cy - 0.6, f"asse {a['ax']}: {a['desc']}", fs=4.4, ha="left")
        s.text(356, cy - 4.0, f"driver {a['ppr']} imp/giro", fs=4.4, ha="left")
    # connettore XP1
    s.line([(262, 270), (262, 52)], lw=2.0, c="#555", ls=(0, (4, 2)))
    s.text(262, 276.5, "XP1  Harting Han-Modular 24B", fs=5.5, w="bold")
    s.text(262, 273, "a,b: Han EE 8p (fasi) - c,d: Han DD 12p (encoder) - PE telaio", fs=4.3)
    s.text(258, 54, "quadro", fs=4.5, ha="right", c="#555")
    s.text(266, 54, "portale (catena portacavi)", fs=4.5, ha="left", c="#555")
    s.text(300, 268.5, "schermi: a PE solo lato quadro (staffa/pressacavo EMC, PE9)", fs=4.3, c="#333")
    # alimentazione arduino
    yb = 58
    s.text(27, yb + 12, "Alimentazione A1:", fs=4.8, ha="left", w="bold")
    s.text(27, yb + 8, "Vin (jack) <- PSU3 +12 V (701)", fs=4.4, ha="left")
    s.text(27, yb + 4.6, "GND <- PSU3 -V (702)", fs=4.4, ha="left")
    s.text(27, yb + 1.2, "5V -> X7:1 (400)  GND -> X6:1 (401)", fs=4.4, ha="left")
    s.text(27, yb - 2.4, "RJ45 -> W23 -> switch VLAN IoT", fs=4.4, ha="left")
    s.text(27, yb - 5.6, "D4, D10, D50-D53: riservati shield", fs=4.4, ha="left", c=COL["P48"])
    s.save(pdf)


# --------------------------------------------------------------------------------------
# E04 - INGRESSI / USCITE
# --------------------------------------------------------------------------------------
def sheet_e04(pdf):
    s = Sheet(4, "Ingressi e uscite", "Sensori induttivi PNP, pulsanti, schede optoisolate U6/U7, relè U8, colonna luminosa")
    s.heading("E04 - Ingressi / uscite",
              "Ingressi 24 V -> PC817 -> pin INPUT_PULLUP: ingresso a 24 V = pin BASSO (attivo). "
              "Uscite D5-D8 -> modulo relè U8 (attivo ALTO) -> colonna luminosa 24 V.")
    xo, xi = 22, 28  # bus +24 (esterno), 0V (interno)
    xh = 100  # XP2
    rows = [240 - i * 11.5 for i in range(8)]
    for i, (b, sig, pin, ch, xp, pos) in enumerate(SENSORS):
        y = rows[i]
        s.rect(38, y - 4.2, 24, 8.4, lw=0.8)
        s.text(50, y + 1.6, f"{b}  {sig}", fs=4.9, w="bold")
        s.text(50, y - 1.9, "M12 PNP NO", fs=4.0, c="#444")
        s.ax.add_patch(Polygon([(58.6, y - 1.4), (60, y), (58.6, y + 1.4), (57.2, y)], closed=True, fc="none",
                               ec="k", lw=0.5, zorder=5))
        # BN
        s.hhop(y + 2.4, xo, 38, hops=[xi], c=COL["BN"])
        s.dot(xo, y + 2.4, c=COL["BN"])
        s.text(36.8, y + 3.4, "BN", fs=3.6, ha="right", c=COL["BN"])
        # BU
        s.line([(xi, y - 2.4), (38, y - 2.4)], c=COL["BU"])
        s.dot(xi, y - 2.4, c=COL["BU"])
        s.text(36.8, y - 1.4, "BU", fs=3.6, ha="right", c=COL["BU"])
        # BK
        s.line([(62, y), (xh, y)], c=COL["BK"])
        s.text(64, y + 1.2, "BK", fs=3.6, ha="left")
        s.text(81, y + 1.5, pos, fs=3.7, c="#555")
        s.text(xh - 1.2, y - 1.4, str(xp), fs=4.2, ha="right", w="bold")
    yb_top = rows[-1] - 2.4
    s.line([(xo, rows[-1] + 2.4), (xo, 260), (xh, 260)], c=COL["BN"], lw=0.9)
    s.line([(xi, yb_top), (xi, 256), (xh, 256)], c=COL["BU"], lw=0.9)
    s.text(xh - 1.2, 260 + 1.3, "1", fs=4.2, ha="right", w="bold")
    s.text(xh - 1.2, 256 + 1.3, "2", fs=4.2, ha="right", w="bold")
    s.text(45, 262, "+24 V sensori (BN)", fs=4.3, c=COL["BN"])
    s.text(45, 253.8, "0V (BU)", fs=4.3, c=COL["BU"])
    s.text(16.5, 198, "distribuzione +24/0V in JB1 (portale), cavi M12 W11-W18", fs=4.4, rot=90, c="#444")
    # XP2
    s.line([(xh, 264), (xh, 150)], lw=2.0, c="#555", ls=(0, (4, 2)))
    s.text(xh, 146.5, "XP2  Harting Han 10 E\n(+PE)  cavo W10", fs=4.8, w="bold", va="top")
    s.text(xh - 3, 265.6, "portale", fs=4.2, ha="right", c="#555")
    s.text(xh + 3, 265.6, "quadro", fs=4.2, ha="left", c="#555")
    # +24/0V lato quadro
    s.line([(xh, 260), (134, 260)], c=COL["P24"])
    s.line([(xh, 256), (134, 256)], c=COL["M24"])
    s.term(134.65, 260)
    s.term(134.65, 256)
    s.wn(118, 260, 350)
    s.wn(118, 256, 351)
    s.text(136.5, 260, "X3:11  +24 V I/O (F5)", fs=4.4, ha="left")
    s.text(136.5, 256, "X4:9  0V24", fs=4.4, ha="left")
    # U6
    u6x0, u6x1 = 150, 192
    s.rect(u6x0, rows[-1] - 7, u6x1 - u6x0, rows[0] - rows[-1] + 12, lw=1.0)
    s.text(171, (rows[0] + rows[-1]) / 2, "U6  scheda optoisolata 8 canali PC817  24 V -> 5 V", fs=5.4, rot=90,
           w="bold")
    for i, (b, sig, pin, ch, xp, pos) in enumerate(SENSORS):
        y = rows[i]
        s.line([(xh, y), (u6x0 - 0.65, y)], c=COL["P24"])
        s.term(u6x0, y)
        s.text(u6x0 + 1.3, y, ch, fs=4.3, ha="left")
        s.wn(125, y, 352 + i)
        s.term(u6x1, y)
        s.text(u6x1 - 1.3, y, f"OUT{i + 1}", fs=4.3, ha="right")
        s.line([(u6x1 + 0.65, y), (254.35, y)], c=COL["ALM"])
        s.wn(222, y, 501 + i)
    # U6 alimentazioni (in basso)
    yb6 = rows[-1] - 7
    for xx, lab, n, c in ((155, "COM", 360, COL["M24"]), (174, "VCC", 509, COL["V5"]), (186, "GND", 510, COL["GND"])):
        s.term(xx, yb6)
        s.text(xx, yb6 + 2, lab, fs=3.9)
        s.line([(xx, yb6 - 0.65), (xx, yb6 - 5)], c=c)
    s.text(155, yb6 - 6.8, "X4:10 0V24 (360)", fs=4.2, ha="center")
    s.text(174, yb6 - 10.0, "X7:2 +5V (509)", fs=4.2, ha="center")
    s.text(194, yb6 - 6.8, "X6:6 GND (510)", fs=4.2, ha="center")
    s.line([(174, yb6 - 5), (174, yb6 - 8.3)], c=COL["V5"])
    # U7
    r7 = [128, 117, 106, 95]
    u7top, u7bot = 134, 88
    s.rect(u6x0, u7bot, u6x1 - u6x0, u7top - u7bot, lw=1.0)
    s.text(171, (u7top + u7bot) / 2, "U7  optoisolata\n8 can. (4 usati)", fs=5, w="bold")
    src = [("K1:44  (E02, filo 324)", None), ("K3:14  (E02, filo 340)", None)]
    for i, (ch, sig, pin, srcd) in enumerate(U7_INPUTS):
        y = r7[i]
        s.term(u6x0, y)
        s.text(u6x0 + 1.3, y, ch, fs=4.3, ha="left")
        s.term(u6x1, y)
        s.text(u6x1 - 1.3, y, f"OUT{i + 1}", fs=4.3, ha="right")
        s.line([(u6x1 + 0.65, y), (254.35, y)], c=COL["ALM"])
        s.wn(222, y, 511 + i)
        if i < 2:
            s.line([(106, y), (u6x0 - 0.65, y)], c=COL["P24"])
            s.term(105.35, y)
            s.text(103.5, y, src[i][0], fs=4.4, ha="right")
            s.text(128, y + 1.6, sig, fs=4.0, c="#444")
        else:
            xt = 66
            s.term(xt, y)
            s.text(xt - 1.6, y, "X3:9 +24 V" if i == 2 else "X3:10 +24 V", fs=4.4, ha="right")
            s.line([(xt + 0.65, y), (97, y)], c=COL["P24"])
            s.sym("pb_no" if i == 2 else "pb_nc", 100, y, "h")
            s.line([(103, y), (u6x0 - 0.65, y)], c=COL["P24"])
            s.wn(84, y, 341 if i == 2 else 343)
            s.wn(128, y, 342 if i == 2 else 344)
            s.text(108, y + 2.6, "S2 START (NO, verde)" if i == 2 else "S3 STOP (NC, nero)", fs=4.4,
                   ha="left", w="bold")
            s.text(97.2, y - 2.1, "13" if i == 2 else "11", fs=3.8)
            s.text(102.8, y - 2.1, "14" if i == 2 else "12", fs=3.8)
    for xx, lab, n, c, t in ((155, "COM", 345, COL["M24"], "X4:8 0V24 (345)"),
                             (174, "VCC", 515, COL["V5"], "X7:3 +5V (515)"),
                             (186, "GND", 516, COL["GND"], "X6:7 GND (516)")):
        s.term(xx, u7bot)
        s.text(xx, u7bot + 2, lab, fs=3.9)
        s.line([(xx, u7bot - 0.65), (xx, u7bot - (5 if xx != 174 else 8.3))], c=c)
    s.text(155, u7bot - 6.8, "X4:8 0V24 (345)", fs=4.2)
    s.text(174, u7bot - 10.0, "X7:3 +5V (515)", fs=4.2)
    s.text(194, u7bot - 6.8, "X6:7 GND (516)", fs=4.2)
    s.notes(22, 70, 190, [
        "Sensori: induttivi M12 PNP NO 24 V, 3 fili: BN = +24 V, BU = 0V, BK = uscita (24 V con target presente).",
        "Logica: target presente -> 24 V su INx -> fototransistor ON -> OUTx a GND -> pin BASSO = attivo.",
        "SEAT_A/SEAT_B BASSO = portale in sede. Filo rotto o +24 V mancante = ingresso ALTO (non attivo).",
        "S3 STOP è NC: a riposo D49 BASSO; premuto o filo interrotto -> D49 ALTO (come da SPEC).",
        "D2 ESTOP_OK e D3 CURTAIN_OK: BASSO = OK. Mancanza 24 V -> ALTO = emergenza (fail-safe).",
        "U6/U7: schede PC817 con ingresso per segnali PNP (comune 0V) e uscita open collector verso",
        "Arduino (VCC = +5 V logica). Verificare sulla scheda acquistata la polarità del comune.",
        "12 ingressi totali: servono 2 schede da 8 canali (U6 sensori, U7 sicurezza/pulsanti).",
    ], title="Note E04 - ingressi", fs=4.8, lh=2.95)
    # Arduino parziale
    axa, axb = 255, 292
    s.rect(axa, 72, axb - axa, 194, lw=1.1)
    s.text(273.5, 170, "A1  Arduino Mega 2560 (vista parziale - vedi E03)", fs=6, rot=90, w="bold")
    for i, (b, sig, pin, ch, xp, pos) in enumerate(SENSORS):
        s.term(axa, rows[i])
        s.text(axa + 1.4, rows[i] + 1.5, f"D{pin}", fs=4.7, ha="left", w="bold")
        s.text(axa + 1.4, rows[i] - 1.6, sig, fs=3.6, ha="left", c="#444")
    for i, (ch, sig, pin, srcd) in enumerate(U7_INPUTS):
        s.term(axa, r7[i])
        s.text(axa + 1.4, r7[i] + 1.5, f"D{pin}", fs=4.7, ha="left", w="bold")
        s.text(axa + 1.4, r7[i] - 1.6, sig, fs=3.6, ha="left", c="#444")
    # uscite -> U8
    r8 = [240, 230, 220, 210]
    u8x0, u8x1 = 314, 352
    for i, (pin, ch, h, desc) in enumerate(OUTPUTS):
        y = r8[i]
        s.term(axb, y)
        s.text(axb - 1.4, y + 1.5, f"D{pin}", fs=4.7, ha="right", w="bold")
        s.text(axb - 1.4, y - 1.6, desc.split()[-1].lower(), fs=3.6, ha="right", c="#444")
        s.line([(axb + 0.65, y), (u8x0 - 0.65, y)], c=COL["SIG"])
        s.wn(303, y, 601 + i)
        s.term(u8x0, y)
        s.text(u8x0 + 1.3, y, ch, fs=4.3, ha="left")
    for y, lab, n, c, t in ((200, "VCC", 605, COL["V5"], "+5V"), (192, "GND", 606, COL["GND"], "GND")):
        s.term(axb, y)
        s.text(axb - 1.4, y, t, fs=4.5, ha="right", w="bold")
        s.line([(axb + 0.65, y), (u8x0 - 0.65, y)], c=c)
        s.wn(303, y, n)
        s.term(u8x0, y)
        s.text(u8x0 + 1.3, y, lab, fs=4.3, ha="left")
    s.text(303, 188.2, "via X7:4 / X6:8", fs=3.8, c="#444")
    u8b, u8t = 174, 248
    s.rect(u8x0, u8b, u8x1 - u8x0, u8t - u8b, lw=1.0)
    s.text(333, 244, "U8  modulo relè 4 can. 5 V", fs=4.6, w="bold")
    s.text(333, 180.5, "ingressi optoisolati\ntrigger ALTO\ncontatti 10 A", fs=3.9, c="#444")
    # COM in alto
    s.term(345, u8t)
    s.text(345, u8t - 2, "COM", fs=3.8)
    s.line([(345, u8t + 0.65), (345, 258)], c=COL["P24"])
    s.term(345, 258.65)
    s.text(343.5, 261.3, "X3:12 +24 V (370)", fs=4.3, ha="right")
    s.text(347, 252, "COM1-4\nponticellati", fs=3.6, ha="left", c="#444")
    # contatti / lampade
    xl = 377
    xc = 398
    labels = ["H1 verde", "H2 giallo", "H3 rosso", "H4 buzzer"]
    for i, (pin, ch, h, desc) in enumerate(OUTPUTS):
        y = r8[i]
        s.term(u8x1, y)
        s.text(u8x1 - 1.3, y, f"NO{i + 1}", fs=4.3, ha="right")
        s.line([(u8x1 + 0.65, y), (xl - 3, y)], c=COL["P24"])
        s.wn(362, y, 371 + i)
        s.sym("buzzer" if i == 3 else "lamp", xl, y, "h")
        s.line([(xl + 3, y), (xc, y)], c=COL["M24"])
        s.text(xl, y + 3.6, labels[i], fs=4.2, w="bold")
        if i > 0:
            s.dot(xc, y, c=COL["M24"])
    s.line([(xc, r8[0]), (xc, 196)], c=COL["M24"])
    s.term(xc, 195.35)
    s.text(xc, 192.6, "X4:11\n0V24\n(375)", fs=4.2, va="top")
    s.rect(368, 204, 37, 45, lw=0.5, ls=(0, (3, 1.5)), fc="none")
    s.text(386.5, 251, "colonna luminosa 24 V (W22)", fs=4.3)
    # JD-VCC e DC/DC U9
    for xx, lab, n, c in ((322, "JD-VCC", 382, COL["V5"]), (338, "GND(JD)", 383, COL["GND"])):
        s.term(xx, u8b)
        s.text(xx, u8b + 2.2, lab, fs=3.6)
        s.line([(xx, u8b - 0.65), (xx, 159)], c=c)
        s.wn(xx, 166, n)
    s.rect(314, 143, 38, 16, lw=0.9, ls=(0, (3, 1.5)))
    s.text(333, 154.5, "U9  DC/DC 24 -> 5 V 1 A", fs=4.6, w="bold")
    s.text(333, 150.6, "(consigliato, guida DIN)", fs=4.0, c="#444")
    s.text(333, 147.0, "alimenta solo bobine U8", fs=4.0, c="#444")
    for xx, lab, n, c, t in ((322, "+Vin", 380, COL["P24"], "X3:13\n+24 V"), (338, "-Vin", 381, COL["M24"], "X4:12\n0V24")):
        s.term(xx, 143)
        s.line([(xx, 142.35), (xx, 132)], c=c)
        s.wn(xx, 137, n)
        s.text(xx, 130, t, fs=4.2, va="top")
    s.notes(298, 120, 110, [
        "U8: togliere il ponticello JD-VCC/VCC. Ingressi (VCC) da +5 V",
        "Arduino, bobine (JD-VCC) da U9: le 4 bobine (~70 mA cad.)",
        "non devono caricare il regolatore 5 V dell'Arduino.",
        "Scegliere un modulo con trigger ALTO (SPEC: attivo ALTO);",
        "i moduli comuni a 'trigger basso' invertirebbero la logica.",
        "Colonna luminosa 24 V DC con comune 0V (es. 3 luci + buzzer).",
        "Pulsanti S0-S3 su porta quadro; colonna sul tetto quadro.",
        "Test: comando STATUS, attivare un ingresso alla volta",
        "(vedi README, procedura di verifica).",
    ], title="Note E04 - uscite", fs=4.8, lh=2.95)
    s.legend(298, 84, [("BN", "BN marrone: +24 V sensore"), ("BU", "BU blu: 0V sensore"),
                       ("BK", "BK nero: uscita sensore"), ("P24", "+24 V / segnali 24 V"),
                       ("M24", "0V24"), ("ALM", "uscite opto -> Arduino"), ("SIG", "uscite Arduino -> U8"),
                       ("V5", "+5 V logica")], w=110)
    s.save(pdf)


# --------------------------------------------------------------------------------------
# E05 - LAYOUT QUADRO E CONNETTORI
# --------------------------------------------------------------------------------------
def sheet_e05(pdf):
    s = Sheet(5, "Disposizione quadro e connettori", "Cassetta inox 400x300x200 (scala 1:2), Harting XP1/XP2, collegamento portale")
    s.heading("E05 - Disposizione quadro (indicativa)",
              "Viste in scala 1:2 (quote in mm reali). Ingombri da verificare sui componenti acquistati.")
    k = 0.5
    # ---- vista A: piastra di fondo ----
    X0, Y0 = 20, 118
    s.text(X0, Y0 + 150 + 5.5, "VISTA A - piastra di fondo (porta rimossa) - cassetta 400 x 300 x 200, scala 1:2", fs=6, ha="left", w="bold")
    s.rect(X0, Y0, 400 * k, 300 * k, lw=1.2, fc="#F5F5F5")
    s.rect(X0 + 10 * k, Y0 + 10 * k, 380 * k, 280 * k, lw=0.5, fc="white")

    def R(x, y, w, h, lab, fc="#E3F2FD", fs=4.0, rot=0):
        s.rect(X0 + x * k, Y0 + y * k, w * k, h * k, lw=0.6, fc=fc, z=3)
        s.text(X0 + (x + w / 2) * k, Y0 + (y + h / 2) * k, lab, fs=fs, rot=rot, z=6)

    # canaline
    for yy in (262, 147):
        s.rect(X0 + 20 * k, Y0 + yy * k, 360 * k, 20 * k, lw=0.4, fc="#EEEEEE", ls=(0, (2, 1)), z=2)
    s.text(X0 + 200 * k, Y0 + 272 * k, "canalina 40x20 (forata)", fs=3.8, c="#666", z=4)
    s.text(X0 + 200 * k, Y0 + 157 * k, "canalina 40x20 - separare potenza / segnali", fs=3.8, c="#666", z=4)
    s.rect(X0 + 15 * k, Y0 + 20 * k, 4 * k, 125 * k, lw=0.3, fc="#EEEEEE", z=2)
    # guida DIN 1
    s.line([(X0 + 20 * k, Y0 + 215 * k), (X0 + 380 * k, Y0 + 215 * k)], lw=1.4, c="#9E9E9E")
    x = 22
    row1 = [("X0", 21, "#FFF9C4"), ("Q1", 36, "#FFCDD2"), ("Q2", 36, "#FFCDD2"), ("F1", 17.5, "#FFE0B2"),
            ("F2", 17.5, "#FFE0B2"), ("F3", 17.5, "#FFE0B2"), ("KM1", 45, "#FFCDD2"), ("K1", 22.5, "#C8E6C9"),
            ("K2", 6.2, "#C8E6C9"), ("K3", 6.2, "#C8E6C9"), ("F4", 8.2, "#FFE0B2"), ("F5", 8.2, "#FFE0B2"),
            ("F11-F14", 32.8, "#FFE0B2"), ("X1", 15.6, "#FFF9C4"), ("X2", 26, "#FFF9C4")]
    for lab, w, fc in row1:
        h = 90 if lab not in ("X0", "X1", "X2", "F4", "F5", "F11-F14", "K2", "K3") else 70
        rot = 90 if w < 16 else 0
        R(x, 215 - h / 2, w, h, lab, fc=fc, fs=3.8, rot=rot)
        x += w + 1.5
    # barra PE
    s.rect(X0 + 330 * k, Y0 + 24 * k, 45 * k, 6 * k, lw=0.5, fc=COL["PE"], z=3)
    s.text(X0 + 352 * k, Y0 + 35 * k, "BPE", fs=4.0, c=COL["PE"], w="bold")
    # riga 2
    s.line([(X0 + 20 * k, Y0 + 82 * k), (X0 + 380 * k, Y0 + 82 * k)], lw=1.4, c="#9E9E9E")
    R(24, 20, 85.5, 125, "PSU1\nSDR-480-48\n85,5x125", fc="#FFCDD2", fs=4.2)
    for i, a in enumerate(AXES):
        R(120 + i * 43, 25, 33, 118, f"{a['u']}\nCL57T\n{a['ax']}", fc="#D1C4E9", fs=4.0)
    R(292, 37, 52.5, 90, "PSU2\nHDR-60-24", fc="#BBDEFB", fs=4.0)
    R(350, 37, 17.5, 90, "PSU3 HDR-15-12", fc="#BBDEFB", fs=3.8, rot=90)
    s.text(X0 + 191 * k, Y0 + 15 * k, "driver montati di fianco (dissipatore verticale), distanza >= 10 mm",
           fs=3.8, c="#444")
    # quote

    # ---- vista B: parete laterale sinistra ----
    XB, YB = 236, 118
    s.text(XB, YB + 150 + 5.5, "VISTA B - parete laterale sx (interno)", fs=6, ha="left", w="bold")
    s.rect(XB, YB, 200 * k, 300 * k, lw=1.2, fc="#F5F5F5")
    s.text(XB + 2, YB + 2.5, "lato piastra", fs=3.8, ha="left", c="#666")
    s.text(XB + 98, YB + 2.5, "lato porta", fs=3.8, ha="right", c="#666")

    def RB(x, y, w, h, lab, fc="#E8F5E9", fs=4.0):
        s.rect(XB + x * k, YB + y * k, w * k, h * k, lw=0.6, fc=fc, z=3)
        s.text(XB + (x + w / 2) * k, YB + (y + h / 2) * k, lab, fs=fs, z=6)

    for yy in (250, 175, 100, 32):
        s.line([(XB + 12 * k, YB + yy * k), (XB + 178 * k, YB + yy * k)], lw=1.2, c="#9E9E9E")
    RB(20, 222, 112, 58, "A1 Arduino Mega\n+ Ethernet Shield 2\nsu supporto DIN", fc="#B2DFDB")
    RB(14, 150, 74, 50, "U6\nopto 8 can.", fc="#E1BEE7")
    RB(92, 150, 74, 50, "U7\nopto 8 can.", fc="#E1BEE7")
    RB(14, 75, 82, 50, "U8 rele 4 can.\nsu supporto DIN", fc="#FFE0B2")
    RB(100, 75, 26, 50, "U9\nDC/DC", fc="#BBDEFB")
    RB(130, 75, 42, 50, "X6 X7\n0V/5V\nlogica", fc="#FFF9C4")
    RB(14, 14, 68, 36, "X3  +24 V\n(13 morsetti)", fc="#FFF9C4")
    RB(86, 14, 68, 36, "X4  0V24\n(12 morsetti)", fc="#FFF9C4")
    s.text(XB + 50, YB - 4, "200 (profondità)", fs=4.5)

    # ---- tabella XP1 ----
    TX, TY = 342, 270
    s.text(TX, TY + 3.5, "XP1  Han-Modular 24B (motori/encoder)", fs=5.2, ha="left", w="bold")
    rows = xp1_pins()
    ee = [r for r in rows if r[0][0] in "ab"]
    dd = [r for r in rows if r[0][0] in "cd"]
    lh = 3.05
    s.text(TX, TY, "Han EE 8p (a,b) - fasi", fs=4.3, ha="left", w="bold")
    for i, r in enumerate(ee):
        s.text(TX, TY - 3.3 - i * lh, f"{r[0]:<3} {r[2]:<8} {r[3]}", fs=3.9, ha="left", family="DejaVu Sans Mono")
    y2 = TY - 3.3 - len(ee) * lh - 2
    s.text(TX, y2, "Han DD 12p (c,d) - encoder", fs=4.3, ha="left", w="bold")
    for i, r in enumerate(dd):
        s.text(TX, y2 - 3.3 - i * lh, f"{r[0]:<3} {r[2]:<12} {r[3]}", fs=3.9, ha="left",
               family="DejaVu Sans Mono")
    y3 = y2 - 3.3 - len(dd) * lh
    s.text(TX, y3, "PE  telaio Han -> W9 portale", fs=3.9, ha="left", family="DejaVu Sans Mono")

    # ---- vista C: fondo cassetta ----
    XC, YC = 20, 14
    kc = 0.4
    s.text(XC, YC + 80 + 2.5, "VISTA C - fondo cassetta (dal basso), passaggi cavi - scala 1:2,5", fs=6, ha="left", w="bold")
    s.rect(XC, YC, 400 * kc, 200 * kc, lw=1.2, fc="#F5F5F5")
    s.rect(XC + 40 * kc, YC + 74 * kc, 112 * kc, 52 * kc, lw=0.8, fc="#CFD8DC", z=3)
    s.text(XC + 96 * kc, YC + 105 * kc, "XP1", fs=5.5, w="bold", z=6)
    s.text(XC + 96 * kc, YC + 92 * kc, "Han-Modular 24B\nmotori + encoder", fs=3.8, z=6)
    s.rect(XC + 175 * kc, YC + 78 * kc, 83 * kc, 44 * kc, lw=0.8, fc="#CFD8DC", z=3)
    s.text(XC + 216 * kc, YC + 105 * kc, "XP2", fs=5.5, w="bold", z=6)
    s.text(XC + 216 * kc, YC + 92 * kc, "Han 10 E\nsensori", fs=3.8, z=6)
    glands = [(300, 150, 14, "W0 rete\nM20"), (350, 150, 11, "W20\nLC1-TX M16"), (300, 50, 14, "W23 RJ45\nIP67"),
              (350, 50, 11, "W21\nLC1-RX M16"), (380, 100, 5, "PE\nest.")]
    for gx, gy, r, lab in glands:
        s.ax.add_patch(Circle((XC + gx * kc, YC + gy * kc), r * kc, fc="#CFD8DC", ec="k", lw=0.6, zorder=3))
        s.text(XC + gx * kc, YC + (gy - r) * kc - 1.0, lab, fs=3.6, va="top", z=6)
    s.text(XC + 80, YC + 2.5, "lato porta", fs=3.8, c="#666")
    s.text(XC + 80, YC + 77.5, "lato piastra di fondo", fs=3.8, c="#666")
    s.text(XC + 120 * kc, YC + 32 * kc, "XP1/XP2: custodie a parete con coperchio;\nlato portale spine volanti "
           "cablate\nsui cavi (il portale si stacca)", fs=3.9, ha="center", c="#333")

    # ---- tabella XP2 + avvertenza ----
    TX2, TY2 = 186, 92
    s.text(TX2, TY2, "XP2  Han 10 E (sensori)", fs=5.0, ha="left", w="bold")
    xp2 = [("1", "+24 V (BN)"), ("2", "0V (BU)")] + [(str(x[4]), f"{x[1]} ({x[0]})") for x in SENSORS] + [
        ("PE", "telaio JB1")]
    for i, (pn, lab) in enumerate(xp2):
        s.text(TX2, TY2 - 3.6 - i * 3.0, f"{pn:<3} {lab}", fs=3.9, ha="left", family="DejaVu Sans Mono")
    s.notes(186, 52, 42, ["Cassetta 400x300 quasi", "satura (~95%) e calore", "interno ~40-70 W:",
                          "valutare 500x400x250", "o ventilazione IP54", "con filtro."],
            title="ATTENZIONE", fs=4.2, lh=2.7)
    # ---- porta ----
    XD, YD = 236, 52
    kd = 1 / 7
    s.text(XD, YD + 300 * kd + 3, "VISTA D - porta (1:7)", fs=5.5, ha="left", w="bold")
    s.rect(XD, YD, 400 * kd, 300 * kd, lw=1.0, fc="#F5F5F5")
    dev = [(90, 210, "S0", "#D32F2F", 20), (200, 210, "S1", "#1E88E5", 11), (90, 100, "S2", "#43A047", 11),
           (200, 100, "S3", "#212121", 11)]
    for dx, dy, lab, cc, r in dev:
        s.ax.add_patch(Circle((XD + dx * kd, YD + dy * kd), r * kd * 1.4, fc=cc, ec="k", lw=0.5, zorder=4))
        s.text(XD + (dx + 32) * kd, YD + dy * kd, lab, fs=4.2, ha="left", z=6)
    s.text(XD + 340 * kd, YD + 150 * kd, "colonna\nH1-H4\nsul tetto", fs=3.6, z=6)
    s.text(XD + 30.5, YD - 3, "S0 emergenza (giallo/rosso), S1 reset blu, S2 START verde, S3 STOP nero", fs=3.6,
           ha="center")

    # ---- schema collegamento portale ----
    XP, YP = 302, 52
    s.text(XP, YP + 42, "VISTA E - collegamento al portale (pianta, 1:40)", fs=5.5, ha="left", w="bold")
    kp = 1 / 40
    tx0, ty0 = XP + 12, YP + 18
    s.rect(tx0, ty0, 2000 * kp, 800 * kp, lw=0.8, fc="#FAFAFA")
    s.text(tx0 + 25, ty0 + 10, "tavolo 2000x800", fs=3.8, c="#666")
    for ax_, ay_ in ((-930, -330), (930, -330), (-930, 330), (930, 330)):
        s.rect(tx0 + (1000 + ax_ - 50) * kp, ty0 + (400 + ay_ - 50) * kp, 100 * kp, 100 * kp, lw=0.4, fc="#BDBDBD")
    s.line([(tx0 + 70 * kp, ty0 + 70 * kp), (tx0 + 1930 * kp, ty0 + 70 * kp)], lw=1.4, c="#607D8B")
    s.line([(tx0 + 70 * kp, ty0 + 730 * kp), (tx0 + 1930 * kp, ty0 + 730 * kp)], lw=1.4, c="#607D8B")
    s.rect(tx0 + 300 * kp, ty0 + 10 * kp, 1000 * kp, 40 * kp, lw=0.5, fc="#FFE082")
    s.text(tx0 + 800 * kp, ty0 - 2.3, "catena portacavi su longherone Y-", fs=3.6, c="#6D4C41")
    s.rect(tx0 + 120 * kp, ty0 + 120 * kp, 120 * kp, 90 * kp, lw=0.6, fc="#CFD8DC")
    s.text(tx0 + 185 * kp, ty0 + 260 * kp, "JB1", fs=3.8)
    s.rect(XP - 2, ty0 + 2, 9, 12, lw=0.8, fc="#B0BEC5")
    s.text(XP + 2.5, ty0 + 8, "Q", fs=4.5, w="bold")
    s.line([(XP + 7, ty0 + 6), (tx0 + 120 * kp, ty0 + 6)], lw=0.9, c="#E65100")
    s.line([(XP + 7, ty0 + 10), (tx0 + 120 * kp, ty0 + 10)], lw=0.9, c="#1A237E")
    s.text(XP - 1, YP + 13, "quadro: XP1 (arancio) motori/encoder, XP2 (blu) sensori via JB1;\n"
           "cavi per posa mobile nella catena fino ai carrelli Z1/Z2/R", fs=3.6, ha="left", va="top")
    s.save(pdf)


# --------------------------------------------------------------------------------------
# TABELLE MARKDOWN
# --------------------------------------------------------------------------------------
def md_tables():
    out = []
    out.append("| N. filo | Da | A | Segnale | Sezione [mm²] | Colore | Note |")
    out.append("|---|---|---|---|---|---|---|")
    for r in build_wires():
        out.append("| " + " | ".join(r) + " |")
    out.append("")
    out.append("| Contatto XP1 | Asse | Segnale | Colore anima (motore) | N. filo interno | Cavo |")
    out.append("|---|---|---|---|---|---|")
    for r in xp1_pins():
        out.append(f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |")
    return "\n".join(out)


def main():
    self_check()
    os.makedirs(OUT, exist_ok=True)
    pdf_path = os.path.join(OUT, "schemi_elettrici.pdf")
    with PdfPages(pdf_path) as pdf:
        sheet_e01(pdf)
        sheet_e02(pdf)
        sheet_e03(pdf)
        sheet_e04(pdf)
        sheet_e05(pdf)
        d = pdf.infodict()
        d["Title"] = "ManipMasta - schemi elettrici E01-E05"
        d["Author"] = "ManipMasta"
        d["Subject"] = "Schemi elettrici indicativi - verifica CEI EN 60204-1 a cura di elettricista qualificato"
    with open(os.path.join(OUT, "elenco_fili.csv"), "w", newline="", encoding="utf-8") as f:
        cw = csv.writer(f, delimiter=";")
        cw.writerow(["N. filo", "Da", "A", "Segnale", "Sezione mm2", "Colore", "Note"])
        cw.writerows(build_wires())
    print("Generati:", ", ".join(sorted(os.listdir(OUT))))
    if "--md" in sys.argv:
        print(md_tables())


if __name__ == "__main__":
    main()
