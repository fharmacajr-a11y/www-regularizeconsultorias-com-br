import json
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import parse_qs, unquote, urlsplit


ROOT = Path(__file__).parents[2]
NEWS_PATH = ROOT / "noticias" / "rdc-1000-2025-anvisa-prorroga-prazo-sncr" / "index.html"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
COMUNICADO_PATH = ROOT / "comunicado" / "index.html"
SERVICOS_PATH = ROOT / "servicos" / "index.html"
SITEMAP_PATH = ROOT / "sitemap.xml"
POP_PATH = ROOT / "manuais-e-pops" / "pop-sncr" / "index.html"
ROUTE = "/noticias/rdc-1000-2025-anvisa-prorroga-prazo-sncr/"
URL = f"https://www.regularizeconsultorias.com.br{ROUTE}"
PUBLISHED = "2026-05-28T20:36:00-03:00"
# 20/10/2026, 13h00: quadro do lote 2 (informe de 15/10 e Perguntas e Respostas sobre a integração, 1ª edição).
UPDATED = "2026-10-20T13:00:00-03:00"
UPDATE_20_10_ID = "sncr-atualizacao-20-outubro-title"
STAGE_UPDATE_ID = "sncr-etapa-update-title"
# Fora desta atualização: os 16 dígitos e o registro de mais de um medicamento por receita (anunciados para
# 19/10/2026 às 18h, sem confirmação até 20/10/2026 às 10h30) e a pergunta 47, com marcas de rascunho no PDF.
HELD_BACK_TERMS = (
    "16 dígitos",
    "16 digitos",
    "14 para 16",
    "mais de um medicamento",
    "P47",
    "pergunta 47",
    "questão 47",
)
TITLE = "SNCR: etapa anunciada, transição e sistemas"
ADSENSE_SCRIPT_MARKER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
WHATSAPP_NEWS_TEXT = (
    "Olá! Vi a notícia da Regularize sobre o SNCR e gostaria de verificar "
    "a habilitação da minha farmácia."
)
WHATSAPP_SERVICO_TEXT = (
    "Olá! Gostaria de informações sobre o serviço de implantação e "
    "habilitação do SNCR para minha farmácia."
)
FORBIDDEN_CLAIMS = (
    "o sncr começa em 30",
    "o sncr começa em 30/09",
    "sncr começa em 30 de setembro de 2026",
    "prescrição eletrônica passa a ser obrigatória",
    "prescrição eletrônica se torna obrigatória",
    "substitui o sngpc",
    "29/10 invalida",
    "vence automaticamente",
    "garantimos acesso",
    "garantimos habilitação",
    "sua farmácia ficará irregular automaticamente",
    "obrigatório contratar",
    "prazo foi prorrogado novamente",
    "nova prorrogação foi anunciada",
    "prazo passa de 30/09/2026",
)


def _text(html):
    return " ".join(re.sub(r"<[^>]+>", " ", html).split())


def _callout(html, labelled_by=STAGE_UPDATE_ID):
    start = html.index(f'<aside data-news-update-callout aria-labelledby="{labelled_by}"')
    return html[start:html.index("</aside>", start)]


def _news_cards(html):
    return re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", html, re.DOTALL)


def _active_notices(html):
    return [
        article
        for article in re.findall(r"(<article\b[^>]*>.*?</article>)", html, re.DOTALL)
        if 'data-status="resolved"' not in article.split(">", 1)[0]
    ]


def _jsonld_blocks(html):
    pattern = re.compile(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', re.DOTALL
    )
    return [json.loads(match.group(1)) for match in pattern.finditer(html)]


