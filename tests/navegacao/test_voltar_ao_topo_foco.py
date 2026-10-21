"""Foco no início da página depois do "Voltar ao topo".

Até 20/10/2026, ao clicar em voltar ao topo, o foco ficava no botão, que some
quando a página chega ao topo; o navegador o tirava de lá e o foco ia para o
body, mas a navegação sequencial continuava a partir do lugar do botão, no fim
do documento. O 1º Tab ia para o WhatsApp, o 2º saía da página e só o 3º
chegava à faixa da Portaria; um Shift+Tab levava ao último link do rodapé e a
página rolava de volta até o fim. Desde então, logo depois de iniciar a
rolagem, o main.js leva o foco para o primeiro elemento do body (a faixa da
Portaria, aside.site-regulatory-banner) com tabindex="-1" e
focus({preventScroll: true}), sem contorno de foco em volta da faixa, e tira o
tabindex e o estilo quando o foco sai dela.

A sonda rola a página até 1500 px, espera o botão aparecer e o aciona pelo
mouse (clique) ou pelo teclado (Tab a partir do último controle antes do botão
e Enter). Um ouvinte de clique registrado depois do main.js lê o scrollY e o
elemento com foco logo depois da chamada dele; um registro por quadro acompanha
a página até ela parar no topo. Parada, a sonda lê o elemento com foco, se ele
casa com :focus-visible e o contorno calculado, aperta Tab (ou, numa segunda
carga da página, Shift+Tab), espera a rolagem parar e lê de novo. Entram a Home
(base.css e components.css), em 390x844, e o Comunicado (custom.min.css), em
1280x900, com e sem prefers-reduced-motion: reduce, pelo teclado e pelo mouse;
a rolagem continua direta com movimento reduzido e suave sem ele.

Roda em subprocesso com o ServidorDeTeste (fila de 128; ver tests/support.py).
A sonda registra os recursos locais que não carregaram.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler

import pytest

from support import ROOT, SITE_DIR, ServidorDeTeste, parse_html, public_html_paths, subprocess_env


START_Y = 1500
CASES = tuple(
    (route, width, height, motion, entrada)
    for route, width, height in (("/", 390, 844), ("/comunicado/", 1280, 900))
    for motion in ("reduce", "no-preference")
    for entrada in ("teclado", "mouse")
)

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, route, width, height, motion, entrada, start = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), sys.argv[5], sys.argv[6], int(sys.argv[7])
output = {"load_failures": [], "other_load_failures": [], "sequencias": {}}

DESCREVE = '''
window.__descreve = (el) => {
  if (!el) return null;
  const texto = (el.getAttribute('aria-label') || el.textContent || '').replace(/\s+/g, ' ').trim().slice(0, 60);
  return {
    tag: el.tagName.toLowerCase(), id: el.id || null, classe: el.getAttribute('class'), texto,
    body: el === document.body, faixa: el.matches('.site-regulatory-banner'),
    primeiroDoBody: el === document.body.firstElementChild,
    linkDaFaixa: el.matches('.site-regulatory-banner__link'),
    noRodape: !!el.closest('footer'), noFlutuante: !!el.closest('.floating-buttons'),
    tabindex: el.getAttribute('tabindex'),
  };
};
'''
READY = '''async ([start, entrada]) => {
  await document.fonts.ready;
  scrollTo(0, start);
  const button = document.getElementById('btn-voltar-topo');
  const began = performance.now();
  while (performance.now() - began < 3000) {
    await new Promise((done) => requestAnimationFrame(done));
    if (button.classList.contains('is-visible') && getComputedStyle(button).opacity === '1') break;
  }
  // Último controle antes do botão na ordem do documento: o ponto de onde o
  // Tab chega ao botão e para onde o Shift+Tab levava depois do clique.
  const tabbable = [...document.querySelectorAll('a[href], button, input, select, textarea, [tabindex]')]
    .filter((el) => el.tabIndex >= 0 && !el.disabled && el.checkVisibility({visibilityProperty: true}));
  const anteriores = tabbable.filter((el) => el.compareDocumentPosition(button) & Node.DOCUMENT_POSITION_FOLLOWING);
  const ultimo = anteriores[anteriores.length - 1];
  window.__ultimoAntesDoBotao = ultimo;
  if (entrada === 'teclado') ultimo.focus({preventScroll: true});
  // Ouvinte registrado depois do main.js: roda logo depois da chamada de rolagem e de foco dele.
  window.__voltarTopo = {partida: scrollY, noClique: null, focoNoClique: null, quadros: []};
  button.addEventListener('click', () => {
    window.__voltarTopo.noClique = scrollY;
    window.__voltarTopo.focoNoClique = __descreve(document.activeElement);
  }, {once: true});
  return {scrollY, visivel: button.classList.contains('is-visible'),
          reduzido: matchMedia('(prefers-reduced-motion: reduce)').matches,
          ultimoAntesDoBotao: __descreve(ultimo), focoAntes: __descreve(document.activeElement)};
}'''
ON_BUTTON = '''() => ({foco: __descreve(document.activeElement),
  focoVisivel: document.activeElement.matches(':focus-visible'), scrollY})'''
FOLLOW = '''async () => {
  const state = window.__voltarTopo;
  const began = performance.now();
  let since = performance.now();
  while (performance.now() - began < 5000) {
    await new Promise((done) => requestAnimationFrame(done));
    state.quadros.push(scrollY);
    if (scrollY !== 0) since = performance.now();
    else if (performance.now() - since >= 300) break;
  }
  const el = document.activeElement;
  const style = getComputedStyle(el);
  const rect = el.getBoundingClientRect();
  return {...state, final: scrollY, esperou: Math.round(performance.now() - began),
          foco: __descreve(el), focoVisivel: el.matches(':focus-visible'),
          contorno: {estilo: style.outlineStyle, largura: style.outlineWidth, cor: style.outlineColor,
                     sombra: style.boxShadow, inline: el.style.outline || null},
          caixa: {largura: Math.round(rect.width), altura: Math.round(rect.height)}};
}'''
AFTER_KEY = '''async () => {
  const began = performance.now();
  let last = scrollY, since = performance.now();
  while (performance.now() - began < 3000) {
    await new Promise((done) => requestAnimationFrame(done));
    if (scrollY !== last) { last = scrollY; since = performance.now(); }
    else if (performance.now() - since >= 300) break;
  }
  const el = document.activeElement;
  const faixa = document.querySelector('.site-regulatory-banner');
  return {foco: __descreve(el), focoVisivel: el.matches(':focus-visible'), scrollY,
          ultimoAntesDoBotao: el === window.__ultimoAntesDoBotao,
          documentoComFoco: document.hasFocus(),
          faixaTabindex: faixa && faixa.getAttribute('tabindex'), faixaOutlineInline: faixa && (faixa.style.outline || null)};
}'''

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR", reduced_motion=motion)
        context.add_init_script(DESCREVE)
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        for key in ("Tab", "Shift+Tab"):
            page.goto(base + route, wait_until="networkidle")
            medida = {"pronto": page.evaluate(READY, [start, entrada])}
            if entrada == "teclado":
                page.keyboard.press("Tab")
                medida["noBotao"] = page.evaluate(ON_BUTTON)
                page.keyboard.press("Enter")
            else:
                page.locator("#btn-voltar-topo").click()
            medida["topo"] = page.evaluate(FOLLOW)
            page.keyboard.press(key)
            medida["depois"] = page.evaluate(AFTER_KEY)
            output["sequencias"][key] = medida
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


def run_probe(base_url, route, width, height, motion, entrada):
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, base_url, route, str(width), str(height), motion, entrada, str(START_Y)],
        capture_output=True, text=True, encoding="utf-8", timeout=180, env=subprocess_env(),
    )
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    if not isinstance(output, dict) or "sequencias" not in output:
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    if completed.returncode:
        pytest.fail(f"sonda caiu (código {completed.returncode}); carregamento {output['load_failures']}:\n{completed.stderr[-4000:]}")
    return output


@pytest.mark.parametrize(
    "route,width,height,motion,entrada", CASES,
    ids=[f"{route.strip('/') or 'home'}-{width}-{motion}-{entrada}" for route, width, _, motion, entrada in CASES],
)
def test_focus_goes_to_top_of_page_after_back_to_top(base_url, route, width, height, motion, entrada):
    output = run_probe(base_url, route, width, height, motion, entrada)
    assert not output["load_failures"], f"recursos locais que não carregaram: {output['load_failures']}"

    for key, medida in output["sequencias"].items():
        label = f"{route} {width}x{height}, {motion}, {entrada}, {key}"
        ready, top, after = medida["pronto"], medida["topo"], medida["depois"]
        assert ready["visivel"] and ready["scrollY"] == START_Y, f"{label}: botão não apareceu em scrollY {START_Y} ({ready})"
        assert ready["reduzido"] == (motion == "reduce"), f"{label}: emulação da preferência não aplicada"
        if entrada == "teclado":
            on_button = medida["noBotao"]
            assert on_button["foco"]["id"] == "btn-voltar-topo" and on_button["focoVisivel"], (
                f"{label}: o Tab a partir de {ready['ultimoAntesDoBotao']} não chegou ao botão ({on_button})"
            )
        assert top["noClique"] is not None, f"{label}: o acionamento não chegou ao botão"

        # A rolagem continua como antes: direta com movimento reduzido, suave sem ele.
        assert top["final"] == 0, f"{label}: a página parou em scrollY {top['final']} depois de {top['esperou']} ms"
        frames = top["quadros"]
        intermediate = [y for y in frames if 0 < y < START_Y]
        if motion == "reduce":
            assert top["noClique"] == 0, f"{label}: logo depois do clique o scrollY era {top['noClique']}, não 0"
            assert not intermediate, f"{label}: {len(intermediate)} quadros com posição intermediária: {intermediate[:10]}"
        else:
            assert top["noClique"] == START_Y, f"{label}: a página saltou para {top['noClique']} no clique, sem rolagem suave"
            assert len(intermediate) >= 3, f"{label}: só {len(intermediate)} quadros intermediários ({frames[:20]})"
            assert all(a >= b for a, b in zip(frames, frames[1:])), f"{label}: a posição subiu e desceu ({frames[:40]})"

        # Logo depois de iniciar a rolagem, o foco já está na faixa, primeiro elemento do body.
        assert top["focoNoClique"] and top["focoNoClique"]["faixa"] and top["focoNoClique"]["primeiroDoBody"], (
            f"{label}: no clique, o foco estava em {top['focoNoClique']}"
        )
        assert top["foco"]["faixa"] and top["foco"]["tabindex"] == "-1", f"{label}: no topo, o foco estava em {top['foco']}"
        # Sem contorno de foco em volta da faixa inteira, pelo teclado (:focus-visible) e pelo mouse.
        assert top["focoVisivel"] == (entrada == "teclado"), f"{label}: :focus-visible inesperado na faixa ({top})"
        assert top["contorno"]["estilo"] == "none" and top["contorno"]["sombra"] == "none", (
            f"{label}: a faixa ({top['caixa']}) ganhou contorno ou sombra de foco: {top['contorno']}"
        )

        assert after["scrollY"] == 0, f"{label}: depois do {key}, a página rolou até scrollY {after['scrollY']} (foco em {after['foco']})"
        assert after["faixaTabindex"] is None and after["faixaOutlineInline"] is None, (
            f"{label}: a faixa ficou com tabindex {after['faixaTabindex']} ou outline {after['faixaOutlineInline']} depois do {key}"
        )
        if key == "Tab":
            assert after["foco"]["linkDaFaixa"] and after["focoVisivel"], f"{label}: o Tab levou o foco a {after['foco']}"
        else:
            focused = after["foco"]
            assert not (focused["noRodape"] or focused["noFlutuante"] or after["ultimoAntesDoBotao"]), (
                f"{label}: o Shift+Tab levou o foco de volta ao fim da página: {focused}"
            )


def test_back_to_top_pages_start_with_the_portaria_banner():
    # O main.js foca o primeiro elemento do body; o teste de navegador abre só a Home e o Comunicado.
    pages = [path for path in public_html_paths() if 'id="btn-voltar-topo"' in path.read_text(encoding="utf-8")]
    pages.append(ROOT / "noticias" / "template-noticia.html")
    assert len(pages) > 2
    for path in pages:
        body = next(node for node in parse_html(path).descendants() if node.tag == "body")
        first = body.children[0]
        assert first.tag == "aside" and "site-regulatory-banner" in first.attrs.get("class", "").split(), (
            f"{path.relative_to(ROOT)}: o primeiro elemento do body é <{first.tag} class={first.attrs.get('class')!r}>"
        )
