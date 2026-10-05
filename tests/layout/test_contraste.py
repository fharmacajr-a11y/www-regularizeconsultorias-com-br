"""Contraste do texto visível, medido com as cores renderizadas.

Região medida: as linhas dos nós de texto de cada elemento (Range.getClientRects),
sem os espaços das pontas e recortadas pelos ancestrais com overflow. Padding,
bordas, ícones e controles filhos ficam fora por construção; os botões
flutuantes ficam fora da coleta e ocultos na captura. Um elemento pintado por
cima do texto (imagem, fundo, pseudo-elemento) é reprovado como sobreposição.
O conteúdo de um <details> fechado não é pintado e fica de fora; cada <details>
é aberto pelo summary e medido de novo.

Fundo: a janela ganha a altura da página (o layout não pode mudar com isso; o
teste confere), o texto fica invisível só pelo -webkit-text-fill-color e a
captura dá o fundo real, já composto: degradês, imagens e camadas
transparentes. Contam todos os pixels com centro na região, sem percentil nem
amostragem. Sobre fundo sólido, a conta também é feita com as cores CSS dos
ancestrais, sem o arredondamento de 8 bits da captura, e vale o menor valor.

Cor do texto: a computada pelo navegador, com o alfa vezes a opacidade dos
ancestrais, composta sobre cada cor de fundo. Os pixels do texto nunca entram.
Exige 4,5:1, ou 3:1 para texto grande (24 px, ou 14 pt = 18,67 px em negrito),
sem arredondar. Texto aria-hidden, oculto ou desabilitado fica de fora.
Placeholders visíveis (campo vazio) entram com a cor, a opacidade e a fonte
calculadas do ::placeholder.

Modos: `texto` (390 e 1440 px, todas as rotas), `degrade` (só o texto cujo
fundo não é o sólido dos ancestrais, em 320 e 360 px, nos breakpoints 640, 768,
1024 e 1280 e em 896) e `hover` (CTAs coloridos com o ponteiro em cima). Os limites
do método estão no tests/README.md.

Roda num subprocesso, como layout/test_rodape_espaco.py.
"""
import io
import json
import math
import os
import subprocess
import sys
import threading
from collections import Counter
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support import SITE_DIR, new_context


ROUTES = (
    "/", "/sobre/", "/servicos/", "/equipe/", "/contato/", "/comunicado/", "/noticias/",
    "/farmacia-popular/", "/manuais-e-pops/", "/manuais-e-pops/manual-boas-praticas-drogaria/",
    "/politica-de-privacidade/",
    "/noticias/cnes-prorroga-transmissor-competencia-06-2026/",
    "/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/",
    "/noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/",
    "/noticias/farmacia-popular-adequacao-materiais-periodo-eleitoral/",
    "/noticias/o-que-e-afe-e-por-que-e-importante/",
    "/noticias/prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular/",
    # Informativo com o hero do custom.min.css (o do MAPA vem do noticia-detalhe.css).
    "/noticias/anvisa-proibe-plataforma-consultas-entrega-medicamentos/",
)
WIDTHS = (390, 1440)
# Breakpoints sm, md, lg e xl, e 896 px: o container dos artigos (max-w-4xl)
# deixa de ocupar a janela, e o texto fica mais perto da borda dos degradês.
GRADIENT_WIDTHS = (320, 360, 640, 768, 896, 1024, 1280)
HOVER_TARGETS = (
    ("/comunicado/", "#avisos-lista a.rounded-lg"),
    ("/noticias/", "#news-article-list a.news-amber-button"),
    ("/contato/", "main a.rounded-xl[href^='/whatsapp/']"),
    ("/noticias/prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular/", "[data-news-update-callout] a"),
)
# Diferença máxima, por canal, entre a captura e o fundo CSS composto para o
# fundo contar como o sólido dos ancestrais (arredondamento de 8 bits).
SOLID_TOLERANCE = 1.5
EFFECTIVE_FONT = os.environ.get("CONTRASTE_FONTE_EFETIVA") == "1"

