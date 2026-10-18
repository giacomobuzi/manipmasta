"""Protocollo ManipMasta (SPEC §3, §4): validazione comandi, riga RUN, stime.

Modulo puro (nessuna dipendenza da rete/DB), usato da server, simulatore e test.
"""
from __future__ import annotations

import math
import re

# Comandi ammessi dal server (whitelist, SPEC §3)
COMMANDS = (
    "PING", "STATUS", "HOME", "ENABLE", "JOG", "MOVE", "GAP", "RUN", "PAUSE",
    "RESUME", "STOP", "RESET", "SET", "GET", "SAVE", "DEFAULTS",
)
NO_ARG = {"PING", "STATUS", "HOME", "PAUSE", "RESUME", "STOP", "RESET", "SAVE", "DEFAULTS"}

# Parametri EEPROM (SPEC §2.2) con default
PARAM_DEFAULTS: dict[str, object] = {
    "x_spm": 16.0, "z_spm": 200.0, "r_spm": 5.093,
    "x_min": -700.0, "x_max": 700.0, "g_min": 0.5, "g_max": 150.0,
    "z_home_gap": 150.0, "x_vmax": 150.0, "x_acc": 300.0,
    "z_vmax": 8.0, "z_acc": 20.0, "x_home_off": 20.0, "od": 2.0,
    "ip": "192.168.50.60", "gw": "192.168.50.1", "mask": "255.255.255.0", "dns": "192.168.50.1",
    "mqtt_host": "192.168.50.10", "mqtt_port": 1883, "mqtt_user": "manipmasta", "mqtt_pass": "",
}
IP_KEYS = {"ip", "gw", "mask", "dns", "mqtt_host"}
STR_KEYS = {"mqtt_user", "mqtt_pass"}
INT_KEYS = {"mqtt_port"}
NUM_KEYS = set(PARAM_DEFAULTS) - IP_KEYS - STR_KEYS

# Parametri del ciclo RUN (SPEC §4) con default (esempio SPEC §3)
RUN_KEYS = ("cx", "s0", "s1", "g0", "g1", "dg", "f", "n", "od")
RUN_DEFAULTS = {"cx": 0.0, "s0": 150.0, "s1": 300.0, "g0": 40.0, "g1": 5.0,
                "dg": 3.0, "f": 60.0, "n": 2, "od": 2.0}

RUN_MARGIN = 60.0     # mm oltre il bordo impasto (SPEC §4)
SAFE_GAP_ADD = 20.0   # g0 + 20 gap sicuro di approccio
END_GAP_ADD = 30.0    # g1 + 30 a fine ciclo

_NUM = r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)"
_NUM_RE = re.compile(rf"^{_NUM}$")
_IP_RE = re.compile(r"^(?:\d{1,3}\.){3}\d{1,3}$")
_STR_RE = re.compile(r"^[A-Za-z0-9_.\-@#%+=!]{0,32}$")


class CommandError(ValueError):
    """Comando non valido (sintassi lato server)."""


def is_num(s: str) -> bool:
    return bool(_NUM_RE.match(s))


def fmt(v: float) -> str:
    """Numero compatto per la riga di comando (niente zeri inutili)."""
    if isinstance(v, int) or float(v).is_integer():
        return str(int(v))
    return f"{float(v):.3f}".rstrip("0").rstrip(".")


def parse_run_args(tokens: list[str]) -> dict[str, float]:
    """Parsa `k=v` della riga RUN. Chiavi sconosciute o valori non numerici -> CommandError.
    Restituisce solo le chiavi presenti (i mancanti li completa il firmware)."""
    out: dict[str, float] = {}
    for tok in tokens:
        if "=" not in tok:
            raise CommandError(f"argomento RUN non valido: {tok!r} (atteso chiave=valore)")
        k, v = tok.split("=", 1)
        k = k.strip().lower()
        if k not in RUN_KEYS:
            raise CommandError(f"parametro RUN sconosciuto: {k}")
        if not is_num(v):
            raise CommandError(f"valore non numerico per {k}: {v!r}")
        if k in out:
            raise CommandError(f"parametro RUN ripetuto: {k}")
        out[k] = int(float(v)) if k == "n" else float(v)
    return out


