"""Faixa de categorias da listagem de notícias com mouse e com toque, abaixo de 1024 px.

A faixa foi criada em 21/10/2026 (d05e546) para o toque: as categorias e, no fim, a ordenação numa linha que
rola na horizontal, sem barra, com o item da borda direita esmaecido. No computador, com a janela em meia tela
(por volta de 960 px) e mouse de roda, ela também rolava só para o lado, sem barra e sem setas, e as categorias
escondidas não se alcançavam. Desde então, com mouse ((hover: hover) and (pointer: fine), o contexto padrão do
Playwright), as categorias e a ordenação quebram em linhas, todas à vista; com toque (has_touch e is_mobile:
hover none e pointer coarse), a faixa continua rolando com o dedo.

Com mouse, em 320, 390, 640, 768, 960 e 1023 px, o teste confere que a faixa não rola na horizontal (nem a
página), não tem o esmaecido e que cada botão fica inteiro na faixa e, levado ao meio da janela pela rolagem
vertical, inteiro na janela, abaixo do cabeçalho e com o centro livre (nenhum botão flutuante por cima). Com o
cartão da faixa logo abaixo do cabeçalho, todos aparecem ao mesmo tempo, inteiros e livres, em todas essas
janelas menos 320x640, onde as nove linhas passam 1 px do fim da janela. Com toque, em 390, 768 e 960 px, a
faixa continua numa linha só, rola na horizontal e tem o esmaecido. Com mouse e com toque, todos os botões da
faixa (categorias e ordenação) têm pelo menos 44 px de altura; até 21/10/2026 eram 42 px nas categorias e 36 px
na ordenação. Com o CSS de d05e546 todos os casos falham: os de mouse pela rolagem horizontal, os de toque pela
altura.

Roda em subprocesso com o ServidorDeTeste (fila de 128; ver tests/support.py) e registra os recursos locais que
não carregaram, como test_noticias_ordem_tab.py.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler

import pytest

from support import SITE_DIR, ServidorDeTeste, subprocess_env


# (largura, altura, todos os botões na janela ao mesmo tempo).
MOUSE = ((320, 640, False), (390, 844, True), (640, 900, True), (768, 1024, True), (960, 900, True), (1023, 900, True))
TOUCH = ((390, 844), (768, 1024), (960, 900))
MIN_HEIGHT = 44

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, pointer, width, height = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
output = {"load_failures": [], "other_load_failures": [], "state": None}
OPTIONS = {"mouse": {}, "toque": {"has_touch": True, "is_mobile": True}}

STATE = r'''async () => {
  const filters = document.querySelector('.news-filters');
  filters.scrollIntoView({block: 'start', behavior: 'instant'});
  await new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
  const strip = document.querySelector('.news-filters__strip');
  const s = strip.getBoundingClientRect(), style = getComputedStyle(strip);
  const header = document.getElementById('navbar').getBoundingClientRect().bottom;
  const width = document.documentElement.clientWidth;
  const buttons = [...strip.querySelectorAll('button')].map(node => {
    const r = node.getBoundingClientRect();
    const inStrip = r.left >= s.left - 0.5 && r.right <= s.right + 0.5;
    const inWindow = r.left >= -0.5 && r.right <= width + 0.5 && r.top >= header - 0.5 && r.bottom <= innerHeight + 0.5;
    const hit = inWindow && document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    return {label: node.innerText.replace(/\s+/g, ' ').trim(), top: r.top, bottom: r.bottom, height: r.height,
            inStrip, inWindow, free: !!hit && (hit === node || node.contains(hit)),
            where: {top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right)}};
  });
  // Linhas: um botão abre linha nova quando começa abaixo do fim da linha atual.
  const rows = [];
  for (const b of buttons) {
    const last = rows[rows.length - 1];
    if (!last || b.top >= last.bottom - 1) rows.push({bottom: b.bottom, labels: [b.label]});
    else { last.bottom = Math.max(last.bottom, b.bottom); last.labels.push(b.label); }
  }
  // Cada botão sozinho, levado ao meio da janela pela rolagem vertical.
  const nodes = [...strip.querySelectorAll('button')];
  for (const [index, node] of nodes.entries()) {
    node.scrollIntoView({block: 'center', inline: 'nearest', behavior: 'instant'});
    await new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
    const r = node.getBoundingClientRect(), top = document.getElementById('navbar').getBoundingClientRect().bottom;
    const inWindow = r.left >= -0.5 && r.right <= width + 0.5 && r.top >= top - 0.5 && r.bottom <= innerHeight + 0.5;
    const hit = inWindow && document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
    buttons[index].alone = inWindow && !!hit && (hit === node || node.contains(hit));
  }
  const mask = style.maskImage && style.maskImage !== 'none' ? style.maskImage : style.webkitMaskImage;
  return {
    mouse: matchMedia('(hover: hover) and (pointer: fine)').matches,
    touch: matchMedia('(hover: none) and (pointer: coarse)').matches,
    stripScroll: strip.scrollWidth - strip.clientWidth, overflowX: style.overflowX, faded: !!mask && mask !== 'none',
    pageScroll: document.documentElement.scrollWidth - width,
    header: Math.round(header), innerHeight, stripTop: Math.round(s.top), stripBottom: Math.round(s.bottom),
    rows: rows.map(row => row.labels), buttons,
  };
}'''

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR", **OPTIONS[pointer])
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        page.goto(base + "/noticias/", wait_until="load")
        page.evaluate("document.fonts.ready")
        output["state"] = page.evaluate(STATE)
        closing()
        context.close()
        browser.close()
finally:
    print(json.dumps(output, ensure_ascii=False))
"""


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def base_url():
    server = ServidorDeTeste(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _state(base_url, pointer, width, height):
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, base_url, pointer, str(width), str(height)],
        capture_output=True, text=True, encoding="utf-8", timeout=180, env=subprocess_env(),
    )
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    if not isinstance(output, dict) or completed.returncode or not output.get("state"):
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    assert not output["load_failures"], f"recursos locais que não carregaram em {width}x{height}: {output['load_failures']}"
    return output["state"]


