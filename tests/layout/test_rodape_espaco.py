"""Geometria do rodapé e dos controles flutuantes.

A referência visual é o commit 331a974, último estado aprovado antes do
fd53409. O fd53409 abriu um vão escuro abaixo dos créditos, porque reservava
a altura da coluna de botões em `footer > .max-w-7xl`. Depois, uma folga
lateral de 60 px corrigiu o eixo, mas estreitou o aviso legal e os créditos.

Nessa referência, os créditos e o fechamento do comunicado ocupam a largura
útil toda do container, sem recuo de nenhum lado. O teste confere essa
largura, as bordas e as quebras de linha medidas no 331a974. Também compara
o padding inferior com o da mesma página em 1440 px, confere se a página
termina no rodapé e se os botões visíveis cobrem texto, imagem ou controle.
Centralizar o texto não basta: um bloco estreito também fica no eixo.
"""
import json
import os
import subprocess
import sys
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from support import ROOT, public_html_paths


DETAIL_PAGES = [
    "index.html",
    "sobre/index.html",
    "servicos/index.html",
    "equipe/index.html",
    "contato/index.html",
    "manuais-e-pops/index.html",
    "manuais-e-pops/pop-sncr/index.html",
    "farmacia-popular/index.html",
    "noticias/index.html",
    "noticias/farmacia-popular-portaria-12091-2026-novas-regras/index.html",
    "noticias/anvisa-apreensao-cosmeticos-saneantes-empresas-desconhecidas/index.html",
    "noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/index.html",
    "comunicado/index.html",
    "politica-de-privacidade/index.html",
]

# Larguras pedidas e as bordas dos breakpoints reais do CSS.
DETAIL_WIDTHS = [
    320, 360, 375, 390, 414, 419, 420, 421, 462,
    478, 479, 480, 638, 639, 640, 641,
    767, 768, 898, 899, 900,
    1023, 1024, 1280, 1359, 1360, 1375, 1376, 1440,
]
GENERAL_WIDTHS = [390, 768, 1280, 1440]
REFERENCE_WIDTH = 1440

# Quebras de linha do 331a974, medidas por este script no fim da rolagem.
# Home: (aviso legal, direitos, crédito do desenvolvedor). Comunicado: linha
# de direitos do fechamento. As outras páginas variam o texto do aviso e
# entram só nas checagens de largura útil e alinhamento.
REFERENCE_COMMIT = "331a974"
REFERENCE_LINES = {
    "index.html": (("aviso legal", "direitos", "crédito do desenvolvedor"), {
        320: (9, 2, 3), 360: (8, 2, 2), 375: (8, 2, 2), 390: (8, 1, 2),
        414: (7, 1, 2), 419: (7, 1, 2), 420: (7, 1, 2), 421: (7, 1, 2),
        462: (6, 1, 2), 478: (6, 1, 2), 479: (6, 1, 2), 480: (6, 1, 2),
        638: (5, 1, 1), 639: (5, 1, 1), 640: (5, 1, 1), 641: (5, 1, 1),
        767: (4, 1, 1), 768: (4, 1, 1), 898: (3, 1, 1), 899: (3, 1, 1),
        900: (3, 1, 1), 1023: (3, 1, 1), 1024: (3, 1, 1), 1280: (2, 1, 1),
        1359: (2, 1, 1), 1360: (2, 1, 1), 1375: (2, 1, 1), 1376: (2, 1, 1),
        1440: (2, 1, 1),
    }),
    "comunicado/index.html": (("direitos do comunicado",), {
        width: (2,) if width < 414 else (1,) for width in DETAIL_WIDTHS
    }),
}


def _reference_lines(relative_path, width):
    names, by_width = REFERENCE_LINES.get(relative_path, ((), {}))
    counts = by_width.get(width)
    return dict(zip(names, counts)) if counts else None

