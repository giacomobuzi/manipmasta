#!/usr/bin/env python3
"""ManipMasta - modello 3D parametrico (fonte unica di verità geometrica).

Genera:
  cad/build/model.json      primitive per il viewer three.js (assieme + esploso + cinematica)
  cad/manipmasta.scad       modello OpenSCAD equivalente (parametro `explode`, `gap`, `xpos`)

Convenzioni: mm; origine al centro del piano del tavolo; X lungo il tavolo, Y profondità, Z in alto.
Le parti con mov="x" seguono la posizione X del rullo; mov="xz" seguono anche il gap (asse Z).
Posizione di riferimento del modello: X=0, gap = P["gap_ref"].

Uso:  python3 cad/model.py            (legge cad/params.json)
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
    "rail_len": 1800, "x_travel": 700, "car_len": 250, "car_w": 150, "car_t": 12,
    "pulley_x": 870,
    # asse Z / rullo
    "roller_d": 100, "roller_len": 370, "stub_d": 20, "gap_ref": 40, "gap_max": 150,
    "zplate_w": 300, "zplate_t": 15, "zplate_bottom": 140,
    "slide_w": 220, "slide_t": 12, "slide_h": 230,
    # quadro
    "box_w": 500, "box_h": 400, "box_d": 250,
}

C = {
    "inox": "#b9c0c8", "inox_dark": "#8a949f", "anchor": "#6d7a87", "table": "#d4d9de",
    "table_leg": "#9aa2ab", "rail": "#3d4550", "block": "#2f6db0", "plate": "#c5ccd3",
    "motor": "#24272b", "motor_cap": "#9aa1a8", "roller": "#eef1f4", "bearing": "#7f8b97",
    "belt": "#151515", "pulley": "#a7adb3", "pom": "#f3f1ea", "box": "#d5dade",
    "dough": "#e6c48a", "sensor": "#e0b000", "screw": "#8f8f8f", "estop": "#d42020",
}


def load_params():
    p = dict(DEFAULT)
    path = os.path.join(HERE, "params.json")
    if os.path.exists(path):
        with open(path) as f:
            p.update({k: v for k, v in json.load(f).items() if not k.startswith("_")})
    return p


class Model:
    def __init__(self):
        self.parts = []

    def add(self, code, name, group, prims, mov="fixed", explode=(0, 0, 0), info=None):
        self.parts.append({
            "code": code, "name": name, "group": group, "mov": mov,
            "explode": list(explode), "prims": prims, "info": info or {},
        })


def box(x0, y0, z0, sx, sy, sz, color, **kw):
    """Parallelepipedo dato l'angolo minimo e le dimensioni."""
    d = {"t": "box", "c": [x0 + sx / 2, y0 + sy / 2, z0 + sz / 2], "s": [sx, sy, sz], "col": color}
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


