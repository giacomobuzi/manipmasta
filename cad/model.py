#!/usr/bin/env python3
"""ManipMasta - modello 3D parametrico (fonte unica di verità geometrica).

Genera:
  cad/build/model.json   parti + primitive + sequenza di montaggio + visite guidate (viewer three.js)
  cad/manipmasta.scad    modello OpenSCAD equivalente (parametri explode, xpos, gap)

Convenzioni: mm; origine al centro del piano del tavolo; X lungo il tavolo, Y profondità (Y− = lato operatore),
Z verso l'alto. mov="x": segue la traslazione del rullo; mov="xz": segue anche il gap (asse Z).
Posizione di riferimento: X=0, gap = P["gap_ref"].
Ogni parte ha: step (fase di montaggio), explode (esploso globale), dexp (esploso di dettaglio nel montaggio).
Le primitive con "spin" ruotano nel viewer: src "x" (traslazione), "z" (vite Z), "r" (rullo).
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))

DEFAULT = {
    # tavolo (da sostituire con le misure reali)
    "table_L": 2000, "table_W": 800, "table_H": 900, "table_top": 40,
    # ancoraggi
    "anchor_x": 930, "anchor_y": 340, "anchor_size": 100, "anchor_h": 50,
    # portale
    "leg": 60, "beam_h": 80, "beam_w": 40, "beam_top": 470, "cross_h": 60,
    "foot": 120, "foot_t": 10, "pin_d": 20, "pin_len": 35,
    # asse X
    "rail_len": 1800, "x_travel": 700, "car_len": 290, "car_w": 220, "car_t": 12, "pulley_x": 885,
    # asse Z / rullo
    "roller_d": 100, "roller_len": 360, "stub_d": 20, "gap_ref": 40, "gap_max": 150,
    "zplate_w": 290, "zplate_t": 15, "zplate_bottom": 130,
    "slide_w": 300, "slide_t": 16, "slide_h": 250, "slide_below": 40,
    "guide_dx": 115, "screw_dx": -65,
    # quadro elettrico (cassetta inox)
    "box_w": 500, "box_h": 400, "box_d": 250, "box_z0": 100,
}

C = {
    "inox": "#b9c0c8", "inox_dark": "#8a949f", "anchor": "#6d7a87", "table": "#d4d9de",
    "table_leg": "#9aa2ab", "rail": "#3d4550", "chrome": "#d6dbe0", "block": "#2f6db0", "plate": "#c5ccd3",
    "motor": "#24272b", "motor_cap": "#9aa1a8", "encoder": "#3a3f46", "roller": "#eef1f4", "bearing": "#7f8b97",
    "belt": "#151515", "pulley": "#a7adb3", "pom": "#f3f1ea", "box": "#cfd5db", "dough": "#e6c48a",
    "sensor": "#e0b000", "screw": "#8f8f8f", "bronze": "#b08d3a", "estop": "#d42020", "mark": "#e0a100",
    "coupling": "#c0392b", "din": "#eeeeec", "duct": "#c3c8cd", "pcb": "#0f7f86", "pcb2": "#1d5fa8",
    "heatsink": "#2b2f33", "term": "#8a8f99", "term_n": "#3f6fb5", "pe": "#58a23a", "safety": "#f2c200",
    "psu": "#aab3bc", "chain": "#4a4f57", "cable": "#202326", "harting": "#7b858f",
}

RP_X = 15.92      # raggio primitivo puleggia HTD-5M 20T


def load_params():
    p = dict(DEFAULT)
    path = os.path.join(HERE, "params.json")
    if os.path.exists(path):
        with open(path) as f:
            p.update({k: v for k, v in json.load(f).items() if not k.startswith("_")})
    return p


class Model:
    def __init__(self):
        self.parts, self.labels, self._ids = [], [], {}

    def add(self, code, name, group, prims, mov="fixed", explode=(0, 0, 0), info=None, step=0,
            dexp=(0, 0, 0), sub="", **extra):
        n = self._ids.get(code, 0) + 1
        self._ids[code] = n
        d = {"id": f"{code}#{n}", "code": code, "name": name, "group": group, "mov": mov,
             "explode": list(explode), "dexp": list(dexp), "step": step, "sub": sub,
             "prims": prims, "info": info or {}}
        d.update(extra)
        self.parts.append(d)
        return d

    def label(self, lid, text, p, mov="fixed", tours=()):
        self.labels.append({"id": lid, "text": text, "p": list(p), "mov": mov, "tours": list(tours)})


def box(x0, y0, z0, sx, sy, sz, color, **kw):
    d = {"t": "box", "c": [x0 + sx / 2, y0 + sy / 2, z0 + sz / 2], "s": [abs(sx), abs(sy), abs(sz)], "col": color}
    d.update(kw)
    return d


def boxc(cx, cy, cz, sx, sy, sz, color, **kw):
    return box(cx - sx / 2, cy - sy / 2, cz - sz / 2, sx, sy, sz, color, **kw)


def cyl(cx, cy, cz, axis, d, length, color, **kw):
    r = {"t": "cyl", "c": [cx, cy, cz], "ax": axis, "r": d / 2, "l": length, "col": color}
    r.update(kw)
    return r


def ell(cx, cy, cz, rx, ry, rz, color):
    return {"t": "ell", "c": [cx, cy, cz], "r": [rx, ry, rz], "col": color}


def tube(points, d, color):
    return {"t": "tube", "pts": [list(p) for p in points], "r": d / 2, "col": color,
            "c": [sum(p[i] for p in points) / len(points) for i in range(3)]}


def spun(prim, src, k, mark=True):
    """Primitiva rotante: angolo = k * valore sorgente (rad). mark = tacca colorata per vedere la rotazione."""
    prim["spin"] = {"src": src, "k": k}
    prim["mark"] = mark
    return prim


def nema23(c, axis, sign, length=76, enc=22, shaft_src=None, k=0.0):
    """Motore NEMA23 closed-loop. c = centro della faccia flangia; l'albero esce verso sign*axis."""
    i = "xyz".index(axis)

    def at(off):
        p = list(c)
        p[i] += off
        return p

    def bx(off, L, col, side=57):
        s = [side, side, side]
        s[i] = L
        p = at(off)
        return boxc(p[0], p[1], p[2], s[0], s[1], s[2], col)

    prims = [bx(-sign * 4, 8, C["motor_cap"]),                          # flangia
             bx(-sign * (8 + length / 2), length, C["motor"], 56),       # pacco lamellare
             bx(-sign * (8 + length + enc / 2), enc, C["encoder"], 54),  # encoder
             bx(-sign * (8 + length + enc + 3), 6, C["motor_cap"], 50)]
    sp = at(sign * 11)
    sh = cyl(sp[0], sp[1], sp[2], axis, 8, 22, C["chrome"])
    if shaft_src:
        spun(sh, shaft_src, k)
    prims.append(sh)
    con = at(-sign * (8 + length - 10))
    con[(i + 1) % 3] += 33
    prims.append(boxc(con[0], con[1], con[2], 14 if axis != "x" else 16, 14 if axis != "y" else 16, 14 if axis != "z" else 16, "#555b62"))
    return prims


