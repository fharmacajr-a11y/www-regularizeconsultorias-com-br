"""Leitura compartilhada do HTML público do site e rede dos testes de navegador."""
import json
import os
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[1]
TESTS_DIR = Path(__file__).resolve().parent
# Pasta servida nos testes de navegador: o repositório ou, com PAGES_SITE_DIR,
# a saída do build do GitHub Pages gerada por scripts/gerar_site_pages.py.
SITE_DIR = Path(os.environ.get("PAGES_SITE_DIR") or ROOT).resolve()
EXCLUDED_PUBLIC_PATHS = {
    Path("noticias/template-noticia.html"),
    Path("whatsapp/index.html"),
}
# Única exceção à regra de não encaminhar o leitor para fora nas notícias: link oficial
# conferido, por página e destino exato. Desde 15/10/2026, só a íntegra da RE nº 4.035/2026
# no DOU, no quadro de 14/10/2026 da matéria consolidada de produtos irregulares.
NEWS_OFFICIAL_SOURCE_LINKS = {
    "noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/index.html": (
        "https://www.in.gov.br/web/dou/-/resolucao-re-n-4.035-de-9-de-outubro-de-2026-738059775",
    ),
}

# ---------------------------------------------------------------------------
# Rede dos testes de navegador
#
# Todo contexto do Chromium nasce com a rota abaixo, antes de qualquer
# navegação: 127.0.0.1/localhost passam; o CSS do Google Fonts vira o
# @font-face da Inter local (o mesmo arquivo e os mesmos descritores da home) e
# o .woff2 sai de assets/fonts; todo o resto (AdSense, wa.me, redes sociais) é
# abortado e registrado. Assim as medidas não dependem da rede e nenhum teste
# carrega anúncio. Os subprocessos importam este módulo (PYTHONPATH apontando
# para tests/) e usam as mesmas funções.
# ---------------------------------------------------------------------------
LOCAL_HOSTS = {"127.0.0.1", "localhost"}
FONT_FILE = ROOT / "assets" / "fonts" / "inter-latin-variable-v20.woff2"
LOCAL_FONT_URL = "https://fonts.gstatic.com/regularize-testes/inter-latin-variable-v20.woff2"
LOCAL_FONT_CSS = (
    "@font-face{font-family:'Inter';font-style:normal;font-weight:400 800;font-display:swap;"
    f"src:url('{LOCAL_FONT_URL}') format('woff2');"
    "unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,"
    "U+0308,U+0329,U+2000-206F,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}"
)
FONT_MODES = ("local", "block")
# Requisições externas abortadas neste processo (url).
BLOCKED_REQUESTS = []


def _log_request(action, url):
    """Com RC_REDE_LOG=<pasta>, grava cada acesso externo tratado (comprovação).

    Cada processo escreve o próprio arquivo (rede-<pid>.jsonl): os testes rodam
    subprocessos em paralelo e um arquivo comum misturaria as linhas.
    """
    folder = os.environ.get("RC_REDE_LOG")
    if not folder:
        return
    os.makedirs(folder, exist_ok=True)
    entry = {"acao": action, "url": url[:200], "pid": os.getpid(),
             "teste": os.environ.get("PYTEST_CURRENT_TEST", "").split(" ")[0]}
    with open(os.path.join(folder, f"rede-{os.getpid()}.jsonl"), "a", encoding="utf-8") as handle:
        handle.write(json.dumps(entry, ensure_ascii=False) + "\n")


def guard_network(context, fonts="local", allow=()):
    """Instala a rota de rede dos testes num contexto recém-criado.

    fonts="local" serve a Inter de assets/fonts; fonts="block" aborta as
    fontes externas (o navegador usa a fonte de reserva). allow são prefixos de
    URL liberados além de 127.0.0.1, por exemplo o domínio público numa sonda de
    produção. Falha na hora se a fonte local não existir.
    """
    if fonts not in FONT_MODES:
        raise ValueError(f"fonts deve ser um de {FONT_MODES}, não {fonts!r}")
    font_bytes = None
    if fonts == "local":
        if not FONT_FILE.is_file():
            raise FileNotFoundError(f"fonte local dos testes ausente: {FONT_FILE}")
        font_bytes = FONT_FILE.read_bytes()
    allowed = tuple(allow)

    def handler(route):
        url = route.request.url
        host = urlsplit(url).hostname or ""
        if host in LOCAL_HOSTS or url.startswith(allowed):
            return route.continue_()
        if font_bytes is not None and host == "fonts.googleapis.com":
            _log_request("fonte local (css)", url)
            return route.fulfill(status=200, body=LOCAL_FONT_CSS, content_type="text/css; charset=utf-8",
                                 headers={"Access-Control-Allow-Origin": "*"})
        if font_bytes is not None and url == LOCAL_FONT_URL:
            _log_request("fonte local (woff2)", url)
            return route.fulfill(status=200, body=font_bytes, content_type="font/woff2",
                                 headers={"Access-Control-Allow-Origin": "*"})
        BLOCKED_REQUESTS.append(url)
        _log_request("bloqueado", url)
        return route.abort("blockedbyclient")

    context.route("**/*", handler)
    return context


