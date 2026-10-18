#!/usr/bin/env python3
"""Inserisce cad/build/model.json nel template e produce un HTML autonomo + render PNG (Playwright)."""
import json, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def build():
    tpl = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
    model = open(os.path.join(HERE, "build", "model.json"), encoding="utf-8").read()
    body = tpl.replace("/*MODEL*/null", model)
    # pagina completa (apribile da file) + frammento per pubblicazione
    page = ("<!doctype html>\n<html lang=\"it\"><head><meta charset=\"utf-8\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1,viewport-fit=cover\">\n"
            + body.replace("<div class=\"app\">", "</head><body>\n<div class=\"app\">", 1) + "\n</body></html>\n")
    out = os.path.join(HERE, "build", "manipmasta_3d.html")
    open(out, "w", encoding="utf-8").write(page)
    open(os.path.join(HERE, "build", "manipmasta_3d_fragment.html"), "w", encoding="utf-8").write(body)
    return out


def render(path):
    from playwright.sync_api import sync_playwright
    img = os.path.join(ROOT, "docs", "img")
    os.makedirs(img, exist_ok=True)
    with sync_playwright() as p:
        b = p.chromium.launch(args=["--use-gl=swiftshader", "--enable-webgl", "--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1600, "height": 1000})
        # in ambienti senza internet: THREE_LOCAL=/percorso/pacchetto/three (npm pack three@0.128.0)
        loc = os.environ.get("THREE_LOCAL")
        if loc:
            pg.route("**/three.min.js", lambda r: r.fulfill(path=os.path.join(loc, "build/three.min.js")))
            pg.route("**/OrbitControls.js", lambda r: r.fulfill(path=os.path.join(loc, "examples/js/controls/OrbitControls.js")))
            pg.route("https://fonts.googleapis.com/**", lambda r: r.fulfill(body="", content_type="text/css"))
        pg.goto("file://" + path)
        pg.wait_for_function("window.__mm !== undefined", timeout=30000)
        shots = [("assieme_iso", "iso", 0, 0, 40), ("esploso_iso", "iso", 1, 0, 40),
                 ("vista_fronte", "front", 0, 300, 20), ("vista_alto", "top", 0, -300, 20)]
        for name, view, ex, x, gap in shots:
            pg.evaluate(f"(()=>{{const m=window.__mm;m.state.ex={ex};m.state.x={x};m.state.gap={gap};m.state.minGap={gap};m.setView('{view}');m.refresh();}})()")
            pg.wait_for_timeout(600)
            pg.locator(".stage").screenshot(path=os.path.join(img, name + ".png"))
        b.close()


if __name__ == "__main__":
    out = build()
    print(out)
    if "--render" in sys.argv:
        render(out)