def build(P):
    m = Model()
    L, W, top = P["table_L"], P["table_W"], P["table_top"]
    ax, ay, A, Ah = P["anchor_x"], P["anchor_y"], P["anchor_size"], P["anchor_h"]
    leg, bh, bw, btop = P["leg"], P["beam_h"], P["beam_w"], P["beam_top"]
    g0 = P["gap_ref"]
    rc = g0 + P["roller_d"] / 2                    # quota asse rullo
    car_z0 = btop + 18 + 35                        # sotto piastra carrello
    car_z1 = car_z0 + P["car_t"]
    zy = ay - 90                                   # faccia interna piastra Z (250)
    sh_y = zy - 27                                 # asse alberi/vite Z (SK16: altezza asse 27)
    s_out = zy - 47                                # faccia esterna slitta (203)
    s_in = s_out - P["slide_t"]                    # faccia interna slitta (187)
    gdx, sdx = P["guide_dx"], P["screw_dx"]
    px = P["pulley_x"]
    belt_z = btop - bh / 2
    by_out = ay + bw / 2 + 15                      # piano cinghie X (375)
    kz = -2 * math.pi / 4                          # rad per mm di gap (vite passo 4)
    kr = 1 / (P["roller_d"] / 2) * 1.02            # rad per mm di X (rullo, od 2%)

    # ============ 0. tavolo e impasto (riferimento) ============
    tl = [box(-L / 2, -W / 2, -top, L, W, top, C["table"])]
    for sx in (-1, 1):
        for sy in (-1, 1):
            tl.append(box(sx * (L / 2 - 40) - 25, sy * (W / 2 - 40) - 25, -P["table_H"], 50, 50, P["table_H"] - top, C["table_leg"]))
    tl.append(box(-L / 2 + 40, -W / 2 + 40, -P["table_H"] + 150, L - 80, W - 80, 20, C["table_leg"]))
    m.add("TAV", "Tavolo da pasticceria (esistente)", "Tavolo", tl, explode=(0, 0, -250), step=0,
          info={"Materiale": "esistente", "Dimensioni": f"{L}×{W}×{P['table_H']}"})
    m.add("IMP", "Palla di impasto (indicativa)", "Impasto", [ell(0, 0, 55, 110, 110, 55, C["dough"])], step=0,
          info={"Nota": "1–3 kg al centro del tavolo"})

    # ============ 1. ancoraggi ============
    names = {(-1, -1): ("ANC-01", "A1 riferimento Ø20 H7"), (1, -1): ("ANC-02", "A2 asola 20 H7×26"),
             (-1, 1): ("ANC-03", "A3 appoggio Ø26"), (1, 1): ("ANC-03", "A4 appoggio Ø26")}
    for (sx, sy), (code, nm) in names.items():
        x, y = sx * ax, sy * ay
        prims = [box(x - A / 2, y - A / 2, 0, A, A, Ah, C["anchor"]),
                 cyl(x, y, Ah + 0.5, "z", 26 if code != "ANC-01" else 20, 1, "#333a42")]
        m.add(code, f"Ancoraggio {nm}", "Ancoraggi", prims, explode=(0, 0, 60), step=1, dexp=(0, 0, 160),
              info={"Materiale": "AISI 304 pieno 100×100×50", "Fornitura": "Tornitore/fresatore", "Fissaggio": "4× M8 da sotto il piano"})
        m.add("CTP-01", "Contropiastra sotto piano", "Ancoraggi", [boxc(x, y, -top - 2.5, 140, 140, 5, C["inox_dark"])],
              explode=(0, 0, -120), step=1, dexp=(0, 0, -160), info={"Materiale": "AISI 304 sp. 5"})
        m.add("VIT-M8", "Viti M8×60 A2 (×4)", "Ancoraggi",
              [cyl(x + dx, y + dy, -top - 5 + 25, "z", 8, 60, C["screw"]) for dx in (-35, 35) for dy in (-35, 35)],
              explode=(0, 0, -160), step=1, dexp=(0, 0, -260), info={"Coppia": "20 Nm"})

    # ============ 2. telaio portale ============
    fr = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * ax, sy * ay
            fr.append(boxc(x, y, Ah + P["foot_t"] / 2, P["foot"], P["foot"], P["foot_t"], C["inox_dark"]))
            fr.append(box(x - leg / 2, y - leg / 2, Ah + P["foot_t"], leg, leg, btop - bh - Ah - P["foot_t"], C["inox"]))
    for sy in (-1, 1):
        fr.append(box(-ax - leg / 2, sy * ay - bw / 2, btop - bh, 2 * ax + leg, bw, bh, C["inox"]))
    for sx in (-1, 1):
        fr.append(box(sx * ax - 20, -ay + bw / 2, btop - P["cross_h"], 40, 2 * ay - bw, P["cross_h"], C["inox"]))
    for sy in (-1, 1):
        for sx in (-1, 1):
            fr.append(boxc(sx * 500, sy * (ay + bw / 2 + 17.5), btop - 19, 120, 35, 12, C["inox_dark"]))
    m.add("TEL-01", "Telaio portale saldato", "Portale", fr, explode=(0, 0, 320), step=2, dexp=(0, 0, 420),
          info={"Materiale": "AISI 304 tubo 60×60×3, 80×40×3, 60×40×3", "Fornitura": "Carpenteria inox (TIG)", "Peso": "~32 kg"})
    pins = [cyl(sx * ax, sy * ay, Ah - P["pin_len"] / 2, "z", P["pin_d"], P["pin_len"], C["inox_dark"]) for sx in (-1, 1) for sy in (-1, 1)]
    m.add("PER-01", "Perni di centraggio Ø20 g6 (×4)", "Portale", pins, explode=(0, 0, 200), step=2, dexp=(0, 0, 420),
          info={"Materiale": "AISI 420 temprato", "Fornitura": "Tornitore"})
    for sx in (-1, 1):
        x = sx * ax
        m.add("PBL", "Perno a sfere Ø8 di bloccaggio", "Portale",
              [cyl(x, -ay, Ah - 25, "x", 8, 130, C["chrome"]), cyl(x - 70, -ay, Ah - 25, "y", 30, 4, C["chrome"])],
              explode=(-100 * sx, 0, 60), step=2, dexp=(-180, 0, 0), info={"Tipo": "ball-lock pin Ø8 (GN 113 / KIPP)"})

    # ============ 3. guide X ============
    rl = []
    for sy in (-1, 1):
        rl.append(box(-P["rail_len"] / 2, sy * ay - 20, btop, P["rail_len"], 40, 18, C["rail"]))
        rl.append(cyl(0, sy * ay, btop + 27, "x", 20, P["rail_len"], C["chrome"]))
    m.add("SBR20", "Guide supportate SBR20 L=1800 (×2)", "Asse X", rl, explode=(0, 0, 420), step=3, dexp=(0, 0, 160), sub="x",
          info={"Tipo": "SBR20 (albero Ø20 cromato/inox)", "Fissaggio": "M6 ogni 150 mm sul longherone", "Fornitura": "Acquisto"})

    # ============ 4. carrelli X ============
    blocks = [boxc(dx, sy * ay, btop + 18 + 17.5, 50, 48, 35, C["block"]) for sy in (-1, 1) for dx in (-75, 75)]
    m.add("SBR20UU", "Pattini SBR20UU (×4)", "Asse X", blocks, mov="x", explode=(0, 0, 470), step=4, dexp=(0, 0, 90), sub="x",
          info={"Fissaggio": "4× M6 per pattino", "Fornitura": "Acquisto"})
    cw = P["car_w"]
    for sy in (-1, 1):
        y0 = sy * (s_out - 23 + cw / 2)       # piastra da y=180 a 400
        prims = [boxc(0, y0, car_z0 + P["car_t"] / 2, P["car_len"], cw, P["car_t"], C["plate"]),
                 boxc(60, sy * by_out, (belt_z + 17 + car_z0) / 2, 40, 16, car_z0 - belt_z - 17, C["plate"]),   # attacco cinghia
                 boxc(60, sy * by_out, belt_z + 19, 44, 22, 6, C["inox_dark"])]                                # morsetto
        m.add("CAR-01", f"Piastra carrello X lato {'Y−' if sy < 0 else 'Y+'}", "Asse X", prims, mov="x",
              explode=(0, 0, 560), step=4, dexp=(0, 0, 200), sub="x",
              info={"Materiale": "AISI 304 sp. 12", "Fornitura": "Taglio laser + fresatura", "Fissaggio": "4× M6 per pattino, 10 Nm"})
        m.add("SQZ-01", "Squadra attacco piastra Z", "Asse X",
              [box(-130, sy * (zy + P["zplate_t"]), car_z0 - 6, 260, sy * 48, 6, C["inox_dark"]),
               box(-130, sy * (zy + P["zplate_t"]), car_z0 - 60, 260, sy * 6, 60, C["inox_dark"])],
              mov="x", explode=(0, sy * 60, 520), step=4, dexp=(0, sy * 40, -120), sub="x",
              info={"Materiale": "angolare AISI 304 60×60×6", "Fissaggio": "4× M8 al carrello, 4× M8 alla piastra Z"})
    m.add("PON-01", "Traversa ponte 40×40×2", "Asse X",
          [box(100 - 20, -(s_out - 23 + cw), car_z1, 40, 2 * (s_out - 23 + cw), 40, C["inox"])], mov="x",
          explode=(0, 0, 640), step=4, dexp=(0, 0, 200), sub="x",
          info={"Materiale": "AISI 304 tubo 40×40×2", "Fissaggio": "2× M8 per lato"})

    # ============ 5. trasmissione X ============
    tx_fix = []
    for sy in (-1, 1):
        for xx in (-px, px):
            tx_fix.append(boxc(xx, sy * (ay + bw / 2 + 4), belt_z, 60, 8, 60, C["inox_dark"]))   # supporti KFL / rinvio
    m.add("KFL", "Supporti flangiati KFL002 e perni di rinvio (×4)", "Asse X", tx_fix, explode=(0, 0, 380),
          step=5, dexp=(0, 0, 0), sub="x", info={"Tipo": "KFL002 foro 15", "Fissaggio": "2× M8 sul longherone"})
    shaft = spun(cyl(-px, 0, belt_z, "y", 16, 2 * by_out + 150, C["screw"]), "x", 1 / RP_X)
    m.add("ASS-X", "Albero di sincronismo Ø16", "Asse X", [shaft], explode=(0, 0, 380), step=5, dexp=(0, -500, 0), sub="x",
          info={"Materiale": "AISI 304 Ø16, sedi Ø15 k6", "Fornitura": "Tornitore"})
    pul = []
    for sy in (-1, 1):
        pul.append(spun(cyl(-px, sy * by_out, belt_z, "y", 34, 22, C["pulley"]), "x", 1 / RP_X))
        pul.append(spun(cyl(px, sy * by_out, belt_z, "y", 34, 22, C["pulley"]), "x", 1 / RP_X))
    m.add("PUL-X", "Pulegge HTD-5M 20T motrici e di rinvio (×4)", "Asse X", pul, explode=(0, 0, 380), step=5,
          dexp=(0, 0, 120), sub="x", info={"Tipo": "HTD-5M 20T b15, foro 15 + cava", "Fissaggio": "linguetta + grano M5"})
    belts = []
    for sy in (-1, 1):
        y = sy * by_out
        belts.append(box(-px, y - 7.5, belt_z + 15, 2 * px, 15, 2.5, C["belt"]))
        belts.append(box(-px, y - 7.5, belt_z - 17.5, 2 * px, 15, 2.5, C["belt"]))
    m.add("BELT-X", "Cinghie aperte HTD-5M larghezza 15 (×2)", "Asse X", belts, explode=(0, 0, 380), step=5,
          dexp=(0, 0, 60), sub="x", info={"Tipo": "HTD-5M-15 aperta, fissata al carrello con morsetto", "Tensione": "freccia 5 mm a 10 N a metà campata"})
    mx_y = by_out + 30 + 60
    mx = nema23([-px, mx_y, belt_z], "y", -1, shaft_src="x", k=1 / RP_X)
    mx.append(boxc(-px, mx_y + 4, belt_z, 80, 8, 80, C["plate"]))
    mx.append(boxc(-px, mx_y - 10, belt_z + 40 + 3, 80, 36, 6, C["plate"]))
    m.add("MOT-X", "Motore X NEMA23 closed-loop (M1)", "Motori", mx, explode=(0, 150, 380), step=5, dexp=(0, 220, 0), sub="x",
          info={"Tipo": "NEMA23 2 Nm, encoder 1000 lin., driver CL57T 1600 imp/giro", "Rapporto": "1 giro = 100 mm di corsa (16 step/mm)"})
    cp = spun(cyl(-px, mx_y - 40, belt_z, "y", 32, 34, C["coupling"]), "x", 1 / RP_X)
    m.add("GIU-X", "Giunto elastico 8→14", "Asse X", [cp], explode=(0, 150, 380), step=5, dexp=(0, 140, 0), sub="x",
          info={"Tipo": "soffietto Ø32, fori 8/14"})

    # ============ 6. piastre Z con supporti ============
    zt = P["zplate_t"]
    for sy in (-1, 1):
        side = "Y−" if sy < 0 else "Y+"
        out = sy
        zp = [boxc(0, sy * (zy + zt / 2), (P["zplate_bottom"] + car_z0) / 2, P["zplate_w"], zt, car_z0 - P["zplate_bottom"], C["plate"])]
        m.add("ZPL-01", f"Piastra Z fissa lato {side}", "Asse Z", zp, mov="x", explode=(0, out * 140, 560), step=6,
              dexp=(0, out * 160, 0), sub="z", info={"Materiale": "AISI 304 sp. 15", "Fissaggio": "4× M8 sulla squadra"})
        sup = []
        for dx in (-gdx, gdx):
            for zz in (P["zplate_bottom"] + 12, car_z0 - 30):
                sup.append(boxc(dx, sy * (zy - 18), zz, 42, 36, 14, "#9aa3ad"))
        sup.append(boxc(sdx, sy * (zy - 14), P["zplate_bottom"] + 18, 60, 28, 22, "#7a8590"))   # BF12
        sup.append(boxc(sdx, sy * (zy - 14), car_z0 - 40, 60, 28, 30, "#7a8590"))              # BK12
        m.add("SUP-Z", f"Supporti SK16 (×4) e BK12/BF12 lato {side}", "Asse Z", sup, mov="x", explode=(0, out * 120, 560),
              step=6, dexp=(0, -out * 80, 0), sub="z", info={"Tipo": "SK16 alluminio, BK12 (fisso) + BF12 (libero)", "Fissaggio": "M6 / M5"})

    # ============ 7. gruppo rullo (al banco) ============
    sb = P["slide_below"]
    for sy in (-1, 1):
        side = "Y−" if sy < 0 else "Y+"
        out = sy
        sl = [boxc(0, sy * (s_in + P["slide_t"] / 2), rc - sb + P["slide_h"] / 2, P["slide_w"], P["slide_t"], P["slide_h"], C["plate"]),
              boxc(P["slide_w"] / 2 + 8, sy * (s_in + P["slide_t"] / 2), rc + P["slide_h"] - sb - 7, 16, 10, 14, C["plate"])]  # bandierina
        m.add("ZSL-0" + ("1" if sy < 0 else "2"), f"Slitta Z lato {side}" + (" (porta motore R)" if sy < 0 else ""), "Asse Z", sl,
              mov="xz", explode=(0, out * 200, 360), step=7, dexp=(0, out * 120, 0), sub="z",
              info={"Materiale": "AISI 304 sp. 16, sede cuscinetto Ø47 H7", "Fornitura": "Taglio laser + fresatura"})
        scb = []
        for dx in (-gdx, gdx):
            for dz in (120, 180):
                scb.append(boxc(dx, sy * (s_out + 20), rc + dz, 42, 40, 36, C["block"]))
        m.add("SC16UU", f"Pattini SC16UU (×4) lato {side}", "Asse Z", scb, mov="xz", explode=(0, out * 200, 360), step=7,
              dexp=(0, out * 200, 0), sub="z", info={"Fissaggio": "4× M5 per pattino", "Fornitura": "Acquisto"})
        nut = [boxc(sdx, sy * (s_out + 20), rc + 150, 50, 40, 40, C["inox_dark"]),
               cyl(sdx, sy * sh_y, rc + 150, "z", 30, 46, C["bronze"])]
        m.add("NUT-Z", f"Chiocciola TR16×4 con supporto lato {side}", "Asse Z", nut, mov="xz", explode=(0, out * 200, 360),
              step=7, dexp=(0, out * 200, 60), sub="z", info={"Tipo": "chiocciola flangiata bronzo", "Fissaggio": "4× M5"})
        brg = [cyl(0, sy * (s_in + P["slide_t"] / 2), rc, "y", 47, 14, C["bearing"]),
               cyl(0, sy * (s_out + 2.5), rc, "y", 72, 5, C["inox_dark"])]
        m.add("BRG-6204", f"Cuscinetto inox S6204-2RS + coperchio lato {side}", "Rullo", brg, mov="xz",
              explode=(0, out * 260, 300), step=7, dexp=(0, out * 60, 0), sub="r",
              info={"Tipo": "S6204-2RS inox Ø20×47×14", "Fissaggio": "coperchio Ø72 sp. 5, 4× M5"})

    rl_len = P["roller_len"]
    stub_out = s_out + 30            # estremità perni (233)
    roll = [spun(cyl(0, 0, rc, "y", P["roller_d"], rl_len, C["roller"]), "r", kr),
            spun(cyl(0, -(rl_len / 2 + stub_out) / 2, rc, "y", P["stub_d"], stub_out - rl_len / 2, C["inox"]), "r", kr, mark=False),
            spun(cyl(0, (rl_len / 2 + s_out + 8) / 2, rc, "y", P["stub_d"], s_out + 8 - rl_len / 2, C["inox"]), "r", kr, mark=False)]
    m.add("RUL-01", f"Rullo Ø{P['roller_d']} L={rl_len} con perni Ø20", "Rullo", roll, mov="xz", explode=(0, 0, 240), step=7,
          dexp=(0, 0, -20), sub="r", info={"Materiale": "AISI 304 Ø100×3 rettificato Ra≤0,8", "Fornitura": "Tornitore"})

    # ============ 8. alberi e viti Z ============
    for sy in (-1, 1):
        side = "Y−" if sy < 0 else "Y+"
        out = sy
        gz = [cyl(dx, sy * sh_y, (P["zplate_bottom"] + 3 + car_z0 - 23) / 2, "z", 16, car_z0 - 23 - P["zplate_bottom"] - 3, C["chrome"]) for dx in (-gdx, gdx)]
        m.add("ALB-Z", f"Alberi Ø16 h6 (×2) lato {side}", "Asse Z", gz, mov="x", explode=(0, out * 90, 600), step=8,
              dexp=(0, 0, 300), sub="z", info={"Tipo": "Ø16 h6 inox L=370", "Fissaggio": "vite di serraggio SK16"})
        vs = [spun(cyl(sdx, sy * sh_y, (P["zplate_bottom"] + 8 + car_z1 + 22) / 2, "z", 16, car_z1 + 22 - P["zplate_bottom"] - 8, C["screw"]), "z", kz)]
        m.add("VIT-Z", f"Vite trapezia TR16×4 lato {side}", "Asse Z", vs, mov="x", explode=(0, out * 90, 600), step=8,
              dexp=(0, 0, 340), sub="z", info={"Tipo": "TR16×4 L=420, estremità lavorate Ø12", "Nota": "autobloccante"})

    # ============ 9. motori Z ============
    for sy in (-1, 1):
        side = "Y−" if sy < 0 else "Y+"
        out = sy
        cpz = spun(cyl(sdx, sy * sh_y, car_z1 + 22, "z", 25, 30, C["coupling"]), "z", kz)
        dis = [cyl(sdx + ddx, sy * sh_y + ddy, car_z1 + 20, "z", 12, 40, C["inox"]) for ddx in (-23.6, 23.6) for ddy in (-23.6, 23.6)]
        flange = boxc(sdx, sy * sh_y, car_z1 + 45, 80, 80, 10, C["plate"])
        mot = nema23([sdx, sy * sh_y, car_z1 + 50], "z", -1, shaft_src="z", k=kz)
        m.add("GIU-Z", f"Giunto elastico 8→12 lato {side}", "Asse Z", [cpz], mov="x", explode=(0, out * 90, 700), step=9,
              dexp=(0, 0, 120), sub="z", info={"Tipo": "soffietto Ø25, fori 8/12"})
        m.add("STM-01", f"Flangia motore + distanziali 40 mm lato {side}", "Asse Z", dis + [flange], mov="x",
              explode=(0, out * 90, 730), step=9, dexp=(0, 0, 200), sub="z", info={"Materiale": "AISI 304 sp. 10 + distanziali Ø12"})
        m.add("MOT-Z", f"Motore Z{1 if sy < 0 else 2} NEMA23 closed-loop (M{2 if sy < 0 else 3})", "Motori", mot, mov="x",
              explode=(0, out * 90, 760), step=9, dexp=(0, 0, 230), sub="z",
              info={"Tipo": "NEMA23 2 Nm, encoder 1000 lin., driver CL57T 800 imp/giro", "Rapporto": "1 giro = 4 mm di salita (200 step/mm)"})

    # ============ 10. motore R, cinghia, raschietto ============
    yR = -(s_out + 17)               # piano cinghia R (lato Y−, tra slitta e piastra Z)
    pr = [spun(cyl(0, yR, rc, "y", 66, 22, C["pulley"]), "r", kr)]
    m.add("PUL-R", "Puleggia HTD-5M 40T sul perno rullo", "Rullo", pr, mov="xz", explode=(0, -120, 420), step=10,
          dexp=(0, -140, 0), sub="r", info={"Tipo": "HTD-5M 40T b15, foro 20 + linguetta 6"})
    mr = nema23([0, -s_in, rc + 135], "y", -1, shaft_src="r", k=2 * kr)
    mr.append(spun(cyl(0, yR, rc + 135, "y", 34, 22, C["pulley"]), "r", 2 * kr))
    m.add("MOT-R", "Motore R rotazione rullo NEMA23 closed-loop (M4)", "Motori", mr, mov="xz", explode=(0, 120, 420), step=10,
          dexp=(0, 200, 0), sub="r", info={"Tipo": "NEMA23 + CL57T 800 imp/giro", "Rapporto": "20T→40T = 2:1, asservito a X"})
    bl = [boxc(-25, yR, rc + 67.5, 3, 15, 135, C["belt"]), boxc(25, yR, rc + 67.5, 3, 15, 135, C["belt"])]
    m.add("BELT-R", "Cinghia chiusa HTD 425-5M-15", "Rullo", bl, mov="xz", explode=(0, -120, 420), step=10, dexp=(0, -80, 0), sub="r",
          info={"Tensione": "asole motore ±6 mm"})
    ras = [boxc(-P["roller_d"] / 2 - 6, 0, rc + 30, 10, rl_len - 10, 40, C["pom"]),
           boxc(-P["roller_d"] / 2 - 14, 0, rc + 58, 8, 2 * s_in, 16, C["inox_dark"])]
    m.add("RAS-01", "Raschietto POM-C con barra di supporto", "Rullo", ras, mov="xz", explode=(-120, 0, 300), step=10,
          dexp=(-140, 0, 0), sub="r", info={"Materiale": "POM-C alimentare sp. 10", "Fissaggio": "barra 2× M6 sulle slitte, molla a lamina"})

    # ============ 11. sensori ============
    fc = []
    for sx in (-1, 1):
        fc.append(cyl(sx * (P["x_travel"] + 145), -(ay - 45), btop + 25, "z", 12, 40, C["sensor"]))
        fc.append(boxc(sx * (P["x_travel"] + 145), -(ay - 33), btop + 8, 20, 30, 4, C["inox_dark"]))
    m.add("SEN-X", "Finecorsa X_MIN / X_MAX induttivi M12", "Sensori", fc, explode=(0, -60, 420), step=11, dexp=(0, 0, 80),
          info={"Tipo": "induttivo M12 PNP NO 24 V", "Funzione": "rilevano la piastra carrello da sotto"})
    for sy in (-1, 1):
        zs = []
        for zz in (P["gap_max"] + P["roller_d"] / 2 + P["slide_h"] - sb - 7, 0.5 + P["roller_d"] / 2 + P["slide_h"] - sb - 7):
            zs.append(cyl(P["slide_w"] / 2 + 8, sy * (s_out + 22), zz, "y", 12, 40, C["sensor"]))
        m.add("SEN-Z", f"Sensori Z HOME (alto) e LOW (basso) lato {'Y−' if sy < 0 else 'Y+'}", "Sensori", zs, mov="x",
              explode=(0, sy * 140, 560), step=11, dexp=(60, 0, 0), info={"Tipo": "induttivo M12 PNP NO", "Funzione": "leggono la bandierina della slitta"})
    sens = [cyl(sx * ax + 45, -ay - 45, Ah + P["foot_t"] + 25, "z", 12, 50, C["sensor"]) for sx in (-1, 1)]
    m.add("SEN-SEAT", "Sensori 'portale in sede' M12 (×2)", "Sensori", sens, explode=(0, 0, 330), step=11, dexp=(0, 0, 80),
          info={"Tipo": "induttivo M12 PNP NO 24 V", "Funzione": "leggono gli ancoraggi A1 e A2"})

    # ============ 12. catena portacavi e cavi ============
    ty = -(by_out + 60)              # asse catena
    tray = [box(-760, ty - 25, belt_z + 5, 1520, 50, 3, C["inox_dark"]),
            box(-760, ty - 25, belt_z + 5, 1520, 3, 30, C["inox_dark"]),
            box(-760, ty + 22, belt_z + 5, 1520, 3, 30, C["inox_dark"])]
    for xx in (-600, 0, 600):
        tray.append(boxc(xx, (ty + -(ay + bw / 2)) / 2, belt_z + 6, 30, abs(ty) - ay - bw / 2 + 25, 6, C["inox_dark"]))
    m.add("CAN-01", "Canalina di guida catena (lato Y−)", "Cavi", tray, explode=(0, -150, 300), step=12, dexp=(0, -150, 0),
          info={"Materiale": "lamiera inox piegata sp. 1,5"})
    chain = {"x0": 0, "y": ty, "zl": belt_z + 8 + 12, "zh": car_z0 - 4 - 12, "w": 38, "h": 24,
             "L": P["x_travel"] + 30, "col": C["chain"]}
    cprims = [box(0, ty - 19, chain["zl"] - 12, P["x_travel"] / 2 + 15, 38, 24, C["chain"]),
              box(0, ty - 19, chain["zh"] - 12, P["x_travel"] / 2 + 15, 38, 24, C["chain"])]
    m.add("CHAIN", "Catena portacavi 15×30 R48", "Cavi", cprims, explode=(0, -150, 300), step=12, dexp=(0, 0, 200), chain=chain,
          info={"Tipo": "igus E2 micro serie 15 o equivalente", "Contenuto": "4 cavi motore, 4 encoder, sensori Z"})
    m.add("STF-CAT", "Staffa catena sul carrello", "Cavi", [box(-40, -(s_out - 23 + cw), car_z0 - 6, 80, -(abs(ty) + 25 - (s_out - 23 + cw)), 6, C["inox_dark"])],
          mov="x", explode=(0, -150, 560), step=12, dexp=(0, -100, 0))

    # ============ 13-14. quadro elettrico ============
    bw_, bh_, bd_, bz = P["box_w"], P["box_h"], P["box_d"], P["box_z0"]
    xb = -L / 2 - 5                  # retro cassetta (fuori dal tavolo)
    xf = xb - bd_                    # fronte (porta)
    zt0 = bz + bh_
    shell = [box(xf + 2, -bw_ / 2, bz, bd_ - 2, bw_, 2, C["box"]),           # fondo
             box(xf + 2, -bw_ / 2, zt0 - 2, bd_ - 2, bw_, 2, C["box"]),      # tetto
             box(xb - 2, -bw_ / 2, bz, 2, bw_, bh_, C["box"]),               # retro
             box(xf + 2, -bw_ / 2, bz, bd_ - 2, 2, bh_, C["box"]),           # fianco Y−
             box(xf + 2, bw_ / 2 - 2, bz, bd_ - 2, 2, bh_, C["box"])]        # fianco Y+
    for yy in (-200, 200):
        shell.append(box(xb, yy - 10, btop - 40, -xb - ax - 20, 20, 20, C["inox_dark"]))    # staffe al traverso
    m.add("QE-01", "Cassetta inox IP65 500×400×250 con staffe", "Quadro", shell, explode=(-260, 0, 300), step=13,
          dexp=(-250, 0, 0), sub="q", info={"Materiale": "AISI 304 IP65", "Fissaggio": "2 staffe al traverso X−"})
    door = [box(xf, -bw_ / 2, bz, 2, bw_, bh_, C["box"]),
            cyl(xf - 12, -120, bz + 300, "x", 40, 22, C["estop"]), cyl(xf - 4, -120, bz + 300, "x", 60, 4, C["safety"]),
            cyl(xf - 6, -190, bz + 300, "x", 24, 12, "#1e6fd0"),
            cyl(xf - 6, -120, bz + 210, "x", 24, 12, "#2a9a3a"), cyl(xf - 6, -190, bz + 210, "x", 24, 12, "#202020"),
            boxc(xf - 4, 200, bz + 200, 6, 16, 60, C["motor_cap"])]
    for (yy, zz) in ((-120, 300), (-190, 300), (-120, 210), (-190, 210)):
        door.append(boxc(xf + 30, yy, bz + zz, 50, 30, 40, "#30353b"))       # blocchetti contatto
    m.add("QE-DOOR", "Porta con fungo emergenza S0, reset S1, START S2, STOP S3", "Quadro", door, explode=(-320, 0, 300), step=13,
          dexp=(-300, 0, 0), sub="q", pivot={"p": [xf, bw_ / 2, bz], "axis": "z"},
          info={"S0": "emergenza 2NC", "S1": "reset blu", "S2": "START verde", "S3": "STOP NC"})
    tw = [cyl(xb - 40, 200, zt0 + 15, "z", 40, 30, C["motor_cap"]), cyl(xb - 40, 200, zt0 + 45, "z", 40, 30, "#30a040"),
          cyl(xb - 40, 200, zt0 + 75, "z", 40, 30, "#e0b000"), cyl(xb - 40, 200, zt0 + 105, "z", 40, 30, C["estop"])]
    m.add("H1", "Colonna luminosa 24 V verde/giallo/rosso + buzzer", "Quadro", tw, explode=(-260, 0, 420), step=13, dexp=(0, 0, 150), sub="q")
    hart = [boxc(xf + 80, -60, bz - 35, 90, 43, 70, C["harting"]), boxc(xf + 80, -60, bz - 80, 70, 35, 24, C["harting"]),
            boxc(xf + 80, 70, bz - 30, 70, 40, 60, C["harting"]), boxc(xf + 80, 70, bz - 70, 55, 32, 22, C["harting"]),
            cyl(xf + 180, -150, bz - 12, "z", 30, 24, "#2b2f33"), cyl(xf + 180, 150, bz - 12, "z", 24, 24, "#2b2f33")]
    m.add("XP", "Connettori Harting XP1 (motori/encoder) e XP2 (sensori), pressacavi", "Quadro", hart, explode=(-260, 0, 200),
          step=13, dexp=(0, 0, -150), sub="q", info={"XP1": "Han-Modular 24B", "XP2": "Han 10E"})
    cab = tube([(xf + 80, -60, bz - 92), (xf + 80, -60, bz - 115), (xf + 80, -bw_ / 2 - 25, bz - 115),
                (xf + 80, -bw_ / 2 - 25, belt_z + 15), (xb + 20, -bw_ / 2 - 25, belt_z + 15), (xb + 20, ty, belt_z + 15),
                (-20, ty, belt_z + 15)], 22, C["cable"])
    m.add("CAV-01", "Fascio cavi quadro → catena portacavi", "Cavi", [cab], explode=(0, -150, 300), step=12, dexp=(0, -120, 0))

    # ---- interno quadro: piastra di fondo (u = −y guardando dalla porta, v = altezza) ----
    xp = xb - 5                      # faccia piastra di fondo

    def comp(u0, v0, wu, hv, depth, col):
        return box(xp - depth, -(u0 + wu), bz + v0, depth, wu, hv, col)

    plate = [box(xp, -bw_ / 2 + 8, bz + 8, 3, bw_ - 16, bh_ - 16, "#dfe3e7")]
    ducts = [comp(-222, 362, 444, 25, 40, C["duct"]), comp(-222, 222, 444, 25, 40, C["duct"]), comp(-222, 20, 444, 25, 40, C["duct"]),
             comp(-248, 20, 18, 367, 40, C["duct"]), comp(230, 20, 18, 367, 40, C["duct"])]
    rails = [comp(-215, 302, 430, 10, 8, C["chrome"]), comp(-215, 132, 360, 10, 8, C["chrome"])]
    m.add("QE-PIA", "Piastra di fondo, canaline 40×25, guide DIN", "Quadro interno", plate + ducts + rails, explode=(-260, 0, 300),
          step=14, dexp=(0, 0, 0), sub="q", info={"Nota": "potenza in alto, azionamenti in basso, logica sulla parete destra"})
    row = [("X0", 24, C["term"], 70), ("Q1", 36, C["din"], 75), ("Q2", 36, C["din"], 75), ("F1", 18, C["din"], 70),
           ("F2", 18, C["din"], 70), ("F3", 18, C["din"], 70), ("KM1", 45, "#9aa5b1", 85), ("KM2", 45, "#9aa5b1", 85),
           ("K1", 22.5, C["safety"], 115), ("F4", 18, C["din"], 70), ("F5", 18, C["din"], 70),
           ("F11-F14", 72, C["din"], 70), ("X1", 15, C["term"], 60), ("X2", 15, C["term"], 60)]
    u = -215
    din = []
    pos = {}
    for name, wdt, col, dep in row:
        din.append(comp(u, 262, wdt, 90, dep, col))
        pos[name] = (u + wdt / 2, 262 + 45, dep)
        u += wdt + 2
    m.add("QE-DIN", "Fila potenza: X0, Q1, Q2, F1–F5, KM1+KM2, K1 sicurezza, F11–F14, X1, X2", "Quadro interno", din,
          explode=(-260, 0, 300), step=14, dexp=(-120, 0, 0), sub="q",
          info={"Q1": "magnetotermico 2P C10", "KM1/KM2": "contattori in serie (ridondanza)", "K1": "relè di sicurezza cat. 3", "F11–F14": "fusibili 5 A, uno per driver"})
    psu = [comp(-215, 80, 85.5, 125, 128.5, C["psu"]), comp(65, 100, 52.5, 90, 54.5, C["psu"]), comp(125, 100, 17.5, 90, 54.5, C["psu"])]
    m.add("QE-PSU", "Alimentatori PSU1 48 V 480 W, PSU2 24 V, PSU3 12 V", "Quadro interno", psu, explode=(-260, 0, 300), step=14,
          dexp=(-160, 0, 0), sub="q", info={"PSU1": "SDR-480-48 → driver", "PSU2": "HDR-60-24 → sensori, relè", "PSU3": "HDR-15-12 → Arduino"})
    drv = []
    for i, uu in enumerate((-115, -70, -25, 20)):
        drv.append(comp(uu, 85, 34, 118, 75.5, C["heatsink"]))
        drv.append(comp(uu + 4, 190, 26, 10, 77, "#2a9a3a"))
        drv.append(comp(uu + 4, 90, 26, 10, 77, "#2a9a3a"))
    m.add("QE-DRV", "Driver closed-loop CL57T U11 (X), U12 (Z1), U13 (Z2), U14 (R)", "Quadro interno", drv, explode=(-260, 0, 300),
          step=14, dexp=(-200, 0, 0), sub="q", info={"Ingressi": "PUL/DIR/ENA 5 V dall'Arduino", "Uscite": "fasi A+/A−/B+/B−, ingresso encoder, ALM"})
    bpe = [comp(150, 62, 65, 10, 25, C["pe"])]
    m.add("QE-BPE", "Barra di terra BPE", "Quadro interno", bpe, explode=(-260, 0, 300), step=14, dexp=(-80, 0, 0), sub="q")

    # parete destra (Y−) interna: d = profondità dalla piastra, v = altezza
    yw = -bw_ / 2 + 2

    def wall(d0, v0, dd, hv, t, col):
        return box(xp - d0 - dd, yw, bz + v0, dd, t, hv, col)

    logic = [wall(30, 290, 101.6, 53.3, 32, C["pcb"]), wall(36, 296, 70, 40, 40, "#2f3a44"),
             wall(30, 205, 72, 50, 18, C["pcb2"]), wall(120, 205, 72, 50, 18, C["pcb2"]),
             wall(30, 125, 75, 55, 22, C["pcb2"]), wall(40, 135, 55, 35, 38, "#2a62c9"),
             wall(120, 125, 20, 55, 25, C["psu"]), wall(155, 125, 45, 55, 40, C["term"]),
             wall(30, 55, 80, 40, 45, C["term"]), wall(120, 55, 80, 40, 45, C["term_n"])]
    m.add("QE-LOG", "Logica: Arduino Mega + Ethernet (A1), opto U6/U7, relè U8, DC/DC U9, morsetti X3/X4/X6/X7", "Quadro interno",
          logic, explode=(-260, 0, 300), step=14, dexp=(0, 140, 0), sub="q",
          info={"A1": "Arduino Mega 2560 + Ethernet Shield 2", "U6/U7": "ingressi 24 V optoisolati", "U8": "relè lampade/buzzer", "X3/X4": "+24 V / 0 V"})
    fan = [box(xp - 125 - 60, bw_ / 2 - 2 - 30, bz + 250, 120, 30, 120, "#3a4048"), cyl(xp - 125, bw_ / 2 - 2 - 16, bz + 310, "y", 110, 6, "#59616b"),
           box(xp - 125 - 60, bw_ / 2 - 2 - 12, bz + 30, 120, 12, 120, "#59616b")]
    m.add("QE-FAN", "Ventola filtrata 120 mm e griglia di uscita", "Quadro interno", fan, explode=(-260, 0, 300), step=14,
          dexp=(0, -100, 0), sub="q")

    # ---------------- etichette ----------------
    def L_(lid, text, p, mov="fixed", tours=()):
        m.label(lid, text, p, mov, tours)

    def lq(name, text):
        u0, v0, dep = pos[name]
        L_("q-" + name, text, (xp - dep, -u0, bz + v0), tours=["quadro"])

    lq("Q1", "Q1 interruttore generale")
    lq("KM1", "KM1+KM2 contattori sicurezza")
    lq("K1", "K1 relè di sicurezza")
    lq("F11-F14", "F11–F14 fusibili driver")
    L_("q-psu1", "PSU1 48 V → driver", (xp - 128, 172, bz + 150), tours=["quadro"])
    L_("q-psu2", "PSU2 24 V · PSU3 12 V", (xp - 55, -100, bz + 150), tours=["quadro"])
    L_("q-drv", "U11–U14 driver X · Z1 · Z2 · R", (xp - 76, 30, bz + 145), tours=["quadro"])
    L_("q-ard", "A1 Arduino Mega + Ethernet", (xp - 80, yw + 40, bz + 316), tours=["quadro"])
    L_("q-opto", "U6/U7 ingressi optoisolati", (xp - 110, yw + 18, bz + 230), tours=["quadro"])
    L_("q-rel", "U8 relè lampade", (xp - 70, yw + 38, bz + 152), tours=["quadro"])
    L_("q-xp", "XP1/XP2 connettori al portale", (xf + 80, 0, bz - 60), tours=["quadro"])
    L_("q-fan", "Ventola filtrata", (xp - 125, bw_ / 2 - 20, bz + 310), tours=["quadro"])

    L_("x-mot", "M1 motore X closed-loop", (-px, mx_y + 50, belt_z + 30), tours=["x", "servo"])
    L_("x-giu", "Giunto elastico", (-px, mx_y - 40, belt_z + 18), tours=["x"])
    L_("x-alb", "Albero di sincronismo Ø16", (-px, 0, belt_z + 10), tours=["x"])
    L_("x-pul", "Puleggia 20T: 1 giro = 100 mm", (-px, -by_out, belt_z + 20), tours=["x"])
    L_("x-belt", "Cinghia HTD-5M fissata al carrello", (60, -by_out, belt_z + 18), mov="x", tours=["x"])
    L_("x-pat", "Pattini SBR20UU su guide Ø20", (75, -ay, btop + 40), mov="x", tours=["x"])
    L_("x-rinv", "Puleggia di rinvio", (px, -by_out, belt_z + 20), tours=["x"])
    L_("z-mot", "M2 motore Z1", (sdx, -sh_y, car_z1 + 150), mov="x", tours=["z"])
    L_("z-mot2", "M3 motore Z2", (sdx, sh_y, car_z1 + 150), mov="x", tours=["z"])
    L_("z-vite", "Vite TR16×4: 1 giro = 4 mm", (sdx, -sh_y, 330), mov="x", tours=["z"])
    L_("z-nut", "Chiocciola sulla slitta", (sdx, -(s_out + 40), rc + 150), mov="xz", tours=["z"])
    L_("z-gui", "Guide Ø16 + pattini SC16UU", (-gdx, -sh_y, rc + 180), mov="xz", tours=["z"])
    L_("z-sens", "Sensori HOME / LOW", (P["slide_w"] / 2 + 8, -(s_out + 45), 330), mov="x", tours=["z"])
    L_("z-gap", "Luce rullo–piano = spessore sfoglia", (0, 120, rc - 50), mov="xz", tours=["z"])
    L_("r-mot", "M4 motore R", (0, -s_in + 60, rc + 135), mov="xz", tours=["r"])
    L_("r-belt", "Cinghia 20T → 40T (2:1)", (25, yR, rc + 70), mov="xz", tours=["r"])
    L_("r-rul", "Rullo Ø100: velocità periferica = velocità X", (60, 40, rc + 50), mov="xz", tours=["r"])
    L_("r-ras", "Raschietto POM-C", (-60, 120, rc + 50), mov="xz", tours=["r"])
    L_("r-brg", "Cuscinetto 6204 nella slitta", (0, -s_out, rc - 30), mov="xz", tours=["r"])
    L_("m-1", "M1 · asse X", (-px, mx_y + 60, belt_z + 40), tours=["motori"])
    L_("m-2", "M2 · asse Z1", (sdx, -sh_y, car_z1 + 160), mov="x", tours=["motori"])
    L_("m-3", "M3 · asse Z2", (sdx, sh_y, car_z1 + 160), mov="x", tours=["motori"])
    L_("m-4", "M4 · asse R (rullo)", (0, -s_in + 60, rc + 170), mov="xz", tours=["motori"])
    L_("m-q", "Driver nel quadro", (xp - 76, 30, bz + 145), tours=["motori"])
    L_("s-enc", "Encoder 1000 linee", (-px, mx_y + 95, belt_z + 30), tours=["servo"])
    L_("s-drv", "Driver CL57T nel quadro", (xp - 76, 30, bz + 145), tours=["servo"])
    L_("s-ard", "Arduino: impulsi STEP/DIR", (xp - 80, yw + 40, bz + 316), tours=["servo"])
    return m