# Linhas dos nós de texto próprios do elemento, sem os espaços das pontas,
# recortadas pelos ancestrais com overflow e pela página (coordenadas da janela).
# Um placeholder não tem nó de texto: a linha dele é a caixa de conteúdo do
# campo, na largura do texto medida com a fonte calculada do ::placeholder.
REGION_JS = r"""
  const textLines = el => {
    const lines = [];
    for (const node of el.childNodes) {
      if (node.nodeType !== 3 || !node.textContent.trim()) continue;
      const text = node.textContent;
      const range = document.createRange();
      range.setStart(node, text.search(/\S/));
      range.setEnd(node, text.length - /\s*$/.exec(text)[0].length);
      for (const r of range.getClientRects()) if (r.width > 0 && r.height > 0) lines.push([r.left, r.top, r.right, r.bottom]);
    }
    return lines;
  };
  const placeholderLines = el => {
    if (!el.placeholder.trim() || !el.matches(':placeholder-shown')) return [];
    const s = getComputedStyle(el), p = getComputedStyle(el, '::placeholder');
    const n = key => parseFloat(s[key]) || 0;
    const box = el.getBoundingClientRect();
    const left = box.left + n('borderLeftWidth') + n('paddingLeft'), right = box.right - n('borderRightWidth') - n('paddingRight');
    const top = box.top + n('borderTopWidth') + n('paddingTop'), bottom = box.bottom - n('borderBottomWidth') - n('paddingBottom');
    const context = document.createElement('canvas').getContext('2d');
    context.font = `${p.fontStyle} ${p.fontWeight} ${p.fontSize} ${p.fontFamily}`;
    const text = el.placeholder.trim();
    const width = context.measureText(text).width + (parseFloat(p.letterSpacing) || 0) * text.length;
    if (el.tagName === 'TEXTAREA') {
      const lineHeight = parseFloat(p.lineHeight) || parseFloat(p.fontSize) * 1.2;
      return [[left, top, right, Math.min(bottom, top + Math.ceil(width / (right - left)) * lineHeight)]];
    }
    const used = Math.min(width, right - left);
    const start = p.textAlign === 'center' ? left + (right - left - used) / 2
      : ['right', 'end'].includes(p.textAlign) ? right - used : left;
    return [[start, top, start + used, bottom]];
  };
  const regionOf = el => {
    const lines = el.matches('input, textarea') ? placeholderLines(el) : textLines(el);
    const page = document.documentElement;
    let clip = [-scrollX, -scrollY, page.scrollWidth - scrollX, page.scrollHeight - scrollY];
    for (let node = el; node && node !== document.body; node = node.parentElement) {
      const s = getComputedStyle(node);
      if (s.display === 'inline' || (s.overflowX === 'visible' && s.overflowY === 'visible')) continue;
      const box = node.getBoundingClientRect();
      const left = box.left + node.clientLeft, top = box.top + node.clientTop;
      clip = [Math.max(clip[0], left), Math.max(clip[1], top),
              Math.min(clip[2], left + node.clientWidth), Math.min(clip[3], top + node.clientHeight)];
    }
    return lines
      .map(r => [Math.max(r[0], clip[0]), Math.max(r[1], clip[1]), Math.min(r[2], clip[2]), Math.min(r[3], clip[3])])
      .filter(r => r[2] > r[0] && r[3] > r[1]);
  };
"""
COLLECT_JS = r"""([root, hitTest]) => {""" + REGION_JS + r"""
  const parse = value => {
    const match = /^rgba?\(([^)]*)\)$/.exec(value.trim());
    if (!match) return null;
    const n = match[1].split(/[\s,\/]+/).filter(Boolean).map(Number);
    return n.length >= 3 && n.every(Number.isFinite) ? [n[0], n[1], n[2], n.length > 3 ? n[3] : 1] : null;
  };
  const describe = node => node.tagName.toLowerCase() + (node.id ? '#' + node.id : '')
    + [...node.classList].slice(0, 3).map(name => '.' + name).join('');
  const paints = node => {
    if (['IMG', 'VIDEO', 'CANVAS', 'IFRAME', 'OBJECT', 'EMBED', 'INPUT', 'TEXTAREA', 'SELECT', 'svg'].includes(node.tagName)) return true;
    const visible = style => style.backgroundImage !== 'none' || (parse(style.backgroundColor) || [0, 0, 0, 0])[3] > 0;
    if (visible(getComputedStyle(node))) return true;
    return ['::before', '::after'].some(pseudo => {
      const style = getComputedStyle(node, pseudo);
      return style.content !== 'none' && style.content !== 'normal' && visible(style);
    });
  };
  for (const node of document.querySelectorAll('[data-contrast-index]')) node.removeAttribute('data-contrast-index');
  const scope = root ? [root, ...root.querySelectorAll('*')] : document.body.querySelectorAll('*');
  const items = [];
  let index = 0;
  for (const el of scope) {
    if (el.closest('svg, script, style, noscript, template, select')) continue;
    // Campo: entra o placeholder visível (campo vazio). Demais: texto próprio.
    const field = el.matches('input, textarea');
    if (field ? !(el.placeholder.trim() && el.matches(':placeholder-shown'))
              : ![...el.childNodes].some(node => node.nodeType === 3 && node.textContent.trim())) continue;
    if (el.closest('[aria-hidden="true"], .floating-buttons, [hidden], :disabled')) continue;
    // Fora também o que não é pintado: display:none, visibility e conteúdo
    // recolhido (o de um <details> fechado tem caixa, mas não aparece).
    if (!el.checkVisibility({visibilityProperty: true})) continue;
    // Do placeholder valem cor, opacidade e fonte calculadas do ::placeholder.
    const style = getComputedStyle(el, field ? '::placeholder' : null);
    let opacity = field ? parseFloat(style.opacity) : 1;
    for (let node = el; node; node = node.parentElement) opacity *= parseFloat(getComputedStyle(node).opacity);
    const color = parse(style.webkitTextFillColor);
    if (opacity < 0.1 || (color && color[3] === 0)) continue;
    const region = regionOf(el);
    if (!region.length) continue;

    const overlays = new Set();
    if (hitTest) {
      for (const [x0, y0, x1, y1] of region) {
        for (const fraction of [0.1, 0.5, 0.9]) {
          const stack = document.elementsFromPoint(x0 + (x1 - x0) * fraction, (y0 + y1) / 2);
          const at = stack.indexOf(el);
          for (const node of at < 0 ? [] : stack.slice(0, at)) {
            if (!el.contains(node) && paints(node)) overlays.add(describe(node));
          }
        }
      }
    }

    const layers = []; let gradient = false;
    for (let node = el; node; node = node.parentElement) {
      const s = getComputedStyle(node);
      if (s.backgroundImage !== 'none') { gradient = true; break; }
      const bg = parse(s.backgroundColor);
      if (!bg) { gradient = true; break; }
      if (bg[3] > 0) layers.push(bg);
      if (bg[3] === 1) break;
    }
    const html = el.outerHTML.slice(0, 120);
    el.setAttribute('data-contrast-index', index);
    items.push({
      index: index++, html, text: (field ? el.placeholder : el.textContent).trim().replace(/\s+/g, ' ').slice(0, 40), field,
      color, rawColor: style.webkitTextFillColor, opacity, layers, gradient, region, overlays: [...overlays],
      size: parseFloat(style.fontSize), weight: parseInt(style.fontWeight, 10),
    });
  }
  return items;
}"""
REGIONS_JS = r"""(indexes) => {""" + REGION_JS + r"""
  return indexes.map(index => regionOf(document.querySelector(`[data-contrast-index="${index}"]`)));
}"""
STABLE = "*,*::before,*::after{transition:none!important;animation:none!important}html{scroll-behavior:auto!important}"
HIT_TEST = "*,*::before,*::after{pointer-events:auto!important}"
HIDE_TEXT = (
    "*,*::before,*::after,*::marker,::placeholder{-webkit-text-fill-color:transparent!important;"
    "-webkit-text-stroke-width:0!important;text-shadow:none!important;"
    "text-decoration-color:transparent!important;caret-color:transparent!important}"
    "::placeholder{color:transparent!important}.floating-buttons{visibility:hidden!important}"
)
NEXT_FRAME = "() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done)))"


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def _luminance(rgb):
    def channel(value):
        value /= 255
        return value / 12.92 if value <= 0.03928 else ((value + 0.055) / 1.055) ** 2.4
    return 0.2126 * channel(rgb[0]) + 0.7152 * channel(rgb[1]) + 0.0722 * channel(rgb[2])


