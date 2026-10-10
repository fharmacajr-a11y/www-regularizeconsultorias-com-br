"""Catálogo de Manuais e POPs: o resumo de cada card aparece inteiro, com altura natural, fora da coluna dos controles.

O resumo dos cards (.manuals-catalog-card p:not(.manuals-card-note)) tinha limite de três linhas (line-clamp com
overflow hidden). A reserva da faixa de Voltar ao topo e WhatsApp estreitou os cards, e o limite passou a esconder mais
palavras do que antes (a 320 px, "POPs,", "publicidade" e "obrigatória" no card de Farmácia Popular). Na revisão v2 do
layout comum (10/10/2026) o resumo não tem mais limite de linhas.

O teste abre o catálogo em cada janela (Inter local, rede dos testes) em três estados: como carrega, expandido pelo
botão "Ver mais documentos" (acionado pelo teclado) e recolhido de novo. Em cada card exibido, mede a exposição de cada
palavra: a área das caixas da palavra (Range.getClientRects) que fica dentro do recorte dos ancestrais com overflow
hidden ou clip, incluído o próprio parágrafo. Recorte por ancestral com overflow auto ou scroll (tabela rolável, janela
de carrossel) não esconde o texto, que a rolagem alcança; o teste separa os dois mecanismos e confere essa separação
num par de calibração (um bloco rolável e um bloco com line-clamp, montados e retirados durante a medida). Exige:

1. resumo: toda palavra exposta por inteiro, inclusive a última, e o parágrafo com altura natural (scrollHeight até
   clientHeight + 1 px, sem limite de linhas);
2. todo o texto do card exposto (título, selo, nota e botões) e cada linha terminando pelo menos 8 px antes da borda
   esquerda da coluna; as caixas clicáveis do card e o botão do catálogo terminando antes da coluna com folga de pelo
   menos max(8 px, contorno de foco, sombra visível), lidos no estado :focus-visible real;
3. expansão e recolhimento: aria-expanded, todos os cards exibidos depois de expandir, o mesmo número inicial depois
   de recolher, e nenhuma rolagem horizontal.

A contagem de reticências ou a presença de uma classe não entram no critério: só a geometria do texto exposto.
"""
import json
import subprocess
import sys
import threading

import pytest

from support import subprocess_env
from test_institucional_faixa_controles import _servidor


PAGINA = "/manuais-e-pops/"
JANELAS = ((320, 568), (375, 667), (768, 1024), (1024, 800), (1280, 900), (1440, 900))
JANELAS_BARRA = ((375, 667), (783, 1024), (1280, 900))
JANELAS_BAIXAS = ((568, 320), (740, 360), (812, 375), (915, 412))
GRUPOS = ((JANELAS, False), (JANELAS_BARRA, True), (JANELAS_BAIXAS, False))
FOLGA_TEXTO = 8.0
TOLERANCIA = 0.05
TOTAL_DE_CARDS = 10

PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, pagina, janelas, barra = sys.argv[1], sys.argv[2], json.loads(sys.argv[3]), sys.argv[4] == "1"

