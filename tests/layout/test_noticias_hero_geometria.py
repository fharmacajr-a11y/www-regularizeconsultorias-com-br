"""Regressão de geometria dos cabeçalhos das notícias (Proposta A).

A folga externa do cabeçalho das notícias (hero) herdava as classes utilitárias
`py-10 sm:py-12 md:py-20` (2.5rem = 40 px abaixo de 640 px; 3rem = 48 px entre
640 e 767 px; 5rem = 80 px a partir de 768 px).
A Proposta A reduziu e unificou a folga externa em assets/css/pages/noticias-tipos.css:
- abaixo de 640 px: 1.5rem (24 px);
- de 640 a 767 px: 2rem (32 px);
- a partir de 768 px: 2.75rem (44 px).

O teste confere:
1. Detecção da folga antiga: rejeita a folga legada (40/48/80 px) e confirma que
   o detector sinaliza qualquer regressão para os valores antigos;
2. Comportamento corrigido nos três intervalos de viewport / breakpoints:
   abaixo de 640 px (320, 360, 390, 639 px), 640 a 767 px (640, 700, 767 px)
   e a partir de 768 px (768, 960, 1024, 1440, 1920 px);
3. Cobertura dos quatro tipos de notícia (Atualização, Informativo, Urgente e Orientação);
4. Cobertura das duas famílias de CSS (components.css + noticia-detalhe.css e custom.min.css);
5. Títulos curtos e longos, conferindo altura determinada pelo conteúdo;
6. Ausência de rolagem horizontal (overflowX == 0) e ausência de sobreposição
   entre os elementos internos (breadcrumb, selos, título, resumo);
7. Espera pelo assentamento das fontes por document.fonts.ready.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env

# Amostra representativa que cobre os 4 tipos, as 2 famílias e títulos curtos/longos
ARTICLES = (
    # slug, família, tipo, título
    ("anvisa-atualiza-fluxo-cbpf-in451-2026", "modular", "atualizacao", "curto"),
    ("anvisa-atualiza-acesso-sncr-afe-farmacias-privadas", "custom", "atualizacao", "longo"),
    ("anvisa-camara-tecnica-cosmetovigilancia", "custom", "informativo", "curto"),
    ("alteracao-cadastral-farmacia-popular-regularizacao", "modular", "informativo", "longo"),
    ("anvisa-prazo-adequacao-notificacao-alimentos-setembro-2026", "modular", "urgente", "medio"),
    ("sngpc-boas-praticas-evitar-pendencias", "custom", "orientacao", "curto"),
    ("crf-responsavel-tecnico-farmacias-drogarias", "modular", "orientacao", "longo"),
)

BREAKPOINTS = (
    # (largura, altura, categoria, padding_esperado_px)
    (320, 640, "abaixo_640", 24.0),
    (360, 780, "abaixo_640", 24.0),
    (390, 844, "abaixo_640", 24.0),
    (639, 900, "abaixo_640", 24.0),
    (640, 900, "640_a_767", 32.0),
    (700, 900, "640_a_767", 32.0),
    (767, 900, "640_a_767", 32.0),
    (768, 1024, "a_partir_768", 44.0),
    (960, 900, "a_partir_768", 44.0),
    (1024, 768, "a_partir_768", 44.0),
    (1440, 900, "a_partir_768", 44.0),
    (1920, 1080, "a_partir_768", 44.0),
)

LEGACY_PADDING = {
    "abaixo_640": 40.0,
    "640_a_767": 48.0,
    "a_partir_768": 80.0,
}

PROBE = r'''
import json
import sys
from playwright.sync_api import sync_playwright

import support

base, articles_json, breakpoints_json = sys.argv[1:4]
articles = json.loads(articles_json)
breakpoints = json.loads(breakpoints_json)

MEASURE_JS = """async () => {
    await document.fonts.ready;
    const header = document.querySelector('main > article > header');
    if (!header) return null;
    const panel = header.querySelector(':scope > div');
    const cs = window.getComputedStyle(header);
    const panelCs = panel ? window.getComputedStyle(panel) : null;

    const rect = el => {
        if (!el) return null;
        const r = el.getBoundingClientRect();
        return {
            left: r.left, top: r.top, width: r.width, height: r.height,
            bottom: r.bottom, right: r.right
        };
    };

    // Sobreposição: confere se cada elemento sequencial do painel fica estritamente acima do próximo
    const items = panel ? Array.from(panel.children).map(rect) : [];
    let overlapping = false;
    for (let i = 0; i < items.length - 1; i++) {
        if (items[i].bottom > items[i+1].top + 1.0) {
            overlapping = true;
        }
    }

    return {
        overflowX: document.documentElement.scrollWidth - document.documentElement.clientWidth,
        paddingTop: parseFloat(cs.paddingTop),
        paddingBottom: parseFloat(cs.paddingBottom),
        headerHeight: rect(header).height,
        panelHeight: panel ? rect(panel).height : 0,
        overlapping,
        hasPanel: !!panel
    };
}"""

results = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    for slug, family, tipo, title_type in articles:
        for width, height, category, expected_px in breakpoints:
            context = support.new_context(browser, allow=(base,), viewport={"width": width, "height": height})
            page = context.new_page()
            page.goto(f"{base}/noticias/{slug}/", wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            data = page.evaluate(MEASURE_JS)
            data["slug"] = slug
            data["family"] = family
            data["tipo"] = tipo
            data["title_type"] = title_type
            data["width"] = width
            data["height"] = height
            data["category"] = category
            data["expected_px"] = expected_px
            results.append(data)
            context.close()
    browser.close()

print(json.dumps(results))
'''


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def geometry_results():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        completed = subprocess.run(
            [
                sys.executable,
                "-c",
                PROBE,
                f"http://127.0.0.1:{server.server_port}",
                json.dumps(ARTICLES),
                json.dumps(BREAKPOINTS),
            ],
            capture_output=True,
            text=True,
            check=True,
            env=subprocess_env(),
        )
        yield json.loads(completed.stdout)
    finally:
        server.shutdown()


def test_detecta_folga_antiga_e_rejeita(geometry_results):
    """Confirma que a folga antiga (40px, 48px, 80px) não ocorre em nenhum caso."""
    for item in geometry_results:
        legacy = LEGACY_PADDING[item["category"]]
        slug = item["slug"]
        w = item["width"]
        pt = item["paddingTop"]
        pb = item["paddingBottom"]
        assert pt != legacy, f"{slug} em {w}px ainda tem folga antiga no topo: {pt}px (esperado {item['expected_px']}px)"
        assert pb != legacy, f"{slug} em {w}px ainda tem folga antiga na base: {pb}px (esperado {item['expected_px']}px)"


def test_validador_rejeita_valores_antigos_em_memoria():
    """Garante que a lógica do detector identifica e rejeita explicitamente a folga antiga se reintroduzida."""
    def _valida_folga(pt, pb, category):
        expected = 24.0 if category == "abaixo_640" else (32.0 if category == "640_a_767" else 44.0)
        legacy = LEGACY_PADDING[category]
        if pt == legacy or pb == legacy:
            return False, f"folga legada detectada: {pt}px/{pb}px"
        if abs(pt - expected) > 0.5 or abs(pb - expected) > 0.5:
            return False, f"folga incorreta: {pt}px/{pb}px != {expected}px"
        return True, "ok"

    # Confere que valores legados são rejeitados
    for cat, legacy_val in LEGACY_PADDING.items():
        ok, msg = _valida_folga(legacy_val, legacy_val, cat)
        assert not ok, f"Deveria ter rejeitado folga legada em {cat}: {msg}"

    # Confere que valores corrigidos da proposta A são aceitos
    assert _valida_folga(24.0, 24.0, "abaixo_640")[0]
    assert _valida_folga(32.0, 32.0, "640_a_767")[0]
    assert _valida_folga(44.0, 44.0, "a_partir_768")[0]


def test_folga_externa_corrigida_nos_breakpoints(geometry_results):
    """Confere que todos os artigos usam a proposta A em todos os breakpoints."""
    for item in geometry_results:
        slug = item["slug"]
        w = item["width"]
        expected = item["expected_px"]
        pt = item["paddingTop"]
        pb = item["paddingBottom"]
        assert abs(pt - expected) <= 0.5, f"{slug} em {w}px: paddingTop {pt}px != {expected}px"
        assert abs(pb - expected) <= 0.5, f"{slug} em {w}px: paddingBottom {pb}px != {expected}px"


def test_ausencia_de_rolagem_horizontal_e_sobreposicao(geometry_results):
    """Confere que não há estouro de rolagem nem sobreposição interna no cabeçalho."""
    for item in geometry_results:
        slug = item["slug"]
        w = item["width"]
        assert item["overflowX"] == 0, f"{slug} em {w}px tem rolagem horizontal: {item['overflowX']}px"
        assert not item["overlapping"], f"{slug} em {w}px tem sobreposição entre elementos do cabeçalho"
        assert item["hasPanel"], f"{slug} em {w}px não tem painel interno"


def test_altura_determinada_pelo_conteudo(geometry_results):
    """Confere que a altura do cabeçalho é determinada pelo conteúdo e que títulos longos geram cabeçalhos mais altos."""
    by_article_width = {}
    for item in geometry_results:
        by_article_width[(item["slug"], item["width"])] = item

    for w in (390, 700, 1440):
        # Atualizacao: curto vs longo
        curto = by_article_width[("anvisa-atualiza-fluxo-cbpf-in451-2026", w)]
        longo = by_article_width[("anvisa-atualiza-acesso-sncr-afe-farmacias-privadas", w)]
        assert longo["headerHeight"] > curto["headerHeight"], (
            f"Em {w}px: título longo ({longo['headerHeight']}px) deve ser mais alto que curto ({curto['headerHeight']}px)"
        )

        # Informativo: curto vs longo
        inf_curto = by_article_width[("anvisa-camara-tecnica-cosmetovigilancia", w)]
        inf_longo = by_article_width[("alteracao-cadastral-farmacia-popular-regularizacao", w)]
        assert inf_longo["headerHeight"] > inf_curto["headerHeight"], (
            f"Em {w}px: título longo informativo ({inf_longo['headerHeight']}px) deve ser mais alto que curto ({inf_curto['headerHeight']}px)"
        )
