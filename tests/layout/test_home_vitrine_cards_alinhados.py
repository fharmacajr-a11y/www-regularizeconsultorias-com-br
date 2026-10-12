"""Cards da vitrine de Manuais e POPs da Home com a mesma altura e os links alinhados na base.

Demanda HOME-CARDS-ALTURA (11/10/2026), registrada com duas capturas do responsável: os cards de
"Manuais, POPs e documentos técnicos para diferentes operações" tinham a altura do próprio texto, e
as bases e os links "Conhecer materiais" ficavam em alturas diferentes; ao avançar o carrossel, o
card visível mudava de altura.

O teste abre a Home em janelas de 320 a 1440 px (639/640, 767/768 e 1023/1024 nos limites das
regras da vitrine) e, com a barra de rolagem clássica do Chromium (sem --hide-scrollbars), em
quatro janelas em que a largura útil fica 15 px menor que a das media queries. Em cada uma, mede
os nove cards na posição inicial, a cada avanço pela seta seguinte até o fim, a cada retorno pela
seta anterior até o início e em cada quadro do movimento (requestAnimationFrame), e exige:

- a mesma altura externa nos nove cards, inclusive os que estão fora da janela do carrossel, e a
  mesma altura em todos os estados (ela pode mudar entre larguras, não entre posições);
- nos cards visíveis, a mesma base e o link "Conhecer materiais" na mesma altura, com a mesma
  distância até a borda inferior em todos os cards;
- título, texto, link e imagem inteiros dentro do card (que tem overflow hidden), sem texto
  transbordando da própria caixa, sem line-clamp nem ellipsis, com a mesma fonte em todos os
  cards (nenhum card com fonte reduzida para caber) e a imagem quadrada na largura do card.

A tolerância de 0,5 px cobre só o arredondamento subpixel do layout (unidades de 1/64 px).
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env


TOL = 0.5
JANELAS = (
    (320, 568), (375, 667), (414, 896), (639, 800), (640, 800), (767, 1024),
    (768, 1024), (1023, 800), (1024, 800), (1280, 900), (1360, 900), (1440, 900),
)
# Com a barra clássica: menor largura útil (305 px), 768 px úteis com a regra de 768 px,
# 3 cards com 900 px úteis e 1265 px úteis.
JANELAS_BARRA = ((320, 568), (783, 1024), (915, 800), (1280, 900))
GRUPOS = ((JANELAS[:4], False), (JANELAS[4:8], False), (JANELAS[8:], False), (JANELAS_BARRA, True))
PORTAS_RECUSADAS = {5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080}

PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, janelas, barra = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3] == "1"

MEDIR = r'''
() => {
  const px = v => parseFloat(v) || 0;
  const car = document.querySelector('[data-home-manuals-carousel]');
  const jan = car.getBoundingClientRect();
  const caixa = e => { const q = e.getBoundingClientRect(); return {l: q.left, r: q.right, t: q.top, b: q.bottom, w: q.width, h: q.height}; };
  return {sl: car.scrollLeft, cards: [...car.querySelectorAll('.home-manuals-card')].map(c => {
    const corpo = c.querySelector('.home-manuals-card-body'), tit = c.querySelector('.home-manuals-card-title'),
      txt = c.querySelector('.home-manuals-card-text'), link = c.querySelector('.home-manuals-card-link'), img = c.querySelector('img');
    const k = caixa(c), cb = getComputedStyle(c);
    const dentro = q => q.t >= k.t - 0.5 && q.b <= k.b + 0.5 && q.l >= k.l - 0.5 && q.r <= k.r + 0.5;
    const est = e => { const s = getComputedStyle(e); return {fs: px(s.fontSize), lh: px(s.lineHeight),
      clamp: s.webkitLineClamp || 'none', to: s.textOverflow}; };
    const partes = [tit, txt, link, img].map(caixa);
    return {titulo: tit.textContent.trim(), card: k, link: caixa(link), img: caixa(img),
      bordas: px(cb.borderLeftWidth) + px(cb.borderRightWidth),
      dentro: partes.every(dentro),
      transborda: [corpo, tit, txt, link].some(e => e.scrollHeight > e.clientHeight + 1 || e.scrollWidth > e.clientWidth + 1),
      estilos: {titulo: est(tit), texto: est(txt), link: est(link)},
      visivel: k.r > jan.left + 1 && k.l < jan.right - 1};
  })};
}
'''

QUADROS = r'''
async () => {
  const car = document.querySelector('[data-home-manuals-carousel]');
  const cards = [...car.querySelectorAll('.home-manuals-card')];
  const quadros = []; let ultimo = null, parado = 0;
  const t0 = performance.now();
  while (performance.now() - t0 < 4000) {
    await new Promise(r => requestAnimationFrame(r));
    const hs = cards.map(c => c.getBoundingClientRect().height);
    quadros.push({sl: car.scrollLeft, min: Math.min(...hs), max: Math.max(...hs)});
    parado = ultimo !== null && Math.abs(car.scrollLeft - ultimo) < 0.01 ? parado + 1 : 0;
    ultimo = car.scrollLeft;
    if (parado >= 8) break;
  }
  return quadros;
}
'''

saida = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True, ignore_default_args=["--hide-scrollbars"] if barra else None)
    for largura, altura in janelas:
        context = support.new_context(browser, viewport={"width": largura, "height": altura}, device_scale_factor=1)
        page = context.new_page()
        page.goto(base + "/", wait_until="load")
        page.evaluate("async () => { await document.fonts.ready; }")
        page.evaluate("() => document.querySelector('.home-manuals-section').scrollIntoView({block: 'center', behavior: 'instant'})")
        estados = [{"acao": "inicial", "medida": page.evaluate(MEDIR), "quadros": []}]
        for acao, seletor in (("avanco", "[data-home-manuals-next]"), ("retorno", "[data-home-manuals-prev]")):
            for _ in range(12):
                antes = estados[-1]["medida"]["sl"]
                caixa = page.locator(seletor).bounding_box()
                page.mouse.click(caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2)
                quadros = page.evaluate(QUADROS)
                medida = page.evaluate(MEDIR)
                estados.append({"acao": acao, "medida": medida, "quadros": quadros})
                if abs(medida["sl"] - antes) <= 0.5:
                    break
        saida.append({"largura": largura, "altura": altura, "barra": barra,
                      "larguraUtil": page.evaluate("document.documentElement.clientWidth"), "estados": estados})
        context.close()
    browser.close()
print(json.dumps(saida))
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def _servidor():
    while True:
        server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=str(SITE_DIR)))
        if server.server_port not in PORTAS_RECUSADAS:
            return server
        server.server_close()


@pytest.fixture(scope="module")
def vitrine():
    server = _servidor()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        processos = [
            subprocess.Popen([sys.executable, "-c", PROBE, base, json.dumps(grupo), "1" if barra else "0"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8",
                             env=subprocess_env())
            for grupo, barra in GRUPOS
        ]
        saidas = [processo.communicate(timeout=900) for processo in processos]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    resultado = []
    for processo, (stdout, stderr) in zip(processos, saidas):
        assert processo.returncode == 0, stderr[-4000:]
        resultado.extend(json.loads(stdout))
    return {(r["largura"], r["altura"], r["barra"]): r for r in resultado}


def _janela(chave):
    largura, altura, barra = chave
    return f"{largura}x{altura}{' barra' if barra else ''}"


def _dif(valores):
    return max(valores) - min(valores)


def test_janelas_e_estados_medidos(vitrine):
    assert len(vitrine) == len(JANELAS) + len(JANELAS_BARRA)
    for chave, janela in vitrine.items():
        if chave[2]:
            assert janela["larguraUtil"] < chave[0], (_janela(chave), "a barra clássica não apareceu")
        acoes = [e["acao"] for e in janela["estados"]]
        # Avança até a seta não mover mais e volta até o início.
        assert acoes.count("avanco") >= 2 and acoes.count("retorno") >= 2, (_janela(chave), acoes)
        assert janela["estados"][-1]["medida"]["sl"] == pytest.approx(0, abs=1), _janela(chave)
        assert all(len(e["medida"]["cards"]) == 9 for e in janela["estados"]), _janela(chave)


def test_nove_cards_com_a_mesma_altura_em_todos_os_estados(vitrine):
    falhas = {}
    for chave, janela in sorted(vitrine.items()):
        inicial = [c["card"]["h"] for c in janela["estados"][0]["medida"]["cards"]]
        referencia = inicial[0]
        for estado in janela["estados"]:
            alturas = [c["card"]["h"] for c in estado["medida"]["cards"]]
            quadros = [q["max"] - q["min"] for q in estado["quadros"]]
            fora = [round(h - referencia, 3) for h in alturas if abs(h - referencia) > TOL]
            if _dif(alturas) > TOL or fora or any(d > TOL for d in quadros):
                falhas.setdefault(_janela(chave), []).append(
                    {"acao": estado["acao"], "sl": round(estado["medida"]["sl"]),
                     "alturas": sorted({round(h, 2) for h in alturas}),
                     "quadroMaisDesigual": round(max(quadros, default=0), 3)})
    assert falhas == {}, "\n".join(f"{k}: {v[:3]}" for k, v in falhas.items())


def test_bases_e_links_alinhados_nos_cards_visiveis(vitrine):
    falhas = {}
    for chave, janela in sorted(vitrine.items()):
        for estado in janela["estados"]:
            cards = estado["medida"]["cards"]
            visiveis = [c for c in cards if c["visivel"]]
            assert visiveis, (_janela(chave), estado["acao"])
            bases = [c["card"]["b"] for c in visiveis]
            links = [c["link"]["b"] for c in visiveis]
            ate_base = [c["card"]["b"] - c["link"]["b"] for c in cards]
            if _dif(bases) > TOL or _dif(links) > TOL or _dif(ate_base) > TOL:
                falhas.setdefault(_janela(chave), []).append(
                    {"acao": estado["acao"], "sl": round(estado["medida"]["sl"]),
                     "bases": [round(b, 2) for b in bases], "links": [round(b, 2) for b in links],
                     "linkAteBase": sorted({round(d, 2) for d in ate_base})})
    assert falhas == {}, "\n".join(f"{k}: {v[:3]}" for k, v in falhas.items())


def test_texto_completo_mesma_fonte_e_imagem_quadrada(vitrine):
    falhas = {}
    for chave, janela in sorted(vitrine.items()):
        for estado in janela["estados"][:1] + janela["estados"][-1:]:
            cards = estado["medida"]["cards"]
            erros = []
            for c in cards:
                if not c["dentro"] or c["transborda"]:
                    erros.append(("texto ou imagem fora do card", c["titulo"]))
                if any(e["clamp"] not in ("none", "") or e["to"] == "ellipsis" for e in c["estilos"].values()):
                    erros.append(("line-clamp ou ellipsis", c["titulo"]))
                largura_interna = c["card"]["w"] - c["bordas"]
                if abs(c["img"]["h"] - c["img"]["w"]) > TOL or abs(c["img"]["w"] - largura_interna) > TOL:
                    erros.append(("imagem fora da proporção 1:1 ou da largura do card", c["titulo"], c["img"]))
            for parte in ("titulo", "texto", "link"):
                fontes = {(c["estilos"][parte]["fs"], c["estilos"][parte]["lh"]) for c in cards}
                if len(fontes) != 1:
                    erros.append((f"fonte do {parte} diferente entre os cards", sorted(fontes)))
            if erros:
                falhas.setdefault(_janela(chave), []).extend(erros)
    assert falhas == {}, "\n".join(f"{k}: {v[:4]}" for k, v in falhas.items())