def test_sncr_news_keeps_publication_and_updates_the_september_stage():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _callout(html)
    callout_text = _text(callout)

    assert f"<title>{TITLE} | Regularize Consultoria</title>" in html
    assert f'"datePublished": "{PUBLISHED}"' in html
    assert f'"dateModified": "{UPDATED}"' in html
    assert datetime.fromisoformat(UPDATED) > datetime.fromisoformat(PUBLISHED)
    assert f'<meta property="article:published_time" content="{PUBLISHED}" />' in html
    assert f'<meta property="article:modified_time" content="{UPDATED}" />' in html
    assert f'<time datetime="{PUBLISHED}">28/05/2026</time> às 20h36' in html
    assert f'<time datetime="{UPDATED}">20/10/2026</time> às 13h00' in html
    assert_profiles_separated(html)
    assert f'<link rel="canonical" href="{URL}" />' in html
    assert html.count(ADSENSE_SCRIPT_MARKER) == 1
    # Quadro de 20/10/2026 (lote 2) acima do quadro da etapa de setembro.
    assert html.count("data-news-update-callout") - html.count("[data-news-update-callout]") == 2
    assert html.index(f'aria-labelledby="{UPDATE_20_10_ID}"') < html.index(f'aria-labelledby="{STAGE_UPDATE_ID}"')
    assert "<h2>Fontes oficiais</h2>" not in html
    assert "Página oficial do SNCR na Anvisa" not in html
    assert "https://www.gov.br/anvisa/" not in html

    news = next(block for block in _jsonld_blocks(html) if block.get("@type") == "NewsArticle")
    assert news["headline"] == TITLE
    assert news["datePublished"] == PUBLISHED
    assert news["dateModified"] == UPDATED
    assert news["url"] == URL

    assert "ATUALIZAÇÃO" in callout_text
    for term in (
        "Cronograma, perfis e nota da API",
        "notícia própria de 29/09/2026",
        "30/09/2026",
        "cronograma anunciado",
        "SNCR-Farmácia",
        "01/10/2026",
        "prescrição eletrônica continua facultativa",
        "não substitui a escrituração no SNGPC",
        "não é comprovação de operação integral",
    ):
        assert term in callout_text
    assert "href=" not in callout


def test_sncr_news_explains_the_stage_without_false_claims():
    html = NEWS_PATH.read_text(encoding="utf-8")
    body = _text(re.search(r'<section class="article-body">(.*?)</section>', html, re.DOTALL).group(1))

    for term in (
        "O SNCR já era utilizado",
        "30 de setembro de 2026",
        "Notificações de Receita",
        "Receitas de Controle Especial",
        "receitas sujeitas à retenção",
        "29/10/2026",
        "30/10/2026",
        "31/10/2026",
        "pergunta 30",
        "art. 18",
        "Gov.br",
        "Cadastro Anvisa",
        "análise cadastral do estabelecimento",
        "cartilha do SNCR para farmácias",
        "SNCR-Farmácia",
        "Nenhum dos dois pares é tratado aqui como prazo único confirmado",
        "não impõe a cada farmácia desenvolver API",
        "não perde a validade",
    ):
        assert term in body or term in html, term

    # O e-CNPJ só aparece no resumo da pergunta 51 das Perguntas e Respostas sobre a integração (quadro de 20/10/2026).
    assert html.count("e-CNPJ") == 1 and "e-CNPJ" in _callout(html, UPDATE_20_10_ID)

    for path in (NEWS_PATH, NEWS_INDEX_PATH, COMUNICADO_PATH, SERVICOS_PATH):
        text = _text(path.read_text(encoding="utf-8")).casefold()
        for claim in FORBIDDEN_CLAIMS:
            assert claim not in text, (path.relative_to(ROOT), claim)
    assert_source_pairs(html)
    assert_art18_relative(html)
    assert_private_public_and_api(html)
    assert_profiles_separated(html)
    assert_october_notices_scoped(html)


def test_sncr_card_is_unique_current_and_featured_in_the_news_listing():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    cards = _news_cards(html)
    sncr_cards = [card for card in cards if f'href="{ROUTE}"' in card]

    assert html.count(f'href="{ROUTE}"') == 1
    assert len(sncr_cards) == 1
    card = sncr_cards[0]
    # 13/10/2026, 09h06: o SNCR permanece na 2ª posição do HTML, empatado com a DCB. Produtos irregulares ficou à frente às 11h51.
    # 16/10/2026, 20h06: o card do CNES 10/2026 entra na 1ª posição da listagem; os demais descem uma.
    # 17/10/2026, 09h50: o card do esclarecimento do Farmácia Popular entra na 1ª posição da listagem; os demais descem uma.
    # 20/10/2026, 10h12: os cards do consolidado de produtos irregulares e do SISPA sobem para a 1ª e a 2ª posições; os que ficavam entre eles descem uma.
    # 21/10/2026, 17h45: a atualização de produtos irregulares devolve aquele card à 1ª posição; o SNCR fica em 2º.
    assert cards.index(card) == 1
    assert "news-card-compact" in card.split(">", 1)[0]
    assert f'data-updated="{UPDATED}"' in card
    assert f'<time datetime="{UPDATED}" class="leading-none">20/10/2026 • 13h00</time>' in card
    for term in (
        TITLE,
        "30/09/2026",
        "01/10",
        "gradual",
        "SNGPC",
    ):
        assert term in card
    assert "29/10" not in card and "31/10" not in card


