from pathlib import Path

from test_rodapes_globais import parse_html, public_html_paths


ROOT = Path(__file__).parents[1]
POLICY_PATH = ROOT / "politica-de-privacidade/index.html"
POLICY_ROUTE = "/politica-de-privacidade/"
PUBLISHER_ID = "ca-pub-2993532924249779"
ADSENSE_SCRIPT_MARKER = "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js"
ACCOUNT_META_MARKER = 'name="google-adsense-account"'
EXCLUDED_FOOTER_PATHS = {
    Path("comunicado/index.html"),
    Path("noticias/template-noticia.html"),
    Path("whatsapp/index.html"),
}


def test_publisher_id_scope_and_privacy_footer_on_monetized_pages():
    """Distinção a preservar:
    - 74 páginas têm o script Auto Ads ativo (adsbygoogle.js). São as páginas
      efetivamente monetizadas / com AdSense.
    - a homepage só declara o identificador em <meta name="google-adsense-account">
      e NÃO carrega o script de anúncios. Não é página com AdSense.
    - 75 páginas públicas referenciam o publisher ID (74 monetizadas + homepage).
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

    assert len(pages_with_publisher_id) == 75
    assert len(monetized_pages) == 74
    assert all("noticias" in path.relative_to(ROOT).parts for path in monetized_pages)
    assert homepage in pages_with_publisher_id
    assert homepage not in monetized_pages
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
