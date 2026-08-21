from pathlib import Path
from urllib.parse import urlsplit

from test_rodapes_globais import ROOT, parse_html


NEWS_DIRECTORY = ROOT / "noticias"
CANONICAL_CALLOUT_CLASSES = {
    "rounded-2xl",
    "border",
    "border-yellow-200",
    "bg-yellow-50",
    "p-5",
    "shadow-sm",
    "md:p-6",
}


def descendants(node, tag=None):
    return [child for child in node.descendants() if tag is None or child.tag == tag]


def normalized_text(node):
    return " ".join(node.text_content().split())


def news_article_paths():
    return sorted(
        path
        for path in NEWS_DIRECTORY.glob("*/index.html")
        if path.parent != NEWS_DIRECTORY
    )


def test_editorial_update_callouts_follow_the_global_contract():
    callout_texts = []
    checked = 0

    for path in news_article_paths():
        relative_path = path.relative_to(ROOT)
        root = parse_html(path)
        callouts = [
            node
            for node in descendants(root)
            if "data-news-update-callout" in node.attrs
        ]

        for callout in callouts:
            checked += 1
            text = normalized_text(callout)
            headings = descendants(callout, "h2") + descendants(callout, "h3") + descendants(callout, "h4")
            icons = descendants(callout, "svg")
            links = descendants(callout, "a")
            classes = set(callout.attrs.get("class", "").split())

            assert callout.tag == "aside", relative_path
            assert "ATUALIZAÇÃO" in text, relative_path
            assert len(headings) == 1 and normalized_text(headings[0]), relative_path
            assert text, relative_path
            assert len(icons) == 1, relative_path
            assert not descendants(callout, "button"), relative_path
            assert CANONICAL_CALLOUT_CLASSES <= classes, relative_path
            assert "style" not in callout.attrs, relative_path
            assert not any("w-[" in class_name for class_name in classes), relative_path
            assert any("ATUALIZAÇÃO" in normalized_text(node) for node in descendants(callout, "span")), relative_path
            assert all(not urlsplit(link.attrs.get("href", "")).scheme for link in links), relative_path
            callout_texts.append(text.casefold())

    assert checked > 0
    assert len(callout_texts) == len(set(callout_texts))


def test_portaria_update_callout_keeps_its_following_section():
    path = NEWS_DIRECTORY / "farmacia-popular-portaria-12091-2026-novas-regras" / "index.html"
    html = path.read_text(encoding="utf-8")
    callout_end = html.index("</aside>", html.index("data-news-update-callout")) + len("</aside>")

    assert html[callout_end:].lstrip().startswith("<h2>Alterações cadastrais passam a ter prazos expressos</h2>")


def test_sifap_update_link_is_a_separate_spaced_content_block():
    path = NEWS_DIRECTORY / "prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular" / "index.html"
    root = parse_html(path)
    callout = next(node for node in descendants(root) if "data-news-update-callout" in node.attrs)
    paragraphs = [child for child in callout.children if child.tag == "p"]

    assert len(paragraphs) == 2
    assert "article-spacing-flush-bottom" in paragraphs[1].attrs.get("class", "").split()
    links = descendants(paragraphs[1], "a")
    assert len(links) == 1
    assert links[0].attrs.get("href") == "/noticias/farmacia-popular-suspensao-temporaria-recadastramento-sifap/"
