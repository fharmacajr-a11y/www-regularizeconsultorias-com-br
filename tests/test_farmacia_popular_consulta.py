import copy
import functools
import json
import math
import re
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest
from playwright.sync_api import sync_playwright


ROOT = Path(__file__).parents[1]
RECORDS_PATH = ROOT / "data" / "farmacia-popular" / "vagas-2026-09-03.json"
METADATA_PATH = ROOT / "data" / "farmacia-popular" / "metadados.json"
RECORDS = json.loads(RECORDS_PATH.read_text(encoding="utf-8"))
METADATA = json.loads(METADATA_PATH.read_text(encoding="utf-8"))
RECORDS_URL = "**/data/farmacia-popular/vagas-2026-09-03.json"
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

    assert page.locator("#fp-total-municipios").text_content() == "1.541"
    assert page.locator("#fp-vagas-totais").text_content() == "3.082"
    assert page.locator("#fp-vagas-preenchidas").text_content() == "963"
    assert page.locator("#fp-vagas-disponiveis").text_content() == "2.119"
    assert page.locator("#fp-indicator-date").text_content() == "03/09/2026"
    assert page.locator("#fp-uf option").count() - 1 == 26
    assert page.locator("#fp-page-size").input_value() == "10"
    assert {"10", "25", "50"}.issubset(set(page.locator("#fp-page-size option").evaluate_all("options => options.map(option => option.value)")))
    assert page.locator("#fp-table-body tr").count() == min(10, len(RECORDS))
    assert page.locator("#fp-page-info").text_content() == f"Página 1 de {math.ceil(len(RECORDS) / 10)}"
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
    page.locator("#fp-status").select_option("unavailable")
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

    # Município com apóstrofo, presente na base de 03/09
    search.fill("Tanque Darca")
    assert page.locator("#fp-table-body").get_by_text("Tanque d'Arca", exact=True).count() == 1

    search.fill("Tanque d’Arca")
    assert page.locator("#fp-table-body").get_by_text("Tanque d'Arca", exact=True).count() == 1

    # Município do AC presente na base de 03/09
    search.fill("Rodrigues Alves")
    assert page.locator("#fp-table-body").get_by_text("Rodrigues Alves", exact=True).count() == 1

    # Município que ENTROU na relação de 03/09 (ausente na base de 20/08)
    search.fill("Placido de Castro")
    assert page.locator("#fp-table-body").get_by_text("Plácido de Castro", exact=True).count() == 1
    search.fill("PLÁCIDO DE CASTRO")
    assert page.locator("#fp-table-body").get_by_text("Plácido de Castro", exact=True).count() == 1

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
    assert page.locator("#fp-table-body tr").count() == min(10, len(RECORDS))
    assert all(page.locator(selector).is_enabled() for selector in ("#fp-search", "#fp-uf", "#fp-status", "#fp-clear", "#fp-page-size"))
    assert page.locator("#fp-total-municipios").text_content() == "1.541"
    assert page.locator("#fp-vagas-totais").text_content() == "3.082"
    assert page.locator("#fp-vagas-preenchidas").text_content() == "963"
    assert page.locator("#fp-vagas-disponiveis").text_content() == "2.119"
    assert page.locator("#fp-indicator-date").text_content() == "—"
    assert page.locator("#fp-error").is_hidden()
    assert page.locator("#fp-pagination").is_visible()
    page.locator("#fp-next").click()
    assert page.locator("#fp-page-info").text_content() == f"Página 2 de {math.ceil(len(RECORDS) / 10)}"