FUNCOES = r'''
(() => {
  // Recorte permanente: caixas de preenchimento dos ancestrais com overflow hidden ou clip (por eixo), do próprio
  // elemento para cima. A subida para no primeiro contêiner rolável (overflow auto ou scroll, fora body e html, cuja
  // rolagem é a da página): o conteúdo dele é alcançado pela rolagem e não conta como oculto; a caixa visível do
  // contêiner é devolvida para registrar as palavras que estão fora dela no momento (alcançáveis, não escondidas).
  const recorte = el => {
    let c = {l: -1e9, t: -1e9, r: 1e9, b: 1e9};
    const corta = v => v === 'hidden' || v === 'clip';
    const rola = v => v === 'auto' || v === 'scroll';
    for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
      const s = getComputedStyle(e);
      const q = e.getBoundingClientRect();
      const caixa = {l: q.left + parseFloat(s.borderLeftWidth), t: q.top + parseFloat(s.borderTopWidth),
                     r: q.right - parseFloat(s.borderRightWidth), b: q.bottom - parseFloat(s.borderBottomWidth)};
      if (e !== document.body && (rola(s.overflowX) || rola(s.overflowY))) return {c, rolavel: caixa};
      if (corta(s.overflowX)) c = {...c, l: Math.max(c.l, caixa.l), r: Math.min(c.r, caixa.r)};
      if (corta(s.overflowY)) c = {...c, t: Math.max(c.t, caixa.t), b: Math.min(c.b, caixa.b)};
    }
    return {c, rolavel: null};
  };
  const area = q => Math.max(0, q.width) * Math.max(0, q.height);
  const dentro = (q, c) => Math.max(0, Math.min(q.right, c.r) - Math.max(q.left, c.l)) * Math.max(0, Math.min(q.bottom, c.b) - Math.max(q.top, c.t));
  // Palavras de um elemento com a área total e a exposta (fora de SVG, script, style e .sr-only).
  const palavras = raiz => {
    const out = [];
    const w = document.createTreeWalker(raiz, NodeFilter.SHOW_TEXT);
    let n;
    while ((n = w.nextNode())) {
      const el = n.parentElement;
      if (!n.textContent.trim() || !el || el.closest('svg, script, style, .sr-only')) continue;
      const {c, rolavel} = recorte(el);
      const re = /\S+/g; let m;
      while ((m = re.exec(n.textContent))) {
        const r = document.createRange(); r.setStart(n, m.index); r.setEnd(n, m.index + m[0].length);
        const qs = [...r.getClientRects()].filter(q => q.width > 0 && q.height > 0);
        const total = qs.reduce((a, q) => a + area(q), 0), exposta = qs.reduce((a, q) => a + dentro(q, c), 0);
        out.push({w: m[0].replace(/­/g, ''), total, exposta, inteira: total > 0 && exposta >= total - 0.5,
                  caixas: qs.map(q => {
                    const l = Math.max(q.left, c.l), rr = Math.min(q.right, c.r), t = Math.max(q.top, c.t), b = Math.min(q.bottom, c.b);
                    return rr - l >= 0.5 && b - t >= 0.5 ? {l, r: rr, t, b} : null; }).filter(Boolean),
                  rolavel: !!rolavel,
                  na_rolagem: !!rolavel && qs.some(q => q.left < rolavel.l - 0.5 || q.right > rolavel.r + 0.5 || q.top < rolavel.t - 0.5 || q.bottom > rolavel.b + 0.5)});
      }
    }
    return out;
  };
  // Linhas do texto exposto de um elemento (caixas de palavra agrupadas por sobreposição vertical).
  const linhas = ps => {
    const ls = [];
    for (const q of ps.flatMap(p => p.caixas.map(k => ({...k, w: p.w}))).sort((x, y) => x.t - y.t || x.l - y.l)) {
      const ln = ls.find(x => Math.min(x.b, q.b) - Math.max(x.t, q.t) > 0.5 * Math.min(x.b - x.t, q.b - q.t));
      if (ln) { ln.l = Math.min(ln.l, q.l); ln.r = Math.max(ln.r, q.r); ln.t = Math.min(ln.t, q.t); ln.b = Math.max(ln.b, q.b); ln.p.push(q.w); }
      else ls.push({l: q.l, r: q.r, t: q.t, b: q.b, p: [q.w]});
    }
    return ls.map(x => ({l: x.l, r: x.r, t: x.t, b: x.b, texto: x.p.join(' ').slice(0, 60)}));
  };
  const alcance = txt => { if (!txt || txt === 'none') return 0; let m = 0;
    for (const parte of txt.split(/,(?![^(]*\))/)) {
      if (/inset/.test(parte)) continue;
      const cor = parte.match(/rgba?\([^)]*\)/); if (cor && /rgba\([^)]*,\s*0\)$/.test(cor[0])) continue;
      const v = (parte.replace(/rgba?\([^)]*\)/, '').match(/-?\d+(\.\d+)?px/g) || []).map(parseFloat).concat([0, 0, 0, 0]);
      m = Math.max(m, Math.abs(v[0]) + v[2] / 2 + v[3]);
    }
    return Math.max(0, m); };
  return {recorte, palavras, linhas, alcance};
})()
'''

