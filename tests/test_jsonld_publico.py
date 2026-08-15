import json
import subprocess
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class JsonLdParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.blocks = []
        self._current = None

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "script" or self._current is not None:
            return
        attributes = {name.lower(): value for name, value in attrs}
        if (attributes.get("type") or "").lower() == "application/ld+json":
            self._current = []

    def handle_data(self, data):
        if self._current is not None:
            self._current.append(data)

    def handle_endtag(self, tag):
        if tag.lower() == "script" and self._current is not None:
            self.blocks.append("".join(self._current))
            self._current = None


def tracked_html_files():
    output = subprocess.check_output(
        ["git", "ls-files", "*.html"], cwd=ROOT, text=True
    )
    return [ROOT / relative_path for relative_path in output.splitlines()]


def test_public_jsonld_is_valid():
    block_count = 0
    for path in tracked_html_files():
        parser = JsonLdParser()
        parser.feed(path.read_text(encoding="utf-8"))
        for block_number, block in enumerate(parser.blocks, 1):
            block_count += 1
            try:
                json.loads(block)
            except json.JSONDecodeError as error:
                relative_path = path.relative_to(ROOT).as_posix()
                raise AssertionError(
                    f"JSON-LD inválido em {relative_path}, "
                    f"bloco {block_number}: {error}"
                ) from error

    assert block_count == 149
