"""Rede dos testes de navegador: nada sai de 127.0.0.1.

Todo contexto do Chromium nos testes nasce por support.new_context ou
support.new_page, com a rota já instalada antes da navegação: AdSense e outros
domínios abortados e a Inter servida do arquivo local. O primeiro teste lê o
código dos testes; o segundo abre de verdade um artigo com AdSense, num
subprocesso, como os outros testes de navegador.
"""
import json
import re
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from support import ROOT, SITE_DIR, TESTS_DIR, subprocess_env


DIRECT_CONTEXT = re.compile(r"\bbrowser\.new_(?:context|page)\(")


def _test_sources():
    return sorted(path for path in TESTS_DIR.rglob("*.py") if "__pycache__" not in path.parts)


def test_every_browser_context_in_the_tests_uses_the_network_guard():
    direct, unguarded = [], []
    for path in _test_sources():
        if path.name == "support.py":
            continue
        text = path.read_text(encoding="utf-8")
        relative = path.relative_to(ROOT).as_posix()
        for match in DIRECT_CONTEXT.finditer(text):
            direct.append(f"{relative}:{text.count(chr(10), 0, match.start()) + 1}")
        if "chromium.launch(" in text and not re.search(r"\bnew_(?:context|page)\(browser", text):
            unguarded.append(relative)
    assert not direct, f"contexto criado sem support.new_context/new_page: {direct}"
    assert not unguarded, f"testes que abrem o Chromium sem a rota de rede: {unguarded}"


PROBE = r'''
import json
import sys
from urllib.parse import urlsplit

from playwright.sync_api import sync_playwright

import support

base, route = sys.argv[1:]
finished = []
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)
    page = support.new_page(browser, viewport={"width": 390, "height": 844})
    page.on("requestfinished", lambda request: finished.append(request.url))
    page.goto(base + route, wait_until="load")
    state = page.evaluate("""async () => {
        await document.fonts.ready;
        const faces = [...document.fonts].filter(face => face.family.replace(/["']/g, '') === 'Inter');
        return {
            adsense: typeof window.adsbygoogle !== 'undefined' && !Array.isArray(window.adsbygoogle) ? 'carregado' : 'ausente',
            interLoaded: faces.some(face => face.status === 'loaded'),
            interUsed: document.fonts.check('600 16px Inter'),
            bodyFont: getComputedStyle(document.body).fontFamily,
        };
    }""")
    browser.close()
external = [url for url in finished if (urlsplit(url).hostname or "") not in support.LOCAL_HOSTS]
print(json.dumps({"state": state, "blocked": support.BLOCKED_REQUESTS, "externalFinished": external}))
'''


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


def _article_with_adsense():
    for path in sorted((SITE_DIR / "noticias").glob("*/index.html")):
        if "pagead2.googlesyndication.com/pagead/js/adsbygoogle.js" in path.read_text(encoding="utf-8"):
            return "/" + path.relative_to(SITE_DIR).as_posix()[: -len("index.html")]
    raise AssertionError("nenhum artigo com AdSense no site servido")


def test_article_with_adsense_loads_nothing_outside_localhost():
    route = _article_with_adsense()
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", PROBE, f"http://127.0.0.1:{server.server_port}", route],
            capture_output=True, text=True, encoding="utf-8", timeout=120, env=subprocess_env(),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert completed.returncode == 0, completed.stderr
    result = json.loads(completed.stdout)
    assert any("googlesyndication.com" in url for url in result["blocked"]), (
        f"{route}: o pedido do AdSense não passou pela rota de bloqueio: {result['blocked']}"
    )
    assert result["state"]["adsense"] == "ausente", result["state"]
    # Só as respostas locais da fonte terminam fora de 127.0.0.1.
    stray = [url for url in result["externalFinished"] if "fonts.g" not in url]
    assert not stray, f"{route}: requisições externas concluídas: {stray}"
    assert result["state"]["interLoaded"] and result["state"]["interUsed"], (
        f"{route}: a Inter local não carregou ({result['state']})"
    )
