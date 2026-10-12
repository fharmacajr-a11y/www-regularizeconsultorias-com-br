"""Contraste, cores e foco do selo e do botão dos cards da listagem de Notícias.

O teste de contraste geral mede o que aparece na carga: os cinco primeiros
cards. Os do sexto em diante (depois de "Ver mais notícias", de uma busca, de um
filtro ou de uma ordenação) ficavam de fora, e foi ali que "Ler atualização"
saiu com branco sobre #f59e0b (2,15:1) e "Ler notícia" com branco sobre #ea580c
(3,56:1). Até 11/10/2026 os cinco primeiros tinham um formato grande próprio;
desde 12/10/2026 (parecer de 11/10/2026, R1) todos os cards têm o mesmo modelo
(news-card-compact) em qualquer posição e estado.

Atualização, Informativo, Urgente e Orientação têm as cores num arquivo só
(assets/css/pages/noticias-tipos.css): fundo vivo e texto com alto contraste,
iguais no selo e no botão de todos os cards, com hover e foco um passo mais
escuros. Em cada janela (celular, meia tela, 1023/1024 e desktop) o teste
percorre a carga inicial, "Ver mais notícias", a busca pelo título de um artigo
de cada tipo que começa oculto (depois dos cinco primeiros), a categoria desse
artigo e a ordenação das mais antigas. Os artigos são achados pelo href, nunca
pela posição: cada um tem de manter o mesmo formato em "Ver mais", na busca e na
categoria. Em até dois cards por combinação de tipo, formato e classes, mede o selo (normal) e o
botão (normal, hover e foco de teclado): a cor do texto e o fundo calculados,
com os fundos dos ancestrais compostos, e o fundo capturado em pixels com o texto
oculto, no miolo do botão. Vale o menor dos dois.

Exige, nos quatro tipos, 4,5:1 em todos os estados, as cores de EXPECTED (as
mesmas em todos os cenários) e, no foco, o anel visível e a pílula mantida.

Roda num subprocesso por janela, como os outros testes de navegador.
"""
import json
import os
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env


VIEWPORTS = ((390, 844), (960, 900), (1023, 900), (1024, 900), (1440, 900))
MINIMUM = 4.5
TYPES = ("atualizacao", "informativo", "orientacao")
TEXT = "rgb(15, 23, 42)"
TEXT_WHITE = "rgb(255, 255, 255)"
# Cores esperadas (texto, fundo) do selo e do botão, por tipo e estado.
EXPECTED = {
    "atualizacao": {"normal": (TEXT, "rgb(245, 158, 11)"), "hover": (TEXT, "rgb(217, 119, 6)"), "foco": (TEXT, "rgb(217, 119, 6)")},
    "informativo": {"normal": (TEXT, "rgb(249, 115, 22)"), "hover": (TEXT, "rgb(234, 88, 12)"), "foco": (TEXT, "rgb(234, 88, 12)")},
    "urgente": {"normal": (TEXT_WHITE, "rgb(220, 38, 38)"), "hover": (TEXT_WHITE, "rgb(185, 28, 28)"), "foco": (TEXT_WHITE, "rgb(185, 28, 28)")},
    "orientacao": {"normal": (TEXT_WHITE, "rgb(21, 101, 192)"), "hover": (TEXT_WHITE, "rgb(26, 58, 92)"), "foco": (TEXT_WHITE, "rgb(26, 58, 92)")},
}

