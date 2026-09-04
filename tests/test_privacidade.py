import re
from pathlib import Path

from test_rodapes_globais import parse_html, public_html_paths


ROOT = Path(__file__).parents[1]
POLICY_PATH = ROOT / "politica-de-privacidade/index.html"
POLICY_ROUTE = "/politica-de-privacidade/"
PUBLISHER_ID = "ca-pub-2993532924249779"
ADSENSE_SCRIPT_MARKER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
ADSENSE_SCRIPT_SRC = f"https://{ADSENSE_SCRIPT_MARKER}?client={PUBLISHER_ID}"
ACCOUNT_META_MARKER = 'name="google-adsense-account"'
NEWS_INDEX_PATH = Path("noticias/index.html")
NEWS_TEMPLATE_PATH = Path("noticias/template-noticia.html")
NOINDEX_PATTERN = re.compile(
    r'<meta[^>]+name="robots"[^>]+content="[^"]*noindex', re.IGNORECASE
)
EXCLUDED_FOOTER_PATHS = {
    Path("comunicado/index.html"),
    Path("noticias/template-noticia.html"),
    Path("whatsapp/index.html"),
}


def publishable_news_paths():
    """Artigos de /noticias/ que são realmente publicáveis.

    Exclui a listagem, o template e qualquer página noindex — nada disso é
    artigo público e, portanto, nada disso entra no escopo de monetização.
    """
    paths = []
    for path in sorted((ROOT / "noticias").rglob("*.html")):
        relative_path = path.relative_to(ROOT)
        if relative_path in {NEWS_INDEX_PATH, NEWS_TEMPLATE_PATH}:
            continue
        if NOINDEX_PATTERN.search(path.read_text(encoding="utf-8")):
            continue
        paths.append(path)
    return paths


def head_of(path):
    heads = [node for node in parse_html(path).descendants() if node.tag == "head"]
    assert len(heads) == 1, path.relative_to(ROOT)
    return heads[0]


def test_every_publishable_news_page_carries_the_canonical_adsense_snippet():
    """Invariante derivada: toda notícia publicável carrega exatamente um snippet
    AdSense canônico no <head>. Uma notícia nova sem o snippet quebra aqui."""
    news_paths = publishable_news_paths()
    assert news_paths

    for path in news_paths:
        relative_path = path.relative_to(ROOT)
        content = path.read_text(encoding="utf-8")
        assert content.count(ADSENSE_SCRIPT_MARKER) == 1, relative_path

        scripts = [
            node
            for node in head_of(path).descendants()
            if node.tag == "script" and ADSENSE_SCRIPT_MARKER in node.attrs.get("src", "")
        ]
        assert len(scripts) == 1, relative_path

        attrs = scripts[0].attrs
        assert attrs["src"] == ADSENSE_SCRIPT_SRC, relative_path
        assert "async" in attrs, relative_path
        assert attrs.get("crossorigin") == "anonymous", relative_path


def test_news_template_stays_outside_the_monetized_scope():
    template = (ROOT / NEWS_TEMPLATE_PATH).read_text(encoding="utf-8")

    assert NOINDEX_PATTERN.search(template)
    assert ADSENSE_SCRIPT_MARKER not in template
    assert PUBLISHER_ID not in template


def test_publisher_id_scope_and_privacy_footer_on_monetized_pages():
    """Distinção a preservar:
    - as páginas monetizadas (com o script Auto Ads) são exatamente as notícias
      publicáveis, nenhuma outra área do site.
    - a homepage só declara o identificador em <meta name="google-adsense-account">
      e NÃO carrega o script de anúncios. Não é página com AdSense.
    - as páginas que referenciam o publisher ID são as monetizadas + a homepage.
    """
    pages_with_publisher_id = [
        path
        for path in public_html_paths()
        if PUBLISHER_ID in path.read_text(encoding="utf-8")
    ]

    monetized_pages = [
        path
        for path in pages_with_publisher_id
        if ADSENSE_SCRIPT_MARKER in path.read_text(encoding="utf-8")
    ]

    homepage = ROOT / "index.html"
    home_content = homepage.read_text(encoding="utf-8")

    assert set(monetized_pages) == set(publishable_news_paths())
    assert set(pages_with_publisher_id) == set(monetized_pages) | {homepage}
    assert all("noticias" in path.relative_to(ROOT).parts for path in monetized_pages)
    assert ACCOUNT_META_MARKER in home_content
    assert ADSENSE_SCRIPT_MARKER not in home_content

    for path in monetized_pages:
        footers = [node for node in parse_html(path).descendants() if node.tag == "footer"]
        assert len(footers) == 1, path.relative_to(ROOT)
        footer_links = [
            node.attrs.get("href")
            for node in footers[0].descendants()
            if node.tag == "a"
        ]
        assert POLICY_ROUTE in footer_links, path.relative_to(ROOT)


def test_privacy_policy_contains_the_confirmed_disclosures_only():
    content = POLICY_PATH.read_text(encoding="utf-8")
    normalized = content.casefold()

    assert "www.regularizeconsultorias.com.br" in normalized
    assert "fharmaca2013@hotmail.com" in normalized
    assert "não possui formulário próprio" in normalized
    assert "whatsapp" in normalized
    assert "instagram" in normalized
    assert "endereço ip" in normalized
    assert "google adsense" in normalized
    assert "cookies" in normalized
    assert "web beacons" in normalized
    assert "https://adssettings.google.com/" in normalized
    assert "26 de agosto de 2026" in normalized
    assert PUBLISHER_ID not in content
    assert "google analytics" not in normalized
    assert "ga4" not in normalized
    assert "clarity" not in normalized
    assert "<form" not in normalized


def test_every_public_page_with_a_footer_links_to_the_policy():
    paths_with_footer = []
    for path in public_html_paths():
        relative_path = path.relative_to(ROOT)
        footers = [node for node in parse_html(path).descendants() if node.tag == "footer"]
        if relative_path == Path("comunicado/index.html"):
            assert not footers
            continue

        assert len(footers) == 1, relative_path
        paths_with_footer.append(path)
        footer_links = [
            node.attrs.get("href")
            for node in footers[0].descendants()
            if node.tag == "a"
        ]
        assert footer_links.count(POLICY_ROUTE) == 1, relative_path

    assert len(paths_with_footer) == 95


def test_noindex_technical_pages_do_not_gain_the_policy_footer_link():
    for relative_path in EXCLUDED_FOOTER_PATHS - {Path("comunicado/index.html")}:
        content = (ROOT / relative_path).read_text(encoding="utf-8")
        assert f'href="{POLICY_ROUTE}"' not in content, relative_path