def test_comunicado_keeps_one_sncr_card_and_seven_active_notices():
    html = COMUNICADO_PATH.read_text(encoding="utf-8")
    active = _active_notices(html)
    sncr_cards = [article for article in active if 'data-category="sncr"' in article]

    assert html.count('data-category="sncr"') == 1
    assert html.count(f'href="{ROUTE}"') == 1
    # 11/10/2026: o aviso do CNES 09/2026 passou ao histórico (6 ativos).
    # 16/10/2026, 20h06: aviso informativo do CNES 10/2026 (6 ativos, depois do encerramento do aviso PF).
    # 17/10/2026, 09h50: aviso informativo do Farmácia Popular sobre lembretes (7 ativos).
    # 19/10/2026, 15h40: aviso informativo sobre a instabilidade nos sistemas da Anvisa (8 ativos).
    # 20/10/2026: o aviso da instabilidade na Anvisa passou ao histórico (7 ativos).
    assert len(active) == 7
    assert re.findall(r'class="aviso-badge[^"]*">(\d+)</span>', html) == ["7", "7"]
    assert len(sncr_cards) == 1
    card_text = _text(sncr_cards[0])
    paragraphs = [_text(item) for item in re.findall(r"<p>(.*?)</p>", sncr_cards[0], re.DOTALL)]
    limit = next(item for item in paragraphs if "limite de numeração" in item)
    incorrect = next(item for item in paragraphs if "numerações disponibilizadas incorretamente" in item)
    for term in (
        "SNCR: cronograma anunciado e nota da API",
        "30/09/2026",
        "01/10/2026",
        "implementação gradual",
        "não comprova operação uniforme",
        "não impõe a cada farmácia desenvolver API",
        "Leia a atualização sobre o SNCR",
    ):
        assert term in card_text
    for term in (
        "algumas Unidades da Federação",
        "Até 29/10/2026",
        "Receitas de Controle Especial",
        "receitas sujeitas à retenção",
        "observados os demais requisitos aplicáveis",
        "Esse informe não é retificação geral",
    ):
        assert term in limit
    for term in (
        "prescritor diferente do solicitante",
        "CRM de outra Unidade da Federação",
        "09/10/2026",
        "serão canceladas",
        "Vigilância Sanitária competente",
        "numeração regular",
    ):
        assert term in incorrect
    for term in (
        "Receitas de Controle Especial",
        "receitas sujeitas à retenção",
        "29/10",
        "outros receituários",
        "retificação geral",
        "Notificações de Receita",
    ):
        assert term not in incorrect
    assert "não se estendem a outros receituários" not in card_text
    assert "não se estendem a outros receituários" not in _text(NEWS_PATH.read_text(encoding="utf-8"))
    assert "31/10" not in card_text
    assert "em operação desde" not in card_text
    assert "como preparar o estabelecimento" not in card_text
    # 16/10/2026, 20h06: o aviso do CNES 10/2026 é o 1º ativo; o do SNCR passa ao 2º.
    # 17/10/2026, 09h50: o aviso do Farmácia Popular sobre lembretes é o 1º ativo; o do CNES, o 2º; o do SNCR passa ao 3º.
    # 19/10/2026, 15h40: o aviso da instabilidade nos sistemas da Anvisa é o 1º ativo; o do SNCR passa ao 4º.
    # 20/10/2026: o aviso da instabilidade passa ao histórico; o do SNCR volta ao 3º.
    assert active[2] is sncr_cards[0]


