"""Texto e alvos clicáveis da Home e de Serviços ficam fora da coluna dos botões flutuantes.

Voltar ao topo e WhatsApp ficam fixos no canto direito. Até ~1390px a coluna
cai dentro do container, e as regras de pages/home.css e
pages/equipe-servicos.css reservam a faixa. O teste abre as duas páginas,
junta as palavras de cada nó de texto do <main> (Range.getClientRects, sem
SVG, script e style) em linhas e mede as caixas de links e botões do <main>
(getClientRects). Linhas e caixas são recortadas pelos ancestrais com
overflow: só conta a parte exposta, e o que está fora da janela do carrossel
não conta. O teste leva cada linha e cada caixa ao centro de cada controle
visível, rolando pelo que os retângulos atuais pedem, e mede de novo tudo o
que está na faixa. Falha com qualquer interseção de área positiva entre uma
linha ou caixa e um controle visível; não há tolerância. Também confere as
linhas que saem da caixa de conteúdo do próprio bloco e a rolagem horizontal
da página. Quatro janelas rodam com a barra de rolagem clássica do Chromium
(sem --hide-scrollbars): as media queries usam a largura da janela, e o
layout, a largura útil, menor.

A vitrine de Manuais da Home rola na horizontal, e o que aparece na faixa
depende da posição. Em cada janela o teste confere que a janela do carrossel
termina antes da coluna e percorre os estados: cada posição de encaixe, em
cada altura que leva uma linha ou um card da vitrine ao centro de um
controle; avanço até o fim e retorno pelas setas, medindo cada quadro do
movimento; foco de cada card pelo teclado (Tab e Shift+Tab), com o card
inteiro na janela; e rolagem horizontal pela roda do mouse, também quadro a
quadro.

Só o rodapé (comum a todas as páginas) fica fora. Uma linha ou caixa que não
alcança a faixa (rolagem negativa, além do fim ou Voltar ao topo com
scrollY <= 300) fica como não aplicável, com o motivo.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env


JANELAS = (
    (320, 568), (375, 667), (639, 800), (640, 800),
    (768, 1024), (960, 768), (1024, 800), (1280, 900),
)
# Com a barra de rolagem clássica: a menor largura útil (305px), limite do CTA
# (880px úteis), título da vitrine em 1024px e, em 1360px, o container já com margem.
JANELAS_BARRA = ((320, 568), (890, 900), (1024, 800), (1360, 900))
GRUPOS = ((JANELAS[:2], False), (JANELAS[2:5], False), (JANELAS[5:], False),
          (JANELAS_BARRA[:2], True), (JANELAS_BARRA[2:], True))
PAGINAS = ("/", "/servicos/")
# Casos da Fase 1O v2 em 375x667: cards Polícia Federal (Home) e SNCR (Serviços).
CASOS = {"/": ".home-services-grid > a:nth-child(3)", "/servicos/": "#servico-sncr"}
# Portas que o Chromium recusa (net::ERR_UNSAFE_PORT) e que a porta 0 pode sortear.
PORTAS_RECUSADAS = {5060, 5061, 6000, 6566, 6665, 6666, 6667, 6668, 6669, 6697, 10080}

PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, janelas, paginas, casos = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3]), json.loads(sys.argv[4])
barra = sys.argv[5] == "1"

INIT = r'''
async () => {
  await document.fonts.ready;
  const frame = () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)));
  await frame();
  const P = window.__p = {frame, sleep: ms => new Promise(r => setTimeout(r, ms))};
  const fora = el => el.closest('script, style, noscript, template, svg, footer, .floating-buttons');
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
  const todas = palavras.map((_, i) => i);
  // recortar = false dá a posição da linha mesmo fora da janela do carrossel.
  P.linhas = (ids = todas, recortar = true) => {
    const porEl = new Map(), clips = new Map();
    for (const i of ids) {
      const u = palavras[i], el = els[u.e];
      if (getComputedStyle(el).visibility !== 'visible') continue;
      if (!clips.has(u.e)) clips.set(u.e, recortar ? clip(el) : SEM);
      const r = document.createRange(); r.setStart(u.n, u.a); r.setEnd(u.n, u.b);
      for (const q of r.getClientRects()) {
        const k = cortar(q, clips.get(u.e));
        if (k) { if (!porEl.has(u.e)) porEl.set(u.e, []); porEl.get(u.e).push({...k, i}); }
      }
    }
    const out = [];
    for (const [e, qs] of porEl) {
      qs.sort((x, y) => x.t - y.t || x.l - y.l);
      const ls = [];
      for (const q of qs) {
        const ln = ls.find(x => Math.min(x.b, q.b) - Math.max(x.t, q.t) > 0.5 * Math.min(x.b - x.t, q.b - q.t));
        if (ln) { ln.l = Math.min(ln.l, q.l); ln.r = Math.max(ln.r, q.r); ln.t = Math.min(ln.t, q.t); ln.b = Math.max(ln.b, q.b); ln.i1 = Math.max(ln.i1, q.i); }
        else ls.push({l: q.l, r: q.r, t: q.t, b: q.b, i0: q.i, i1: q.i});
      }
      for (const x of ls) out.push({e, ...x, texto: palavras.slice(x.i0, x.i1 + 1).map(u => u.w).join(' ').slice(0, 70)});
    }
    return out;
  };
  // Caixa de cada link ou botão do <main>, na parte exposta (recortada pelo overflow dos ancestrais).
  P.interativos = () => [...document.querySelectorAll('main a[href], main button')]
    .filter(el => !fora(el))
    .flatMap(el => { const c = clip(el.parentElement); return [...el.getClientRects()].map(q => cortar(q, c)).filter(Boolean)
      .map(q => ({...q, texto: (el.innerText || el.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 50)})); });
  P.controles = () => {
    const col = document.querySelector('.floating-buttons');
    return [...document.querySelectorAll('.floating-btn')].map(el => {
      const s = getComputedStyle(el), r = el.getBoundingClientRect(), topo = el.classList.contains('floating-btn--top');
      return {id: topo ? 'topo' : 'whatsapp', l: r.left, r: r.right, t: r.top, b: r.bottom, w: r.width, h: r.height,
              posicao: getComputedStyle(col).position, opacidade: Number(s.opacity),
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
  P.alvo = sel => { const el = document.querySelector(sel); return P.linhas().filter(x => el.contains(els[x.e])).map(x => x.i0); };

  // Vitrine de Manuais: linhas e caixas dos cards na posição horizontal do momento.
  const car = document.querySelector('.home-manuals-carousel');
  if (car) {
    const cards = [...car.querySelectorAll('.home-manuals-card')];
    const ids = todas.filter(i => car.contains(els[palavras[i].e]));
    const V = P.v = {car, cards};
    V.janela = () => clip(car);
    V.itens = () => {
      const j = clip(car);
      const out = P.linhas(ids).map(x => ({tipo: 'texto', l: x.l, r: x.r, t: x.t, b: x.b, texto: x.texto}));
      cards.forEach((el, k) => { const q = cortar(el.getBoundingClientRect(), j); if (q) out.push({tipo: 'interativo', ...q, texto: 'card ' + (k + 1)}); });
      return out;
    };
    // Posições de documento de todas as linhas e cards, inclusive fora da janela.
    V.alvos = () => [...P.linhas(ids, false).map(x => ({t: x.t + scrollY, b: x.b + scrollY})),
                     ...cards.map(el => { const q = el.getBoundingClientRect(); return {t: q.top + scrollY, b: q.bottom + scrollY, card: true}; })];
    V.medir = () => {
      const vis = P.controles().filter(c => c.visivel), j = clip(car), hits = [];
      let emFaixa = 0;
      for (const q of V.itens()) for (const c of vis) {
        const iy = Math.min(q.b, c.b) - Math.max(q.t, c.t), ix = Math.min(q.r, c.r) - Math.max(q.l, c.l);
        if (iy >= 1) emFaixa++;
        if (ix > 0 && iy > 0) hits.push({tipo: q.tipo, controle: c.id, texto: q.texto, interX: ix, interY: iy, l: q.l, r: q.r});
      }
      return {sl: car.scrollLeft, sy: scrollY, hits, emFaixa, controles: vis.map(c => c.id), janela: [j.l, j.r]};
    };
    // scrollLeft de cada card no encaixe: borda inicial no início da janela, menos o scroll-padding.
    V.encaixes = () => {
      const q0 = car.getBoundingClientRect(), sp = parseFloat(getComputedStyle(car).scrollPaddingLeft) || 0;
      const max = car.scrollWidth - car.clientWidth;
      const xs = cards.map(c => Math.min(max, Math.max(0, car.scrollLeft + c.getBoundingClientRect().left - q0.left - sp)));
      return [...new Set(xs.map(x => Math.round(x * 100) / 100))].sort((a, b) => a - b);
    };
    V.matriz = async (ys, xs) => {
      const res = {medidas: 0, comFaixa: {}, hits: [], desvios: []};
      for (const y of ys) {
        await P.rolar(y);
        for (const x of xs) {
          car.scrollTo({left: x, behavior: 'instant'});
          const m = V.medir();
          res.medidas++;
          if (Math.abs(m.sl - x) > 1) res.desvios.push([x, m.sl]);
          if (m.emFaixa) for (const c of m.controles) res.comFaixa[c] = (res.comFaixa[c] || 0) + 1;
          for (const h of m.hits) res.hits.push({...h, sy: m.sy, sl: m.sl});
        }
      }
      car.scrollTo({left: 0, behavior: 'instant'});
      return res;
    };
    // Mede a cada quadro até a rolagem horizontal assentar (ou não começar).
    V.amostrar = limite => new Promise(resolve => {
      const quadros = [], t0 = performance.now();
      let ult = car.scrollLeft, mudou = false, desde = t0;
      const passo = () => {
        const agora = performance.now(), m = V.medir();
        if (Math.abs(m.sl - ult) > 0.01) { mudou = true; desde = agora; }
        ult = m.sl;
        quadros.push(m);
        if ((mudou && agora - desde > 400) || (!mudou && agora - t0 > 350) || agora - t0 > limite) {
          const a = document.activeElement, k = cards.indexOf(a), j = clip(car);
          const q = k >= 0 ? a.getBoundingClientRect() : null;
          resolve({mudou, sl: car.scrollLeft, quadros: quadros.length, sls: [...new Set(quadros.map(z => Math.round(z.sl)))].length,
                   hits: quadros.flatMap(z => z.hits.map(h => ({...h, sy: z.sy, sl: z.sl}))),
                   emFaixa: quadros.filter(z => z.emFaixa).length, foco: k,
                   focoInteiro: q ? q.left >= j.l - 0.5 && q.right <= j.r + 0.5 : null});
        } else requestAnimationFrame(passo);
      };
      requestAnimationFrame(passo);
    });
  }
  return [...document.fonts].some(f => f.family.replace(/["']/g, '') === 'Inter' && f.status === 'loaded');
}
'''

MEDIR = r'''
async y => {
  const P = window.__p;
  const ef = await P.rolar(y);
  const cs = P.controles(), vis = cs.filter(c => c.visivel);
  const hits = [];
  for (const [tipo, itens] of [['texto', P.linhas()], ['interativo', P.interativos()]]) {
    for (const q of itens) for (const c of vis) {
      const ix = Math.min(q.r, c.r) - Math.max(q.l, c.l), iy = Math.min(q.b, c.b) - Math.max(q.t, c.t);
      if (ix > 0 && iy > 0) hits.push({tipo, controle: c.id, texto: q.texto, i0: q.i0 ?? null, interX: ix, interY: iy, l: q.l, r: q.r});
    }
  }
  return {scrollY: ef, controles: cs, hits};
}
'''


def faixa_y(alvos, repouso, maximo):
    # scrollY que leva o centro de cada alvo ao centro de cada controle; os que não alcançam ficam de fora, com o motivo.
    ys, fora = set(), {}
    for q in alvos:
        for cid in ("whatsapp", "topo"):
            c = repouso[cid]
            y = (q["t"] + q["b"]) / 2 - (c["t"] + c["b"]) / 2
            motivo = ("rolagem negativa" if y < 0 else "alem do fim" if y > maximo
                      else "topo exige scrollY > 300" if cid == "topo" and round(y) <= 300 else None)
            if motivo:
                fora[motivo] = fora.get(motivo, 0) + 1
            else:
                ys.add(round(y))
    return sorted(ys), fora


def clicar_e_amostrar(page, acao):
    page.evaluate("() => { window.__amostra = window.__p.v.amostrar(5000); }")
    acao()
    return page.evaluate("() => window.__amostra")


def vitrine(page, maximo, repouso):
    v = page.evaluate("() => { const V = window.__p.v; return V && {n: V.cards.length, encaixes: V.encaixes(),"
                      " max: V.car.scrollWidth - V.car.clientWidth, janela: V.janela()}; }")
    if not v:
        return None
    alvos = page.evaluate("() => window.__p.v.alvos()")
    ys, fora = faixa_y(alvos, repouso, maximo)
    v["naoAplicaveis"] = fora
    v["matriz"] = page.evaluate("([ys, xs]) => window.__p.v.matriz(ys, xs)", [ys, v["encaixes"]])
    v["alturas"] = len(ys)
    # Altura de referência: o centro da coluna no centro do primeiro card.
    card = next(q for q in alvos if q.get("card"))
    meio = (repouso["topo"]["t"] + repouso["whatsapp"]["b"]) / 2
    y = round(min(maximo, max(301, (card["t"] + card["b"]) / 2 - meio)))
    v["alturaReferencia"] = y
    preparar = "async y => { await window.__p.rolar(y); window.__p.v.car.scrollTo({left: 0, behavior: 'instant'}); await window.__p.frame(); }"

    # Setas: avança até a seta não mover mais e volta ao início.
    page.evaluate(preparar, y)
    setas = {}
    for nome, sel in (("avanco", "[data-home-manuals-next]"), ("retorno", "[data-home-manuals-prev]")):
        ponto = page.evaluate("s => { const q = document.querySelector(s).getBoundingClientRect(); const x = q.left + q.width / 2,"
                              " y = q.top + q.height / 2; return {x, y, alvo: !!document.elementFromPoint(x, y)?.closest(s)}; }", sel)
        passos = []
        for _ in range(v["n"] + 2):
            r = clicar_e_amostrar(page, lambda: page.mouse.click(ponto["x"], ponto["y"]))
            passos.append(r)
            if not r["mudou"]:
                break
        setas[nome] = {"alvo": ponto["alvo"], "passos": passos}
    v["setas"] = setas

    # Teclado: da seta anterior, Tab por todos os cards e Shift+Tab de volta.
    page.evaluate(preparar, y)
    page.evaluate("() => document.querySelector('[data-home-manuals-prev]').focus({preventScroll: true})")
    teclado = []
    for tecla in ["Tab"] * v["n"] + ["Shift+Tab"] * (v["n"] - 1):
        r = clicar_e_amostrar(page, lambda: page.keyboard.press(tecla))
        # Com o card focado, a coluna volta ao centro dos cards e mede de novo.
        r["alinhado"] = page.evaluate("async y => { await window.__p.rolar(y); return window.__p.v.medir(); }", y)
        r["tecla"] = tecla
        teclado.append(r)
    v["teclado"] = teclado

    # Roda do mouse na horizontal, sobre o primeiro card: cada giro passa de
    # meio card, e o encaixe completa o movimento.
    page.evaluate(preparar, y)
    ponto = page.evaluate("() => { const j = window.__p.v.janela(), [a, b] = window.__p.v.cards.map(c => c.getBoundingClientRect());"
                          " return {x: (j.l + Math.min(j.r, a.right)) / 2, y: a.top + a.height / 3, passo: b.left - a.left}; }")
    page.mouse.move(ponto["x"], ponto["y"])
    giro = round(ponto["passo"] * 0.6)
    roda = []
    for dx in (giro, giro, giro, -giro, -giro, -giro):
        roda.append(clicar_e_amostrar(page, lambda: page.mouse.wheel(dx, 0)))
    v["roda"] = roda
    return v


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
            page.evaluate("async y => { await window.__p.rolar(y); }", min(400, maximo))
            repouso = {c["id"]: c for c in page.evaluate("() => window.__p.controles()")}
            linhas = page.evaluate("() => window.__p.linhas().map(x => ({i0: x.i0, t: x.t + scrollY, b: x.b + scrollY}))")
            itens = page.evaluate("() => window.__p.interativos().map(x => ({t: x.t + scrollY, b: x.b + scrollY}))")
            caso = page.evaluate("s => window.__p.alvo(s)", casos[pagina]) if (largura, altura) == (375, 667) else []
            cenarios, ys = [], set()
            for tipo, lista in (("texto", linhas), ("interativo", itens)):
                for q in lista:
                    for cid in ("whatsapp", "topo"):
                        c = repouso[cid]
                        y = (q["t"] + q["b"]) / 2 - (c["t"] + c["b"]) / 2
                        reg = {"tipo": tipo, "controle": cid, "i0": q.get("i0"), "t": q["t"], "b": q["b"], "y": round(y)}
                        if y < 0:
                            reg["status"] = "rolagem negativa"
                        elif y > maximo:
                            reg["status"] = "alem do fim"
                        elif cid == "topo" and round(y) <= 300:
                            reg["status"] = "topo exige scrollY > 300"
                        else:
                            reg["status"] = "pendente"
                            ys.add(round(y))
                        cenarios.append(reg)
            medidas = {y: page.evaluate(MEDIR, y) for y in sorted(ys)}
            for reg in cenarios:
                if reg["status"] != "pendente":
                    continue
                m = medidas[reg["y"]]
                c = next(k for k in m["controles"] if k["id"] == reg["controle"])
                vo = min(reg["b"] - m["scrollY"], c["b"]) - max(reg["t"] - m["scrollY"], c["t"])
                reg["status"] = "executado" if c["visivel"] and vo >= 1 else ("ancorada" if c["posicao"] == "absolute" else "incompleto")
            hits = {}
            for m in medidas.values():
                for h in m["hits"]:
                    hits.setdefault((h["tipo"], h["controle"], h["texto"]), {**h, "scrollY": m["scrollY"]})
            saida.append({"largura": largura, "altura": altura, "pagina": pagina, "barra": barra, "inter": inter,
                          "larguraUtil": page.evaluate("document.documentElement.clientWidth"), "overflowX": overflow,
                          "transbordos": transbordos, "repouso": repouso, "hits": list(hits.values()),
                          "caso": [r for r in cenarios if r["tipo"] == "texto" and r["i0"] in caso],
                          "status": [r["status"] for r in cenarios],
                          "vitrine": vitrine(page, maximo, repouso) if pagina == "/" else None})
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


def _resumo(hits):
    return [(h["tipo"], h["controle"], h["texto"][:50], round(h["interX"], 2), h.get("scrollY", h.get("sy")), h.get("sl"))
            for h in hits]


def _janela(chave):
    pagina, largura, altura, barra = chave
    return f"{pagina} {largura}x{altura}{' barra' if barra else ''}"


def _falhas(falhas, chave, hits):
    # Junta as interseções de todas as janelas antes de falhar: a mensagem mostra cada janela atingida.
    if hits:
        falhas[_janela(chave)] = {"intersecoes": len(hits), "exemplos": _resumo(hits[:4])}


def _mensagem(falhas):
    # Texto, uma linha por janela: o pytest encurtaria a representação de um dicionário.
    return f"{len(falhas)} janela(s) com interseção:\n" + "\n".join(f"{k}: {v}" for k, v in falhas.items())


@pytest.mark.parametrize("pagina", PAGINAS)
def test_casos_da_fase_1o_em_375(faixa, pagina):
    janela = faixa[(pagina, 375, 667, False)]
    assert janela["inter"] is True
    caso = janela["caso"]
    assert caso, f"{pagina}: card do caso de origem sem linhas de texto"
    # Cada linha do card passa de fato pela faixa dos dois controles.
    assert {c["status"] for c in caso} == {"executado"}, caso
    linhas = {c["i0"] for c in caso}
    atingidas = [h for h in janela["hits"] if h["tipo"] == "texto" and h["i0"] in linhas]
    assert atingidas == [], (pagina, _resumo(atingidas))


@pytest.mark.parametrize("pagina", PAGINAS)
def test_texto_e_controles_do_main_fora_da_coluna(faixa, pagina):
    falhas = {}
    for (p, largura, altura, barra), janela in sorted(faixa.items()):
        if p != pagina:
            continue
        if barra:
            assert janela["larguraUtil"] < largura, (largura, "a barra clássica não apareceu")
        assert janela["inter"] is True, largura
        executados = [s for s in janela["status"] if s == "executado"]
        assert executados, (largura, "nenhum cenário alcançou a faixa")
        assert "incompleto" not in janela["status"], (largura, janela["status"].count("incompleto"))
        for controle in janela["repouso"].values():
            tamanho = 44 if largura <= 640 else 48
            assert controle["w"] == pytest.approx(tamanho, abs=0.1) and controle["h"] == pytest.approx(tamanho, abs=0.1)
            assert controle["posicao"] == "fixed", (largura, controle)
        _falhas(falhas, (p, largura, altura, barra), janela["hits"])
    assert falhas == {}, _mensagem(falhas)


def test_sem_rolagem_horizontal_nem_texto_fora_do_bloco(faixa):
    for chave, janela in sorted(faixa.items()):
        assert janela["overflowX"] <= 0, chave
        assert janela["transbordos"] == [], (chave, janela["transbordos"][:5])


def _vitrines(faixa):
    return [(chave, janela["vitrine"]) for chave, janela in sorted(faixa.items()) if chave[0] == "/"]


def test_vitrine_janela_e_posicoes_de_encaixe(faixa):
    falhas = {}
    for chave, v in _vitrines(faixa):
        assert v and v["n"] >= 2, chave
        m = v["matriz"]
        assert m["medidas"] == v["alturas"] * len(v["encaixes"]) and m["desvios"] == [], (chave, m["desvios"][:5])
        assert set(m["comFaixa"]) == {"whatsapp", "topo"}, (chave, m["comFaixa"])
        # A janela do carrossel termina antes da coluna: nada dentro dela alcança os controles.
        coluna = min(c["l"] for c in faixa[chave]["repouso"].values())
        if v["janela"]["r"] > coluna:
            falhas.setdefault(_janela(chave), {})["janela"] = {"direita": v["janela"]["r"], "coluna": coluna}
        if m["hits"]:
            falhas.setdefault(_janela(chave), {}).update(intersecoes=len(m["hits"]), exemplos=_resumo(m["hits"][:4]))
    assert falhas == {}, _mensagem(falhas)


def test_vitrine_setas_avancam_e_voltam_sem_cobrir_os_controles(faixa):
    falhas = {}
    for chave, v in _vitrines(faixa):
        avanco, retorno = v["setas"]["avanco"], v["setas"]["retorno"]
        assert avanco["alvo"] and retorno["alvo"], chave
        finais = [p["sl"] for p in avanco["passos"]]
        # Cada clique leva a uma posição de encaixe; o último não move (fim da vitrine).
        assert len(avanco["passos"]) >= 2 and not avanco["passos"][-1]["mudou"], (chave, finais)
        assert all(p["mudou"] for p in avanco["passos"][:-1]), (chave, finais)
        assert finais[-1] == pytest.approx(v["max"], abs=1), (chave, finais, v["max"])
        assert all(min(abs(x - e) for e in v["encaixes"]) <= 1 for x in finais), (chave, finais, v["encaixes"])
        assert retorno["passos"][-1]["sl"] == pytest.approx(0, abs=1) and not retorno["passos"][-1]["mudou"], chave
        passos = avanco["passos"] + retorno["passos"]
        # Quadros intermediários medidos durante o movimento, com os cards na faixa dos controles.
        assert sum(p["sls"] for p in passos) > len(passos) * 2, (chave, [p["sls"] for p in passos])
        assert all(p["emFaixa"] for p in passos if p["mudou"]), chave
        _falhas(falhas, chave, [h for p in passos for h in p["hits"]])
    assert falhas == {}, _mensagem(falhas)


def test_vitrine_foco_pelo_teclado_mostra_o_card_inteiro(faixa):
    falhas = {}
    for chave, v in _vitrines(faixa):
        teclado = v["teclado"]
        n = v["n"]
        # Tab passa pelos cards em ordem; Shift+Tab volta até o primeiro.
        assert [t["foco"] for t in teclado] == list(range(n)) + list(range(n - 2, -1, -1)), (chave, [t["foco"] for t in teclado])
        assert all(t["focoInteiro"] for t in teclado), (chave, [(t["foco"], t["sl"]) for t in teclado if not t["focoInteiro"]])
        assert all(t["alinhado"]["emFaixa"] for t in teclado), chave
        _falhas(falhas, chave, [h for t in teclado for h in t["hits"] + [{**x, "sl": t["alinhado"]["sl"]} for x in t["alinhado"]["hits"]]])
    assert falhas == {}, _mensagem(falhas)


def test_vitrine_rolagem_horizontal_pela_roda(faixa):
    falhas = {}
    for chave, v in _vitrines(faixa):
        roda = v["roda"]
        assert any(r["mudou"] for r in roda[:3]) and any(r["mudou"] for r in roda[3:]), (chave, [r["sl"] for r in roda])
        assert all(r["emFaixa"] for r in roda if r["mudou"]), chave
        _falhas(falhas, chave, [h for r in roda for h in r["hits"]])
    assert falhas == {}, _mensagem(falhas)
