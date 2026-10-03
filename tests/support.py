"""Leitura compartilhada do HTML público do site."""
import os
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
# Pasta servida nos testes de navegador: o repositório ou, com PAGES_SITE_DIR,
# a saída do build do GitHub Pages gerada por scripts/gerar_site_pages.py.
SITE_DIR = Path(os.environ.get("PAGES_SITE_DIR") or ROOT).resolve()
EXCLUDED_PUBLIC_PATHS = {
    Path("noticias/template-noticia.html"),
    Path("whatsapp/index.html"),
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
    VOID_ELEMENTS = {
        "area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr",
    }

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
        and "a-publicar" not in path.relative_to(ROOT).parts
    )
