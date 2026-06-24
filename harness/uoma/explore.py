"""
Fase 2 — loop de authoring.

Roda DENTRO do container. Fala com o UI-TARS no HOST (MODEL_BASE_URL).
Por passo: screenshot -> UI-TARS -> ação -> map coord->DOM (seletor estável)
-> executa via SELETOR (fallback pixel) -> grava em artifacts/steps.json.

Saída: artifacts/steps.json + artifacts/screens/NNN.png (insumo do uoma.gen).
"""
import os
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from uoma import uitars

TARGET_URL = os.environ["TARGET_URL"]
TARGET_USER = os.environ.get("TARGET_USER") or None
TARGET_PASS = os.environ.get("TARGET_PASS") or None
ARTIFACTS = Path("/app/artifacts")
VIEWPORT = (1280, 800)

# data-testid > role+accessible name > tag. Retorna string ([data-testid=...]) ou JSON.
SELECTOR_JS = """
([x, y]) => {
  const el = document.elementFromPoint(x, y);
  if (!el) return null;
  const t = el.closest('[data-testid]');
  if (t) return `[data-testid="${t.getAttribute('data-testid')}"]`;
  const role = el.getAttribute('role') || el.tagName.toLowerCase();
  const name = (el.getAttribute('aria-label') || el.innerText || '').trim().slice(0, 50);
  return JSON.stringify({ role, name, tag: el.tagName.toLowerCase() });
}
"""


def selector_at(page, px, py):
    return page.evaluate(SELECTOR_JS, [px, py])


def _locator(page, sel):
    if not sel:
        return None
    if sel.startswith("[data-testid"):
        return page.locator(sel).first
    try:
        d = json.loads(sel)
    except (ValueError, TypeError):
        return None
    if d.get("name"):
        try:
            return page.get_by_role(d["role"], name=d["name"], exact=False).first
        except Exception:
            pass
    return page.locator(d.get("tag", "*")).first


def execute(page, act):
    """Executa a ação; devolve metadados do passo (selector, via, etc.)."""
    t = act["type"]
    out = {}
    vw, vh = VIEWPORT

    if t in ("click", "left_double", "right_single") and "start" in act:
        px, py = uitars.to_pixels(act["start"], vw, vh)
        sel = selector_at(page, px, py)
        out["selector"] = sel
        loc = _locator(page, sel)
        if loc and loc.count() > 0:
            if t == "click":
                loc.click()
            elif t == "left_double":
                loc.dblclick()
            else:
                loc.click(button="right")
            out["via"] = "selector"
        else:
            page.mouse.click(
                px, py,
                button="right" if t == "right_single" else "left",
                click_count=2 if t == "left_double" else 1,
            )
            out["via"] = "pixel"  # não vira spec determinístico

    elif t == "type":
        page.keyboard.type(act.get("content", ""))
        out["content"] = act.get("content", "")

    elif t == "hotkey":
        keys = act.get("key", "").split()
        if keys:
            page.keyboard.press("+".join(keys))
        out["key"] = act.get("key")

    elif t == "scroll":
        dx, dy = {
            "down": (0, 600), "up": (0, -600),
            "left": (-600, 0), "right": (600, 0),
        }.get(act.get("direction", "down"), (0, 600))
        page.mouse.wheel(dx, dy)
        out["direction"] = act.get("direction", "down")

    elif t == "drag" and "start" in act and "end" in act:
        sx, sy = uitars.to_pixels(act["start"], vw, vh)
        ex, ey = uitars.to_pixels(act["end"], vw, vh)
        page.mouse.move(sx, sy)
        page.mouse.down()
        page.mouse.move(ex, ey)
        page.mouse.up()

    elif t == "wait":
        page.wait_for_timeout(1000)

    return out


def _login_if_needed(page):
    # Stub: preencha se a app exigir login. Mantém credenciais fora do código (env).
    if TARGET_USER and TARGET_PASS:
        # TODO: ajustar seletores ao form de login real da TARGET_URL.
        pass


def run(task: str, max_steps: int = 40):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    (ARTIFACTS / "screens").mkdir(exist_ok=True)
    steps, history = [], []

    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page(viewport={"width": VIEWPORT[0], "height": VIEWPORT[1]})
        page.goto(TARGET_URL)
        page.wait_for_load_state("networkidle")
        _login_if_needed(page)

        for i in range(max_steps):
            shot = page.screenshot()
            (ARTIFACTS / "screens" / f"{i:03d}.png").write_bytes(shot)
            act = uitars.ask(shot, task, history)
            history.append(act.get("raw", "")[:200])

            rec = {"i": i, "action": act["type"], "url": page.url}
            if act["type"] == "finished":
                rec["content"] = act.get("content", "")
                steps.append(rec)
                break
            try:
                rec.update(execute(page, act))
            except Exception as e:  # noqa: BLE001 - registrar e seguir
                rec["error"] = str(e)
            steps.append(rec)
            page.wait_for_timeout(500)

        browser.close()

    (ARTIFACTS / "steps.json").write_text(
        json.dumps(steps, indent=2, ensure_ascii=False)
    )
    print(f"{len(steps)} passos -> artifacts/steps.json")


if __name__ == "__main__":
    run(task=os.environ.get(
        "UOMA_TASK",
        "Explore a aplicação e percorra os principais fluxos de usuário.",
    ))