# ---------------------------------------------------------------- sequenza di montaggio
STEPS = [
    {"t": "Preparazione", "ops": ["Verificare la distinta: tutte le parti lavorate e acquistate presenti, forature [V] confrontate con i pezzi reali.",
                                  "Pulire e sgrassare il piano; tracciare il centro del tavolo e gli assi X/Y."],
     "vit": [], "chk": "Piano pulito, assi tracciati.", "cam": [-2300, -2700, 1900], "tgt": [0, 0, 150]},
    {"t": "Ancoraggi fissi al tavolo", "ops": [
        "Tracciare i centri degli ancoraggi a (±930, ±340) dal centro; forare il piano Ø9 in 4 punti per ancoraggio (interasse 70×70).",
        "Appoggiare A1 (foro tondo) a X−/Y−, A2 (asola, lato lungo lungo X) a X+/Y−, A3 e A4 (foro Ø26) sul lato Y+.",
        "Da sotto il piano: contropiastra CTP-01 e 4 viti M8×60 per ancoraggio. Serrare a mano: la posizione definitiva si fissa al passo 2."],
     "vit": ["16× M8×60 A2 + rondelle", "4× contropiastra 140×140×5"], "cpl": "M8: 20 Nm (dopo il passo 2)",
     "chk": "Diagonali tra i centri uguali entro 1 mm.", "cam": [-1500, -1500, 900], "tgt": [-500, 0, 0]},
    {"t": "Telaio portale sugli ancoraggi", "ops": [
        "Infilare i 4 perni di centraggio nelle piastre piede (battuta Ø30) se non già saldati.",
        "Sollevare il telaio in due con le maniglie e calarlo verticalmente: prima A1, poi A2, poi A3/A4.",
        "Serrare ora le viti M8 degli ancoraggi. Inserire i perni a sfere Ø8 su A1 e A2."],
     "vit": ["2× perno a sfere Ø8"], "cpl": "M8 ancoraggi: 20 Nm",
     "chk": "Il telaio scende e si sfila senza forzare; nessun gioco percepibile su A1.", "cam": [-2300, -2700, 1700], "tgt": [0, 0, 200]},
    {"t": "Guide X SBR20", "ops": [
        "Posare la guida Y− sul longherone; allinearla con riga e comparatore (rettilineità 0,1 su 1800). Serrare le M6 dal centro verso le estremità.",
        "Posare la guida Y+ parallela alla prima: comparatore su un pattino di prova che scorre sulla guida Y−.",
        "Ingrassare gli alberi con grasso alimentare NSF H1."],
     "vit": ["2×12 viti M6×20 A2"], "cpl": "M6: 8 Nm", "chk": "Parallelismo guide 0,1 su tutta la corsa.",
     "cam": [-1900, -1900, 1300], "tgt": [0, 0, 450]},
    {"t": "Carrelli X e traversa ponte", "ops": [
        "Infilare 2 pattini SBR20UU per guida.",
        "Avvitare le piastre carrello CAR-01 sui pattini (4× M6 per pattino), lato largo verso l'esterno.",
        "Avvitare sotto ogni piastra la squadra SQZ-01 (4× M8) e sopra la traversa ponte PON-01 (2× M8 per lato).",
        "Far scorrere a mano il ponte su tutta la corsa: nessun punto duro. Se tira, allentare le M6 di un lato, far scorrere e risserrare."],
     "vit": ["16× M6×16", "8× M8×20", "4× M8×60"], "cpl": "M6: 8 Nm · M8: 20 Nm", "chk": "Ponte che scorre libero, squadro diagonali ±0,5.",
     "cam": [-700, -1300, 1100], "tgt": [0, 0, 480]},
    {"t": "Trasmissione X: albero, pulegge, cinghie, motore X", "ops": [
        "Montare i supporti KFL002 sui longheroni (lato X−) e i perni di rinvio (lato X+).",
        "Infilare l'albero di sincronismo da Y+ con le due pulegge 20T; linguette e grani M5 con frenafiletti medio.",
        "Montare le pulegge di rinvio; passare le cinghie aperte e bloccarne le estremità nei morsetti dei carrelli.",
        "Tensionare le due cinghie con la stessa freccia (≈5 mm con 10 N a metà campata): il ponte deve restare in squadro.",
        "Montare la flangia motore, il giunto 8→14 e il motore X (M1) sul lato Y+. Allineare albero e motore entro 0,1."],
     "vit": ["8× M8 supporti", "4× M5 motore", "2× grano M5 pulegge"], "cpl": "M5: 5 Nm · M8: 20 Nm",
     "chk": "Ruotando il motore a mano, i due carrelli si muovono insieme senza ritardo.", "cam": [-1500, 900, 900], "tgt": [-800, 0, 420]},
    {"t": "Piastre Z con supporti (al banco, poi in macchina)", "ops": [
        "Al banco: avvitare su ogni piastra Z i 4 supporti SK16, il BF12 in basso e il BK12 in alto.",
        "Avvitare la piastra Z alla squadra SQZ-01 (4× M8). Ripetere per il lato Y+.",
        "Controllare con squadra: piastra Z verticale e perpendicolare al piano entro 0,1/300."],
     "vit": ["16× M6 SK16", "8× M5 BK/BF", "8× M8 squadre"], "cpl": "M5: 5 Nm · M6: 8 Nm · M8: 20 Nm",
     "chk": "Fori SK16 coassiali: un albero Ø16 deve infilarsi nei due supporti senza forzare.", "cam": [-700, -1100, 700], "tgt": [0, -200, 330]},
    {"t": "Gruppo rullo (al banco)", "ops": [
        "Montare i cuscinetti S6204 nelle sedi delle slitte (pressa o tampone, mai colpire l'anello interno).",
        "Infilare il rullo nei cuscinetti, chiudere con i coperchi Ø72 (4× M5).",
        "Avvitare sulle slitte i 4 pattini SC16UU per lato e i supporti delle chiocciole TR16.",
        "La slitta Y− (ZSL-01) è quella con i fori per il motore R."],
     "vit": ["8× M5 coperchi", "16× M5 pattini", "8× M5 chiocciole"], "cpl": "M5: 5 Nm", "chk": "Il rullo gira a mano libero, senza gioco assiale.",
     "cam": [-600, -1000, 500], "tgt": [0, 0, 200]},
    {"t": "Inserimento gruppo rullo, alberi e viti Z", "ops": [
        "Portare il gruppo rullo tra le piastre Z, con i pattini allineati ai supporti SK16.",
        "Infilare gli alberi Ø16 dall'alto attraverso i fori della piastra carrello, i supporti SK16 e i pattini; serrare le viti degli SK16.",
        "Infilare le viti TR16 dall'alto, avvitarle nelle chiocciole, bloccarle nel BK12 (ghiera) e nel BF12 (seeger)."],
     "vit": ["8× vite serraggio SK16", "2× ghiera BK12"], "cpl": "Ghiera BK12: a mano + controdado",
     "chk": "Girando a mano una vite, la slitta sale e scende senza punti duri su tutta la corsa.", "cam": [-700, -1100, 900], "tgt": [0, 0, 330]},
    {"t": "Motori Z1 e Z2", "ops": [
        "Avvitare i 4 distanziali da 40 mm e la flangia motore sopra ogni carrello.",
        "Montare il giunto 8→12 sulla vite, poi il motore dall'alto: albero nel giunto, 4× M5 sulla flangia.",
        "Serrare il giunto lato motore per ultimo, con la slitta a metà corsa."],
     "vit": ["8× distanziali Ø12×40", "8× M5 flangia", "4× M5 motori"], "cpl": "M5: 5 Nm · viti giunto: 2 Nm",
     "chk": "Le due slitte alla stessa quota (±0,5) prima di serrare i giunti.", "cam": [-500, -900, 1100], "tgt": [0, 0, 500]},
    {"t": "Motore R, cinghia e raschietto", "ops": [
        "Puleggia 40T sul perno rullo lato Y− (linguetta 6 + grano).",
        "Motore R sulla slitta Y− dall'interno, puleggia 20T sull'albero; cinghia HTD 425-5M; tensionare con le asole (±6 mm).",
        "Barra del raschietto sulle due slitte (2× M6), lama POM-C in leggero appoggio sul rullo."],
     "vit": ["4× M5 motore R", "2× M6 barra raschietto"], "cpl": "M5: 5 Nm · M6: 8 Nm",
     "chk": "Cinghia R: freccia 3 mm con 5 N. Rullo trascinato senza slittamenti.", "cam": [-500, -700, 450], "tgt": [0, -150, 200]},
    {"t": "Sensori", "ops": [
        "Finecorsa X_MIN e X_MAX sulle staffe interne del longherone Y−: distanza di lettura 2 mm dalla piastra carrello.",
        "Sensori Z HOME (alto) e Z LOW (basso) sulle piastre Z: leggono la bandierina della slitta a 2 mm.",
        "Sensori 'portale in sede' nei piedi A1 e A2 (M12×1): 2 mm sopra l'ancoraggio."],
     "vit": ["8× sensori M12 con 2 dadi"], "cpl": "Dadi M12: 10 Nm", "chk": "LED del sensore acceso con il pezzo davanti, spento senza.",
     "cam": [-1400, -1400, 800], "tgt": [-400, -300, 300]},
    {"t": "Catena portacavi e cavi", "ops": [
        "Avvitare la canalina inox sul fianco Y− del portale e l'estremità fissa della catena al centro (X=0).",
        "Collegare l'estremità mobile alla staffa del carrello Y−.",
        "Posare nella catena i cavi motore, encoder e sensori Z (solo cavi per posa mobile), con raggio ≥ 48 mm; il fascio arriva al quadro lungo il montante X−."],
     "vit": ["6× M6 canalina", "4× M4 attacchi catena"], "cpl": "M6: 8 Nm",
     "chk": "Corsa completa a mano: la catena non tocca la cinghia né il carrello.", "cam": [-1300, -1700, 900], "tgt": [-300, -400, 400]},
    {"t": "Quadro elettrico sul portale", "ops": [
        "Avvitare le due staffe della cassetta al traverso X− (il quadro sporge oltre il bordo del tavolo).",
        "Montare la colonna luminosa sul tetto e i connettori XP1/XP2 sul fondo.",
        "Collegare i connettori volanti del portale a XP1 (motori/encoder) e XP2 (sensori)."],
     "vit": ["4× M8 staffe quadro"], "cpl": "M8: 20 Nm", "chk": "Il portale si stacca dal tavolo scollegando solo XP1, XP2 e il cavo di rete.",
     "cam": [-2100, -900, 700], "tgt": [-1100, 0, 300]},
    {"t": "Interno del quadro (a cura del quadrista)", "ops": [
        "Piastra di fondo: canaline 40×25, guide DIN. Fila alta: X0, Q1, Q2, F1–F3, KM1, KM2, K1, F4–F5, F11–F14, X1, X2.",
        "Fila bassa: PSU1 48 V, i 4 driver CL57T montati di fianco (dissipatore verticale, ≥10 mm tra loro), PSU2 24 V, PSU3 12 V, barra BPE.",
        "Parete destra: Arduino Mega + Ethernet, schede opto U6/U7, relè U8, DC/DC U9, morsetti X3/X4/X6/X7. Parete sinistra: ventola filtrata.",
        "Cablare secondo wiring/out/schemi_elettrici.pdf e verificare secondo wiring/README.md."],
     "vit": [], "cpl": "Morsetti: coppia indicata dal costruttore", "chk": "Prove CEI EN 60204-1: continuità PE, isolamento, funzionamento emergenza.",
     "cam": [-1900, -650, 650], "tgt": [-1130, 0, 300], "door": 1},
    {"t": "Collaudo", "ops": [
        "Prima accensione senza motori collegati: verificare le tensioni 48/24/12 V e gli ingressi (comando STATUS).",
        "Collegare i motori; JOG piccoli su ogni asse per il verso; HOME; calibrazione della luce con spessimetro (docs/montaggio_collaudo.md).",
        "Prova di emergenza, barriera, STOP e sfilamento portale. Primo ciclo con impasto a velocità ridotta."],
     "vit": [], "cpl": "", "chk": "Tutte le prove di docs/montaggio_collaudo.md superate.", "cam": [-2300, -2700, 1900], "tgt": [0, 0, 150]},
]

