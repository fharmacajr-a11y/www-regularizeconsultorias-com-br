"""Texto e alvos clicáveis de Sobre e Equipe ficam fora da coluna dos botões flutuantes.

Voltar ao topo e WhatsApp ficam fixos no canto direito. Até ~1390px a coluna
cai dentro do container, e as regras de pages/sobre.css e
pages/equipe-servicos.css (só Equipe) reservam a faixa. O teste abre as duas
páginas, junta as palavras de cada nó de texto do <main> (Range.getClientRects,
sem SVG, script, style e o título .sr-only) em linhas e mede as caixas de links
e botões do <main> (getClientRects). Linhas e caixas são recortadas pelos
ancestrais com overflow: só conta a parte exposta, e a coleta descarta
fragmentos menores que 0,5 px. O teste leva cada linha e cada caixa ao centro
de cada controle visível, rolando pelo que os retângulos atuais pedem, e mede de
novo tudo o que está na faixa. Falha com qualquer interseção de área positiva
entre uma linha ou caixa e um controle visível; não há tolerância na
interseção. Também mede, nos scrollY <= 300 que alinham um alvo com o Voltar ao
topo, a interseção com a caixa dele mesmo invisível (na transição de aparição só
a opacidade muda), e a chegada ao rodapé a cada 40 px nos últimos 400 px.

Os quatro casos do parecer da Fase 1Q são exigidos pelas mesmas palavras e pela
mesma caixa: em 375 x 667, "Ser referência nacional em consultoria de" (Sobre) e
"O atendimento da Regularize é distribuído entre" (Equipe); em 640 x 800, a caixa
inteira de "Conhecer os Serviços" no CTA final das duas páginas. Cada um passa
pela faixa do controle no scrollY que o centraliza e no scrollY registrado na
base.

A matriz cobre os limites das regras de página (359/360 px úteis, 639/640,
699/700, 819/820, 1023/1024, 1279/1280) e oito janelas com a barra de rolagem
clássica do Chromium (sem --hide-scrollbars): as media queries usam a largura
da janela, e o layout, a largura útil, menor. Também confere o tamanho e a
posição fixa dos controles, a ausência de rolagem horizontal, de linha fora da
caixa do próprio bloco, de palavra recortada por overflow e de ellipsis ou
line-clamp no <main>. Só o rodapé (comum a todas as páginas) fica fora. Um alvo
que não alcança a faixa (rolagem negativa, além do fim ou Voltar ao topo com
scrollY <= 300) fica como não aplicável, com o motivo.
"""
import json
import subprocess
import sys
import threading

import pytest

from support import subprocess_env
from test_institucional_faixa_controles import _servidor


JANELAS = (
    (320, 568), (359, 800), (360, 800), (375, 667), (639, 800), (640, 800), (699, 800), (700, 800),
    (768, 1024), (819, 900), (820, 900), (1023, 800), (1024, 800), (1279, 900), (1280, 900), (1440, 900),
)
# Com a barra clássica (15px): a menor largura útil (305px), 360px úteis (duas
# colunas de números), o CTA em 625px úteis, 753px úteis (botões do CTA lado a
# lado só com 768px úteis), 885px, 1009px, 1265px e 1376px úteis.
JANELAS_BARRA = ((320, 568), (375, 667), (640, 800), (768, 1024), (900, 900), (1024, 800), (1280, 900), (1391, 900))
GRUPOS = ((JANELAS[:3], False), (JANELAS[3:6], False), (JANELAS[6:9], False), (JANELAS[9:13], False),
          (JANELAS[13:], False), (JANELAS_BARRA[:4], True), (JANELAS_BARRA[4:], True))
