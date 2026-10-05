"""Menu mobile em telas baixas e na orientação paisagem.

O menu mobile (até 899 px) fica dentro do cabeçalho fixo, abaixo da faixa
regulatória. Ele crescia com o conteúdo, sem limite de altura: em 740x360 a
faixa (76,8 px) e a linha principal (80 px) já ocupavam 157 px, o menu ia até
506 px, e Notícias, Contato e AVISOS ficavam abaixo da borda. Como o cabeçalho
é fixo, rolar a janela movia só a página, e o Tab focava os últimos destinos
fora da tela.

Nas páginas representativas das duas famílias de CSS (a home com
components.css e o Comunicado com custom.min.css), em paisagem, em retrato, na
transição de 899 para 900 px e com zoom de 200%, o teste usa o menu como uma
pessoa: abre pelo botão; alcança cada destino rolando com a roda sobre o menu e
depois por Tab; ativa Notícias (Enter), Contato e AVISOS (clique); fecha por
Escape e pelo botão e reabre; e redimensiona com o menu aberto (para o desktop
e girando a tela). Os controles são achados pelo papel, nome e destino; a roda
vai no centro medido do menu. Em cada parada o menu cabe na janela, o destino
fica visível e é ele que recebe o clique no centro, nenhum botão flutuante
visível fica sobre o menu ou o botão de fechar, aria-expanded e o rótulo do
botão acompanham o estado e o foco nunca fica num controle oculto.

Os botões flutuantes (voltar ao topo e WhatsApp) recolhem enquanto o menu está
aberto. O teste guarda o estado deles antes de abrir, no início e no fim da
página, e confere que, fechado pelo botão ou por Escape, cada um volta como
estava: visível, clicável, na mesma posição e com a coluna ancorada ou não,
sem rolar a página. Em 899 px ele também passa a 900 e volta com o menu aberto
e o foco num destino.

No fim da página, a coluna de voltar ao topo e WhatsApp, ancorada acima dos
créditos do rodapé pelo main.js, subia sobre o cabeçalho em telas baixas e
cobria o botão do menu (z-index 9999 contra 50): o teste também abre o menu ali.

O segundo teste mede, em todas as páginas que têm o cabeçalho, a altura dele
fechado, a ausência de faixa vazia e de rolagem horizontal; aberto, se o menu
cabe na janela e se o último destino pode ser trazido à vista; e, no fim da
página, se o botão do menu continua livre.

Roda em subprocesso, como os outros testes de navegador.
"""
import json
import subprocess
import sys
import threading
from concurrent.futures import ThreadPoolExecutor
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import ROOT, SITE_DIR, public_html_paths, subprocess_env


PAGES = (("components", "/"), ("custom.min", "/comunicado/"))
# (largura, altura, escala): paisagem de celulares, retrato, a transição de
# 899/900 px e 1280x720 com zoom de 200% (640x360 em px CSS, escala 2).
VIEWPORTS = (
    (740, 360, 1), (568, 320, 1), (667, 375, 1), (844, 390, 1), (896, 414, 1),
    (320, 568, 1), (390, 844, 1), (899, 600, 1), (640, 360, 2),
)
DESTINATIONS = (
    ("Sobre", "/sobre/"),
    ("Serviços", "/servicos/"),
    ("Manuais e POPs", "/manuais-e-pops/"),
    ("Farmácia Popular", "/farmacia-popular/"),
    ("Notícias", "/noticias/"),
    ("Contato", "/contato/"),
    ("AVISOS!", "/comunicado/"),
)
DESKTOP_WIDTH = 1024
# Geometria em todas as páginas: uma janela de cada altura da faixa.
GEOMETRY_VIEWPORTS = ((740, 360), (844, 390))

