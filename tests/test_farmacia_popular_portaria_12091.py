import json
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).parents[1]
SLUG = "farmacia-popular-portaria-12091-2026-novas-regras"
ARTICLE_PATH = ROOT / "noticias" / SLUG / "index.html"
ARTICLE_URL = f"https://www.regularizeconsultorias.com.br/noticias/{SLUG}/"
OG_IMAGE_URL = f"https://www.regularizeconsultorias.com.br/assets/img/og/noticias/{SLUG}.webp"
OG_IMAGE_PATH = ROOT / "assets" / "img" / "og" / "noticias" / f"{SLUG}.webp"
PUBLISHED_AT = "2026-08-12T09:59:00-03:00"
NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
FARMACIA_POPULAR_PATH = ROOT / "farmacia-popular" / "index.html"


class MetadataParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.canonicals = []
        self.h1 = []
        self.links = []
        self.scripts = []
        self._in_h1 = False
        self._h1_text = []
        self._in_jsonld = False
        self._script_text = []

    def handle_starttag(self, tag, attrs):
        attributes = dict(attrs)
        if tag == "link" and "canonical" in attributes.get("rel", "").split():
            self.canonicals.append(attributes.get("href"))
        if tag == "a":
            self.links.append(attributes.get("href", ""))
        if tag == "h1":
            self._in_h1 = True
            self._h1_text = []
        if tag == "script" and attributes.get("type") == "application/ld+json":
            self._in_jsonld = True
            self._script_text = []

    def handle_data(self, data):
        if self._in_h1:
            self._h1_text.append(data)
        if self._in_jsonld:
            self._script_text.append(data)

    def handle_endtag(self, tag):
        if tag == "h1" and self._in_h1:
            self.h1.append("".join(self._h1_text).strip())
            self._in_h1 = False
        if tag == "script" and self._in_jsonld:
            self.scripts.append("".join(self._script_text))
            self._in_jsonld = False


def parse_article():
    parser = MetadataParser()
    parser.feed(ARTICLE_PATH.read_text(encoding="utf-8"))
    return parser


def jsonld_objects(parser):
    return [json.loads(script) for script in parser.scripts]


def news_card_for_slug(html, slug):
    match = re.search(
        rf'<article\b[^>]*data-news-card[^>]*>.*?href="/noticias/{re.escape(slug)}/".*?</article>',
        html,
        flags=re.DOTALL,
    )
    assert match
    return match.group(0)


def test_portaria_article_has_expected_slug_h1_and_canonical():
    assert ARTICLE_PATH.is_file()
    parser = parse_article()
    assert parser.h1 == ["Farmácia Popular tem novas regras com a Portaria GM/MS nº 12.091/2026"]
    assert parser.canonicals == [ARTICLE_URL]


def test_portaria_article_has_expected_newsarticle_metadata():
    parser = parse_article()
    news_article = next(item for item in jsonld_objects(parser) if item.get("@type") == "NewsArticle")

    assert news_article["headline"] == "Farmácia Popular tem novas regras com a Portaria GM/MS nº 12.091/2026"
    assert news_article["url"] == ARTICLE_URL
    assert news_article["datePublished"] == PUBLISHED_AT
    assert news_article["dateModified"] == PUBLISHED_AT
    assert news_article["articleSection"] == "Farmácia Popular"
    assert news_article["author"] == {"@type": "Person", "name": "Júnior Costa"}
    assert news_article["publisher"]["name"] == "Regularize Consultoria"
    assert news_article["mainEntityOfPage"]["@id"] == ARTICLE_URL


def test_portaria_article_uses_specific_og_image():
    html = ARTICLE_PATH.read_text(encoding="utf-8")
    news_article = next(item for item in jsonld_objects(parse_article()) if item.get("@type") == "NewsArticle")

    assert OG_IMAGE_PATH.is_file()
    assert html.count(f'property="og:image" content="{OG_IMAGE_URL}"') == 1
    assert html.count(f'property="og:image:secure_url" content="{OG_IMAGE_URL}"') == 1
    assert html.count(f'name="twitter:image" content="{OG_IMAGE_URL}"') == 1
    assert news_article["image"] == OG_IMAGE_URL
    assert "assets/img/og/noticias.jpg" not in html