def test_cenario_i_limites_de_paginacao(page, site_url):
    open_consultation(page, site_url)
    assert page.locator("#fp-prev").is_disabled()
    assert page.locator("#fp-table-body tr").count() == min(10, len(RECORDS))

    page.locator("#fp-page-size").select_option("25")
    assert page.locator("#fp-page-info").text_content() == f"Página 1 de {math.ceil(len(RECORDS) / 25)}"
    assert page.locator("#fp-table-body tr").count() == min(25, len(RECORDS))
    page.locator("#fp-next").click()
    assert page.locator("#fp-page-info").text_content() == f"Página 2 de {math.ceil(len(RECORDS) / 25)}"

    page.locator("#fp-page-size").select_option("50")
    total_pages = math.ceil(len(RECORDS) / 50)
    assert page.locator("#fp-page-info").text_content() == f"Página 1 de {total_pages}"
    assert page.locator("#fp-table-body tr").count() == min(50, len(RECORDS))
    assert page.locator("#fp-prev").is_disabled()
    for expected_page in range(2, total_pages + 1):
        page.locator("#fp-next").click()
        assert page.locator("#fp-page-info").text_content() == f"Página {expected_page} de {total_pages}"
    assert page.locator("#fp-next").is_disabled()
    assert page.locator("#fp-table-body tr").count() == len(RECORDS) - 50 * (total_pages - 1)

    page.locator("#fp-page-size").select_option("10")
    assert page.locator("#fp-page-info").text_content() == f"Página 1 de {math.ceil(len(RECORDS) / 10)}"
    assert page.locator("#fp-table-body tr").count() == min(10, len(RECORDS))
    assert page.locator("#fp-prev").is_disabled()


def test_cenario_j_filtros_e_limpeza_preservam_page_size(page, site_url):
    open_consultation(page, site_url)

    page.locator("#fp-search").fill("Poxoreo")
    assert page.locator("#fp-table-body tr").count() == 1
    assert page.locator("#fp-page-size").input_value() == "10"
    assert page.locator("#fp-page-info").text_content() == "Página 1 de 1"

    page.locator("#fp-search").fill("")
    page.locator("#fp-uf").select_option("AC")
    ac_records = [record for record in RECORDS if record["uf"] == "AC"]
    assert page.locator("#fp-table-body tr").count() == min(10, len(ac_records))
    assert page.locator("#fp-page-info").text_content() == f"Página 1 de {math.ceil(len(ac_records) / 10)}"

    page.locator("#fp-status").select_option("available")
    available_ac_records = [record for record in ac_records if record["vagas_disponiveis"] > 0]
    assert page.locator("#fp-table-body tr").count() == min(10, len(available_ac_records))

    page.locator("#fp-clear").click()
    assert page.locator("#fp-search").input_value() == ""
    assert page.locator("#fp-uf").input_value() == ""
    assert page.locator("#fp-status").input_value() == ""
    assert page.locator("#fp-page-size").input_value() == "10"
    assert page.locator("#fp-page-info").text_content() == f"Página 1 de {math.ceil(len(RECORDS) / 10)}"


def test_cenario_k_filtro_vagas_preenchidas_retorna_registros_reais(page, site_url):
    open_consultation(page, site_url)

    filled_records = [record for record in RECORDS if record["vagas_preenchidas"] > 0]
    assert len(filled_records) == 963

    page.locator("#fp-status").select_option("filled")
    assert page.locator("#fp-result-count").text_content() == "963 municípios encontrados"
    assert page.locator("#fp-table-body tr").count() == 10  # primeira página, page size 10
    assert page.locator("#fp-page-info").text_content() == f"Página 1 de {math.ceil(963 / 10)}"
    assert page.locator("#fp-empty").is_hidden()
    assert page.locator("#fp-pagination").is_visible()

    # Validar que todos os registros exibidos possuem vagas_preenchidas > 0
    rows = page.locator("#fp-table-body tr")
    for idx in range(rows.count()):
        row = rows.nth(idx)
        preenchidas_cell = row.locator("td:nth-child(4)").text_content()
        assert int(preenchidas_cell) > 0