HELPERS = r"""
window.__menu = (() => {
  const toggle = () => document.getElementById('menu-toggle');
  const menu = () => document.getElementById('mobile-menu');
  const rendered = el => !!el && el.getClientRects().length > 0 && getComputedStyle(el).visibility === 'visible';
  const box = el => { const r = el.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, left: r.left, right: r.right}; };
  const hits = (a, b) => a.left < b.right - 0.5 && a.right > b.left + 0.5 && a.top < b.bottom - 0.5 && a.bottom > b.top + 0.5;
  // Parte do menu dentro da janela.
  const visibleMenu = () => { const r = box(menu()); return {top: Math.max(r.top, 0), bottom: Math.min(r.bottom, innerHeight), left: r.left, right: r.right}; };
  const free = el => {
    const r = el.getBoundingClientRect();
    const x = r.left + r.width / 2, y = r.top + r.height / 2;
    if (y < 0 || y >= innerHeight || x < 0 || x >= innerWidth) return false;
    const hit = document.elementFromPoint(x, y);
    return !!hit && (hit === el || el.contains(hit));
  };
  const floating = () => [...document.querySelectorAll('.floating-buttons .floating-btn')].filter(b => {
    const cs = getComputedStyle(b);
    return cs.visibility === 'visible' && parseFloat(cs.opacity) > 0.01 && b.getClientRects().length;
  });
  const describe = el => !el || el === document.body ? 'body' :
    (el.getAttribute('href') || el.id || el.textContent.trim() || el.tagName).replace(/\s+/g, ' ').slice(0, 40);
  return {
    state() {
      const t = toggle(), m = menu(), open = rendered(m);
      const over = [];
      if (open) {
        const area = visibleMenu();
        for (const b of floating()) {
          if (hits(box(b), area)) over.push('menu: ' + (b.getAttribute('aria-label') || b.className));
          if (rendered(t) && hits(box(b), box(t))) over.push('botão do menu: ' + (b.getAttribute('aria-label') || b.className));
        }
      }
      const active = document.activeElement;
      return {
        innerWidth, innerHeight, overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        expanded: t ? t.getAttribute('aria-expanded') : null, label: t ? t.getAttribute('aria-label') : null,
        toggleShown: rendered(t), toggleFree: rendered(t) && free(t), toggleBox: rendered(t) ? box(t) : null,
        open, menuBox: open ? box(m) : null, menuScroll: open ? [m.scrollTop, m.scrollHeight, m.clientHeight] : null,
        desktopNav: rendered(document.querySelector('#navbar nav[aria-label="Navegação principal"]')),
        floatingOver: over,
        active: describe(active), activeHidden: !!active && active !== document.body && !rendered(active),
        activeInMenu: !!active && !!m && m.contains(active),
      };
    },
    link(href) {
      const a = menu().querySelector(`a[href="${href}"]`);
      if (!a || !rendered(a)) return {exists: !!a, shown: false};
      const r = box(a), area = visibleMenu();
      return {exists: true, shown: true, top: r.top, bottom: r.bottom,
              visible: r.top >= area.top - 0.5 && r.bottom <= area.bottom + 0.5 && r.bottom <= innerHeight + 0.5,
              free: free(a), focused: document.activeElement === a};
    },
    wheelPoint() { const a = visibleMenu(); return {x: (a.left + a.right) / 2, y: (a.top + a.bottom) / 2}; },
    // Estado de cada botão flutuante: visível (visibilidade e opacidade),
    // clicável (o centro dele recebe o clique) e posição; e a coluna ancorada
    // ou não acima dos créditos do rodapé.
    floating() {
      const group = document.querySelector('.floating-buttons');
      const one = selector => {
        const b = group.querySelector(selector), cs = getComputedStyle(b), r = b.getBoundingClientRect();
        const visible = cs.visibility === 'visible' && parseFloat(cs.opacity) > 0.99 && b.getClientRects().length > 0;
        return {visible, interactive: visible && cs.pointerEvents !== 'none' && free(b), top: Math.round(r.top), left: Math.round(r.left)};
      };
      return {whatsapp: one('.floating-btn--whatsapp'), topo: one('.floating-btn--top'),
              docked: group.classList.contains('is-docked'), inert: group.hasAttribute('inert'), scrollY: Math.round(scrollY)};
    },
  };
})();
"""