def test_sncr_news_has_current_sitemap_lastmod():
    sitemap = SITEMAP_PATH.read_text(encoding="utf-8")

    assert sitemap.count(f"<loc>{URL}</loc>") == 1
    assert f"<loc>{URL}</loc>\n    <lastmod>2026-10-20</lastmod>" in sitemap
    assert (
        "<loc>https://www.regularizeconsultorias.com.br/servicos/</loc>\n"
        "    <lastmod>2026-10-09</lastmod>"
    ) in sitemap


def test_sncr_news_cta_and_floating_whatsapp_use_the_service_message():
    html = NEWS_PATH.read_text(encoding="utf-8")
    assert "Solicitar análise para o SNCR" in html
    assert 'href="/servicos/#servico-sncr"' in html

    floating = re.search(
        r'<a href="(/whatsapp/\?text=[^"]+)"[^>]*class="[^"]*floating-btn--whatsapp',
        html,
    )
    assert floating is not None
    query = parse_qs(urlsplit(floating.group(1)).query)
    assert unquote(query["text"][0]) == WHATSAPP_NEWS_TEXT

    cta = re.search(
        r'article-final-cta__link--primary" href="(/whatsapp/\?text=[^"]+)"',
        html,
    )
    assert cta is not None
    cta_query = parse_qs(urlsplit(cta.group(1)).query)
    assert unquote(cta_query["text"][0]) == WHATSAPP_NEWS_TEXT


def test_servicos_sncr_card_describes_the_access_service():
    html = SERVICOS_PATH.read_text(encoding="utf-8")
    start = html.index('id="servico-sncr"')
    card = html[start:html.index("</article>", start)]
    text = _text(card)

    assert "Implantação e habilitação de acesso ao SNCR" in text
    for term in (
        "análise cadastral",
        "Cadastro Anvisa",
        "usuários e perfis",
        "não concede acesso",
    ):
        assert term.casefold() in text.casefold()

    assert "Solicitar análise para o SNCR" not in card
    assert "/whatsapp/" not in card
    assert WHATSAPP_SERVICO_TEXT not in unquote(card)
    assert "e-CNPJ" not in card
    assert "Implanta\\u00e7\\u00e3o e habilita\\u00e7\\u00e3o de acesso ao SNCR" in html


def test_sncr_news_stays_informative_without_tutorial_or_universal_deadline():
    html = NEWS_PATH.read_text(encoding="utf-8")
    body_html = re.search(r'<section class="article-body">(.*?)</section>', html, re.DOTALL).group(1)
    body = _text(body_html)

    # Corpo editorial sem links nem encaminhamento para fontes, manuais, sistemas ou modelos.
    assert "href=" not in body_html
    for term in (
        "Nenhum dos dois pares é tratado aqui como prazo único confirmado",
        "não perde a validade",
        "disponibilização do registro de utilização",
        "não impõe a cada farmácia desenvolver API",
        "escopo e orçamento próprios",
        "avaliada individualmente",
    ):
        assert term in body
    for term in (
        "passo a passo",
        "faça login",
        "inclua colaboradores",
        "atribua permissões",
        ".pdf",
        "https://www.gov.br",
        "o papel acabou",
        "o sngpc foi substituído",
        "o cnes foi dispensado para qualquer finalidade",
        "em operação desde 30/09",
    ):
        assert term.casefold() not in body.casefold()

    news_index = _text(NEWS_INDEX_PATH.read_text(encoding="utf-8"))
    comunicado = _text(COMUNICADO_PATH.read_text(encoding="utf-8"))
    assert "gradual" in news_index
    assert "implementação gradual" in comunicado
    assert "como preparar o estabelecimento" not in comunicado
    assert_concrete_errors_rejected(html)


def _article_body(html):
    match = re.search(r'<section class="article-body">(.*?)</section>', html, re.DOTALL)
    if match is None:
        raise AssertionError("corpo-editorial: secao ausente")
    return match.group(1)


def _plain(fragment):
    return " ".join(re.sub(r"<[^>]+>", " ", fragment).split())


def _paragraphs(body_html):
    return re.findall(r"<p\b[^>]*>.*?</p>", body_html, re.DOTALL)