def new_context(browser, fonts="local", allow=(), **options):
    """browser.new_context com a rota de rede dos testes já instalada."""
    return guard_network(browser.new_context(**options), fonts=fonts, allow=allow)


def new_page(browser, fonts="local", allow=(), **options):
    """Página num contexto próprio com a rota de rede dos testes."""
    return new_context(browser, fonts=fonts, allow=allow, **options).new_page()


ESSENTIAL_RESOURCES = ("document", "stylesheet", "script", "font")


def watch_local_loading(page, base, essential, other):
    """Registra, a partir de agora, os recursos do servidor local (base) que não carregaram nesta página.

    Cada falha leva página (a que fez o pedido; numa navegação, o próprio
    endereço), janela, URL, tipo do recurso, erro, se era uma navegação e o
    motivo: conexão recusada, outra falha de rede, abortado ou resposta HTTP de
    erro. Documento, CSS, JavaScript e fonte vão para essential: sem eles o caso
    não pode ser avaliado, e o registro não diz se a causa está no servidor dos
    testes ou no site. Os outros recursos vão para other.

    Um net::ERR_ABORTED só é cancelamento esperado (other) com evidência: outra
    navegação da página começou depois do pedido (a navegação dele foi
    descartada) ou o contexto está sendo encerrado. Sem isso, o recurso
    essencial abortado conta como falha. Recursos externos ficam de fora: a
    rota de rede já os trata.

    Devolve a função a chamar logo antes de context.close(): os cancelamentos
    depois dela são do encerramento do contexto.
    """
    state = {"navigations": 0, "closing": False}
    started = {}

    def main_navigation(request):
        try:
            return request.is_navigation_request() and request.frame.parent_frame is None
        except Exception:  # noqa: BLE001 - pedido sem frame (service worker) não é navegação da página
            return False

    def requested(request):
        if main_navigation(request):
            state["navigations"] += 1
        started[request] = (state["navigations"], page.url)

    def record(target, request, kind, error, reason):
        navigation = request.is_navigation_request()
        page_url = request.url if navigation else started.get(request, (0, page.url))[1]
        viewport = page.viewport_size or {}
        target.append({"tipo": kind, "recurso": request.resource_type, "url": request.url.replace(base, "", 1),
                       "erro": error, "pagina": page_url.replace(base, "", 1),
                       "janela": f"{viewport.get('width')}x{viewport.get('height')}", "navegacao": navigation,
                       "motivo": reason})

    def failed(request):
        if not request.url.startswith(base):
            return
        error = request.failure or "falha sem descrição"
        target = essential if request.resource_type in ESSENTIAL_RESOURCES else other
        if "ERR_ABORTED" in error:
            # Sem registro do início, vale a navegação atual: nada prova o descarte.
            generation = started.get(request, (state["navigations"], None))[0]
            if state["closing"]:
                return record(other, request, "cancelamento esperado", error, "encerramento do contexto")
            if state["navigations"] > generation:
                return record(other, request, "cancelamento esperado", error,
                              "navegação descartada: outra navegação da página começou depois do pedido")
            return record(target, request, "abortado", error,
                          "abortado sem navegação nova nem encerramento do contexto; não carregou na página avaliada")
        if "ERR_CONNECTION_REFUSED" in error:
            return record(target, request, "conexão recusada", error, "a conexão com o servidor local foi recusada")
        return record(target, request, "falha de rede", error, "o pedido falhou antes da resposta")

    def responded(response):
        if response.url.startswith(base) and response.status >= 400:
            target = essential if response.request.resource_type in ESSENTIAL_RESOURCES else other
            record(target, response.request, "resposta HTTP de erro", f"HTTP {response.status}",
                   "o servidor local respondeu com erro")

    def closing():
        state["closing"] = True

    page.on("request", requested)
    page.on("requestfailed", failed)
    page.on("response", responded)
    return closing


def subprocess_env(**extra):
    """Ambiente dos subprocessos de teste: importam support por PYTHONPATH."""
    env = dict(os.environ, PYTHONIOENCODING="utf-8", **extra)
    env["PYTHONPATH"] = os.pathsep.join(filter(None, [str(TESTS_DIR), env.get("PYTHONPATH")]))
    return env


class ServidorDeTeste(ThreadingHTTPServer):
    """Servidor local dos testes de navegador com fila de conexões de 128.

    No diagnóstico de 18/10/2026, o teste do menu mobile (4 sondas em paralelo;
    o SimpleHTTPRequestHandler responde em HTTP/1.0, uma conexão por recurso)
    teve documento, CSS e JS recusados (net::ERR_CONNECTION_REFUSED) com a fila
    padrão da biblioteca (socketserver.TCPServer.request_queue_size = 5) e
    nenhuma recusa com 128, mudando só a fila. A explicação é uma hipótese
    sustentada por esse experimento, não um mecanismo medido: a fila de 5 enche
    nas rajadas e o Windows recusa as conexões excedentes; a fila do sistema não
    foi observada diretamente. O valor vale antes da ativação, porque o
    construtor chama server_activate(), que faz listen(request_queue_size). Só
    esta subclasse muda; protocolo, threads e handler continuam os da biblioteca.
    """

    request_queue_size = 128


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
