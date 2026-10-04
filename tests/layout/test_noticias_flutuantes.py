"""Controles flutuantes sobre a coluna lateral das Notícias.

Abaixo de 1024 px a coluna lateral (pesquisa, categorias, ordenação e
atendimento) vem depois da lista, com a largura toda do miolo, e a coluna fixa
de voltar ao topo e WhatsApp passava sobre a borda direita dela: em 960 px o
WhatsApp cobria a contagem "54" de ANVISA. A listagem recolhe esses botões
enquanto eles estão na região da coluna e os devolve ao sair dela.

Em cada largura o teste reproduz o caso de 960 px (centro de ANVISA na altura
do centro do WhatsApp), rola com a roda do mouse para baixo e para cima por
toda a coluna, com passo menor que um botão, percorre os controles dela por
Tab e por Shift+Tab e aplica um filtro pelo mouse e outro pelo teclado (a lista
muda de altura e a coluna se move sem rolagem). Em cada parada, com a rolagem e
as transições terminadas,
nenhum botão flutuante visível pode ficar sobre o texto da coluna (nomes e
contagens das categorias inclusive), sobre os campos ou sobre o anel de foco
do controle focado. Também confere que os botões estão visíveis longe da
coluna, que o estado troca no máximo uma vez na entrada e outra na saída, que
um botão recolhido não recebe foco, que o foco de mouse deixado num botão não
fica preso num botão oculto e que um botão com foco de teclado não some. Os
contatos da página ("Falar com a Regularize" e o WhatsApp de "Orientação
técnica") continuam visíveis em todas as paradas.
"""
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR


# (largura, altura): celular, limites de 640, 768 e 1024 px, meia tela de
# 1920 px e desktop. Até 1023 px a coluna fica empilhada depois da lista.
VIEWPORTS = (
    (320, 640), (360, 780), (390, 844), (414, 896),
    (639, 900), (640, 900), (767, 900), (768, 1024),
    (940, 900), (960, 900), (1023, 900),
    (1024, 768), (1440, 900),
)
STACKED_LIMIT = 1023
# Passo da roda menor que o WhatsApp (44 px no celular) + uma linha de texto:
# toda linha da coluna passa por baixo dele em alguma parada.
WHEEL_STEP = 40
# Longe da coluna (ou ao lado dela), os botões têm de estar visíveis.
FAR = 40