MEDIR = r'''
async (estado) => {
  const F = __FUNCOES__;
  await document.fonts.ready;
  const quadro = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  for (let y = 0; y <= document.documentElement.scrollHeight; y += Math.max(200, innerHeight - 40)) {
    window.scrollTo({top: y, behavior: 'instant'}); await quadro();
  }
  window.scrollTo({top: 0, behavior: 'instant'}); await quadro(); await quadro();
  const col = [...document.querySelectorAll('.floating-btn')].map(b => b.getBoundingClientRect());
  const colL = Math.min(...col.map(q => q.left));
  const grade = document.getElementById('manuals-catalog-grid');
  const todos = [...grade.querySelectorAll('.manuals-catalog-card')];
  const cards = [];
  for (const card of todos) {
    if (getComputedStyle(card).display === 'none') continue;
    const titulo = card.querySelector('h3').textContent.replace(/­/g, '').trim().replace(/\s+/g, ' ');
    const p = card.querySelector('p:not(.manuals-card-note)');
    const sp = getComputedStyle(p);
    const ps = F.palavras(p);
    const ultima = ps[ps.length - 1];
    const qp = p.getBoundingClientRect();
    const texto = F.palavras(card);
    const caixas = [];
    for (const el of card.querySelectorAll('a[href], button')) {
      el.focus({focusVisible: true, preventScroll: true});
      const s = getComputedStyle(el);
      const anel = Math.max(s.outlineStyle !== 'none' ? parseFloat(s.outlineOffset) + parseFloat(s.outlineWidth) : 0, F.alcance(s.boxShadow));
      el.blur();
      const q = el.getBoundingClientRect();
      caixas.push({r: q.right, anel, sombra: F.alcance(getComputedStyle(el).boxShadow), texto: el.textContent.trim().slice(0, 30)});
    }
    cards.push({
      titulo,
      resumo: {
        palavras: ps.length, ocultas: ps.filter(x => !x.inteira).map(x => ({w: x.w, exposicao: x.total ? +(x.exposta / x.total).toFixed(3) : 0})),
        ultima: ultima ? {w: ultima.w, inteira: ultima.inteira, base: ultima.caixas.length ? Math.max(...ultima.caixas.map(k => k.b)) : null} : null,
        scrollHeight: p.scrollHeight, clientHeight: p.clientHeight, altura: qp.height, fundo: qp.bottom,
        lineClamp: sp.webkitLineClamp, overflow: sp.overflowY, display: sp.display,
        linhas: F.linhas(ps).length, texto: p.textContent.trim().replace(/\s+/g, ' '),
      },
      texto_oculto: texto.filter(x => !x.inteira).map(x => x.w),
      texto_na_rolagem: texto.filter(x => x.na_rolagem).map(x => x.w),
      linhas: F.linhas(texto).map(x => ({r: x.r, texto: x.texto})),
      caixas,
    });
  }
  const botao = document.querySelector('.manuals-catalog-toggle');
  let toggle = null;
  if (botao) {
    botao.focus({focusVisible: true, preventScroll: true});
    const s = getComputedStyle(botao);
    const q = botao.getBoundingClientRect();
    toggle = {r: q.right, anel: Math.max(s.outlineStyle !== 'none' ? parseFloat(s.outlineOffset) + parseFloat(s.outlineWidth) : 0, F.alcance(s.boxShadow)),
              sombra: F.alcance(s.boxShadow), focado: document.activeElement === botao, expandido: botao.getAttribute('aria-expanded'),
              rotulo: botao.textContent.trim(), sublinhado: s.textDecorationLine};
    botao.blur();
  }
  return {estado, colL, cards, exibidos: cards.length, total: todos.length, toggle,
          larguraUtil: document.documentElement.clientWidth, overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
          inter: [...document.fonts].some(f => f.family.replace(/["']/g, '') === 'Inter' && f.status === 'loaded')};
}
'''