MEASURE_JS = r"""
() => {
  const footer = document.querySelector('footer');
  const wrap = footer ? footer.querySelector(':scope > .max-w-7xl') : null;
  const group = document.querySelector('.floating-buttons');
  const visible = (el) => {
    if (!el) return false;
    const style = getComputedStyle(el);
    return style.display !== 'none' && style.visibility !== 'hidden' && parseFloat(style.opacity) > 0.05;
  };
  // O "voltar ao topo" entra com transição de opacidade; conta pelo estado
  // final (.is-visible), não pela opacidade do quadro medido.
  const shown = (el) => el.classList.contains('floating-btn--top') ? el.classList.contains('is-visible') : visible(el);
  const buttonRects = group
    ? [...group.querySelectorAll('.floating-btn')].filter(shown).map((el) => el.getBoundingClientRect())
    : [];
  const overlaps = (a, b) => {
    const width = Math.min(a.right, b.right) - Math.max(a.left, b.left);
    const height = Math.min(a.bottom, b.bottom) - Math.max(a.top, b.top);
    return width > 0.5 && height > 0.5;
  };
  const hits = [];
  const roots = footer ? [footer] : [...document.querySelectorAll('main')];
  roots.forEach((root) => {
    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.textContent.trim()) continue;
      const parent = node.parentElement;
      if (!parent || parent.closest('.floating-buttons') || !visible(parent)) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.width < 0.5 || rect.height < 0.5) continue;
        if (buttonRects.some((button) => overlaps(rect, button))) {
          hits.push(node.textContent.trim().replace(/\s+/g, ' ').slice(0, 90));
          break;
        }
      }
    }
    root.querySelectorAll('a, button, img').forEach((el) => {
      if (el.closest('.floating-buttons') || !visible(el)) return;
      const rect = el.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) return;
      if (buttonRects.some((button) => overlaps(rect, button))) {
        hits.push((el.getAttribute('aria-label') || el.innerText || el.getAttribute('alt') || el.tagName).trim().slice(0, 90));
      }
    });
  });
  // Menor distância lateral entre um botão flutuante e um controle na mesma
  // faixa vertical. O anel de foco dos botões avança 5 px.
  let controlGap = null;
  let controlGapName = null;
  roots.forEach((root) => {
    root.querySelectorAll('a, button').forEach((el) => {
      if (el.closest('.floating-buttons') || !visible(el)) return;
      const rect = el.getBoundingClientRect();
      if (rect.width < 1 || rect.height < 1) return;
      buttonRects.forEach((button) => {
        if (rect.bottom <= button.top - 5 || rect.top >= button.bottom + 5) return;
        const gap = Math.max(button.left - rect.right, rect.left - button.right);
        if (controlGap === null || gap < controlGap) {
          controlGap = gap;
          controlGapName = (el.getAttribute('aria-label') || el.innerText || el.tagName).trim().replace(/\s+/g, ' ').slice(0, 60);
        }
      });
    });
  });
  let lastBottom = null;
  if (footer) {
    const walker = document.createTreeWalker(footer, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.height < 0.5) continue;
        if (lastBottom === null || rect.bottom > lastBottom) lastBottom = rect.bottom;
      }
    }
  }
  const footerRect = footer ? footer.getBoundingClientRect() : null;
  const groupRect = group ? group.getBoundingClientRect() : null;
  const centerOf = (rect) => rect.left + rect.width / 2;
  const contentBox = (el) => {
    const rect = el.getBoundingClientRect();
    const style = getComputedStyle(el);
    return {
      left: rect.left + parseFloat(style.paddingLeft) + parseFloat(style.borderLeftWidth),
      right: rect.right - parseFloat(style.paddingRight) - parseFloat(style.borderRightWidth),
    };
  };
  const lineCount = (el) => {
    const tops = [];
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.textContent.trim()) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.width < 0.5 || rect.height < 0.5) continue;
        if (!tops.some((top) => Math.abs(top - rect.top) < 4)) tops.push(rect.top);
      }
    }
    return tops.length;
  };
  // Cada bloco é comparado com a área útil de quem o contém: a borda
  // esquerda e a direita precisam coincidir, como no 331a974.
  const blocks = [];
  const lines = {};
  const noteBlock = (name, box, container) => {
    blocks.push({name, left: box.left, right: box.right, containerLeft: container.left, containerRight: container.right});
  };
  const creditNames = ['aviso legal', 'direitos', 'crédito do desenvolvedor'];
  const centerShifts = [];
  const noteShift = (name, value) => {
    if (value === null || Number.isNaN(value)) return;
    centerShifts.push({ name, shift: value });
  };
  const lineShifts = (el, axis) => {
    const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
    while (walker.nextNode()) {
      const node = walker.currentNode;
      if (!node.textContent.trim()) continue;
      if (node.parentElement && node.parentElement.closest('a, button')) continue;
      const range = document.createRange();
      range.selectNodeContents(node);
      for (const rect of range.getClientRects()) {
        if (rect.width < 0.5 || rect.height < 0.5) continue;
        noteShift(node.textContent.trim().replace(/\s+/g, ' ').slice(0, 42), centerOf(rect) - axis);
      }
    }
  };
  if (wrap) {
    const axis = centerOf(wrap.getBoundingClientRect());
    const credit = wrap.querySelector(':scope > .border-t');
    if (credit) {
      const creditBox = contentBox(credit);
      noteBlock('créditos', creditBox, contentBox(wrap));
      [...credit.children].filter(visible).forEach((child, index) => {
        const name = creditNames[index] || `bloco ${index + 1} dos créditos`;
        noteBlock(name, child.getBoundingClientRect(), creditBox);
        lines[name] = lineCount(child);
      });
      credit.querySelectorAll(':scope > p, :scope > a').forEach((child) => {
        if (getComputedStyle(child).display.includes('flex')) {
          const kids = [...child.children].filter(visible);
          if (!kids.length) return;
          const left = Math.min(...kids.map((el) => el.getBoundingClientRect().left));
          const right = Math.max(...kids.map((el) => el.getBoundingClientRect().right));
          noteShift('crédito do desenvolvedor', (left + right) / 2 - axis);
        } else {
          lineShifts(child, axis);
        }
      });
    }
    const logo = footer.querySelector('img[alt="Regularize Consultoria"]');
    if (logo) {
      const contentLeft = wrap.getBoundingClientRect().left + parseFloat(getComputedStyle(wrap).paddingLeft);
      noteShift('logo do rodapé', logo.getBoundingClientRect().left - contentLeft);
      if (window.innerWidth < 768) {
        footer.querySelectorAll('h2, h4').forEach((heading) => {
          const text = heading.textContent.trim();
          if (text !== 'Navegação' && text !== 'Contato') return;
          noteShift(text, heading.getBoundingClientRect().left - logo.getBoundingClientRect().left);
        });
      }
    }
  }
  const closer = document.querySelector('main .mt-12.text-center');
  if (closer && closer.parentElement) {
    const axis = centerOf(closer.parentElement.getBoundingClientRect());
    const closerBox = contentBox(closer);
    noteBlock('fechamento do comunicado', closerBox, contentBox(closer.parentElement));
    const link = closer.querySelector(':scope > a');
    if (link && visible(link)) noteShift('Voltar ao Início', centerOf(link.getBoundingClientRect()) - axis);
    const copy = closer.querySelector(':scope > p');
    if (copy) {
      lineShifts(copy, axis);
      noteBlock('direitos do comunicado', copy.getBoundingClientRect(), closerBox);
      lines['direitos do comunicado'] = lineCount(copy);
    }
  }
  const pageEnd = document.documentElement.scrollHeight - scrollY;
  const lastBlock = footer || [...document.querySelectorAll('main')].pop();
  return {
    paddingBottom: wrap ? parseFloat(getComputedStyle(wrap).paddingBottom) : null,
    gapBelowLastText: footerRect && lastBottom !== null ? footerRect.bottom - lastBottom : null,
    belowLastBlock: lastBlock ? pageEnd - lastBlock.getBoundingClientRect().bottom : null,
    groupHeight: groupRect ? groupRect.height : null,
    groupInView: groupRect ? groupRect.top >= 0 && groupRect.bottom <= innerHeight + 0.5 : null,
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    hits: [...new Set(hits)],
    controlGap,
    controlGapName,
    hasFooter: Boolean(footer),
    hasFloating: Boolean(group),
    centerShifts,
    blocks,
    lines,
  };
}
"""

