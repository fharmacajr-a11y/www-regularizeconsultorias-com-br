"""Guarda de transição: nenhuma transição CSS antes da carga da página.

Achado de compatibilidade da 2ª entrega (seção 10.1 do relatório) e B2 da 3ª: no Chrome 152, os
elementos com `transition` dentro de contêineres de consulta (`container-type`) recebiam um estilo
calculado antes das folhas externas e, quando elas chegavam, transicionavam desse estilo (borda
preta, cantos retos, sem padding) até o final. Na Home isso aparecia como o "pisca" dos cards de
"Por que escolher". Num iframe (srcdoc ou navegação real do iframe), a Home disparou cerca de 300
eventos `transitionrun` em todas as cargas; na navegação de topo do painel do app não reproduziu
nas tentativas registradas, e no Chromium headless dos testes não reproduz. Por isso o teste não
espera o defeito acontecer: ele confere o mecanismo que o impede.

Cada página pública (e o modelo de notícia) tem, logo depois do `<meta charset>`, antes de qualquer
folha externa ou outro script:
- um script que põe a classe `transicoes-contidas` no `<html>` e a tira dois quadros depois do `load`;
- um `<style>` que, com a classe, zera `transition` em todos os elementos e pseudoelementos.

O seletor da guarda leva `:not(#sem-transicao)`, que lhe dá especificidade (1,1,1): ela vence as
regras do site que declaram `transition` com `!important` (no máximo (0,2,2)). Um teste estático
confere isso nas folhas do site.

No navegador (Home, Sobre, Comunicado, listagem e uma matéria), o teste confere que a classe está
no `<html>` no DOMContentLoaded e no `load`, que sai depois, que nenhuma transição roda enquanto ela
está ativa (inclusive com uma mudança de estilo forçada num card de "Por que escolher" no
DOMContentLoaded) e que, depois de liberada, a mesma mudança volta a transicionar.
"""
import json
import re
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import ROOT, SITE_DIR, public_html_paths, subprocess_env


GUARDA_SCRIPT = ("<script>document.documentElement.classList.add('transicoes-contidas');addEventListener('load',function(){"
                 "requestAnimationFrame(function(){requestAnimationFrame(function(){document.documentElement.classList.remove("
                 "'transicoes-contidas');});});});</script>")
GUARDA_STYLE = ("<style>html.transicoes-contidas *:not(#sem-transicao),html.transicoes-contidas *:not(#sem-transicao)::before,"
                "html.transicoes-contidas *:not(#sem-transicao)::after{transition:none!important}</style>")
ESPECIFICIDADE_GUARDA = (1, 1, 1)
PAGINAS = ("/", "/sobre/", "/comunicado/", "/noticias/", "/noticias/anvisa-alerta-soroterapia-promessas-sem-evidencia/")
PORTAS_RECUSADAS = {5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080}


def _paginas_com_guarda():
    return list(public_html_paths()) + [ROOT / "noticias" / "template-noticia.html"]


def test_guarda_logo_depois_do_charset_em_todas_as_paginas():
    faltas = []
    for caminho in _paginas_com_guarda():
        html = caminho.read_text(encoding="utf-8")
        rel = caminho.relative_to(ROOT).as_posix()
        if html.count(GUARDA_SCRIPT) != 1 or html.count(GUARDA_STYLE) != 1:
            faltas.append((rel, "guarda ausente ou repetida"))
            continue
        charset = re.search(r'<meta charset="[^"]+"\s*/?>', html, re.I)
        pos_script, pos_style = html.index(GUARDA_SCRIPT), html.index(GUARDA_STYLE)
        primeira_folha = html.find('rel="stylesheet"')
        outros_scripts = [m.start() for m in re.finditer(r"<script", html) if m.start() != pos_script]
        if not (charset and charset.end() <= pos_script < pos_style):
            faltas.append((rel, "guarda fora do lugar"))
        if primeira_folha != -1 and pos_style > primeira_folha:
            faltas.append((rel, "guarda depois de uma folha externa"))
        if outros_scripts and min(outros_scripts) < pos_script:
            faltas.append((rel, "outro script antes da guarda"))
    assert len(_paginas_com_guarda()) >= 105
    assert faltas == [], faltas