# Par de calibração: o mesmo medidor precisa ver o texto de um bloco rolável como alcançável (não oculto) e o de um
# bloco com line-clamp como oculto.
CALIBRAR = r'''
async () => {
  const F = __FUNCOES__;
  const caixa = document.createElement('div');
  caixa.innerHTML = '<div id="cal-rola" style="overflow-x:auto;width:120px"><p style="white-space:nowrap;margin:0">tabela larga com palavras alcançadas pela rolagem horizontal</p></div>'
    + '<p id="cal-clamp" style="width:120px;display:-webkit-box;-webkit-box-orient:vertical;-webkit-line-clamp:2;overflow:hidden;margin:0">resumo longo com muitas palavras que passam do limite de duas linhas e ficam escondidas</p>';
  document.body.appendChild(caixa);
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  const rola = F.palavras(caixa.querySelector('#cal-rola')), clamp = F.palavras(caixa.querySelector('#cal-clamp'));
  caixa.remove();
  return {rolavel_oculto: rola.filter(x => !x.inteira).length, rolavel_alcancado: rola.filter(x => x.na_rolagem).length, rolavel_total: rola.length,
          clamp_oculto: clamp.filter(x => !x.inteira).length, clamp_total: clamp.length};
}
'''

MEDIR = MEDIR.replace("__FUNCOES__", FUNCOES.strip())
CALIBRAR = CALIBRAR.replace("__FUNCOES__", FUNCOES.strip())

saida = []
with sync_playwright() as p:
    opcoes = {"headless": True}
    if barra:
        opcoes["ignore_default_args"] = ["--hide-scrollbars"]
    browser = p.chromium.launch(**opcoes)
    for largura, altura in janelas:
        context = support.new_context(browser, fonts="local", viewport={"width": largura, "height": altura}, device_scale_factor=1)
        page = context.new_page()
        page.goto(base + pagina, wait_until="load")
        estados = [page.evaluate(MEDIR, "inicial")]
        if page.locator(".manuals-catalog-toggle").count():
            # Expansão e recolhimento pelo teclado: foco no botão e Enter, depois Espaço.
            page.focus(".manuals-catalog-toggle")
            page.keyboard.press("Enter")
            estados.append(page.evaluate(MEDIR, "expandido"))
            page.focus(".manuals-catalog-toggle")
            page.keyboard.press(" ")
            estados.append(page.evaluate(MEDIR, "recolhido"))
        calibracao = page.evaluate(CALIBRAR)
        saida.append({"largura": largura, "altura": altura, "barra": barra, "estados": estados, "calibracao": calibracao})
        context.close()
    browser.close()