def build(P):
    m = Model()
    L, W, top = P["table_L"], P["table_W"], P["table_top"]
    ax, ay, A, Ah = P["anchor_x"], P["anchor_y"], P["anchor_size"], P["anchor_h"]
    leg, bh, bw, btop = P["leg"], P["beam_h"], P["beam_w"], P["beam_top"]
    g0 = P["gap_ref"]
    rc = g0 + P["roller_d"] / 2            # quota asse rullo
    car_z0 = btop + 18 + 35                 # sotto piastra carrello (rail base 18 + pattino 35)
    car_z1 = car_z0 + P["car_t"]

    # ---------------- tavolo (riferimento, non fornito) ----------------
    tl = []
    tl.append(box(-L / 2, -W / 2, -top, L, W, top, C["table"]))
    for sx in (-1, 1):
        for sy in (-1, 1):
            tl.append(box(sx * (L / 2 - 40) - 25, sy * (W / 2 - 40) - 25, -P["table_H"], 50, 50, P["table_H"] - top, C["table_leg"]))
    tl.append(box(-L / 2 + 40, -W / 2 + 40, -P["table_H"] + 150, L - 80, W - 80, 20, C["table_leg"]))
    m.add("TAV", "Tavolo da pasticceria (esistente)", "Tavolo", tl, explode=(0, 0, -250),
          info={"Materiale": "esistente", "Dimensioni": f"{L}×{W}×{P['table_H']}"})

    # impasto
    m.add("IMP", "Palla di impasto (indicativa)", "Impasto",
          [ell(0, 0, 55, 110, 110, 55, C["dough"])], explode=(0, 0, 0),
          info={"Nota": "1–3 kg al centro del tavolo"})

    # ---------------- ancoraggi fissi ----------------
    names = {(-1, -1): ("ANC-01", "A1 riferimento Ø20 H7"), (1, -1): ("ANC-02", "A2 asola 20 H7×26"),
             (-1, 1): ("ANC-03", "A3 appoggio Ø26"), (1, 1): ("ANC-03", "A4 appoggio Ø26")}
    for (sx, sy), (code, nm) in names.items():
        prims = [box(sx * ax - A / 2, sy * ay - A / 2, 0, A, A, Ah, C["anchor"])]
        prims.append(cyl(sx * ax, sy * ay, Ah + 0.5, "z", 26 if code != "ANC-01" else 20, 1, "#333a42"))
        m.add(code, f"Ancoraggio {nm}", "Ancoraggi", prims, explode=(0, 0, 60),
              info={"Materiale": "AISI 304 pieno", "Fornitura": "Tornitore/fresatore", "Dim.": f"{A}×{A}×{Ah}"})

    # ---------------- portale (telaio saldato) ----------------
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
    # maniglie
    for sy in (-1, 1):
        for sx in (-1, 1):
            fr.append(boxc(sx * 500, sy * (ay + bw / 2 + 17.5), btop - 19, 120, 35, 12, C["inox_dark"]))
    m.add("TEL-01", "Telaio portale saldato", "Portale", fr, explode=(0, 0, 320),
          info={"Materiale": "AISI 304 tubo 60×60×3, 80×40×3, 60×40×3", "Fornitura": "Carpenteria inox (TIG)"})

    pins = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            pins.append(cyl(sx * ax, sy * ay, Ah - P["pin_len"] / 2, "z", P["pin_d"], P["pin_len"], C["inox_dark"]))
    m.add("PER-01", "Perni di centraggio Ø20 g6 (×4)", "Portale", pins, explode=(0, 0, 200),
          info={"Materiale": "AISI 304 / 420 temprato", "Fornitura": "Tornitore"})

    sens = []
    for sx in (-1, 1):
        sens.append(cyl(sx * ax + 45, -ay - 45, Ah + P["foot_t"] + 25, "z", 12, 50, C["sensor"]))
    m.add("SEN-SEAT", "Sensori induttivi M12 'portale in sede' (×2)", "Sensori", sens, explode=(0, 0, 330),
          info={"Tipo": "induttivo M12 PNP NO 24 V, Sn 4 mm", "Fornitura": "Acquisto"})

    # ---------------- guide X ----------------
    rl = []
    for sy in (-1, 1):
        rl.append(box(-P["rail_len"] / 2, sy * ay - 20, btop, P["rail_len"], 40, 18, C["rail"]))
        rl.append(cyl(0, sy * ay, btop + 27, "x", 20, P["rail_len"], "#c9ced4"))
    m.add("SBR20", "Guide supportate SBR20 L=1800 (×2)", "Asse X", rl, explode=(0, 0, 420),
          info={"Tipo": "SBR20 (albero Ø20 cromato/inox)", "Fornitura": "Acquisto"})

    # ---------------- carrelli X ----------------
    blocks = []
    for sy in (-1, 1):
        for dx in (-75, 75):
            blocks.append(boxc(dx, sy * ay, btop + 18 + 17.5, 50, 48, 35, C["block"]))
    m.add("SBR20UU", "Pattini SBR20UU (×4)", "Asse X", blocks, mov="x", explode=(0, 0, 470),
          info={"Fornitura": "Acquisto"})

    cl = P["car_len"]
    for sy, code in ((-1, "CAR-01"), (1, "CAR-01")):
        y0 = sy * (ay - 75)
        prims = [boxc(0, y0, car_z0 + P["car_t"] / 2, cl, P["car_w"], P["car_t"], C["plate"])]
        # attacco cinghia
        prims.append(boxc(-60, sy * (ay + 45), car_z0 - 30, 40, 10, 60, C["plate"]))
        m.add(code, f"Piastra carrello X lato {'Y−' if sy < 0 else 'Y+'}", "Asse X", prims, mov="x",
              explode=(0, 0, 560), info={"Materiale": "AISI 304 sp. 12", "Fornitura": "Taglio laser + fresatura"})

    # traversa ponte
    m.add("PON-01", "Traversa ponte 40×40×2", "Asse X",
          [box(-100 - 20, -ay - 75, car_z1, 40, 2 * ay + 150, 40, C["inox"])], mov="x", explode=(0, 0, 640),
          info={"Materiale": "AISI 304 tubo 40×40×2", "Fornitura": "Carpenteria inox"})

    # ---------------- moduli Z ----------------
    zw, zt = P["zplate_w"], P["zplate_t"]
    zy = ay - 90                    # faccia interna piastra Z (250 con ay=340)
    for sy in (-1, 1):
        side = "Y−" if sy < 0 else "Y+"
        yin = sy * zy                 # faccia interna
        ymid = sy * (zy + zt / 2)
        out = sy  # verso esterno
        # piastra Z fissa (appesa al carrello)
        zp = [boxc(0, ymid, (P["zplate_bottom"] + car_z1) / 2, zw, zt, car_z1 - P["zplate_bottom"], C["plate"])]
        m.add("ZPL-01", f"Piastra Z fissa lato {side}", "Asse Z", zp, mov="x", explode=(0, out * 140, 560),
              info={"Materiale": "AISI 304 sp. 15", "Fornitura": "Taglio laser + fresatura"})
        # guide tonde Z + vite
        gz = []
        sh_y = sy * (zy - 8)
        for dx in (-100, 100):
            gz.append(cyl(dx, sh_y, (P["zplate_bottom"] + 20 + car_z1 - 10) / 2, "z", 16, car_z1 - P["zplate_bottom"] - 30, "#c9ced4"))
        gz.append(cyl(75, sh_y, (P["zplate_bottom"] + 10 + car_z1 + 20) / 2, "z", 16, car_z1 + 20 - P["zplate_bottom"] - 10, C["screw"]))
        m.add("ZGD", f"Guide Ø16 + vite TR16×4 lato {side}", "Asse Z", gz, mov="x", explode=(0, out * 90, 600),
              info={"Tipo": "albero Ø16 h6 inox + vite TR16×4 L=420 con supporti", "Fornitura": "Acquisto"})
        # motore Z
        mz = [boxc(75, sh_y, car_z1 + 10 + 50, 57, 57, 100, C["motor"]),
              boxc(75, sh_y, car_z1 + 10 + 102, 40, 40, 4, C["motor_cap"]),
              boxc(75, sh_y, car_z1 + 5, 90, 80, 10, C["plate"])]
        m.add("MOT-Z", f"Motore Z{1 if sy < 0 else 2} NEMA23 closed-loop", "Motori", mz, mov="x",
              explode=(0, out * 90, 760), info={"Tipo": "NEMA23 2 Nm encoder 1000 PPR + CL57T", "Fornitura": "Acquisto"})
        # slitta Z (mobile)
        sl_y = sy * (zy - 16 - P["slide_t"] / 2)
        sl = [boxc(0, sl_y, rc + P["slide_h"] / 2 - 45, P["slide_w"] + 60, P["slide_t"], P["slide_h"], C["plate"])]
        for dx in (-100, 100):
            sl.append(boxc(dx, sy * (zy - 8), rc + P["slide_h"] - 75, 34, 30, 45, C["block"]))
        sl.append(boxc(75, sy * (zy - 8), rc + P["slide_h"] - 95, 40, 30, 30, "#b08d3a"))  # chiocciola
        m.add("ZSL-01", f"Slitta Z lato {side}", "Asse Z", sl, mov="xz", explode=(0, out * 200, 360),
              info={"Materiale": "AISI 304 sp. 12 + pattini SC16UU", "Fornitura": "Taglio laser + fresatura"})
        # supporto cuscinetto flangiato SUCF204
        by = sy * (zy - 16 - P["slide_t"] - 12)
        bu = [boxc(0, by, rc, 86, 24, 86, C["bearing"]), cyl(0, by - sy * 14, rc, "y", 40, 8, C["inox"])]
        m.add("SUCF204", f"Supporto flangiato inox SUCF204 lato {side}", "Rullo", bu, mov="xz",
              explode=(0, out * 260, 300), info={"Tipo": "SUCF204 (inox, foro Ø20)", "Fornitura": "Acquisto"})

    # ---------------- rullo ----------------
    rl_len = P["roller_len"]
    stub_len = zy - rl_len / 2 + 10
    rp = [cyl(0, 0, rc, "y", P["roller_d"], rl_len, C["roller"])]
    for sy in (-1, 1):
        rp.append(cyl(0, sy * (rl_len / 2 + stub_len / 2), rc, "y", P["stub_d"], stub_len, C["inox"]))
    m.add("RUL-01", f"Rullo Ø{P['roller_d']} L={rl_len} con perni Ø20", "Rullo", rp, mov="xz", explode=(0, 0, 240),
          info={"Materiale": "AISI 304 tubo Ø100×3 rettificato Ra≤0,8 (alt. POM-C alimentare)", "Fornitura": "Tornitore"})
    # raschietto
    m.add("RAS-01", "Raschietto POM-C a molla", "Rullo",
          [boxc(-P["roller_d"] / 2 - 6, 0, rc + 25, 10, rl_len - 10, 40, C["pom"])], mov="xz", explode=(-120, 0, 300),
          info={"Materiale": "POM-C alimentare sp. 10", "Fornitura": "Fresatura plastica"})

    # ---------------- asse R ----------------
    ry = -(zy - 16 - P["slide_t"] / 2)       # slitta lato Y−
    mr_z = rc + 135
    rr = [cyl(0, ry - 12, mr_z, "y", 57, 0.1, C["motor"]),
          boxc(0, ry + 6 + 50, mr_z, 57, 100, 57, C["motor"]),
          cyl(0, ry - 14, mr_z, "y", 32, 18, C["pulley"]),
          cyl(0, ry - 14, rc, "y", 64, 18, C["pulley"]),
          boxc(-30, ry - 14, (rc + mr_z) / 2, 3, 15, mr_z - rc, C["belt"]),
          boxc(30, ry - 14, (rc + mr_z) / 2, 3, 15, mr_z - rc, C["belt"])]
    m.add("MOT-R", "Motore R (rotazione rullo) + cinghia HTD-5M 20T→40T", "Motori", rr, mov="xz",
          explode=(0, 120, 420), info={"Tipo": "NEMA23 closed-loop + CL57T, rapporto 2:1", "Fornitura": "Acquisto"})

    # ---------------- trasmissione X ----------------
    px = P["pulley_x"]
    belt_z = btop - bh / 2
    by_out = ay + bw / 2 + 15
    tx = []
    tx.append(cyl(-px, 0, belt_z, "y", 16, 2 * by_out + 120, C["screw"]))     # albero sincronismo
    for sy in (-1, 1):
        y = sy * by_out
        tx.append(cyl(-px, y, belt_z, "y", 32, 20, C["pulley"]))
        tx.append(cyl(px, y, belt_z, "y", 32, 20, C["pulley"]))
        tx.append(box(-px, y - 7.5, belt_z + 15, 2 * px, 15, 2, C["belt"]))
        tx.append(box(-px, y - 7.5, belt_z - 17, 2 * px, 15, 2, C["belt"]))
        tx.append(boxc(-px, sy * (ay + bw / 2 + 4), belt_z, 60, 8, 60, C["inox_dark"]))   # supporto KFL
        tx.append(boxc(px, sy * (ay + bw / 2 + 4), belt_z, 60, 8, 60, C["inox_dark"]))
    m.add("TRX-01", "Trasmissione X: albero Ø16, pulegge HTD-5M 20T, cinghie 15 mm", "Asse X", tx,
          explode=(0, 0, 380), info={"Fornitura": "Acquisto + tornitura albero"})
    mx = [boxc(-px, by_out + 60 + 50, belt_z, 57, 100, 57, C["motor"]),
          boxc(-px, by_out + 55, belt_z, 80, 10, 80, C["plate"])]
    m.add("MOT-X", "Motore X NEMA23 closed-loop", "Motori", mx, explode=(0, 150, 380),
          info={"Tipo": "NEMA23 2 Nm + CL57T, giunto elastico 8→16", "Fornitura": "Acquisto"})

    # ---------------- finecorsa ----------------
    fc = []
    fc.append(cyl(-(P["x_travel"] + 140), -ay - 30, btop + 10, "x", 12, 40, C["sensor"]))
    fc.append(cyl(P["x_travel"] + 140, -ay - 30, btop + 10, "x", 12, 40, C["sensor"]))
    m.add("SEN-X", "Finecorsa X_MIN / X_MAX induttivi M12", "Sensori", fc, explode=(0, -60, 420),
          info={"Tipo": "induttivo M12 PNP NO 24 V", "Fornitura": "Acquisto"})

    # ---------------- quadro elettrico ----------------
    bx = -ax - leg / 2 - 20
    q = [box(bx - P["box_d"], -P["box_w"] / 2, btop - P["box_h"] - 10, P["box_d"], P["box_w"], P["box_h"], C["box"]),
         cyl(bx - P["box_d"] - 10, 120, btop - 90, "x", 40, 20, C["estop"]),
         cyl(bx - P["box_d"] - 6, -120, btop - 90, "x", 22, 12, "#2a9a3a"),
         cyl(bx - P["box_d"] - 6, -170, btop - 90, "x", 22, 12, "#202020"),
         cyl(bx - 40, -P["box_w"] / 2 + 40, btop - 10 + 60, "z", 40, 120, "#30a040")]
    m.add("QE-01", "Quadro elettrico inox IP65 500×400×250 + colonna luminosa", "Elettronica", q,
          explode=(-260, 0, 300), info={"Contenuto": "Arduino Mega + Ethernet, 4 driver CL57T, PSU 48/24/12 V, sicurezza", "Fornitura": "Quadrista"})
    return m