PAGINAS = ("/sobre/", "/equipe/")
CASOS = {
    "sobre_visao_375": {"pagina": "/sobre/", "janela": [375, 667], "secao": ".about-principles-section",
                        "frase": "Ser referência nacional em consultoria de", "scrollY": 36},
    "equipe_atendimento_375": {"pagina": "/equipe/", "janela": [375, 667], "secao": ".team-overview-section",
                               "frase": "O atendimento da Regularize é distribuído entre", "scrollY": 18},
    "sobre_cta_640": {"pagina": "/sobre/", "janela": [640, 800],
                      "seletor": '.about-final-cta-section a[href="/servicos/"]', "scrollY": 3010},
    "equipe_cta_640": {"pagina": "/equipe/", "janela": [640, 800],
                       "seletor": '.institutional-cta-section a[href="/servicos/"]', "scrollY": 5881},
}

PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, janelas, paginas, casos = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3]), json.loads(sys.argv[4])
barra = sys.argv[5] == "1"
LIMIAR = 300

INIT = r'''
async () => {
  await document.fonts.ready;
  const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  await frame();
  const P = window.__p = {frame, sleep: ms => new Promise(r => setTimeout(r, ms))};
  const fora = el => el.closest('script, style, noscript, template, svg, footer, .floating-buttons, .sr-only');
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
  const cortar = (q, c) => {
    const l = Math.max(q.left, c.l), r = Math.min(q.right, c.r), t = Math.max(q.top, c.t), b = Math.min(q.bottom, c.b);
    return r - l >= 0.5 && b - t >= 0.5 ? {l, r, t, b} : null;
  };
  const SEM = {l: -1e9, t: -1e9, r: 1e9, b: 1e9};
  const els = [], idx = new Map(), palavras = [];
  const w = document.createTreeWalker(document.querySelector('main'), NodeFilter.SHOW_TEXT);
  let n;
  while ((n = w.nextNode())) {
    const el = n.parentElement;
    if (!n.textContent.trim() || !el || fora(el)) continue;
    if (!idx.has(el)) { idx.set(el, els.length); els.push(el); }
    const re = /\S+/g; let m;
    while ((m = re.exec(n.textContent))) palavras.push({n, a: m.index, b: m.index + m[0].length, e: idx.get(el), w: m[0]});
  }
  const rects = (u, c) => {
    const r = document.createRange(); r.setStart(u.n, u.a); r.setEnd(u.n, u.b);
    return [...r.getClientRects()].map(q => cortar(q, c)).filter(Boolean);
  };
  // Posição de documento de cada palavra (o layout não muda com a rolagem): filtra a faixa vertical.
  for (const u of palavras) {
    const qs = rects(u, SEM);
    u.dt = qs.length ? Math.min(...qs.map(q => q.t)) + scrollY : 1e9;
    u.db = qs.length ? Math.max(...qs.map(q => q.b)) + scrollY : -1e9;
  }
  P.linhas = (faixa = null) => {
    const porEl = new Map(), clips = new Map();
    palavras.forEach((u, i) => {
      if (faixa && (u.db < faixa[0] || u.dt > faixa[1])) return;
      const el = els[u.e];
      if (getComputedStyle(el).visibility !== 'visible') return;
      if (!clips.has(u.e)) clips.set(u.e, clip(el));
      for (const k of rects(u, clips.get(u.e))) { if (!porEl.has(u.e)) porEl.set(u.e, []); porEl.get(u.e).push({...k, i}); }
    });
    const out = [];
    for (const [e, qs] of porEl) {
      qs.sort((x, y) => x.t - y.t || x.l - y.l);
      const ls = [];
      for (const q of qs) {
        const ln = ls.find(x => Math.min(x.b, q.b) - Math.max(x.t, q.t) > 0.5 * Math.min(x.b - x.t, q.b - q.t));
        if (ln) { ln.l = Math.min(ln.l, q.l); ln.r = Math.max(ln.r, q.r); ln.t = Math.min(ln.t, q.t); ln.b = Math.max(ln.b, q.b); ln.i0 = Math.min(ln.i0, q.i); ln.i1 = Math.max(ln.i1, q.i); }
        else ls.push({l: q.l, r: q.r, t: q.t, b: q.b, i0: q.i, i1: q.i});
      }
      for (const x of ls) out.push({e, ...x, texto: palavras.slice(x.i0, x.i1 + 1).map(u => u.w).join(' ').slice(0, 70)});
    }
    return out;
  };
  // Caixa de cada link ou botão do <main>, na parte exposta (recortada pelo overflow dos ancestrais).
  const alvos = [...document.querySelectorAll('main a[href], main button')].filter(el => !fora(el));
  P.interativos = () => alvos.flatMap((el, k) => {
    const c = clip(el.parentElement);
    return [...el.getClientRects()].map(q => cortar(q, c)).filter(Boolean)
      .map(q => ({...q, k, texto: (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 50)}));
  });
  P.controles = () => {
    const col = document.querySelector('.floating-buttons');
    return [...document.querySelectorAll('.floating-btn')].map(el => {
      const s = getComputedStyle(el), r = el.getBoundingClientRect(), topo = el.classList.contains('floating-btn--top');
      return {id: topo ? 'topo' : 'whatsapp', l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height,
              posicao: getComputedStyle(col).position, ancorada: col.classList.contains('is-docked'), opacidade: Number(s.opacity),
              visivel: s.visibility === 'visible' && Number(s.opacity) >= 0.99 && !col.hasAttribute('inert')
                       && (!topo || el.classList.contains('is-visible'))};
    });
  };
  P.rolar = async y => {
    window.scrollTo({top: y, behavior: 'instant'});
    await frame();
    for (let k = 0; k < 12; k++) {
      const topo = P.controles().find(c => c.id === 'topo');
      if (Math.abs(topo.opacidade - (scrollY > 300 ? 1 : 0)) < 0.001) break;
      await P.sleep(60); await frame();
    }
    return scrollY;
  };
  P.transbordos = () => {
    const bloco = el => { let e = el; while (['inline', 'contents'].includes(getComputedStyle(e).display)) e = e.parentElement; return e; };
    return P.linhas().filter(x => {
      const b = bloco(els[x.e]), q = b.getBoundingClientRect(), s = getComputedStyle(b);
      return x.r > q.right - parseFloat(s.borderRightWidth) - parseFloat(s.paddingRight) + 0.5
          || x.l < q.left + parseFloat(s.borderLeftWidth) + parseFloat(s.paddingLeft) - 0.5;
    }).map(x => x.texto);
  };
  // Conferência independente de corte: palavra cuja parte exposta é menor que a palavra inteira.
  P.cortes = () => palavras.filter(u => {
    const area = qs => qs.reduce((s, q) => s + (q.r - q.l) * (q.b - q.t), 0);
    return area(rects(u, SEM)) - area(rects(u, clip(els[u.e]))) > 0.5;
  }).map(u => u.w);
  P.elipses = () => [...document.querySelectorAll('main *')].filter(el => {
    const s = getComputedStyle(el);
    return s.textOverflow === 'ellipsis' || (s.webkitLineClamp && s.webkitLineClamp !== 'none');
  }).map(el => String(el.className).slice(0, 60));
  P.frase = (secao, frase) => {
    const alvo = frase.split(/\s+/), sec = document.querySelector(secao);
    for (let i = 0; i + alvo.length <= palavras.length; i++)
      if (sec.contains(els[palavras[i].e]) && alvo.every((x, k) => palavras[i + k].w === x)) return [i, i + alvo.length - 1];
    return null;
  };
  P.caixa = sel => { const el = document.querySelector(sel), q = el.getBoundingClientRect();
                     return {k: alvos.indexOf(el), t: q.top + scrollY, b: q.bottom + scrollY, r: q.right}; };
  return [...document.fonts].some(f => f.family.replace(/["']/g, '') === 'Inter' && f.status === 'loaded');
}
'''

