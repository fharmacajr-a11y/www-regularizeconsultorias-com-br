"""Título e resumo dos cards da listagem ficam fora da faixa dos botões flutuantes.

A reserva é uma regra de #news-article-list em pages/noticias.css, com o recuo
do modelo único dos cards (2px de borda e padding de 1.5rem, ou 2rem a partir de 768px; até 12/10/2026 eram 1px e 1.25rem; até 11/10/2026
havia também o formato destaque nos cinco primeiros, com border-2, p-6 e md:p-8). O teste abre /noticias/, clica em "Ver mais notícias", leva
cada linha real do texto (Range.getClientRects) à faixa vertical de cada botão
visível, rolando a página pelo que os retângulos atuais pedem, e mede a folga
horizontal até o botão. Presença de seletor não basta.

Folga mínima: 8 px (a 0,5rem da regra). Tolerância numérica: 0,5 px, só para
arredondamento de subpixel; a folga zero não passa. Uma linha que não alcança a
faixa (rolagem negativa, além do fim, ou Voltar ao topo com scrollY <= 300)
fica como "nao_aplicavel", com o motivo, e não conta como aprovada.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env


FOLGA_MINIMA = 8.0
TOLERANCIA_PX = 0.5
CASO_DE_ORIGEM = "Anvisa descontinua Sicert para certificados de dispositivos médicos"
JANELAS = (
    (360, 800), (390, 844), (640, 800), (767, 1024), (768, 1024),
    (960, 900), (1024, 800), (1359, 900), (1360, 900), (1440, 900),
)
GRUPOS = (JANELAS[:5], JANELAS[5:])
# Cards medidos: os cinco primeiros da carga e três revelados por "Ver mais notícias".
PRIMEIROS = range(0, 5)
REVELADOS = range(5, 8)

PROBE = r"""
import json
import sys
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright
import support

base, janelas, alvos, caso = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3]), sys.argv[4]

INIT = r'''
async () => {
  document.documentElement.style.scrollBehavior = 'auto';
  window.__f = {
    frame: () => new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))),
    sleep: ms => new Promise(r => setTimeout(r, ms)),
    cards() { return [...document.querySelectorAll('#news-article-list [data-news-card]')]; },
    linhas(el) {
      const rects = [];
      const w = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let n;
      while ((n = w.nextNode())) {
        if (!n.textContent.trim()) continue;
        const r = document.createRange();
        r.selectNodeContents(n);
        for (const q of r.getClientRects()) if (q.width >= 0.5 && q.height >= 0.5) rects.push({l: q.left, r: q.right, t: q.top, b: q.bottom});
        r.detach();
      }
      rects.sort((a, b) => a.t - b.t || a.l - b.l);
      const out = [];
      for (const q of rects) {
        const ln = out.find(x => Math.min(x.b, q.b) - Math.max(x.t, q.t) > 0.5 * Math.min(x.b - x.t, q.b - q.t));
        if (ln) { ln.l = Math.min(ln.l, q.l); ln.r = Math.max(ln.r, q.r); ln.t = Math.min(ln.t, q.t); ln.b = Math.max(ln.b, q.b); }
        else out.push({...q});
      }
      return out;
    },
    controles() {
      const col = document.querySelector('.floating-buttons');
      const inert = !!(col && col.hasAttribute('inert'));
      return [...document.querySelectorAll('.floating-btn')].map(el => {
        const s = getComputedStyle(el), r = el.getBoundingClientRect();
        const topo = el.classList.contains('floating-btn--top');
        return {id: topo ? 'topo' : 'whatsapp', l: r.left, r: r.right, t: r.top, b: r.bottom, opacidade: Number(s.opacity),
                visivel: !inert && s.visibility === 'visible' && Number(s.opacity) >= 0.99 && r.width >= 2 && r.height >= 2
                         && (!topo || el.classList.contains('is-visible'))};
      });
    }
  };
  await document.fonts.ready;
  return [...document.fonts].some(f => f.family.replace(/["']/g, '') === 'Inter' && f.status === 'loaded');
}
'''

