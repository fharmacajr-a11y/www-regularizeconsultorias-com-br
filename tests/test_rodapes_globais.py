from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).parents[1]
WHATSAPP_PATH = Path("whatsapp/index.html")
COMUNICADO_PATH = Path("comunicado/index.html")


class Node:
    def __init__(self, tag="root", attrs=(), parent=None):
        self.tag = tag
        self.attrs = dict(attrs)
        self.parent = parent
        self.children = []

    def descendants(self):
        for child in self.children:
            yield child
            yield from child.descendants()


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


def parse_html(path):
    parser = TreeParser()
    parser.feed(path.read_text(encoding="utf-8"))
    return parser.root


def nearest_list_item(node, footer):
    current = node.parent
    while current and current is not footer:
        if current.tag == "li":
            return current
        current = current.parent
    return None


def test_footer_navigation_links_are_distinct_list_items():
    for path in sorted(ROOT.rglob("*.html")):
        relative_path = path.relative_to(ROOT)
        if relative_path == WHATSAPP_PATH:
            continue

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
