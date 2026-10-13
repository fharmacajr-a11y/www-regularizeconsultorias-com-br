import re
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).parents[2]
NEWS_PATH = ROOT / "noticias" / "anvisa-suspende-medicamento-proibe-produtos-irregulares" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"
PUBLISHED = "2026-07-05T18:00:00-03:00"
# 13/10/2026, 09h06: RE nº 3.946 e 3.947/2026 e retificação do fabricante do Aloe Care.
UPDATED = "2026-10-13T09:06:00-03:00"
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
    # A RE nº 3.546/2026 (TYG), do mesmo dia, e os atos de 08 e 01/09 vêm depois e ficam fora da fatia.
    return html[start:html.index("<h2>11 de setembro: RE nº 3.546/2026", start)]


def _re3717_section(html):
    start = html.index("<h2>21 de setembro: RE nº 3.717/2026")
    # A revogação da RE nº 3.718/2026, também de 21/09, vem logo depois e fica fora da fatia.
    return html[start:html.index("<h2>21 de setembro: RE nº 3.718/2026", start)]


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


def _consolidated_card(news_index):
    cards = re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', news_index, re.DOTALL)
    own = [card for card in cards if 'href="/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/"' in card]
    assert len(own) == 1
    return own[0]


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

    assert html.index("novas-medidas-06-outubro-title") < html.index("novas-medidas-02-outubro-title")
    assert html.index("novas-medidas-02-outubro-title") < html.index("novas-medidas-25-setembro-title")
    assert html.index("novas-medidas-25-setembro-title") < html.index("novas-medidas-21-setembro-title")
    assert html.index("novas-medidas-21-setembro-title") < html.index("novas-medidas-16-setembro-title")
    assert html.index("novas-medidas-16-setembro-title") < html.index("novas-medidas-setembro-title")
    assert html.index("novas-medidas-setembro-title") < html.index("novas-medidas-agosto-title")
    # Sete quadros: o de 06/10/2026 ficou antes do de 02/10/2026.
    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert "ATUALIZAÇÃO" in september
    assert "Resolução-RE nº 3.547/2026" in text
    assert "de 09/09/2026 e publicada no DOU em 11/09/2026" in text
    assert "Medidas de julho a outubro mostram" in html
    assert "Medidas de julho a setembro" not in html
    assert "Medidas de julho e agosto" not in html
    assert f'<time datetime="{UPDATED}">13/10/2026</time> às 09h06' in html
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

    # Retificação publicada no DOU de 02/10/2026: nova denominação do primeiro produto, sem nova medida.
    assert "Cápsula Nespresso de Moringa Oleífera</strong>" not in moringa
    assert "retificação publicada no Diário Oficial da União de 02/10/2026" in moringa
    assert "não cria nova medida nem altera a empresa, os demais produtos, o alcance ou o tipo de medida" in moringa
    for product in (
        "Cápsulas de Moringa Oleífera, marca Moringa da Paz, compatíveis com máquinas Nespresso®",
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
    assert "União Vegetal Agroindustrial Ltda." in aloe
    assert "retificação publicada no DOU em 09/10/2026" in aloe
    assert "não cria outra medida nem altera o produto, os lotes ou as proibições" in aloe
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
    assert "13/10/2026 • 09h06" in news_index
    assert "medidas sobre United Labz, Mounjcaps, lotes falsificados de Enhertu e Dysport e um lote do TYG" in news_index
    for term in ("Hytamicina", "Pangastri", "Gripinew", "Lipo Top Gold", "Anagalis", "RE 3.440/2026", "RE 3.479/2026",
                 "RE 3.480/2026", "RE 3.546/2026", "RE 3.738/2026"):
        assert term in _consolidated_card(news_index).split('data-keywords="', 1)[1].split('"', 1)[0]
    assert ("Publicações da Anvisa de 01/09 a 02/10 trazem seis resoluções de 02/10 sobre dispositivos médicos "
            "(um lote de tiras G TECH e um lote falsificado do Hidrafemme), cosméticos e saneantes, a suspensão das "
            "operações da Reach Latam") in news_index
    assert "Publicações da Anvisa de 01 a 28/09" not in news_index
    assert "revogações de medidas referentes à Higia, à Tha &amp; Thi e à Terapêutica (RE nº 3.743, 3.718 e 3.436/2026)" in news_index
    assert "Publicações da Anvisa de 21 a 28/09" not in news_index
    assert "Publicações da Anvisa de 21 e 25/09" not in news_index
    cards = re.findall(r'(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)', news_index, re.DOTALL)
    # 13/10/2026, 09h06: a inclusão das RE nº 3.946 e 3.947 e da retificação do Aloe Care leva o card à 1ª posição.
    assert 'anvisa-suspende-medicamento-proibe-produtos-irregulares' in cards[0]
    assert "news-card-compact" in cards[0].split(">", 1)[0]
    assert "As RE nº 3.946 e 3.947/2026 foram publicadas no DOU de 06/10/2026" in cards[0]
    assert "União Vegetal Agroindustrial Ltda. como fabricante do Aloe Care" in cards[0]
    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-13</lastmod>" in sitemap


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


def test_new_measures_of_21_and_25_september_keep_their_own_scope():
    html = NEWS_PATH.read_text(encoding="utf-8")
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-25-setembro-title"')
    callout = html[start:html.index("</aside>", start)]
    items = [_text(item) for item in _items(callout)]
    body_start = html.index("<h2>25 de setembro: RE nº 3.751/2026")
    body = _text(html[body_start:html.index("<h2>21 de setembro: RE nº 3.717/2026", body_start)])

    assert len(items) == 11
    reach, ocrevus, ict, enhertu, mounjcaps, higia, eleve, dcasa, smart, thathi, terapeutica = items
    assert "RE nº 3.751/2026" in ocrevus and "RE nº 3.751/2026" in ict
    # RE nº 3.751/2026, LAF MED: os lotes estão no campo de produto, mas a motivação
    # estende as ações a quaisquer medicamentos, sem proibir o Ocrevus em geral.
    assert "LAF MED" in ocrevus and "H7953B14 e H7953B06" in ocrevus
    assert "se aplicam a quaisquer medicamentos" in ocrevus
    assert "não é uma proibição geral do Ocrevus" in ocrevus
    assert "restrita aos dois lotes" not in ocrevus
    # ICT: o campo de produto alcança todos os manipulados estéreis, todos os lotes;
    # 31/08 a 02/09/2026 é o período da inspeção, não da produção nem do recolhimento.
    assert "todos os medicamentos manipulados estéreis da empresa, em todos os lotes" in ict
    assert "suspensão de comercialização, distribuição, manipulação, propaganda e uso" in ict
    assert "31/08 a 02/09/2026 são as da inspeção" in ict
    assert "produzidos" not in ict and "refere-se ao recolhimento" not in ict
    assert "RE nº 3.712/2026" in eleve and "Gama Suplementos Alimentares" in eleve
    assert "RE nº 3.714/2026" in dcasa and "Fórmula Química" in dcasa
    assert "RE nº 3.714/2026" in smart
    assert "A publicação da Anvisa identifica esses três produtos da Klug como atingidos pela medida." in smart
    assert "A publicação da Anvisa identifica esses três produtos da Klug como atingidos pela medida." in body
    # Sem afirmação sobre a situação dos demais produtos da empresa.
    assert "demais produtos da Klug" not in callout and "demais produtos da Klug" not in body
    assert "href=" not in callout

    # Limites de alcance e de atribuição informados na revisão.
    assert "falsific" not in ocrevus.casefold()
    assert "falsific" not in _text(html[body_start:html.index("<h3>ICT Farmacêutica", body_start)]).casefold()
    laf_body = _text(html[body_start:html.index("<h3>ICT Farmacêutica", body_start)])
    ict_body = _text(html[html.index("<h3>ICT Farmacêutica", body_start):html.index("<h2>23 de setembro: RE nº 3.738/2026", body_start)])
    assert "Resolução-RE nº 3.751, de 24/09/2026, publicada no DOU em 25/09/2026" in body
    assert "proibição de armazenamento, comercialização, distribuição, exportação, importação, propaganda e transporte" in laf_body
    assert "o item não determina recolhimento" in laf_body
    assert "se aplicam a quaisquer medicamentos" in laf_body
    assert "não é uma proibição geral do Ocrevus" in laf_body
    assert "art. 7º, inciso XV, da Lei nº 9.782/1999" in laf_body
    assert "não se estende aos demais lotes" not in laf_body
    assert "todos os medicamentos manipulados estéreis, em todos os lotes" in ict_body
    assert "suspensão da comercialização, da distribuição, da manipulação, da propaganda e do uso" in ict_body
    assert "o item não determina apreensão" in ict_body
    assert "correspondem à inspeção de boas práticas de manipulação" in ict_body
    assert "não delimitam a produção nem os lotes alcançados" in ict_body
    assert "art. 7º da Lei nº 6.360/1976" in ict_body
    assert "produzidos entre" not in ict_body and "se refere ao recolhimento" not in ict_body
    assert "o alcance da suspensão deve ser conferido no ato publicado" not in body
    assert "Smart GR" not in dcasa and "saneantes" not in smart
    # RE nº 3.738/2026 (DOU de 23/09) tem seção própria desde a Fase 1F; não aparece nos itens nem nas seções
    # das RE nº 3.751, 3.712 e 3.714/2026.
    assert all("3.738" not in part for part in (ocrevus, ict, eleve, dcasa, smart, laf_body, ict_body))
    assert "3.738" not in _text(html[html.index("<h2>21 de setembro: RE nº 3.712"):html.index("<h2>21 de setembro: RE nº 3.717/2026")])
    assert "CNPJ" not in dcasa and "CNPJ" not in _text(html[html.index("<h3>D Casa"):html.index("<h3>Smart GR")])
    assert "href=" not in html[body_start:html.index("<h2>21 de setembro: RE nº 3.717/2026", body_start)]


def test_re_3764_and_re_3743_keep_suspension_and_revocation_apart():
    html = NEWS_PATH.read_text(encoding="utf-8")
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-25-setembro-title"')
    callout = html[start:html.index("</aside>", start)]
    items = [_text(item) for item in _items(callout)]
    reach_item, higia_item = items[0], items[5]
    reach_start = html.index("<h2>28 de setembro: RE nº 3.764/2026")
    reach = _text(html[reach_start:html.index("<h2>25 de setembro: RE nº 3.751/2026", reach_start)])
    higia_start = html.index("<h2>23 de setembro: RE nº 3.743/2026")
    higia = _text(html[higia_start:html.index("<h2>21 de setembro: RE nº 3.712", higia_start)])

    # A Fase 1D reaproveitou o quadro de 21 a 28/09; o de outubro (Fase 1G) é o sexto.
    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert "Atualização: medidas de 21 a 28/09/2026 e revogações de 01, 21 e 23/09/2026" in _text(callout)
    assert "publicações de 01, 21, 23, 25 e 28/09/2026" in _text(callout)
    assert "As RE nº 3.436, 3.718 e 3.743/2026 revogam, cada uma, uma medida anterior referente a uma empresa" in _text(callout)
    # Ordem cronológica das seções: 28/09, 25/09, 23/09, 21/09.
    assert reach_start < html.index("<h2>25 de setembro: RE nº 3.751/2026") < higia_start
    assert higia_start < html.index("<h2>21 de setembro: RE nº 3.712")

    # RE nº 3.764/2026 (24/09, DOU 28/09): suspensão dirigida à Reach Latam.
    assert "RE nº 3.764/2026, suspensão" in reach_item and "Reach Latam" in reach_item
    assert "suspensão de armazenamento, comercialização, distribuição, importação, propaganda e transporte" in reach_item
    assert "não é uma proibição geral da tirzepatida" in reach_item
    assert "Resolução-RE nº 3.764, de 24/09/2026, publicada no DOU em 28/09/2026" in reach
    assert "Reach Latam Consultoria e Comércio Exterior Ltda." in reach and "24.662.773/0001-00" in reach
    assert "todos os produtos sujeitos a controle especial, incluindo tirzepatida" in reach
    assert "todos os lotes" in reach and "insumo farmacêutico" in reach
    assert "suspensão de armazenamento, comercialização, distribuição, importação, propaganda e transporte" in reach
    assert "Boas Práticas de Distribuição, Armazenamento, Importação e Controle de Insumos Farmacêuticos" in reach
    assert "identidade, segurança, controle e rastreabilidade" in reach
    assert "não representa proibição geral da tirzepatida nem medida contra a manipulação em geral" in reach
    assert "o ato não determina recolhimento nem apreensão" in reach
    for wrong in ("fabricação", "exportação", "uso,", " uso ", "proíbe", "proibição de", "determina o recolhimento", "determina a apreensão"):
        assert wrong not in reach_item and wrong not in reach.replace("proibição geral", ""), wrong

    # RE nº 3.743/2026 (22/09, DOU 23/09): revogação da medida nº 2 da RE nº 939/2026, com as restrições da motivação.
    assert "RE nº 3.743/2026, revogação" in higia_item and "Higia Pharmaceutical" in higia_item
    assert "medida preventiva nº 2 do anexo da RE nº 939/2026" in higia_item
    assert "Satisfatória Com Restrições" in higia_item and "estudo complementar de validações" in higia_item
    assert "Resolução-RE nº 3.743, de 22/09/2026, publicada no DOU em 23/09/2026" in higia
    assert "medida preventiva nº 2 do anexo da Resolução-RE nº 939, de 12/03/2026, publicada no DOU em 13/03/2026" in higia
    assert "Higia Pharmaceutical Limitada" in higia and "57.022.608/0001-34" in higia
    assert "apreensão, o recolhimento e a suspensão de comercialização, manipulação, propaganda e uso" in higia
    assert "de 08 a 09/09/2026" in higia and "Satisfatória Com Restrições" in higia
    assert "resultados do estudo complementar de validações" in higia and "desinterdição" in higia
    assert "não informa que essa renovação já tenha ocorrido" in higia
    assert "A revogação alcança apenas a medida nº 2 da RE nº 939/2026" in higia
    assert "Não equivale à manutenção da medida anterior nem a uma liberação sem condições" in higia
    assert "não se estende à outra medida do mesmo ato nem a outras empresas" in higia
    for wrong in ("El Elyon", "liberação total", "licença renovada", "teve a licença renovada", "mantém a suspensão"):
        assert wrong not in higia and wrong not in higia_item
    assert "href=" not in html[reach_start:html.index("<h2>25 de setembro", reach_start)]
    assert "href=" not in html[higia_start:html.index("<h2>21 de setembro: RE nº 3.712", higia_start)]


def test_re_3718_and_re_3436_revoke_only_their_own_items():
    html = NEWS_PATH.read_text(encoding="utf-8")
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-25-setembro-title"')
    callout = html[start:html.index("</aside>", start)]
    items = [_text(item) for item in _items(callout)]
    thathi_item, terapeutica_item = items[9], items[10]
    thathi_start = html.index("<h2>21 de setembro: RE nº 3.718/2026")
    thathi = _text(html[thathi_start:html.index("<h2>16 de setembro: quatro resoluções", thathi_start)])
    terapeutica_start = html.index("<h2>1º de setembro: RE nº 3.436/2026")
    terapeutica = _text(html[terapeutica_start:html.index("<h2>Agosto amplia", terapeutica_start)])

    # Quadro de 21 a 28/09 reaproveitado: título e fecho cobrem 01/09; cada item novo traz sua publicação.
    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert "Atualização: medidas de 21 a 28/09/2026 e revogações de 01, 21 e 23/09/2026" in _text(callout)
    assert "publicações de 01, 21, 23, 25 e 28/09/2026" in _text(callout)
    assert "As RE nº 3.436, 3.718 e 3.743/2026 revogam, cada uma, uma medida anterior referente a uma empresa" in _text(callout)
    # Seções por data de publicação; no dia 21/09, a revogação vem depois das medidas preventivas.
    assert html.index("<h2>21 de setembro: RE nº 3.717/2026") < thathi_start < html.index("<h2>16 de setembro")
    assert html.index("<h2>Setembro: RE nº 3.547/2026") < terapeutica_start < html.index("<h2>Agosto amplia")

    # RE nº 3.718/2026 (18/09, DOU 21/09): só a medida nº 2 da RE nº 3.357/2026; proibição revogada.
    assert "RE nº 3.718/2026, revogação, DOU de 21/09/2026" in thathi_item and "Tha &amp; Thi" in thathi_item
    assert "medida preventiva nº 2 do anexo da RE nº 3.357/2026" in thathi_item
    assert "apreensão e a proibição de comercialização, manipulação, propaganda e uso" in thathi_item
    assert "não a RE nº 3.357/2026 inteira" in thathi_item
    assert "Resolução-RE nº 3.718, de 18/09/2026, publicada no DOU em 21/09/2026" in thathi
    assert "medida preventiva nº 2 do anexo da Resolução-RE nº 3.357, de 26/08/2026, publicada no DOU em 27/08/2026" in thathi
    assert "06.177.615/0001-74" in thathi and "preparações magistrais estéreis" in thathi
    assert "apreensão e a proibição de comercialização, manipulação, propaganda e uso" in thathi
    assert "AFE vigente para a manipulação de produtos estéreis" in thathi
    assert "o ato não concede nova autorização" in thathi
    assert "item 5.10 da RDC nº 67/2007" in thathi
    assert "o art. 1º revoga apenas a medida nº 2, referente à Tha &amp; Thi" in thathi
    assert "não equivale a uma certificação de toda a produção da empresa" in thathi
    for wrong in ("suspensão", "distribuição", "recolhimento", "estudo complementar", "Satisfatória", "concede AFE", "nova AFE"):
        assert wrong not in thathi_item and wrong not in thathi, wrong

    # RE nº 3.436/2026 (28/08, DOU 01/09): só a medida nº 3 da RE nº 1.380/2026; suspensão revogada.
    assert "RE nº 3.436/2026, revogação, DOU de 01/09/2026" in terapeutica_item and "Terapêutica" in terapeutica_item
    assert "medida preventiva nº 3 do anexo da RE nº 1.380/2026" in terapeutica_item
    assert "apreensão e a suspensão de comercialização, distribuição, manipulação, propaganda e uso" in terapeutica_item
    assert "Resolução-RE nº 3.436, de 28/08/2026, publicada no DOU em 01/09/2026" in terapeutica
    assert "medida preventiva nº 3 do anexo da Resolução-RE nº 1.380, de 07/04/2026, publicada no DOU em 08/04/2026" in terapeutica
    assert "47.545.371/0001-12" in terapeutica and "todos os medicamentos manipulados estéreis" in terapeutica
    assert "apreensão e a suspensão de comercialização, distribuição, manipulação, propaganda e uso" in terapeutica
    assert "Vigilância Sanitária de São José dos Campos" in terapeutica and "04/08/2026" in terapeutica
    assert "não se estende às demais medidas do mesmo ato" in terapeutica
    assert "atribuída pelo ato à fiscalização municipal" in terapeutica
    # O anexo da RE nº 3.436 não lista recolhimento: o texto não o acrescenta nem conclui que ele permanece.
    for wrong in ("recolhimento", "proibição de", "AFE", "estudo complementar", "Satisfatória", "denúncia"):
        assert wrong not in terapeutica_item and wrong not in terapeutica, wrong
    assert "href=" not in html[thathi_start:html.index("<h2>16 de setembro", thathi_start)]
    assert "href=" not in html[terapeutica_start:html.index("<h2>Agosto amplia", terapeutica_start)]


def test_september_measures_of_re_3440_3479_3480_3546_and_3738_keep_their_own_scope():
    html = NEWS_PATH.read_text(encoding="utf-8")

    def section(start, end):
        begin = html.index(start)
        return _text(html[begin:html.index(end, begin)])

    re3738 = section("<h2>23 de setembro: RE nº 3.738/2026", "<h2>23 de setembro: RE nº 3.743/2026")
    enhertu = section("<h3>Enhertu — lotes", "<h3>Mounjcaps — todos os lotes</h3>")
    mounjcaps = section("<h3>Mounjcaps — todos os lotes</h3>", "<h2>23 de setembro: RE nº 3.743/2026")
    tyg = section("<h2>11 de setembro: RE nº 3.546/2026", "<h2>8 de setembro: RE nº 3.479/2026")
    re3479 = section("<h2>8 de setembro: RE nº 3.479/2026", "<h2>8 de setembro: RE nº 3.480/2026")
    hytamicina = section("<h3>Hytamicina", "<h3>Pangastri")
    pangastri = section("<h3>Pangastri", "<h2>8 de setembro: RE nº 3.480/2026")
    re3480 = section("<h2>8 de setembro: RE nº 3.480/2026", "<h2>1º de setembro: RE nº 3.440/2026")
    mundial = section("<h3>Mundial Comércio de Encapsulados", "<h3>Produtos à base de retatrutida")
    gopharma = section("<h3>Produtos à base de retatrutida", "<h3>Anagalis")
    anagalis = section("<h3>Anagalis", "<h3>Dysport — lotes P08193")
    dysport = section("<h3>Dysport — lotes P08193", "<h3>Gripinew")
    gripinew = section("<h3>Gripinew", "<h2>1º de setembro: RE nº 3.440/2026")
    united = section("<h2>1º de setembro: RE nº 3.440/2026", "<h2>1º de setembro: RE nº 3.436/2026")

    # Ordem por data do DOU; no mesmo dia, medidas preventivas antes da revogação; RE nº 3.547 preservada antes da 3.546.
    positions = [html.index(h) for h in (
        "<h2>25 de setembro: RE nº 3.751/2026", "<h2>23 de setembro: RE nº 3.738/2026",
        "<h2>23 de setembro: RE nº 3.743/2026", "<h2>21 de setembro: RE nº 3.712",
        "<h2>Setembro: RE nº 3.547/2026", "<h2>11 de setembro: RE nº 3.546/2026",
        "<h2>8 de setembro: RE nº 3.479/2026", "<h2>8 de setembro: RE nº 3.480/2026",
        "<h2>1º de setembro: RE nº 3.440/2026", "<h2>1º de setembro: RE nº 3.436/2026", "<h2>Agosto amplia")]
    assert positions == sorted(positions)
    assert html.count("data-news-update-callout aria-labelledby=") == 7

    # Quadros: dois itens da RE nº 3.738 no quadro do topo; referência separada no quadro de setembro.
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-25-setembro-title"')
    top_items = [_text(item) for item in _items(html[start:html.index("</aside>", start)])]
    assert "Enhertu 100 mg — lotes 432221, 432844 e 432862 (RE nº 3.738/2026, DOU de 23/09/2026)" in top_items[3]
    assert "Mounjcaps — todos os lotes (RE nº 3.738/2026, DOU de 23/09/2026)" in top_items[4]
    assert "Não se refere ao Mounjaro" in top_items[4]
    september = _text(_september_callout(html))
    assert len(_items(_september_callout(html))) == 4
    assert "RE nº 3.440/2026 (DOU de 01/09, marca United Labz)" in september
    assert "RE nº 3.479 e 3.480/2026 (DOU de 08/09)" in september
    assert "RE nº 3.546/2026 (DOU de 11/09, interdição cautelar de um lote do TYG)" in september
    assert "Eles não integram a RE nº 3.547/2026." in september

    # RE nº 3.738/2026: Enhertu falsificado e Mounjcaps, sem atribuição à detentora nem confusão com Mounjaro.
    assert "Resolução-RE nº 3.738, de 22/09/2026, publicada no DOU em 23/09/2026" in re3738
    assert "distintas da revogação referente à Higia" in re3738
    re3738_intro = re3738.split("Enhertu — lotes", 1)[0]
    assert "duas medidas preventivas referentes a produtos distintos, cada uma com a motivação e o alcance indicados em seu item" in re3738_intro
    assert "em comum" not in re3738_intro and "sem empresa, produto ou fundamento" not in re3738_intro
    assert all(lote in enhertu for lote in ("432221", "432844", "432862"))
    assert "empresa responsável não identificada" in enhertu
    assert "Daiichi Sankyo Brasil Farmacêutica Ltda." in enhertu and "60.874.187/0001-84" in enhertu
    assert "proíbe o armazenamento, a comercialização, a distribuição, o transporte e o uso" in enhertu
    assert "A falsificação não é atribuída à detentora do registro" in enhertu
    assert "não alcança os demais lotes do Enhertu" in enhertu
    for wrong in ("fabricação", "propaganda", "importação", "recolhimento"):
        assert wrong not in enhertu, wrong
    assert "todos os lotes" in mounjcaps and "empresa desconhecida" in mounjcaps
    assert "“Mounjcaps Natural”" in mounjcaps
    assert "armazenamento, comercialização, distribuição, fabricação, propaganda, transporte e uso" in mounjcaps
    assert "não se refere ao Mounjaro" in mounjcaps
    for wrong in ("importação", "recolhimento"):
        assert wrong not in mounjcaps, wrong

    # RE nº 3.546/2026: interdição cautelar de um lote, por suspeita, com 90 dias.
    assert "Resolução-RE nº 3.546, de 09/09/2026, publicada no DOU em 11/09/2026" in tyg
    assert "2604940" in tyg and "TYG 50 mg" in tyg and "60.665.981/0001-18" in tyg
    assert "interdição cautelar" in tyg and "suspeita" in tyg and "90 dias" in tyg
    assert "a motivação registra suspeita, não desvio confirmado" in tyg
    assert "O anexo determina interdição cautelar e não lista recolhimento como ação adicional" in tyg
    assert "Enquanto a interdição estiver vigente, o lote não pode ser utilizado ou comercializado" in tyg
    assert "distinta da RE nº 3.547/2026" in tyg
    # A interdição não é apresentada como liberação: nenhuma negativa de "proibição" nem permissão de uso/venda.
    assert "não determina recolhimento nem proibição" not in tyg
    for wrong in ("pode ser utilizado e", "pode ser comercializado e", "pode ser utilizado ou comercializado durante",
                  "liberad", "permitid"):
        assert wrong not in tyg, wrong
    assert tyg.count("pode ser utilizado ou comercializado") == 1
    assert "não pode ser utilizado ou comercializado" in tyg
    # Fora da negativa exata do recolhimento, nenhuma outra ação é atribuída ao lote.
    tyg_rest = tyg.replace("não lista recolhimento como ação adicional", "")
    for wrong in ("recolhimento", "proibição", "proíbe", "apreensão", "suspensão de", "confirmação de desvio"):
        assert wrong not in tyg_rest, wrong
    assert "3.456" not in html

    # RE nº 3.479/2026: Hytamicina (desvio confirmado) e Pangastri (recolhimento voluntário).
    assert "Resolução-RE nº 3.479, de 03/09/2026, publicada no DOU em 08/09/2026" in re3479
    assert all(lote in hytamicina for lote in ("25091367", "25111733", "25081181"))
    assert "suspensão de comercialização, distribuição, fabricação e uso" in hytamicina
    assert "confirmação de desvio de qualidade" in hytamicina and "corpo estranho" in hytamicina
    for wrong in ("voluntário", "apreensão", "2610715"):
        assert wrong not in hytamicina, wrong
    assert "2610715" in pangastri and "recolhimento voluntário" in pangastri
    assert "suspensão de comercialização, distribuição e uso" in pangastri and "pedaço de vidro" in pangastri
    for wrong in ("fabricação", "confirmação", "25091367", "TYG"):
        assert wrong not in pangastri, wrong
    assert "não se estendem à produção das empresas" in re3479

    # RE nº 3.480/2026: cinco medidas sem operações trocadas entre itens.
    assert "Resolução-RE nº 3.480, de 03/09/2026" in re3480 and "DOU em 08/09/2026" in re3480
    re3480_intro = re3480.split("Mundial Comércio de Encapsulados", 1)[0]
    assert "adota cinco medidas preventivas, cada uma com os produtos, as ações e a motivação indicados em seu item" in re3480_intro
    assert "não compartilham" not in re3480_intro and "fundamento" not in re3480_intro
    for product in ("Lipo Top Gold", "Red Nature", "Mundial Caps BR (Lipo Bari)", "Mundial Caps Black (Lipo Top Extra Forte)"):
        assert product in mundial
    assert "56.137.545/0001-07" in mundial
    assert "proibição de comercialização, distribuição, fabricação, propaganda e uso" in mundial
    for wrong in ("importação", "armazenamento", "recolhimento"):
        assert wrong not in mundial, wrong
    assert "todos os produtos à base de retatrutida" in gopharma and "todos os produtos à base de tirzepatida" in gopharma
    assert "gopharma.shop" in gopharma
    assert all(name in gopharma for name in ("T.G. 15 mg", "Tirzec 15 mg", "Lipoless MD 15 mg", "Retatrutide"))
    assert "proibição de comercialização, distribuição, importação, propaganda e uso" in gopharma
    assert "não decide sobre medicamentos registrados" in gopharma
    for wrong in ("fabricação", "armazenamento", "Go Pharma"):
        assert wrong not in gopharma, wrong
    assert "suspensão da propaganda" in anagalis and "04.540.131/0001-12" in anagalis and "item 5.17.14" in anagalis
    assert "não suspende a atividade da farmácia" in anagalis
    anagalis_rest = anagalis.replace("nem determina recolhimento, apreensão ou proibição de manipulação", "")
    for wrong in ("recolhimento", "apreensão", "proibição", "suspensão de comercialização"):
        assert wrong not in anagalis_rest, wrong
    assert "P08193" in dysport and "06/2029" in dysport and "U14534" in dysport and "02/2029" in dysport
    assert "Beaufour Ipsen Farmacêutica Ltda." in dysport
    assert "proíbe a comercialização, a distribuição e o uso" in dysport
    assert "não se confundem com os três lotes de Dysport da RE nº 3.717/2026" in dysport
    assert "a falsificação não é atribuída à detentora do registro" in dysport
    for wrong in ("P08191", "P08192", "P22368", "armazenamento", "exportação", "importação", "propaganda"):
        assert wrong not in dysport, wrong
    re3717 = _text(_re3717_section(html))
    assert "P08193" not in re3717 and "U14534" not in re3717
    assert "OB2529" in gripinew and "0B2529" not in html
    assert "recolhimento voluntário" in gripinew
    assert "suspensão de comercialização, distribuição, exportação e uso" in gripinew
    assert "monitoramento contínuo da qualidade" in gripinew
    for wrong in ("fabricação", "apreensão"):
        assert wrong not in gripinew, wrong

    # RE nº 3.440/2026: toda a marca United Labz, sem extensão a outras marcas ou à revogação do mesmo dia.
    assert "Resolução-RE nº 3.440, de 31/08/2026, publicada no DOU em 01/09/2026" in united
    assert "todos os produtos da marca United Labz" in united
    assert "proíbe armazenamento, comercialização, distribuição, fabricação, importação, propaganda, transporte e uso" in united
    assert "não se estende a outras marcas" in united
    assert "distinta da revogação referente à Terapêutica" in united
    for wrong in ("recolhimento", "tirzepatida", "retatrutida"):
        assert wrong not in united, wrong

    # Sem links nas seções novas (nem para o endereço fiscalizado).
    assert "href=" not in html[html.index("<h2>23 de setembro: RE nº 3.738/2026"):html.index("<h2>23 de setembro: RE nº 3.743/2026")]
    assert "href=" not in html[html.index("<h2>11 de setembro: RE nº 3.546/2026"):html.index("<h2>1º de setembro: RE nº 3.436/2026")]
    assert "gopharma.shop/" not in html and "http://gopharma" not in html and "https://gopharma" not in html


def _october_06_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-06-outubro-title"')
    return html[start:html.index("</aside>", start)]


def test_october_06_callout_keeps_each_act_and_the_aloe_rectification_apart():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _october_06_callout(html)
    items = [_text(item) for item in _items(callout)]

    assert len(items) == 8
    labs, costa, sintonia, peptideos, marcas, imaavy, lizbi, aloe = items
    assert "LABS" in labs and "25.178.555/0001-59" in labs and "28/09/2026 a 02/10/2026" in labs
    assert "Costa Mar" not in labs and "Sintonia" not in labs
    assert "Costa Mar" in costa and "51.939.490/0001-27" in costa and "insulina glargina" in costa
    assert "não determina recolhimento nem apreensão" in costa and "não é proibição geral da insulina" in costa
    assert "Sintonia Pharma" in sintonia and "37.560.104/0001-60" in sintonia and "Vermefree" in sintonia
    assert "LABS" not in sintonia
    assert "empresa não identificada" in peptideos and "CNPJ é desconhecido" in peptideos
    assert "BPC157" not in peptideos and "Imaavy" not in peptideos
    assert "BPC157" in marcas and "Alluvi Healthcare" in marcas and "Oxygen KW Pharma" in marcas
    assert "Não é proibição geral da tirzepatida nem da retatrutida" in marcas
    assert "Imaavy" in imaavy and "JNYJ1201" in imaavy and "51.780.468/0001-87" in imaavy
    assert "não alcança outros lotes" in imaavy
    assert "Lizbi" in lizbi and "0000207107" in lizbi and "01.571.702/0001-98" in lizbi
    assert "restrita ao lote identificado" in lizbi
    assert "Biodis Industrial Ltda." in aloe and "União Vegetal Agroindustrial Ltda." in aloe
    assert "10.536.977/0001-81" in aloe
    assert "não cria outra medida nem altera o produto, os lotes ou as proibições" in aloe
    assert "RE nº 3.946 e 3.947 foram assinadas em 02/10/2026" in _text(callout)
    assert "publicação de ambas no DOU de 06/10/2026" in _text(callout)
    for number in ("3.850", "3.852", "3.854", "3.855", "3.856", "3.857"):
        assert number not in callout


def _october_callout(html):
    start = html.index('data-news-update-callout aria-labelledby="novas-medidas-02-outubro-title"')
    return html[start:html.index("</aside>", start)]


def _normalize_search(value):
    # Mesma normalização de normalizeText() em assets/js/main.js: minúsculas, NFD e sem diacríticos.
    import unicodedata
    value = unicodedata.normalize("NFD", value.lower())
    return "".join(ch for ch in value if not "\u0300" <= ch <= "\u036f").strip()


def test_october_callout_keeps_each_measure_bound_to_its_own_act_and_scope():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _october_callout(html)
    items = [_text(item) for item in _items(callout)]

    # Quadro de 02/10/2026 antes dos cinco anteriores, que permanecem.
    assert html.count("data-news-update-callout aria-labelledby=") == 7
    assert html.index("novas-medidas-06-outubro-title") < html.index("novas-medidas-02-outubro-title")
    assert html.index("novas-medidas-02-outubro-title") < html.index("novas-medidas-25-setembro-title")
    assert "Atualização: medidas publicadas no DOU em 02/10/2026" in callout and "ATUALIZAÇÃO" in callout
    assert len(items) == 7
    gtech, hidrafemme, cosmeticos, multjet, lgr, brmega, biojet = items

    # RE nº 3.850/2026: só o lote da C & P, só três operações suspensas.
    assert "G TECH" in gtech and "lote Z25J215F1 (RE nº 3.850/2026, suspensão)" in gtech
    assert "suspensão de comercialização, distribuição e propaganda do lote" in gtech
    assert "C &amp; P Comércio de Produtos Médicos, Farmacêuticos e Hospitalares Ltda." in gtech
    assert "venda ao consumidor final" in gtech
    for wrong in ("recolhimento", "apreensão", "proibição", "falsific", "desvio", "importação", "fabricação", "propaganda e uso"):
        assert wrong not in gtech, wrong

    # RE nº 3.852/2026: lote “lot 2 2511006”, origem desconhecida, Helianto como detentora que comunicou.
    assert "lote “lot 2 2511006” (RE nº 3.852/2026)" in hidrafemme
    assert "recolhimento e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in hidrafemme
    assert "de empresa desconhecida" in hidrafemme and "Helianto Farmacêutica, detentora do registro" in hidrafemme
    assert "a falsificação não é atribuída a ela" in hidrafemme
    assert "apreensão" not in hidrafemme

    # RE nº 3.854/2026, itens 1, 2 e 4: apreensão de cosméticos; Perspirex só nos dois lotes.
    assert "Perspirex Strong (lotes 614326 e 614323), MAV C-22 e GhostBond XL (todos os lotes) — RE nº 3.854/2026, itens 1, 2 e 4" in cosmeticos
    assert "apreensão e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in cosmeticos
    assert "a Megalabs desconhece a fabricação das unidades" in cosmeticos
    assert "no MAV C-22 e no GhostBond XL, o motivo é a falta de regularização sanitária" in cosmeticos
    for wrong in ("recolhimento", "Mult Jet", "item 3"):
        assert wrong not in cosmeticos, wrong

    # RE nº 3.854/2026, item 3: recolhimento dos dois saneantes Mult Jet, sem apreensão.
    assert "Mult Jet — Desincrustante Ácido DX 1:40 Mult-Cap e Água Sanitária, todos os lotes (RE nº 3.854/2026, item 3)" in multjet
    assert "recolhimento e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso desses dois saneantes" in multjet
    for wrong in ("apreensão", "Perspirex", "todos os saneantes"):
        assert wrong not in multjet, wrong

    # RE nº 3.855/2026: suspensão geral de três operações (item 1) separada do recorte dos três produtos (item 2).
    assert "LGR Indústria e Comércio de Produtos de Limpeza (RE nº 3.855/2026)" in lgr
    item1, item2 = lgr.split("o item 2", 1)
    assert "o item 1 suspende a comercialização, a distribuição e a fabricação de todos os saneantes da empresa" in item1
    assert "inspeção de 14 a 18/09/2026" in item1
    assert "recolhimento" not in item1 and "uso" not in item1
    assert "determina recolhimento e suspensão de comercialização, distribuição, fabricação e uso apenas do Medicpro Zime, do Medicpro Zime Ultra e do Lapzyme" in item2

    # RE nº 3.856/2026: todos os saneantes, com a marca BR MT LIMP; sem importação nem recolhimento.
    assert "BR Mega Limp — todos os saneantes, incluindo os da marca BR MT LIMP (RE nº 3.856/2026)" in brmega
    assert "apreensão e proibição de comercialização, distribuição, fabricação, propaganda e uso" in brmega
    for wrong in ("importação", "transporte", "recolhimento"):
        assert wrong not in brmega, wrong

    # RE nº 3.857/2026: só os dois produtos da Biojet.
    assert "Biojet — Bio Lavanda Limpador de Uso Geral e Bio Água Sanitária, todos os lotes (RE nº 3.857/2026)" in biojet
    assert "recolhimento e proibição de comercialização, distribuição, fabricação, importação, propaganda e uso desses dois produtos" in biojet
    for wrong in ("todos os saneantes", "toda a produção", "apreensão"):
        assert wrong not in biojet, wrong

    # Assinatura em setembro, publicação e vigência em 02/10; nenhum item mistura atos.
    closing = _text(callout.split("</ul>", 1)[1])
    assert "assinadas em 29 e 30/09/2026 e publicadas no DOU em 02/10/2026, data em que entraram em vigor" in closing
    for item, own in zip(items, ("3.850", "3.852", "3.854", "3.854", "3.855", "3.856", "3.857")):
        assert all(other not in item for other in ("3.850", "3.852", "3.854", "3.855", "3.856", "3.857") if other != own)
    assert "href=" not in callout


def test_october_body_sections_preserve_products_lots_operations_and_limits():
    html = NEWS_PATH.read_text(encoding="utf-8")

    def section(start, end):
        begin = html.index(start)
        return _text(html[begin:html.index(end, begin)])

    heads = ("<h2>2 de outubro: RE nº 3.850/2026", "<h2>2 de outubro: RE nº 3.852/2026", "<h2>2 de outubro: RE nº 3.854/2026",
             "<h2>2 de outubro: RE nº 3.855/2026", "<h2>2 de outubro: RE nº 3.856/2026", "<h2>2 de outubro: RE nº 3.857/2026",
             "<h2>28 de setembro: RE nº 3.764/2026")
    positions = [html.index(h) for h in heads]
    # Bloco de 02/10 depois do resumo regulatório e antes dos atos de setembro.
    assert html.index("Resumo regulatório") < positions[0] and positions == sorted(positions)
    gtech, hidrafemme, re3854, lgr, brmega, biojet = (_text(html[a:b]) for a, b in zip(positions, positions[1:]))
    perspirex = section("<h3>Item 1 — Perspirex Strong", "<h3>Item 2 — MAV C-22")
    mav = section("<h3>Item 2 — MAV C-22", "<h3>Item 4 — GhostBond XL")
    ghost = section("<h3>Item 4 — GhostBond XL", "<h3>Item 3 — Mult Jet")
    mult = section("<h3>Item 3 — Mult Jet", "<h2>2 de outubro: RE nº 3.855/2026")
    lgr1 = section("<h3>Item 1 — todos os saneantes da LGR", "<h3>Item 2 — Medicpro Zime")
    lgr2 = section("<h3>Item 2 — Medicpro Zime", "<h2>2 de outubro: RE nº 3.856/2026")

    for part, number, signed in ((gtech, "3.850", "29/09/2026"), (hidrafemme, "3.852", "29/09/2026"), (re3854, "3.854", "30/09/2026"),
                                 (lgr, "3.855", "30/09/2026"), (brmega, "3.856", "30/09/2026"), (biojet, "3.857", "30/09/2026")):
        assert f"Resolução-RE nº {number}, de {signed}, publicada no DOU em 02/10/2026" in part, number

    # G TECH: empresa e lote do anexo, três operações suspensas, sem recolhimento, apreensão ou falsificação.
    assert "C &amp; P Comércio de Produtos Médicos, Farmacêuticos e Hospitalares Ltda." in gtech and "36.470.048/0001-00" in gtech
    assert "tiras reagentes para medição de glicose G TECH" in gtech and "lote Z25J215F1" in gtech
    assert "determina a suspensão de comercialização, distribuição e propaganda" in gtech
    assert "inciso IV do art. 10 da Lei nº 6.437/1977" in gtech
    assert "A medida é restrita à empresa e ao lote indicados" in gtech and "não alcança as tiras G TECH em geral" in gtech
    gtech_rest = gtech.replace("O ato não determina recolhimento nem apreensão", "")
    for wrong in ("recolhimento", "apreensão", "proíbe", "proibição", "falsific", "desvio", "importação", "fabricação"):
        assert wrong not in gtech_rest, wrong

    # Hidrafemme: identificador “lot 2 2511006” preservado; origem desconhecida; Helianto não é a fabricante.
    assert "“lot 2 2511006”" in hidrafemme
    assert html.count("2511006") == html.count("lot 2 2511006") == 2
    assert "A empresa responsável por essas unidades e o respectivo CNPJ constam como desconhecidos" in hidrafemme
    assert "determina o recolhimento e proíbe a comercialização, a distribuição, a fabricação, a importação, a propaganda e o uso" in hidrafemme
    assert "Helianto Farmacêutica Ltda." in hidrafemme and "detentora do registro do produto, identificou unidades" in hidrafemme
    assert "A falsificação não é atribuída à Helianto" in hidrafemme and "não alcança os demais lotes do Hidrafemme" in hidrafemme
    for wrong in ("apreensão", "fabricadas pela Helianto", "fabricado pela Helianto", "Shopee"):
        assert wrong not in hidrafemme, wrong

    # RE nº 3.854/2026: ordem editorial 1, 2, 4, 3 com os números corretos; apreensão nos cosméticos, recolhimento no Mult Jet.
    assert "Os itens 1, 2 e 4 tratam de cosméticos e determinam apreensão; o item 3 trata de saneantes e determina recolhimento" in re3854
    assert all(lote in perspirex for lote in ("614326", "614323"))
    assert "Megalabs Farmacêutica S.A." in perspirex and "33.026.055/0001-20" in perspirex
    assert "desconhece a fabricação dessas unidades" in perspirex
    assert "A fabricação dessas unidades não é atribuída à Megalabs" in perspirex and "se limita aos dois lotes indicados" in perspirex
    for part in (perspirex, mav, ghost):
        assert "determina a apreensão e proíbe a comercialização, a distribuição, a fabricação, a importação, a propaganda e o uso" in part
        assert "recolhimento" not in part
    assert "todos os lotes" not in perspirex and "fabricadas pela Megalabs" not in perspirex
    for part in (mav, ghost):
        assert "sem regularização sanitária" in part and "todos os lotes" in part
        for wrong in ("falsific", "Megalabs", "dados cadastrais"):
            assert wrong not in part, wrong
    assert "MAV C-22 Solvente Removedor Cola Mega Hair" in mav
    assert "GhostBond XL — With Xtra Moisture Control Cola para Próteses Capilares" in ghost
    assert "Desincrustante Ácido DX 1:40 Mult-Cap Mult Jet" in mult and "Água Sanitária Mult Jet" in mult
    assert "Ramos Indústria e Comércio de Materiais de Limpeza Ltda." in mult and "46.069.515/0001-49" in mult
    assert "o ato determina o recolhimento" in mult
    assert "além da proibição de comercialização, distribuição, fabricação, importação, propaganda e uso" in mult
    assert "não se estende aos demais saneantes da Ramos" in mult
    assert "apreensão" not in mult.replace("não determina apreensão", "")

    # LGR: item 1 (todos os saneantes, três operações suspensas) separado do item 2 (três produtos, recolhimento e uso).
    assert "LGR Indústria e Comércio de Produtos de Limpeza Ltda." in lgr and "08.706.183/0001-77" in lgr
    assert "todos os produtos saneantes da empresa, em todos os lotes, e determina a suspensão de comercialização, distribuição e fabricação" in lgr1
    assert "RDC nº 47/2013" in lgr1 and "14 a 18/09/2026" in lgr1
    assert "Essas datas são as da inspeção e não delimitam a produção nem os lotes alcançados" in lgr1
    lgr1_rest = lgr1.replace("O item 1 não determina recolhimento nem suspensão do uso", "")
    assert "recolhimento" not in lgr1_rest and not re.search(r"\buso\b", lgr1_rest)
    assert all(product in lgr2 for product in ("Medicpro Zime", "Medicpro Zime Ultra", "Lapzyme"))
    assert "determina o recolhimento e a suspensão de comercialização, distribuição, fabricação e uso" in lgr2
    assert "valem apenas para os três produtos do item 2, e não para toda a produção da LGR" in lgr2

    # BR Mega Limp: todos os saneantes, com BR MT LIMP; sem importação, transporte ou recolhimento.
    assert "todos os produtos saneantes da BR Mega Limp Ltda." in brmega and "BR MT LIMP" in brmega and "16.731.434/0001-00" in brmega
    assert "determina a apreensão e proíbe a comercialização, a distribuição, a fabricação, a propaganda e o uso" in brmega
    assert "importação" not in brmega and "transporte" not in brmega
    assert "recolhimento" not in brmega.replace("O anexo não determina recolhimento.", "")

    # Biojet: só os dois produtos.
    assert "Bio Lavanda Limpador de Uso Geral Biojet" in biojet and "Bio Água Sanitária Biojet" in biojet
    assert "Biojet Indústria de Produtos Químicos Ltda." in biojet and "04.611.333/0001-08" in biojet
    assert "determina o recolhimento e proíbe a comercialização, a distribuição, a fabricação, a importação, a propaganda e o uso desses produtos" in biojet
    assert "A medida alcança apenas os dois produtos indicados, e não toda a produção da Biojet" in biojet
    for wrong in ("todos os produtos saneantes", "todos os saneantes", "apreensão"):
        assert wrong not in biojet, wrong

    # Sem links, prazos inventados ou atos fora da fase.
    block = html[positions[0]:positions[-1]]
    assert "href=" not in block
    for wrong in ("prazo de", "até que", "renova", "autoriza"):
        assert wrong not in _text(block), wrong
    assert "3.851" not in html and "3.853" not in html


def test_october_update_reaches_lead_summary_metadata_and_listing_search():
    html = NEWS_PATH.read_text(encoding="utf-8")
    news_index = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    description = ("Medidas recentes alcançam medicamentos, dispositivos médicos, cosméticos, saneantes e produtos sem registro, "
                   "inclusive itens divulgados com alegação emagrecedora.")

    assert html.count(description) == 4  # description, og, twitter e JSON-LD
    assert '"keywords": "medicamentos, dispositivos médicos, cosméticos,' in html
    assert "Medidas de julho a outubro alcançaram medicamentos, dispositivos médicos, cosméticos, saneantes" in html
    assert '"headline": "Anvisa suspende medicamento e proíbe produtos irregulares"' in html
    assert f'<meta content="{UPDATED}" property="article:modified_time"/>' in html

    card = _consolidated_card(news_index)
    assert "anvisa-suspende-medicamento-proibe-produtos-irregulares" in card
    attrs = dict(re.findall(r'\b(data-[a-z-]+)="([^"]*)"', card.split(">", 1)[0]))
    haystack = _normalize_search(" ".join([attrs["data-title"], attrs["data-summary"], attrs["data-keywords"],
                                           attrs["data-tags"], _text(card)]).replace("&amp;", "&"))
    for term in ("G TECH", "Hidrafemme", "Perspirex", "MAV C-22", "GhostBond XL", "Mult Jet", "LGR", "Medicpro",
                 "Lapzyme", "BR Mega Limp", "BR MT LIMP", "Biojet", "dispositivos médicos", "RE 3.850/2026",
                 "RE 3.852/2026", "RE 3.854/2026", "RE 3.855/2026", "RE 3.856/2026", "RE 3.857/2026"):
        assert _normalize_search(term) in haystack, term
    assert _consolidated_card(news_index).count(f'data-updated="{UPDATED}"') == 1
    # O mesmo minuto também carimba o SNCR e a DCB; o empate conserva a ordem relativa.
    assert news_index.count(f'data-updated="{UPDATED}"') == 3