# Fechamento do comunicado com o último histórico aberto e fechado pelo
# teclado. Cada quadro pintado é amostrado: ancorada, a coluna fica 16 px acima
# do fechamento ou da linha de direitos; solta, fica a 24 px da base da janela
# e não alcança a linha de direitos. Um quadro na posição antiga falha aqui.
HISTORY_WIDTHS = [320, 360, 390, 414]
HISTORY_TOGGLE = '[aria-controls="aviso-historico-sngpc"]'
HISTORY_SAMPLER_JS = r"""
() => {
  const group = document.querySelector('.floating-buttons');
  const closer = document.querySelector('main .mt-12.text-center');
  const stops = [closer, closer.querySelector(':scope > p')];
  window.__historyFrames = [];
  window.__historySampling = true;
  const sample = () => {
    const g = group.getBoundingClientRect();
    const tops = stops.map((el) => el.getBoundingClientRect().top);
    const docked = group.classList.contains('is-docked');
    let problem = null;
    if (g.top < 0 || g.bottom > innerHeight + 0.5) problem = 'coluna fora da janela';
    else if (docked && !tops.some((top) => Math.abs(g.bottom - (top - 16)) <= 1)) problem = `ancorada a ${g.bottom.toFixed(1)} px, fora das paradas ${tops.map((t) => (t - 16).toFixed(1)).join('/')}`;
    else if (!docked && Math.abs(g.bottom - (innerHeight - 24)) > 1) problem = `solta a ${g.bottom.toFixed(1)} px da base`;
    else if (!docked && g.bottom > tops[1] - 16 + 1 && tops[1] < innerHeight) problem = 'solta sobre a linha de direitos';
    if (problem) window.__historyFrames.push(problem);
  };
  const tick = () => requestAnimationFrame(() => setTimeout(() => {
    if (!window.__historySampling) return;
    sample();
    tick();
  }, 0));
  tick();
}
"""



class QuietHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT.resolve()), **kwargs)

    def log_message(self, format, *args):
        pass


def _browser():
    """Chromium num processo limpo.

    A consulta da Farmácia Popular usa o Playwright síncrono no processo do
    pytest e deixa o loop do asyncio ativo. Os outros testes de layout já
    abrem o navegador num subprocesso; este faz o mesmo.
    """
    server = ThreadingHTTPServer(("127.0.0.1", 0), QuietHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    from playwright.sync_api import sync_playwright

    playwright = sync_playwright().start()
    browser = None
    try:
        browser = playwright.chromium.launch(headless=True)
        yield server.server_address[1], browser
    finally:
        if browser is not None:
            browser.close()
        playwright.stop()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def _url(port, relative_path):
    return f"http://127.0.0.1:{port}/{Path(relative_path).as_posix()}"


def _open(page, port, relative_path):
    response = page.goto(_url(port, relative_path), wait_until="domcontentloaded", timeout=20000)
    assert response is not None and response.ok, relative_path
    page.evaluate("() => document.fonts.ready")


def _measure(page, width, scroll):
    height = 844 if width < 768 else 900
    page.set_viewport_size({"width": width, "height": height})
    # A coluna fixa é reposicionada pelo main.js no evento de rolagem; a
    # medição espera dois quadros, como a tela já pintada que o usuário vê.
    page.evaluate(
        """async (scroll) => {
            document.documentElement.style.scrollBehavior = 'auto';
            window.scrollTo(0, scroll === 'end' ? document.documentElement.scrollHeight : 0);
            await new Promise((done) => requestAnimationFrame(() => requestAnimationFrame(done)));
        }""",
        scroll,
    )
    return page.evaluate(MEASURE_JS)


def _problems(label, data, reference_padding, reference_lines=None):
    problems = []
    if data["overflowX"] > 1:
        problems.append(f"{label}: rolagem horizontal de {data['overflowX']} px")
    if data["hits"]:
        problems.append(f"{label}: botão cobre {data['hits'][:3]}")
    if data["hasFloating"] and data["groupInView"] is False:
        problems.append(f"{label}: controles flutuantes fora da janela no fim da página")
    if data["controlGap"] is not None and data["controlGap"] < 5:
        problems.append(
            f"{label}: {data['controlGapName']} a {data['controlGap']:.1f} px da coluna; "
            "o anel de foco de 5 px o tocaria"
        )
    if data["belowLastBlock"] is not None and data["belowLastBlock"] > 1:
        problems.append(
            f"{label}: faixa de {data['belowLastBlock']:.1f} px depois do último bloco da página"
        )
    for block in data.get("blocks") or []:
        left = block["left"] - block["containerLeft"]
        right = block["containerRight"] - block["right"]
        if abs(left) > 1 or abs(right) > 1:
            problems.append(
                f"{label}: {block['name']} com {block['right'] - block['left']:.0f} px de largura, "
                f"recuo {left:.0f}/{right:.0f} px, numa área útil de "
                f"{block['containerRight'] - block['containerLeft']:.0f} px "
                f"(no {REFERENCE_COMMIT} o bloco ocupa a área toda)"
            )
    for name, expected in (reference_lines or {}).items():
        found = data["lines"].get(name)
        if found != expected:
            problems.append(
                f"{label}: {name} em {found} linha(s); o {REFERENCE_COMMIT} quebra em {expected}"
            )
    if data["hasFooter"]:
        if reference_padding is None:
            problems.append(f"{label}: padding de referência ausente")
        elif abs(data["paddingBottom"] - reference_padding) > 1:
            problems.append(
                f"{label}: padding-bottom {data['paddingBottom']} px "
                f"difere dos {reference_padding} px em {REFERENCE_WIDTH} px"
            )
        if data["gapBelowLastText"] is not None and abs(data["gapBelowLastText"] - data["paddingBottom"]) > 16:
            problems.append(
                f"{label}: vão de {data['gapBelowLastText']:.1f} px abaixo do crédito "
                f"não acompanha o padding de {data['paddingBottom']} px"
            )
    for item in data.get("centerShifts") or []:
        if abs(item["shift"]) > 2:
            problems.append(
                f"{label}: {item['name']} fora da referência do container em {item['shift']:.1f} px"
            )
    return problems


def _collect(mode):
    failures = []
    browser_cm = _browser()
    port, browser = next(browser_cm)
    page = browser.new_page() if mode != "menu" else browser.new_page(viewport={"width": 390, "height": 844})
    try:
        if mode == "clearance":
            for relative_path in DETAIL_PAGES:
                if not (ROOT / relative_path).is_file():
                    failures.append(f"{relative_path}: arquivo ausente")
                    continue
                _open(page, port, relative_path)
                reference = _measure(page, REFERENCE_WIDTH, "end")
                reference_padding = reference["paddingBottom"]
                failures.extend(_problems(
                    f"{relative_path} @{REFERENCE_WIDTH} fim", reference, reference_padding,
                    _reference_lines(relative_path, REFERENCE_WIDTH),
                ))
                for width in DETAIL_WIDTHS:
                    if width == REFERENCE_WIDTH:
                        continue
                    for scroll in ("start", "end"):
                        data = _measure(page, width, scroll)
                        if scroll == "start":
                            if data["overflowX"] > 1:
                                failures.append(f"{relative_path} @{width} início: rolagem horizontal")
                            continue
                        failures.extend(_problems(
                            f"{relative_path} @{width} {scroll}", data, reference_padding,
                            _reference_lines(relative_path, width),
                        ))
        elif mode == "all":
            for path in public_html_paths():
                relative_path = path.relative_to(ROOT).as_posix()
                _open(page, port, relative_path)
                reference = _measure(page, REFERENCE_WIDTH, "end")
                for width in GENERAL_WIDTHS:
                    data = reference if width == REFERENCE_WIDTH else _measure(page, width, "end")
                    failures.extend(_problems(
                        f"{relative_path} @{width}", data, reference["paddingBottom"],
                        _reference_lines(relative_path, width),
                    ))
        elif mode == "historico":
            relative_path = "comunicado/index.html"
            for width in HISTORY_WIDTHS:
                label = f"{relative_path} @{width}"
                page.set_viewport_size({"width": width, "height": 844})
                _open(page, port, relative_path)
                page.evaluate("() => { document.documentElement.style.scrollBehavior = 'auto'; }")
                toggle = page.locator(HISTORY_TOGGLE)

                def sampled(action, settle_ms=600):
                    page.evaluate(HISTORY_SAMPLER_JS)
                    action()
                    page.wait_for_timeout(settle_ms)
                    page.evaluate("() => { window.__historySampling = false; }")
                    return sorted(set(page.evaluate("() => window.__historyFrames")))

                def end_state(step):
                    data = _measure(page, width, "end")
                    failures.extend(_problems(f"{label} {step}", data, None, _reference_lines(relative_path, width)))

                end_state("histórico fechado")
                page.locator("main .mt-12.text-center > a[href='/']").focus()
                page.keyboard.press("Shift+Tab")
                if not toggle.evaluate("el => document.activeElement === el"):
                    failures.append(f"{label}: Shift+Tab não chegou ao último histórico")
                    continue
                for problem in sampled(lambda: page.keyboard.press("Enter")):
                    failures.append(f"{label} ao abrir pelo teclado: {problem}")
                if toggle.get_attribute("aria-expanded") != "true":
                    failures.append(f"{label}: Enter não abriu o histórico")
                end_state("histórico aberto")

                def wheel_up_and_down():
                    page.mouse.move(width / 2, 400)
                    for delta in [-90] * 12 + [90] * 14:
                        page.mouse.wheel(0, delta)
                        page.wait_for_timeout(30)

                for problem in sampled(wheel_up_and_down, 900):
                    failures.append(f"{label} rolando com o histórico aberto: {problem}")
                page.evaluate("() => window.scrollTo(0, document.documentElement.scrollHeight)")
                for problem in sampled(lambda: page.keyboard.press("Enter")):
                    failures.append(f"{label} ao fechar pelo teclado: {problem}")
                if toggle.get_attribute("aria-expanded") != "false":
                    failures.append(f"{label}: Enter não fechou o histórico")
                end_state("histórico fechado de novo")
        elif mode == "menu":
            page.goto(_url(port, "index.html"), wait_until="domcontentloaded")
            toggle = page.locator("#menu-toggle")
            menu = page.locator("#mobile-menu")
            toggle.focus()
            if not toggle.evaluate("el => document.activeElement === el"):
                failures.append("foco não chegou ao botão do menu")
            page.keyboard.press("Enter")
            if not menu.is_visible():
                failures.append("Enter não abriu o menu")
            if toggle.get_attribute("aria-expanded") != "true":
                failures.append("aria-expanded não ficou true")
            if toggle.get_attribute("aria-label") != "Fechar menu de navegação":
                failures.append("rótulo não mudou para fechar")
            overflow = page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
            if overflow > 1:
                failures.append(f"menu aberto com rolagem horizontal de {overflow} px")
            page.keyboard.press("Escape")
            if not menu.is_hidden():
                failures.append("Escape não fechou o menu")
            if toggle.get_attribute("aria-expanded") != "false":
                failures.append("aria-expanded não voltou para false")
            if toggle.get_attribute("aria-label") != "Abrir menu de navegação":
                failures.append("rótulo não voltou para abrir")
            if not toggle.evaluate("el => document.activeElement === el"):
                failures.append("foco não voltou ao botão depois do Escape")
            page.keyboard.press("Enter")
            if not menu.is_visible():
                failures.append("o menu não reabriu")
            page.locator("#mobile-menu a[href='/contato/']").click()
            page.wait_for_url("**/contato/**")
            if not page.locator("h1").is_visible():
                failures.append("o destino do menu não mostrou o título")
        else:
            failures.append(f"modo desconhecido: {mode}")
    finally:
        page.close()
        try:
            next(browser_cm)
        except StopIteration:
            pass
    return failures


def _run(mode):
    env = os.environ.copy()
    env["PYTHONIOENCODING"] = "utf-8"
    completed = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), mode],
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=240,
        env=env,
    )
    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert not payload["failures"], "\n".join(payload["failures"])


def test_reference_table_covers_every_measured_width():
    for relative_path, (_, by_width) in REFERENCE_LINES.items():
        missing = [width for width in DETAIL_WIDTHS if width not in by_width]
        assert not missing, f"{relative_path}: sem referência do {REFERENCE_COMMIT} em {missing}"


def test_footer_clearance_matches_the_wide_layout():
    _run("clearance")


def test_every_public_page_keeps_footer_and_viewport_clear():
    _run("all")


def test_comunicado_history_keeps_the_column_anchored():
    _run("historico")


def test_mobile_menu_opens_and_closes_from_the_keyboard():
    _run("menu")


if __name__ == "__main__":
    print(json.dumps({"failures": _collect(sys.argv[1])}, ensure_ascii=False))
