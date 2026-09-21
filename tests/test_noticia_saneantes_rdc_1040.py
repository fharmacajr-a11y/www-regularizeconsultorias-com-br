import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ARTICLE_PATH = ROOT / "noticias" / "anvisa-rdc-1040-in-468-2026-saneantes-regularizacao" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
ARTICLE_URL = "https://www.regularizeconsultorias.com.br/noticias/anvisa-rdc-1040-in-468-2026-saneantes-regularizacao/"
DATE_PUBLISHED = "2026-09-15T16:17:00-03:00"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _article_html():
    return ARTICLE_PATH.read_text(encoding="utf-8")


def _index_html():
    return NEWS_INDEX_PATH.read_text(encoding="utf-8")


def _jsonld_blocks(html):
    pattern = re.compile(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL
    )
    return [json.loads(m.group(1)) for m in pattern.finditer(html)]


# ---------------------------------------------------------------------------
# Testes do arquivo da notícia
# ---------------------------------------------------------------------------


def test_article_file_exists():
    assert ARTICLE_PATH.is_file(), f"Arquivo não encontrado: {ARTICLE_PATH}"


def test_article_has_canonical():
    html = _article_html()
    assert f'rel="canonical"' in html
    assert ARTICLE_URL in html


def test_article_has_single_h1():
    html = _article_html()
    h1_matches = re.findall(r'<h1[^>]*>', html, re.IGNORECASE)
    assert len(h1_matches) == 1, f"Esperado 1 h1, encontrado {len(h1_matches)}"


def test_article_title_contains_rdc_1040_in_468():
    html = _article_html()
    assert "RDC 1.040" in html or "RDC&nbsp;1.040" in html
    assert "IN 468" in html or "IN&nbsp;468" in html or "IN 468/2026" in html


def test_article_has_no_noindex():
    html = _article_html()
    robots_meta = re.findall(
        r'<meta[^>]+name=["\']robots["\'][^>]*>', html, re.IGNORECASE
    )
    for tag in robots_meta:
        assert "noindex" not in tag.casefold(), f"noindex encontrado: {tag}"


def test_article_has_adsense_snippet():
    html = _article_html()
    assert "ca-pub-2993532924249779" in html


def test_article_og_image_is_fallback_noticias():
    html = _article_html()
    assert "assets/img/og/noticias.jpg" in html


def test_article_og_image_alt_is_public_and_descriptive():
    """O og:image:alt é metadado público: não pode conter anotação interna
    (ex.: 'OG TEMPORÁRIA') e deve descrever a matéria de forma legível."""
    html = _article_html()
    match = re.search(r'<meta content="([^"]*)" property="og:image:alt"/>', html)
    assert match, "meta og:image:alt não encontrada"
    alt_text = match.group(1)
    assert "OG TEMPORÁRIA" not in alt_text
    assert "substituir futuramente" not in alt_text.casefold()
    assert "saneantes" in alt_text.casefold()


def test_article_jsonld_newsarticle_is_valid():
    html = _article_html()
    blocks = _jsonld_blocks(html)
    news_blocks = [b for b in blocks if b.get("@type") == "NewsArticle"]
    assert news_blocks, "Bloco NewsArticle ausente"
    news = news_blocks[0]
    assert news["datePublished"] == DATE_PUBLISHED
    assert news["dateModified"] == DATE_PUBLISHED
    assert news["url"] == ARTICLE_URL
    assert "1.040" in news["headline"] or "RDC" in news["headline"]
    assert news["articleSection"] == "ANVISA"
    assert news["publisher"]["name"] == "Regularize Consultoria"


def test_article_jsonld_breadcrumb_is_valid():
    html = _article_html()
    blocks = _jsonld_blocks(html)
    bc_blocks = [b for b in blocks if b.get("@type") == "BreadcrumbList"]
    assert bc_blocks, "Bloco BreadcrumbList ausente"
    items = bc_blocks[0]["itemListElement"]
    assert len(items) == 3
    assert items[0]["item"] == "https://www.regularizeconsultorias.com.br/"
    assert items[1]["item"] == "https://www.regularizeconsultorias.com.br/noticias/"
    assert items[2]["item"] == ARTICLE_URL


