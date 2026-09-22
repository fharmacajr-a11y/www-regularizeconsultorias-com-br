import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parents[1]
NEWS_PATH = ROOT / "noticias" / "anvisa-suspende-medicamento-proibe-produtos-irregulares" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
PUBLISHED = "2026-07-05T18:00:00-03:00"
UPDATED = "2026-09-22T14:16:45-03:00"
DOBUTAMINA_LOTES = ("24092127", "24102310", "25102244", "25102243", "25112308")


def _august_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-agosto-title"')
    return html[start:html.index("</aside>", start)]


def _re3717_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-21-setembro-title"')
    return html[start:html.index("</aside>", start)]


def _latest_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-16-setembro-title"')
    return html[start:html.index("</aside>", start)]


def _september_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-setembro-title"')
    return html[start:html.index("</aside>", start)]


def _september_section(html):
    start = html.index("<h2>Setembro: RE nº 3.547/2026")
    return html[start:html.index("<h2>Agosto amplia", start)]


def _re3717_section(html):
    start = html.index("<h2>21 de setembro: RE nº 3.717/2026")
    return html[start:html.index("<h2>16 de setembro: quatro resoluções", start)]


def _latest_section(html):
    start = html.index("<h2>16 de setembro: quatro resoluções")
    return html[start:html.index("<h2>Setembro: RE nº 3.547/2026", start)]


def _subsection(section, heading, next_heading=None):
    start = section.index(f"<h3>{heading}</h3>")
    if next_heading is None:
        return section[start:]
    return section[start:section.index(f"<h3>{next_heading}</h3>", start)]


def _items(callout):
    return re.findall(r"<li>(.*?)</li>", callout, re.DOTALL)


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def test_article_consolidates_the_measures_of_17_and_19_august():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _august_callout(html)

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

    assert html.index("novas-medidas-21-setembro-title") < html.index("novas-medidas-16-setembro-title")
    assert html.index("novas-medidas-16-setembro-title") < html.index("novas-medidas-setembro-title")
    assert html.index("novas-medidas-setembro-title") < html.index("novas-medidas-agosto-title")
    assert html.count("data-news-update-callout aria-labelledby=") == 4
    assert "ATUALIZAÇÃO" in september
    assert "Resolução-RE nº 3.547/2026" in text
    assert "de 09/09/2026 e publicada no DOU em 11/09/2026" in text
    assert "Medidas de julho a setembro mostram" in html
    assert "Medidas de julho e agosto" not in html
    assert f'<time datetime="{UPDATED}">22/09/2026</time> às 14h16' in html
    assert f'<time datetime="{PUBLISHED}">05/07/2026</time> às 18h00' in html
    # Histórico de agosto e julho preservado.
    for term in ("12/08 — saneantes sem registro", "14/08 — Chá Sarapião", "Fiscalização de julho amplia", "Chlorohex 2,0%"):
        assert term in html
    for forbidden in ("Ozempic", "Mounjaro", "150 g", "150 mg", "href="):
        assert forbidden not in september


def test_latest_callout_keeps_each_resolution_bound_to_its_own_products_and_measures():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _latest_callout(html)
    items = _items(callout)

    assert len(items) == 4
    assert "Atualização de 16/09: T36 e alimentos são alcançados por quatro resoluções distintas" in callout
    t36, moringa, notshake, aloe = (_text(item) for item in items)

    assert "T36 (TIRZEPATIDA) — RE nº 3.626/2026" in t36
    assert "armazenamento, comercialização, distribuição, exportação, importação, propaganda, transporte e uso proibidos" in t36
    assert "não determina recolhimento nem apreensão" in t36

    assert "Produtos Moringa da Paz — RE nº 3.628/2026" in moringa
    assert "apreensão e proibição de fabricação, comercialização, distribuição, propaganda e uso" in moringa
    assert "não determina recolhimento" in moringa

    assert "NotShake Protein — RE nº 3.629/2026" in notshake
    assert "recolhimento e proibição de fabricação, comercialização, distribuição, propaganda e uso" in notshake
    assert "apreensão" not in notshake

    assert "Aloe Care — RE nº 3.634/2026" in aloe
    assert "recolhimento e proibição de fabricação, distribuição, comercialização, propaganda e uso" in aloe
    assert "RE nº 3.629/2026" not in aloe

    for item, own_re in zip(items, ("3.626", "3.628", "3.629", "3.634")):
        assert all(other not in item for other in ("3.626", "3.628", "3.629", "3.634") if other != own_re)


