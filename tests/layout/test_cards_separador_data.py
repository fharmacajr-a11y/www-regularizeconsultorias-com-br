"""Separador "•" entre o selo e a data dos cards, sem ficar sozinho no fim da linha.

Nos cards do Comunicado, a linha de cima junta ícone, selo, "•" e data numa
linha flexível com quebra. Em celular, a data descia para a linha seguinte e o
"•" ficava sozinho no fim da primeira, depois do selo. Até 20/10/2026 só o card
#instabilidade-anvisa-2026-10-19 escondia o "•" abaixo de 640 px
(`hidden sm:block`); desde então todos os cards, ativos e encerrados, usam a
mesma classe. Na listagem de notícias o separador entre o selo e a categoria é
um ponto (`span.h-1.w-1`), já escondido abaixo de 640 px, e o "•" fica dentro
da data ("DD/MM/AAAA • HHhMM"), numa linha própria com `whitespace-nowrap`.

Em 320, 360, 390 e 414 px o teste exige o separador de cada card oculto
(`display: none`); em 1280 px, visível. Em todas as larguras, cada "•" visível
de cada card (o separador e o da data) tem de estar na mesma linha do caractere
visível seguinte e do anterior: sozinho no fim ou no começo da linha reprova. A
linha é a do próprio caractere (`Range.getClientRects`), e dois caracteres estão
na mesma linha quando as caixas se sobrepõem na vertical em pelo menos metade
da menor altura. O separador sem texto das notícias é medido pela caixa dele.
Entram todos os cards: no Comunicado, os ativos e os de "Histórico / encerrados";
nas Notícias, os 84, depois de "Ver mais notícias".

Na Farmácia Popular, o quadro "Atualização normativa • 12/08/2026" é texto
corrido, sem separador próprio: o "•" ficava no fim da linha de 320 a 414 px e
em 640 e 680 px, quando o quadro passa a ter o link ao lado. Desde 20/10/2026 o
"•" e a data ficam num `whitespace-nowrap` e descem juntos; ali o "•" pode
começar a linha, mas não terminá-la.

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

from support import SITE_DIR, ServidorDeTeste, subprocess_env


NARROW_WIDTHS = (320, 360, 390, 414)
WIDE_WIDTH = 1280
PAGES = {
    "comunicado": {"route": "/comunicado/", "cards": "#avisos-lista > article", "dot": None, "separator": True,
                   "widths": NARROW_WIDTHS + (WIDE_WIDTH,)},
    "noticias": {"route": "/noticias/", "cards": "#news-article-list [data-news-card]",
                 "dot": 'span.h-1.w-1.rounded-full[aria-hidden="true"]', "separator": True,
                 "widths": NARROW_WIDTHS + (WIDE_WIDTH,)},
    "farmacia-popular": {"route": "/farmacia-popular/", "cards": ".fp-regulatory-update", "dot": None, "separator": False,
                         "widths": NARROW_WIDTHS + (640, 680, WIDE_WIDTH)},
}
CASES = [(page, width) for page, config in PAGES.items() for width in config["widths"]]

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, route, cards, dot, width, height = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4], int(sys.argv[5]), int(sys.argv[6])
output = {"cards": [], "total": 0, "load_failures": [], "other_load_failures": [], "falhas": []}

READY = '''async () => {
  await document.fonts.ready;
  for (let i = 0; i < 2; i += 1) await new Promise((done) => requestAnimationFrame(done));
}'''
# Para cada card visível: o separador (folha com "•" ou o ponto das notícias) e
# cada "•" visível, com a linha do caractere vizinho de cada lado.
MEASURE = '''({cards, dot}) => {
  const visible = (range) => [...range.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
  const charRect = (node, offset) => {
    const range = document.createRange();
    range.setStart(node, offset);
    range.setEnd(node, offset + 1);
    const rects = visible(range);
    return rects.length ? rects[0] : null;
  };
  const sameLine = (a, b) => Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top) >= 0.5 * Math.min(a.height, b.height);
  const box = (r) => r && {top: Math.round(r.top), bottom: Math.round(r.bottom), left: Math.round(r.left), right: Math.round(r.right)};
  // Caractere visível mais próximo, a partir de (nodes[index], offset), no sentido step.
  const neighbor = (nodes, index, offset, step) => {
    for (let i = index, off = offset + step; i >= 0 && i < nodes.length; i += step) {
      if (i !== index) off = step > 0 ? 0 : nodes[i].data.length - 1;
      for (; off >= 0 && off < nodes[i].data.length; off += step) {
        const ch = nodes[i].data[off];
        if (!ch.trim()) continue;
        const rect = charRect(nodes[i], off);
        if (rect) return {ch, rect};
      }
    }
    return null;
  };
  const lines = (rect, prev, next) => ({
    fim_de_linha: Boolean(next && !sameLine(rect, next.rect)),
    inicio_de_linha: Boolean(prev && !sameLine(rect, prev.rect)),
    anterior: prev && prev.ch, seguinte: next && next.ch, caixa: box(rect),
    caixa_seguinte: next && box(next.rect),
  });
  const all = [...document.querySelectorAll(cards)];
  return {total: all.length, cards: all.filter((card) => card.getClientRects().length).map((card, index) => {
    const walker = document.createTreeWalker(card, NodeFilter.SHOW_TEXT);
    const nodes = [];
    for (let node = walker.nextNode(); node; node = walker.nextNode()) nodes.push(node);
    const title = card.querySelector('h2, h3');
    const separators = [...card.querySelectorAll('*')].filter((el) => !el.children.length && el.textContent.trim() === '•');
    if (dot) separators.push(...card.querySelectorAll(dot));
    return {
      indice: index + 1,
      id: card.id || null,
      status: card.getAttribute('data-status'),
      titulo: title ? title.textContent.trim().slice(0, 70) : null,
      separadores: separators.map((el) => {
        const rects = [...el.getClientRects()].filter((r) => r.width > 0 && r.height > 0);
        const item = {tipo: el.textContent.trim() === '•' ? 'span •' : 'ponto', classe: el.getAttribute('class'),
                      display: getComputedStyle(el).display, visivel: rects.length > 0};
        if (!rects.length || el.textContent.trim()) return item;
        // Ponto sem texto: vizinhos são o último caractere antes dele e o primeiro depois.
        let after = nodes.findIndex((node) => el.compareDocumentPosition(node) & Node.DOCUMENT_POSITION_FOLLOWING);
        if (after < 0) after = nodes.length;
        const next = after < nodes.length ? neighbor(nodes, after, -1, 1) : null;
        const prev = after > 0 ? neighbor(nodes, after - 1, nodes[after - 1].data.length, -1) : null;
        return {...item, ...lines(rects[0], prev, next)};
      }),
      pontos: nodes.flatMap((node, i) => [...node.data].map((ch, off) => [ch, off]).filter(([ch]) => ch === '•').map(([, off]) => {
        const rect = charRect(node, off);
        const context = node.data.trim().slice(0, 30);
        if (!rect) return {contexto: context, visivel: false};
        return {contexto: context, visivel: true, ...lines(rect, neighbor(nodes, i, off, -1), neighbor(nodes, i, off, 1))};
      })),
    };
  })};
}'''

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR")
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        page.goto(base + route, wait_until="networkidle")
        if route == "/noticias/":
            # "Ver mais notícias" até revelar todos os cards.
            for _ in range(10):
                if not page.locator("#btn-carregar-mais").is_visible():
                    break
                page.locator("#btn-carregar-mais").click()
                page.wait_for_timeout(100)
        page.evaluate(READY)
        output.update(page.evaluate(MEASURE, {"cards": cards, "dot": dot or None}))
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


def _probe(base_url, page, width):
    config = PAGES[page]
    height = 900 if width == WIDE_WIDTH else 844
    completed = subprocess.run(
        [sys.executable, "-c", PROBE, base_url, config["route"], config["cards"], config["dot"] or "", str(width), str(height)],
        capture_output=True, text=True, encoding="utf-8", timeout=180, env=subprocess_env(),
    )
    try:
        output = json.loads(completed.stdout)
    except ValueError:
        output = None
    if not isinstance(output, dict) or not isinstance(output.get("cards"), list):
        pytest.fail(f"sonda sem saída válida (código {completed.returncode}):\n{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
    if completed.returncode:
        pytest.fail(f"sonda caiu (código {completed.returncode}); carregamento {output['load_failures']}:\n{completed.stderr[-4000:]}")
    assert not output["load_failures"], f"recursos locais que não carregaram em {page} {width}px: {output['load_failures']}"
    return output


@pytest.mark.parametrize("page,width", CASES, ids=[f"{page}-{width}" for page, width in CASES])
def test_card_separator_never_ends_a_line(base_url, page, width):
    output = _probe(base_url, page, width)
    cards = output["cards"]
    assert cards and len(cards) == output["total"], f"{page} {width}px: {len(cards)} de {output['total']} cards visíveis"

    failures = []
    for card in cards:
        label = f"card {card['indice']} ({card['id'] or card['titulo']})"
        items = card["pontos"]
        if PAGES[page]["separator"]:
            if len(card["separadores"]) != 1:
                failures.append(f"{label}: {len(card['separadores'])} separadores, esperado 1")
                continue
            separator = card["separadores"][0]
            if width < 640 and separator["display"] != "none":
                failures.append(f"{label}: separador {separator['tipo']} aparece em {width}px (display {separator['display']}, "
                                f"classe {separator['classe']!r}); deveria ficar oculto abaixo de 640 px")
            if width >= 640 and not separator["visivel"]:
                failures.append(f"{label}: separador {separator['tipo']} sumiu em {width}px (display {separator['display']})")
            items = [separator] + items
        elif not any(item["visivel"] for item in items):
            failures.append(f"{label}: nenhum '•' visível")
        for item in items:
            where = item.get("contexto") or item["tipo"]
            if item.get("fim_de_linha"):
                failures.append(f"{label}: '{where}' sozinho no fim da linha (caixa {item['caixa']}, "
                                f"'{item['seguinte']}' na linha seguinte {item['caixa_seguinte']})")
            # Sem separador próprio (Farmácia Popular), o "•" desce com a data e pode começar a linha.
            if item.get("inicio_de_linha") and PAGES[page]["separator"]:
                failures.append(f"{label}: '{where}' sozinho no começo da linha, separado de '{item['anterior']}'")
    if width >= 640 and page == "comunicado":
        bullets = sum(1 for card in cards for item in card["pontos"] if item["contexto"] == "•" and item["visivel"])
        assert bullets == len(cards), f"comunicado {width}px: {bullets} '•' separadores visíveis em {len(cards)} cards"
    assert not failures, f"{page} {width}px, {len(failures)} problema(s):\n" + "\n".join(failures)
