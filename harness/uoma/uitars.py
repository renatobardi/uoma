"""
Cliente do UI-TARS (OpenAI-compatible) + parser do action-space.

⚠️ v1 PARA CALIBRAR: o jeito que o UI-TARS expressa coordenada varia por build.
No smoke test (1º run), confira no steps.json se os cliques caem no lugar certo.
Se errar sistematicamente, ajuste COORD_SPACE no .env:
  norm1000  -> coordenadas 0..1000 normalizadas (default)
  absolute  -> pixels da imagem enviada
"""
import os
import re
import base64

from openai import OpenAI

MODEL_BASE_URL = os.environ["MODEL_BASE_URL"]
MODEL_NAME = os.environ.get("MODEL_NAME", "ui-tars-1.5-7b")
COORD_SPACE = os.environ.get("COORD_SPACE", "norm1000")

client = OpenAI(base_url=MODEL_BASE_URL, api_key="none")

SYSTEM_PROMPT = """You are a GUI agent operating a web browser. You receive a task and a screenshot.
Reason briefly, then output exactly one action.

Output format:
Thought: <short reasoning>
Action: <one action below>

Action space:
click(start_box='(x,y)')
left_double(start_box='(x,y)')
right_single(start_box='(x,y)')
drag(start_box='(x,y)', end_box='(x,y)')
type(content='text to type')
hotkey(key='ctrl c')
scroll(start_box='(x,y)', direction='down')   # down|up|left|right
wait()
finished(content='summary of what was accomplished')

Rules:
- Exactly one Action per step.
- Coordinates are integers.
- Call finished() when the task/flow is complete or no further useful action exists.
"""

_ACTION_RE = re.compile(r"Action:\s*(\w+)\((.*)\)", re.S)
_BOX_RE = re.compile(r"\(?\s*(\d+)\s*,\s*(\d+)\s*\)?")


def ask(screenshot_png: bytes, task: str, history: list[str]) -> dict:
    """Envia screenshot + tarefa + histórico curto; devolve ação parseada."""
    b64 = base64.b64encode(screenshot_png).decode()
    user_text = task
    if history:
        user_text += "\n\nPrevious actions:\n" + "\n".join(history[-10:])
    resp = client.chat.completions.create(
        model=MODEL_NAME,
        temperature=0,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": [
                {"type": "text", "text": user_text},
                {"type": "image_url",
                 "image_url": {"url": f"data:image/png;base64,{b64}"}},
            ]},
        ],
    )
    return parse(resp.choices[0].message.content)


def parse(raw: str) -> dict:
    """Action: name(args) -> dict {type, start?, end?, content?, key?, direction?, raw}."""
    act = {"type": "wait", "raw": raw or ""}
    m = _ACTION_RE.search(raw or "")
    if not m:
        return act
    act["type"] = m.group(1)
    args = m.group(2)

    if "content=" in args:
        c = re.search(r"content=['\"](.*?)['\"]", args, re.S)
        act["content"] = c.group(1) if c else ""
    if "key=" in args:
        k = re.search(r"key=['\"](.*?)['\"]", args)
        act["key"] = k.group(1) if k else ""
    if "direction=" in args:
        d = re.search(r"direction=['\"](.*?)['\"]", args)
        act["direction"] = d.group(1) if d else "down"

    boxes = _BOX_RE.findall(args)
    if boxes:
        act["start"] = (int(boxes[0][0]), int(boxes[0][1]))
        if len(boxes) > 1:
            act["end"] = (int(boxes[1][0]), int(boxes[1][1]))
    return act


def to_pixels(coord, viewport_w, viewport_h):
    """Converte coordenada do modelo -> pixel real do viewport."""
    x, y = coord
    if COORD_SPACE == "norm1000":
        return (x * viewport_w / 1000.0, y * viewport_h / 1000.0)
    return (float(x), float(y))  # absolute
