"""Botões e controles de todas as páginas publicadas: 44 px e um estilo só por tipo (desde 23/10/2026).

Até 23/10/2026 cada página tinha os seus botões: o azul do fim das matérias com 48 px e sombra, o branco das
seções de chamada com 56 a 58 px e 16 px de fonte, o dos Manuais com 46 px e cantos de 14 px, os do Comunicado com
38 px e uma cor por tipo de aviso, o "Ver mais documentos" como link de texto de 31 px. Os botões dos cards
tinham 40 px nas notícias e 30 px nos Manuais, e alguns controles ficavam abaixo de 44 px: o botão do menu do
celular e o "AVISOS!" (40), a faixa regulatória (40 a partir de 768 px), as setas da vitrine de manuais da home
(36 e 32), as categorias de /noticias/ na coluna (42) e o "Acessar rapidamente o manual" (42).

Desde então os botões usam assets/css/botoes.css: .botao com um dos quatro tipos (principal, secundario, claro e
contorno) e .botao-card nos cards de notícias e do catálogo de Manuais. O teste abre cada página publicada em
390 px com toque e em 960 e 1440 px com mouse e confere:
- todo botão e controle visível com pelo menos 44 px de altura e de largura: button, summary, select, campos,
  .botao, .botao-card, a faixa regulatória, o "AVISOS!", os links do acesso rápido aos manuais (com o menu
  aberto), os destinos do menu do celular (com o menu aberto, em 390 px) e qualquer link com fundo ou borda;
- botões do mesmo tipo com o mesmo estilo calculado (altura mínima, padding, borda, cantos, fonte, tamanho,
  peso, linha, cores, sombra e alinhamento), e os botões dos cards com o mesmo tamanho, cantos e fonte (a cor
  vem do tipo da notícia);
- nenhum link ou botão com a cara de um dos quatro tipos (azul com texto branco; branco com borda sobre fundo
  claro; branco sobre fundo escuro; transparente com borda branca sobre fundo escuro) sem a classe .botao.
Ficam fora os links de texto (sem fundo nem borda), o rodapé, os cards inteiros clicáveis (mais de 80 px de
altura ou com título ou imagem dentro) e os controles de estado (aria-pressed: categorias e ordenação de
/noticias/), que têm teste próprio. Na terceira conferência ficam fora também os controles que não são botões de
ação: o cabeçalho, a faixa, os flutuantes, os links do acesso rápido aos manuais e as setas dos carrosséis (que
entram na conferência dos 44 px).

Roda em subprocesso com o ServidorDeTeste (fila de 128; ver tests/support.py), uma sonda por largura, em paralelo.
"""
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler

import pytest

from support import ROOT, SITE_DIR, ServidorDeTeste, public_html_paths, subprocess_env


LARGURAS = ((390, 844, "toque"), (960, 900, "mouse"), (1440, 900, "mouse"))
MINIMO = 44
TIPOS = ("principal", "secundario", "claro", "contorno")
ROTAS = [
    "/" + rel[: -len("index.html")] if rel.endswith("index.html") else "/" + rel
    for rel in (path.relative_to(ROOT).as_posix() for path in public_html_paths())
]

