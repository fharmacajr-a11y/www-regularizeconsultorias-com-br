"""A reorganização do consolidado de irregulares conserva os fatos da versão de 151ad89.

Desde a v2, cada RE fica num item recolhido próprio, a linha da tabela leva ao item, a busca olha também o texto
dos detalhes e a página, como o leitor a encontra, tem altura limitada.
"""
import re
import subprocess
import threading
from collections import Counter
from functools import partial
from html import unescape
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest
from playwright.sync_api import sync_playwright

from support import SITE_DIR, new_context

ROOT = SITE_DIR
PAGE = "noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/index.html"
BASE = "151ad89"
ROUTE = "/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
STOP = {
    "produtos", "produto", "todos", "todas", "lotes", "lote", "empresa", "desconhecida",
    "preparações", "magistrais", "marca", "diversos", "manipulados", "itens", "item",
    "sem", "registro", "notificação", "cadastro", "base", "para", "com", "não",
    "ato", "medida", "medidas", "proibição", "apreensão", "recolhimento", "suspensão",
    "comercialização", "distribuição", "fabricação", "propaganda", "uso", "armazenamento",
}


def _old_html():
    return subprocess.check_output(["git", "show", f"{BASE}:{PAGE}"], cwd=ROOT).decode("utf-8")


def _new_html():
    return (ROOT / PAGE).read_text(encoding="utf-8")


def _plain(html):
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.DOTALL | re.IGNORECASE)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", unescape(text)).casefold()


def _re_numbers(html):
    return set(re.findall(r"(?:Resolução-)?RE nº\s*(\d{1,2}\.\d{3})", html))


def _strongs(html):
    found = []
    for raw in re.findall(r"<strong\b[^>]*>(.*?)</strong>", html, flags=re.DOTALL | re.IGNORECASE):
        text = re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", "", raw))).strip()
        if text:
            found.append(text)
    return found


class _Quiet(SimpleHTTPRequestHandler):
    def log_message(self, format, *args):
        return


@pytest.fixture(scope="module")
def origem():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_Quiet, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    yield f"http://{host}:{port}{ROUTE}"
    server.shutdown()
    server.server_close()
    thread.join(timeout=5)