def test_cenario_l_registro_parcial_2_1_1(page, site_url):
    open_consultation(page, site_url)

    # Tanque d'Arca (AL) possui exatamente 2 vagas totais, 1 preenchida e 1 disponível
    target = next(
        record for record in RECORDS
        if record["uf"] == "AL" and record["municipio_exibicao"] == "Tanque d'Arca"
    )
    assert target["vagas_totais"] == 2
    assert target["vagas_preenchidas"] == 1
    assert target["vagas_disponiveis"] == 1

    page.locator("#fp-search").fill("Tanque d'Arca")
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    assert page.locator("#fp-table-body tr").count() == 1

    row = page.locator("#fp-table-body tr").first
    assert row.locator("td:nth-child(1)").text_content() == "AL"
    assert row.locator("td:nth-child(2)").text_content() == "Tanque d'Arca"
    assert row.locator("td:nth-child(3)").text_content() == "2"
    assert row.locator("td:nth-child(4)").text_content() == "1"
    assert row.locator("td:nth-child(5)").text_content() == "1"
    assert row.locator("td:nth-child(6) span").text_content() == "Com vagas"
    assert "fp-status--available" in (row.locator("td:nth-child(6) span").get_attribute("class") or "")

    # Deve aparecer no filtro 'available' (vagas_disponiveis > 0)
    page.locator("#fp-status").select_option("available")
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    assert page.locator("#fp-table-body tr").count() == 1
    assert page.locator("#fp-table-body tr").first.locator("td:nth-child(2)").text_content() == "Tanque d'Arca"

    # Deve aparecer simultaneamente no filtro 'filled' (vagas_preenchidas > 0)
    page.locator("#fp-status").select_option("filled")
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    assert page.locator("#fp-table-body tr").count() == 1
    assert page.locator("#fp-table-body tr").first.locator("td:nth-child(2)").text_content() == "Tanque d'Arca"

    # NÃO deve aparecer no filtro 'unavailable' (vagas_disponiveis === 0)
    page.locator("#fp-status").select_option("unavailable")
    assert page.locator("#fp-result-count").text_content() == "0 municípios encontrados"
    assert page.locator("#fp-table-body tr").count() == 0
    assert page.locator("#fp-empty").is_visible()


def test_cenario_m_links_auxiliares_pdf_e_noticia_respondem_com_sucesso(page, site_url):
    open_consultation(page, site_url)

    pdf_link = page.locator('a:has-text("Ver lista em PDF")')
    assert pdf_link.is_visible()
    pdf_href = pdf_link.get_attribute("href")
    assert pdf_href == "/noticias/credenciamento-farmacia-popular-municipios-com-vagas/farmacia-popular-municipios-vagas-03-09-2026.pdf"

    pdf_response = page.request.get(f"{site_url}{pdf_href}")
    assert pdf_response.status == 200
    assert pdf_response.body().startswith(b"%PDF-")

    news_link = page.locator('a:has-text("Ler notícia relacionada")')
    assert news_link.is_visible()
    news_href = news_link.get_attribute("href")
    assert news_href == "/noticias/credenciamento-farmacia-popular-municipios-com-vagas/"

    news_response = page.request.get(f"{site_url}{news_href}")
    assert news_response.status == 200


def test_cenario_n_registro_sem_preenchimento_2_0_2(page, site_url):
    """Belo Monte (AL) na base de 03/09 tem 2 totais, 0 preenchidas e 2 disponíveis."""
    open_consultation(page, site_url)

    target = next(
        record for record in RECORDS
        if record["uf"] == "AL" and record["municipio_exibicao"] == "Belo Monte"
    )
    assert target["vagas_totais"] == 2
    assert target["vagas_preenchidas"] == 0
    assert target["vagas_disponiveis"] == 2

    page.locator("#fp-search").fill("Belo Monte")
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    row = page.locator("#fp-table-body tr").first
    assert row.locator("td:nth-child(3)").text_content() == "2"
    assert row.locator("td:nth-child(4)").text_content() == "0"
    assert row.locator("td:nth-child(5)").text_content() == "2"
    assert row.locator("td:nth-child(6) span").text_content() == "Com vagas"

    # Aparece em 'available' e NÃO aparece em 'filled'.
    page.locator("#fp-status").select_option("available")
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    page.locator("#fp-status").select_option("filled")
    assert page.locator("#fp-result-count").text_content() == "0 municípios encontrados"


