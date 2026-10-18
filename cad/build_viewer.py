#!/usr/bin/env python3
"""Inserisce cad/build/model.json nel template, produce l'HTML autonomo e (con --render) le immagini:
   docs/img/*.png (assieme, esploso, visite guidate) e cad/build/steps/step_XX_[a|b].png (montaggio).
In ambienti senza internet: THREE_LOCAL=/percorso/three (npm pack three@0.128.0, cartella package/)."""
import json
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def build():
    tpl = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
    model = open(os.path.join(HERE, "build", "model.json"), encoding="utf-8").read()
    body = tpl.replace("/*MODEL*/null", model)
    page = ("<!doctype html>\n<html lang=\"it\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
            + body.replace("<div class=\"app\">", "</head><body>\n<div class=\"app\">", 1) + "\n</body></html>\n")
    out = os.path.join(HERE, "build", "manipmasta_3d.html")
    open(out, "w", encoding="utf-8").write(page)
    open(os.path.join(HERE, "build", "manipmasta_3d_fragment.html"), "w", encoding="utf-8").write(body)
    return out


def open_page(p, path, w=1600, h=1000):
    pg = p.new_page(viewport={"width": w, "height": h})
    loc = os.environ.get("THREE_LOCAL")
    if loc:
        pg.route("**/three.min.js", lambda r: r.fulfill(path=os.path.join(loc, "build/three.min.js")))
        pg.route("**/OrbitControls.js", lambda r: r.fulfill(path=os.path.join(loc, "examples/js/controls/OrbitControls.js")))
    pg.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(body="", content_type="text/css"))
    pg.goto("file://" + path)
    pg.wait_for_function("window.__mm !== undefined", timeout=30000)
    pg.evaluate("window.__mm.state.freeze = true")
    return pg


def shot(pg, path):
    pg.evaluate("(()=>{const m=window.__mm; m.layout(); m.controls.update(); m.renderer.render(m.scene,m.camera); m.drawLabels();})()")
    pg.wait_for_timeout(250)
    pg.locator(".stage").screenshot(path=path)


def render(path, only=None):
    from playwright.sync_api import sync_playwright
    img = os.path.join(ROOT, "docs", "img")
    stp = os.path.join(HERE, "build", "steps")
    os.makedirs(img, exist_ok=True)
    os.makedirs(stp, exist_ok=True)
    model = json.load(open(os.path.join(HERE, "build", "model.json")))
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = open_page(b, path)
        hide = "document.querySelectorAll('.ctrl,.stepbar,.head,.views').forEach(e=>e.style.visibility='hidden')"
        if only in (None, "base"):
            pg.evaluate(hide)
            for name, view, ex, x, gap in [("assieme_iso", "iso", 0, 0, 40), ("esploso_iso", "iso", 1, 0, 40),
                                           ("vista_fronte", "front", 0, 300, 20), ("vista_alto", "top", 0, -300, 20)]:
                pg.evaluate(f"(()=>{{const m=window.__mm;m.state.ex={ex};m.state.x={x};m.state.gap={gap};m.state.minGap={gap};m.setView('{view}');m.refresh();}})()")
                shot(pg, os.path.join(img, name + ".png"))
        if only in (None, "tour"):
            pg.evaluate("window.__mm.setMode('tour')")
            pg.evaluate(hide)
            for t in model["tours"]:
                pg.evaluate(f"(()=>{{const m=window.__mm; m.startTour('{t['id']}'); m.state.x=-200; m.state.gap=60; "
                            f"if('{t['id']}'==='quadro') m.state.door=1; if('{t['id']}'==='ciclo'){{m.state.x=150;m.state.gap=12;m.state.minGap=12;}} }})()")
                shot(pg, os.path.join(img, f"funziona_{t['id']}.png"))
        if only in (None, "step"):
            pg.evaluate("window.__mm.setMode('step')")
            pg.evaluate(hide)
            for i in range(1, len(model["steps"])):
                pg.evaluate(f"(()=>{{const m=window.__mm; m.goStep({i}); m.state.f=1;}})()")
                shot(pg, os.path.join(stp, f"step_{i:02d}_a.png"))
                pg.evaluate("(()=>{const m=window.__mm; m.state.f=0; })()")
                pg.evaluate("document.getElementById('labels').innerHTML=''; window.__mm.scene.children.filter(o=>o.type==='ArrowHelper').forEach(a=>a.visible=false)")
                shot(pg, os.path.join(stp, f"step_{i:02d}_b.png"))
        b.close()


if __name__ == "__main__":
    out = build()
    print(out)
    if "--render" in sys.argv:
        only = sys.argv[sys.argv.index("--render") + 1] if len(sys.argv) > sys.argv.index("--render") + 1 else None
        render(out, only)
