"""Persistenza SQLite (stdlib sqlite3): ricette e storico cicli."""
from __future__ import annotations

import os
import sqlite3
import threading
import time

RECIPE_FIELDS = ("name", "cx", "s0", "s1", "g0", "g1", "dg", "f", "n", "od", "note")

SAMPLE_RECIPES = [
    # Frolla: impasto burroso, si lavora a velocità media, finale 5 mm
    dict(name="Frolla 5 mm", cx=0, s0=150, s1=300, g0=40, g1=5, dg=3, f=60, n=2, od=2.0,
         note="Pasta frolla fredda di frigo (4-6 °C), panetto 1,5 kg. Spolverare il piano."),
    # Sfoglia: riduzioni piccole per non rompere gli strati, più lenta
    dict(name="Sfoglia 3 mm", cx=0, s0=180, s1=400, g0=30, g1=3, dg=2, f=45, n=3, od=1.5,
         note="Pasta sfoglia dopo le pieghe e riposo. Riduzioni piccole per non rompere gli strati."),
    # Biscotti: impasto più spesso, poche passate
    dict(name="Pasta biscotti 8 mm", cx=0, s0=140, s1=260, g0=45, g1=8, dg=4, f=70, n=1, od=2.0,
         note="Impasto per biscotti da stampo. Finale 8 mm."),
]

SCHEMA = """
CREATE TABLE IF NOT EXISTS recipes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    cx REAL NOT NULL, s0 REAL NOT NULL, s1 REAL NOT NULL,
    g0 REAL NOT NULL, g1 REAL NOT NULL, dg REAL NOT NULL,
    f REAL NOT NULL, n INTEGER NOT NULL, od REAL NOT NULL,
    note TEXT NOT NULL DEFAULT '',
    created_at REAL NOT NULL, updated_at REAL NOT NULL
);
CREATE TABLE IF NOT EXISTS history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    started_at REAL NOT NULL,
    ended_at REAL,
    duration_s REAL,
    recipe_id INTEGER,
    recipe_name TEXT,
    run_line TEXT,
    np INTEGER,
    passes_done INTEGER NOT NULL DEFAULT 0,
    outcome TEXT NOT NULL DEFAULT 'in corso',
    detail TEXT NOT NULL DEFAULT ''
);
CREATE TABLE IF NOT EXISTS meta (k TEXT PRIMARY KEY, v TEXT);
"""


class Database:
    def __init__(self, path: str):
        self.path = path
        if path != ":memory:":
            d = os.path.dirname(os.path.abspath(path))
            os.makedirs(d, exist_ok=True)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.executescript(SCHEMA)
        self._seed()

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _seed(self) -> None:
        with self._lock:
            row = self._conn.execute("SELECT v FROM meta WHERE k='seeded'").fetchone()
            if row:
                return
            for r in SAMPLE_RECIPES:
                self.create_recipe(r)
            self._conn.execute("INSERT INTO meta(k, v) VALUES ('seeded', '1')")
            self._conn.commit()

    # ---------------------------------------------------------- ricette
    def list_recipes(self) -> list[dict]:
        with self._lock:
            rows = self._conn.execute("SELECT * FROM recipes ORDER BY name COLLATE NOCASE").fetchall()
        return [dict(r) for r in rows]

    def get_recipe(self, rid: int) -> dict | None:
        with self._lock:
            r = self._conn.execute("SELECT * FROM recipes WHERE id=?", (rid,)).fetchone()
        return dict(r) if r else None

    def create_recipe(self, data: dict) -> dict:
        now = time.time()
        vals = [data.get(k, "" if k == "note" else None) for k in RECIPE_FIELDS]
        with self._lock:
            cur = self._conn.execute(
                f"INSERT INTO recipes({','.join(RECIPE_FIELDS)}, created_at, updated_at) "
                f"VALUES ({','.join('?' * len(RECIPE_FIELDS))}, ?, ?)", (*vals, now, now))
            self._conn.commit()
            return self.get_recipe(cur.lastrowid)

    def update_recipe(self, rid: int, data: dict) -> dict | None:
        sets = [k for k in RECIPE_FIELDS if k in data]
        if not sets:
            return self.get_recipe(rid)
        with self._lock:
            cur = self._conn.execute(
                f"UPDATE recipes SET {', '.join(f'{k}=?' for k in sets)}, updated_at=? WHERE id=?",
                (*[data[k] for k in sets], time.time(), rid))
            self._conn.commit()
            if cur.rowcount == 0:
                return None
            return self.get_recipe(rid)

    def delete_recipe(self, rid: int) -> bool:
        with self._lock:
            cur = self._conn.execute("DELETE FROM recipes WHERE id=?", (rid,))
            self._conn.commit()
            return cur.rowcount > 0

    # ---------------------------------------------------------- storico
    def start_cycle(self, recipe_id: int | None, recipe_name: str | None, run_line: str | None,
                    np_: int | None, started_at: float | None = None) -> int:
        with self._lock:
            # un ciclo rimasto aperto (es. riavvio server) viene chiuso come "sconosciuto"
            self._conn.execute(
                "UPDATE history SET outcome='sconosciuto', ended_at=started_at, "
                "detail='nuovo ciclo avviato prima della chiusura' WHERE ended_at IS NULL")
            cur = self._conn.execute(
                "INSERT INTO history(started_at, recipe_id, recipe_name, run_line, np) VALUES (?,?,?,?,?)",
                (started_at or time.time(), recipe_id, recipe_name, run_line, np_))
            self._conn.commit()
            return cur.lastrowid

    def open_cycle(self) -> dict | None:
        with self._lock:
            r = self._conn.execute(
                "SELECT * FROM history WHERE ended_at IS NULL ORDER BY id DESC LIMIT 1").fetchone()
        return dict(r) if r else None

    def update_cycle_pass(self, hid: int, passes_done: int, np_: int | None) -> None:
        with self._lock:
            self._conn.execute(
                "UPDATE history SET passes_done=?, np=COALESCE(?, np) WHERE id=?", (passes_done, np_, hid))
            self._conn.commit()

    def end_cycle(self, hid: int, outcome: str, detail: str = "", ended_at: float | None = None) -> None:
        ended_at = ended_at or time.time()
        with self._lock:
            self._conn.execute(
                "UPDATE history SET ended_at=?, duration_s=?-started_at, outcome=?, detail=? WHERE id=?",
                (ended_at, ended_at, outcome, detail, hid))
            self._conn.commit()

    def list_history(self, limit: int = 50) -> list[dict]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [dict(r) for r in rows]