print(json.dumps(saida))
"""


@pytest.fixture(scope="module")
def catalogo():
    server = _servidor()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        processos = [
            subprocess.Popen([sys.executable, "-c", PROBE, base, PAGINA, json.dumps(grupo), "1" if barra else "0"],
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
    assert len(resultado) == sum(len(g) for g, _ in GRUPOS)
    return resultado


def _janela(r, estado=None):
    return f"{r['largura']}x{r['altura']}{' barra' if r['barra'] else ''}" + (f" {estado['estado']}" if estado else "")


def test_medidor_separa_rolagem_de_recorte_permanente(catalogo):
    for r in catalogo:
        c = r["calibracao"]
        assert c["rolavel_oculto"] == 0 and c["rolavel_alcancado"] > 0, (_janela(r), c)
        assert 0 < c["clamp_oculto"] < c["clamp_total"], (_janela(r), c)


def test_resumos_do_catalogo_inteiros_com_altura_natural(catalogo):
    falhas = {}
    for r in catalogo:
        for e in r["estados"]:
            assert e["inter"], f"Inter local não carregou: {_janela(r, e)}"
            for card in e["cards"]:
                s = card["resumo"]
                problemas = {}
                if s["ocultas"]:
                    problemas["palavras_ocultas"] = s["ocultas"]
                if not s["ultima"] or not s["ultima"]["inteira"]:
                    problemas["ultima_palavra"] = s["ultima"]
                if s["scrollHeight"] > s["clientHeight"] + 1:
                    problemas["altura"] = {"scrollHeight": s["scrollHeight"], "clientHeight": s["clientHeight"]}
                if problemas:
                    falhas.setdefault(_janela(r, e), {})[card["titulo"][:60]] = problemas
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)


def test_texto_dos_cards_inteiro_e_fora_da_coluna(catalogo):
    falhas = {}
    for r in catalogo:
        for e in r["estados"]:
            col_l = e["colL"]
            for card in e["cards"]:
                ocultas = card["texto_oculto"]
                linhas = [(round(col_l - x["r"], 2), x["texto"]) for x in card["linhas"] if col_l - x["r"] < FOLGA_TEXTO - TOLERANCIA]
                caixas = [(round(col_l - x["r"], 2), round(max(FOLGA_TEXTO, x["anel"], x["sombra"]), 2), x["texto"]) for x in card["caixas"]
                          if col_l - x["r"] < max(FOLGA_TEXTO, x["anel"], x["sombra"]) - TOLERANCIA]
                if ocultas or linhas or caixas:
                    falhas.setdefault(_janela(r, e), {})[card["titulo"][:60]] = {"ocultas": ocultas[:8], "linhas": linhas[:4], "caixas": caixas}
            t = e["toggle"]
            if t and col_l - t["r"] < max(FOLGA_TEXTO, t["anel"], t["sombra"]) - TOLERANCIA:
                falhas.setdefault(_janela(r, e), {})["botão do catálogo"] = t
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)


def test_expansao_e_recolhimento_do_catalogo(catalogo):
    falhas = {}
    for r in catalogo:
        estados = {e["estado"]: e for e in r["estados"]}
        inicial = estados["inicial"]
        problemas = []
        if set(estados) != {"inicial", "expandido", "recolhido"}:
            problemas.append(("estados", sorted(estados)))
        else:
            exp, rec = estados["expandido"], estados["recolhido"]
            if inicial["total"] != TOTAL_DE_CARDS or not 3 <= inicial["exibidos"] < TOTAL_DE_CARDS:
                problemas.append(("inicial", inicial["exibidos"], inicial["total"]))
            if (inicial["toggle"]["expandido"], exp["toggle"]["expandido"], rec["toggle"]["expandido"]) != ("false", "true", "false"):
                problemas.append(("aria-expanded", inicial["toggle"]["expandido"], exp["toggle"]["expandido"], rec["toggle"]["expandido"]))
            if exp["exibidos"] != TOTAL_DE_CARDS or rec["exibidos"] != inicial["exibidos"]:
                problemas.append(("cards exibidos", inicial["exibidos"], exp["exibidos"], rec["exibidos"]))
            if not all(e["toggle"]["focado"] for e in (inicial, exp, rec)):
                problemas.append(("foco no botão", [e["toggle"]["focado"] for e in (inicial, exp, rec)]))
        for e in r["estados"]:
            if e["overflowX"] > 0:
                problemas.append(("rolagem horizontal", e["estado"], e["overflowX"]))
        if problemas:
            falhas[_janela(r)] = problemas
    assert not falhas, json.dumps(falhas, ensure_ascii=False, indent=1)