def test_four_new_body_subsections_preserve_exact_products_measures_and_negative_limits():
    html = NEWS_PATH.read_text(encoding="utf-8")
    section = _latest_section(html)
    t36 = _text(_subsection(section, "T36 — RE nº 3.626/2026", "Moringa da Paz — RE nº 3.628/2026"))
    moringa = _text(_subsection(section, "Moringa da Paz — RE nº 3.628/2026", "NotShake Protein — RE nº 3.629/2026"))
    notshake = _text(_subsection(section, "NotShake Protein — RE nº 3.629/2026", "Aloe Care — RE nº 3.634/2026"))
    aloe = _text(_subsection(section, "Aloe Care — RE nº 3.634/2026"))

    assert "todos os lotes" in t36
    assert "empresa não foi identificada" in t36 and "CNPJ é desconhecido" in t36
    assert "medicamento sem registro sanitário concedido pela Agência" in t36
    for measure in ("armazenamento", "comercialização", "distribuição", "exportação", "importação", "propaganda", "transporte", "uso"):
        assert measure in t36
    assert "não determina recolhimento nem apreensão" in t36
    assert "determina o recolhimento" not in t36 and "determina a apreensão" not in t36
    assert "Go Pharma" not in section and "3.480" not in section

    for product in (
        "Cápsula Nespresso de Moringa Oleífera",
        "Pó Orgânico de Moringa Oleífera",
        "Cápsulas com Pó Orgânico de Moringa Oleífera",
        "Chá Orgânico de Moringa Oleífera",
    ):
        assert product in moringa
    assert "apreensão e proíbe a fabricação, a comercialização, a distribuição, a propaganda e o uso" in moringa
    assert "não determina recolhimento" in moringa
    assert "efeitos genotóxicos e hepatotóxicos não puderam ser afastados" in moringa
    assert "não equivalem a afirmar que a moringa cause câncer ou dano hepático" in moringa

    for product in (
        "NotShake Protein Morango com Tâmara",
        "NotShake Protein Baunilha com Coco",
        "NotShake Protein Chocolate",
        "NotShake Protein Café Caramelo",
    ):
        assert product in notshake
    assert "NotCo Brasil Distribuição e Comércio de Produtos Alimentícios Ltda." in notshake
    assert "determina o recolhimento e proíbe a fabricação, a comercialização, a distribuição, a propaganda e o uso" in notshake
    for reason in ("suco concentrado de repolho", "recategorização inadequada", "ausência de notificação como suplemento", "insuficiência dos estudos", "zero lactose"):
        assert reason in notshake
    assert "apreensão" not in notshake and "3.634" not in notshake

    assert "Aloe Care – Cranberry Flavored Aloe Vera Gel" in aloe
    assert "Biodis Industrial Ltda." in aloe
    assert "determina o recolhimento e proíbe a fabricação, a distribuição, a comercialização, a propaganda, a divulgação e o uso" in aloe
    for reason in ("sem prévia avaliação de segurança e autorização de uso", "língua estrangeira", "alegações de saúde ou terapêuticas não autorizadas"):
        assert reason in aloe
    assert "não representa proibição genérica de todo uso de Aloe vera" in aloe
    assert "3.629" not in aloe


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
    assert "22/09/2026 • 14h16" in news_index
    assert "A RE nº 3.717/2026, publicada em 21/09" in news_index
    cards = re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', news_index, re.DOTALL)
    assert 'anvisa-suspende-medicamento-proibe-produtos-irregulares' in cards[0]
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-09-22</lastmod>" in sitemap