PROBE = r'''
import json
import os
import sys

from playwright.sync_api import sync_playwright

from support import new_context

base, path, width, height, scale = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
destinations = json.loads(sys.argv[6])
desktop = int(sys.argv[7])
helpers = os.environ["MENU_MOBILE_JS"]
failures = []
label = f"{path} @{width}x{height}" + (f" escala {scale}" if scale != 1 else "")


def state():
    # Espera as transições finitas (os botões flutuantes recolhem em 0,3 s).
    page.evaluate("""() => Promise.all(document.getAnimations()
        .filter(a => a.effect && a.effect.getComputedTiming().endTime !== Infinity)
        .map(a => a.finished.catch(() => 0))).then(() => true)""")
    return page.evaluate("window.__menu.state()")


def check(where, expect_open):
    s = state()
    tag = f"{label} {where}"
    if s["overflowX"] > 0:
        failures.append(f"{tag}: rolagem horizontal de {s['overflowX']} px")
    if s["activeHidden"]:
        failures.append(f"{tag}: foco em controle oculto ({s['active']})")
    if s["toggleShown"]:
        want = "true" if expect_open else "false"
        if s["expanded"] != want:
            failures.append(f"{tag}: aria-expanded={s['expanded']}, esperado {want}")
        name = "Fechar menu de navegação" if expect_open else "Abrir menu de navegação"
        if s["label"] != name:
            failures.append(f"{tag}: rótulo do botão {s['label']!r}, esperado {name!r}")
        if not s["toggleFree"]:
            failures.append(f"{tag}: botão do menu coberto ou fora da janela")
    if s["open"] != expect_open:
        failures.append(f"{tag}: menu {'aberto' if s['open'] else 'fechado'}, esperado {'aberto' if expect_open else 'fechado'}")
    if s["open"]:
        bottom = s["menuBox"]["bottom"]
        if bottom > s["innerHeight"] + 0.5:
            failures.append(f"{tag}: o menu termina em {bottom:.0f} px, abaixo da janela ({s['innerHeight']} px)")
        failures.extend(f"{tag}: botão flutuante sobre o {over}" for over in s["floatingOver"])
    return s


def link(href):
    return page.evaluate("href => window.__menu.link(href)", href)


def floating_state():
    """Botões flutuantes depois do reposicionamento (dois quadros) e das transições."""
    page.evaluate("""() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))).then(() =>
        Promise.all(document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().endTime !== Infinity)
          .map(a => a.finished.catch(() => 0)))).then(() => true)""")
    return page.evaluate("window.__menu.floating()")


def floating_hidden(where):
    """Com o menu aberto, nenhum botão flutuante visível nem clicável."""
    during = floating_state()
    for name in ("whatsapp", "topo"):
        if during[name]["visible"] or during[name]["interactive"]:
            failures.append(f"{label} {where}: {name} visível ou clicável com o menu aberto ({during[name]})")


def floating_restored(before, where):
    """Ao fechar, cada botão volta ao estado de antes de abrir."""
    after = floating_state()
    tag = f"{label} {where}"
    if after["scrollY"] != before["scrollY"]:
        failures.append(f"{tag}: a página rolou de {before['scrollY']} para {after['scrollY']} px")
    if after["docked"] != before["docked"] or after["inert"] != before["inert"]:
        failures.append(f"{tag}: coluna ancorada/inert {before['docked']}/{before['inert']} → {after['docked']}/{after['inert']}")
    for name in ("whatsapp", "topo"):
        b, a = before[name], after[name]
        for key in ("visible", "interactive"):
            if a[key] != b[key]:
                failures.append(f"{tag}: {name} {key} era {b[key]}, ficou {a[key]}")
        if abs(a["top"] - b["top"]) > 1 or abs(a["left"] - b["left"]) > 1:
            failures.append(f"{tag}: {name} mudou de posição ({b['left']},{b['top']}) → ({a['left']},{a['top']})")
    return after


def go_end():
    """Tecla End e espera a rolagem parar."""
    page.keyboard.press("End")
    for _ in range(40):
        before = page.evaluate("scrollY")
        page.wait_for_timeout(100)
        if page.evaluate("scrollY") == before:
            break


def scroll_to(href, where):
    """Roda do mouse sobre o menu até o destino ficar inteiro à vista."""
    for _ in range(40):
        st = link(href)
        if st.get("visible") and st.get("free"):
            return True
        point = page.evaluate("window.__menu.wheelPoint()")
        page.mouse.move(point["x"], point["y"])
        page.mouse.wheel(0, 60)
        page.wait_for_timeout(60)
    failures.append(f"{label} {where}: {href} não fica à vista nem recebe o clique rolando o menu ({link(href)})")
    return False


def load(target=path):
    page.goto(base + target, wait_until="load")
    page.evaluate("document.fonts.ready.then(() => true)")


def open_by_button():
    button = page.get_by_role("button", name="Abrir menu de navegação")
    if button.count() != 1 or not button.is_visible():
        failures.append(f"{label}: botão 'Abrir menu de navegação' ausente ou oculto")
        return False
    return click(button, "abrir pelo botão")


def mobile_link(name, href):
    """Link de nome `name` e destino `href` na região que o botão controla.

    O nome acessível do AVISOS inclui a contagem do selo ("AVISOS! 6") e, no
    Comunicado, ele fica fora do <nav> do menu: a busca é no menu inteiro, pelo
    nome (parcial) e pelo endereço exato.
    """
    region = page.locator("#" + page.locator("#menu-toggle").get_attribute("aria-controls"))
    candidates = region.get_by_role("link", name=name)
    matches = [candidates.nth(i) for i in range(candidates.count()) if candidates.nth(i).get_attribute("href") == href]
    if len(matches) != 1:
        failures.append(f"{label}: destino {name!r} → {href} não encontrado no menu mobile ({len(matches)})")
        return None
    return matches[0]


def click(locator, what):
    """Clique real; se outro elemento recebe o clique, vira falha (sem derrubar a sonda)."""
    try:
        locator.click(timeout=5000)
        return True
    except Exception as error:  # noqa: BLE001
        lines = str(error).splitlines()
        blocker = next((line.strip()[:160] for line in lines if "intercepts pointer events" in line), lines[0][:160])
        failures.append(f"{label} {what}: clique não chega ao controle ({blocker})")
        return False


with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    context = new_context(browser, viewport={"width": width, "height": height}, device_scale_factor=scale)
    context.add_init_script(helpers)
    page = context.new_page()

    # 1. Abrir pelo botão; os destinos existem pelo nome e pelo endereço.
    load()
    check("fechado na carga", False)
    if open_by_button():
        check("aberto pelo botão", True)
        links = [mobile_link(name, href) for name, href in destinations]

        # 2. Rolando com a roda sobre o menu, cada destino fica à vista.
        for name, href in destinations:
            if scroll_to(href, "rolagem"):
                check(f"rolagem até {name}", True)

        # 3. Por Tab, a partir do botão, na ordem do menu.
        page.get_by_role("button", name="Fechar menu de navegação").focus()
        for name, href in destinations:
            page.keyboard.press("Tab")
            st = link(href)
            if not st.get("focused"):
                failures.append(f"{label} Tab: esperado foco em {name}, foco em {state()['active']}")
                break
            if not (st["visible"] and st["free"]):
                failures.append(f"{label} Tab: {name} focado fora da janela ou coberto ({st})")
            check(f"Tab até {name}", True)

        # 4. Escape fecha e devolve o foco ao botão; Enter reabre.
        page.keyboard.press("Escape")
        s = check("depois do Escape", False)
        if s["active"] != "menu-toggle":
            failures.append(f"{label} Escape: foco em {s['active']}, esperado no botão do menu")
        page.keyboard.press("Enter")
        check("reaberto pelo Enter", True)
        page.keyboard.press("Tab")
        if not link(destinations[0][1]).get("focused"):
            failures.append(f"{label} reabertura: o Tab não leva ao primeiro destino ({state()['active']})")

        # 5. O botão fecha e reabre.
        if click(page.get_by_role("button", name="Fechar menu de navegação"), "fechar pelo botão"):
            s = check("fechado pelo botão", False)
            if s["active"] != "menu-toggle":
                failures.append(f"{label} fechar pelo botão: foco em {s['active']}")
            if click(page.get_by_role("button", name="Abrir menu de navegação"), "reabrir pelo botão"):
                check("reaberto pelo botão", True)

    # 6. Os últimos destinos ativados de verdade: Notícias pelo teclado,
    #    Contato e AVISOS pelo clique depois de rolar o menu.
    for name, href, how in ([*destinations[-3], "Enter"], [*destinations[-2], "clique"], [*destinations[-1], "clique"]):
        load()
        if not open_by_button():
            break
        target = mobile_link(name, href)
        if target is None:
            continue
        if how == "Enter":
            page.get_by_role("button", name="Fechar menu de navegação").focus()
            for _ in range(len(destinations)):
                page.keyboard.press("Tab")
                if link(href).get("focused"):
                    break
            st = link(href)
            if not (st.get("focused") and st.get("visible")):
                failures.append(f"{label} ativar {name}: não chega focado e à vista ({st})")
                continue
        elif not scroll_to(href, f"ativar {name}"):
            continue
        try:
            with page.expect_navigation(timeout=15000):
                if how == "Enter":
                    page.keyboard.press("Enter")
                else:
                    target.click(timeout=5000)
        except Exception as error:  # noqa: BLE001
            failures.append(f"{label} ativar {name} ({how}): sem navegação ({str(error).splitlines()[0][:160]})")
            continue
        page.evaluate("document.fonts.ready.then(() => true)")
        arrived = page.evaluate("location.pathname")
        if arrived != href:
            failures.append(f"{label} ativar {name} ({how}): chegou em {arrived}, esperado {href}")
        check(f"chegada em {href}", False)

    # 7. Redimensionar com o menu aberto e o foco no último destino.
    load()
    if open_by_button():
        page.get_by_role("button", name="Fechar menu de navegação").focus()
        for _ in range(len(destinations)):
            page.keyboard.press("Tab")
        # Para o desktop: menu e botão somem; o foco não fica neles.
        page.set_viewport_size({"width": desktop, "height": max(height, 600)})
        page.wait_for_timeout(150)
        s = check("desktop com o menu aberto", False)
        if not s["desktopNav"]:
            failures.append(f"{label} desktop: navegação principal oculta")
        if s["toggleShown"]:
            failures.append(f"{label} desktop: botão do menu visível")
        # De volta: o estado do botão e o do menu continuam de acordo.
        page.set_viewport_size({"width": width, "height": height})
        page.wait_for_timeout(150)
        s = state()
        check("de volta do desktop", s["expanded"] == "true")
        # Girando a tela com o menu aberto e o foco no último destino.
        load()
        if open_by_button():
            page.get_by_role("button", name="Fechar menu de navegação").focus()
            for _ in range(len(destinations)):
                page.keyboard.press("Tab")
            page.set_viewport_size({"width": height, "height": width})
            page.wait_for_timeout(150)
            if page.evaluate("innerWidth") < 900:
                check("girado com o menu aberto", True)
                st = link(destinations[-1][1])
                if not (st.get("focused") and st.get("visible") and st.get("free")):
                    failures.append(f"{label} girado: o último destino perdeu o foco ou saiu da vista ({st})")
    # Os passos seguintes voltam à janela do caso.
    page.set_viewport_size({"width": width, "height": height})

    # 8. No fim da página: a coluna flutuante ancorada acima dos créditos do
    #    rodapé não pode cobrir o botão; o menu abre e o último destino chega.
    load()
    go_end()
    check("fim da página, fechado", False)
    if open_by_button():
        check("aberto no fim da página", True)
        if scroll_to(destinations[-1][1], "fim da página"):
            check("último destino no fim da página", True)

    # 9. Botões flutuantes antes de abrir e depois de fechar, pelo botão e por
    #    Escape, no início (voltar ao topo oculto) e no fim da página (visível
    #    e, onde a altura pede, a coluna ancorada acima dos créditos). Com o
    #    menu aberto eles recolhem; ao fechar, cada um volta como estava.
    for where in ("início", "fim"):
        load()
        if where == "fim":
            go_end()
        before = floating_state()
        if not before["whatsapp"]["visible"]:
            failures.append(f"{label} {where}: WhatsApp oculto antes de abrir o menu ({before['whatsapp']})")
        for how in ("botão", "Escape"):
            if not open_by_button():
                break
            floating_hidden(f"{where}, aberto")
            if how == "botão":
                if not click(page.get_by_role("button", name="Fechar menu de navegação"), f"{where}: fechar pelo botão"):
                    break
            else:
                page.keyboard.press("Escape")
            check(f"{where}, fechado por {how}", False)
            floating_restored(before, f"{where}, fechado por {how}")

    # 10. 899 → 900 → 899 px com o menu aberto e o foco em Contato: em 900 px
    #     a navegação desktop aparece, menu e botão somem sem levar o foco e os
    #     flutuantes voltam; de volta a 899 px, botão e menu seguem de acordo e,
    #     fechado o menu, os flutuantes voltam ao estado de antes de abrir.
    if width == 899:
        load()
        before = floating_state()
        if open_by_button():
            page.get_by_role("button", name="Fechar menu de navegação").focus()
            for _ in range(len(destinations)):
                page.keyboard.press("Tab")
                if link("/contato/").get("focused"):
                    break
            if not link("/contato/").get("focused"):
                failures.append(f"{label} 899→900: foco não chegou a Contato ({state()['active']})")
            page.set_viewport_size({"width": 900, "height": height})
            page.wait_for_timeout(150)
            s = check("900 px com o menu aberto", False)
            if not s["desktopNav"]:
                failures.append(f"{label} 900 px: navegação principal oculta")
            if s["toggleShown"]:
                failures.append(f"{label} 900 px: botão do menu visível")
            at900 = floating_state()
            for name in ("whatsapp", "topo"):
                if at900[name]["visible"] != before[name]["visible"] or at900[name]["interactive"] != before[name]["interactive"]:
                    failures.append(f"{label} 900 px: {name} não voltou ao estado de antes ({before[name]} → {at900[name]})")
            page.set_viewport_size({"width": 899, "height": height})
            page.wait_for_timeout(150)
            s = state()
            still_open = s["expanded"] == "true"
            check("de volta a 899 px", still_open)
            if still_open:
                floating_hidden("de volta a 899 px, aberto")
                if click(page.get_by_role("button", name="Fechar menu de navegação"), "899 px: fechar pelo botão"):
                    check("899 px, fechado pelo botão", False)
            floating_restored(before, "899→900→899, fechado")

    context.close()
    browser.close()
print(json.dumps({"failures": failures}, ensure_ascii=False))
'''