def _one_paragraph(body_html, needle):
    found = [paragraph for paragraph in _paragraphs(body_html) if needle in _plain(paragraph)]
    if len(found) != 1:
        raise AssertionError(f"paragrafo-unico: {needle} -> {len(found)}")
    return _plain(found[0])


def assert_profiles_separated(html):
    body = _article_body(html)
    intro = _one_paragraph(body, "permanecer separadas")
    required = (
        "Quatro comunicações",
        "nota da nova etapa",
        "preparação no Cadastro Anvisa",
        "notícia própria de 29 de setembro de 2026",
        "disponibilidade dos perfis de acesso",
        "nota da API",
    )
    missing = [item for item in required if item not in intro]
    if missing or "Três comunicações" in intro or "não foi localizada" in intro or "não é uma nota separada" in intro:
        raise AssertionError("comunicacoes-distintas: " + ",".join(missing))
    callout = _one_paragraph(body, "notícia própria de 29/09/2026")
    if "SNCR-Farmácia" not in callout or "distinta da preparação e da nota da API" not in callout:
        raise AssertionError("perfis-distintos-da-preparacao: " + callout)


def assert_source_pairs(html):
    body = _article_body(html)
    cartilha = _one_paragraph(body, "cartilha do SNCR para farmácias")
    faq = _one_paragraph(body, "pergunta 30")
    caveat = _one_paragraph(body, "Nenhum dos dois pares")
    if "até 29/10/2026" not in cartilha or "a partir de 30/10/2026" not in cartilha or "31/10/2026" in cartilha:
        raise AssertionError("pares-cartilha: " + cartilha)
    if "de 30/09/2026 a 30/10/2026" not in faq or "a partir de 31/10/2026" not in faq or "29/10/2026" in faq:
        raise AssertionError("pares-faq: " + faq)
    if "prazo único confirmado" not in caveat:
        raise AssertionError("pares-ressalva: " + caveat)


def assert_october_notices_scoped(html):
    body = _article_body(html)
    plain = _plain(body)
    intro = _one_paragraph(body, "publicou dois informes")
    limit = _one_paragraph(body, "O informe sobre o limite de numeração registra")
    transition = _one_paragraph(body, "No mesmo informe")
    incorrect = _one_paragraph(body, "numerações vinculadas a prescritores diferentes")
    if "O informe sobre o limite de numeração trata de Receitas de Controle Especial e de receitas sujeitas à retenção" not in intro:
        raise AssertionError("informe-limite-rce-ret: " + intro)
    second = intro.split("O outro informe", 1)[-1]
    if "O outro informe" not in intro or "Receitas de Controle Especial" in second or "retenção" in second:
        raise AssertionError("informe-incorreto-sem-rce-ret: " + second)
    if "Receitas de Controle Especial" not in limit or "receitas sujeitas à retenção" not in limit:
        raise AssertionError("informe-limite-rce-ret: " + limit)
    if "até 29 de outubro de 2026" not in transition or "dois receituários eletrônicos" not in transition:
        raise AssertionError("informe-limite-transicao: " + transition)
    for forbidden in (
        "não se estendem a outros receituários",
        "outros receituários",
        "Receitas de Controle Especial",
        "receitas sujeitas à retenção",
        "29 de outubro",
        "29/10",
        "retificação geral",
        "Notificações de Receita",
    ):
        if forbidden in incorrect:
            raise AssertionError("informe-incorreto-alcance: " + forbidden)
    for required in (
        "serviços de prescrição integrados",
        "prescritores diferentes",
        "CRM de outra Unidade da Federação",
        "09/10/2026",
        "serão canceladas",
        "Vigilância Sanitária competente",
        "numeração regular",
    ):
        if required not in incorrect:
            raise AssertionError("informe-incorreto-alcance: ausencia " + required)
    for phrase in (
        "não se estendem a outros receituários",
        "nem se estendem a Notificações de Receita",
        "não se estendem a Notificações de Receita",
    ):
        if phrase in plain:
            raise AssertionError("exclusao-generica: " + phrase)


def assert_art18_relative(html):
    text = _one_paragraph(_article_body(html), "art. 18")
    if "após o início da disponibilização do registro de utilização" not in text or re.search(r"\d{2}/10/2026", text):
        raise AssertionError("art18-marco-relativo: " + text)


