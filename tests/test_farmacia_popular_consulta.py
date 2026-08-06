import copy
import functools
import json
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parents[1]
RECORDS_PATH = ROOT / "data" / "farmacia-popular" / "vagas-2026-07-28.json"
METADATA_PATH = ROOT / "data" / "farmacia-popular" / "metadados.json"
RECORDS = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
METADATA = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
RECORDS_URL = "**/data/farmacia-popular/vagas-2026-07-28.json"
METADATA_URL = "**/data/farmacia-popular/metadados.json"
INDICATORS = (
    "#fp-total-municipios",
    "#fp-vagas-totais",
    "#fp-vagas-preenchidas",
    "#fp-vagas-disponiveis",
    "#fp-indicator-date",
)
CONTROLS = ("#fp-search", "#fp-uf", "#fp-status", "#fp-clear", "#fp-prev", "#fp-next", "#fp-page-size")


class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="session")
def site_url():
    handler = functools.partial(QuietHandler, directory=str(ROOT))
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture(scope="session")
def browser():
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        yield browser
        browser.close()


@pytest.fixture
def page(browser):
    context = browser.new_context()
    page = context.new_page()
    try:
        yield page
    finally:
        context.close()


def open_consultation(page, site_url):
    page.goto(f"{site_url}/farmacia-popular/", wait_until="domcontentloaded")
    page.wait_for_function(
        "document.querySelector('#fp-result-count').textContent !== 'Carregando municípios…'"
    )


def assert_fatal_state(page):
    assert page.locator("#fp-error").is_visible()
    assert page.locator("#fp-loading").is_hidden()
    assert page.locator("#fp-result-count").text_content() == "Consulta indisponível."
    assert page.locator("#fp-table-body tr").count() == 0
    assert page.locator(".fp-table-scroll").is_hidden()
    assert page.locator("#fp-empty").is_hidden()
    assert page.locator("#fp-pagination").is_hidden()
    assert page.locator("#fp-pagination").evaluate("node => getComputedStyle(node).display") == "none"
    assert page.locator("#fp-page-info").text_content() == ""
    assert all(page.locator(selector).is_disabled() for selector in CONTROLS)
    assert all(page.locator(selector).text_content() == "—" for selector in INDICATORS)


def test_css_paginacao_hidden_prevalece_sobre_display_flex():
    css = (ROOT / "assets" / "css" / "pages" / "farmacia-popular.css").read_text(encoding="utf-8")
    matching_rules = [
        (selectors, declarations)
        for selectors, declarations in re.findall(r"([^{}]+)\{([^{}]*)\}", css)
        if ".fp-pagination.hidden" in selectors or ".fp-pagination[hidden]" in selectors
    ]
    assert matching_rules
    assert any(re.search(r"\bdisplay\s*:\s*none\s*;?", declarations) for _, declarations in matching_rules)


def test_cenario_a_carga_normal(page, site_url):
    open_consultation(page, site_url)

    assert page.locator("#fp-total-municipios").text_content() == "1.082"
    assert page.locator("#fp-vagas-totais").text_content() == "1.644"
    assert page.locator("#fp-vagas-preenchidas").text_content() == "0"
    assert page.locator("#fp-vagas-disponiveis").text_content() == "1.644"
    assert page.locator("#fp-uf option").count() - 1 == 26
    assert page.locator("#fp-table-body tr").count() == 25
    assert page.locator("#fp-page-info").text_content() == "Página 1 de 44"
    assert page.locator("#fp-pagination").is_visible()
    assert page.locator("#fp-loading").is_hidden()
    assert page.locator("#fp-error").is_hidden()


def test_cenario_b_busca_sem_resultado_oculta_paginacao(page, site_url):
    open_consultation(page, site_url)
    page.locator("#fp-search").fill("Município que certamente não existe")

    assert page.locator("#fp-result-count").text_content() == "0 municípios encontrados"
    assert page.locator("#fp-table-body tr").count() == 0
    assert page.locator("#fp-empty").is_visible()
    assert page.locator("#fp-pagination").evaluate("node => getComputedStyle(node).display") == "none"

    page.locator("#fp-search").fill("")
    page.locator("#fp-status").select_option("filled")
    assert page.locator("#fp-result-count").text_content() == "0 municípios encontrados"
    assert page.locator("#fp-pagination").evaluate("node => getComputedStyle(node).display") == "none"


