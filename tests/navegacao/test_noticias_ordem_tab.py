"""Ordem do Tab igual à ordem da tela na listagem de notícias (e nas páginas vizinhas).

Até 21/10/2026, abaixo de 1024 px, a coluna de filtros da listagem vinha antes da lista no HTML e depois
dela na tela (classes order-2 / order-1). Do topo, o Tab descia até a pesquisa, abaixo dos cinco cards,
percorria as categorias, a ordenação e "Falar com a Regularize" e voltava para cima até o 1º card: em
390x844, 3.271 px para baixo e 3.745 px de volta. O diagnóstico está em
diagnostico-ordem-tab-noticias-2026-10-21. Desde então a coluna vem antes da lista também na tela.

O teste abre cada página no topo, sem foco, e aperta Tab até o foco sair da página. Em cada parada fora
dos elementos fixos ou sticky (faixa do topo, cabeçalho e botões flutuantes, que ficam no mesmo lugar da
tela), compara a parada com a anterior:
- na mesma linha (sobreposição vertical de pelo menos metade da menor altura), a seguinte não pode
  começar à esquerda da anterior. Dentro de um contêiner que rola na horizontal (a faixa de categorias,
  a vitrine da Home) vale a posição no conteúdo dele, sem a rolagem; entre contêineres, a posição na
  janela no momento do foco;
- acima da anterior, só numa coluna à direita (a lista ao lado da coluna de filtros a partir de 1024 px,
  a coluna de contato do rodapé): a seguinte começa depois da borda direita da anterior.
Toda parada tem de aparecer inteira: dentro da janela, abaixo do cabeçalho e dentro do recorte dos
contêineres com overflow. Na listagem, todos os controles exibidos da coluna de filtros recebem o foco.
Com o HTML de c74d97b, a listagem falha em 390 e 960 px e passa em 1440 px.

Roda em subprocesso com o ServidorDeTeste (fila de 128; ver tests/support.py) e registra os recursos
locais que não carregaram, como test_noticias_tab_rapido.py.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler

import pytest

from support import SITE_DIR, ServidorDeTeste, subprocess_env


VIEWPORTS = ((390, 844), (960, 900), (1440, 900))
PAGES = ("/noticias/", "/", "/manuais-e-pops/", "/comunicado/")

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, path, width, height = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
output = {"failures": [], "load_failures": [], "other_load_failures": [], "stops": []}

STOP = '''() => {
  const el = document.activeElement;
  if (!el || el === document.body || el === document.documentElement) return null;
  let fixed = false;
  for (let n = el; n && n !== document.documentElement; n = n.parentElement) {
    const p = getComputedStyle(n).position;
    if (p === 'fixed' || p === 'sticky') { fixed = true; break; }
  }
  const r = el.getBoundingClientRect();
  const width = document.documentElement.clientWidth;
  let clip = {l: 0, t: 0, r: width, b: innerHeight}, scroller = null;
  for (let n = el.parentElement; n && n !== document.body; n = n.parentElement) {
    const s = getComputedStyle(n);
    if (s.overflowX === 'visible' && s.overflowY === 'visible') continue;
    const q = n.getBoundingClientRect();
    clip = {l: Math.max(clip.l, q.left), t: Math.max(clip.t, q.top), r: Math.min(clip.r, q.right), b: Math.min(clip.b, q.bottom)};
    if (!scroller && n.scrollWidth > n.clientWidth + 1) scroller = n;
  }
  window.__rolaveis = window.__rolaveis || [];
  if (scroller && !window.__rolaveis.includes(scroller)) window.__rolaveis.push(scroller);
  const navbar = document.getElementById('navbar');
  const header = navbar ? navbar.getBoundingClientRect().bottom : 0;
  const inside = r.left >= clip.l - 0.5 && r.right <= clip.r + 0.5 && r.top >= clip.t - 0.5 && r.bottom <= clip.b + 0.5;
  return {
    label: (el.getAttribute('aria-label') || el.innerText || el.value || el.placeholder || el.tagName)
      .replace(/\s+/g, ' ').trim().slice(0, 50),
    fixed, column: !!el.closest('main aside'),
    top: r.top + scrollY, bottom: r.bottom + scrollY, left: r.left, right: r.right,
    // Posição no conteúdo do contêiner que rola na horizontal, sem a rolagem dele.
    contentLeft: r.left + (scroller ? scroller.scrollLeft : 0), contentRight: r.right + (scroller ? scroller.scrollLeft : 0),
    scroller: scroller ? window.__rolaveis.indexOf(scroller) : -1,
    shown: inside && (fixed || r.top >= header - 0.5),
    where: {top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right),
            header: Math.round(header), clip: Object.fromEntries(Object.entries(clip).map(([k, v]) => [k, Math.round(v)]))},
  };
}'''
COLUMN_CONTROLS = '''() => [...document.querySelectorAll('main aside :is(a[href], button, input)')]
  .filter(node => node.getClientRects().length).length'''

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR")
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        page.goto(base + path, wait_until="load")
        page.evaluate("document.fonts.ready")
        page.evaluate("() => { window.scrollTo(0, 0); document.activeElement && document.activeElement.blur(); }")
        stops = []
        for tabs in range(1, 301):
            page.keyboard.press("Tab")
            stop = page.evaluate(STOP)
            if stop is None or (stops and stop["label"] == stops[0]["label"] and stop["top"] == stops[0]["top"]):
                break
            stop["n"] = tabs
            stops.append(stop)
        output["stops"] = [{k: s[k] for k in ("n", "label", "fixed", "top", "left")} for s in stops]
        for stop in stops:
            if not stop["shown"]:
                output["failures"].append(f"Tab {stop['n']} ('{stop['label']}') não aparece inteiro: {stop['where']}")
        flow = [s for s in stops if not s["fixed"]]
        for a, b in zip(flow, flow[1:]):
            overlap = min(a["bottom"], b["bottom"]) - max(a["top"], b["top"])
            same_row = overlap >= 0.5 * min(a["bottom"] - a["top"], b["bottom"] - b["top"])
            shared = a["scroller"] >= 0 and a["scroller"] == b["scroller"]
            a_left, b_left = (a["contentLeft"], b["contentLeft"]) if shared else (a["left"], b["left"])
            a_right = a["contentRight"] if shared else a["right"]
            pair = f"Tab {a['n']} ('{a['label']}') → Tab {b['n']} ('{b['label']}')"
            if same_row:
                if b_left < a_left - 1:
                    output["failures"].append(f"{pair}: na mesma linha, volta para a esquerda ({a_left:.0f} → {b_left:.0f} px)")
            elif b["top"] < a["top"] and b_left < a_right - 1:
                output["failures"].append(f"{pair}: volta {a['top'] - b['top']:.0f} px para cima na mesma coluna "
                                          f"(y {a['top']:.0f} → {b['top']:.0f}, x {a_left:.0f} → {b_left:.0f})")
        if path == "/noticias/":
            expected = page.evaluate(COLUMN_CONTROLS)
            reached = len({(s["label"], round(s["top"]), round(s["contentLeft"])) for s in stops if s["column"]})
            if reached != expected:
                output["failures"].append(f"{reached} de {expected} controles da coluna de filtros receberam o foco")
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


@pytest.mark.parametrize("viewport", VIEWPORTS, ids=[f"{w}x{h}" for w, h in VIEWPORTS])
@pytest.mark.parametrize("path", PAGES)
def test_tab_order_follows_the_screen_order(base_url, path, viewport):
    width, height = viewport
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, base_url, path, str(width), str(height)],
        capture_output=True, text=True, encoding="utf-8", timeout=240, env=subprocess_env(),
    )
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    if not isinstance(output, dict) or not isinstance(output.get("failures"), list):
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    if completed.returncode:
        pytest.fail(f"sonda caiu (código {completed.returncode}); falhas já registradas {output['failures']}; "
                    f"carregamento {output['load_failures']}:\n{completed.stderr[-4000:]}")
    assert not output["load_failures"], f"recursos locais que não carregaram em {path} {width}x{height}: {output['load_failures']}"
    assert len(output["stops"]) >= 5, f"{path} {width}x{height}: só {len(output['stops'])} paradas do Tab"
    assert not output["failures"], f"{path} {width}x{height}: " + "; ".join(output["failures"][:8])