def _ratio(first, second):
    high, low = sorted((_luminance(first), _luminance(second)), reverse=True)
    return (high + 0.05) / (low + 0.05)


def _over(color, background):
    alpha = color[3]
    return tuple(color[i] * alpha + background[i] * (1 - alpha) for i in range(3))


def _solid_background(layers):
    background = (255, 255, 255)
    for layer in reversed(layers):
        background = _over(layer, background)
    return background


def _required(item):
    # 18 pt = 24 px; 14 pt = 56/3 px. Sem arredondar o limite a favor do texto.
    large = item["size"] >= 24 or (item["size"] >= 56 / 3 and item["weight"] >= 700)
    return 3.0 if large else 4.5


def _shown(ratio):
    """Trunca para exibir: um 4,499:1 aparece como 4,49, nunca como 4,50."""
    return f"{math.floor(ratio * 100) / 100:.2f}"


def _region_colors(shot, region):
    """Cores (com contagem) dos pixels cujo centro cai na região do texto."""
    colors = Counter()
    for x0, y0, x1, y1 in region:
        i0, i1 = math.ceil(x0 - 0.5), math.ceil(x1 - 0.5)
        j0, j1 = math.ceil(y0 - 0.5), math.ceil(y1 - 0.5)
        if i1 <= i0:
            i0 = math.floor((x0 + x1) / 2); i1 = i0 + 1
        if j1 <= j0:
            j0 = math.floor((y0 + y1) / 2); j1 = j0 + 1
        i0, j0 = max(i0, 0), max(j0, 0)
        i1, j1 = min(i1, shot.size[0]), min(j1, shot.size[1])
        if i1 <= i0 or j1 <= j0:
            continue
        crop = shot.crop((i0, j0, i1, j1))
        for count, color in crop.getcolors(crop.size[0] * crop.size[1]):
            colors[color] += count
    return colors