def test_portaria_article_preserves_editorial_safeguards_and_internal_flow():
    html = ARTICLE_PATH.read_text(encoding="utf-8")
    parser = parse_article()
    lowered = html.casefold()

    assert "Órgão regulador:</span><span" in html
    assert "Ministério da Saúde</span>" in html
    assert 'href="/farmacia-popular/"' in html
    assert re.search(
        r'<a\b[^>]*href="/farmacia-popular/"[^>]*>Consultar municípios com vagas</a>',
        html,
    )
    assert "não a implantação imediata desses serviços" in lowered
    assert "podem ser aplicadas isolada ou cumulativamente" in lowered
    assert "não representa promessa de credenciamento, renovação, aprovação, desbloqueio ou permanência" in lowered
    assert "renovação anual" in lowered
    assert "orientações então vigentes" in lowered
    assert "2027" not in lowered
    assert "2028" not in lowered
    assert "aprovação garantida" not in lowered
    assert "credenciamento garantido" not in lowered
    for public_path in (ARTICLE_PATH, NEWS_INDEX_PATH, FARMACIA_POPULAR_PATH):
        public_html = public_path.read_text(encoding="utf-8").casefold()
        assert "127.0.0.1" not in public_html
        assert "localhost" not in public_html

    government_hosts = ("gov.br", "in.gov.br", "saude.gov.br", "anvisa.gov.br", "caixa.gov.br")
    external_government_links = [
        href
        for href in parser.links
        if urlsplit(href).hostname and any(host in urlsplit(href).hostname for host in government_hosts)
    ]
    assert not external_government_links


def test_portaria_article_and_listing_use_urgent_badge_without_changing_category():
    article_html = ARTICLE_PATH.read_text(encoding="utf-8")
    index_html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    new_card = news_card_for_slug(index_html, SLUG)
    previous_urgent_card = news_card_for_slug(
        index_html, "farmacia-popular-suspensao-temporaria-recadastramento-sifap"
    )
    previous_update_card = news_card_for_slug(
        index_html, "credenciamento-farmacia-popular-municipios-com-vagas"
    )

    assert ">URGENTE</span>" in article_html
    assert "bg-red-600" in article_html
    assert ">URGENTE</span>" in new_card
    assert "news-urgent-card" in new_card
    assert "bg-red-600" in new_card
    assert ">FARMÁCIA POPULAR</span>" in article_html
    assert 'data-category="farmacia-popular"' in new_card
    assert ">FARMÁCIA POPULAR</span>" in new_card
    assert ">URGENTE</span>" in previous_urgent_card
    assert ">Atualização</span>" in previous_update_card
    assert "news-amber-card" in previous_update_card


def test_portaria_article_explains_document_retention_change_and_caution():
    lowered = ARTICLE_PATH.read_text(encoding="utf-8").casefold()

    assert "regra anterior" in lowered
    assert "10 anos" in lowered
    assert "5 anos" in lowered
    assert "redução de 10 para 5 anos é uma mudança real" in lowered
    assert "prioriza a guarda em meio digital ou eletrônico" in lowered
    assert "integridade, autenticidade, disponibilidade e rastreabilidade" in lowered
    assert "até sua conclusão" in lowered
    assert "não deve ser interpretada como autorização automática para eliminar documentos" in lowered
    for prazo in ("legais", "fiscais", "sanitários", "contábeis", "administrativos"):
        assert prazo in lowered


def test_portaria_article_distinguishes_current_renewal_and_prescription_rules():
    lowered = ARTICLE_PATH.read_text(encoding="utf-8").casefold()

    assert "deverá ser renovada a cada" in lowered
    assert "2 anos" in lowered
    assert "renovação de 2025" in lowered
    assert "renovação anual" in lowered
    assert "a nova portaria passa a estabelecer a renovação da participação a cada 2 anos" in lowered
    assert "não significa renovação automática" in lowered
    assert "convocação deverá estabelecer prazo, procedimento e condições" in lowered
    assert "validade das prescrições permanece em 180 e 365 dias" in lowered
    assert "mantém a regra geral já conhecida" in lowered
    assert "esses prazos não foram criados ou alterados" in lowered