def test_cenario_o_situacoes_refletem_a_base_real(page, site_url):
    """Contagens dos filtros derivadas do dataset, sem números presumidos."""
    open_consultation(page, site_url)

    available = [r for r in RECORDS if r["vagas_disponiveis"] > 0]
    unavailable = [r for r in RECORDS if r["vagas_disponiveis"] == 0]
    filled = [r for r in RECORDS if r["vagas_preenchidas"] > 0]
    assert len(available) == len(RECORDS) == 1541
    assert len(unavailable) == 0
    assert len(filled) == 963

    page.locator("#fp-status").select_option("available")
    assert page.locator("#fp-result-count").text_content() == "1.541 municípios encontrados"

    page.locator("#fp-status").select_option("filled")
    assert page.locator("#fp-result-count").text_content() == "963 municípios encontrados"

    # Nenhum município da relação de 03/09 está sem vaga disponível.
    page.locator("#fp-status").select_option("unavailable")
    assert page.locator("#fp-result-count").text_content() == "0 municípios encontrados"
    assert page.locator("#fp-table-body tr").count() == 0
    assert page.locator("#fp-empty").is_visible()
    assert page.locator("#fp-pagination").evaluate("node => getComputedStyle(node).display") == "none"


def test_cenario_p_paginacao_reflete_o_tamanho_da_base(page, site_url):
    """ceil(1541 / page_size) para cada tamanho de página oferecido."""
    open_consultation(page, site_url)
    assert len(RECORDS) == 1541

    for page_size in (10, 25, 50, 100):
        page.locator("#fp-page-size").select_option(str(page_size))
        esperado = math.ceil(len(RECORDS) / page_size)
        assert page.locator("#fp-page-info").text_content() == f"Página 1 de {esperado}"
        assert page.locator("#fp-table-body tr").count() == min(page_size, len(RECORDS))

    # Combinar filtros não pode duplicar registros.
    page.locator("#fp-page-size").select_option("100")
    page.locator("#fp-uf").select_option("AC")
    page.locator("#fp-status").select_option("available")
    ac_disponiveis = [r for r in RECORDS if r["uf"] == "AC" and r["vagas_disponiveis"] > 0]
    nomes = page.locator("#fp-table-body tr td:nth-child(2)").all_text_contents()
    assert len(nomes) == len(ac_disponiveis)
    assert len(set(nomes)) == len(nomes)


def _track_navigations(page):
    """Registra navegações do frame principal (reload/submit) após a carga inicial."""
    navegacoes = []
    page.on(
        "framenavigated",
        lambda frame: navegacoes.append(frame.url) if frame == page.main_frame else None,
    )
    return navegacoes


def test_cenario_q_enter_na_busca_nao_recarrega_a_pagina(page, site_url):
    """Enter no campo de busca confirma o filtro; não submete o <form>.

    Os filtros vivem dentro de <form id="fp-filters"> e o campo de busca é o
    único controle de texto, então o Enter dispara a submissão implícita do
    formulário. Sem listener de 'submit' o navegador faz um GET na própria URL:
    a página recarrega, o input é esvaziado e todos os filtros voltam ao estado
    inicial. Antes da correção este teste falhava na primeira asserção de URL
    (ia para '/farmacia-popular/?') e também no valor preservado do input.
    """
    open_consultation(page, site_url)
    navegacoes = _track_navigations(page)

    page.fill("#fp-search", "Poxoréu")
    page.wait_for_timeout(150)

    url_antes = page.url
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    assert page.locator("#fp-table-body tr").count() == 1

    page.press("#fp-search", "Enter")
    page.wait_for_timeout(400)

    assert page.url == url_antes, "Enter não pode navegar/recarregar"
    assert navegacoes == [], f"houve navegação do frame principal: {navegacoes}"
    assert page.input_value("#fp-search") == "Poxoréu", "o texto digitado deve permanecer"
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    assert page.locator("#fp-table-body tr").count() == 1
    assert (
        page.locator("#fp-table-body tr td:nth-child(2)").first.text_content() == "Poxoréu"
    )
    assert page.evaluate("document.activeElement.id") == "fp-search", "o foco deve permanecer"