def test_re_3717_callout_keeps_each_measure_inside_its_own_item():
    html = NEWS_PATH.read_text(encoding="utf-8")
    items = [_text(item) for item in _items(_re3717_callout(html))]

    assert len(items) == 5
    phesgo, dysport, queen, malheiro, cannabis = items

    assert "Phesgo — lote B5011B05" in phesgo
    assert "fabricação 06/2025" in phesgo
    assert "33.009.945/0001-23" in phesgo
    assert "apreensão e proibição de armazenamento, comercialização, distribuição, exportação, importação e uso" in phesgo
    assert "não determina recolhimento" in phesgo
    assert "Dysport" not in phesgo and "Queen" not in phesgo and "Malheiro" not in phesgo and "cannabis" not in phesgo

    assert "lotes P08191, P08192 e P22368" in dysport
    assert "07.718.721/0001-80" in dysport
    assert "04/2029, 05/2029 e 02/2029" in dysport
    assert "apreensão e proibição de comercialização, distribuição e uso" in dysport
    assert "não determina recolhimento nem proíbe armazenamento, exportação, importação ou propaganda" in dysport
    assert "Phesgo" not in dysport and "Queen" not in dysport and "Malheiro" not in dysport and "cannabis" not in dysport

    assert "48.822.189/0001-24" in queen
    assert "suspensão da propaganda" in queen
    assert "não determina recolhimento, apreensão nem proibição de fabricação ou comercialização" in queen
    assert "Phesgo" not in queen and "Dysport" not in queen and "Malheiro" not in queen and "cannabis" not in queen

    assert "47.843.321/0001-11" in malheiro
    assert "suspensão da propaganda de todos os manipulados" in malheiro
    assert "não determina recolhimento, apreensão nem proibição de fabricação" in malheiro
    assert "comercialização" not in malheiro
    assert "Phesgo" not in malheiro and "Dysport" not in malheiro and "Queen" not in malheiro and "cannabis" not in malheiro

    assert "proibição de comercialização e propaganda" in cannabis
    assert "não determina apreensão, recolhimento nem proibição de uso" in cannabis
    assert "Phesgo" not in cannabis and "Dysport" not in cannabis and "Queen" not in cannabis and "Malheiro" not in cannabis
    assert "href=" not in _re3717_callout(html)


def test_re_3717_body_uses_the_dou_text_and_does_not_mix_measures():
    html = NEWS_PATH.read_text(encoding="utf-8")
    section = _re3717_section(html)
    phesgo = _text(_subsection(section, "Phesgo — lote B5011B05 com fabricação 06/2025", "Dysport — lotes P08191, P08192 e P22368"))
    dysport = _text(_subsection(section, "Dysport — lotes P08191, P08192 e P22368", "Queen Pharma Aesthetic — suspensão de propaganda"))
    queen = _text(_subsection(section, "Queen Pharma Aesthetic — suspensão de propaganda", "Farmácia Malheiro — suspensão de propaganda"))
    malheiro = _text(_subsection(section, "Farmácia Malheiro — suspensão de propaganda", "Cannabis — comercialização e propaganda proibidas"))
    cannabis = _text(_subsection(section, "Cannabis — comercialização e propaganda proibidas"))

    assert "de 18/09/2026" in _text(section)
    assert "21/09/2026, edição 178, seção 1, página 183" in _text(section)
    assert "33.009.945/0001-23" in phesgo
    assert "CNPJ 3.009.945/0001-23" not in section and "CNPJ <strong>3.009.945/0001-23" not in section
    assert "quaisquer pessoas físicas ou jurídicas" in phesgo
    assert "não determina recolhimento do Phesgo" in phesgo
    for lot, validity in (("P08191", "04/2029"), ("P08192", "05/2029"), ("P22368", "02/2029")):
        assert lot in dysport and validity in dysport
    assert "Não há, nesse item, proibição de armazenamento, exportação, importação ou propaganda" in dysport
    for product in (
        "lidocaína 2% sem vasoconstritor",
        "Desinflame",
        "Morusil Slim+",
        "Hepato Detox",
        "Metabolismo Power",
        "Muscledefin",
        "glicose 75% com lidocaína",
        "hialuronidase 3000 UTR",
        "mescla capilar",
        "Strill Repair",
        "Face Body Firm",
        "Boom de Colágeno",
        "Cellu Slim",
        "Soft Lipo",
        "Slim Flash/Gordura Light",
        "Lipo Slim",
        "Liposolve Intensive",
        "gordura localizada descafeinada",
        "Skinbooster",
        "Papada Slim",
        "Melasma",
    ):
        assert product in queen
    assert "@queenpharmaaesthetic" in queen
    assert "item 5.14" in queen and "RDC nº 67/2007" in queen
    assert "não determina recolhimento, apreensão nem proibição de fabricação ou comercialização" in queen
    assert "todos os manipulados" in malheiro
    assert "item 5.14" in malheiro
    assert "não determina recolhimento, apreensão, proibição de fabricação nem interdição do estabelecimento" in malheiro
    assert "artigos 2º, 12 e 59 da Lei nº 6.360/1976" in cannabis
    assert "@medicinatural.sac" in cannabis
    assert "não determina apreensão, recolhimento nem proibição de uso" in cannabis
    assert "não representa proibição genérica de produtos de cannabis" in cannabis
    assert "href=" not in section