MEDIR = r'''
async ([y, geo]) => {
  const P = window.__p;
  const ef = await P.rolar(y);
  const cs = P.controles(), vis = cs.filter(c => c.visivel || (geo && c.id === 'topo'));
  const hits = [];
  if (vis.length) {
    const t0 = Math.min(...vis.map(c => c.t)) - 40 + ef, b0 = Math.max(...vis.map(c => c.b)) + 40 + ef;
    for (const [tipo, itens] of [['texto', P.linhas([t0, b0])], ['interativo', P.interativos()]]) {
      for (const q of itens) for (const c of vis) {
        const ix = Math.min(q.r, c.r) - Math.max(q.l, c.l), iy = Math.min(q.b, c.b) - Math.max(q.t, c.t);
        if (ix > 0 && iy > 0) hits.push({tipo, controle: c.id, texto: q.texto, i0: q.i0 ?? null, i1: q.i1 ?? null, k: q.k ?? null,
                                         interX: ix, interY: iy, l: q.l, r: q.r});
      }
    }
  }
  return {scrollY: ef, controles: cs, hits};
}
'''


def centro(q, c):
    return (q["t"] + q["b"]) / 2 - (c["t"] + c["b"]) / 2


def motivo(y, cid, maximo):
    return ("rolagem negativa" if y < 0 else "alem do fim" if y > maximo
            else "topo exige scrollY > 300" if cid == "topo" and round(y) <= LIMIAR else None)


