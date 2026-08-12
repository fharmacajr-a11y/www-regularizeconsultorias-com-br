import re
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parents[1]
TEMPLATE_PATH = ROOT / "noticias" / "template-noticia.html"
BANNER_CLASS = "site-regulatory-banner"
BANNER_HREF = "/noticias/farmacia-popular-portaria-12091-2026-novas-regras/"
CSS_PATHS = (
    ROOT / "assets" / "css" / "custom.css",
    ROOT / "assets" / "css" / "components.css",
    ROOT / "assets" / "css" / "custom.min.css",
)


class _Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.nodes = []

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs), self.getpos()[0]))


def _parse(path):
    parser = _Parser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.nodes


def _pages_with_global_header():
    excluded = {".git", ".venv", "node_modules", "tests", "tmp", "temp"}
    return sorted(
        path
        for path in ROOT.rglob("*.html")
        if not any(part in excluded for part in path.relative_to(ROOT).parts)
        and path != TEMPLATE_PATH
        and any(tag == "header" and attrs.get("id") == "navbar" for tag, attrs, _ in _parse(path))
    )


def _assert_banner(path):
    html = path.read_text(encoding="utf-8")
    nodes = _parse(path)
    banners = [node for node in nodes if node[0] == "aside" and BANNER_CLASS in node[1].get("class", "").split()]
    headers = [node for node in nodes if node[0] == "header" and node[1].get("id") == "navbar"]
    links = re.findall(
        r'<a\b[^>]*class="[^"]*site-regulatory-banner__link[^\"]*"[^>]*href="([^"]+)"[^>]*>(.*?)</a>',
        html,
        re.DOTALL,
    )

    relative_path = path.relative_to(ROOT)
    assert len(banners) == 1, relative_path
    assert len(headers) == 1, relative_path
    assert len(links) == 1, relative_path
    assert links[0][0] == BANNER_HREF, relative_path
    assert "Farmácia Popular" in links[0][1], relative_path
    assert "Portaria 12.091/2026" in links[0][1], relative_path
    assert 'aria-label="Atualização importante do Farmácia Popular"' in html, relative_path
    banner_html = html[html.index('<aside class="site-regulatory-banner"'):html.index("</aside>")]
    assert 'target="_blank"' not in banner_html, relative_path
    assert "localhost" not in html and "127.0.0.1" not in html, relative_path
    navbar_match = re.search(r'<header\b[^>]*id="navbar"', html)
    assert navbar_match is not None, relative_path
    assert html.index('class="site-regulatory-banner') < navbar_match.start(), relative_path


def test_every_page_with_global_header_has_one_portaria_banner():
    pages = _pages_with_global_header()
    assert pages
    for path in pages:
        _assert_banner(path)


def test_news_template_has_one_portaria_banner():
    _assert_banner(TEMPLATE_PATH)


def _rule(css, selector):
    match = re.search(rf"{re.escape(selector)}\s*\{{([^}}]+)\}}", css)
    assert match is not None, selector
    return re.sub(r"\s+", "", match.group(1)).lower()


def test_banner_css_stays_sticky_and_uses_the_avisos_red():
    tailwind = (ROOT / "assets" / "css" / "tailwind.min.css").read_text(encoding="utf-8")
    avisos_match = re.search(r"\.bg-red-600\s*\{([^}]+)\}", tailwind)
    assert avisos_match is not None
    avisos_rule = avisos_match.group(1)
    avisos_red = re.search(r"background-color:rgb\(\s*(\d+)\s+(\d+)\s+(\d+)", avisos_rule)
    assert avisos_red is not None
    avisos_hex = "#" + "".join(f"{int(channel):02x}" for channel in avisos_red.groups())

    for path in CSS_PATHS:
        css = path.read_text(encoding="utf-8")
        compact_css = re.sub(r"\s+", "", css).lower()
        banner_rule = _rule(css, ".site-regulatory-banner")
        link_rule = _rule(css, ".site-regulatory-banner__link")
        label_rule = _rule(css, ".site-regulatory-banner__label")
        navbar_rule = _rule(css, "#navbar")
        assert "position:sticky" in banner_rule, path.name
        assert "top:0" in banner_rule, path.name
        assert re.search(r"(?:^|;)height:4\.8rem(?:;|$)", link_rule), path.name
        assert "min-height:4.8rem" in link_rule, path.name
        assert "top:4.8rem" in navbar_rule, path.name
        assert f"background-color:{avisos_hex}" in label_rule, path.name
        assert "color:#fff" in label_rule or "color:#ffffff" in label_rule, path.name
        assert "@media(max-width:420px)" in compact_css, path.name
        assert "flex-direction:column" in compact_css, path.name
        assert "white-space:nowrap" in compact_css, path.name
        assert "position:absolute" in compact_css, path.name
        assert "height:4.8rem" in compact_css, path.name
        assert "@media(min-width:768px){.site-regulatory-banner__link{height:2.5rem;min-height:2.5rem" in compact_css, path.name
        assert "#navbar{top:2.5rem" in compact_css, path.name