def _sem_comentarios(css):
    return re.sub(r"/\*.*?\*/", "", css, flags=re.S)


def _regras(css):
    """(seletor, declarações) de cada regra de estilo, inclusive dentro de @media/@container/@supports."""
    regras, i, n = [], 0, len(css)
    pilha = []
    inicio = 0
    while i < n:
        c = css[i]
        if c == "{":
            pilha.append(css[inicio:i].strip())
            inicio = i + 1
        elif c == "}":
            if pilha:
                cabeca = pilha.pop()
                corpo = css[inicio:i]
                if not cabeca.startswith("@") and "{" not in corpo:
                    regras.append((cabeca, corpo))
            inicio = i + 1
        elif c == ";" and not pilha:
            inicio = i + 1
        i += 1
    return regras


def _dividir(lista):
    partes, nivel, atual = [], 0, ""
    for c in lista:
        if c == "(":
            nivel += 1
        elif c == ")":
            nivel -= 1
        if c == "," and nivel == 0:
            partes.append(atual)
            atual = ""
        else:
            atual += c
    partes.append(atual)
    return [p.strip() for p in partes if p.strip()]


def _especificidade(seletor):
    """(ids, classes/atributos/pseudoclasses, tipos/pseudoelementos), como no CSS Selectors 4."""
    a = b = c = 0
    s = seletor
    # Pseudoclasses funcionais: :is/:not/:has contam o argumento mais específico; :where conta zero.
    while True:
        m = re.search(r":(is|not|has|where|matches)\(", s)
        if not m:
            break
        nivel, j = 1, m.end()
        while nivel:
            if s[j] == "(":
                nivel += 1
            elif s[j] == ")":
                nivel -= 1
            j += 1
        dentro = s[m.start() + len(m.group(1)) + 2:j - 1]
        if m.group(1) != "where":
            maior = max((_especificidade(x) for x in _dividir(dentro)), default=(0, 0, 0))
            a, b, c = a + maior[0], b + maior[1], c + maior[2]
        s = s[:m.start()] + " " + s[j:]
    for padrao, peso in ((r"\[[^\]]*\]", "b"), (r"#(?:\\.|[\w-])+", "a"), (r"\.(?:\\.|[\w-])+", "b"),
                         (r"::[\w-]+(?:\([^)]*\))?", "c"), (r":(?:before|after|first-line|first-letter)\b", "c"),
                         (r":[\w-]+(?:\([^)]*\))?", "b")):
        achados = len(re.findall(padrao, s))
        s = re.sub(padrao, " ", s)
        if peso == "a":
            a += achados
        elif peso == "b":
            b += achados
        else:
            c += achados
    c += len(re.findall(r"(?:^|[\s>+~])([a-zA-Z][\w-]*)", s))
    return (a, b, c)


def test_especificidade_da_guarda_vence_as_transicoes_com_important():
    assert _especificidade("html.transicoes-contidas *:not(#sem-transicao)") == ESPECIFICIDADE_GUARDA
    assert _especificidade("html.transicoes-contidas *:not(#sem-transicao)::before") == (1, 1, 2)
    concorrentes = []
    for arquivo in sorted((ROOT / "assets" / "css").rglob("*.css")):
        for seletor, corpo in _regras(_sem_comentarios(arquivo.read_text(encoding="utf-8"))):
            if re.search(r"transition[\w-]*\s*:[^;]*!important", corpo):
                for s in _dividir(seletor):
                    concorrentes.append((arquivo.relative_to(ROOT).as_posix(), s, _especificidade(s)))
    # Hoje há quatro regras assim (cards compactos de notícias e o ícone deles), em custom.css,
    # custom.min.css e noticias.css.
    assert concorrentes, "nenhuma regra concorrente encontrada: confira o leitor de CSS"
    acima = [x for x in concorrentes if x[2] >= ESPECIFICIDADE_GUARDA]
    assert acima == [], acima


PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, paginas = sys.argv[1], json.loads(sys.argv[2])
INIT = r'''
window.__guarda = {eventos: [], dcl: null, load: null};
document.addEventListener('transitionrun', e => window.__guarda.eventos.push({prop: e.propertyName,
  alvo: (e.target.className && e.target.className.baseVal === undefined ? e.target.className : e.target.tagName).toString().slice(0, 40),
  t: performance.now()}), true);
document.addEventListener('DOMContentLoaded', () => {
  const h = document.documentElement;
  const card = document.querySelector('.home-about-cards-grid > *');
  window.__guarda.dcl = {classe: h.classList.contains('transicoes-contidas'),
    transicaoCard: card ? getComputedStyle(card).transitionProperty : null};
  if (card) card.style.borderColor = 'rgb(255, 0, 0)';
});
addEventListener('load', () => {
  window.__guarda.load = {classe: document.documentElement.classList.contains('transicoes-contidas'), t: performance.now()};
});
'''
saida = []
with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    for pagina in paginas:
        context = support.new_context(browser, viewport={"width": 1280, "height": 900}, device_scale_factor=1)
        context.add_init_script(INIT)
        page = context.new_page()
        page.goto(base + pagina, wait_until="load")
        page.wait_for_timeout(400)
        estado = page.evaluate("() => ({...window.__guarda, depois: document.documentElement.classList.contains('transicoes-contidas'), "
                               "liberacao: performance.now()})")
        antes = len(estado["eventos"])
        depois = page.evaluate('''async () => {
          const card = document.querySelector('.home-about-cards-grid > *');
          if (!card) return null;
          const n0 = window.__guarda.eventos.length;
          card.style.borderColor = 'rgb(0, 0, 255)';
          await new Promise(r => setTimeout(r, 200));
          return {transicao: getComputedStyle(card).transitionProperty, eventos: window.__guarda.eventos.slice(n0)};
        }''')
        saida.append({"pagina": pagina, "estado": estado, "eventosNaGuarda": estado["eventos"][:antes], "depois": depois})
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
def guarda():
    server = _servidor()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        processo = subprocess.run([sys.executable, "-c", PROBE, base, json.dumps(PAGINAS)], capture_output=True, text=True,
                                  encoding="utf-8", env=subprocess_env(), timeout=600)
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert processo.returncode == 0, processo.stderr[-4000:]
    return {r["pagina"]: r for r in json.loads(processo.stdout)}


def test_classe_ativa_na_carga_e_retirada_depois(guarda):
    for pagina, r in guarda.items():
        e = r["estado"]
        assert e["dcl"]["classe"] is True, (pagina, "guarda inativa no DOMContentLoaded")
        assert e["load"]["classe"] is True, (pagina, "guarda inativa no load")
        assert e["depois"] is False, (pagina, "guarda não foi retirada depois do load")


def test_nenhuma_transicao_enquanto_a_guarda_esta_ativa(guarda):
    for pagina, r in guarda.items():
        assert r["eventosNaGuarda"] == [], (pagina, r["eventosNaGuarda"][:5])
    home = guarda["/"]
    # O card de "Por que escolher" tem transition-all; com a guarda, nada transiciona, nem a mudança forçada.
    assert home["estado"]["dcl"]["transicaoCard"] == "none"


def test_transicoes_voltam_depois_da_carga(guarda):
    depois = guarda["/"]["depois"]
    assert depois and depois["transicao"] == "all", depois
    props = {e["prop"] for e in depois["eventos"]}
    assert {"border-top-color", "border-bottom-color"} <= props, depois["eventos"][:5]
