"""
Fase 2 — loop de authoring (SKELETON).

Roda DENTRO do container. Fala com o UI-TARS no HOST (MODEL_BASE_URL).
Fluxo por passo:
  screenshot (Playwright) -> UI-TARS (ação + coord) -> map coord->DOM (seletor estável)
  -> executa via SELETOR (não pixel) -> grava passo.

Este arquivo é o esqueleto da arquitetura; as partes marcadas TODO são
preenchidas na execução, quando TARGET_URL estiver definido.
"""
import os
import json
import base64
from pathlib import Path

from openai import OpenAI
from playwright.sync_api import sync_playwright

MODEL_BASE_URL = os.environ["MODEL_BASE_URL"]
MODEL_NAME = os.environ.get("MODEL_NAME", "ui-tars-1.5-7b")
TARGET_URL = os.environ["TARGET_URL"]
ARTIFACTS = Path("/app/artifacts")

client = OpenAI(base_url=MODEL_BASE_URL, api_key="none")

# Prioridade de seletor estável: data-testid > role+name > css path curto.
COORD_TO_SELECTOR_JS = """
([x, y]) => {
  const el = document.elementFromPoint(x, y);
  if (!el) return null;
  if (el.dataset && el.dataset.testid) return `[data-testid="${el.dataset.testid}"]`;
  const role = el.getAttribute('role') || el.tagName.toLowerCase();
  const name = (el.getAttribute('aria-label') || el.textContent || '').trim().slice(0, 40);
  return JSON.stringify({ role, name, tag: el.tagName.toLowerCase() });
}
"""


def ask_uitars(screenshot_png: bytes, goal: str) -> dict:
    """Manda screenshot + objetivo, retorna a próxima ação no action-space do UI-TARS."""
    b64 = base64.b64encode(screenshot_png).decode()
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": goal},  # TODO: prompt completo c/ action-space
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ],
        }],
    )
    return parse_action(resp.choices[0].message.content)  # TODO


def parse_action(raw: str) -> dict:
    """click/left_double/right_single/drag/type/hotkey/scroll/wait/finished."""
    raise NotImplementedError("TODO: parser do action-space do UI-TARS")


def coord_to_selector(page, x, y) -> str | None:
    return page.evaluate(COORD_TO_SELECTOR_JS, [x, y])


def run(goal: str, max_steps: int = 40):
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    steps = []
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(TARGET_URL)
        # TODO: login se TARGET_USER/TARGET_PASS definidos
        for i in range(max_steps):
            shot = page.screenshot()
            action = ask_uitars(shot, goal)
            if action["type"] == "finished":
                break
            selector = coord_to_selector(page, *action.get("coord", (0, 0)))
            # TODO: executar via selector (page.locator(selector).click()/fill()/...)
            #       fallback p/ pixel se selector is None (marca passo como pixel-only)
            steps.append({"i": i, "action": action, "selector": selector})
        browser.close()
    (ARTIFACTS / "steps.json").write_text(json.dumps(steps, indent=2))


if __name__ == "__main__":
    run(goal="Explore a aplicação e percorra os principais fluxos de usuário.")