LEITURA = r'''
([i, sel]) => {
  const card = window.__f.cards()[i];
  const el = card.querySelector(sel);
  const r = el.getBoundingClientRect();
  const pr = parseFloat(getComputedStyle(el).paddingRight) || 0;
  const cs = getComputedStyle(card);
  const cardConteudo = card.getBoundingClientRect().right - parseFloat(cs.borderRightWidth) - parseFloat(cs.paddingRight);
  return {titulo: card.dataset.title, compacto: card.classList.contains('news-card-compact'),
          w: r.width, h: r.height, paddingRight: pr, reservaDireita: cardConteudo - pr,
          linhas: window.__f.linhas(el).map(q => ({t: q.t + scrollY, b: q.b + scrollY, r: q.r}))};
}
'''

CENARIO = r'''
async ([i, sel, li, cid, y]) => {
  const F = window.__f;
  const max = document.documentElement.scrollHeight - innerHeight;
  let ctrls = [], linhas = [], ln = null, c = null, vo = -1;
  for (let k = 0; k < 4; k++) {
    window.scrollTo(0, y);
    await F.frame();
    ctrls = F.controles();
    if (ctrls.some(q => q.opacidade > 0.01 && q.opacidade < 0.99) || ctrls.some(q => q.id === 'topo' && scrollY > 300 && !q.visivel)) {
      await F.sleep(380); await F.frame(); ctrls = F.controles();
    }
    linhas = F.linhas(F.cards()[i].querySelector(sel));
    ln = linhas[li]; c = ctrls.find(q => q.id === cid);
    vo = Math.min(ln.b, c.b) - Math.max(ln.t, c.t);
    if (vo >= 1) break;
    y = Math.max(0, Math.min(max, scrollY + (ln.t + ln.b) / 2 - (c.t + c.b) / 2));
  }
  const pares = [];
  for (const q of linhas) for (const k of ctrls.filter(x => x.visivel)) {
    const v = Math.min(q.b, k.b) - Math.max(q.t, k.t);
    if (v > 0) pares.push({controle: k.id, folga: k.l - q.r, interX: Math.min(q.r, k.r) - Math.max(q.l, k.l), interY: v});
  }
  return {scrollY, sobreposicao: vo, controleVisivel: !!(c && c.visivel), controleL: c ? c.l : null, pares};
}
'''

