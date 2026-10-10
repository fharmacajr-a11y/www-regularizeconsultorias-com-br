"""O corpo da notícia não entra debaixo dos botões flutuantes.

A reserva é uma regra de .article-body na folha compartilhada pelas duas
famílias. O teste mede a caixa de cada caractere não branco, com a página
rolada e o alvo na faixa dos controles. Presença de seletor não basta.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import ROOT, SITE_DIR, subprocess_env


MAIN = (
    ("farmacopeia", "/noticias/novos-compendios-farmacopeia-brasileira-entram-em-vigor/", "custom.min.css"),
    ("mapa", "/noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/", "modular"),
)
SAMPLES = (
    ("hmp", "/noticias/anvisa-hmp-solicita-medicamentos-produtos-biologicos/", "custom.min.css"),
    ("informativo", "/noticias/anvisa-camara-tecnica-cosmetovigilancia/", "custom.min.css"),
    ("orientacao", "/noticias/crf-responsavel-tecnico-farmacias-drogarias/", "modular"),
    ("urgente", "/noticias/anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026/", "modular"),
    ("tabela", "/noticias/anvisa-in-470-2026-suplementos-ingredientes-limites-alegacoes/", "modular"),
    ("duas-folhas", "/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/", "ambas"),
)
MAIN_WIDTHS = (320, 360, 390, 639, 640, 641, 767, 768, 896, 950, 960, 1023, 1024, 1279, 1280, 1440)
SAMPLE_WIDTHS = (390, 768, 960, 1440)
TITULOS = (
    "Qual resolução aprova cada compêndio",
    "O que a Portaria determinou",
)

PROBE = r"""
import json
import sys
from playwright.sync_api import sync_playwright
import support

base, jobs_json = sys.argv[1], sys.argv[2]
jobs = json.loads(jobs_json)

