"""Conteúdo público das notícias não encaminha o leitor a fonte ou material externo.

A varredura cobre o <main> de cada matéria: corpo, quadros, FAQ, cartões de
fontes e blocos equivalentes. Ficam de fora o cabeçalho técnico, os scripts,
os metadados, o rodapé, a navegação global, os botões flutuantes e o contato
institucional da Regularize. Link interno e arquivo servido pelo próprio site
não são referência de terceiro. A única exceção é o link oficial conferido de
support.NEWS_OFFICIAL_SOURCE_LINKS, aceito só como href de <a> na página e no
destino exatos listados.
"""
import re
from urllib.parse import urlsplit

from support import NEWS_OFFICIAL_SOURCE_LINKS, ROOT, TreeParser


NEWS_DIRECTORY = ROOT / "noticias"
OWN_HOSTS = {"www.regularizeconsultorias.com.br", "regularizeconsultorias.com.br"}
INSTITUTIONAL_EMAILS = {"fharmaca2013@hotmail.com"}
FORWARD_ATTRIBUTES = ("href", "src", "action", "formaction", "poster", "cite", "data-href")
BARE_URL = re.compile(r"https?://[^\s<>\"']+|(?<![A-Za-z0-9:/])//[A-Za-z0-9.-]+\.[A-Za-z]{2,}[^\s<>\"']*")
# Destinos que já saíram do conteúdo público e não podem voltar em outra matéria.
REMOVED_DESTINATIONS = (
    "https://bvsms.saude.gov.br/bvs/saudelegis/gm/2026/prt12091_24_09_2026_rep.html",
    "https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular/renovacao-de-estabelecimentos-participantes",
    "https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular/participacao/documentacao",
    "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/anvisa-aprova-regularizacao-de-cosmeticos-artesanais",
    "https://www.planalto.gov.br/ccivil_03/_ato2023-2026/2025/lei/L15154.htm",
    "https://www.gov.br/anvisa/pt-br/assuntos/regulamentacao/agenda-regulatoria/minutas-previas",
    "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2026/anvisa-publica-perguntas-e-respostas-sobre-o-peticionamento-de-historico-de-mudanca-de-produto-hmp-via-pelo-solicita",
    "https://www.gov.br/anvisa/pt-br/assuntos/noticias-anvisa/2025/assuntos-de-peticoes-de-medicamentos-e-produtos-biologicos-serao-migrados-para-o-solicita",
    "https://cnes2.datasus.gov.br/Mod_Mensagem_Abertura1.asp",
    "https://www.gov.br/anvisa/pt-br/assuntos/farmacopeia/farmacopeia-brasileira",
    "anvisalegis.datalegis.net",
    "cnes2.datasus.gov.br",
)


def news_article_paths():
    return sorted(NEWS_DIRECTORY.glob("*/index.html"))


def parse_text(html):
    parser = TreeParser()
    parser.feed(html)
    return parser.root


def _main(root):
    mains = [node for node in root.descendants() if node.tag == "main"]
    assert len(mains) == 1, "a matéria precisa de um único main editorial"
    return mains[0]


def _own_host(hostname):
    host = (hostname or "").lower().rstrip(".")
    return host in OWN_HOSTS or host.endswith(".regularizeconsultorias.com.br")


def _email_address(href):
    address = href.split(":", 1)[1].split("?", 1)[0].strip().lower()
    return address


def external_forward(value):
    """Destino que tira o leitor do site. Vazio se o valor for navegação interna."""
    if not value or value.startswith(("#", "?", "/")) and not value.startswith("//"):
        return ""
    if value.startswith("//"):
        host = (urlsplit("https:" + value).hostname or "").lower()
        return "" if _own_host(host) else value
    parsed = urlsplit(value)
    scheme = parsed.scheme.lower()
    if scheme in {"http", "https"}:
        return "" if _own_host(parsed.hostname) else value
    if scheme == "mailto":
        return "" if _email_address(value) in INSTITUTIONAL_EMAILS else value
    if scheme:
        return value
    return ""


def _visible_text(node):
    if node.tag in {"script", "style"}:
        return
    for piece in node.text:
        yield piece
    for child in node.children:
        yield from _visible_text(child)


def editorial_external_problems(html, page):
    """Lista encaminhamentos externos no conteúdo editorial. Lista vazia se não houver."""
    root = parse_text(html)
    main = _main(root)
    problems = []
    authorized = NEWS_OFFICIAL_SOURCE_LINKS.get(page, ())

    for node in [main, *main.descendants()]:
        if node.tag in {"script", "style"}:
            continue
        for attribute in FORWARD_ATTRIBUTES:
            value = node.attrs.get(attribute, "")
            for part in value.split(","):
                destination = external_forward(part.strip().split(" ")[0])
                if not destination:
                    continue
                if node.tag == "a" and attribute == "href" and destination in authorized:
                    continue
                anchor = " ".join(node.text_content().split())[:160]
                problems.append(
                    f"{page}: erro editorial, encaminhamento externo em <{node.tag} {attribute}> "
                    f"“{anchor}” → {destination}"
                )
        if node is not main and node.tag in {"script", "style"}:
            continue

    for piece in _visible_text(main):
        for match in BARE_URL.findall(piece):
            if external_forward(match):
                problems.append(
                    f"{page}: erro editorial, URL escrita no conteúdo editorial → {match[:240]}"
                )

    without_metadata = re.sub(r"<script\b[^>]*>.*?</script>", "", html, flags=re.I | re.S)
    without_metadata = re.sub(r"<style\b[^>]*>.*?</style>", "", without_metadata, flags=re.I | re.S)
    for destination in REMOVED_DESTINATIONS:
        if destination in without_metadata:
            problems.append(
                f"{page}: erro editorial, destino retirado reapareceu no conteúdo público → {destination}"
            )
    return problems


def test_news_editorial_content_does_not_forward_to_external_references():
    paths = news_article_paths()
    assert len(paths) == 83
    problems = []
    for path in paths:
        page = path.relative_to(ROOT).as_posix()
        problems.extend(editorial_external_problems(path.read_text(encoding="utf-8"), page))
    assert not problems, "erro editorial: referência externa no conteúdo público das notícias\n" + "\n".join(problems)
    # A exceção não fica órfã: cada link autorizado aparece uma vez, como href, na página listada.
    for page, destinations in NEWS_OFFICIAL_SOURCE_LINKS.items():
        html = (ROOT / page).read_text(encoding="utf-8")
        for destination in destinations:
            assert html.count(destination) == 1 and f'href="{destination}"' in html, (page, destination)
