"""Cards de /noticias/: um só modelo, medido nos estilos calculados (parecer de 11/10/2026, R1).

O pedido do responsável: os 83 cards com a mesma tipografia e os mesmos espaçamentos, sem tamanho maior para os cinco
primeiros e sem outra tipografia por categoria; no card, só a data e, quando houver, a hora. O teste abre /noticias/
no Chromium com a Inter local e, em cada janela, lê os estilos calculados (getComputedStyle) dos elementos
equivalentes de cada card visível: o card (padding, borda, raio e sombra), a linha de selos, o selo do tipo e a
categoria (fonte, tamanho, peso, entrelinha, caixa e padding; as cores ficam fora, porque são do tipo e da categoria),
a data e o bloco dela, o título, o resumo e o botão (fonte, tamanho, peso, entrelinha, espaçamento entre letras,
margens, padding, largura máxima e a reserva da faixa dos controles). A altura do botão também conta: ele tem uma linha.
A altura do título e do resumo não conta: o número de linhas vem do tamanho do texto.

Estados: a carga (os cinco primeiros), "Ver mais notícias" (83), o filtro "Farmácia Popular" (5 e, com "Ver mais",
10), a busca "cnes" e a ordem "Mais velha". Em cada janela, a união dos cards de todos os estados tem de ter um único
estilo por elemento; a posição, o estado e a categoria não podem trocar o formato. Antes da leitura o foco sai do card
e o ponteiro sai da página: o "Ver mais" leva o foco ao primeiro card revelado, e o foco muda borda e sombra.

Também em cada estado: nenhum card com "Atualizado em" ou "Publicado em"; título e resumo inteiros (sem rolagem
interna, sem reticências, sem limite de linhas, overflow visível); nenhuma rolagem horizontal da página. E, com o
foco de teclado num card dos cinco primeiros e num card revelado por "Ver mais", o anel de foco do botão aparece
(contorno sólido de 2px afastado 2px) e fica dentro da janela.

Janelas: 320, 375, 414, 640, 767, 768, 1024, 1280 e 1440 px sem a barra de rolagem clássica e, com a barra clássica do
Chromium (sem --hide-scrollbars), 320 (305 px úteis), 783 (768 úteis), 1039 (1024 úteis) e 1375 (1360 úteis, o limite
da reserva da faixa dos controles). A distância real entre o texto dos cards e os botões flutuantes é medida em
test_noticias_cards_faixa.py.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env


JANELAS = ((320, 800), (375, 667), (414, 896), (640, 800), (767, 1024), (768, 1024), (1024, 800), (1280, 900),
           (1440, 900))
JANELAS_BARRA = ((320, 568), (783, 1024), (1039, 800), (1375, 900))
GRUPOS = ((JANELAS[:5], False), (JANELAS[5:], False), (JANELAS_BARRA, True))
ELEMENTOS = ("card", "linha", "selo", "categoria", "data", "data_bloco", "titulo", "resumo", "botao", "botao_altura")

PROBE = r'''
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, janelas, barra = sys.argv[1], json.loads(sys.argv[2]), sys.argv[3] == "1"

LEITURA = r"""
() => {
  const props = {
    card: ['paddingTop','paddingRight','paddingBottom','paddingLeft','borderTopWidth','borderRightWidth','borderBottomWidth','borderLeftWidth','borderRadius','boxShadow'],
    linha: ['marginBottom','rowGap','columnGap','fontSize','fontWeight','flexDirection'],
    selo: ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','textTransform','paddingTop','paddingRight','paddingBottom','paddingLeft','borderRadius'],
    categoria: ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','textTransform','paddingTop','paddingRight','paddingBottom','paddingLeft','borderRadius'],
    data: ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','color','whiteSpace','fontStyle'],
    data_bloco: ['fontSize','fontWeight','lineHeight','color','textAlign','columnGap','justifyContent','whiteSpace'],
    titulo: ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','color','marginTop','marginBottom','maxWidth','paddingRight','textTransform','textOverflow','overflow','webkitLineClamp'],
    resumo: ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','color','marginTop','marginBottom','maxWidth','paddingRight','textOverflow','overflow','webkitLineClamp'],
    botao: ['fontFamily','fontSize','fontWeight','lineHeight','letterSpacing','paddingTop','paddingRight','paddingBottom','paddingLeft','columnGap','borderRadius','textTransform'],
  };
  const pick = (el, ks) => { if (!el) return null; const s = getComputedStyle(el); const o = {}; for (const k of ks) o[k] = s[k]; return o; };
  const cards = [...document.querySelectorAll('#news-article-list [data-news-card]')]
    .filter(c => getComputedStyle(c).display !== 'none' && c.getClientRects().length);
  return {
    rolagemX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    cards: cards.map((c, i) => {
      const linha = c.querySelector(':scope > div');
      const selo = linha && linha.querySelector(':scope > div > span');
      const cat = c.querySelector('.category-chip');
      const time = c.querySelector('time');
      const h2 = c.querySelector('h2'), p = c.querySelector(':scope > p'), a = c.querySelector(':scope > a');
      return {
        pos: i + 1,
        titulo: c.dataset.title,
        texto: c.textContent.replace(/\s+/g, ' '),
        estilos: {card: pick(c, props.card), linha: pick(linha, props.linha), selo: pick(selo, props.selo),
                  categoria: pick(cat, props.categoria), data: pick(time, props.data),
                  data_bloco: pick(time && time.closest('div'), props.data_bloco), titulo: pick(h2, props.titulo),
                  resumo: pick(p, props.resumo), botao: pick(a, props.botao),
                  botao_altura: a ? Math.round(a.getBoundingClientRect().height * 100) / 100 : null},
        transbordo: [h2.scrollWidth - h2.clientWidth, h2.scrollHeight - h2.clientHeight,
                     p.scrollWidth - p.clientWidth, p.scrollHeight - p.clientHeight,
                     c.scrollWidth - c.clientWidth],
      };
    }),
  };
}
"""

FOCO = r"""
(i) => {
  const cards = [...document.querySelectorAll('#news-article-list [data-news-card]')].filter(c => !c.classList.contains('hidden'));
  const a = cards[i].querySelector(':scope > a');
  a.focus();
  const s = getComputedStyle(a), r = a.getBoundingClientRect(), off = parseFloat(s.outlineOffset), w = parseFloat(s.outlineWidth);
  return {focusVisible: a.matches(':focus-visible'), estilo: s.outlineStyle, largura: w, afastamento: off,
          esquerda: r.left - off - w, direita: r.right + off + w, janela: document.documentElement.clientWidth};
}
"""

saida = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, ignore_default_args=["--hide-scrollbars"] if barra else None)
    for largura, altura in janelas:
        page = support.new_page(browser, allow=(base,), viewport={"width": largura, "height": altura}, device_scale_factor=1)
        page.goto(base + "/noticias/", wait_until="load")
        page.evaluate("document.fonts.ready")
        estados = {}
        focos = {}

        def ler(nome):
            page.evaluate("() => document.activeElement && document.activeElement.blur()")
            page.mouse.move(0, 0)
            page.wait_for_timeout(120)
            estados[nome] = page.evaluate(LEITURA)

        def foco(nome, i):
            page.keyboard.press("Shift")
            page.locator("#news-article-list [data-news-card]:not(.hidden) > a").nth(i).scroll_into_view_if_needed()
            focos[nome] = page.evaluate(FOCO, i)

        ler("carga")
        foco("carga_1o_card", 0)
        page.click("#btn-carregar-mais")
        ler("ver_mais")
        foco("ver_mais_card_revelado", 40)
        page.click("[data-news-category='farmacia-popular']")
        ler("filtro")
        page.click("#btn-carregar-mais")
        ler("filtro_ver_mais")
        page.click("[data-news-category='todos']")
        page.fill("#news-search", "cnes")
        ler("busca")
        page.fill("#news-search", "")
        page.click("[data-news-sort='asc']")
        ler("mais_velha")
        util = page.evaluate("() => document.documentElement.clientWidth")
        saida.append({"janela": [largura, altura], "barra": barra, "util": util, "estados": estados, "focos": focos})
        page.context.close()
    browser.close()
print(json.dumps(saida))
'''


class _Quieto(SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


@pytest.fixture(scope="module")
def medidas():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quieto, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        processos = [
            subprocess.Popen([sys.executable, "-c", PROBE, base, json.dumps(janelas), "1" if barra else "0"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, env=subprocess_env())
            for janelas, barra in GRUPOS
        ]
        resultado = []
        for processo in processos:
            out, err = processo.communicate(timeout=300)
            assert processo.returncode == 0, err[-4000:]
            resultado += json.loads(out.strip().splitlines()[-1])
        return resultado
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


def test_janelas_e_barra_classica(medidas):
    assert len(medidas) == len(JANELAS) + len(JANELAS_BARRA)
    for janela in medidas:
        if janela["barra"]:
            assert janela["util"] < janela["janela"][0], (janela["janela"], "a barra clássica não apareceu")
        else:
            assert janela["util"] == janela["janela"][0]
        visiveis = {nome: len(e["cards"]) for nome, e in janela["estados"].items()}
        assert visiveis == {"carga": 5, "ver_mais": 85, "filtro": 5, "filtro_ver_mais": 11, "busca": 5,
                            "mais_velha": 5}, (janela["janela"], visiveis)


def test_dois_modelos_uniformes_dentro_de_cada_grupo(medidas):
    """Posição 1–5: um estilo. Posição 6 em diante: outro. Cada grupo é estável entre os estados."""
    divergencias = []
    for janela in medidas:
        acumulado = {elemento: {"maior": set(), "compacto": set()} for elemento in ELEMENTOS}
        for nome, estado in janela["estados"].items():
            for elemento in ELEMENTOS:
                por_grupo = {"maior": set(), "compacto": set()}
                for card in estado["cards"]:
                    grupo = "maior" if card["pos"] <= 5 else "compacto"
                    por_grupo[grupo].add(json.dumps(card["estilos"][elemento], sort_keys=True))
                    acumulado[elemento][grupo].add(json.dumps(card["estilos"][elemento], sort_keys=True))
                if any(len(valores) > 1 for valores in por_grupo.values()):
                    divergencias.append((janela["janela"], nome, elemento, {k: len(v) for k, v in por_grupo.items()}))
            visiveis = estado["cards"]
            if nome in ("ver_mais", "filtro_ver_mais"):
                if not any(c["pos"] == 5 for c in visiveis) or not any(c["pos"] == 6 for c in visiveis):
                    divergencias.append((janela["janela"], nome, "sem quinto e sexto"))
                else:
                    quinto = next(c for c in visiveis if c["pos"] == 5)
                    sexto = next(c for c in visiveis if c["pos"] == 6)
                    if quinto["estilos"]["titulo"] == sexto["estilos"]["titulo"]:
                        divergencias.append((janela["janela"], nome, "quinto e sexto com o mesmo titulo"))
        for elemento in ("card", "titulo", "resumo", "botao"):
            if len(acumulado[elemento]["maior"]) != 1 or len(acumulado[elemento]["compacto"]) != 1:
                divergencias.append((janela["janela"], elemento, "grupo instavel",
                                     {k: len(v) for k, v in acumulado[elemento].items()}))
            # O botão é o mesmo nos dois modelos desde 23/10/2026 (.botao-card, assets/css/botoes.css: 44 px e 14 px,
            # como nos cards de Manuais); antes o do compacto era menor.
            elif elemento == "botao" and acumulado[elemento]["maior"] != acumulado[elemento]["compacto"]:
                divergencias.append((janela["janela"], elemento, "maior diferente do compacto"))
            elif elemento != "botao" and acumulado[elemento]["maior"] == acumulado[elemento]["compacto"]:
                divergencias.append((janela["janela"], elemento, "maior igual ao compacto"))
    assert not divergencias, json.dumps(divergencias, ensure_ascii=False)[:6000]


def test_cards_sem_prefixo_texto_inteiro_e_sem_rolagem_horizontal(medidas):
    falhas = []
    for janela in medidas:
        for nome, estado in janela["estados"].items():
            if estado["rolagemX"] > 0:
                falhas.append((janela["janela"], nome, "rolagem horizontal", estado["rolagemX"]))
            for card in estado["cards"]:
                if "Atualizado em" in card["texto"] or "Publicado em" in card["texto"]:
                    falhas.append((janela["janela"], nome, card["titulo"], "prefixo"))
                if any(x > 0.5 for x in card["transbordo"]):
                    falhas.append((janela["janela"], nome, card["titulo"], "transbordo", card["transbordo"]))
                titulo, resumo = card["estilos"]["titulo"], card["estilos"]["resumo"]
                for el in (titulo, resumo):
                    if el["textOverflow"] != "clip" or el["webkitLineClamp"] != "none" or el["overflow"] != "visible":
                        falhas.append((janela["janela"], nome, card["titulo"], "corte", el))
    assert not falhas, falhas[:20]


def test_anel_de_foco_do_botao_nos_cinco_primeiros_e_nos_revelados(medidas):
    falhas = []
    for janela in medidas:
        for nome, foco in janela["focos"].items():
            ok = (foco["focusVisible"] and foco["estilo"] == "solid" and foco["largura"] >= 2 and foco["afastamento"] >= 2
                  and foco["esquerda"] >= 0 and foco["direita"] <= foco["janela"])
            if not ok:
                falhas.append((janela["janela"], janela["barra"], nome, foco))
    assert not falhas, falhas