def test_article_mentions_rdc_989_2025():
    html = _article_html()
    assert "RDC 989/2025" in html or "RDC&nbsp;989/2025" in html


def test_article_mentions_in_394_2025():
    html = _article_html()
    assert "IN 394/2025" in html or "394/2025" in html


def test_article_mentions_escoamento_365_dias():
    html = _article_html()
    assert "365 dias" in html or "365&nbsp;dias" in html


def test_article_mentions_escoamento_60_dias():
    html = _article_html()
    assert "60 dias" in html or "60&nbsp;dias" in html


def test_article_mentions_ciatox():
    html = _article_html()
    assert "CIATox" in html or "ciatox" in html.casefold()


def test_article_not_mix_fiscalizacao_apreensao():
    """Confirmação de isolamento editorial: não misturar com apreensão/fiscalização de saneantes."""
    html = _article_html()
    # A notícia trata APENAS de regularização/rotulagem — não deve linkar para a
    # matéria consolidada de produtos irregulares.
    assert "anvisa-apreensao-saneante-cosmeticos-irregulares" not in html


def test_article_does_not_promise_approval():
    """Garantia editorial: não prometer aprovação, deferimento ou regularização automática."""
    html = _article_html()
    forbidden_phrases = [
        "garante aprovação",
        "garantirá aprovação",
        "será deferido",
        "regularização automática",
        "aprova automaticamente",
    ]
    html_lower = html.casefold()
    for phrase in forbidden_phrases:
        assert phrase not in html_lower, f"Frase proibida encontrada: {phrase!r}"


def test_article_has_institutional_disclaimer():
    html = _article_html()
    assert "empresa privada e independente" in html


# ---------------------------------------------------------------------------
# Testes do índice de notícias
# ---------------------------------------------------------------------------


def test_index_contains_saneantes_card():
    html = _index_html()
    assert "anvisa-rdc-1040-in-468-2026-saneantes-regularizacao" in html


def test_index_saneantes_card_has_correct_timestamp():
    html = _index_html()
    assert f'data-updated="{DATE_PUBLISHED}"' in html


def test_index_saneantes_in_itemlist_position_3():
    html = _index_html()
    blocks = _jsonld_blocks(html)
    coll_blocks = [b for b in blocks if b.get("@type") == "CollectionPage"]
    assert coll_blocks, "CollectionPage ausente no índice"
    items = coll_blocks[0]["mainEntity"]["itemListElement"]
    assert items[2]["url"] == ARTICLE_URL, (
        f"Posição 3 esperada para {ARTICLE_URL!r}, encontrado {items[2]['url']!r}"
    )
    assert items[2]["position"] == 3


def test_index_itemlist_positions_are_sequential():
    html = _index_html()
    blocks = _jsonld_blocks(html)
    coll_blocks = [b for b in blocks if b.get("@type") == "CollectionPage"]
    items = coll_blocks[0]["mainEntity"]["itemListElement"]
    positions = [item["position"] for item in items]
    assert positions == list(range(1, len(positions) + 1))


def test_index_saneantes_card_is_not_compact():
    """O card deve ser exibido como featured (sem news-card-compact) pois é a notícia mais recente."""
    html = _index_html()
    article_match = re.search(
        r'(<article[^>]*data-updated="2026-09-15T16:17:00-03:00"[^>]*>.*?</article>)',
        html,
        re.DOTALL,
    )
    assert article_match, "Card do saneantes não localizado no índice"
    card_html = article_match.group(1)
    opening_tag = card_html.split(">", 1)[0]
    assert "news-card-compact" not in opening_tag, (
        "Card do saneantes não deve ter news-card-compact (é featured)"
    )


def test_index_saneantes_card_is_unique():
    html = _index_html()
    matches = re.findall(
        r'href="/noticias/anvisa-rdc-1040-in-468-2026-saneantes-regularizacao/"', html
    )
    assert len(matches) == 1, f"Esperado exatamente 1 link/card no índice, encontrado {len(matches)}"