TOURS = [
    {"id": "motori", "t": "Dove sono i quattro motori", "anim": "cycle", "focus": ["MOT-X", "MOT-Z", "MOT-R", "GIU-X", "GIU-Z", "QE-01", "QE-DRV"],
     "cam": [-2000, -2300, 1700], "tgt": [-300, 0, 350],
     "p": ["M1 (asse X) è fisso sul portale, lato Y+ in fondo a X−: muove il ponte con cinghie e albero di sincronismo.",
           "M2 e M3 (assi Z1 e Z2) stanno sopra i due carrelli e viaggiano con il ponte: ognuno gira la vite che alza o abbassa il proprio lato del rullo.",
           "M4 (asse R) è montato sulla slitta Z lato operatore e sale e scende con il rullo, che fa ruotare con una cinghia.",
           "I quattro driver sono nel quadro inox; i cavi arrivano ai motori mobili attraverso la catena portacavi."]},
    {"id": "servo", "t": "Il motore closed-loop", "anim": "x", "focus": ["MOT-X", "GIU-X", "QE-DRV", "QE-LOG"],
     "cam": [-1700, 1300, 900], "tgt": [-1000, 150, 380], "ex": {"MOT-X": 0},
     "p": ["Tutti e quattro gli assi usano un motore passo-passo NEMA23 con encoder sul retro e un driver CL57T: è un 'servo ibrido'. "
           "L'Arduino manda al driver un impulso per ogni passo (STEP) e il verso (DIR); il driver alimenta le due fasi del motore.",
           "L'encoder (1000 linee, 4000 conteggi/giro) dice al driver dove si trova davvero l'albero. Se un carico frena il motore, il driver "
           "aumenta la corrente e recupera i passi persi; se l'errore supera la soglia apre il contatto ALM e l'Arduino va in ALLARME.",
           "Rispetto a un servo AC costa meno, tiene la posizione da fermo e si comanda con gli stessi segnali di un passo-passo."]},
    {"id": "x", "t": "Asse X: traslazione del rullo", "anim": "x", "focus": ["MOT-X", "GIU-X", "ASS-X", "PUL-X", "BELT-X", "KFL", "SBR20", "SBR20UU", "CAR-01", "PON-01"],
     "cam": [-1900, -1500, 1200], "tgt": [-300, 0, 430],
     "p": ["Il motore M1 sta sul lato Y+ in fondo al portale (X−). Tramite un giunto elastico fa girare l'albero di sincronismo, "
           "che porta una puleggia 20T per lato: i due lati del ponte si muovono insieme e il rullo resta sempre in squadro.",
           "Le cinghie HTD-5M sono aperte e fissate ai carrelli: un giro di motore = 100 mm di corsa (16 step/mm). "
           "I carrelli scorrono su 4 pattini SBR20UU sulle guide Ø20."]},
    {"id": "z", "t": "Assi Z1 e Z2: altezza del rullo", "anim": "z", "focus": ["MOT-Z", "GIU-Z", "STM-01", "VIT-Z", "NUT-Z", "ALB-Z", "SUP-Z", "ZSL-01", "ZSL-02", "SC16UU", "SEN-Z", "RUL-01"],
     "cam": [-900, -1300, 800], "tgt": [0, -100, 300],
     "p": ["Sopra ogni carrello c'è un motore Z (M2 lato operatore, M3 lato opposto) che gira una vite trapezia TR16×4: "
           "1 giro = 4 mm di salita. La chiocciola è sulla slitta, che scorre su due guide Ø16.",
           "La vite è autobloccante: a motori spenti il rullo non scende. All'avvio ogni slitta sale fino al proprio sensore HOME: "
           "così i due lati si allineano da soli e il rullo resta parallelo al piano.",
           "La quota Z è la luce tra rullo e piano, cioè lo spessore della sfoglia."]},
    {"id": "r", "t": "Asse R: rotazione del rullo", "anim": "r", "focus": ["MOT-R", "BELT-R", "PUL-R", "RUL-01", "BRG-6204", "RAS-01"],
     "cam": [-800, -1050, 650], "tgt": [0, -150, 200],
     "p": ["Il motore M4 è montato sulla slitta Y− e sale e scende con il rullo. Con una cinghia 20T→40T (2:1) fa ruotare il rullo, "
           "sostenuto da due cuscinetti inox 6204 nelle slitte.",
           "Il firmware lo comanda 'agganciato' all'asse X: per ogni millimetro di traslazione il rullo ruota di un millimetro di superficie "
           "(più un piccolo overdrive regolabile). Così il rullo rotola sull'impasto invece di trascinarlo. Il raschietto in POM tiene pulita la superficie."]},
    {"id": "quadro", "t": "Dentro il quadro inox", "anim": "door", "focus": ["QE-01", "QE-DOOR", "QE-PIA", "QE-DIN", "QE-PSU", "QE-DRV", "QE-BPE", "QE-LOG", "QE-FAN", "XP", "H1"],
     "cam": [-1900, -650, 650], "tgt": [-1130, 0, 300],
     "p": ["Cassetta inox IP65 500×400×250 appesa al traverso X−, fuori dal tavolo. In alto la potenza su guida DIN: interruttore Q1, "
           "fusibili, i due contattori KM1+KM2 comandati dal relè di sicurezza K1 (tolgono i 48 V ai driver in emergenza).",
           "In basso l'alimentatore 48 V e i 4 driver CL57T (X, Z1, Z2, R), poi i 24 V per sensori e relè e i 12 V per l'Arduino.",
           "Sulla parete destra la logica: Arduino Mega con Ethernet, schede di ingresso optoisolate, relè delle lampade. "
           "Sul fondo i connettori Harting XP1 e XP2: scollegandoli il portale si toglie dal tavolo."]},
    {"id": "ciclo", "t": "Il ciclo di sfogliatura", "anim": "cycle", "focus": [],
     "cam": [-2300, -2700, 1900], "tgt": [0, 0, 150],
     "p": ["Rullo alzato, si porta fuori dall'impasto, scende alla luce iniziale (es. 40 mm), passa avanti e indietro. "
           "A ogni fine corsa, fuori dall'impasto, scende di qualche millimetro, fino allo spessore finale; poi passate di finitura, "
           "si alza e torna al centro."]},
]