def run_params(partial: dict[str, float]) -> dict[str, float]:
    p = dict(RUN_DEFAULTS)
    p.update(partial)
    return p


def build_run_line(p: dict) -> str:
    return "RUN " + " ".join(f"{k}={fmt(p[k])}" for k in RUN_KEYS if k in p and p[k] is not None)


def validate_command(line: str) -> str:
    """Valida un comando contro la whitelist e la sintassi della SPEC §3.
    Restituisce la riga normalizzata (parola chiave maiuscola, spazi singoli)."""
    if not isinstance(line, str):
        raise CommandError("comando mancante")
    if any(c in line for c in "\r\n\t\0"):
        raise CommandError("caratteri di controllo non ammessi")
    if len(line) > 200:
        raise CommandError("comando troppo lungo")
    parts = line.strip().split()
    if not parts:
        raise CommandError("comando vuoto")
    kw, args = parts[0].upper(), parts[1:]
    if kw not in COMMANDS:
        raise CommandError(f"comando non ammesso: {kw}")

    if kw in NO_ARG:
        if args:
            raise CommandError(f"{kw} non accetta argomenti")
        return kw
    if kw == "ENABLE":
        if len(args) != 1 or args[0] not in ("0", "1"):
            raise CommandError("uso: ENABLE 1|0")
        return f"ENABLE {args[0]}"
    if kw == "JOG":
        if len(args) != 2 or args[0].upper() not in ("X", "G", "R") or not is_num(args[1]):
            raise CommandError("uso: JOG X|G|R <mm>")
        return f"JOG {args[0].upper()} {args[1]}"
    if kw == "MOVE":
        ok = len(args) in (2, 4) and args[0].upper() == "X" and is_num(args[1])
        if ok and len(args) == 4:
            ok = args[2].upper() == "F" and is_num(args[3]) and float(args[3]) > 0
        if not ok:
            raise CommandError("uso: MOVE X <mm> [F <mm/s>]")
        out = f"MOVE X {args[1]}"
        return out + (f" F {args[3]}" if len(args) == 4 else "")
    if kw == "GAP":
        if len(args) != 1 or not is_num(args[0]):
            raise CommandError("uso: GAP <mm>")
        return f"GAP {args[0]}"
    if kw == "RUN":
        parsed = parse_run_args(args)
        return build_run_line(parsed) if parsed else "RUN"
    if kw == "GET":
        if len(args) != 1 or args[0].lower() not in PARAM_DEFAULTS:
            raise CommandError("uso: GET <chiave> (chiave SPEC §2.2)")
        return f"GET {args[0].lower()}"
    if kw == "SET":
        if len(args) != 2 or args[0].lower() not in PARAM_DEFAULTS:
            raise CommandError("uso: SET <chiave> <valore> (chiave SPEC §2.2)")
        key, val = args[0].lower(), args[1]
        if key in IP_KEYS and not _valid_ip(val):
            raise CommandError(f"{key}: indirizzo IPv4 non valido")
        if key in INT_KEYS and not (val.isdigit() and 1 <= int(val) <= 65535):
            raise CommandError(f"{key}: porta non valida")
        if key in NUM_KEYS and key not in INT_KEYS and not is_num(val):
            raise CommandError(f"{key}: valore numerico richiesto")
        if key in STR_KEYS and not _STR_RE.match(val):
            raise CommandError(f"{key}: caratteri non ammessi (max 32)")
        return f"SET {key} {val}"
    raise CommandError(f"comando non gestito: {kw}")  # pragma: no cover


def _valid_ip(s: str) -> bool:
    return bool(_IP_RE.match(s)) and all(0 <= int(o) <= 255 for o in s.split("."))


# ---------------------------------------------------------------- ciclo RUN

def num_passes(g0: float, g1: float, dg: float, n: int) -> int:
    """np = ceil((g0 − g1)/dg) + n  (SPEC §4)."""
    if dg <= 0:
        raise ValueError("dg deve essere > 0")
    return max(0, math.ceil(round((g0 - g1) / dg, 9))) + int(n)