def test_portaria_article_details_fines_without_alarmism():
    lowered = ARTICLE_PATH.read_text(encoding="utf-8").casefold()

    for classification, percentage in (
        ("leve", "até 2%"),
        ("média", "até 5%"),
        ("grave", "até 10%"),
        ("gravíssima", "até 20%"),
    ):
        assert f"{classification}: <strong>{percentage}</strong>" in lowered
    assert "3 últimos meses completos das autorizações consolidadas" in lowered
    assert "valor da irregularidade individualizada" in lowered
    assert "prejuízo causado ou potencialmente causado ao erário" in lowered
    assert "vendas realizadas no pfpb nos 12 meses anteriores à decisão" in lowered
    assert "percentual e a base de cálculo dependem" in lowered
    assert "20% do faturamento anual" not in lowered
    assert "prazo de <strong>15 dias</strong>" in lowered
    assert "comprovante de pagamento" in lowered
    assert "contraditório e ampla defesa" in lowered


def test_portaria_article_distinguishes_preventive_suspension_and_penalty():
    lowered = ARTICLE_PATH.read_text(encoding="utf-8").casefold()

    assert "suspensão cautelar ou preventiva" in lowered
    assert "não possui natureza sancionatória" in lowered
    assert "não significa, por si só, que uma penalidade definitiva já foi aplicada" in lowered
    assert "bloqueio temporário" in lowered
    assert "é uma sanção" in lowered
    assert "3 a 6 meses" in lowered


def test_portaria_article_individualizes_headquarters_and_branches():
    lowered = ARTICLE_PATH.read_text(encoding="utf-8").casefold()

    assert "unidade autônoma" in lowered
    assert "endereço e cnpj" in lowered
    assert "não implica automaticamente" in lowered
    assert "participação ou conhecimento da pessoa jurídica" in lowered
    assert "benefício para ela" in lowered
    assert "conluio fraudulento" in lowered
    assert "não representa imunidade" in lowered


def test_portaria_article_covers_other_operational_points_without_generalizing():
    lowered = ARTICLE_PATH.read_text(encoding="utf-8").casefold()

    assert "6 meses consecutivos após o início das atividades" in lowered
    assert "situações excepcionais devidamente justificadas e comprovadas" in lowered
    assert "não se trata de exclusão automática aos 6 meses" in lowered
    assert "situação cadastral perante a receita federal esteja “baixada”" in lowered
    assert "automaticamente cancelada no pfpb" in lowered
    assert "reanálise em até 60 dias contados da ordem bancária" in lowered
    assert "cancelamento a pedido" in lowered
    assert "<strong>não renovação:</strong> pode resultar no cancelamento" in lowered
    assert "cancelamento por irregularidades" in lowered
    assert "após <strong>6 meses</strong>" in lowered
    assert "após <strong>2 anos</strong>" in lowered


