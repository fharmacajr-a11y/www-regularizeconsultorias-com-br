"""Faixa de categorias da listagem de notícias com mouse e com toque, abaixo de 1024 px.

A faixa foi criada em 21/10/2026 (d05e546) para o toque: as categorias e, no fim, a ordenação numa linha que
rola na horizontal, sem barra, com o item da borda direita esmaecido. No computador, com a janela em meia tela
(por volta de 960 px) e mouse de roda, ela também rolava só para o lado, sem barra e sem setas. De 21 a
23/10/2026, com mouse, as categorias e a ordenação quebravam em linhas (2 em 960 px, 3 em 768 px): todas à vista,
mas pesado. Desde 23/10/2026, com mouse ((hover: hover) and (pointer: fine), o contexto padrão do Playwright),
as categorias ficam num carrossel de uma linha que rola na horizontal, com setas, e a ordenação fica fora dele;
com toque (has_touch e is_mobile: hover none e pointer coarse), a faixa continua rolando com o dedo, sem setas.

Com mouse, em 320, 390, 640, 768, 960 e 1023 px, o teste confere:
- as categorias numa linha só, dentro do carrossel, que rola na horizontal; a faixa não passa da largura do
  cartão e a página não rola;
- as setas: a da esquerda só com categorias escondidas à esquerda e a da direita só com categorias escondidas à
  direita (no início, no meio e no fim do carrossel), cada uma com 44 px, fora do Tab (tabindex="-1") e fora
  da árvore de acessibilidade (aria-hidden="true"); o esmaecido só do lado que tem categorias escondidas;
- o clique na seta da direita rola cerca de 80% da largura visível (entre 70% e 90%) e não tira o foco de
  onde ele estava;
- a ordenação fora do carrossel: à direita dele, na mesma linha, em 768, 960 e 1023 px (onde o carrossel ainda
  tem pelo menos 18rem); numa linha própria logo abaixo em 320, 390 e 640 px;
- pelo Tab, cada categoria aparece inteira no carrossel e na janela, sem seta por cima (com o foco do teclado as
  setas saem); depois da última categoria vêm as duas da ordenação;
- todos os botões da faixa com pelo menos 44 px de altura.
Com toque, em 390, 768 e 960 px, a faixa continua numa linha só (com a ordenação no fim), rola na horizontal, tem
o esmaecido e não mostra setas; os botões têm pelo menos 44 px. Com o CSS e o HTML de 8e02600 os casos de mouse
falham (as categorias quebram em linhas e não há carrossel nem setas); os de toque passam.

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


# (largura, altura, ordenação na mesma linha do carrossel).
MOUSE = ((320, 640, False), (390, 844, False), (640, 900, False), (768, 1024, True), (960, 900, True), (1023, 900, True))
TOUCH = ((390, 844), (768, 1024), (960, 900))
MIN_HEIGHT = 44

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, pointer, width, height = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
output = {"load_failures": [], "other_load_failures": [], "state": None}
OPTIONS = {"mouse": {}, "toque": {"has_touch": True, "is_mobile": True}}
FRAMES = "() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))"

SNAPSHOT = r'''() => {
  const strip = document.querySelector('.news-filters__strip');
  const carousel = document.querySelector('.news-filters__carousel');
  const scroller = carousel ? carousel.querySelector('.news-filters__categories') : document.querySelector('.news-filters__categories');
  const sort = document.querySelector('.news-filters__sort');
  const box = node => { const r = node.getBoundingClientRect(); return {left: r.left, right: r.right, top: r.top, bottom: r.bottom, width: r.width, height: r.height}; };
  const mask = node => { const s = getComputedStyle(node); const m = s.maskImage && s.maskImage !== 'none' ? s.maskImage : s.webkitMaskImage; return m && m !== 'none' ? m : ''; };
  const shown = node => node.getClientRects().length > 0 && getComputedStyle(node).display !== 'none';
  const arrows = carousel ? [...carousel.querySelectorAll('[data-news-scroll]')].map(node => ({
    side: Number(node.dataset.newsScroll) < 0 ? 'start' : 'end', shown: shown(node),
    tabIndex: node.tabIndex, ariaHidden: node.getAttribute('aria-hidden'), box: box(node)})) : [];
  const categories = [...scroller.querySelectorAll('[data-news-category]')].filter(shown);
  const controls = [...strip.querySelectorAll('[data-news-category], [data-news-sort]')].filter(shown);
  const buttons = [...strip.querySelectorAll('button')].filter(shown)
    .map(node => ({label: node.innerText.replace(/\s+/g, ' ').trim() || node.className, height: node.getBoundingClientRect().height}));
  const scrollerStyle = getComputedStyle(scroller), stripStyle = getComputedStyle(strip);
  return {
    mouse: matchMedia('(hover: hover) and (pointer: fine)').matches,
    touch: matchMedia('(hover: none) and (pointer: coarse)').matches,
    pageScroll: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    strip: {scroll: strip.scrollWidth - strip.clientWidth, overflowX: stripStyle.overflowX, mask: mask(strip),
            rows: new Set(controls.map(node => Math.round(node.getBoundingClientRect().top / 8))).size},
    scroller: {left: scroller.scrollLeft, max: scroller.scrollWidth - scroller.clientWidth, client: scroller.clientWidth,
               overflowX: scrollerStyle.overflowX, mask: mask(scroller)},
    categoryRows: new Set(categories.map(node => Math.round(node.getBoundingClientRect().top))).size,
    carousel: carousel ? box(carousel) : null, sort: box(sort), arrows, buttons,
  };
}'''

TAB = r'''() => {
  const el = document.activeElement, r = el.getBoundingClientRect();
  const carousel = document.querySelector('.news-filters__carousel');
  const scroller = carousel.querySelector('.news-filters__categories').getBoundingClientRect();
  const header = document.getElementById('navbar').getBoundingClientRect().bottom;
  const covered = [...carousel.querySelectorAll('[data-news-scroll]')].filter(a => getComputedStyle(a).display !== 'none')
    .some(a => { const q = a.getBoundingClientRect(); return r.left < q.right && r.right > q.left && r.top < q.bottom && r.bottom > q.top; });
  const inCarousel = carousel.contains(el);
  return {label: el.innerText.replace(/\s+/g, ' ').trim(), category: !!el.dataset.newsCategory, sort: !!el.dataset.newsSort,
          covered,
          whole: (!inCarousel || (r.left >= scroller.left - 0.5 && r.right <= scroller.right + 0.5))
                 && r.left >= -0.5 && r.right <= document.documentElement.clientWidth + 0.5 && r.top >= header - 0.5 && r.bottom <= innerHeight + 0.5};
}'''

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR", **OPTIONS[pointer])
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        page.goto(base + "/noticias/", wait_until="load")
        page.evaluate("document.fonts.ready")
        page.evaluate("() => document.querySelector('.news-filters').scrollIntoView({block: 'center', behavior: 'instant'})")
        page.evaluate(FRAMES)
        state = {"start": page.evaluate(SNAPSHOT)}
        if pointer == "mouse" and state["start"]["carousel"] and any(a["shown"] for a in state["start"]["arrows"]):
            page.focus("#news-search")
            before = page.evaluate("() => document.querySelector('.news-filters__carousel .news-filters__categories').scrollLeft")
            page.locator(".news-filters__arrow--next").click()
            # Espera a rolagem suave começar e parar (três quadros seguidos na mesma posição).
            page.evaluate(
                "before => new Promise(done => { const s = document.querySelector('.news-filters__carousel .news-filters__categories');"
                " let last = s.scrollLeft, same = 0, frames = 0;"
                " const tick = () => { frames += 1; const v = s.scrollLeft;"
                "   if (v !== before && v === last) same += 1; else same = 0; last = v;"
                "   if (same >= 3 || frames > 300) done(); else requestAnimationFrame(tick); };"
                " requestAnimationFrame(tick); })", before)
            state["click"] = {"before": before,
                              "after": page.evaluate("() => document.querySelector('.news-filters__carousel .news-filters__categories').scrollLeft"),
                              "focused": page.evaluate("() => document.activeElement.id")}
            state["middle"] = page.evaluate(SNAPSHOT)
            page.evaluate("() => { const s = document.querySelector('.news-filters__carousel .news-filters__categories'); s.scrollLeft = s.scrollWidth; }")
            page.evaluate(FRAMES)
            state["end"] = page.evaluate(SNAPSHOT)
            page.evaluate("() => { document.querySelector('.news-filters__carousel .news-filters__categories').scrollLeft = 0; }")
            page.focus("#news-search")
            tabs = []
            for _ in range(16):
                page.keyboard.press("Tab")
                page.evaluate(FRAMES)
                stop = page.evaluate(TAB)
                tabs.append(stop)
                if not (stop["category"] or stop["sort"]):
                    break
            state["tabs"] = tabs
        output["state"] = state
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


def _assert_min_height(snapshot, label):
    short = [(b["label"], round(b["height"], 1)) for b in snapshot["buttons"] if b["height"] < MIN_HEIGHT - 0.5]
    assert not short, f"{label}: botões com menos de {MIN_HEIGHT} px de altura: {short}"


def _arrows(snapshot):
    return {a["side"]: a["shown"] for a in snapshot["arrows"]}


def _fade(snapshot):
    """Lados esmaecidos do carrossel: o degradê da máscara começa e/ou termina em transparente."""
    mask = snapshot["scroller"]["mask"].replace(" ", "")
    if not mask:
        return set()
    # Valor calculado: linear-gradient(to right, <paradas>), com o transparente como rgba(0, 0, 0, 0).
    body = mask[mask.index("(") + 1:-1]
    stops = body.split(",", 1)[1]
    clear = ("rgba(0,0,0,0)", "transparent")
    return {side for side, edge in (("start", stops.startswith(clear)), ("end", stops.endswith(clear))) if edge}


@pytest.mark.parametrize("width,height,same_line", MOUSE, ids=[f"{w}x{h}" for w, h, _ in MOUSE])
def test_mouse_categories_scroll_in_one_row_with_arrows_and_sort_outside(base_url, width, height, same_line):
    state = _state(base_url, "mouse", width, height)
    label = f"mouse {width}x{height}"
    start = state["start"]
    assert start["mouse"] and not start["touch"], f"{label}: o contexto padrão não casou com mouse"
    assert start["carousel"], f"{label}: as categorias não estão num carrossel (.news-filters__carousel)"
    assert start["categoryRows"] == 1, f"{label}: as categorias quebraram em {start['categoryRows']} linhas"
    assert start["scroller"]["overflowX"] == "auto" and start["scroller"]["max"] > 0, (
        f"{label}: o carrossel não rola na horizontal ({start['scroller']})")
    assert start["strip"]["scroll"] <= 0 and not start["strip"]["mask"], (
        f"{label}: a faixa passa da largura do cartão ou ainda esmaece inteira ({start['strip']})")
    assert start["pageScroll"] <= 0, f"{label}: a página rola {start['pageScroll']} px na horizontal"

    # Setas e esmaecido só do lado com categorias escondidas.
    middle, end = state["middle"], state["end"]
    assert _arrows(start) == {"start": False, "end": True}, f"{label}: setas no início {start['arrows']}"
    assert _fade(start) == {"end"}, f"{label}: esmaecido no início {start['scroller']['mask']}"
    assert 0 < middle["scroller"]["left"] < middle["scroller"]["max"], f"{label}: o clique levou ao fim {middle['scroller']}"
    assert _arrows(middle) == {"start": True, "end": True}, f"{label}: setas no meio {middle['arrows']}"
    assert _fade(middle) == {"start", "end"}, f"{label}: esmaecido no meio {middle['scroller']['mask']}"
    assert end["scroller"]["left"] >= end["scroller"]["max"] - 1, f"{label}: o carrossel não chegou ao fim"
    assert _arrows(end) == {"start": True, "end": False}, f"{label}: setas no fim {end['arrows']}"
    assert _fade(end) == {"start"}, f"{label}: esmaecido no fim {end['scroller']['mask']}"
    for arrow in middle["arrows"]:
        assert arrow["tabIndex"] == -1 and arrow["ariaHidden"] == "true", f"{label}: seta no Tab ou visível ao leitor: {arrow}"
        assert min(arrow["box"]["width"], arrow["box"]["height"]) >= MIN_HEIGHT - 0.5, f"{label}: seta menor que 44 px {arrow}"

    # O clique rola cerca de 80% da largura visível e o foco fica onde estava.
    moved = state["click"]["after"] - state["click"]["before"]
    client = start["scroller"]["client"]
    assert 0.7 * client <= moved <= 0.9 * client, f"{label}: a seta rolou {moved} px de {client} px visíveis"
    assert state["click"]["focused"] == "news-search", f"{label}: a seta tirou o foco da pesquisa"

    # Ordenação fora do carrossel: à direita na mesma linha ou logo abaixo.
    carousel, sort = start["carousel"], start["sort"]
    if same_line:
        assert abs(sort["top"] - carousel["top"]) < 16 and sort["left"] >= carousel["right"] - 0.5, (
            f"{label}: a ordenação devia ficar à direita do carrossel {carousel} {sort}")
    else:
        assert sort["top"] >= carousel["bottom"] - 0.5, f"{label}: a ordenação devia ficar abaixo do carrossel {carousel} {sort}"

    # Pelo Tab: cada categoria inteira, sem seta por cima; depois, as duas da ordenação.
    tabs = state["tabs"]
    categories = [stop for stop in tabs if stop["category"]]
    assert len(categories) == 11, f"{label}: o Tab passou por {len(categories)} categorias: {[s['label'] for s in tabs]}"
    bad = [(s["label"], s["whole"], s["covered"]) for s in categories if not s["whole"] or s["covered"]]
    assert not bad, f"{label}: categorias focadas cortadas ou sob uma seta: {bad}"
    order = ["categoria" if s["category"] else "ordenação" if s["sort"] else "fora" for s in tabs]
    assert order[:13] == ["categoria"] * 11 + ["ordenação"] * 2, f"{label}: ordem do Tab {order}"
    for snapshot in (start, middle, end):
        _assert_min_height(snapshot, label)


@pytest.mark.parametrize("viewport", TOUCH, ids=[f"{w}x{h}" for w, h in TOUCH])
def test_touch_strip_keeps_scrolling_sideways_in_one_row(base_url, viewport):
    width, height = viewport
    state = _state(base_url, "toque", width, height)["start"]
    label = f"toque {width}x{height}"
    assert state["touch"] and not state["mouse"], f"{label}: o contexto com has_touch não casou com toque"
    assert state["strip"]["rows"] == 1, f"{label}: a faixa quebrou em {state['strip']['rows']} linhas"
    assert state["strip"]["scroll"] > 0 and state["strip"]["overflowX"] == "auto", (
        f"{label}: a faixa não rola na horizontal ({state['strip']})")
    assert state["strip"]["mask"], f"{label}: a faixa perdeu o esmaecido na borda"
    assert not any(a["shown"] for a in state["arrows"]), f"{label}: setas aparecem com toque {state['arrows']}"
    assert state["pageScroll"] <= 0, f"{label}: a página rola {state['pageScroll']} px na horizontal"
    _assert_min_height(state, label)