def executado(m, cid, t, b):
    c = next(k for k in m["controles"] if k["id"] == cid)
    vo = min(b - m["scrollY"], c["b"]) - max(t - m["scrollY"], c["t"])
    return "executado" if c["visivel"] and vo >= 1 else ("ancorada" if c["posicao"] == "absolute" else "incompleto")


def caso(page, chave, cfg, repouso, maximo):
    out = {"caso": chave, "medidas": []}
    if "frase" in cfg:
        faixa = page.evaluate("([s, f]) => window.__p.frase(s, f)", [cfg["secao"], cfg["frase"]])
        out["palavras"] = faixa
        if not faixa:
            return out
        i0, i1 = faixa
        dentro = lambda h: h["tipo"] == "texto" and h["i1"] >= i0 and h["i0"] <= i1
        linhas = [x for x in page.evaluate("() => window.__p.linhas().map(x => ({i0: x.i0, i1: x.i1, t: x.t + scrollY, b: x.b + scrollY}))")
                  if x["i1"] >= i0 and x["i0"] <= i1]
        alvos = [(x["t"], x["b"]) for x in linhas]
    else:
        q = page.evaluate("s => window.__p.caixa(s)", cfg["seletor"])
        out["caixa"] = q
        dentro = lambda h: h["tipo"] == "interativo" and h["k"] == q["k"]
        alvos = [(q["t"], q["b"])]
    m = page.evaluate(MEDIR, [cfg["scrollY"], False])
    out["registrado"] = {"scrollY": m["scrollY"], "hits": [h for h in m["hits"] if dentro(h)]}
    for t, b in alvos:
        for cid in ("whatsapp", "topo"):
            y = centro({"t": t, "b": b}, repouso[cid])
            if motivo(y, cid, maximo):
                out["medidas"].append({"controle": cid, "status": motivo(y, cid, maximo)})
                continue
            m = page.evaluate(MEDIR, [round(y), False])
            out["medidas"].append({"controle": cid, "scrollY": m["scrollY"], "status": executado(m, cid, t, b),
                                   "hits": [h for h in m["hits"] if dentro(h)]})
    return out