PROBE = r'''
import io
import json
import re
import sys

from PIL import Image
from playwright.sync_api import sync_playwright

import support

base, width, height = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
TYPES = ("atualizacao", "informativo", "orientacao")

HELPERS = r"""
window.__cta = (() => {
  const TYPES = [['news-amber-card', 'atualizacao'], ['news-orange-card', 'informativo'],
                 ['news-urgent-card', 'urgente'], ['news-card--orientation', 'orientacao']];
  const typeOf = card => (TYPES.find(([cls]) => card.classList.contains(cls)) || [null, 'outro'])[1];
  const parse = c => { const m = c.match(/[\d.]+/g).map(Number); return [m[0], m[1], m[2], m.length > 3 ? m[3] : 1]; };
  const over = (top, bottom) => [0, 1, 2].map(i => top[i] * top[3] + bottom[i] * (1 - top[3]));
  const backdrop = el => {
    const layers = [];
    for (let a = el; a; a = a.parentElement) {
      const cs = getComputedStyle(a);
      if (cs.backgroundImage !== 'none') return null;
      const c = parse(cs.backgroundColor);
      if (c[3] > 0) layers.push(c);
      if (c[3] >= 1) break;
    }
    let rgb = [255, 255, 255];
    for (const c of layers.reverse()) rgb = over(c, rgb);
    return rgb;
  };
  const cards = () => [...document.querySelectorAll('#news-article-list [data-news-card]')];
  const parts = card => ({
    badge: card.querySelector(':scope > div:first-of-type > div:first-child > span:first-child'),
    cta: [...card.querySelectorAll(':scope > a[href]')].pop(),
  });
  const measure = el => {
    const cs = getComputedStyle(el);
    const bg = backdrop(el);
    const text = parse(cs.color);
    return {text: bg ? over(text, bg) : null, background: bg, color: cs.color, backgroundColor: cs.backgroundColor,
            focusVisible: el.matches(':focus-visible'), hover: el.matches(':hover'), label: el.textContent.trim().replace(/\s+/g, ' '),
            radius: parseFloat(cs.borderTopLeftRadius) || 0, height: el.getBoundingClientRect().height,
            outline: {style: cs.outlineStyle, width: parseFloat(cs.outlineWidth) || 0, color: cs.outlineColor}};
  };
  const describe = card => {
    const {badge, cta} = parts(card);
    return {href: cta && cta.getAttribute('href'), type: typeOf(card), compact: card.classList.contains('news-card-compact'),
            hidden: card.classList.contains('hidden') || !card.getClientRects().length, category: card.dataset.category,
            title: card.dataset.title, ctaClass: cta && cta.className, badgeClass: badge && badge.className};
  };
  const settle = el => Promise.all(el.getAnimations().map(a => a.finished.catch(() => 0)));
  const part = (href, which) => {
    const card = cards().find(c => { const p = parts(c); return p.cta && p.cta.getAttribute('href') === href; });
    return parts(card)[which];
  };
  return {all: () => cards().map(describe), measure, settle, part};
})();
"""


def luminance(rgb):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def ratio(first, second):
    high, low = sorted((luminance(first), luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def pixel_background(page, handle):
    """Cores do fundo pintado no miolo do elemento, com o texto e o ícone ocultos."""
    page.evaluate("el => el.setAttribute('data-medir-contraste', '')", handle)
    style = page.add_style_tag(content="[data-medir-contraste],[data-medir-contraste] *{-webkit-text-fill-color:transparent!important;"
                                       "text-decoration-color:transparent!important;transition:none!important}"
                                       "[data-medir-contraste] svg{visibility:hidden!important}")
    box = handle.bounding_box()
    inset = min(box["width"] / 2 - 1, box["height"] / 2)
    clip = {"x": box["x"] + inset, "y": box["y"] + 2, "width": max(1, box["width"] - 2 * inset), "height": max(1, box["height"] - 4)}
    image = Image.open(io.BytesIO(page.screenshot(clip=clip))).convert("RGB")
    page.evaluate("el => el.removeAttribute('data-medir-contraste')", handle)
    style.evaluate("node => node.remove()")
    return [color for _, color in image.getcolors(maxcolors=1 << 20)]


def measure(page, href, which, state):
    handle = page.evaluate_handle("([href, which]) => window.__cta.part(href, which)", [href, which]).as_element()
    page.mouse.move(0, 0)
    page.evaluate("() => document.activeElement && document.activeElement.blur()")
    handle.scroll_into_view_if_needed()
    if state == "hover":
        handle.hover()
    elif state == "foco":
        page.keyboard.press("Shift")
        handle.evaluate("el => el.focus()")
    handle.evaluate("el => window.__cta.settle(el)")
    css = handle.evaluate("el => window.__cta.measure(el)")
    pixels = pixel_background(page, handle)
    result = {
        "estado": state, "cor": css["color"], "fundo": css["backgroundColor"], "rotulo": css["label"],
        "foco_visivel": css["focusVisible"], "hover": css["hover"],
        "contraste_css": round(ratio(css["text"], css["background"]), 3) if css["background"] else None,
        "contraste_pixels": round(min(ratio(css["text"] or [0, 0, 0], color) for color in pixels), 3),
        "cores_de_fundo": len(pixels), "raio": css["radius"], "altura": round(css["height"], 2), "contorno": css["outline"],
    }
    result["contraste"] = min(value for value in (result["contraste_css"], result["contraste_pixels"]) if value is not None)
    return result


def representatives(cards, extra=()):
    seen, chosen = {}, []
    for card in cards:
        if card["hidden"] or not card["href"]:
            continue
        key = (card["type"], card["compact"], card["ctaClass"], card["badgeClass"])
        if seen.get(key, 0) < 2 or card["href"] in extra:
            seen[key] = seen.get(key, 0) + 1
            chosen.append(card)
    return chosen


def collect(page, scenario, cards, extra=()):
    rows = []
    for card in representatives(cards, extra):
        common = {"cenario": scenario, "href": card["href"], "tipo": card["type"],
                  "formato": "compacto" if card["compact"] else "grande",
                  "classes": [card["ctaClass"], card["badgeClass"]]}
        badge = measure(page, card["href"], "badge", "normal")
        rows.append({**common, "parte": "selo", **badge})
        for state in ("normal", "hover", "foco"):
            rows.append({**common, "parte": "cta", **measure(page, card["href"], state=state, which="cta")})
    return rows


output = {"largura": width, "linhas": [], "alvos": {}, "formatos_dos_alvos": {}}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True, args=["--force-color-profile=srgb"])
    context = support.new_context(browser, viewport={"width": width, "height": height})
    context.add_init_script(HELPERS)
    page = context.new_page()

    def load():
        page.goto(base + "/noticias/", wait_until="load")
        page.evaluate("document.fonts.ready.then(() => true)")
        page.add_style_tag(content="html{scroll-behavior:auto!important}")
        return page.evaluate("window.__cta.all()")

    cards = load()
    # Alvo de cada tipo: o primeiro que começa oculto (depois dos cinco primeiros)
    # e fica entre os cinco primeiros da própria categoria (aparece no filtro dela).
    targets = {}
    for kind in TYPES:
        for card in cards:
            if card["type"] == kind and card["hidden"]:
                same = [other["href"] for other in cards if other["category"] == card["category"]]
                if same.index(card["href"]) < 5:
                    targets[kind] = card
                    break
        assert kind in targets, f"nenhum artigo oculto de {kind} encontrado"
        output["alvos"][kind] = {"href": targets[kind]["href"], "categoria": targets[kind]["category"], "titulo": targets[kind]["title"]}
        output["formatos_dos_alvos"][kind] = {}
    hrefs = tuple(t["href"] for t in targets.values())
    output["linhas"] += collect(page, "inicial", cards)

    page.locator("#btn-carregar-mais").click()
    cards = page.evaluate("window.__cta.all()")
    for kind, target in targets.items():
        output["formatos_dos_alvos"][kind]["ver_mais"] = next(c["compact"] for c in cards if c["href"] == target["href"])
    output["linhas"] += collect(page, "ver_mais", cards, extra=hrefs)

    for kind, target in targets.items():
        load()
        page.locator("#news-search").fill(target["title"])
        cards = page.evaluate("window.__cta.all()")
        output["formatos_dos_alvos"][kind]["busca"] = next(c["compact"] for c in cards if c["href"] == target["href"])
        output["linhas"] += collect(page, "busca", [c for c in cards if c["href"] == target["href"]], extra=(target["href"],))

        load()
        page.locator(f"[data-news-category='{target['category']}']").click()
        cards = page.evaluate("window.__cta.all()")
        found_cat = [c["compact"] for c in cards if c["href"] == target["href"]]
        output["formatos_dos_alvos"][kind]["categoria"] = found_cat[0] if found_cat else None
        output["linhas"] += collect(page, "categoria", cards, extra=(target["href"],))

    load()
    page.locator("[data-news-sort='asc']").click()
    cards = page.evaluate("window.__cta.all()")
    output["linhas"] += collect(page, "ordenacao_asc", cards)
    page.locator("#btn-carregar-mais").click()
    cards = page.evaluate("window.__cta.all()")
    output["linhas"] += collect(page, "ordenacao_asc_ver_mais", cards)

    # Até 11/10/2026 aqui cada variante (tipo + classes) era buscada para aparecer
    # também no formato grande. Com o modelo único não há outro formato: as
    # variantes já foram medidas em "Ver mais" e na ordenação.
    browser.close()
print(json.dumps(output, ensure_ascii=False))
'''


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def medidas():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"

    def run(viewport):
        return subprocess.run(
            [sys.executable, "-c", PROBE, base, str(viewport[0]), str(viewport[1])],
            capture_output=True, text=True, encoding="utf-8", timeout=900, env=subprocess_env(),
        )

    try:
        with ThreadPoolExecutor(max_workers=3) as pool:
            completed = dict(zip(VIEWPORTS, pool.map(run, VIEWPORTS)))
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    results = {}
    for viewport, done in completed.items():
        assert done.returncode == 0, f"@{viewport[0]}: {done.stderr[-3000:]}"
        results[viewport[0]] = json.loads(done.stdout)
    # Com RC_MEDIDAS_CTA=<arquivo>, grava todas as medidas (relatório da rodada).
    if os.environ.get("RC_MEDIDAS_CTA"):
        with open(os.environ["RC_MEDIDAS_CTA"], "w", encoding="utf-8") as handle:
            json.dump({"site": str(SITE_DIR), "medidas": results}, handle, ensure_ascii=False, indent=1)
    return results


