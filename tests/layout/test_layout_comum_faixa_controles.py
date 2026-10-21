"""Layout comum: rodapé, CTAs, conteúdo, título e Home fora da coluna dos botões flutuantes.

Voltar ao topo e WhatsApp ficam fixos à direita, a max(1.5rem, safe-area) da borda da largura útil, com 2.75rem
até 640px e 3rem acima. Como a coluna não muda de posição horizontal enquanto a página rola, uma linha de texto
ou uma caixa clicável que passa pela faixa vertical da coluna em alguma rolagem só fica livre se terminar antes da
borda esquerda dela. O teste abre cada página em cada janela (com a Inter local e a rede dos testes) e mede:

1. texto do <main> e do rodapé: as palavras de cada nó de texto (Range.getClientRects, sem SVG, script, style e
   .sr-only) unidas em linhas por elemento e recortadas pelos ancestrais com overflow (só a parte exposta conta;
   fragmentos menores que 0,5 px saem). Cada linha que a coluna alcança precisa terminar pelo menos 8 px antes da
   borda esquerda da coluna em repouso (a folga calculada das regras; a medida pode passar disso). Alcance vertical:
   em coordenadas do documento, cada controle varre da posição de repouso dele com scrollY 0 (WhatsApp) ou 301
   (Voltar ao topo, visível acima de 300 pelo main.js) até a posição real dele no fim da página, medida no scrollY
   máximo com a ancoragem do main.js (a coluna para 1rem acima dos créditos do rodapé ou do fechamento do
   Comunicado e não desce além disso). Uma linha cuja faixa vertical cruza essa varredura é alcançada; abaixo da
   parada (os créditos, que a coluna nunca cobre) não é;
2. caixas clicáveis (links, botões, campos, summary): as alcançáveis precisam terminar antes da coluna com folga
   de pelo menos max(8 px, alcance do contorno de foco, alcance horizontal da sombra visível). Contorno e sombra
   vêm do estilo computado no estado :focus-visible real (focus({focusVisible: true})) e no repouso; o alcance
   visível da sombra é |x| + espalhamento + desfoque/2;
3. fim real da página: no scrollY máximo, com a coluna no estado em que estiver (ancorada ou fixa), nenhuma linha
   ou caixa do <main> e do rodapé na faixa vertical dela pode encostar nela;
4. títulos (H1 das matérias e dos heróis institucionais): nenhuma palavra passa da caixa de conteúdo do título (o
   caso de "estabelecimentos" em 320 px no Edital 6/2026 e as outras palavras longas), e nenhuma palavra do título é
   partida entre linhas fora de um hífen opcional (&shy;) — quebra sem hífen não conta como solução;
5. Home: os cards de "Por que escolher" (superfícies sem link) não ficam sob a coluna, e a seta seguinte da
   vitrine cumpre o critério de foco do item 2.

Exceções declaradas: elementos fixos ou sticky (cabeçalho, faixa regulatória) e os próprios controles ficam fora.
Até 21/10/2026 a coluna de filtros da listagem de notícias também ficava, porque vinha depois da lista e o
assets/js/pages/noticias.js recolhia os botões enquanto ela passava por eles; desde então ela vem antes da lista,
compacta abaixo de 1024 px, e a pesquisa e a faixa de categorias reservam a faixa como os outros blocos (o
conteúdo da faixa que rola conta só na parte exposta, pelo recorte do overflow). A matriz inclui janelas com a barra de rolagem clássica do
Chromium (sem --hide-scrollbars): as media queries usam a largura da janela e o layout, a largura útil (15 px a
menos). Inclui também telas baixas (568x320, 667x375, 740x360 e 812x375): com pouca altura, o herói e o começo da
página, que em altura normal ficam acima do alcance da coluna, passam pela faixa dela.
"""
import json
import subprocess
import sys
import threading

import pytest

from support import subprocess_env
from test_institucional_faixa_controles import _servidor


