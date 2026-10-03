"""Versão dos CSS e JS carregados pelas páginas.

Cada página carrega components.css ou custom.min.css, e main.min.js, com um
parâmetro ?v=. Os CSS de página alterados depois do rodapé de 03/10/2026
(Farmácia Popular, notícias e artigo) também passaram a ter ?v=. O valor é o
mesmo em todas as páginas para cada arquivo: uma página esquecida na versão
anterior receberia do cache o CSS ou o JS antigo. Ao mudar outro CSS ou JS de
página, acrescente ?v= a todas as referências dele e inclua-o em VERSIONED_ASSETS.
"""
import os
import re
from collections import defaultdict

from support import ROOT


VERSIONED_ASSETS = (
    "/assets/css/components.css",
    "/assets/css/custom.min.css",
    "/assets/js/main.min.js",
    "/assets/css/pages/farmacia-popular.css",
    "/assets/css/pages/noticia-detalhe.css",
    "/assets/css/pages/noticias.css",
)
ASSET_REFERENCE = re.compile(r'(?:href|src)="(/assets/[^"?]+\.(?:css|js))(\?[^"]*)?"')


def html_paths():
    for folder, subfolders, files in os.walk(ROOT):
        subfolders[:] = [name for name in subfolders if not name.startswith(".") and name != "__pycache__"]
        for name in files:
            if name.endswith(".html"):
                yield os.path.join(folder, name)


def _versions():
    versions = defaultdict(lambda: defaultdict(list))
    for path in html_paths():
        with open(path, encoding="utf-8") as handle:
            html = handle.read()
        for asset, query in ASSET_REFERENCE.findall(html):
            versions[asset][query].append(os.path.relpath(path, ROOT))
    return versions


def test_versioned_assets_use_one_version_per_file():
    versions = _versions()

    assert set(VERSIONED_ASSETS) <= set(versions), sorted(set(VERSIONED_ASSETS) - set(versions))
    for asset in VERSIONED_ASSETS:
        by_query = versions[asset]
        assert "" not in by_query, f"{asset} sem ?v= em {sorted(by_query[''])[:5]}"
        assert len(by_query) == 1, {
            query: sorted(paths)[:3] for query, paths in by_query.items()
        }
        query = next(iter(by_query))
        assert re.fullmatch(r"\?v=\d{8}-[a-z0-9-]+", query), f"{asset}: versão fora do padrão {query}"


def test_any_versioned_asset_is_versioned_on_every_page():
    for asset, by_query in _versions().items():
        if set(by_query) == {""}:
            continue
        assert "" not in by_query, f"{asset} tem ?v= em parte das páginas e falta em {sorted(by_query[''])[:5]}"
        assert len(by_query) == 1, f"{asset} com versões diferentes: {sorted(by_query)}"