def _label(row):
    return (f"@{row['largura']} {row['cenario']} {row['tipo']} {row['formato']} {row['parte']} {row['estado']} "
            f"{row['href']} ({row['cor']} sobre {row['fundo']})")


def _rows(medidas, width):
    return [{**row, "largura": width} for row in medidas[width]["linhas"]]


@pytest.mark.parametrize("kind", TYPES)
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_type_badge_and_button_reach_the_minimum_in_every_state(medidas, width, kind):
    rows = [row for row in _rows(medidas, width) if row["tipo"] == kind]
    # Os cinco primeiros do resultado são grandes; os demais, compactos. Os dois formatos entram na medida.
    assert {row["formato"] for row in rows} == {"compacto", "grande"}, f"{kind} não cobriu os dois modelos"
    assert {row["estado"] for row in rows if row["parte"] == "cta"} == {"normal", "hover", "foco"}
    for row in rows:
        if row["estado"] == "foco":
            assert row["foco_visivel"], f"{_label(row)}: foco sem :focus-visible"
        if row["estado"] == "hover":
            assert row["hover"], f"{_label(row)}: hover não aplicado"
    below = [f"{_label(row)}: {row['contraste']:.2f}:1" for row in rows if row["contraste"] < MINIMUM]
    assert not below, "abaixo de 4,5:1:\n" + "\n".join(below)