PAGINAS = (
    "/", "/servicos/", "/comunicado/", "/farmacia-popular/", "/noticias/", "/manuais-e-pops/",
    "/manuais-e-pops/manual-farmacia-manipulacao/", "/contato/", "/politica-de-privacidade/",
    "/noticias/anvisa-camara-tecnica-cosmetovigilancia/", "/noticias/anvisa-regras-cosmeticos-artesanais/",
    "/noticias/anvisa-edital-6-2026-afe-manipulacao-preparacoes-estereis/",
    "/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/", "/manuais-e-pops/manual-transportadoras/",
)
JANELAS = ((320, 568), (375, 667), (768, 1024), (1024, 800), (1280, 900))
JANELAS_BARRA = ((375, 667), (768, 1024), (1280, 900))
# Telas baixas (celular e tablet em paisagem): o herói e o começo da página entram no alcance da coluna.
JANELAS_BAIXAS = ((568, 320), (667, 375), (740, 360), (812, 375))
GRUPOS = ((JANELAS[:2], False), (JANELAS[2:], False), (JANELAS_BARRA, True), (JANELAS_BAIXAS, False))
FOLGA_TEXTO = 8.0
TOLERANCIA = 0.05

PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, janelas, paginas, barra = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3]), sys.argv[4] == "1"