def _evaluate(item, shot):
    """Menor contraste do texto na sua região e de onde veio o fundo."""
    text = (*item["color"][:3], item["color"][3] * item["opacity"])
    colors = _region_colors(shot, item["region"])
    if not colors:
        return None
    ratios = {color: _ratio(_over(text, color), color) for color in colors}
    worst = min(ratios, key=ratios.get)
    ratio, source = ratios[worst], "captura"
    if not item["gradient"]:
        expected = _solid_background(item["layers"])
        if all(abs(color[i] - expected[i]) <= SOLID_TOLERANCE for color in colors for i in range(3)):
            ratio, source = min(ratio, _ratio(_over(text, expected), expected)), "sólido"
    below = sum(count for color, count in colors.items() if ratios[color] < _required(item))
    return {
        "ratio": ratio, "required": _required(item), "source": source, "background": worst,
        "below": below / sum(colors.values()), "colors": len(colors),
    }


def _describe(label, item, result):
    where = "" if result["source"] == "sólido" else f" (fundo da captura, {result['below']:.2%} da região abaixo)"
    return f"{label}: {_shown(result['ratio'])}:1{where} em '{item['text']}' {item['html'][:90]}"


def _items(page, root=None, hit_test=True):
    style = page.add_style_tag(content=HIT_TEST) if hit_test else None
    items = page.evaluate(COLLECT_JS, [root, hit_test])
    if style:
        style.evaluate("node => node.remove()")
    return items


def _check(page, label, items, only_backgrounds=False):
    """Captura a janela com o texto invisível e confere cada item nela."""
    from PIL import Image

    style = page.add_style_tag(content=HIDE_TEXT)
    page.evaluate(NEXT_FRAME)
    hidden = page.evaluate(REGIONS_JS, [item["index"] for item in items])
    shot = Image.open(io.BytesIO(page.screenshot())).convert("RGB")
    style.evaluate("node => node.remove()")
    page.evaluate(NEXT_FRAME)
    failures = []
    moved = [item["text"] for item, region in zip(items, hidden) if region != item["region"]]
    if moved:
        failures.append(f"{label}: o texto invisível mudou o layout em {moved[:3]}")
    for item in items:
        if item["color"] is None:
            failures.append(f"{label}: cor de texto não lida ({item['rawColor']}) em '{item['text']}'")
            continue
        if item["overlays"]:
            failures.append(f"{label}: '{item['text']}' tem {', '.join(item['overlays'])} pintado por cima")
        result = _evaluate(item, shot)
        if result is None or (only_backgrounds and result["source"] == "sólido"):
            continue
        if result["ratio"] < result["required"]:
            failures.append(_describe(label, item, result))
    return failures


