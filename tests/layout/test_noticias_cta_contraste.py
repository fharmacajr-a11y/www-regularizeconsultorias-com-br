"""Contraste do selo e do botão dos cards da listagem de Notícias.

O teste de contraste geral mede o que aparece na carga: os cinco primeiros
cards, sempre no formato grande. Os compactos (do sexto em diante, depois de
"Ver mais notícias", de uma busca, de um filtro ou de uma ordenação) ficavam de
fora, e foi ali que "Ler atualização" saiu com branco sobre #f59e0b (2,15:1).

Em cada janela (celular, meia tela, 1023/1024 e desktop) o teste percorre a
carga inicial, "Ver mais notícias", a busca pelo título de um artigo de
Atualização que começa compacto, a categoria desse artigo e a ordenação das
mais antigas. O artigo é achado pelo href, nunca pela posição na lista: ele tem
de aparecer compacto em "Ver mais" e grande na busca e na categoria. Em até dois
cards por combinação de tipo, formato e classes, mede o selo (normal) e o botão
(normal, hover e foco de teclado): a cor do texto e o fundo calculados, com os
fundos dos ancestrais compostos, e o fundo capturado em pixels com o texto
oculto, no miolo do botão. Vale o menor dos dois.

Exige 4,5:1 em Atualização em todos os estados e as mesmas cores de texto e
fundo nos dois formatos. Os outros tipos (Informativo, Orientação e Urgente)
entram na medição e também têm de passar, exceto o que está em KNOWN_BELOW:
visual aprovado que fica registrado aqui, sem mudança silenciosa no site.

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
# Casos abaixo de 4,5:1 com visual aprovado, pela combinação exata (tipo,
# formato, parte, estado, cor do texto, fundo). Mudar o visual deles é decisão
# à parte; enquanto isso, o teste exige que continuem iguais ao medido (não
# pioram e não mudam sem atualizar esta lista). Registrados em 04/10/2026.
ORANGE_600 = "rgb(234, 88, 12)"
KNOWN_BELOW = {
    # Informativo compacto: branco sobre #ea580c (orange-600). O grande usa #c2410c (5,18:1).
    ("informativo", "compacto", "cta", "normal", "rgb(255, 255, 255)", ORANGE_600): (3.5, 3.6),
    # Informativo com "Ler notícia" em link de texto (text-orange-600 sobre o
    # branco do card), visível em formato grande depois de uma busca.
    ("informativo", "grande", "cta", "normal", ORANGE_600, "rgba(0, 0, 0, 0)"): (3.5, 3.6),
    ("informativo", "grande", "cta", "foco", ORANGE_600, "rgba(0, 0, 0, 0)"): (3.5, 3.6),
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
            focusVisible: el.matches(':focus-visible'), hover: el.matches(':hover'), label: el.textContent.trim().replace(/\s+/g, ' ')};
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
        "cores_de_fundo": len(pixels),
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
            rows.append({**common, "parte": "cta", **measure(page, card["href"], "cta", state)})
    return rows


output = {"largura": width, "linhas": [], "alvo": None, "formatos_do_alvo": {}}
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
    # Alvo: Atualização compacta na ordem padrão e entre as cinco primeiras da própria categoria.
    target = None
    for card in cards:
        if card["type"] == "atualizacao" and card["compact"]:
            same = [other["href"] for other in cards if other["category"] == card["category"]]
            if same.index(card["href"]) < 5:
                target = card
                break
    assert target, "nenhum artigo de Atualização compacto que fique entre os cinco primeiros da categoria"
    output["alvo"] = {"href": target["href"], "categoria": target["category"], "titulo": target["title"]}
    output["linhas"] += collect(page, "inicial", cards)

    page.locator("#btn-carregar-mais").click()
    cards = page.evaluate("window.__cta.all()")
    output["formatos_do_alvo"]["ver_mais"] = next(c["compact"] for c in cards if c["href"] == target["href"])
    output["linhas"] += collect(page, "ver_mais", cards, extra=(target["href"],))

    load()
    page.locator("#news-search").fill(target["title"])
    cards = page.evaluate("window.__cta.all()")
    output["formatos_do_alvo"]["busca"] = next(c["compact"] for c in cards if c["href"] == target["href"])
    output["linhas"] += collect(page, "busca", [c for c in cards if c["href"] == target["href"]], extra=(target["href"],))

    load()
    page.locator(f"[data-news-category='{target['category']}']").click()
    cards = page.evaluate("window.__cta.all()")
    output["formatos_do_alvo"]["categoria"] = next(c["compact"] for c in cards if c["href"] == target["href"])
    output["linhas"] += collect(page, "categoria", cards, extra=(target["href"],))

    load()
    page.locator("[data-news-sort='asc']").click()
    cards = page.evaluate("window.__cta.all()")
    output["linhas"] += collect(page, "ordenacao_asc", cards)
    page.locator("#btn-carregar-mais").click()
    cards = page.evaluate("window.__cta.all()")
    output["linhas"] += collect(page, "ordenacao_asc_ver_mais", cards)

    # Toda variante (tipo + classes do botão e do selo) também no formato grande:
    # a busca pelo título leva o card ao topo da lista.
    seen = {(row["tipo"], *row["classes"]) for row in output["linhas"] if row["formato"] == "grande"}
    for card in cards:
        signature = (card["type"], card["ctaClass"], card["badgeClass"])
        if signature in seen:
            continue
        seen.add(signature)
        load()
        page.locator("#news-search").fill(card["title"])
        found = [c for c in page.evaluate("window.__cta.all()") if c["href"] == card["href"]]
        assert found and not found[0]["compact"], f"busca não trouxe {card['href']} em formato grande"
        output["linhas"] += collect(page, "busca_variante", found, extra=(card["href"],))
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
            capture_output=True, text=True, encoding="utf-8", timeout=600, env=subprocess_env(),
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


@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_atualizacao_badge_and_button_reach_the_minimum_in_every_state(medidas, width):
    rows = [row for row in _rows(medidas, width) if row["tipo"] == "atualizacao"]
    assert {row["formato"] for row in rows} == {"grande", "compacto"}, "Atualização não apareceu nos dois formatos"
    assert {row["estado"] for row in rows if row["parte"] == "cta"} == {"normal", "hover", "foco"}
    for row in rows:
        if row["estado"] == "foco":
            assert row["foco_visivel"], f"{_label(row)}: foco sem :focus-visible"
        if row["estado"] == "hover":
            assert row["hover"], f"{_label(row)}: hover não aplicado"
    below = [f"{_label(row)}: {row['contraste']:.2f}:1" for row in rows if row["contraste"] < MINIMUM]
    assert not below, "abaixo de 4,5:1:\n" + "\n".join(below)


@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_atualizacao_uses_the_same_colors_in_both_formats(medidas, width):
    rows = [row for row in _rows(medidas, width) if row["tipo"] == "atualizacao"]
    by_state = {}
    for row in rows:
        by_state.setdefault((row["parte"], row["estado"]), set()).add((row["formato"], row["cor"], row["fundo"]))
    for (part, state), values in sorted(by_state.items()):
        colors = {(color, background) for _, color, background in values}
        assert len(colors) == 1, f"@{width} {part} {state}: cores diferentes entre formatos ou cards: {sorted(values)}"


@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_the_same_update_article_turns_from_compact_to_large(medidas, width):
    result = medidas[width]
    formats = result["formatos_do_alvo"]
    assert formats == {"ver_mais": True, "busca": False, "categoria": False}, (result["alvo"], formats)
    rows = [row for row in _rows(medidas, width) if row["href"] == result["alvo"]["href"] and row["parte"] == "cta"]
    compact = {row["estado"]: (row["cor"], row["fundo"]) for row in rows if row["formato"] == "compacto"}
    large = {row["estado"]: (row["cor"], row["fundo"]) for row in rows if row["formato"] == "grande"}
    assert compact and compact == large, f"@{width} {result['alvo']['href']}: compacto {compact} x grande {large}"


@pytest.mark.parametrize("width", [w for w, _ in VIEWPORTS])
def test_other_card_types_reach_the_minimum_or_stay_as_registered(medidas, width):
    rows = [row for row in _rows(medidas, width) if row["tipo"] != "atualizacao"]
    assert {"informativo", "orientacao", "urgente"} <= {row["tipo"] for row in rows}
    failures = []
    for row in rows:
        key = (row["tipo"], row["formato"], row["parte"], row["estado"], row["cor"], row["fundo"])
        if key in KNOWN_BELOW:
            low, high = KNOWN_BELOW[key]
            if not low <= row["contraste"] <= high:
                failures.append(f"{_label(row)}: {row['contraste']:.2f}:1 mudou do registrado ({low}–{high})")
        elif row["contraste"] < MINIMUM:
            failures.append(f"{_label(row)}: {row['contraste']:.2f}:1")
    assert not failures, "\n".join(failures)