def test_index_keeps_exactly_five_highlighted_cards():
    """`news-featured-card` está presente em TODOS os cards (não é o marcador de
    destaque). O marcador real é a AUSÊNCIA de `news-card-compact`. O padrão do
    site mantém exatamente 5 cards destacados (sem `news-card-compact`) no topo
    da listagem; ao entrar uma notícia nova em 1º, o antigo 5º destacado deve
    passar a compacto."""
    html = _index_html()
    articles = re.findall(r'<article class="([^"]*)"[^>]*data-news-card', html)
    assert len(articles) >= 6
    highlighted = [c for c in articles if "news-card-compact" not in c]
    assert len(highlighted) == 5, (
        f"Esperado exatamente 5 cards destacados (sem news-card-compact), "
        f"encontrado {len(highlighted)}"
    )
    # Os 5 primeiros cards da listagem devem ser exatamente os 5 destacados.
    assert all("news-card-compact" not in c for c in articles[:5])
    # O 6º card (antigo 5º destacado) deve ser o primeiro compacto.
    assert "news-card-compact" in articles[5]


def test_index_saneantes_is_third_of_five_highlighted():
    html = _index_html()
    article_blocks = re.findall(
        r'<article class="[^"]*"[^>]*data-news-card.*?</article>', html, re.DOTALL
    )
    assert article_blocks, "Nenhum card encontrado no índice"
    third_block = article_blocks[2]
    assert "news-card-compact" not in third_block
    assert "anvisa-rdc-1040-in-468-2026-saneantes-regularizacao" in third_block


# ---------------------------------------------------------------------------
# Testes específicos de conformidade regulatória (Item 18 do prompt)
# ---------------------------------------------------------------------------


def test_article_official_publication_date():
    html = _article_html()
    assert "28/08/2026" in html, "Data de publicação oficial dos atos (28/08/2026) ausente"


def test_article_mentions_versoes_produto():
    html = _article_html()
    assert "versão" in html.casefold() or "versões" in html.casefold()
    assert "mesmo número de autorização" in html.casefold()


def test_article_mentions_extrazona_and_cvl():
    html = _article_html()
    assert "extrazona" in html.casefold()
    assert "cvl" in html.casefold() or "certificado de venda livre" in html.casefold()


def test_article_mentions_packaging_limits_10l_and_50l():
    html = _article_html()
    assert "10 l" in html.casefold() or "10 kg" in html.casefold()
    assert "50 l" in html.casefold() or "50 kg" in html.casefold()
    assert "piscinas" in html.casefold()


def test_article_mentions_ph_assay_by_company():
    html = _article_html()
    assert "ph" in html.casefold()
    assert "própria empresa" in html.casefold()


def test_article_mentions_vigencia_na_publicacao():
    html = _article_html()
    assert "em vigor na data de sua publicação" in html.casefold() or "vigência" in html.casefold()


def test_article_mentions_procedimento_simplificado_risco_2():
    html = _article_html()
    assert "procedimento simplificado" in html.casefold()
    assert "risco 2" in html.casefold()
    assert "imediatamente após a protocolização" in html.casefold()


def test_article_sitemap_entry():
    sitemap_path = ROOT / "sitemap.xml"
    sitemap_text = sitemap_path.read_text(encoding="utf-8")
    assert ARTICLE_URL in sitemap_text
    assert "<lastmod>2026-09-15</lastmod>" in sitemap_text


# ---------------------------------------------------------------------------
# Testes negativos contra simplificações indevidas (Item 18 do prompt)
# ---------------------------------------------------------------------------


def test_negative_not_claim_all_labels_have_365_days():
    html = _article_html().casefold()
    forbidden_simplifications = [
        "todo rótulo pode ser utilizado por 365 dias",
        "todos os rótulos podem ser utilizados por 365 dias",
        "qualquer alteração tem prazo de 365 dias",
        "prazo de 365 dias para qualquer alteração",
        "todas as alterações de rotulagem têm 365 dias",
    ]
    for phrase in forbidden_simplifications:
        assert phrase not in html, f"Simplificação incorreta de 365 dias encontrada: {phrase!r}"


