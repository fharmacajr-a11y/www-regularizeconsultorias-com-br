from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parents[2]
NEWS_PATH = ROOT / "noticias" / "credenciamento-farmacia-popular-municipios-com-vagas" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/credenciamento-farmacia-popular-municipios-com-vagas/"
PUBLISHED = "2026-05-22T23:30:00-03:00"
UPDATED = "2026-10-06T18:11:00-03:00"


def test_credenciamento_news_uses_the_current_municipalities_list():
    html = NEWS_PATH.read_text(encoding="utf-8")

    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert "Versão da lista utilizada nesta notícia: 03/09/2026" in html
    assert "1.541 municípios" in html
    assert "3.082 vagas totais" in html
    assert "963 preenchidas" in html
    assert "2.119 disponíveis" in html
    assert html.count("data-news-update-callout") == 1
    assert "ATUALIZAÇÃO" in html
    assert 'href="./farmacia-popular-municipios-vagas-03-09-2026.pdf"' in html
    assert 'href="./farmacia-popular-municipios-vagas-20-08-2026.pdf"' not in html
    assert 'href="./farmacia-popular-municipios-vagas-28-07-2026.pdf"' not in html
    # A relação de 20/08 permanece citada como referência histórica no texto.
    assert "A versão anteriormente utilizada era a de 20/08/2026" in html


def test_historical_pdfs_remain_available_on_disk():
    for name in (
        "farmacia-popular-municipios-vagas-03-09-2026.pdf",
        "farmacia-popular-municipios-vagas-20-08-2026.pdf",
        "farmacia-popular-municipios-vagas-28-07-2026.pdf",
    ):
        assert (NEWS_PATH.parent / name).is_file(), f"PDF ausente: {name}"


def test_credenciamento_news_is_unique_and_current_in_listing_and_sitemap():
    news_index = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert news_index.count('href="/noticias/credenciamento-farmacia-popular-municipios-com-vagas/"') == 1
    assert f'data-updated="{UPDATED}"' in news_index
    assert "06/10/2026 • 18h11" in news_index
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-06</lastmod>" in sitemap


def test_credenciamento_news_summarizes_the_convocation_without_promising_a_vacancy():
    import re
    html = NEWS_PATH.read_text(encoding="utf-8")
    text = " ".join(re.sub(r"<[^>]+>", " ", html).split())

    assert "municípios onde ainda não há farmácia participante, relacionados no Anexo I" in text
    assert "ordem cronológica de inscrição, desde que atendidos todos os requisitos" in text
    assert "a seleção como apta não garante a participação" in text
    assert "um município com vaga na posição de 03/09/2026 pode já não ter vaga disponível" in text
    assert "a vaga não assegura o ingresso de uma empresa específica" in text
    # A convocação é atribuída ao MS sem número/data inventados, sem atalho para o PDF e sem promessa.
    for wrong in ("Convocação nº 1/2026", "inscrições começaram em 18/08", "abertas em todos os municípios",
                  "credenciamento garantido", "vaga garantida", "edital-de-convocacao", "Protocolo Digital"):
        assert wrong not in text and wrong not in html, wrong
    # Fase 1H v2: uma única referência oficial, a página de documentação do MS, no parágrafo da convocação.
    main = html.split("<main", 1)[1].split("</main>", 1)[0]
    documentacao = "https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular/participacao/documentacao"
    assert re.findall(r'href="(https?://[^"]*gov\.br[^"]*)"', main) == [documentacao]
    assert (f'na <a href="{documentacao}" target="_blank" rel="noopener noreferrer">página de documentação do '
            'Programa</a> trata da participação') in html