GEOMETRY_PROBE = r'''
import json
import sys

from playwright.sync_api import sync_playwright

from support import new_context

base, routes, viewports = sys.argv[1], json.loads(sys.argv[2]), json.loads(sys.argv[3])
MEASURE = r"""() => {
  const box = el => { const r = el.getBoundingClientRect(); return {top: r.top, bottom: r.bottom, height: r.height}; };
  const header = document.getElementById('navbar');
  const row = header.querySelector(':scope > div:first-child');
  const spacer = header.nextElementSibling;
  const after = spacer && spacer.nextElementSibling;
  return {
    overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
    banner: box(document.querySelector('.site-regulatory-banner')), header: box(header), row: box(row),
    spacer: spacer ? box(spacer) : null, content: after ? box(after) : null,
  };
}"""
OPEN = r"""() => {
  const menu = document.getElementById('mobile-menu');
  const links = [...menu.querySelectorAll('a[href]')];
  const last = links[links.length - 1];
  last.scrollIntoView({block: 'nearest'});
  const r = menu.getBoundingClientRect(), l = last.getBoundingClientRect();
  const hit = document.elementFromPoint(l.left + l.width / 2, l.top + l.height / 2);
  const floating = [...document.querySelectorAll('.floating-buttons .floating-btn')].filter(b => {
    const cs = getComputedStyle(b), q = b.getBoundingClientRect();
    return cs.visibility === 'visible' && parseFloat(cs.opacity) > 0.01 && q.width &&
      q.left < r.right && q.right > r.left && q.top < Math.min(r.bottom, innerHeight) && q.bottom > r.top;
  }).length;
  return {innerHeight, menuBottom: r.bottom, lastTop: l.top, lastBottom: l.bottom,
          lastFree: !!hit && (hit === last || last.contains(hit)), floating, count: links.length};
}"""
# Dois quadros (a coluna flutuante é reposicionada num requestAnimationFrame) e
# as transições finitas.
SETTLE = r"""() => new Promise(done => requestAnimationFrame(() => requestAnimationFrame(done))).then(() =>
  Promise.all(document.getAnimations().filter(a => a.effect && a.effect.getComputedTiming().endTime !== Infinity)
    .map(a => a.finished.catch(() => 0)))).then(() => true)"""
TOGGLE_FREE = r"""() => { const t = document.getElementById('menu-toggle'), r = t.getBoundingClientRect();
  const hit = document.elementFromPoint(r.left + r.width / 2, r.top + r.height / 2);
  return {free: !!hit && (hit === t || t.contains(hit)),
          blocker: hit && hit !== t && !t.contains(hit) ? ((hit.closest('a, button') || hit).getAttribute('aria-label') || hit.tagName) : null}; }"""
results = {}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for width, height in viewports:
        context = new_context(browser, viewport={"width": width, "height": height})
        page = context.new_page()
        for route in routes:
            page.goto(base + route, wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            closed = page.evaluate(MEASURE)
            page.get_by_role("button", name="Abrir menu de navegação").click()
            page.evaluate(SETTLE)
            opened = page.evaluate(OPEN)
            page.get_by_role("button", name="Fechar menu de navegação").click()
            page.evaluate("window.scrollTo({top: document.documentElement.scrollHeight, behavior: 'instant'})")
            page.evaluate(SETTLE)
            end = page.evaluate(TOGGLE_FREE)
            results[f"{route} @{width}x{height}"] = {"fechado": closed, "aberto": opened, "fim": end}
        context.close()
    browser.close()
print(json.dumps(results))
'''


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def _serve():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server, thread