saida = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, ignore_default_args=["--hide-scrollbars"] if barra else None)
    for largura, altura in janelas:
        for pagina in paginas:
            context = support.new_context(browser, viewport={"width": largura, "height": altura}, device_scale_factor=1)
            page = context.new_page()
            page.goto(base + pagina, wait_until="load")
            inter = page.evaluate(INIT)
            maximo = page.evaluate("() => document.documentElement.scrollHeight - innerHeight")
            overflow = page.evaluate("() => document.documentElement.scrollWidth - document.documentElement.clientWidth")
            transbordos = page.evaluate("() => window.__p.transbordos()")
            cortes = page.evaluate("() => window.__p.cortes()")
            elipses = page.evaluate("() => window.__p.elipses()")
            page.evaluate("async y => { await window.__p.rolar(y); }", min(400, maximo))
            repouso = {c["id"]: c for c in page.evaluate("() => window.__p.controles()")}
            linhas = page.evaluate("() => window.__p.linhas().map(x => ({t: x.t + scrollY, b: x.b + scrollY}))")
            itens = page.evaluate("() => window.__p.interativos().map(x => ({t: x.t + scrollY, b: x.b + scrollY}))")
            cenarios, ys, transicao = [], set(), set()
            for tipo, lista in (("texto", linhas), ("interativo", itens)):
                for q in lista:
                    for cid in ("whatsapp", "topo"):
                        y = centro(q, repouso[cid])
                        reg = {"tipo": tipo, "controle": cid, "t": q["t"], "b": q["b"], "y": round(y),
                               "status": motivo(y, cid, maximo) or "pendente"}
                        if reg["status"] == "pendente":
                            ys.add(round(y))
                        elif reg["status"] == "topo exige scrollY > 300":
                            transicao.add(round(y))
                        cenarios.append(reg)
            medidas = {y: page.evaluate(MEDIR, [y, False]) for y in sorted(ys)}
            for reg in cenarios:
                if reg["status"] == "pendente":
                    reg["status"] = executado(medidas[reg["y"]], reg["controle"], reg["t"], reg["b"])
            hits = {}
            for m in medidas.values():
                for h in m["hits"]:
                    hits.setdefault((h["tipo"], h["controle"], h["texto"]), {**h, "scrollY": m["scrollY"]})
            geo = [{**h, "scrollY": m["scrollY"]} for m in (page.evaluate(MEDIR, [y, True]) for y in sorted(transicao))
                   for h in m["hits"] if h["controle"] == "topo"]
            fim, ancorada = [], {}
            for y in sorted(set(range(max(0, maximo - 400), maximo + 1, 40)) | {maximo}):
                m = page.evaluate(MEDIR, [y, False])
                ancorada[m["scrollY"]] = any(c["ancorada"] for c in m["controles"])
                fim += [{**h, "scrollY": m["scrollY"]} for h in m["hits"]]
            saida.append({"largura": largura, "altura": altura, "pagina": pagina, "barra": barra, "inter": inter,
                          "larguraUtil": page.evaluate("document.documentElement.clientWidth"), "overflowX": overflow,
                          "transbordos": transbordos, "cortes": cortes, "elipses": elipses, "repouso": repouso,
                          "hits": list(hits.values()), "transicaoTopo": geo, "fim": fim, "ancorada": ancorada,
                          "status": [r["status"] for r in cenarios],
                          "casos": [caso(page, k, c, repouso, maximo) for k, c in casos.items()
                                    if not barra and c["pagina"] == pagina and c["janela"] == [largura, altura]]})
            context.close()
    browser.close()