# ---------------------------------------------------------------- OpenSCAD
def to_scad(m, P):
    out = ["// ManipMasta - generato da cad/model.py: non modificare a mano, rigenera.",
           "// Parametri vista:", "explode = 0;   // 0..1", "xpos = 0;      // posizione X rullo (mm)",
           f"gap = {P['gap_ref']};   // luce rullo-piano (mm)", "$fn = 48;", "",
           f"dz = gap - {P['gap_ref']};", ""]

    def col(h):
        h = h.lstrip("#")
        return "[%.3f,%.3f,%.3f]" % tuple(int(h[i:i + 2], 16) / 255 for i in (0, 2, 4))

    for p in m.parts:
        e = p["explode"]
        mv = {"fixed": "[0,0,0]", "x": "[xpos,0,0]", "xz": "[xpos,0,dz]"}[p["mov"]]
        out.append(f"// {p['code']} - {p['name']}")
        out.append(f"translate({mv}) translate(explode*[{e[0]},{e[1]},{e[2]}]) {{")
        for q in p["prims"]:
            if q["t"] == "box":
                c, s = q["c"], q["s"]
                out.append(f"  color({col(q['col'])}) translate([{c[0]-s[0]/2:.2f},{c[1]-s[1]/2:.2f},{c[2]-s[2]/2:.2f}]) cube([{abs(s[0]):.2f},{abs(s[1]):.2f},{abs(s[2]):.2f}]);")
            elif q["t"] == "cyl":
                c = q["c"]
                rot = {"x": "[0,90,0]", "y": "[-90,0,0]", "z": "[0,0,0]"}[q["ax"]]
                out.append(f"  color({col(q['col'])}) translate([{c[0]:.2f},{c[1]:.2f},{c[2]:.2f}]) rotate({rot}) cylinder(r={q['r']:.2f}, h={q['l']:.2f}, center=true);")
            elif q["t"] == "ell":
                c, r = q["c"], q["r"]
                out.append(f"  color({col(q['col'])}) translate([{c[0]},{c[1]},{c[2]}]) scale([{r[0]},{r[1]},{r[2]}]) sphere(r=1);")
        out.append("}")
    return "\n".join(out) + "\n"


def main():
    P = load_params()
    m = build(P)
    os.makedirs(os.path.join(HERE, "build"), exist_ok=True)
    data = {"params": P, "parts": m.parts}
    with open(os.path.join(HERE, "build", "model.json"), "w") as f:
        json.dump(data, f, separators=(",", ":"))
    with open(os.path.join(HERE, "manipmasta.scad"), "w") as f:
        f.write(to_scad(m, P))
    print(f"{len(m.parts)} parti, {sum(len(p['prims']) for p in m.parts)} primitive")


if __name__ == "__main__":
    main()