HELPERS = r"""
window.__flutuantes = (() => {
  const group = () => document.querySelector('.floating-buttons');
  const sidebar = () => document.querySelector('aside .news-sidebar');
  const opacity = node => {
    let value = 1;
    for (; node && node.nodeType === 1; node = node.parentElement) value *= parseFloat(getComputedStyle(node).opacity);
    return value;
  };
  const shown = node => getComputedStyle(node).visibility === 'visible' && opacity(node) > 0.01;
  const name = node => node.classList.contains('floating-btn--whatsapp') ? 'WhatsApp' : 'voltar ao topo';
  const hits = (a, b) => a.left < b.right - 0.5 && a.right > b.left + 0.5 && a.top < b.bottom - 0.5 && a.bottom > b.top + 0.5;
  const box = r => ({left: r.left, right: r.right, top: r.top, bottom: r.bottom});
  const describe = node => (node.textContent.trim() || node.getAttribute('aria-label') || node.id || node.tagName)
    .replace(/\s+/g, ' ').slice(0, 40);
  // Alcance do indicador de foco: contorno (largura + afastamento) e sombras externas.
  const ring = node => {
    const style = getComputedStyle(node);
    let reach = 0;
    if (style.outlineStyle !== 'none') {
      reach = Math.max(reach, parseFloat(style.outlineWidth) + parseFloat(style.outlineOffset));
    }
    const shadows = style.boxShadow === 'none' ? [] : style.boxShadow.split(/,(?![^(]*\))/);
    for (const shadow of shadows) {
      if (shadow.includes('inset')) continue;
      const [x = 0, y = 0, blur = 0, spread = 0] = (shadow.replace(/rgba?\([^)]*\)/g, '').match(/-?[\d.]+px/g) || [])
        .map(parseFloat);
      reach = Math.max(reach, Math.max(Math.abs(x), Math.abs(y)) + blur + spread);
    }
    return Math.max(0, reach);
  };
  const regions = () => {
    const column = sidebar();
    const found = [];
    const walker = document.createTreeWalker(column, NodeFilter.SHOW_TEXT);
    for (let text = walker.nextNode(); text; text = walker.nextNode()) {
      const value = text.data.trim();
      if (!value) continue;
      const category = text.parentElement.closest('[data-news-category]');
      const kind = !category ? 'texto' : text.parentElement === category.lastElementChild ? 'contagem' : 'categoria';
      const range = document.createRange();
      range.selectNodeContents(text);
      for (const r of range.getClientRects()) {
        if (r.width && r.height) found.push({kind, name: value.slice(0, 40), ...box(r)});
      }
    }
    for (const field of column.querySelectorAll('input, select, textarea')) {
      found.push({kind: 'campo', name: field.id, ...box(field.getBoundingClientRect())});
    }
    const active = document.activeElement;
    if (active && column.contains(active)) {
      const r = active.getBoundingClientRect(), reach = ring(active);
      found.push({kind: 'foco', name: describe(active),
                  left: r.left - reach, right: r.right + reach, top: r.top - reach, bottom: r.bottom + reach});
    }
    return found;
  };
  return {
    async settle() {
      // Rolagem parada por 120 ms, transições terminadas e um quadro pintado.
      let last = scrollY, since = performance.now();
      const started = since;
      while (performance.now() - since < 120 && performance.now() - started < 4000) {
        await new Promise(done => setTimeout(done, 30));
        if (scrollY !== last) { last = scrollY; since = performance.now(); }
      }
      const finite = document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().endTime !== Infinity);
      await Promise.all(finite.map(a => a.finished.catch(() => null)));
      await new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
    },
    geometry() {
      const column = sidebar().getBoundingClientRect(), g = group().getBoundingClientRect();
      return {columnTop: column.top + scrollY, columnBottom: column.bottom + scrollY,
              groupTop: g.top, groupBottom: g.bottom, maxScroll: document.documentElement.scrollHeight - innerHeight};
    },
    alignAnvisa() {
      // O caso das capturas: centro de ANVISA na altura do centro do WhatsApp.
      const middle = r => r.top + r.height / 2;
      const anvisa = document.querySelector('[data-news-category=anvisa]');
      const whatsapp = document.querySelector('.floating-btn--whatsapp');
      window.scrollBy(0, middle(anvisa.getBoundingClientRect()) - middle(whatsapp.getBoundingClientRect()));
    },
    state() {
      const g = group(), column = sidebar().getBoundingClientRect(), r = g.getBoundingClientRect();
      const buttons = [...g.querySelectorAll('.floating-btn')];
      const overlaps = [];
      for (const button of buttons.filter(shown)) {
        const b = button.getBoundingClientRect();
        for (const region of regions()) {
          if (hits(region, b)) overlaps.push(`${region.kind} '${region.name}' sob o botão ${name(button)}`);
        }
      }
      const active = document.activeElement;
      const contacts = [document.querySelector('aside .news-sidebar a[href="/contato/"]'),
                        [...document.querySelectorAll('main a[href^="/whatsapp/"]')].find(a => a.closest('.border-l-4'))];
      const controls = [...sidebar().querySelectorAll('a[href], button, input')];
      return {
        scrollY, overlaps: [...new Set(overlaps)],
        collapsed: !shown(g.querySelector('.floating-btn--whatsapp')),
        whatsappOpacity: opacity(g.querySelector('.floating-btn--whatsapp')),
        // Distância vertical entre as duas colunas (negativa quando se cruzam).
        gap: Math.max(column.top - r.bottom, r.top - column.bottom),
        beside: column.right <= r.left || column.left >= r.right,
        activeInGroup: g.contains(active), activeShown: !g.contains(active) || shown(active),
        activeIndex: controls.indexOf(active), activeLabel: active && active !== document.body ? describe(active) : 'body',
        contactsShown: contacts.every(node => node && shown(node)),
      };
    },
    // Um botão recolhido não pode receber foco, nem pelo script.
    focusHiddenButtons() {
      const before = document.activeElement, taken = [];
      for (const button of group().querySelectorAll('.floating-btn')) {
        if (shown(button)) continue;
        button.focus();
        if (document.activeElement === button) taken.push(name(button));
      }
      // Desfaz o foco tomado, para não contaminar as etapas seguintes.
      if (document.activeElement !== before) {
        document.activeElement.blur();
        if (before && before !== document.body) before.focus();
      }
      return taken;
    },
  };
})();
"""