MEDIR = r'''
async () => {
  await document.fonts.ready;
  const quadro = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  // Imagens com loading=lazy carregam antes da medida (a geometria não depende delas, mas a página fica estável).
  for (let y = 0; y <= document.documentElement.scrollHeight; y += Math.max(200, innerHeight - 40)) {
    window.scrollTo({top: y, behavior: 'instant'}); await quadro();
  }
  window.scrollTo({top: 0, behavior: 'instant'}); await quadro(); await quadro();
  const fixo = el => { for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
    const p = getComputedStyle(e).position; if (p === 'fixed' || p === 'sticky') return true; } return false; };
  const fora = el => el.closest('script, style, noscript, template, svg, .floating-buttons, .sr-only')
    || fixo(el) || !el.closest('main, footer');
  const clip = el => {
    let c = {l: -1e9, t: -1e9, r: 1e9, b: 1e9};
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      const s = getComputedStyle(e);
      if (s.overflowX !== 'visible' || s.overflowY !== 'visible') {
        const q = e.getBoundingClientRect();
        c = {l: Math.max(c.l, q.left + parseFloat(s.borderLeftWidth)), t: Math.max(c.t, q.top + parseFloat(s.borderTopWidth)),
             r: Math.min(c.r, q.right - parseFloat(s.borderRightWidth)), b: Math.min(c.b, q.bottom - parseFloat(s.borderBottomWidth))};
      }
    }
    return c;
  };
  const cortar = (q, c) => { const l = Math.max(q.left, c.l), r = Math.min(q.right, c.r), t = Math.max(q.top, c.t), b = Math.min(q.bottom, c.b);
    return r - l >= 0.5 && b - t >= 0.5 ? {l, r, t, b} : null; };
  const opac = el => { let o = 1; for (let e = el; e; e = e.parentElement) o *= Number(getComputedStyle(e).opacity); return o; };
  const sy0 = scrollY;
  // Linhas de texto por elemento.
  const porEl = new Map(), clips = new Map();
  const w = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const el = n.parentElement;
    if (!n.textContent.trim() || !el || fora(el) || getComputedStyle(el).visibility !== 'visible' || opac(el) < 0.1) continue;
    if (!clips.has(el)) clips.set(el, clip(el));
    const re = /\S+/g; let m;
    while ((m = re.exec(n.textContent))) {
      const r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
      for (const q of r.getClientRects()) { const k = cortar(q, clips.get(el)); if (k) { if (!porEl.has(el)) porEl.set(el, []); porEl.get(el).push({...k, w: m[0]}); } }
    }
  }
  const linhas = [];
  for (const [el, qs] of porEl) {
    qs.sort((x, y) => x.t - y.t || x.l - y.l);
    const ls = [];
    for (const q of qs) {
      const ln = ls.find(x => Math.min(x.b, q.b) - Math.max(x.t, q.t) > 0.5 * Math.min(x.b - x.t, q.b - q.t));
      if (ln) { ln.l = Math.min(ln.l, q.l); ln.r = Math.max(ln.r, q.r); ln.t = Math.min(ln.t, q.t); ln.b = Math.max(ln.b, q.b); ln.p.push(q.w); }
      else ls.push({l: q.l, r: q.r, t: q.t, b: q.b, p: [q.w]});
    }
    for (const x of ls) linhas.push({l: x.l, r: x.r, t: x.t + sy0, b: x.b + sy0, texto: x.p.join(' ').slice(0, 70),
                                      rodape: !!el.closest('footer')});
  }
  // Caixas clicáveis, com contorno de foco e sombra visível.
  const alcance = txt => { if (!txt || txt === 'none') return 0; let m = 0;
    for (const parte of txt.split(/,(?![^(]*\))/)) {
      if (/inset/.test(parte)) continue;
      const cor = parte.match(/rgba?\([^)]*\)/); if (cor && /rgba\([^)]*,\s*0\)$/.test(cor[0])) continue;
      const v = (parte.replace(/rgba?\([^)]*\)/, '').match(/-?\d+(\.\d+)?px/g) || []).map(parseFloat).concat([0, 0, 0, 0]);
      m = Math.max(m, Math.abs(v[0]) + v[2] / 2 + v[3]);
    }
    return Math.max(0, m); };
  const SEL = 'a[href], button, input:not([type=hidden]), select, textarea, summary, [tabindex]:not([tabindex="-1"])';
  const caixas = [];
  for (const el of document.querySelectorAll(SEL)) {
    if (fora(el) || getComputedStyle(el).visibility !== 'visible' || opac(el) < 0.1) continue;
    const c = clip(el.parentElement || el);
    for (const q of el.getClientRects()) {
      const k = cortar(q, c);
      if (k) caixas.push({el, l: k.l, r: k.r, t: k.t + sy0, b: k.b + sy0, texto: (el.innerText || el.getAttribute('aria-label') || el.tagName).trim().replace(/\s+/g, ' ').slice(0, 60)});
    }
  }
  const col = [...document.querySelectorAll('.floating-btn')].map(b => b.getBoundingClientRect());
  const colL = Math.min(...col.map(q => q.left));
  for (const cx of caixas) {
    cx.anel = 0; cx.sombra = alcance(getComputedStyle(cx.el).boxShadow);
    if (colL - cx.r < 24) {
      cx.el.focus({focusVisible: true, preventScroll: true});
      const s = getComputedStyle(cx.el);
      cx.anel = Math.max(s.outlineStyle !== 'none' ? parseFloat(s.outlineOffset) + parseFloat(s.outlineWidth) : 0, alcance(s.boxShadow));
      cx.el.blur();
    }
  }
  window.scrollTo({top: sy0, behavior: 'instant'});
  // Superfícies dos cards de "Por que escolher" (Home).
  const superficies = [...document.querySelectorAll('.home-about-cards-grid > div')].map(el => {
    const q = el.getBoundingClientRect(); return {l: q.left, r: q.right, t: q.top + sy0, b: q.bottom + sy0, texto: el.innerText.trim().slice(0, 40)}; });
  // Título (H1 da matéria ou do herói institucional): palavras além da caixa de conteúdo e palavras partidas entre
  // linhas sem hífen opcional antes do ponto de quebra.
  const h1 = document.querySelector('main h1');
  let titulo = null;
  if (h1) {
    const s = getComputedStyle(h1), q = h1.getBoundingClientRect();
    const limite = q.right - parseFloat(s.paddingRight) - parseFloat(s.borderRightWidth);
    const r = document.createRange(); r.selectNodeContents(h1);
    const direita = Math.max(...[...r.getClientRects()].map(x => x.right));
    const partidas = [];
    const tw = document.createTreeWalker(h1, NodeFilter.SHOW_TEXT);
    let tn;
    while ((tn = tw.nextNode())) {
      const re = /\S+/g; let m;
      while ((m = re.exec(tn.textContent))) {
        let t0 = null, corte = -1;
        for (let i = m.index; i < m.index + m[0].length; i++) {
          const rc = document.createRange(); rc.setStart(tn, i); rc.setEnd(tn, i + 1);
          const qs2 = [...rc.getClientRects()].filter(z => z.width > 0); const qq = qs2.length ? qs2.reduce((a, z) => z.top > a.top ? z : a) : null;
          if (!qq) continue;
          if (t0 === null) t0 = qq.top; else if (qq.top - t0 > 2) { corte = i; break; }
        }
        if (corte > 0 && tn.textContent[corte - 1] !== '\u00ad' && tn.textContent[corte - 1] !== '-') partidas.push(m[0].replace(/\u00ad/g, ''));
      }
    }
    titulo = {direita, limite, partidas, texto: h1.textContent.replace(/\u00ad/g, '').trim().replace(/\s+/g, ' ').slice(0, 80)};
  }
  return {colL, colunas: col.map(q => ({l: q.left, r: q.right, t: q.top, b: q.bottom, w: q.width})),
          linhas: linhas, caixas: caixas.map(({el, ...x}) => x), superficies, titulo,
          scrollMax: document.documentElement.scrollHeight - innerHeight, larguraUtil: document.documentElement.clientWidth,
          overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          inter: [...document.fonts].some(f => f.family.replace(/["']/g, '') === 'Inter' && f.status === 'loaded')};
}
'''