saida = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for largura, altura in janelas:
        context = support.new_context(browser, allow=(base,), viewport={"width": largura, "height": altura}, device_scale_factor=1)
        page = context.new_page()
        page.goto(base + "/noticias/", wait_until="load")
        inter = page.evaluate(INIT)
        estado = "() => ({cards: window.__f.cards().length, visiveis: window.__f.cards().filter(c => !c.classList.contains('hidden')).length, destaques: window.__f.cards().filter(c => !c.classList.contains('hidden') && !c.classList.contains('news-card-compact')).length, ordem: window.__f.cards().map(c => c.dataset.title), overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth})"
        antes = page.evaluate(estado)
        page.get_by_role("button", name="Ver mais notícias").click()
        page.wait_for_function("() => window.__f.cards().every(c => !c.classList.contains('hidden'))", timeout=5000)
        depois = page.evaluate(estado)
        page.evaluate("async () => { window.scrollTo(0, 400); await window.__f.frame(); await window.__f.sleep(380); }")
        repouso = {c["id"]: c for c in page.evaluate("() => window.__f.controles()")}
        indices = list(alvos)
        origem = next((n for n, t in enumerate(depois["ordem"]) if t == caso), None)
        if origem is not None and origem not in indices:
            indices.append(origem)
        cenarios, caixas = [], []
        for i in indices:
            for elemento, sel in (("titulo", "h2"), ("resumo", "p")):
                info = page.evaluate(LEITURA, [i, sel])
                caixas.append({"card": i, "elemento": elemento, "compacto": info["compacto"], "titulo": info["titulo"],
                               "w": info["w"], "h": info["h"], "paddingRight": info["paddingRight"],
                               "folgaReserva": repouso["whatsapp"]["l"] - info["reservaDireita"]})
                for li, linha in enumerate(info["linhas"]):
                    for cid in ("whatsapp", "topo"):
                        c = repouso[cid]
                        y = (linha["t"] + linha["b"]) / 2 - (c["t"] + c["b"]) / 2
                        reg = {"card": i, "titulo": info["titulo"], "compacto": info["compacto"], "elemento": elemento,
                               "linha": li, "controle": cid, "scrollCalculado": y}
                        if y < 0:
                            reg.update(status="nao_aplicavel", motivo="rolagem negativa", linha_t=linha["t"], faixa_t=c["t"])
                        elif y > page.evaluate("() => document.documentElement.scrollHeight - innerHeight"):
                            reg.update(status="nao_aplicavel", motivo="alem do fim", linha_t=linha["t"])
                        elif cid == "topo" and y <= 301:
                            reg.update(status="nao_aplicavel", motivo="topo exige scrollY > 300", linha_t=linha["t"], faixa_t=c["t"])
                        else:
                            med = page.evaluate(CENARIO, [i, sel, li, cid, y])
                            ok = med["controleVisivel"] and med["sobreposicao"] >= 1 and bool(med["pares"])
                            reg.update(med, status="executado" if ok else "incompleto")
                        cenarios.append(reg)
        clique = None
        if (largura, altura) in ((768, 1024), (360, 800)):
            i = origem if largura == 768 else 0
            card = page.locator("#news-article-list [data-news-card]").nth(i)
            link = card.locator("a[href]").first
            link.scroll_into_view_if_needed()
            page.evaluate("() => window.__f.frame()")
            href = link.get_attribute("href")
            caixa = link.bounding_box()
            visivel = page.evaluate(
                "([x, y, href]) => { const e = document.elementFromPoint(x, y); const a = e && e.closest('a'); return !!(a && a.getAttribute('href') === href); }",
                [caixa["x"] + caixa["width"] / 2, caixa["y"] + caixa["height"] / 2, href])
            link.click()
            page.wait_for_url("**" + href, timeout=10000)
            clique = {"card": i, "href": href, "centroNoLink": visivel, "aberta": urlsplit(page.url).path}
        saida.append({"largura": largura, "altura": altura, "inter": inter, "antes": antes, "depois": depois,
                      "origem": origem, "cenarios": cenarios, "caixas": caixas, "clique": clique})
        context.close()
    browser.close()
print(json.dumps(saida))
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def faixa():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    alvos = json.dumps(list(PRIMEIROS) + list(REVELADOS))
    try:
        processos = [
            subprocess.Popen(
                [sys.executable, "-c", PROBE, base, json.dumps(grupo), alvos, CASO_DE_ORIGEM],
                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, encoding="utf-8", env=subprocess_env(),
            )
            for grupo in GRUPOS
        ]
        saidas = [processo.communicate(timeout=420) for processo in processos]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    janelas = []
    for processo, (stdout, stderr) in zip(processos, saidas):
        assert processo.returncode == 0, stderr[-4000:]
        janelas.extend(json.loads(stdout))
    return {(j["largura"], j["altura"]): j for j in janelas}


def _falhas(cenarios):
    falhas = []
    for c in cenarios:
        if c["status"] != "executado":
            continue
        for par in c["pares"]:
            if (par["interX"] > 0 and par["interY"] > 0) or par["folga"] < FOLGA_MINIMA - TOLERANCIA_PX:
                falhas.append((c["titulo"][:50], c["elemento"], c["linha"], c["controle"], round(par["folga"], 2)))
    return falhas