def _stop(server, thread):
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


@pytest.fixture(scope="module")
def probes():
    server, thread = _serve()
    base = f"http://127.0.0.1:{server.server_port}"
    cases = [(family, path, viewport) for family, path in PAGES for viewport in VIEWPORTS]

    def run(case):
        _family, path, (width, height, scale) = case
        return subprocess.run(
            [sys.executable, "-c", PROBE, base, path, str(width), str(height), str(scale),
             json.dumps(DESTINATIONS, ensure_ascii=False), str(DESKTOP_WIDTH)],
            capture_output=True, text=True, encoding="utf-8", timeout=600,
            env=subprocess_env(MENU_MOBILE_JS=HELPERS),
        )

    try:
        with ThreadPoolExecutor(max_workers=4) as pool:
            completed = dict(zip(cases, pool.map(run, cases)))
    finally:
        _stop(server, thread)
    return completed


@pytest.mark.parametrize("family,path", PAGES, ids=[family for family, _ in PAGES])
@pytest.mark.parametrize("viewport", VIEWPORTS, ids=[f"{w}x{h}" + (f"@{s}x" if s != 1 else "") for w, h, s in VIEWPORTS])
def test_mobile_menu_fits_and_every_destination_is_reachable(probes, family, path, viewport):
    completed = probes[(family, path, viewport)]
    assert completed.returncode == 0, completed.stderr[-3000:]
    failures = json.loads(completed.stdout)["failures"]
    assert not failures, f"{len(failures)} falha(s):\n" + "\n".join(failures[:25])