MEASURE = r'''
async () => {
  document.documentElement.style.scrollBehavior = 'auto';
  await document.fonts.ready;
  const folhas = [...document.querySelectorAll('link[rel="stylesheet"]')].map(el => el.getAttribute('href') || '');
  function buttons() {
    return [...document.querySelectorAll('.floating-btn')].filter(el => {
      const s = getComputedStyle(el);
      const r = el.getBoundingClientRect();
      if (s.visibility === 'hidden' || Number(s.opacity) === 0 || r.width < 2 || r.height < 2) return false;
      if (el.classList.contains('floating-btn--top') && !el.classList.contains('is-visible')) return false;
      return true;
    });
  }
  function clip(rect, el) {
    let box = {left: rect.left, right: rect.right, top: rect.top, bottom: rect.bottom};
    let node = el.parentElement;
    while (node && node !== document.body) {
      const s = getComputedStyle(node);
      const mode = s.overflow + s.overflowX + s.overflowY;
      if (/auto|hidden|clip|scroll/.test(mode)) {
        const r = node.getBoundingClientRect();
        box.left = Math.max(box.left, r.left);
        box.right = Math.min(box.right, r.right);
        box.top = Math.max(box.top, r.top);
        box.bottom = Math.min(box.bottom, r.bottom);
      }
      node = node.parentElement;
    }
    return box;
  }
  function hits(el, btns) {
    const found = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    let textNode;
    while ((textNode = walker.nextNode())) {
      const text = textNode.textContent || '';
      for (let i = 0; i < text.length; i++) {
        if (!text[i].trim()) continue;
        const range = document.createRange();
        range.setStart(textNode, i);
        range.setEnd(textNode, i + 1);
        for (const rect of range.getClientRects()) {
          const box = clip(rect, textNode.parentElement || el);
          if (box.right - box.left <= 0.5 || box.bottom - box.top <= 0.5) continue;
          for (const b of btns) {
            const br = b.getBoundingClientRect();
            const ix = Math.min(box.right, br.right) - Math.max(box.left, br.left);
            const iy = Math.min(box.bottom, br.bottom) - Math.max(box.top, br.top);
            if (ix > 0.5 && iy > 0.5) found.push({ch: text[i], controle: b.getAttribute('aria-label') || '', ix: +ix.toFixed(2), iy: +iy.toFixed(2)});
          }
        }
        range.detach();
      }
    }
    return found;
  }
  async function alinhar(el) {
    const frame = () => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
    if (!el) return {status: 'ausente'};
    const antes = el.getBoundingClientRect();
    if (antes.width < 2 || antes.height < 2) return {status: 'incompleto', motivo: 'caixa zero'};
    let y = antes.top + window.scrollY + Math.min(antes.height, 40) / 2 - window.innerHeight * 0.72;
    const maxScroll = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
    if (y < 0) return {status: 'nao_aplicavel', motivo: 'rolagem negativa'};
    if (y > maxScroll + 2) return {status: 'nao_aplicavel', motivo: 'alvo alem do fim'};
    window.scrollTo(0, Math.min(Math.max(y, 0), maxScroll));
    await frame();
    for (let i = 0; i < 4; i++) {
      const btns = buttons();
      if (!btns.length) break;
      const rects = btns.map(b => b.getBoundingClientRect());
      const top = Math.min(...rects.map(r => r.top));
      const bottom = Math.max(...rects.map(r => r.bottom));
      const er = el.getBoundingClientRect();
      const delta = (er.top + Math.min(er.height, 40) / 2) - ((top + bottom) / 2);
      if (Math.abs(delta) <= 12) break;
      if (window.scrollY + delta < 0) return {status: 'nao_aplicavel', motivo: 'rolagem negativa'};
      window.scrollTo(0, Math.min(window.scrollY + delta, maxScroll));
      await frame();
    }
    const btns = buttons();
    const labels = btns.map(b => b.getAttribute('aria-label') || '');
    const ambos = labels.some(t => t.includes('topo')) && labels.some(t => t.includes('WhatsApp'));
    if (window.scrollY <= 300 || !ambos) {
      return {status: 'incompleto', motivo: 'controle ausente ou scrollY <= 300', scrollY: +window.scrollY.toFixed(1), botoes: labels};
    }
    const er = el.getBoundingClientRect();
    if (er.width < 2 || er.height < 2) return {status: 'incompleto', motivo: 'caixa zero', scrollY: +window.scrollY.toFixed(1)};
    const found = hits(el, btns);
    const centro = {x: er.left + Math.min(er.width, 80) / 2, y: Math.min(Math.max(er.top + 8, 0), window.innerHeight - 1)};
    return {
      status: 'executado',
      scrollY: +window.scrollY.toFixed(1),
      texto: (el.innerText || '').replace(/\s+/g, ' ').trim().slice(0, 120),
      w: +er.width.toFixed(1),
      h: +er.height.toFixed(1),
      hits: found.length,
      amostra: found.slice(0, 4),
      botoes: labels
    };
  }
  async function um(seletor) {
    const nodes = [...document.querySelectorAll(seletor)];
    if (!nodes.length) return {status: 'ausente'};
    let ultimo = {status: 'ausente'};
    for (const el of nodes) {
      const item = await alinhar(el);
      window.scrollTo(0, 0);
      if (item.status === 'executado') return item;
      if (item.status === 'incompleto' && !(item.motivo || '').includes('scrollY')) return item;
      ultimo = item;
    }
    return ultimo;
  }
  async function todos(seletor) {
    const itens = [];
    for (const el of document.querySelectorAll(seletor)) {
      const item = await alinhar(el);
      window.scrollTo(0, 0);
      itens.push(item);
    }
    return itens;
  }
  const corpo = document.querySelector('.article-body');
  const cr = corpo.getBoundingClientRect();
  const pad = parseFloat(getComputedStyle(corpo).paddingRight) || 0;
  const wa = document.querySelector('.floating-btn--whatsapp').getBoundingClientRect();
  const aviso = document.querySelector('.article-important-notice');
  const tabela = document.querySelector('.article-table-scroll');
  const h2 = await todos('article .article-body h2');
  const p = await um('article .article-body p');
  const h3 = await um('article .article-body h3');
  const lista = await um('article .article-body ul, article .article-body ol');
  const tabelaAlvo = await um('article .article-body .article-table-scroll');
  const avisoAlvo = await um('.article-important-notice');
  const ctaTitulo = await um('.article-final-cta__title');
  const ctaTexto = await um('.article-final-cta__text');
  const ctaAcoes = await um('.article-final-cta__actions');
  const relacionada = await um('.article-related-news__title');
  let tabelaInfo = null;
  if (tabela) {
    tabelaInfo = {
      scroll: tabela.scrollWidth > tabela.clientWidth + 1,
      w: +tabela.getBoundingClientRect().width.toFixed(1)
    };
  }
  return {
    folhas,
    paddingRight: +pad.toFixed(2),
    folga: +(wa.left - (cr.right - pad)).toFixed(2),
    avisoPad: aviso ? +parseFloat(getComputedStyle(aviso).paddingRight).toFixed(2) : null,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    h2, p, h3, lista, tabela: tabelaAlvo, aviso: avisoAlvo,
    ctaTitulo, ctaTexto, ctaAcoes, relacionada, tabelaInfo
  };
}
'''