def test_caso_de_origem_compacto_768(faixa):
    janela = faixa[(768, 1024)]
    assert janela["inter"] is True
    assert janela["origem"] is not None, "o card do caso de origem não está na listagem"
    titulo = [c for c in janela["cenarios"] if c["card"] == janela["origem"] and c["elemento"] == "titulo"]
    assert titulo and all(c["compacto"] for c in titulo)
    caixa = next(c for c in janela["caixas"] if c["card"] == janela["origem"] and c["elemento"] == "titulo")
    assert caixa["w"] > 0 and caixa["h"] > 0
    for controle in ("whatsapp", "topo"):
        executados = [c for c in titulo if c["controle"] == controle and c["status"] == "executado"]
        assert executados, (controle, titulo)
        for c in executados:
            assert c["sobreposicao"] >= 1 and c["scrollY"] > 300
    assert _falhas(titulo) == []


def test_titulos_e_resumos_fora_da_faixa_dos_botoes(faixa):
    for (largura, altura), janela in faixa.items():
        assert janela["inter"] is True, largura
        assert [c for c in janela["cenarios"] if c["status"] == "incompleto"] == [], largura
        assert _falhas(janela["cenarios"]) == [], (largura, _falhas(janela["cenarios"]))
        executados = [c for c in janela["cenarios"] if c["status"] == "executado"]
        # Os cinco primeiros do resultado são o modelo maior; do sexto em diante, o compacto.
        assert all((c["card"] >= 5) == c["compacto"] for c in janela["cenarios"]), largura
        assert any(c["card"] < 5 for c in executados) and any(c["card"] >= 5 for c in executados), largura
        for c in janela["cenarios"]:
            if c["status"] == "nao_aplicavel":
                assert c["motivo"] in ("rolagem negativa", "alem do fim", "topo exige scrollY > 300"), c


def test_reserva_do_modelo_unico_e_cessa_no_desktop(faixa):
    # folgaReserva: do fim do conteúdo do card, menos o padding-right do texto,
    # até o botão. Abaixo de 1280px o container não tem margem e a reserva é
    # exata (8 px); de 1360px em diante ela é zero.
    for (largura, altura), janela in faixa.items():
        for caixa in janela["caixas"]:
            assert caixa["w"] > 0 and caixa["h"] > 0
            if largura >= 1360:
                assert caixa["paddingRight"] == pytest.approx(0, abs=0.01), (largura, caixa)
                assert caixa["folgaReserva"] >= FOLGA_MINIMA - TOLERANCIA_PX, (largura, caixa)
            elif largura < 1280:
                assert FOLGA_MINIMA - TOLERANCIA_PX <= caixa["folgaReserva"] <= FOLGA_MINIMA + TOLERANCIA_PX, (largura, caixa)
            else:
                assert caixa["folgaReserva"] >= FOLGA_MINIMA - TOLERANCIA_PX, (largura, caixa)


def test_listagem_contagem_ordem_e_cliques(faixa):
    for (largura, altura), janela in faixa.items():
        assert janela["antes"]["cards"] == 83
        # "destaques" conta os cards visíveis sem news-card-compact: com o modelo único (12/10/2026) não há nenhum.
        assert janela["antes"]["visiveis"] == 5 and janela["antes"]["destaques"] == 5
        assert janela["depois"]["visiveis"] == 83 and janela["depois"]["destaques"] == 5
        assert janela["antes"]["ordem"] == janela["depois"]["ordem"]
        assert janela["depois"]["overflowX"] <= 0, largura
    ordens = {tuple(j["depois"]["ordem"]) for j in faixa.values()}
    assert len(ordens) == 1
    for chave in ((768, 1024), (360, 800)):
        clique = faixa[chave]["clique"]
        assert clique["centroNoLink"] is True, clique
        assert clique["aberta"] == clique["href"], clique