def test_cenario_r_enter_com_municipio_inexistente_mantem_empty_state(page, site_url):
    """Enter sem resultados preserva a busca e o empty-state, sem recarregar."""
    open_consultation(page, site_url)
    navegacoes = _track_navigations(page)

    page.fill("#fp-search", "zzzzzznaoexiste")
    page.wait_for_timeout(150)

    url_antes = page.url
    page.press("#fp-search", "Enter")
    page.wait_for_timeout(400)

    assert page.url == url_antes
    assert navegacoes == []
    assert page.input_value("#fp-search") == "zzzzzznaoexiste"
    assert page.locator("#fp-result-count").text_content() == "0 municípios encontrados"
    assert page.locator("#fp-table-body tr").count() == 0
    assert page.locator("#fp-empty").is_visible()
    assert (
        page.locator("#fp-empty").text_content()
        == "Nenhum município foi encontrado com os filtros selecionados."
    )


def test_cenario_s_enter_preserva_filtros_combinados(page, site_url):
    """Enter reaplica o filtro sem resetar UF nem Situação."""
    open_consultation(page, site_url)
    navegacoes = _track_navigations(page)
    url_antes = page.url

    # busca + UF
    page.fill("#fp-search", "Poxoréu")
    page.locator("#fp-uf").select_option("MT")
    page.wait_for_timeout(150)
    page.press("#fp-search", "Enter")
    page.wait_for_timeout(300)
    assert page.url == url_antes
    assert page.input_value("#fp-search") == "Poxoréu"
    assert page.input_value("#fp-uf") == "MT"
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"

    # busca + UF + Situação
    page.locator("#fp-status").select_option("available")
    page.wait_for_timeout(150)
    page.press("#fp-search", "Enter")
    page.wait_for_timeout(300)
    assert page.url == url_antes
    assert page.input_value("#fp-search") == "Poxoréu"
    assert page.input_value("#fp-uf") == "MT"
    assert page.input_value("#fp-status") == "available"
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"

    # busca + Situação (sem UF)
    page.locator("#fp-uf").select_option("")
    page.wait_for_timeout(150)
    page.press("#fp-search", "Enter")
    page.wait_for_timeout(300)
    assert page.url == url_antes
    assert page.input_value("#fp-search") == "Poxoréu"
    assert page.input_value("#fp-status") == "available"
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"

    assert navegacoes == [], f"houve navegação do frame principal: {navegacoes}"


def test_cenario_t_busca_em_tempo_real_continua_sem_enter(page, site_url):
    """A filtragem no evento 'input' não pode depender do Enter."""
    open_consultation(page, site_url)
    navegacoes = _track_navigations(page)

    page.fill("#fp-search", "Poxoréu")
    page.wait_for_timeout(200)
    assert page.locator("#fp-result-count").text_content() == "1 município encontrado"
    assert page.locator("#fp-table-body tr").count() == 1

    page.fill("#fp-search", "")
    page.wait_for_timeout(200)
    assert page.locator("#fp-result-count").text_content() == "1.541 municípios encontrados"

    assert navegacoes == []
    # aria-live do contador e o botão de limpeza seguem íntegros.
    assert page.locator("#fp-result-count").get_attribute("aria-live") == "polite"
    assert page.locator("#fp-clear").get_attribute("type") == "button"


def test_cenario_u_correcao_do_enter_nao_usa_captura_global_de_teclado(page, site_url):
    """A correção é um listener de 'submit' no próprio formulário."""
    js = (ROOT / "assets" / "js" / "pages" / "farmacia-popular.js").read_text(encoding="utf-8")

    assert "addEventListener('submit'" in js, "listener de submit ausente"
    assert "event.preventDefault()" in js
    assert "document.addEventListener('keydown'" not in js, "captura global de teclado proibida"
    assert "document.addEventListener('keyup'" not in js
    assert "'keypress'" not in js
    # O filtro em tempo real segue no evento 'input'.
    assert "'input' : 'change'" in js

    open_consultation(page, site_url)
    assert page.locator("#fp-filters").count() == 1, "o <form> deve ser preservado"