def test_negative_not_claim_all_changes_implemented_immediately():
    html = _article_html().casefold()
    forbidden_simplifications = [
        "qualquer alteração regulatória pode ser implementada imediatamente",
        "todas as alterações podem ser implementadas imediatamente",
        "qualquer alteração de rotulagem pode ser implementada imediatamente",
        "toda alteração pode ser implementada imediatamente",
        # Formulação universal/absoluta removida: não deve afirmar que NENHUMA
        # outra alteração ou petição pode ser implementada imediatamente — essa
        # é uma generalização não sustentada pelo art. 47-C, que trata apenas do
        # procedimento simplificado específico.
        "nenhuma outra alteração ou petição regulatória pode ser implementada imediatamente",
    ]
    for phrase in forbidden_simplifications:
        assert phrase not in html, f"Simplificação incorreta de implementação imediata encontrada: {phrase!r}"


def test_article_restricts_art_47c_scope_correctly():
    """O texto deve vincular a implementação imediata ao art. 47-C sem
    generalizar a restrição para 'nenhuma outra alteração ou petição'."""
    html = _article_html().casefold()
    assert "decorre do art. 47-c" in html
    assert "não deve ser estendida" in html
    assert "fora das condições ali previstas" in html


def test_article_mentions_official_sources_as_plain_text():
    """Padrão editorial da Regularize: fontes oficiais são citadas textualmente,
    sem hyperlink externo. A notícia deve mencionar a fonte oficial da Anvisa e
    o Diário Oficial da União como texto simples."""
    html_lower = _article_html().casefold()
    assert "notícia oficial da anvisa" in html_lower, "Menção textual à notícia oficial da Anvisa ausente"
    assert "diário oficial da união de 28/08/2026" in html_lower, (
        "Menção textual ao Diário Oficial da União de 28/08/2026 ausente"
    )


def test_article_has_no_external_source_hyperlinks():
    """Regra do site: notícias da Regularize não usam hyperlink externo para
    gov.br, in.gov.br (DOU) ou AnvisaLegis como destino de navegação. As fontes
    devem ser citadas apenas textualmente."""
    html = _article_html()
    forbidden_href_fragments = [
        'href="https://www.gov.br/',
        'href="https://gov.br/',
        'href="https://www.in.gov.br/',
        'href="https://in.gov.br/',
        'href="https://anvisalegis.datalegis.net',
    ]
    for fragment in forbidden_href_fragments:
        assert fragment not in html, f"Hyperlink externo de fonte encontrado: {fragment!r}"
    # Nenhuma menção a esses domínios deve aparecer como destino de link em
    # nenhum lugar do artigo (mesmo fora do corpo principal).
    assert "anvisalegis.datalegis.net" not in html, "Referência ao AnvisaLegis ainda presente no HTML"
    assert "in.gov.br" not in html, "Referência ao domínio in.gov.br (DOU) ainda presente no HTML"
    assert "gov.br/anvisa" not in html, "Referência ao domínio gov.br/anvisa ainda presente no HTML"


def test_article_does_not_add_new_sources_section():
    """A regra pede citação textual das fontes sem criar seção nova de
    'Fontes', 'Referência oficial' ou bibliografia, nem CTA externo."""
    html_lower = _article_html().casefold()
    forbidden_headings = [
        ">fontes<",
        ">referência oficial<",
        ">referencias<",
        ">referências<",
        ">bibliografia<",
    ]
    for heading in forbidden_headings:
        assert heading not in html_lower, f"Seção/heading não permitido encontrado: {heading!r}"


def test_article_has_no_local_or_file_links():
    html = _article_html()
    assert "file:///" not in html
    assert "d:/" not in html.lower()
    assert "d:\\" not in html.lower()
    assert "c:/" not in html.lower()
    assert "c:\\" not in html.lower()


def test_article_fine_normative_phrasing_365_and_60_days():
    html = _article_html().casefold()
    # 365 dias: art. 47-A, após aprovação do pleito, sem prorrogação
    assert "art. 47-a" in html
    assert "365 dias após aprovação do pleito" in html
    assert "sem prorrogação" in html
    # 60 dias: art. 47-B, após aprovação do pleito, sem prorrogação
    assert "art. 47-b" in html
    assert "60 dias após aprovação do pleito" in html