@pytest.mark.parametrize("width,height,all_at_once", MOUSE, ids=[f"{w}x{h}" for w, h, _ in MOUSE])
def test_mouse_strip_wraps_with_every_button_whole_in_the_window(base_url, width, height, all_at_once):
    state = _state(base_url, "mouse", width, height)
    label = f"mouse {width}x{height}"
    assert state["mouse"] and not state["touch"], f"{label}: o contexto padrão não casou com mouse {state}"
    assert state["stripScroll"] <= 0 and state["overflowX"] == "visible", (
        f"{label}: a faixa rola na horizontal ({state['stripScroll']} px escondidos, overflow-x {state['overflowX']})")
    assert state["pageScroll"] <= 0, f"{label}: a página rola {state['pageScroll']} px na horizontal"
    assert not state["faded"], f"{label}: a faixa ainda tem o esmaecido na borda"
    alone = [(b["label"], b["where"]) for b in state["buttons"] if not (b["inStrip"] and b["alone"])]
    assert not alone, f"{label}: botões que não aparecem inteiros e livres na faixa e na janela: {alone}"
    if all_at_once:
        together = [(b["label"], b["where"]) for b in state["buttons"] if not (b["inWindow"] and b["free"])]
        assert not together, (
            f"{label}: com a faixa logo abaixo do cabeçalho, botões fora da janela ou cobertos (cabeçalho até "
            f"{state['header']}, janela {state['innerHeight']}, linhas {state['rows']}): {together}")
    _assert_min_height(state, label)


def _assert_min_height(state, label):
    short = [(b["label"], round(b["height"], 1)) for b in state["buttons"] if b["height"] < MIN_HEIGHT - 0.5]
    assert not short, f"{label}: botões com menos de {MIN_HEIGHT} px de altura: {short}"


@pytest.mark.parametrize("viewport", TOUCH, ids=[f"{w}x{h}" for w, h in TOUCH])
def test_touch_strip_keeps_scrolling_sideways_in_one_row(base_url, viewport):
    width, height = viewport
    state = _state(base_url, "toque", width, height)
    label = f"toque {width}x{height}"
    assert state["touch"] and not state["mouse"], f"{label}: o contexto com has_touch não casou com toque {state}"
    assert len(state["rows"]) == 1, f"{label}: a faixa quebrou em {len(state['rows'])} linhas: {state['rows']}"
    assert state["stripScroll"] > 0 and state["overflowX"] == "auto", (
        f"{label}: a faixa não rola na horizontal ({state['stripScroll']} px, overflow-x {state['overflowX']})")
    assert state["faded"], f"{label}: a faixa perdeu o esmaecido na borda"
    assert state["pageScroll"] <= 0, f"{label}: a página rola {state['pageScroll']} px na horizontal"
    _assert_min_height(state, label)