def assert_private_public_and_api(html):
    body = _article_body(html)
    ident = _one_paragraph(body, "pergunta 58")
    if "farmácia privada pela AFE" not in ident or "identificados a partir do CNES" not in ident:
        raise AssertionError("afe-cnes-publico: " + ident)
    if "privada pelo CNES" in ident or "identificados a partir da AFE" in ident:
        raise AssertionError("afe-cnes-publico: " + ident)
    if "não impõe a cada farmácia desenvolver API" not in _plain(body):
        raise AssertionError("api-natureza: ausencia da delimitacao")


def assert_concrete_errors_rejected(html):
    body = _article_body(html)
    plain = _plain(body)
    folded_body = plain.casefold()
    if "href=" in body or any(marker in folded_body for marker in ("https://", "http://", "mailto:")):
        raise AssertionError("url-no-corpo")
    for term in (
        "passo a passo",
        "faça login",
        "inclua colaboradores",
        "atribua permissões",
        ".pdf",
    ):
        if term.casefold() in folded_body:
            raise AssertionError("procedimento: " + term)
    for claim in FORBIDDEN_CLAIMS:
        if claim in folded_body:
            raise AssertionError("alegacao-proibida: " + claim)
    for sentence in (part.strip() for part in re.split(r"(?<=[.!?])\s+", plain) if part.strip()):
        folded = sentence.casefold()
        if "api" in folded and re.search(r"obrigad|deve desenvolver api|devem desenvolver api", folded) and not re.search(r"\bn[aã]o\b", folded):
            raise AssertionError("api-obrigacao-universal: " + sentence)
        if re.search(r"papel", folded) and re.search(r"deix\w+ de ser admitid|papel acabou", folded):
            raise AssertionError("papel-admitido: " + sentence)
        if (
            re.search(
                r"funcionar[aã]o|passam a funcionar|entram em opera|est[aáã]o? em opera|em opera[cç][aã]o desde",
                folded,
            )
            and re.search(r"30/09(?:/2026)?|30 de setembro", folded)
        ):
            raise AssertionError("funcionalidades-data-operacao: " + sentence)
        if re.search(r"único prazo|prazo definitivo|prazo único confirmado é", folded):
            raise AssertionError("prazo-unico: " + sentence)
        if "o sngpc foi substituído" in folded or "o cnes foi dispensado para qualquer finalidade" in folded:
            raise AssertionError("corpo-proibido: " + sentence)


ARTICLE_GUARDS = (
    assert_profiles_separated,
    assert_source_pairs,
    assert_october_notices_scoped,
    assert_art18_relative,
    assert_private_public_and_api,
    assert_concrete_errors_rejected,
)


def rejecting_guards(html):
    found = []
    for guard in ARTICLE_GUARDS:
        try:
            guard(html)
        except AssertionError as exc:
            found.append(str(exc).split(":", 1)[0])
    return found


def _insert_paragraph(html, sentence):
    return html.replace("</section>", f"<p>{sentence}</p></section>", 1)


def _swap_october_pairs(html):
    body = _article_body(html)
    cartilha = next(paragraph for paragraph in _paragraphs(body) if "cartilha do SNCR para farmácias" in _plain(paragraph))
    faq = next(paragraph for paragraph in _paragraphs(body) if "pergunta 30" in _plain(paragraph))
    new_cartilha = cartilha.replace("29/10/2026", "30/10/2026").replace("a partir de 30/10/2026", "a partir de 31/10/2026")
    new_faq = faq.replace("a 30/10/2026", "a 29/10/2026").replace("a partir de 31/10/2026", "a partir de 30/10/2026")
    return html.replace(cartilha, new_cartilha, 1).replace(faq, new_faq, 1)


def _invert_afe_cnes(html):
    return html.replace(
        "identificam a farmácia privada pela AFE ativa",
        "identificam a farmácia privada pelo CNES ativo",
        1,
    ).replace(
        "são identificados a partir do CNES",
        "são identificados a partir da AFE",
        1,
    )


def _shift_art18(html):
    return html.replace(
        "após o início da disponibilização do registro de utilização",
        "após 29/10/2026",
        1,
    )


