import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parents[1]
NEWS_PATH = ROOT / "noticias" / "anvisa-suspende-medicamento-proibe-produtos-irregulares" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
PUBLISHED = "2026-07-05T18:00:00-03:00"
UPDATED = "2026-09-14T13:02:55-03:00"
DOBUTAMINA_LOTES = ("24092127", "24102310", "25102244", "25102243", "25112308")


def _new_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-agosto-title"')
    return html[start:html.index("</aside>", start)]


def _september_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-setembro-title"')
    return html[start:html.index("</aside>", start)]


def _september_section(html):
    start = html.index("<h2>Setembro: RE nº 3.547/2026")
    return html[start:html.index("<h2>Agosto amplia", start)]


def _items(callout):
    return re.findall(r"<li>(.*?)</li>", callout, re.DOTALL)


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_article_consolidates_the_measures_of_17_and_19_august():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _new_callout(html)

    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert 'property="article:modified_time"' in html
    assert "17/08" in callout and "19/08" in callout
    assert callout.index("17/08") < callout.index("19/08")
    assert "data-news-update-callout" in callout
    assert "ATUALIZAÇÃO" in callout
    for term in (
        "Newfit",
        "sibutramina",
        "fluoxetina",
        "furosemida",
        "Mounja Gummy",
        "Trodelvy",
        "lote 10008808",
        "Shark Pro",
        "Boas Práticas de Fabricação",
        "Máscara Avocado Tutano Vegano",
        "Capi Hair",
        "Essence",
        "Geo Beauty",
        "Essencial for Men",
        "Rainha Solar",
        "Mixderme",
        "Ar Tratamento",
        "Natural Perfection Double Shield Sun Stick SPD50+",
        "Fraijour Retin-Collagen 3D Core Eye Cream",
    ):
        assert term in callout
    assert "não alcança todos os lotes ou a marca" in callout
    assert "recolhimento" in callout
    assert "Mounjaro" not in callout
    assert "suspensão de AFE" not in callout
    assert "Fonte oficial" not in html


def test_september_update_reflects_re_3547_and_keeps_history():
    html = NEWS_PATH.read_text(encoding="utf-8")
    september = _september_callout(html)
    text = _text(september)

    assert html.index("novas-medidas-setembro-title") < html.index("novas-medidas-agosto-title")
    assert html.count("data-news-update-callout aria-labelledby=") == 2
    assert "ATUALIZAÇÃO" in september
    assert "Resolução-RE nº 3.547/2026" in text
    assert "de 09/09/2026 e publicada no DOU em 11/09/2026" in text
    assert "Medidas de julho a setembro mostram" in html
    assert "Medidas de julho e agosto" not in html
    assert f'<time datetime="{UPDATED}">14/09/2026</time> às 13h02' in html
    assert f'<time datetime="{PUBLISHED}">05/07/2026</time> às 18h00' in html
    # Histórico de agosto e julho preservado.
    for term in ("12/08 — saneantes sem registro", "14/08 — Chá Sarapião", "Fiscalização de julho amplia", "Chlorohex 2,0%"):
        assert term in html
    for forbidden in ("Ozempic", "Mounjaro", "150 g", "150 mg", "href="):
        assert forbidden not in september


def test_each_september_measure_is_attributed_only_to_its_product():
    html = NEWS_PATH.read_text(encoding="utf-8")
    items = _items(_september_callout(html))
    assert len(items) == 4
    dobutamina, pharmes, soll, berberina = (_text(item) for item in items)

    assert "Hypofarma" in dobutamina and "dobutamina 12,5 mg/mL" in dobutamina
    assert all(lote in dobutamina for lote in DOBUTAMINA_LOTES)
    assert "recolhimento e suspensão da comercialização, da distribuição e do uso restritos aos lotes" in dobutamina
    assert "todos os lotes" not in dobutamina and "apreensão" not in dobutamina

    assert "Pharmes" in pharmes and "Lupatini e Pinheiro Instituto de Manipulação Ltda." in pharmes
    assert pharmes.endswith("suspensão da propaganda.")
    for other in ("recolhimento", "apreensão", "proibição", "lotes"):
        assert other not in pharmes

    assert "Soll*Q-75" in soll and "Método Quantumbio" in soll
    assert "apreensão de todos os lotes e proibição de comercialização, distribuição, fabricação, propaganda e uso" in soll
    assert "recolhimento" not in soll and "importação" not in soll

    assert "berberina sem registro, notificação ou cadastro" in berberina
    assert "apreensão de todos os lotes e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in berberina
    assert "recolhimento" not in berberina

    assert all(lote not in _text(item) for item in items[1:] for lote in DOBUTAMINA_LOTES)


def test_september_body_details_and_numbering_note():
    html = NEWS_PATH.read_text(encoding="utf-8")
    section = _text(_september_section(html))

    assert "Resolução-RE nº 3.547, de 09/09/2026" in section
    assert "11/09/2026" in section
    assert "A medida é restrita aos lotes identificados." in section
    assert "O ato não determina recolhimento, apreensão ou proibição de fabricação desses produtos." in section
    assert "Nattubras Produtos Natturais Ltda. também ficou proibida de fabricar o produto" in section
    assert "quaisquer pessoas físicas ou jurídicas, ou veículos de comunicação" in section
    # 3.457 só aparece na nota neutra de divergência; a referência normativa é 3.547.
    assert html.count("3.457") == 1
    assert "A notícia institucional da Anvisa sobre essas medidas traz a numeração 3.457/2026, enquanto o ato normativo publicado no DOU corresponde à RE nº 3.547/2026." in section
    for forbidden in ("Ozempic", "150 g", "150 mg"):
        assert forbidden not in section
    for term in ("Expert Berlian", "Nutra Senior", "3.540", "3.541"):
        assert term not in html


def test_article_is_unique_and_current_in_the_listing_and_sitemap():
    news_index = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert news_index.count('href="/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"') == 1
    assert f'data-updated="{UPDATED}"' in news_index
    assert "14/09/2026 • 13h02" in news_index
    assert "RE nº 3.547/2026" in news_index
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-09-14</lastmod>" in sitemap