def test_re_numeros_e_nomes_da_versao_151ad89_permanecem():
    old, new = _old_html(), _new_html()
    new_plain = _plain(new)

    missing_re = sorted(_re_numbers(old) - _re_numbers(new), key=lambda item: [int(part) for part in item.split(".")])
    assert missing_re == []
    old_cnpj = set(re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", old))
    assert old_cnpj <= set(re.findall(r"\d{2}\.\d{3}\.\d{3}/\d{4}-\d{2}", new))

    faltando = []
    for text in dict.fromkeys(_strongs(old)):
        if text.casefold() in new_plain:
            continue
        tokens = re.findall(r"[A-Za-zÀ-ÿ0-9][A-Za-zÀ-ÿ0-9*®./-]{2,}", text)
        names = [
            token for token in tokens
            if token.casefold() not in STOP and (len(token) >= 4 or any(char.isdigit() for char in token))
        ]
        ausentes = [token for token in names if token.casefold() not in new_plain]
        if ausentes:
            faltando.append((text, ausentes))
    assert faltando == []


def test_ids_meses_busca_e_links_internos():
    old, new = _old_html(), _new_html()
    new_ids = set(re.findall(r'\bid="([^"]+)"', new))
    assert Counter(re.findall(r'\bid="([^"]+)"', new)).most_common(1)[0][1] == 1
    assert set(re.findall(r'\bid="([^"]+)"', old)) <= new_ids
    assert "correcao-re-3159-2026" in new_ids

    assert re.search(r'<details class="irregulares-mes" id="mes-outubro-2026" open>', new)
    for month in ("mes-setembro-2026", "mes-agosto-2026", "mes-julho-2026"):
        tag = re.search(rf'<details class="irregulares-mes" id="{month}"[^>]*>', new).group(0)
        assert "open" not in tag, month
    assert 'id="irregulares-busca-form" hidden' in new
    assert ">Buscar produto, empresa ou RE</label>" in new

    main = new[new.index("<main"):new.index("</main>")]
    assert 'href="http' not in main and "href='http" not in main
    for heading in (
        "Irregularidade não significa sempre o mesmo problema",
        "O que empresas devem observar",
        "Precisa de apoio técnico?",
        "Notícias relacionadas",
    ):
        assert heading in new
    # 22/10/2026, 22h40 (hora do commit): lote das RE nº 4.143, 4.147 e 4.150/2026.
    # 28/10/2026, 18h50 (hora do commit): lote das RE nº 4.160, 4.228, 4.231 e 4.232/2026.
    assert 'datetime="2026-10-28T18:50:00-03:00"' in new
    assert "28/10/2026" in new and "18h50" in new


def _posicao(page, element_id):
    return page.evaluate(
        """(id) => {
            const el = document.getElementById(id);
            const header = document.querySelector('header');
            const box = el.getBoundingClientRect();
            return {
                aberto: el.closest('details').open,
                topo: box.top,
                limite: header.getBoundingClientRect().bottom,
                visivel: box.bottom > 0 && box.top < window.innerHeight
            };
        }""",
        element_id,
    )


def test_link_interno_abre_o_mes_e_a_busca_encontra_keytruda(origem):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": 1280, "height": 800}, locale="pt-BR")
        page = context.new_page()
        page.goto(origem + "#correcao-re-3159-2026", wait_until="load")
        page.wait_for_function(
            """() => {
                const el = document.getElementById('correcao-re-3159-2026');
                if (!el || !el.closest('details').open) return false;
                const topo = el.getBoundingClientRect().top;
                const limite = document.querySelector('header').getBoundingClientRect().bottom;
                return topo >= limite - 2 && topo < window.innerHeight;
            }"""
        )
        correcao = _posicao(page, "correcao-re-3159-2026")
        assert correcao["aberto"] is True
        assert correcao["topo"] >= correcao["limite"] - 2

        page.goto(origem + "#novas-medidas-25-setembro-title", wait_until="load")
        page.wait_for_function(
            """() => {
                const el = document.getElementById('novas-medidas-25-setembro-title');
                const mes = document.getElementById('mes-setembro-2026');
                if (!el || !mes.open) return false;
                const topo = el.getBoundingClientRect().top;
                const limite = document.querySelector('header').getBoundingClientRect().bottom;
                return topo >= limite - 2 && topo < window.innerHeight;
            }"""
        )
        setembro = _posicao(page, "novas-medidas-25-setembro-title")
        assert setembro["aberto"] is True
        assert page.locator("#mes-setembro-2026").evaluate("el => el.open") is True

        page.goto(origem, wait_until="load")
        page.wait_for_selector("#irregulares-busca", state="visible")
        page.evaluate("() => document.querySelectorAll('.irregulares-mes').forEach(el => { el.open = false; })")
        page.fill("#irregulares-busca", "Keytruda")
        page.wait_for_function(
            """() => {
                const linha = [...document.querySelectorAll('.irregulares-mes tbody tr')]
                    .find(tr => (tr.getAttribute('data-busca') || '').includes('Keytruda'));
                const mes = document.getElementById('mes-outubro-2026');
                return linha && !linha.hidden && mes.open;
            }"""
        )
        estado = page.evaluate(
            """() => {
                const linha = [...document.querySelectorAll('.irregulares-mes tbody tr')]
                    .find(tr => (tr.getAttribute('data-busca') || '').includes('Keytruda'));
                return {
                    outubro: document.getElementById('mes-outubro-2026').open,
                    setembro: document.getElementById('mes-setembro-2026').open,
                    agosto: document.getElementById('mes-agosto-2026').open,
                    julho: document.getElementById('mes-julho-2026').open,
                    oculta: linha.hidden,
                    texto: linha.innerText
                };
            }"""
        )
        assert estado["oculta"] is False
        assert "Keytruda" in estado["texto"]
        assert estado["outubro"] is True
        assert estado["setembro"] is False
        assert estado["agosto"] is False
        assert estado["julho"] is False
        context.close()
        browser.close()


# ---------------------------------------------------------------------------
# v2: cada RE num item recolhido próprio, tabela que leva ao item, busca nos detalhes e altura da página.
# ---------------------------------------------------------------------------
RESUMO = re.compile(r"^(?:RE nº \d\.\d{3}/2026|Sem número de RE) — .+ \((\d{2}/\d{2}/2026)\)$")
# Quadros quebrados por RE: número de itens e as RE de cada um, na ordem.
QUADROS = {
    "novas-medidas-28-outubro-title": ["4.228", "4.231", "4.232"],
    "novas-medidas-26-outubro-title": ["4.160"],
    "novas-medidas-22-outubro-title": ["4.143", "4.147", "4.150"],
    "novas-medidas-21-outubro-title": ["4.140", "3.159"],
    "novas-medidas-19-outubro-title": ["4.090", "4.105"],
    "novas-medidas-14-outubro-title": ["4.035"],
    "novas-medidas-13-outubro-title": ["3.989", "4.000", "4.001", "4.002", "4.009", "4.028"],
    "novas-medidas-06-outubro-title": ["3.946", "3.947", "3.634"],
}
# A meta fixa de altura (10.000 px em 390 px e 5.500 px em 1280 px) saiu em 22/10/2026: a tabela do mês aberto
# cresce a cada RE até o mês virar, e o mês anterior fecha quando entra um mês novo (CLAUDE.md). No lugar dela, o
# teste confere a estrutura (só o mês atual aberto, detalhes fechados, cartões de até 3 linhas em 390 px e linhas de
# até 2 linhas em 1280 px) e que a parte fixa da página (altura total menos a tabela do mês aberto) não passe de 10%
# acima do valor medido em 22/10/2026.
PARTE_FIXA_BASE = {390: 6148, 1280: 3703}


def _itens(html):
    """Itens recolhidos: (id, resumo, corpo), na ordem da página."""
    return [(m.group(1), unescape(m.group(2)).strip(), m.group(3)) for m in re.finditer(
        r'<details class="irregulares-re" id="([^"]+)"><summary>(.*?)</summary>(.*?)</details>', html, re.DOTALL)]


def _mes(html, month):
    start = html.index(f'<details class="irregulares-mes" id="{month}"')
    end = html.index('<details class="irregulares-mes"', start + 10) if month != "mes-julho-2026" else html.index(
        "<h2>Irregularidade não significa sempre o mesmo problema</h2>")
    return html[start:end]


def test_cada_re_fica_num_item_recolhido_com_resumo_e_os_detalhes_comecam_fechados():
    new = _new_html()
    itens = _itens(new)
    # 45 da v2 + RE nº 4.143, 4.147 e 4.150/2026 (22/10/2026) + RE nº 4.160 (26/10/2026), 4.228, 4.231 e 4.232/2026
    # (28/10/2026).
    assert len(itens) == 52
    for item_id, resumo, _ in itens:
        assert RESUMO.match(resumo), (item_id, resumo)
    # Nenhum item, nem o bloco de detalhes de cada mês, vem aberto: em outubro, só a tabela aparece.
    assert re.findall(r'<details class="irregulares-re"[^>]*\bopen\b', new) == []
    detalhes = re.findall(r'<details class="irregulares-detalhes" id="([^"]+)"([^>]*)>', new)
    assert [d for d, _ in detalhes] == ["detalhes-outubro-2026", "detalhes-setembro-2026",
                                        "detalhes-agosto-2026", "detalhes-julho-2026"]
    assert all("open" not in attrs for _, attrs in detalhes)
    # A correção da RE nº 3.159/2026 é um item próprio e mantém o id.
    correcao = dict((i, c) for i, _, c in itens)["re-3159-2026"]
    assert 'id="correcao-re-3159-2026"' in correcao
    assert "3.159" in correcao and "4.140" not in correcao


def test_os_quadros_grandes_ficam_quebrados_por_re_com_o_mesmo_texto():
    new = _new_html()
    for label, numeros in QUADROS.items():
        start = new.index(f'data-news-update-callout aria-labelledby="{label}"')
        quadro = new[start:new.index("</aside>", start)]
        itens = _itens(quadro)
        assert len(itens) == len(numeros), label
        for (item_id, resumo, corpo), numero in zip(itens, numeros):
            assert resumo.startswith(f"RE nº {numero}/2026"), (label, resumo)
            rotulos = re.findall(r"<li id=\"[^\"]+\"><strong>(.*?)</strong>", corpo, re.DOTALL)
            assert rotulos, item_id
            for rotulo in rotulos:
                proprios = set(re.findall(r"RE nº (\d\.\d{3})/2026", rotulo))
                assert numero in proprios or (numero == "3.634" and "3.634" in rotulo), (item_id, rotulo)
                assert proprios <= {numero, "2.895", "3.159"}, (item_id, rotulo)
    # Agosto: 17 e 19/08 viram dois itens; o parágrafo que compara as datas fica no quadro, depois deles.
    start = new.index('data-news-update-callout aria-labelledby="novas-medidas-agosto-title"')
    agosto = new[start:new.index("</aside>", start)]
    assert [i for i, _, _ in _itens(agosto)] == ["medidas-17-08-2026", "medidas-19-08-2026"]
    assert agosto.rindex("</details>") < agosto.index("Os fatos de 19/08 são distintos dos de 17/08")


def test_cada_linha_da_tabela_leva_ao_item_da_sua_re_e_data():
    new = _new_html()
    resumo_de_id = {}
    for item_id, resumo, corpo in _itens(new):
        for alvo in re.findall(r'\bid="([^"]+)"', corpo) + [item_id]:
            resumo_de_id[alvo] = resumo
    total = {}
    insubsistentes = []
    for month in ("mes-outubro-2026", "mes-setembro-2026", "mes-agosto-2026", "mes-julho-2026"):
        mes = _mes(new, month)
        tabela = mes[:mes.index('<details class="irregulares-detalhes"')]
        total[month] = 0
        for grupo in re.finditer(r'<th colspan="4" scope="rowgroup">([^<]+)</th></tr>(.*?)</tbody>', tabela, re.DOTALL):
            data = grupo.group(1)
            for alvo, linha in re.findall(r'<tr data-busca="[^"]*" data-alvo="([^"]+)">(.*?)</tr>', grupo.group(2), re.DOTALL):
                total[month] += 1
                assert f'href="#{alvo}"' in linha
                if alvo == "correcao-re-3159-2026" and month == "mes-julho-2026":
                    # Medida de 24/07 (RE nº 2.895/2026) que a correção de outubro tornou insubsistente.
                    produto = unescape(re.sub(r"<[^>]+>", "", re.search(r'<td data-label="Produto ou empresa">(.*?)</td>', linha).group(1)))
                    situacao = unescape(re.search(r'<td data-label="Situação"[^>]*>(.*?)</td>', linha).group(1))
                    assert situacao == "Tornada insubsistente (RE nº 3.159/2026)", (produto, situacao)
                    insubsistentes.append(produto)
                    continue
                resumo = resumo_de_id[alvo]
                assert RESUMO.match(resumo).group(1) == data, (alvo, data, resumo)
                celula_re = unescape(re.search(r'<td data-label="RE"[^>]*>(.*?)</td>', linha).group(1))
                numero = re.match(r"RE nº (\d\.\d{3})/2026", resumo)
                if numero:
                    assert celula_re.startswith(f"RE nº {numero.group(1)}/2026"), (alvo, celula_re, resumo)
                else:
                    assert celula_re == "Sem número de RE", (alvo, celula_re)
    # 28/10/2026: seis linhas novas em outubro (RE nº 4.160, 4.228, os três lotes da RE nº 4.231 e a RE nº 4.232).
    assert total == {"mes-outubro-2026": 56, "mes-setembro-2026": 33, "mes-agosto-2026": 7, "mes-julho-2026": 12}
    assert insubsistentes == ["Fluído Flesh Air Frionel", "Ecotec-Pro e Ecotec", "Bardahl Flush Promax", "Air Repair Pescan"]


def _aberto(page, item_id):
    return page.evaluate("(id) => document.getElementById(id).open", item_id)


def test_clique_na_linha_abre_o_item_certo_e_mostra_abaixo_do_cabecalho(origem):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for largura in (390, 1280):
            context = new_context(browser, viewport={"width": largura, "height": 800}, locale="pt-BR")
            page = context.new_page()
            page.goto(origem, wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            # Clique fora do link (na coluna da medida): a linha inteira leva ao detalhe.
            page.locator('.irregulares-tabela tr[data-alvo="irregulares-item-57"] td[data-label="Medida"]').click()
            page.wait_for_function(
                """() => {
                    const el = document.getElementById('irregulares-item-57');
                    if (!el || !el.closest('details').open) return false;
                    const topo = el.getBoundingClientRect().top;
                    const limite = document.querySelector('header').getBoundingClientRect().bottom;
                    return topo >= limite - 2 && topo < limite + 80;
                }"""
            )
            assert _aberto(page, "re-4105-2026") is True
            assert _aberto(page, "detalhes-outubro-2026") is True
            assert _aberto(page, "re-4090-2026") is False
            assert page.evaluate("() => document.querySelectorAll('.irregulares-re[open]').length") == 1
            assert page.evaluate("location.hash") == "#irregulares-item-57"
            context.close()
        browser.close()


def test_busca_por_lote_que_so_esta_no_detalhe_abre_o_mes_e_o_item(origem):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": 1280, "height": 800}, locale="pt-BR")
        page = context.new_page()
        page.goto(origem, wait_until="load")
        page.wait_for_selector("#irregulares-busca", state="visible")
        lote = "24092127"  # lote da dobutamina (RE nº 3.547/2026): está no detalhe, não na linha da tabela
        linha = '.irregulares-tabela tr[data-alvo="irregulares-item-33"]'
        assert lote not in page.locator(linha).get_attribute("data-busca")
        page.fill("#irregulares-busca", lote)
        page.wait_for_function("() => document.getElementById('re-3547-2026').open")
        estado = page.evaluate(
            """() => ({
                setembro: document.getElementById('mes-setembro-2026').open,
                outubro: document.getElementById('mes-outubro-2026').open,
                detalhes: document.getElementById('detalhes-setembro-2026').open,
                abertos: [...document.querySelectorAll('.irregulares-re[open]')].map(el => el.id),
                visiveis: [...document.querySelectorAll('.irregulares-mes tbody tr[data-alvo]')]
                    .filter(tr => !tr.hidden).map(tr => tr.getAttribute('data-alvo')),
                status: document.querySelector('.irregulares-busca__status').textContent
            })"""
        )
        assert estado["setembro"] is True and estado["detalhes"] is True
        assert estado["outubro"] is False
        assert estado["abertos"] == ["re-3547-2026"]
        assert estado["visiveis"] == ["irregulares-item-33"]
        assert estado["status"] == "1 medidas encontradas."
        # Limpar a busca volta ao estado inicial: outubro aberto, só com a tabela; todos os itens fechados.
        page.fill("#irregulares-busca", "")
        page.wait_for_function("() => !document.getElementById('re-3547-2026').open")
        assert page.evaluate("() => document.querySelectorAll('.irregulares-re[open], .irregulares-detalhes[open]').length") == 0
        assert page.evaluate("() => document.getElementById('mes-outubro-2026').open") is True
        assert page.evaluate("() => document.getElementById('mes-setembro-2026').open") is False
        context.close()
        browser.close()


def test_link_para_a_correcao_abre_o_mes_os_detalhes_e_o_item(origem):
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        context = new_context(browser, viewport={"width": 390, "height": 800}, locale="pt-BR")
        page = context.new_page()
        page.goto(origem, wait_until="load")
        page.locator('.irregulares-resumo a[href="#correcao-re-3159-2026"]').click()
        page.wait_for_function(
            """() => {
                const el = document.getElementById('correcao-re-3159-2026');
                if (!document.getElementById('re-3159-2026').open) return false;
                const topo = el.getBoundingClientRect().top;
                const limite = document.querySelector('header').getBoundingClientRect().bottom;
                return topo >= limite - 2 && topo < window.innerHeight;
            }"""
        )
        assert _aberto(page, "mes-outubro-2026") is True
        assert _aberto(page, "detalhes-outubro-2026") is True
        assert _aberto(page, "re-4140-2026") is False
        context.close()
        browser.close()


def test_pagina_como_o_leitor_encontra_tem_tabela_compacta_e_parte_fixa_estavel(origem):
    resultados = {}
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch()
        for largura in PARTE_FIXA_BASE:
            context = new_context(browser, viewport={"width": largura, "height": 900}, locale="pt-BR")
            page = context.new_page()
            page.goto(origem, wait_until="load")
            page.evaluate("document.fonts.ready.then(() => true)")
            resultados[largura] = page.evaluate(
                """() => {
                    const linhas = (el) => {
                        const s = getComputedStyle(el);
                        const altura = el.getBoundingClientRect().height - parseFloat(s.paddingTop) - parseFloat(s.paddingBottom);
                        return Math.round(altura / parseFloat(s.lineHeight));
                    };
                    const abertos = [...document.querySelectorAll('.irregulares-mes[open]')].map((el) => el.id);
                    const mes = document.querySelector('.irregulares-mes[open]');
                    const linhasDaTabela = [...mes.querySelectorAll('tbody tr[data-alvo]')].map((tr) => {
                        const tds = [...tr.querySelectorAll('td')];
                        const cartao = linhas(tds[0]) + linhas(tds[1]) + Math.max(linhas(tds[2]), linhas(tds[3]));
                        return {alvo: tr.getAttribute('data-alvo'), cartao, linha: Math.max(...tds.map(linhas))};
                    });
                    return {
                        abertos,
                        itensAbertos: document.querySelectorAll('.irregulares-re[open], .irregulares-detalhes[open]').length,
                        linhas: linhasDaTabela,
                        total: document.documentElement.scrollHeight,
                        tabela: mes.querySelector('.irregulares-tabela-caixa').getBoundingClientRect().height,
                    };
                }"""
            )
            context.close()
        browser.close()

    for largura, r in resultados.items():
        # Só o mês atual aberto, e todos os detalhes (bloco do mês e itens de RE) fechados.
        assert r["abertos"] == ["mes-outubro-2026"], (largura, r["abertos"])
        assert r["itensAbertos"] == 0, largura
        assert len(r["linhas"]) >= 50, largura
        parte_fixa = r["total"] - r["tabela"]
        assert parte_fixa <= PARTE_FIXA_BASE[largura] * 1.10, (largura, round(parte_fixa), PARTE_FIXA_BASE[largura])
    # Em 390 px, nenhum cartão passa de 3 linhas de texto (RE; produto ou empresa; medida e situação).
    assert [l for l in resultados[390]["linhas"] if l["cartao"] > 3] == []
    # Em 1280 px, nenhuma linha da tabela passa de 2 linhas.
    assert [l for l in resultados[1280]["linhas"] if l["linha"] > 2] == []