# ---------------------------------------------------------------- OpenSCAD
def to_scad(m, P):
    out = ["// ManipMasta - generato da cad/model.py: non modificare a mano, rigenera.",
           "explode = 0;   // 0..1", "xpos = 0;      // posizione X rullo (mm)",
           f"gap = {P['gap_ref']};   // luce rullo-piano (mm)", "$fn = 40;", "", f"dz = gap - {P['gap_ref']};", ""]

    def col(h):
        h = h.lstrip("#")
        return "[%.3f,%.3f,%.3f]" % tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    for p in m.parts:
        e = [a + b for a, b in zip(p["explode"], p["dexp"])]
        mv = {"fixed": "[0,0,0]", "x": "[xpos,0,0]", "xz": "[xpos,0,dz]"}[p["mov"]]
        out.append(f"// {p['id']} - {p['name']}")
        out.append(f"translate({mv}) translate(explode*[{e[0]},{e[1]},{e[2]}]) {{")
        for q in p["prims"]:
            if q["t"] == "box":
                c, s = q["c"], q["s"]
                out.append(f"  color({col(q['col'])}) translate([{c[0]-s[0]/2:.2f},{c[1]-s[1]/2:.2f},{c[2]-s[2]/2:.2f}]) cube([{s[0]:.2f},{s[1]:.2f},{s[2]:.2f}]);")
            elif q["t"] == "cyl":
                c = q["c"]
                rot = {"x": "[0,90,0]", "y": "[-90,0,0]", "z": "[0,0,0]"}[q["ax"]]
                out.append(f"  color({col(q['col'])}) translate([{c[0]:.2f},{c[1]:.2f},{c[2]:.2f}]) rotate({rot}) cylinder(r={q['r']:.2f}, h={q['l']:.2f}, center=true);")
            elif q["t"] == "ell":
                c, r = q["c"], q["r"]
                out.append(f"  color({col(q['col'])}) translate([{c[0]},{c[1]},{c[2]}]) scale([{r[0]},{r[1]},{r[2]}]) sphere(r=1);")
            elif q["t"] == "tube":
                pts = q["pts"]
                for a, b in zip(pts, pts[1:]):
                    out.append(f"  color({col(q['col'])}) hull() {{ translate({a}) sphere(r={q['r']}); translate({b}) sphere(r={q['r']}); }}")
        out.append("}")
    return "\n".join(out) + "\n"


def main():
    P = load_params()
    m = build(P)
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    data = {"params": P, "parts": m.parts, "labels": m.labels, "steps": STEPS, "tours": TOURS}
    with open(os.path.join(HERE, "build", "model.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    with open(os.path.join(HERE, "manipmasta.scad"), "w") as f:
        f.write(to_scad(m, P))
    print(f"{len(m.parts)} parti, {sum(len(p['prims']) for p in m.parts)} primitive, {len(STEPS)} fasi, {len(TOURS)} visite")


if __name__ == "__main__":
    main()
