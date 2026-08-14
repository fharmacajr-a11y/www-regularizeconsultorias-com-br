import json
from datetime import datetime

from test_rodapes_globais import ROOT, parse_html


NEWS_INDEX_PATH = ROOT / "noticias" / "index.html"
STATUS_LABELS = {"atualização", "informativo", "urgente", "orientação"}


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


def test_explicit_editorial_updates_match_index_page_status_and_classes():
    index_root = parse_html(NEWS_INDEX_PATH)
    cards = [card for card in descendants(index_root, "article") if "data-news-card" in card.attrs]
    checked_updates = 0

    for card in cards:
        page_path, cta = article_page_for(card)
        card_badge = status_badge(card)
        if normalized_text(card_badge) != "atualização" or normalized_text(cta) != "ler atualização":
            continue

        checked_updates += 1
        page_root = parse_html(page_path)
        hero = article_hero(page_root)
        page_badge = status_badge(hero)

        assert normalized_text(page_badge) == "atualização", page_path.relative_to(ROOT)
        assert {"bg-amber-500", "text-white"} <= set(card_badge.attrs.get("class", "").split()), page_path.relative_to(ROOT)
        assert {"bg-amber-500", "text-white"} <= set(page_badge.attrs.get("class", "").split()), page_path.relative_to(ROOT)
        assert {"from-amber-600", "via-brand-dark", "to-brand"} <= set(hero.attrs.get("class", "").split()), page_path.relative_to(ROOT)

    assert checked_updates > 0


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
