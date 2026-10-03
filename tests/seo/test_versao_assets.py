"""Versão dos CSS e do JS compartilhados pelas páginas.

Cada página carrega components.css ou custom.min.css, e main.min.js, com um
parâmetro ?v=. O valor é o mesmo em todas as páginas para cada arquivo: uma
página esquecida na versão anterior receberia do cache o CSS ou o JS antigo.
"""
import os
import re
from collections import defaultdict

from support import ROOT


SHARED_ASSETS = (
    "/assets/css/components.css",
    "/assets/css/custom.min.css",
    "/assets/js/main.min.js",
)
ASSET_REFERENCE = re.compile(
    r'(?:href|src)="(/assets/(?:css/components\.css|css/custom\.min\.css|js/main\.min\.js))(\?[^"]*)?"'
)


def html_paths():
    for folder, subfolders, files in os.walk(ROOT):
        subfolders[:] = [name for name in subfolders if not name.startswith(".") and name != "__pycache__"]
        for name in files:
            if name.endswith(".html"):
                yield os.path.join(folder, name)


def test_shared_assets_use_one_version_per_file():
    versions = defaultdict(lambda: defaultdict(list))
    for path in html_paths():
        with open(path, encoding="utf-8") as handle:
            html = handle.read()
        for asset, query in ASSET_REFERENCE.findall(html):
            versions[asset][query].append(os.path.relpath(path, ROOT))

    assert set(versions) == set(SHARED_ASSETS), sorted(versions)
    for asset, by_query in versions.items():
        assert "" not in by_query, f"{asset} sem ?v= em {sorted(by_query[''])[:5]}"
        assert len(by_query) == 1, {
            query: sorted(paths)[:3] for query, paths in by_query.items()
        }
        query = next(iter(by_query))
        assert re.fullmatch(r"\?v=\d{8}-[a-z0-9-]+", query), f"{asset}: versão fora do padrão {query}"