def test_cenario_c_busca_sem_apostrofo_e_sem_acentos(page, site_url):
    open_consultation(page, site_url)
    search = page.locator("#fp-search")

    search.fill("Pau Darco")
    assert page.locator("#fp-table-body").get_by_text("Pau D'Arco", exact=True).count() >= 1

    search.fill("Pau D’Arco")
    assert page.locator("#fp-table-body").get_by_text("Pau D'Arco", exact=True).count() >= 1

    search.fill("Poxoreo")
    assert page.locator("#fp-table-body").get_by_text("Poxoréu", exact=True).count() == 1

    search.fill("Santa-Cruz")
    assert page.locator("#fp-table-body tr").count() >= 1

    sao_tome = copy.deepcopy(RECORDS[0])
    sao_tome["municipio_fonte_ms"] = "SAO TOME"
    sao_tome["municipio_exibicao"] = "São Tomé"
    metadata = copy.deepcopy(METADATA)
    metadata["quantidade_registros"] = 1
    metadata["quantidade_ufs"] = 1
    metadata["totais_vagas"] = {
        field: sao_tome[field]
        for field in ("vagas_totais", "vagas_preenchidas", "vagas_disponiveis")
    }
    page.route(RECORDS_URL, lambda route: route.fulfill(json=[sao_tome]))
    page.route(METADATA_URL, lambda route: route.fulfill(json=metadata))
    page.reload(wait_until="domcontentloaded")
    page.wait_for_function("document.querySelector('#fp-result-count').textContent === '1 município encontrado'")
    page.locator("#fp-search").fill("Sao Tome")
    assert page.locator("#fp-table-body").get_by_text("São Tomé", exact=True).count() == 1


def test_cenario_d_erro_http_no_json_principal(page, site_url):
    page.route(RECORDS_URL, lambda route: route.fulfill(status=500, body="erro"))
    open_consultation(page, site_url)
    assert_fatal_state(page)


@pytest.mark.parametrize(
    "invalid_records",
    [
        {},
        [{
            "codigo_ibge": "1234567",
            "uf": "SP",
            "municipio_fonte_ms": "TESTE",
            "municipio_exibicao": "Teste",
            "vagas_totais": 1,
            "vagas_preenchidas": 1,
            "vagas_disponiveis": 1,
        }],
    ],
    ids=("objeto", "aritmetica_inconsistente"),
)
def test_cenario_e_json_principal_invalido(page, site_url, invalid_records):
    page.route(RECORDS_URL, lambda route: route.fulfill(json=invalid_records))
    open_consultation(page, site_url)
    assert_fatal_state(page)


def test_cenario_f_codigo_ibge_duplicado(page, site_url):
    duplicated = [copy.deepcopy(RECORDS[0]), copy.deepcopy(RECORDS[0])]
    page.route(RECORDS_URL, lambda route: route.fulfill(json=duplicated))
    open_consultation(page, site_url)
    assert_fatal_state(page)


def test_cenario_g_metadados_divergentes(page, site_url):
    metadata = copy.deepcopy(METADATA)
    metadata["quantidade_registros"] += 1
    metadata["quantidade_ufs"] += 1
    metadata["totais_vagas"]["vagas_totais"] += 1
    page.route(METADATA_URL, lambda route: route.fulfill(json=metadata))
    open_consultation(page, site_url)
    assert_fatal_state(page)


def test_cenario_h_metadados_indisponiveis_usam_fallback(page, site_url):
    page.route(METADATA_URL, lambda route: route.fulfill(status=500, body="erro"))
    open_consultation(page, site_url)

    assert page.locator("#fp-meta-fallback").is_visible()
    assert page.locator("#fp-table-body tr").count() == 25
    assert all(page.locator(selector).is_enabled() for selector in ("#fp-search", "#fp-uf", "#fp-status", "#fp-clear", "#fp-page-size"))
    assert page.locator("#fp-total-municipios").text_content() == "1.082"
    assert page.locator("#fp-vagas-totais").text_content() == "1.644"
    assert page.locator("#fp-vagas-preenchidas").text_content() == "0"
    assert page.locator("#fp-vagas-disponiveis").text_content() == "1.644"
    assert page.locator("#fp-indicator-date").text_content() == "—"
    assert page.locator("#fp-error").is_hidden()
    assert page.locator("#fp-pagination").is_visible()
    page.locator("#fp-next").click()
    assert page.locator("#fp-page-info").text_content() == "Página 2 de 44"


def test_cenario_i_limites_de_paginacao(page, site_url):
    open_consultation(page, site_url)
    assert page.locator("#fp-prev").is_disabled()

    page.locator("#fp-page-size").select_option("100")
    assert page.locator("#fp-page-info").text_content() == "Página 1 de 11"
    assert page.locator("#fp-table-body tr").count() == 100
    for expected_page in range(2, 12):
        page.locator("#fp-next").click()
        assert page.locator("#fp-page-info").text_content() == f"Página {expected_page} de 11"
    assert page.locator("#fp-next").is_disabled()
    assert page.locator("#fp-table-body tr").count() == 82

    page.locator("#fp-page-size").select_option("25")
    assert page.locator("#fp-page-info").text_content() == "Página 1 de 44"
    assert page.locator("#fp-prev").is_disabled()