MUTATION_CASES = (
    ("api-obrigacao-universal", lambda html: _insert_paragraph(html, "Todas as farmácias são obrigadas a implementar uma API própria para acessar o SNCR.")),
    ("papel-admitido", lambda html: _insert_paragraph(html, "As receitas em papel deixaram de ser admitidas no SNCR a partir de 30 de setembro.")),
    ("funcionalidades-data-operacao", lambda html: _insert_paragraph(html, "As novas funcionalidades funcionarão a partir de 30/09/2026.")),
    ("prazo-unico", lambda html: _insert_paragraph(html, "O único prazo definitivo de emissão sem número é 29/10/2026.")),
    ("pares-cartilha", _swap_october_pairs),
    ("url-no-corpo", lambda html: _insert_paragraph(html, "Consulta governamental: https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/.")),
    ("url-no-corpo", lambda html: _insert_paragraph(html, "Consulta externa: https://exemplo.org/nota-sncr.")),
    ("url-no-corpo", lambda html: _insert_paragraph(html, 'Veja o <a href="https://www.gov.br/anvisa/pt-br/assuntos/medicamentos/controlados/sncr">SNCR</a>.')),
    ("afe-cnes-publico", _invert_afe_cnes),
    ("art18-marco-relativo", _shift_art18),
    ("procedimento", lambda html: _insert_paragraph(html, "Faça login no Cadastro Anvisa, inclua colaboradores e atribua permissões antes de dispensar.")),
    ("alegacao-proibida", lambda html: _insert_paragraph(html, "Em 30 de setembro de 2026, o SNCR começa em 30 dias como situação atual.")),
    ("api-obrigacao-universal", lambda html: _insert_paragraph(html, "Toda farmácia deve desenvolver API para continuar vendendo.")),
    ("prazo-unico", lambda html: _insert_paragraph(html, "O prazo único confirmado é 30/10/2026.")),
    ("papel-admitido", lambda html: _insert_paragraph(html, "O papel acabou para todas as receitas.")),
    ("corpo-proibido", lambda html: _insert_paragraph(html, "O SNGPC foi substituído pelo SNCR.")),
    ("corpo-proibido", lambda html: _insert_paragraph(html, "O CNES foi dispensado para qualquer finalidade.")),
    ("funcionalidades-data-operacao", lambda html: _insert_paragraph(html, "A nova etapa está em operação desde 30/09.")),
)


def test_sncr_article_rejects_material_regressions_on_a_temporary_copy(tmp_path):
    source = NEWS_PATH.read_text(encoding="utf-8")
    assert rejecting_guards(source) == []
    for guard_id, mutate in MUTATION_CASES:
        mutated = mutate(source)
        found = rejecting_guards(mutated)
        assert guard_id in found, (guard_id, found)
        copy = tmp_path / f"{guard_id}-{len(found)}.html"
        copy.write_text(mutated, encoding="utf-8")
        assert rejecting_guards(copy.read_text(encoding="utf-8")) == found


def _update_20_10(html):
    return _callout(html, UPDATE_20_10_ID)