def _measure(page, label, only_backgrounds=False):
    """Página inteira numa janela da altura dela; depois, cada <details> aberto."""
    page.add_style_tag(content=STABLE)
    page.evaluate("() => window.scrollTo(0, 0)")
    page.evaluate(NEXT_FRAME)
    width = page.viewport_size["width"]
    reference = _items(page, hit_test=False)
    height = page.evaluate("() => document.documentElement.scrollHeight")
    page.set_viewport_size({"width": width, "height": height})
    page.wait_for_load_state("networkidle")
    page.evaluate(NEXT_FRAME)
    failures = []
    if page.evaluate("() => document.documentElement.scrollHeight") != height:
        failures.append(f"{label}: a altura da página muda com a altura da janela")
    items = _items(page)
    if [item["region"] for item in items] != [item["region"] for item in reference]:
        failures.append(f"{label}: as linhas de texto mudam de lugar com a altura da janela")
    failures.extend(_check(page, label, items, only_backgrounds))
    if only_backgrounds:
        return failures
    details = page.locator("details")
    for index in range(details.count()):
        current = details.nth(index)
        if not current.is_visible() or current.evaluate("node => node.open"):
            continue
        current.locator("summary").first.click()
        page.evaluate(NEXT_FRAME)
        items = _items(page, current.element_handle())
        failures.extend(_check(page, f"{label} <details> {index + 1} aberto", items))
        current.locator("summary").first.click()
    return failures


def _open(context, base, route):
    page = context.new_page()
    page.goto(base + route, wait_until="networkidle")
    page.evaluate("""async () => {
        for (const image of document.images) image.loading = 'eager';
        await Promise.all([...document.images].map(i => i.complete ? 0 : new Promise(d => { i.onload = i.onerror = d; })));
        await document.fonts.ready;
    }""")
    return page


def _new_context(browser, width):
    # Rota de rede comum (support): AdSense e demais domínios externos ficam
    # abortados. Por padrão as fontes externas também ficam de fora e o texto é
    # medido com a fonte de reserva; com CONTRASTE_FONTE_EFETIVA=1 entra a Inter
    # local (o mesmo arquivo da home), sem depender do Google Fonts.
    return new_context(browser, fonts="local" if EFFECTIVE_FONT else "block",
                       viewport={"width": width, "height": 900}, reduced_motion="reduce")


def _texto(browser, base, widths=WIDTHS, only_backgrounds=False):
    failures = []
    for width in widths:
        context = _new_context(browser, width)
        for route in ROUTES:
            page = _open(context, base, route)
            failures.extend(_measure(page, f"{route} @{width}", only_backgrounds))
            page.close()
        context.close()
    return failures


def _degrade(browser, base):
    return _texto(browser, base, GRADIENT_WIDTHS, only_backgrounds=True)


def _hover(browser, base):
    failures = []
    context = _new_context(browser, 1440)
    for route, selector in HOVER_TARGETS:
        page = _open(context, base, route)
        page.add_style_tag(content=STABLE)
        targets = page.locator(selector)
        assert targets.count(), f"{route}: nenhum alvo para {selector}"
        for index in range(targets.count()):
            target = targets.nth(index)
            if not target.is_visible():
                continue
            target.scroll_into_view_if_needed()
            target.hover()
            # Sem o teste de sobreposição: mudar pointer-events tiraria o hover.
            items = _items(page, target.element_handle(), hit_test=False)
            failures.extend(_check(page, f"{route} hover", items))
        page.close()
    context.close()
    return failures


MODES = {"texto": _texto, "degrade": _degrade, "hover": _hover}


def _collect(mode):
    from playwright.sync_api import sync_playwright

    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(headless=True, args=["--force-color-profile=srgb"])
            try:
                return MODES[mode](browser, f"http://127.0.0.1:{server.server_port}")
            finally:
                browser.close()
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _run(mode):
    env = dict(os.environ, PYTHONIOENCODING="utf-8")
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), mode],
        capture_output=True, text=True, encoding="utf-8", timeout=400, env=env,
    )
    assert completed.returncode == 0, completed.stderr
    failures = json.loads(completed.stdout)["failures"]
    assert not failures, "\n".join(failures)


def test_visible_text_meets_the_minimum_contrast():
    _run("texto")


def test_text_over_gradients_and_images_at_narrow_widths_and_breakpoints():
    _run("degrade")


def test_colored_ctas_keep_the_contrast_on_hover():
    _run("hover")


if __name__ == "__main__":
    print(json.dumps({"failures": _collect(sys.argv[1])}, ensure_ascii=False))
