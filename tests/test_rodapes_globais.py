from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parents[1]
EXCLUDED_PUBLIC_PATHS = {Path("noticias/template-noticia.html"), Path("whatsapp/index.html")}
COMUNICADO_PATH = Path("comunicado/index.html")
GLOBAL_NAVIGATION = {
    "/",
    "/sobre/",
    "/servicos/",
    "/equipe/",
    "/contato/",
    "/manuais-e-pops/",
    "/farmacia-popular/",
    "/noticias/",
}


class Node:
    def __init__(self, tag="root", attrs=(), parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []
        self.text = []

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()

    def text_content(self):
        return " ".join(self.text) + " " + " ".join(child.text_content() for child in self.children)


class TreeParser(HTMLParser):
    VOID_ELEMENTS = {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "param", "source", "track", "wbr"}

    def __init__(self):
        super().__init__()
        self.root = Node()
        self.stack = [self.root]

    def handle_starttag(self, tag, attrs):
        node = Node(tag, attrs, self.stack[-1])
        self.stack[-1].children.append(node)
        if tag not in self.VOID_ELEMENTS:
            self.stack.append(node)

    def handle_endtag(self, tag):
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == tag:
                self.stack = self.stack[:index]
                return

    def handle_data(self, data):
        if data.strip():
            self.stack[-1].text.append(data.strip())


def parse_html(path):
    parser = TreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.root


def public_html_paths():
    return sorted(
        path
        for path in ROOT.rglob("*.html")
        if path.relative_to(ROOT) not in EXCLUDED_PUBLIC_PATHS
    )


def nearest_list_item(node, footer):
    current = node.parent
    while current and current is not footer:
        if current.tag == "li":
            return current
        current = current.parent
    return None


def footer_for(path):
    root = parse_html(path)
    footers = [node for node in root.descendants() if node.tag == "footer"]
    assert len(footers) == 1, path.relative_to(ROOT)
    return footers[0]


def test_footer_navigation_links_are_distinct_list_items():
    for path in public_html_paths():
        relative_path = path.relative_to(ROOT)
        root = parse_html(path)
        footers = [node for node in root.descendants() if node.tag == "footer"]
        if relative_path == COMUNICADO_PATH:
            assert not footers, relative_path
            continue

        assert len(footers) == 1, relative_path
        footer = footers[0]
        links = [node for node in footer.descendants() if node.tag == "a"]
        manuals = [node for node in links if node.attrs.get("href") == "/manuais-e-pops/"]
        popular = [node for node in links if node.attrs.get("href") == "/farmacia-popular/"]

        assert len(manuals) == 1, relative_path
        assert len(popular) == 1, relative_path

        manuals_item = nearest_list_item(manuals[0], footer)
        popular_item = nearest_list_item(popular[0], footer)
        assert manuals_item is not None, relative_path
        assert popular_item is not None, relative_path
        assert manuals_item is not popular_item, relative_path


def test_footer_contract_is_canonical():
    for path in public_html_paths():
        relative_path = path.relative_to(ROOT)
        if relative_path == COMUNICADO_PATH:
            assert not [node for node in parse_html(path).descendants() if node.tag == "footer"]
            continue

        footer = footer_for(path)
        links = [node for node in footer.descendants() if node.tag == "a"]
        images = [node for node in footer.descendants() if node.tag == "img"]
        footer_text = footer.text_content()
        navigation_headings = [node for node in footer.descendants() if node.tag in {"h2", "h4"}]
        heading_text = {node.text_content().strip() for node in navigation_headings}

        assert "Navegação" in heading_text, relative_path
        assert "Contato" in heading_text, relative_path
        assert {node.attrs.get("href") for node in links} >= GLOBAL_NAVIGATION, relative_path
        assert any(node.attrs.get("src", "").endswith("logorc2-white.png") for node in images), relative_path
        assert any(node.attrs.get("alt") == "Regularize Consultoria" for node in images), relative_path
        assert "99627-5900" in footer_text, relative_path
        assert any(node.attrs.get("href", "").startswith("mailto:") for node in links), relative_path
        assert any("instagram.com/regularizeconsultoriarc" in node.attrs.get("href", "") for node in links), relative_path
        assert "Regularize Consultoria" in footer_text, relative_path
        assert "privada" in footer_text.lower(), relative_path
        assert "independente" in footer_text.lower(), relative_path
        assert "© 2026 Regularize Consultoria" in footer_text, relative_path
        assert "Todos os direitos reservados" in footer_text, relative_path

        gsa_images = [node for node in images if node.attrs.get("src", "").endswith("login-gsa-48.ico")]
        assert len(gsa_images) == 1, relative_path
        assert gsa_images[0].attrs.get("alt") == "Logo Gestor de Sites e Apps", relative_path
        assert "Gestor de Sites & Apps" in footer_text, relative_path