def test_sncr_update_of_20_october_follows_the_official_notices_and_the_integration_qa():
    html = NEWS_PATH.read_text(encoding="utf-8")
    callout = _update_20_10(html)
    text = _text(callout)
    paragraphs = [_plain(item) for item in re.findall(r"<p\b[^>]*>.*?</p>", callout, re.DOTALL)]
    items = [_plain(item) for item in re.findall(r"<li>(.*?)</li>", callout, re.DOTALL)]

    assert "ATUALIZAÇÃO" in text
    assert f'<h2 id="{UPDATE_20_10_ID}" class="article-spacing-flush-top">Atualização em 20/10/2026</h2>' in callout
    # Informe de 15/10/2026: correção do erro de solicitação de RCE e RET, distinta do limite de numeração.
    fixed = next(item for item in paragraphs if "15/10/2026" in item)
    for term in (
        "correção",
        "erro que impedia a solicitação de numerações",
        "Receitas de Controle Especial",
        "receitas sujeitas à retenção",
        "prescritores já cadastrados no SNCR",
        "funcionalidade está regularizada",
        "não trata do limite de numeração",
    ):
        assert term in fixed, term
    # Perguntas e Respostas sobre a integração, 1ª edição, de 16/10/2026: perguntas 49, 50, 51 e 53, nessa ordem.
    assert any("16/10/2026" in item and "1ª edição" in item for item in paragraphs)
    assert [re.search(r"\(pergunta (\d+)\)", item).group(1) for item in items] == ["49", "50", "51", "53"]
    p49, p50, p51, p53 = items
    for term in ("exclusivamente pelo farmacêutico", "portal web do SNCR", "Cadastro Anvisa"):
        assert term in p49, term
    # P50: só o que o texto diz; a data descreve o conjunto de funcionalidades, não um prazo para a integração.
    for term in (
        "a resposta é “Não”",
        "No conjunto de funcionalidades previstas até 30 de setembro de 2026",
        "não há previsão de endpoint para integração com sistemas de ponto de venda (PDV) ou ERPs de farmácias",
    ):
        assert term in p50, term
    for term in (
        "não é obrigatório para acesso e operação no SNCR",
        "requisitos de acesso futuro",
        "e-CNPJ",
        "AFE válida emitida pela Anvisa",
        "estabelecimento regularizado",
        "conta Gov.br dos gestores ou responsáveis",
        "farmácias e dispensários públicos",
    ):
        assert term in p51, term
    for term in ("receituário físico convencional em papel", "continua válido", "offline", "sincronização posterior"):
        assert term in p53, term
    # Limite de numeração de 09/10/2026: sem solução anunciada, transição até 29/10/2026 e a divergência de 30/10/2026.
    limit = next(item for item in paragraphs if "limite de numeração" in item and "09/10/2026" in item and "15/10" not in item)
    for term in (
        "segue sem solução anunciada",
        "algumas Unidades da Federação",
        "até 29/10/2026",
        "2ª edição das Perguntas e Respostas sobre a RDC nº 1.000/2025",
        "30/10/2026",
        "continua registrada abaixo",
    ):
        assert term in limit, term
    assert re.findall(r"\d{2}/\d{2}/\d{4}", limit) == ["09/10/2026", "29/10/2026", "30/10/2026"]
    folded = text.casefold()
    for claim in (
        "foi resolvido",
        "foi resolvida",
        "foi solucionado",
        "foi solucionada",
        "ampliação foi concluída",
        "ampliação concluída",
        "novo prazo",
        "prorroga",
        "sem api pdv/erp até",
        "até 30/09/2026, não haverá",
    ):
        assert claim not in folded, claim
    # Sem link (regra de 20/10/2026): o documento é citado pelo nome e pela data, e o parágrafo do limite fecha o quadro.
    assert "<a " not in callout and "href=" not in callout and "http" not in callout
    assert any(
        "Em 16/10/2026, a Anvisa publicou a 1ª edição das Perguntas e Respostas sobre a integração dos sistemas de "
        "prescrição eletrônica ao SNCR" in item for item in paragraphs
    )
    last = re.findall(r"<p\b[^>]*>", callout)[-1]
    assert last == '<p class="article-spacing-flush-bottom">' and paragraphs[-1] == limit


def test_sncr_pages_leave_out_the_items_held_for_another_update():
    for path in (NEWS_PATH, POP_PATH, NEWS_INDEX_PATH, COMUNICADO_PATH):
        html = path.read_text(encoding="utf-8")
        visible = _text(html)
        for term in HELD_BACK_TERMS:
            assert term not in html and term not in visible, (path.relative_to(ROOT), term)
    # Nada de notícia nova nem de card novo no comunicado. O contador, em 8 no lote 2, voltou a 7 em 20/10/2026 com o
    # encerramento do aviso da instabilidade na Anvisa.
    comunicado = COMUNICADO_PATH.read_text(encoding="utf-8")
    assert re.findall(r'class="aviso-badge[^"]*">(\d+)</span>', comunicado) == ["7", "7"]
    assert re.findall(r'class="aviso-badge[^"]*">(\d+)</span>', NEWS_PATH.read_text(encoding="utf-8")) == ["7", "7"]
    assert len(list((ROOT / "noticias").glob("*/index.html"))) == 85