def pass_plan(p: dict) -> list[tuple[float, float, float]]:
    """Piano delle passate doppie come il firmware (SPEC §4): lista (gap_avanti, gap_indietro, s).
    La passata avanti si fa al gap corrente; a fine corsa (fuori impasto) si applica
    gap = max(g1, gap − dg) e si torna indietro. Dopo ceil((g0−g1)/dg) passate doppie il gap
    è g1; seguono n passate doppie extra a g1. s è interpolata linearmente tra s0 e s1."""
    np_ = num_passes(p["g0"], p["g1"], p["dg"], p["n"])
    plan = []
    gap = float(p["g0"])
    for k in range(np_):
        s = p["s0"] + (p["s1"] - p["s0"]) * (k / (np_ - 1) if np_ > 1 else 1.0)
        nxt = max(float(p["g1"]), gap - p["dg"])
        plan.append((round(gap, 3), round(nxt, 3), round(s, 3)))
        gap = nxt
    return plan


def move_time(dist: float, vmax: float, acc: float) -> float:
    """Durata di un movimento trapezoidale (o triangolare)."""
    d = abs(dist)
    if d <= 0:
        return 0.0
    d_acc = vmax * vmax / acc
    if d >= d_acc:
        return d / vmax + vmax / acc
    return 2 * math.sqrt(d / acc)


def estimate_seconds(p: dict, params: dict | None = None, x_start: float = 0.0) -> float:
    """Stima della durata del ciclo con la cinematica di SPEC §2.2 (stessa logica del simulatore)."""
    pr = dict(PARAM_DEFAULTS)
    if params:
        pr.update(params)
    xv, xa, zv, za = pr["x_vmax"], pr["x_acc"], pr["z_vmax"], pr["z_acc"]
    f, cx = min(p["f"], xv), p["cx"]
    plan = pass_plan(p)
    if not plan:
        return 0.0
    t = 0.0
    g_safe = min(pr["g_max"], p["g0"] + SAFE_GAP_ADD)
    t += move_time(20.0, zv, za)  # salita a gap sicuro (stima)
    x0 = cx - p["s0"] - RUN_MARGIN
    t += move_time(x0 - x_start, xv, xa)
    t += move_time(g_safe - p["g0"], zv, za)
    x = x0
    for g_fwd, g_back, s in plan:
        a, b = cx - s - RUN_MARGIN, cx + s + RUN_MARGIN
        t += move_time(a - x, f, xa)          # riposizionamento se s cresce
        t += move_time(b - a, f, xa)          # passata avanti
        t += move_time(g_fwd - g_back, zv, za)  # nuovo gap fuori impasto
        t += move_time(b - a, f, xa)          # passata indietro
        x = a
    t += move_time(p["g1"] + END_GAP_ADD - plan[-1][1], zv, za)
    t += move_time(cx - x, xv, xa)
    return t


def run_limits_error(p: dict, params: dict | None = None) -> str | None:
    """Verifica limiti software del ciclo; None se ok, altrimenti messaggio."""
    pr = dict(PARAM_DEFAULTS)
    if params:
        pr.update(params)
    if p["dg"] <= 0:
        return "dg deve essere > 0"
    if p["f"] <= 0 or p["f"] > pr["x_vmax"]:
        return f"f fuori range (0..{fmt(pr['x_vmax'])})"
    if p["g1"] < pr["g_min"] or p["g0"] > pr["g_max"] or p["g0"] < p["g1"]:
        return f"gap fuori range (g_min {fmt(pr['g_min'])} ≤ g1 ≤ g0 ≤ g_max {fmt(pr['g_max'])})"
    if p["s0"] <= 0 or p["s1"] <= 0:
        return "s0 e s1 devono essere > 0"
    if int(p["n"]) < 0 or int(p["n"]) > 50:
        return "n fuori range (0..50)"
    if not (0 <= p["od"] <= 20):
        return "od fuori range (0..20 %)"
    smax = max(p["s0"], p["s1"])
    if p["cx"] - smax - RUN_MARGIN < pr["x_min"] or p["cx"] + smax + RUN_MARGIN > pr["x_max"]:
        return "corsa fuori dai limiti X (cx ± s + 60)"
    return None