CLICKS = r'''
async () => {
  document.documentElement.style.scrollBehavior = 'auto';
  const frame = () => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)));
  const link = document.querySelector('.article-final-cta__link');
  const er = link.getBoundingClientRect();
  window.scrollTo(0, window.scrollY + er.top - window.innerHeight * 0.45);
  await frame();
  const r = link.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  const wa = document.querySelector('.floating-btn--whatsapp');
  const wr = wa.getBoundingClientRect();
  const hitWa = document.elementFromPoint(wr.left + wr.width / 2, wr.top + wr.height / 2);
  return {
    href: link.getAttribute('href'),
    centroDoLink: !!(hit && (hit === link || link.contains(hit))),
    centroDoWhatsapp: !!(hitWa && (hitWa === wa || wa.contains(hitWa)))
  };
}
'''

results = []
clicks = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = support.new_context(browser, allow=(base,), viewport={"width": 390, "height": 800}, device_scale_factor=1)
    page = context.new_page()
    for job in jobs:
        page.goto(base + job["route"], wait_until="load")
        for width, height in job["viewports"]:
            page.set_viewport_size({"width": width, "height": height})
            data = page.evaluate(MEASURE)
            data.update({"slug": job["slug"], "familia": job["familia"], "width": width, "height": height})
            results.append(data)
    page.goto(base + "/noticias/", wait_until="load")
    cards = {}
    for width in (390, 1440):
        page.set_viewport_size({"width": width, "height": 800})
        cards[str(width)] = page.evaluate(
            "() => { const h2 = document.querySelector('#news-article-list .news-card h2');"
            " return {paddingRight: parseFloat(getComputedStyle(h2).paddingRight),"
            " overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth}; }"
        )
    for route in (
        "/noticias/novos-compendios-farmacopeia-brasileira-entram-em-vigor/",
        "/noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/",
    ):
        page.set_viewport_size({"width": 390, "height": 800})
        page.goto(base + route, wait_until="load")
        info = page.evaluate(CLICKS)
        page.locator(".article-final-cta__link--primary").click()
        page.wait_for_url("**/contato/**")
        info["cta"] = page.url
        page.go_back(wait_until="load")
        page.locator(".article-back-link").click()
        page.wait_for_url("**/noticias/**")
        info["volta"] = page.url
        page.go_back(wait_until="load")
        page.evaluate("() => window.scrollTo(0, 800)")
        page.locator("#btn-voltar-topo").click()
        page.wait_for_function("() => window.scrollY < 5", timeout=4000)
        info["topo"] = page.evaluate("() => window.scrollY")
        info["rota"] = route
        clicks.append(info)
    browser.close()