PROBE = r'''
import json
import os
import sys
from playwright.sync_api import sync_playwright

base, width, height, stacked_limit, wheel_step, far = sys.argv[1:]
helpers = os.environ["NOTICIAS_FLUTUANTES_JS"]
width, height, stacked_limit, wheel_step, far = map(int, (width, height, stacked_limit, wheel_step, far))
stacked = width <= stacked_limit
failures, stats = [], {"stops": 0, "collapsedStops": 0}


def settle():
    page.evaluate("window.__flutuantes.settle()")


def check(where, expect_far_visible=True):
    state = page.evaluate("window.__flutuantes.state()")
    stats["stops"] += 1
    stats["collapsedStops"] += state["collapsed"]
    label = f"@{width}x{height} {where} (y={state['scrollY']:.0f})"
    failures.extend(f"{label}: {overlap}" for overlap in state["overlaps"][:3])
    if not state["activeShown"]:
        failures.append(f"{label}: foco em botão flutuante oculto")
    if expect_far_visible and (state["beside"] or state["gap"] > far) and (state["collapsed"] or state["whatsappOpacity"] < 0.99):
        failures.append(f"{label}: botões recolhidos longe da coluna (distância {state['gap']:.0f} px)")
    if not state["contactsShown"]:
        failures.append(f"{label}: contato da página oculto")
    return state


def toggles(states):
    return sum(a != b for a, b in zip(states, states[1:]))


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = browser.new_context(viewport={"width": width, "height": height})
    context.add_init_script(helpers)
    page = context.new_page()
    page.route("**/*", lambda route: route.continue_() if route.request.url.startswith(base) else route.abort())
    page.goto(base + "/noticias/", wait_until="load")
    page.add_style_tag(content="html{scroll-behavior:auto!important}")
    settle()

    # 1. O caso das capturas.
    if stacked:
        page.evaluate("window.__flutuantes.alignAnvisa()")
        settle()
        state = check("ANVISA na altura do WhatsApp")
        taken = page.evaluate("window.__flutuantes.focusHiddenButtons()")
        if taken:
            failures.append(f"@{width} botão recolhido recebeu foco: {taken}")

    # 2. Roda do mouse para baixo e para cima por toda a coluna.
    geometry = page.evaluate("window.__flutuantes.geometry()")
    start = max(0, geometry["columnTop"] - geometry["groupBottom"] - 200)
    end = min(geometry["maxScroll"], geometry["columnBottom"] - geometry["groupTop"] + 200)
    page.evaluate("y => window.scrollTo(0, y)", start)
    settle()
    page.mouse.move(width / 2, height / 2)
    for direction, label in ((1, "roda ↓"), (-1, "roda ↑")):
        states = [check(f"{label} início")["collapsed"]]
        previous = page.evaluate("scrollY")
        for _ in range(400):
            page.mouse.wheel(0, direction * wheel_step)
            settle()
            state = check(label)
            states.append(state["collapsed"])
            if state["scrollY"] - previous > wheel_step * 1.5 or previous - state["scrollY"] > wheel_step * 1.5:
                failures.append(f"@{width} {label}: passo de {abs(state['scrollY'] - previous):.0f} px, maior que o previsto")
            if state["scrollY"] == previous or (direction > 0 and state["scrollY"] >= end) or (direction < 0 and state["scrollY"] <= start):
                break
            previous = state["scrollY"]
        stats[label] = toggles(states)
        if toggles(states) > 2:
            failures.append(f"@{width} {label}: o estado dos botões trocou {toggles(states)} vezes ({states})")
        if stacked and not any(states):
            failures.append(f"@{width} {label}: os botões não recolheram ao passar pela coluna")
        if not stacked and any(states):
            failures.append(f"@{width} {label}: os botões recolheram com a coluna ao lado")

    # 3. Teclado: Tab do topo e Shift+Tab a partir do primeiro card.
    controls = page.evaluate("document.querySelectorAll('aside .news-sidebar :is(a[href], button, input)').length")
    for key, start_at in (("Tab", "main h1"), ("Shift+Tab", "#news-article-list [data-news-card] p")):
        page.evaluate("window.scrollTo(0, 0)")
        settle()
        page.locator(start_at).first.click()
        reached, entered = set(), False
        for _ in range(controls + 12):
            page.keyboard.press(key)
            settle()
            state = check(f"{key} em '{page.evaluate('document.activeElement.textContent.trim().slice(0, 30)')}'")
            if state["activeIndex"] >= 0:
                entered = True
                reached.add(state["activeIndex"])
            elif entered:
                break
        if len(reached) < controls:
            failures.append(f"@{width} {key}: {len(reached)} de {controls} controles da coluna alcançados")

    if stacked:
        # 4. Filtros em uso: a lista muda de altura e a coluna se move sem rolagem.
        page.evaluate("window.__flutuantes.alignAnvisa()")
        settle()
        page.locator("[data-news-category=sngpc]").click()
        settle()
        check("depois de filtrar SNGPC pelo mouse")
        page.locator("[data-news-category=todos]").focus()
        page.keyboard.press("Enter")
        settle()
        check("depois de voltar a Todos pelo teclado")

        # 5. Foco de mouse deixado no "voltar ao topo" não fica preso num botão oculto.
        page.evaluate("window.scrollTo(0, 600)")
        settle()
        page.locator(".floating-btn--top").click()
        settle()
        page.evaluate("window.__flutuantes.alignAnvisa()")
        settle()
        check("ANVISA depois de clicar em voltar ao topo")

        # 6. Botão com foco de teclado não some; ao sair do foco, recolhe.
        # No rodapé, longe da coluna, os botões voltam; depois o Tab chega a eles.
        page.locator("footer a").last.focus()
        settle()
        check("último link do rodapé")
        page.keyboard.press("Tab")
        settle()
        page.evaluate("window.__flutuantes.alignAnvisa()")
        settle()
        state = page.evaluate("window.__flutuantes.state()")
        if not state["activeInGroup"] or state["collapsed"]:
            failures.append(f"@{width}: botão flutuante com foco de teclado sumiu ({state['activeLabel']})")
        page.locator("aside .news-sidebar h2").nth(1).click()
        settle()
        state = check("depois de tirar o foco do botão flutuante")
        if not state["collapsed"]:
            failures.append(f"@{width}: sem foco, os botões não recolheram sobre a coluna")

    context.close()
    browser.close()
print(json.dumps({"failures": failures, "stats": stats}))
'''


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def probes():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def run(viewport):
        width, height = viewport
        return subprocess.run(
            [sys.executable, "-c", PROBE, base, str(width), str(height), str(STACKED_LIMIT),
             str(WHEEL_STEP), str(FAR)],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=420,
            env=dict(os.environ, NOTICIAS_FLUTUANTES_JS=HELPERS, PYTHONIOENCODING="utf-8"),
        )

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            completed = dict(zip(VIEWPORTS, pool.map(run, VIEWPORTS)))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    return completed


@pytest.mark.parametrize("width,height", VIEWPORTS, ids=[f"{w}x{h}" for w, h in VIEWPORTS])
def test_floating_buttons_never_hide_the_news_sidebar(probes, width, height):
    completed = probes[(width, height)]
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    failures = result["failures"]
    assert not failures, f"{len(failures)} falha(s), {result['stats']}:\n" + "\n".join(failures[:25])