print(json.dumps(saida))
"""


@pytest.fixture(scope="module")
def faixa():
    server = _servidor()
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        processos = [
            subprocess.Popen(
                [sys.executable, "-c", PROBE, base, json.dumps(grupo), json.dumps(PAGINAS), json.dumps(CASOS), "1" if barra else "0"],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=subprocess_env(),
            )
            for grupo, barra in GRUPOS
        ]
        saidas = [processo.communicate(timeout=1200) for processo in processos]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    resultado = []
    for processo, (stdout, stderr) in zip(processos, saidas):
        assert processo.returncode == 0, stderr[-4000:]
        resultado.extend(json.loads(stdout))
    return {(r["pagina"], r["largura"], r["altura"], r["barra"]): r for r in resultado}


def _resumo(hits):
    return [(h["tipo"], h["controle"], (h["texto"] or "")[:50], round(h["interX"], 2), round(h["interY"], 2), h.get("scrollY"))
            for h in hits]


def _janela(chave):
    pagina, largura, altura, barra = chave
    return f"{pagina} {largura}x{altura}{' barra' if barra else ''}"


def _mensagem(falhas):
    # Texto, uma linha por janela: o pytest encurtaria a representação de um dicionário.
    return f"{len(falhas)} janela(s) com falha:\n" + "\n".join(f"{k}: {v}" for k, v in falhas.items())


@pytest.mark.parametrize("chave", sorted(CASOS))
def test_casos_do_parecer_mesmas_palavras_e_mesma_caixa(faixa, chave):
    cfg = CASOS[chave]
    janela = faixa[(cfg["pagina"], cfg["janela"][0], cfg["janela"][1], False)]
    assert janela["inter"] is True
    resultado = next(c for c in janela["casos"] if c["caso"] == chave)
    if "frase" in cfg:
        assert resultado["palavras"], f"{chave}: frase não encontrada"
    # As mesmas palavras (ou a mesma caixa) passam de fato pela faixa do WhatsApp.
    assert any(m["controle"] == "whatsapp" and m["status"] == "executado" for m in resultado["medidas"]), resultado["medidas"]
    assert all(m["status"] in ("executado", "rolagem negativa", "alem do fim", "topo exige scrollY > 300")
               for m in resultado["medidas"]), resultado["medidas"]
    atingidos = resultado["registrado"]["hits"] + [h for m in resultado["medidas"] for h in m.get("hits", [])]
    assert atingidos == [], (chave, _resumo(atingidos))


@pytest.mark.parametrize("pagina", PAGINAS)
def test_texto_e_caixas_do_main_fora_da_coluna(faixa, pagina):
    falhas = {}
    for (p, largura, altura, barra), janela in sorted(faixa.items()):
        if p != pagina:
            continue
        if barra:
            assert janela["larguraUtil"] < largura, (largura, "a barra clássica não apareceu")
        assert janela["inter"] is True, largura
        assert "executado" in janela["status"], (largura, "nenhum cenário alcançou a faixa")
        assert "incompleto" not in janela["status"], (largura, janela["status"].count("incompleto"))
        for controle in janela["repouso"].values():
            tamanho = 44 if largura <= 640 else 48
            assert controle["w"] == pytest.approx(tamanho, abs=0.1) and controle["h"] == pytest.approx(tamanho, abs=0.1)
            assert controle["posicao"] == "fixed", (largura, controle)
        if janela["hits"]:
            falhas[_janela((p, largura, altura, barra))] = {"intersecoes": len(janela["hits"]), "exemplos": _resumo(janela["hits"][:4])}
    assert falhas == {}, _mensagem(falhas)


@pytest.mark.parametrize("pagina", PAGINAS)
def test_transicao_do_voltar_ao_topo_e_chegada_ao_rodape(faixa, pagina):
    falhas = {}
    for chave, janela in sorted(faixa.items()):
        if chave[0] != pagina:
            continue
        assert janela["ancorada"], chave
        hits = janela["transicaoTopo"] + janela["fim"]
        if hits:
            falhas[_janela(chave)] = {"intersecoes": len(hits), "exemplos": _resumo(hits[:4])}
    assert falhas == {}, _mensagem(falhas)


def test_sem_rolagem_horizontal_texto_cortado_ou_fora_do_bloco(faixa):
    for chave, janela in sorted(faixa.items()):
        assert janela["overflowX"] <= 0, chave
        assert janela["transbordos"] == [], (chave, janela["transbordos"][:5])
        assert janela["cortes"] == [], (chave, janela["cortes"][:5])
        assert janela["elipses"] == [], (chave, janela["elipses"][:5])