print(json.dumps({"medicoes": results, "cards": cards, "cliques": clicks}))
"""


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def _jobs():
    jobs = []
    for slug, route, familia in MAIN:
        viewports = [(width, 800) for width in MAIN_WIDTHS]
        viewports.append((390, 640))
        jobs.append({"slug": slug, "route": route, "familia": familia, "viewports": viewports})
    for slug, route, familia in SAMPLES:
        jobs.append({
            "slug": slug,
            "route": route,
            "familia": familia,
            "viewports": [(width, 800) for width in SAMPLE_WIDTHS],
        })
    return jobs


@pytest.fixture(scope="module")
def geometria():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", PROBE, f"http://127.0.0.1:{server.server_port}", json.dumps(_jobs())],
            capture_output=True,
            text=True,
            encoding="utf-8",
            timeout=240,
            env=subprocess_env(),
            check=False,
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert completed.returncode == 0, completed.stderr[-4000:]
    return json.loads(completed.stdout)


def _da(geometria, slug, width, height=800):
    return next(item for item in geometria["medicoes"] if item["slug"] == slug and item["width"] == width and item["height"] == height)


def _executados(item):
    blocos = [item["p"], item["h3"], item["lista"], item["tabela"], item["aviso"], item["ctaTitulo"], item["ctaTexto"], item["ctaAcoes"], item["relacionada"]]
    blocos.extend(item["h2"])
    return [bloco for bloco in blocos if bloco.get("status") == "executado"]


def test_reserva_e_regra_do_componente_compartilhado():
    css = (ROOT / "assets" / "css" / "pages" / "noticias-tipos.css").read_text(encoding="utf-8")
    assert ".article-body" in css and "100vw" in css
    assert "line-clamp" not in css and "novos-compendios" not in css and "mapa-portaria-1617" not in css
    detalhe = (ROOT / "assets" / "css" / "pages" / "noticia-detalhe.css").read_text(encoding="utf-8")
    listagem = (ROOT / "assets" / "css" / "pages" / "noticias.css").read_text(encoding="utf-8")
    # Layout comum (10/10/2026): a reserva do herói saiu de noticia-detalhe.css (só o tipo Atualização, valor fixo)
    # e está em noticias-tipos.css para os quatro tipos e as duas famílias.
    assert ".article-hero-atualizacao :is(h1, p)" not in detalhe
    assert "main > article > header > .max-w-4xl > *" in css
    assert "#news-article-list .news-card :is(h2, p)" in listagem
    paginas = [
        ROOT / "noticias" / "novos-compendios-farmacopeia-brasileira-entram-em-vigor" / "index.html",
        ROOT / "noticias" / "mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal" / "index.html",
        ROOT / "noticias" / "anvisa-hmp-solicita-medicamentos-produtos-biologicos" / "index.html",
        ROOT / "noticias" / "farmacia-popular-adequacao-materiais-periodo-eleitoral" / "index.html",
    ]
    for pagina in paginas:
        texto = pagina.read_text(encoding="utf-8")
        assert "noticias-tipos.css?v=20261010-layout-1" in texto
        assert "<br" not in texto[texto.index("<section class=\"article-body\"") : texto.index("</section>", texto.index("article-body"))]


def test_dois_subtitulos_nao_entram_nos_controles(geometria):
    for slug, titulo, width, height in (
        ("farmacopeia", TITULOS[0], 390, 800),
        ("farmacopeia", TITULOS[0], 390, 640),
        ("mapa", TITULOS[1], 390, 800),
        ("mapa", TITULOS[1], 390, 640),
    ):
        item = _da(geometria, slug, width, height)
        alvo = next(h2 for h2 in item["h2"] if h2.get("texto", "").startswith(titulo))
        assert alvo["status"] == "executado", alvo
        assert alvo["w"] > 2 and alvo["h"] > 2 and alvo["scrollY"] > 300
        assert any("topo" in nome for nome in alvo["botoes"])
        assert any("WhatsApp" in nome for nome in alvo["botoes"])
        assert alvo["hits"] == 0, alvo


def test_corpo_reserva_a_faixa_sem_sobrar_largura(geometria):
    for slug, _route, _familia in MAIN:
        for width in MAIN_WIDTHS:
            item = _da(geometria, slug, width)
            assert item["overflowX"] <= 0, (slug, width, item["overflowX"])
            if width >= 1024:
                assert item["paddingRight"] <= 0.5, (slug, width, item["paddingRight"])
                assert item["folga"] >= 8, (slug, width, item["folga"])
            elif item["paddingRight"] > 0.5:
                assert 6 <= item["folga"] <= 12, (slug, width, item["paddingRight"], item["folga"])
            for bloco in _executados(item):
                assert bloco["hits"] == 0, (slug, width, bloco.get("texto"), bloco.get("amostra"))
                assert bloco["w"] > 2 and bloco["h"] > 2 and bloco["scrollY"] > 300
    farm = _da(geometria, "farmacopeia", 390)
    largo = _da(geometria, "farmacopeia", 1440)
    assert farm["paddingRight"] == pytest.approx(60, abs=1)
    assert largo["paddingRight"] == pytest.approx(0, abs=0.5)
    assert farm["avisoPad"] == pytest.approx(60, abs=1)
    assert largo["avisoPad"] == pytest.approx(24, abs=1)


def test_amostras_de_tipo_e_as_duas_familias(geometria):
    for slug, _route, familia in SAMPLES:
        for width in SAMPLE_WIDTHS:
            item = _da(geometria, slug, width)
            assert item["overflowX"] <= 0, (slug, width)
            folhas = " ".join(item["folhas"])
            assert "noticias-tipos.css" in folhas
            if familia == "custom.min.css":
                assert "custom.min.css" in folhas
            elif familia == "modular":
                assert "noticia-detalhe.css" in folhas
            else:
                assert "custom.min.css" in folhas and "noticia-detalhe.css" in folhas
            if width <= 960:
                assert item["paddingRight"] > 8, (slug, width, item["paddingRight"])
            else:
                assert item["paddingRight"] <= 0.5
            for bloco in _executados(item):
                assert bloco["hits"] == 0, (slug, width, bloco.get("texto"), bloco.get("amostra"))
        estreito = _da(geometria, slug, 390)
        assert any(bloco.get("status") == "executado" for bloco in estreito["h2"]), (slug, estreito["h2"])
        assert estreito["p"]["status"] == "executado" and estreito["p"]["hits"] == 0, (slug, estreito["p"])


def test_tabela_continua_na_rolagem_interna(geometria):
    for width in (390, 768, 1440):
        item = _da(geometria, "tabela", width)
        assert item["overflowX"] <= 0
        assert item["tabelaInfo"] is not None
    estreita = _da(geometria, "tabela", 390)
    assert estreita["tabelaInfo"]["scroll"] is True
    assert estreita["tabela"]["status"] == "executado"
    assert estreita["tabela"]["hits"] == 0, estreita["tabela"]


def test_listagem_e_os_cliques_permanecem(geometria):
    assert geometria["cards"]["390"]["paddingRight"] == pytest.approx(34, abs=1)
    assert geometria["cards"]["1440"]["paddingRight"] == pytest.approx(0, abs=0.5)
    assert geometria["cards"]["390"]["overflowX"] <= 0
    assert len(geometria["cliques"]) == 2
    for clique in geometria["cliques"]:
        assert clique["centroDoLink"] is True
        assert clique["centroDoWhatsapp"] is True
        assert clique["cta"].rstrip("/").endswith("/contato")
        assert clique["volta"].rstrip("/").endswith("/noticias")
        assert clique["topo"] < 5