def test_portaria_article_explains_cancellation_effects_and_visible_faq():
    html = ARTICLE_PATH.read_text(encoding="utf-8")
    lowered = html.casefold()

    assert "cancelamento e possibilidade de nova participação" in lowered
    assert "não é recredenciamento automático" in lowered
    assert "<strong>não renovação:</strong> pode resultar no cancelamento" in lowered
    assert "nova solicitação somente após <strong>6 meses</strong>" in lowered
    assert "cancelamento a pedido" in lowered
    assert "o pedido não elimina eventual responsabilização" in lowered
    assert "o cancelamento da participação não extingue imediatamente" in lowered
    assert "podem ser aplicadas isolada ou cumulativamente" in lowered
    assert "dúvidas frequentes sobre as novas regras do farmácia popular" in lowered
    faq_match = re.search(
        r'<section class="article-faq"[^>]*>(.*?)</section>', html, flags=re.DOTALL
    )
    assert faq_match
    faq_html = faq_match.group(1)
    questions = re.findall(r'<summary class="article-faq__question">(.*?)</summary>', faq_html)
    assert len(questions) == 12
    assert faq_html.count("<details") == 12
    assert faq_html.count("<summary") == 12
    assert not re.search(r"<details\b[^>]*\bopen\b", faq_html)
    assert "name=" not in faq_html
    assert all("article-faq__answer" in item for item in re.findall(r"<details\b.*?</details>", faq_html, re.DOTALL))
    assert "onclick=" not in faq_html.casefold()
    communications_match = re.search(
        rf'{re.escape("Como a farmácia deve acompanhar as comunicações do Programa?")}</summary>\s*<div class="article-faq__answer"><p>(.*?)</p>',
        faq_html,
        flags=re.DOTALL,
    )
    assert communications_match
    communications_answer = communications_match.group(1).casefold()
    for expected_text in (
        "e-mail cadastrado atualizado",
        "canal oficial de comunicação",
        "ofício assinado via sei",
        "@saude.gov.br",
        "não realiza contato telefônico",
    ):
        assert expected_text in communications_answer
    assert "contato telefônico oficial" not in communications_answer
    assert questions == [
        "Minha farmácia já participa do Farmácia Popular. Precisa fazer alguma coisa imediatamente por causa da nova Portaria?",
        "A renovação agora acontece automaticamente a cada 2 anos?",
        "Quais alterações da farmácia precisam ser comunicadas e quais são os prazos?",
        "Como a farmácia deve acompanhar as comunicações do Programa?",
        "Estar em um município com vaga garante o credenciamento no Farmácia Popular?",
        "Se a participação for cancelada por irregularidades, quando a farmácia poderá participar novamente?",
        "Se a saída ocorrer a pedido da farmácia ou por falta de renovação, quando poderá solicitar nova participação?",
        "Depois do cancelamento ainda é necessário guardar documentos?",
        "O cancelamento de uma filial afeta automaticamente a matriz ou as outras lojas?",
        "As penalidades podem ser aplicadas juntas?",
        "A multa é sempre de 20%? Como ela é calculada?",
        "Existe recurso contra a aplicação de penalidade?",
    ]
    for expected_text in (
        "não renova automaticamente",
        "15 dias",
        "30 dias",
        "a vaga é uma oportunidade relevante",
        "individualizada por estabelecimento, endereço e cnpj",
    ):
        assert expected_text in faq_html.casefold()
    for removed_question in (
        "Depois de 2 anos a farmácia volta automaticamente ao Programa?",
        "Se a própria farmácia pedir o cancelamento, quando poderá solicitar nova participação?",
        "Se o cancelamento ocorrer por falta de renovação, quando poderá solicitar nova participação?",
        "O que acontece se houver valor a ser ressarcido ao Programa?",
    ):
        assert removed_question not in faq_html
    assert "recurso administrativo em 10 dias" in lowered
    assert "<strong>ressarcimento:</strong> depende do procedimento e da decisão correspondentes" in lowered
    assert '"@type":"faqpage"' not in lowered
    assert '"@type": "faqpage"' not in lowered
    assert '"@type":"qapage"' not in lowered
    assert '"@type": "qapage"' not in lowered


def test_portaria_article_uses_digits_for_regulatory_quantities():
    lowered = ARTICLE_PATH.read_text(encoding="utf-8").casefold()

    for written_quantity in (
        "dois anos",
        "cinco anos",
        "seis meses",
        "três a seis meses",
        "três meses completos",
        "dez dias",
        "quinze dias",
        "trinta dias",
        "doze meses",
        "sessenta dias",
    ):
        assert written_quantity not in lowered


def test_news_index_has_exactly_one_new_article_and_consistent_counts():
    html = NEWS_INDEX_PATH.read_text(encoding="utf-8")
    article_directories = [
        path
        for path in (ROOT / "noticias").iterdir()
        if path.is_dir() and (path / "index.html").is_file()
    ]

    assert html.count("data-news-card") == 64
    assert html.count('data-category="farmacia-popular"') == 10
    assert len(article_directories) == 64
    assert news_card_for_slug(html, SLUG)
    assert "64 notícias encontradas" in html
    assert re.search(r'data-news-category="todos"[^>]*>.*?<span[^>]*>64</span>', html)
    assert re.search(r'data-news-category="farmacia-popular"[^>]*>.*?<span[^>]*>10</span>', html)
    assert f'<time datetime="{PUBLISHED_AT}"' in html


def test_news_index_itemlist_contains_new_article_in_first_position():
    parser = MetadataParser()
    parser.feed(NEWS_INDEX_PATH.read_text(encoding="utf-8"))
    collection = next(item for item in jsonld_objects(parser) if item.get("@type") == "CollectionPage")
    items = collection["mainEntity"]["itemListElement"]

    assert len(items) == 64
    assert [item["position"] for item in items] == list(range(1, 65))
    assert len({item["url"] for item in items}) == 64
    assert items[0]["url"] == ARTICLE_URL
