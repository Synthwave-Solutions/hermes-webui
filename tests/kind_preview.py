"""Preview a data block the way the chat draws it, without a server.

    .venv/bin/python tests/kind_preview.py <kind-or-fence> <spec.json> <out-dir>

Checks the JSON with SWKit.build (kit-core plus every kinds/*.js), builds the
standalone kit page (the same page "Downloaden" gives) and screenshots it in
Chromium at 760 px light and dark and at 390 px dark. Prints the checks'
errors and warnings and any console error. Used while building new kinds.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

NODE = r"""
const path=require('path'),fs=require('fs');
const K=require(path.join(process.argv[1],'static/interactive-ui/kit-core.js'));
global.SWKit=K;
const dir=path.join(process.argv[1],'static/interactive-ui/kinds');
if(fs.existsSync(dir)) for(const f of fs.readdirSync(dir).sort()) if(f.endsWith('.js')) require(path.join(dir,f));
const fence=process.argv[2], kind=K.kitKind(fence)||fence;
const r=K.build(kind,fs.readFileSync(process.argv[3],'utf8'),{lang:'nl',fence});
process.stdout.write(JSON.stringify({kind,spec:r.spec,errors:r.errors,warnings:r.warnings,estHeight:r.estHeight}));
"""


def main() -> int:
    fence, spec_path, out = sys.argv[1], sys.argv[2], Path(sys.argv[3])
    out.mkdir(parents=True, exist_ok=True)
    res = json.loads(subprocess.run(["node", "-e", NODE, str(ROOT), fence, spec_path], capture_output=True, text=True, check=True).stdout)
    print("kind:", res["kind"], "| errors:", res["errors"], "| warnings:", res["warnings"], "| estHeight:", res["estHeight"])
    if not res["spec"]:
        return 1
    from api import interactive_ui
    errors = []
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        browser = p.chromium.launch()
        for name, width, mode in (("light", 760, "light"), ("dark", 760, "dark"), ("mobile", 390, "dark")):
            payload = {"kit": res["kind"], "spec": res["spec"], "data": None, "final": True, "restore": {}, "lang": res["spec"].get("lang", "nl"), "theme": mode}
            doc = interactive_ui.KIT_FRAME_HTML
            at = doc.index("<script>")
            js = json.dumps(payload).replace("<", "\\u003c")
            doc = doc[:at] + "<script>window.__SWKIT_DOC=" + js + ";</script>" + doc[at:]
            doc = doc.replace('<html lang="nl" data-theme="dark">', f'<html lang="nl" data-theme="{mode}">', 1)
            page = browser.new_page(viewport={"width": width, "height": 900})
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.set_content(doc)
            page.wait_for_timeout(1200)
            page.screenshot(path=str(out / f"{res['kind']}-{name}.png"), full_page=True)
            page.close()
        browser.close()
    print("console errors:", errors[:5])
    print("screenshots in", out)
    return 0 if not errors else 2


if __name__ == "__main__":
    raise SystemExit(main())