def _header_routes():
    routes = []
    for page in public_html_paths():
        relative = page.relative_to(ROOT).as_posix()
        if relative.startswith(("tests/", ".")) or 'id="mobile-menu"' not in page.read_text(encoding="utf-8"):
            continue
        routes.append("/" + relative[: -len("index.html")] if relative.endswith("index.html") else "/" + relative)
    return routes


@pytest.fixture(scope="module")
def geometry():
    routes = _header_routes()
    server, thread = _serve()
    base = f"http://127.0.0.1:{server.server_port}"
    try:
        completed = subprocess.run(
            [sys.executable, "-c", GEOMETRY_PROBE, base, json.dumps(routes), json.dumps(GEOMETRY_VIEWPORTS)],
            capture_output=True, text=True, encoding="utf-8", timeout=900, env=subprocess_env(),
        )
    finally:
        _stop(server, thread)
    assert completed.returncode == 0, completed.stderr[-3000:]
    return routes, json.loads(completed.stdout)


def test_header_geometry_and_open_menu_on_every_page(geometry):
    routes, results = geometry
    assert len(routes) > 100, routes
    failures = []
    for key, result in results.items():
        closed, opened = result["fechado"], result["aberto"]
        width = int(key.rsplit("@", 1)[1].split("x")[0])
        banner, row = (76.8, 80) if width < 768 else (40, 96)
        if closed["overflowX"] > 0:
            failures.append(f"{key}: rolagem horizontal de {closed['overflowX']} px")
        if abs(closed["banner"]["height"] - banner) > 0.5 or abs(closed["header"]["top"] - banner) > 0.5:
            failures.append(f"{key}: faixa {closed['banner']['height']:.1f} px, cabeçalho em {closed['header']['top']:.1f} px")
        if abs(closed["header"]["height"] - row) > 0.5 or abs(closed["row"]["height"] - row) > 0.5:
            failures.append(f"{key}: cabeçalho fechado com {closed['header']['height']:.1f} px (esperado {row})")
        if closed["content"] and abs(closed["content"]["top"] - closed["header"]["bottom"]) > 0.5:
            failures.append(f"{key}: o conteúdo começa em {closed['content']['top']:.1f} px e o cabeçalho termina em "
                            f"{closed['header']['bottom']:.1f} px")
        if opened["count"] != 7:
            failures.append(f"{key}: menu com {opened['count']} destinos")
        if opened["menuBottom"] > opened["innerHeight"] + 0.5:
            failures.append(f"{key}: o menu termina em {opened['menuBottom']:.0f} px, abaixo da janela ({opened['innerHeight']} px)")
        if opened["lastBottom"] > opened["innerHeight"] + 0.5 or not opened["lastFree"]:
            failures.append(f"{key}: o último destino não pode ser trazido à vista ({opened['lastTop']:.0f}–{opened['lastBottom']:.0f} px)")
        if opened["floating"]:
            failures.append(f"{key}: {opened['floating']} botão(ões) flutuante(s) sobre o menu aberto")
        if not result["fim"]["free"]:
            failures.append(f"{key}: no fim da página o botão do menu fica sob {result['fim']['blocker']}")
    assert not failures, f"{len(failures)} falha(s):\n" + "\n".join(failures[:40])