PROBE = r"""
import json, sys
from playwright.sync_api import sync_playwright
from support import new_context, watch_local_loading

base, width, height, pointer = sys.argv[1], int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]
rotas = json.loads(sys.argv[5])
output = {"load_failures": [], "other_load_failures": [], "pages": {}}
OPTIONS = {"mouse": {}, "toque": {"has_touch": True, "is_mobile": True}}
FRAMES = "() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))"

COLETA = r'''(extra) => {
  const rgba = v => { const m = /rgba?\(([^)]*)\)/.exec(v || ''); if (!m) return null;
    const n = m[1].split(/[\s,\/]+/).filter(Boolean).map(Number); return {r: n[0], g: n[1], b: n[2], a: n.length > 3 ? n[3] : 1}; };
  const lum = c => { const f = x => { x /= 255; return x <= 0.03928 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4); };
    return 0.2126 * f(c.r) + 0.7152 * f(c.g) + 0.0722 * f(c.b); };
  const fundoEscuro = el => {
    for (let n = el.parentElement; n; n = n.parentElement) {
      const s = getComputedStyle(n);
      if (s.backgroundImage && s.backgroundImage.includes('gradient')) return true;
      const c = rgba(s.backgroundColor);
      if (c && c.a > 0.5) return lum(c) < 0.25;
    }
    return false;
  };
  const visivel = el => { const s = getComputedStyle(el), r = el.getBoundingClientRect();
    return s.display !== 'none' && s.visibility !== 'hidden' && r.width > 0 && r.height > 0 && !el.closest('[hidden], .sr-only'); };
  const rotulo = el => (el.innerText || el.value || el.getAttribute('aria-label') || el.getAttribute('placeholder') || el.className || el.tagName)
    .replace(/\s+/g, ' ').trim().slice(0, 50);
  const estilo = el => { const s = getComputedStyle(el); return {
    altura_minima: s.minHeight, padding: [s.paddingTop, s.paddingRight, s.paddingBottom, s.paddingLeft].join(' '),
    borda: [s.borderTopWidth, s.borderTopStyle, s.borderTopColor].join(' '),
    cantos: [s.borderTopLeftRadius, s.borderTopRightRadius, s.borderBottomRightRadius, s.borderBottomLeftRadius].join(' '),
    fonte: s.fontFamily, tamanho: s.fontSize, peso: s.fontWeight, linha: s.lineHeight, espacamento: s.letterSpacing,
    caixa: s.textTransform, sublinhado: s.textDecorationLine, fundo: s.backgroundColor, imagem: s.backgroundImage,
    cor: s.color, sombra: s.boxShadow, alinhamento: s.alignItems + ' ' + s.justifyContent}; };
  const estiloCard = el => { const s = getComputedStyle(el); return {
    altura_minima: s.minHeight, padding: [s.paddingTop, s.paddingBottom].join(' '),
    cantos: [s.borderTopLeftRadius, s.borderBottomRightRadius].join(' '),
    fonte: s.fontFamily, tamanho: s.fontSize, peso: s.fontWeight, linha: s.lineHeight}; };
  const fora = el => !!el.closest('footer');
  const pareceTipo = el => {
    const s = getComputedStyle(el), bg = rgba(s.backgroundColor) || {a: 0}, cor = rgba(s.color);
    const borda = parseFloat(s.borderTopWidth) > 0 && s.borderTopStyle !== 'none' ? rgba(s.borderTopColor) : null;
    const temBorda = !!borda && borda.a > 0.05, escuro = fundoEscuro(el);
    const branco = bg.a > 0.9 && bg.r > 245 && bg.g > 245 && bg.b > 245;
    const corBranca = cor && cor.r > 245 && cor.g > 245 && cor.b > 245;
    if (bg.a > 0.9 && Math.abs(bg.r - 21) < 12 && Math.abs(bg.g - 101) < 12 && Math.abs(bg.b - 192) < 12 && corBranca) return 'principal';
    if (branco && temBorda && !escuro) return 'secundario';
    if (branco && escuro) return 'claro';
    if (bg.a < 0.3 && temBorda && escuro && corBranca && borda.r > 245 && borda.g > 245 && borda.b > 245) return 'contorno';
    return null;
  };
  const controles = [], estilos = [], cards = [], semTipo = [];
  const vistos = new Set();
  const medir = (el, origem) => {
    if (vistos.has(el) || !visivel(el) || fora(el)) return;
    vistos.add(el);
    const r = el.getBoundingClientRect();
    controles.push({rotulo: rotulo(el), tag: el.tagName.toLowerCase(), origem, altura: Math.round(r.height * 10) / 10,
                    largura: Math.round(r.width * 10) / 10});
  };
  const seletor = extra.seletor;
  for (const el of document.querySelectorAll(seletor)) medir(el, 'controle');
  for (const el of document.querySelectorAll('a[href], button')) {
    if (!visivel(el) || fora(el) || el.matches('.botao, .botao-card') || el.hasAttribute('aria-pressed')) continue;
    const r = el.getBoundingClientRect();
    if (r.height > 80 || el.querySelector('h1, h2, h3, h4, h5, h6, img, picture')) continue;
    const s = getComputedStyle(el), bg = rgba(s.backgroundColor) || {a: 0};
    const temBorda = parseFloat(s.borderTopWidth) > 0 && s.borderTopStyle !== 'none' && (rgba(s.borderTopColor) || {a: 0}).a > 0.05;
    if (bg.a <= 0.15 && !temBorda) continue;
    medir(el, 'link com fundo ou borda');
    const tipo = pareceTipo(el);
    if (tipo && !el.closest('#navbar, .floating-buttons, .site-regulatory-banner, .manuals-filter-dropdown-panel, .news-filters__arrow, .home-manuals-nav'))
      semTipo.push({rotulo: rotulo(el), tipo, classes: String(el.className).slice(0, 120)});
  }
  for (const el of document.querySelectorAll('.botao')) {
    if (!visivel(el)) continue;
    const tipos = [...el.classList].filter(c => c.startsWith('botao--')).map(c => c.slice(7));
    estilos.push({rotulo: rotulo(el), tipos, estilo: estilo(el)});
  }
  for (const el of document.querySelectorAll('.botao-card')) {
    if (visivel(el)) cards.push({rotulo: rotulo(el), estilo: estiloCard(el)});
  }
  return {controles, estilos, cards, semTipo};
}'''

SELETOR = ("button, summary, select, input:not([type=hidden]):not([type=checkbox]):not([type=radio]), [role=button], "
           ".botao, .botao-card, .site-regulatory-banner__link, #navbar a[href='/comunicado/'], .manuals-filter-dropdown-panel a, "
           "#mobile-menu a")

try:
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": width, "height": height}, locale="pt-BR", **OPTIONS[pointer])
        page = context.new_page()
        closing = watch_local_loading(page, base, output["load_failures"], output["other_load_failures"])
        for rota in rotas:
            page.goto(base + rota, wait_until="load")
            page.evaluate("document.fonts.ready")
            page.evaluate(FRAMES)
            dados = page.evaluate(COLETA, {"seletor": SELETOR})
            # Com o menu de acesso rápido aos manuais aberto, os links dele.
            if page.locator(".manuals-filter-dropdown").count():
                page.evaluate("() => document.querySelectorAll('.manuals-filter-dropdown').forEach(d => d.open = true)")
                page.evaluate(FRAMES)
                aberto = page.evaluate(COLETA, {"seletor": ".manuals-filter-dropdown-panel a"})
                dados["controles"] += [c for c in aberto["controles"] if c["origem"] == "controle"]
                page.evaluate("() => document.querySelectorAll('.manuals-filter-dropdown').forEach(d => d.open = false)")
            # Em 390 px, com o menu do celular aberto, os destinos dele.
            if width < 768 and page.locator("#menu-toggle").is_visible():
                page.click("#menu-toggle")
                page.evaluate(FRAMES)
                aberto = page.evaluate(COLETA, {"seletor": "#mobile-menu a, #menu-toggle"})
                dados["controles"] += [c for c in aberto["controles"] if c["origem"] == "controle"]
                page.click("#menu-toggle")
            output["pages"][rota] = dados
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
def medidas():
    server = ServidorDeTeste(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def sonda(caso):
        width, height, pointer = caso
        completed = subprocess.run(
            [sys.executable, "-c", PROBE, base, str(width), str(height), pointer, json.dumps(ROTAS)],
            capture_output=True, text=True, encoding="utf-8", timeout=900, env=subprocess_env(),
        )
        try:
            output = json.loads(completed.stdout)
        except ValueError:
            output = None
        if not isinstance(output, dict) or completed.returncode or len(output.get("pages", {})) != len(ROTAS):
            pytest.fail(f"sonda de {width} px sem saída válida (código {completed.returncode}):\n"
                        f"{completed.stdout[-2000:]}\n{completed.stderr[-4000:]}")
        assert not output["load_failures"], f"recursos locais que não carregaram em {width} px: {output['load_failures'][:5]}"
        return f"{width} px ({pointer})", output["pages"]

    try:
        with ThreadPoolExecutor(max_workers=len(LARGURAS)) as pool:
            yield dict(pool.map(sonda, LARGURAS))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_rotas_cobrem_as_paginas_publicadas():
    assert len(ROTAS) > 100
    assert "/" in ROTAS and "/comunicado/" in ROTAS and "/manuais-e-pops/" in ROTAS


def test_todo_botao_e_controle_tem_pelo_menos_44_px(medidas):
    curtos = []
    for largura, paginas in medidas.items():
        for rota, dados in paginas.items():
            for c in dados["controles"]:
                if c["altura"] < MINIMO - 0.5 or c["largura"] < MINIMO - 0.5:
                    curtos.append(f"{largura} {rota}: <{c['tag']}> {c['rotulo']!r} ({c['origem']}) {c['largura']} x {c['altura']} px")
    contados = sum(len(d["controles"]) for paginas in medidas.values() for d in paginas.values())
    assert contados > 2500, contados
    assert not curtos, f"{len(curtos)} controles abaixo de {MINIMO} px:\n" + "\n".join(curtos[:40])


def test_botoes_do_mesmo_tipo_tem_o_mesmo_estilo(medidas):
    por_tipo = {tipo: {} for tipo in TIPOS}
    sem_um_tipo = []
    for largura, paginas in medidas.items():
        for rota, dados in paginas.items():
            for b in dados["estilos"]:
                if len(b["tipos"]) != 1 or b["tipos"][0] not in TIPOS:
                    sem_um_tipo.append(f"{largura} {rota}: {b['rotulo']!r} com tipos {b['tipos']}")
                    continue
                chave = json.dumps(b["estilo"], sort_keys=True)
                por_tipo[b["tipos"][0]].setdefault(chave, []).append(f"{largura} {rota}: {b['rotulo']!r}")
    assert not sem_um_tipo, "\n".join(sem_um_tipo[:20])
    for tipo in TIPOS:
        assert por_tipo[tipo], f"nenhum botão {tipo} encontrado"
    divergentes = []
    for tipo, estilos in por_tipo.items():
        if len(estilos) > 1:
            base, *outros = sorted(estilos, key=lambda chave: -len(estilos[chave]))
            referencia = json.loads(base)
            for chave in outros:
                diferenca = {k: v for k, v in json.loads(chave).items() if referencia.get(k) != v}
                divergentes.append(f"{tipo}: {len(estilos[chave])} botão(ões) com {diferenca} (o comum tem "
                                   f"{ {k: referencia[k] for k in diferenca} }), ex. {estilos[chave][:3]}")
    assert not divergentes, "\n".join(divergentes)


def test_botoes_dos_cards_tem_o_mesmo_tamanho_e_fonte(medidas):
    estilos = {}
    for largura, paginas in medidas.items():
        for rota, dados in paginas.items():
            for c in dados["cards"]:
                estilos.setdefault(json.dumps(c["estilo"], sort_keys=True), []).append(f"{largura} {rota}: {c['rotulo']!r}")
    rotulos = {exemplo.split(": ", 1)[1] for exemplos in estilos.values() for exemplo in exemplos}
    assert {"'Ler atualização'", "'Ler notícia'", "'Ler orientação'", "'Ver detalhes'", "'Solicitar orçamento'"} <= rotulos, rotulos
    assert len(estilos) == 1, "\n".join(f"{chave}: {len(v)}, ex. {v[:3]}" for chave, v in estilos.items())


def test_nenhum_botao_com_cara_de_tipo_fica_sem_a_classe(medidas):
    soltos = [
        f"{largura} {rota}: {s['rotulo']!r} parece {s['tipo']} ({s['classes']})"
        for largura, paginas in medidas.items()
        for rota, dados in paginas.items()
        for s in dados["semTipo"]
    ]
    assert not soltos, "\n".join(soltos[:30])
