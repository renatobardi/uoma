"""
Fase 3 (geração) — converte artifacts/steps.json em tests/flow.spec.ts.

Só passos executados via SELETOR estável viram comando determinístico.
Passos 'via: pixel' viram comentário (não são reproduzíveis em CI).
Assertions = characterization/golden master (v1: snapshot de URL).
"""
import json
from pathlib import Path

ARTIFACTS = Path("/app/artifacts")
TESTS = Path("/app/tests")


def _esc(s: str) -> str:
    return (s or "").replace("\\", "\\\\").replace("`", "\\`").replace("${", "\\${")


def _ts_locator(sel):
    if not sel:
        return None
    if sel.startswith("[data-testid"):
        return f"page.locator(`{sel}`)"
    try:
        d = json.loads(sel)
    except (ValueError, TypeError):
        return None
    if d.get("name"):
        return f"page.getByRole('{d['role']}', {{ name: `{_esc(d['name'])}` }}).first()"
    return f"page.locator('{d.get('tag', '*')}').first()"


def gen():
    steps = json.loads((ARTIFACTS / "steps.json").read_text())
    L = [
        "import { test, expect } from '@playwright/test';",
        "",
        "// Gerado por uoma — characterization test (golden master).",
        "// Revise antes de confiar: assertions são placeholders de regressão, não de correção.",
        "test('fluxo descoberto pelo uoma', async ({ page }) => {",
        "  await page.goto(process.env.TARGET_URL!);",
    ]
    for s in steps:
        t = s.get("action")
        sel = s.get("selector")
        via = s.get("via")
        loc = _ts_locator(sel) if via == "selector" else None

        if t == "finished":
            continue
        if t in ("click", "left_double", "right_single"):
            if loc:
                method = {"click": "click", "left_double": "dblclick",
                          "right_single": "click"}[t]
                arg = "{ button: 'right' }" if t == "right_single" else ""
                L.append(f"  await {loc}.{method}({arg});")
            else:
                L.append(f"  // [pixel-only, não determinístico] {t} @ {s.get('url','')}")
        elif t == "type":
            L.append(f"  await page.keyboard.type(`{_esc(s.get('content',''))}`);")
        elif t == "hotkey" and s.get("key"):
            keys = "+".join(s["key"].split())
            L.append(f"  await page.keyboard.press('{keys}');")
        elif t == "scroll":
            L.append(f"  await page.mouse.wheel(0, 600);  // {s.get('direction','down')}")

    L += [
        "",
        "  // golden master (v1): fixa a URL final. TODO: snapshot de DOM/texto/screenshot.",
        "  await expect(page).toHaveURL(process.env.GOLDEN_URL ?? /.*/);",
        "});",
        "",
    ]
    TESTS.mkdir(parents=True, exist_ok=True)
    (TESTS / "flow.spec.ts").write_text("\n".join(L))
    print("tests/flow.spec.ts gerado")


if __name__ == "__main__":
    gen()