@pytest.mark.parametrize("kind", TYPES)
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_type_uses_the_central_colors_in_every_scenario(medidas, width, kind):
    rows = [row for row in _rows(medidas, width) if row["tipo"] == kind]
    wrong = []
    for row in rows:
        expected = EXPECTED[kind]["normal" if row["parte"] == "selo" else row["estado"]]
        if (row["cor"], row["fundo"]) != expected:
            wrong.append(f"{_label(row)}: esperado {expected[0]} sobre {expected[1]}")
    assert not wrong, "\n".join(wrong[:20])


@pytest.mark.parametrize("kind", TYPES)
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_type_button_keeps_the_pill_and_a_visible_ring_on_focus(medidas, width, kind):
    rows = [row for row in _rows(medidas, width) if row["tipo"] == kind and row["parte"] == "cta" and row["estado"] == "foco"]
    assert rows
    for row in rows:
        assert row["raio"] >= row["altura"] / 2 - 0.5, f"{_label(row)}: raio {row['raio']} px no foco (pílula perdida)"
        ring = row["contorno"]
        assert ring["style"] not in ("none", "hidden") and ring["width"] >= 2, f"{_label(row)}: anel de foco {ring}"


@pytest.mark.parametrize("kind", TYPES)
@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_the_same_type_article_keeps_one_format_in_every_scenario(medidas, width, kind):
    # O alvo começa depois dos cinco primeiros (compacto em "Ver mais") e passa ao modelo maior
    # quando a busca ou o filtro o colocam entre os cinco primeiros. As cores do botão não mudam.
    result = medidas[width]
    formats = result["formatos_dos_alvos"][kind]
    target = result["alvos"][kind]["href"]
    assert formats == {"ver_mais": True, "busca": False, "categoria": False}, (result["alvos"][kind], formats)
    rows = [row for row in _rows(medidas, width) if row["href"] == target and row["parte"] == "cta"]
    por_cenario = {}
    for row in rows:
        por_cenario.setdefault(row["cenario"], {})[row["estado"]] = (row["cor"], row["fundo"])
    assert {"ver_mais", "busca", "categoria"} <= set(por_cenario), (target, sorted(por_cenario))
    assert len({json.dumps(v, sort_keys=True) for v in por_cenario.values()}) == 1, f"@{width} {target}: {por_cenario}"