FIM = r'''
async (y) => {
  window.scrollTo({top: y, behavior: 'instant'});
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  await new Promise(r => setTimeout(r, 450));
  const controles = [...document.querySelectorAll('.floating-btn')].map(b => { const q = b.getBoundingClientRect(), s = getComputedStyle(b);
    return {id: b.classList.contains('floating-btn--top') ? 'topo' : 'whatsapp', l: q.left, r: q.right, t: q.top, b: q.bottom,
            visivel: s.visibility === 'visible' && Number(s.opacity) > 0.99}; });
  return {scrollY, ancorada: document.querySelector('.floating-buttons').classList.contains('is-docked'), controles,
          col: controles.filter(c => c.visivel).map(({l, r, t, b}) => ({l, r, t, b}))};
}
'''

saida = []
with sync_playwright() as p:
    opcoes = {"headless": True}
    if barra:
        opcoes["ignore_default_args"] = ["--hide-scrollbars"]
    browser = p.chromium.launch(**opcoes)
    for largura, altura in janelas:
        for pagina in paginas:
            context = support.new_context(browser, fonts="local", viewport={"width": largura, "height": altura}, device_scale_factor=1)
            page = context.new_page()
            page.goto(base + pagina, wait_until="load")
            # /farmacia-popular/ preenche a tabela de municípios depois do load (fetch não segura o load) e a página
            # cresce; medir antes disso deixa MEDIR e FIM em alturas diferentes (corrida demonstrada em 12/10/2026,
            # com os dados atrasados no servidor). Espera o fim da carga dos dados; nas outras páginas não há #fp-loading.
            page.wait_for_function("() => { const l = document.getElementById('fp-loading'); return !l || l.classList.contains('hidden'); }")
            m = page.evaluate(MEDIR)
            # Repouso dos dois controles com o Voltar ao topo visível.
            page.evaluate("async () => { window.scrollTo({top: Math.min(400, document.documentElement.scrollHeight - innerHeight), behavior: 'instant'}); "
                          "await new Promise(r => setTimeout(r, 450)); }")
            repouso = page.evaluate("() => [...document.querySelectorAll('.floating-btn')].map(b => { const q = b.getBoundingClientRect(); "
                                    "return {id: b.classList.contains('floating-btn--top') ? 'topo' : 'whatsapp', l: q.left, r: q.right, t: q.top, b: q.bottom}; })")
            fim = page.evaluate(FIM, m["scrollMax"])
            saida.append({"pagina": pagina, "largura": largura, "altura": altura, "barra": barra, "medida": m, "repouso": repouso, "fim": fim})
            context.close()
    browser.close()
