import json
from datetime import datetime

from support import ROOT, parse_html


NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
STATUS_LABELS = {"atualização", "informativo", "urgente", "orientação"}
STATUS_CONTRACTS = {
    # Atualização e Informativo: classes semânticas; as cores (fundo vivo, texto
    # escuro) ficam só em pages/noticias-tipos.css (05/10/2026), iguais no selo e
    # no botão dos dois formatos e no selo e no cabeçalho do artigo.
    "atualização": {
        "cta": "ler atualização",
        "card_classes": {"news-amber-badge"},
        "cta_classes": {"news-amber-button", "rounded-full"},
        "page_badge_classes": {"article-badge-atualizacao"},
        "hero_classes": {"article-hero-atualizacao"},
    },
    "informativo": {
        "cta": "ler notícia",
        "card_classes": {"news-orange-badge"},
        "cta_classes": {"news-orange-button", "rounded-full"},
        "page_badge_classes": {"article-badge-informativo"},
        "hero_classes": {"article-hero-informativo"},
    },
    "orientação": {
        "cta": "ler orientação",
        "card_classes": {"news-orientacao-badge"},
        "cta_classes": {"news-orientacao-button", "rounded-full"},
        "page_badge_classes": {"article-badge-orientacao"},
        "hero_classes": {"article-hero-orientacao"},
    },
    "urgente": {
        "cta": "ler notícia",
        "card_classes": {"news-urgent-badge"},
        "cta_classes": {"news-urgent-button", "rounded-full"},
        "page_badge_classes": {"article-badge-urgente"},
        "hero_classes": {"article-hero-urgente"},
    },
}


def descendants(node, tag=None):
    return [child for child in node.descendants() if tag is None or child.tag == tag]


def normalized_text(node):
    return " ".join(node.text_content().split()).casefold()


def status_badge(node):
    matches = [
        child
        for child in descendants(node, "span")
        if normalized_text(child) in STATUS_LABELS
    ]
    assert len(matches) == 1
    return matches[0]


def article_page_for(card):
    links = [
        link
        for link in descendants(card, "a")
        if link.attrs.get("href", "").startswith("/noticias/")
    ]
    assert links
    relative_url = links[-1].attrs["href"]
    return ROOT / relative_url.strip("/") / "index.html", links[-1]


def article_hero(page_root):
    headings = descendants(page_root, "h1")
    assert len(headings) == 1
    current = headings[0].parent
    while current and current.tag != "header":
        current = current.parent
    assert current is not None
    return current


def jsonld_objects(page_root):
    for script in descendants(page_root, "script"):
        if script.attrs.get("type", "").casefold() != "application/ld+json":
            continue
        yield json.loads("".join(script.text))


def test_card_cta_and_internal_hero_follow_the_status_contract():
    index_root = parse_html(NEWS_INDEX_PATH)
    cards = [card for card in descendants(index_root, "article") if "data-news-card" in card.attrs]
    checked_statuses = set()

    for card in cards:
        page_path, cta = article_page_for(card)
        card_badge = status_badge(card)
        status = normalized_text(card_badge)
        contract = STATUS_CONTRACTS[status]
        checked_statuses.add(status)
        page_root = parse_html(page_path)
        hero = article_hero(page_root)
        page_badge = status_badge(hero)
        relative_path = page_path.relative_to(ROOT)

        assert normalized_text(cta) == contract["cta"], relative_path
        assert normalized_text(page_badge) == status, relative_path
        assert contract.get("card_classes", set()) <= set(card_badge.attrs.get("class", "").split()), relative_path
        assert contract.get("cta_classes", set()) <= set(cta.attrs.get("class", "").split()), relative_path
        assert contract["page_badge_classes"] <= set(page_badge.attrs.get("class", "").split()), relative_path
        assert contract["hero_classes"] <= set(hero.attrs.get("class", "").split()), relative_path

    assert checked_statuses == set(STATUS_CONTRACTS)


def test_data_updated_matches_internal_metadata_and_jsonld():
    index_root = parse_html(NEWS_INDEX_PATH)
    cards = [card for card in descendants(index_root, "article") if "data-news-card" in card.attrs]
    checked = 0

    for card in cards:
        updated = card.attrs.get("data-updated")
        if not updated:
            continue

        checked += 1
        page_path, _ = article_page_for(card)
        page_root = parse_html(page_path)
        news_articles = [item for item in jsonld_objects(page_root) if item.get("@type") == "NewsArticle"]
        assert len(news_articles) == 1, page_path.relative_to(ROOT)
        news_article = news_articles[0]
        assert news_article.get("dateModified") == updated, page_path.relative_to(ROOT)
        datetime.fromisoformat(updated)

        updated_times = [
            time
            for time in descendants(page_root, "time")
            if time.parent and "atualizado em:" in normalized_text(time.parent)
        ]
        if news_article.get("dateModified") == news_article.get("datePublished"):
            assert not updated_times, page_path.relative_to(ROOT)
        else:
            assert len(updated_times) == 1, page_path.relative_to(ROOT)
            assert updated_times[0].attrs.get("datetime") == updated, page_path.relative_to(ROOT)

    assert checked > 0