print(json.dumps(saida))
"""


@pytest.fixture(scope="module")
def medidas():
    server = _servidor()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        processos = [
            subprocess.Popen([sys.executable, "-c", PROBE, base, json.dumps(grupo), json.dumps(PAGINAS), "1" if barra else "0"],
                             stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=subprocess_env())
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
    return {(r["pagina"], r["largura"], r["altura"], r["barra"]): r for r in resultado}


def _janela(chave):
    pagina, largura, altura, barra = chave
    return f"{pagina} {largura}x{altura}{' barra' if barra else ''}"


def _faixas(r):
    """Faixa vertical (coordenadas do documento) que cada controle varre: do repouso com scrollY 0 (WhatsApp) ou 301
    (Voltar ao topo) até a posição real dele no scrollY máximo, ancorada ou não."""
    fim = r["fim"]
    sy = fim["scrollY"]
    faixas = []
    for c in r["repouso"]:
        e = next(x for x in fim["controles"] if x["id"] == c["id"])
        if c["id"] == "topo":
            if sy <= 300:
                continue
            faixas.append((c["t"] + 301, e["b"] + sy))
        else:
            faixas.append((c["t"], e["b"] + sy))
    return faixas


def _alcancavel(item, r):
    """A coluna alcança o item quando a faixa vertical dele cruza a varredura de algum controle (_faixas)."""
    return any(item["b"] > a and item["t"] < b for a, b in _faixas(r))


def _por_pagina(medidas, pagina):
    return {k: v for k, v in medidas.items() if k[0] == pagina}


@pytest.mark.parametrize("pagina", PAGINAS)
def test_texto_e_caixas_alcancaveis_terminam_antes_da_coluna(medidas, pagina):
    falhas = {}
    for chave, r in _por_pagina(medidas, pagina).items():
        m = r["medida"]
        assert m["inter"], f"Inter local não carregou: {_janela(chave)}"
        col_l = m["colL"]
        texto = [(round(col_l - x["r"], 2), x["texto"]) for x in m["linhas"]
                 if _alcancavel(x, r) and col_l - x["r"] < FOLGA_TEXTO - TOLERANCIA]
        caixas = [(round(col_l - x["r"], 2), round(max(FOLGA_TEXTO, x["anel"], x["sombra"]), 2), x["texto"]) for x in m["caixas"]
                  if _alcancavel(x, r) and col_l - x["r"] < max(FOLGA_TEXTO, x["anel"], x["sombra"]) - TOLERANCIA]
        if texto or caixas:
            falhas[_janela(chave)] = {"linhas": len(texto), "exemplos_linhas": sorted(texto)[:4],
                                       "caixas": len(caixas), "exemplos_caixas": sorted(caixas)[:4]}
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_fim_da_pagina_com_a_coluna_no_estado_real(medidas, pagina):
    falhas = {}
    for chave, r in _por_pagina(medidas, pagina).items():
        m, fim = r["medida"], r["fim"]
        sy = fim["scrollY"]
        hits = []
        for c in fim["col"]:
            for x in m["linhas"] + m["caixas"]:
                t, b = x["t"] - sy, x["b"] - sy
                if min(b, c["b"]) - max(t, c["t"]) > 0 and min(x["r"], c["r"]) - max(x["l"], c["l"]) > 0:
                    hits.append(x["texto"])
        if hits:
            falhas[_janela(chave)] = {"ancorada": fim["ancorada"], "intersecoes": len(hits), "exemplos": hits[:4]}
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)


def test_titulo_sem_palavra_alem_da_caixa_nem_partida_sem_hifen(medidas):
    falhas = {}
    for chave, r in medidas.items():
        t = r["medida"]["titulo"]
        if t and (t["direita"] > t["limite"] + 0.5 or t["partidas"]):
            falhas[_janela(chave)] = t
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)


def test_home_cards_de_por_que_escolher_e_seta_da_vitrine_fora_da_coluna(medidas):
    falhas = {}
    for chave, r in _por_pagina(medidas, "/").items():
        m = r["medida"]
        cards = [(round(m["colL"] - s["r"], 2), s["texto"]) for s in m["superficies"] if _alcancavel(s, r) and s["r"] > m["colL"] - TOLERANCIA]
        seta = [x for x in m["caixas"] if "›" in x["texto"] or "Próximo" in x["texto"] or "próximo" in x["texto"]]
        setas = [(round(m["colL"] - x["r"], 2), round(max(FOLGA_TEXTO, x["anel"], x["sombra"]), 2)) for x in seta
                 if m["colL"] - x["r"] < max(FOLGA_TEXTO, x["anel"], x["sombra"]) - TOLERANCIA]
        if cards or setas:
            falhas[_janela(chave)] = {"cards": cards[:3], "seta": setas}
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)


def test_controles_mantem_tamanho_e_posicao_e_sem_rolagem_horizontal(medidas):
    falhas = {}
    for chave, r in medidas.items():
        m = r["medida"]
        esperado = 44 if chave[1] <= 640 else 48
        larguras = sorted({round(c["w"], 2) for c in m["colunas"]})
        direita = max(c["r"] for c in m["colunas"])
        if larguras != [esperado] or abs(direita - (m["larguraUtil"] - 24)) > 0.5 or m["overflowX"] > 0:
            falhas[_janela(chave)] = {"larguras": larguras, "direita": direita, "larguraUtil": m["larguraUtil"], "overflowX": m["overflowX"]}
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)
