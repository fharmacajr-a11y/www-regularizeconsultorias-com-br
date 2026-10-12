"""Guardas da Fase 1K: ciclo histórico do SIFAP, sem tutorial e sem prazo oficial sem prova.

As mutações usam cópias em memória. Quem rejeita o erro é a mesma função
``findings`` que valida as páginas publicadas.
"""
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[2]

PRAZO = ROOT / "noticias/prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular/index.html"
REG = ROOT / "noticias/sifap-regularizacao-cadastral-farmacias-notificadas-13-maio/index.html"
SUSP = ROOT / "noticias/farmacia-popular-suspensao-temporaria-recadastramento-sifap/index.html"
CUIDADOS = ROOT / "noticias/farmacia-popular-cuidados-cadastro-documentacao/index.html"
INDEX = ROOT / "noticias/index.html"
COM = ROOT / "comunicado/index.html"
SITEMAP = ROOT / "sitemap.xml"

TITLE_REG = "SIFAP: regularização, maio/2026"
TITLE_PRAZO = "SIFAP: pendências, maio/2026"
PRAZO_URL = "https://www.regularizeconsultorias.com.br/noticias/prazo-sifap-terminou-pendencias-analise-rta-farmacia-popular/"
REG_URL = "https://www.regularizeconsultorias.com.br/noticias/sifap-regularizacao-cadastral-farmacias-notificadas-13-maio/"

MARKERS = ("não se confunde", "não restaura")
BAD_RTA = ("desbloqueio", "aprovação", "liberação", "libera", "garante")


def plain(html):
    text = re.sub(r"<script\b[^>]*>.*?</script>", " ", html, flags=re.I | re.S)
    text = re.sub(r"<style\b[^>]*>.*?</style>", " ", text, flags=re.I | re.S)
    text = re.sub(r"<[^>]+>", " ", text)
    return " ".join(text.split())


def main_html(html):
    match = re.search(r"<main\b[^>]*>(.*)</main>", html, flags=re.I | re.S)
    assert match, "main editorial ausente"
    return match.group(1)


def historico_html(html):
    marker = 'id="aviso-historico-sifap"'
    index = html.find(marker)
    assert index != -1, "registro histórico SIFAP ausente"
    start = html.rfind("<article", 0, index)
    end = html.find("</article>", index) + len("</article>")
    assert start != -1 and end > index
    return html[start:end]


def blocks(html):
    found = re.findall(r"<(p|li|h1|h2|h3)\b[^>]*>(.*?)</\1>", html, flags=re.I | re.S)
    return [plain(body) for _, body in found]


def findings(html):
    """Problemas editoriais no fragmento. Conjunto vazio quando o texto passa."""
    found = set()
    text = plain(html)
    folded = text.casefold()
    if re.search(
        r"acesse o sifap|deve acessar|verificar imediatamente|verifique imediatamente|realizar a assinatura",
        folded,
    ):
        found.add("instrucao-acesso-assinatura")
    if re.search(
        r"o que fazer agora|o que fazer em cada status|quem precisa agir agora|o que revisar dentro do sistema|"
        r"ver orientação pós-prazo|veja próximos passos|ler aviso urgente|corrija os documentos|\breenvie\b",
        folded,
    ):
        found.add("tutorial-status")
    if re.search(r"\breabre\b|prazo aberto|permanece aberto|nova prorrogação", folded):
        found.add("prazo-atual")
    if re.search(r"13/05|15/05|29/04|13 de maio", folded):
        found.add("data-sem-prova")
    for block in blocks(html):
        low = block.casefold()
        if "maio" in low and "31/08" in low and not any(marker in low for marker in MARKERS):
            found.add("associacao-3108")
        for sentence in re.split(r"[.!?]", block):
            slow = sentence.casefold()
            if "rta" in slow and any(word in slow for word in BAD_RTA) and "não" not in slow:
                found.add("rta-liberacao")
    if re.search(r"consultoria privada é golpe|proibido contratar", folded):
        found.add("taxa-consultoria")
    for href in re.findall(r"""href\s*=\s*["']([^"']+)["']""", html, flags=re.I):
        value = href.strip()
        if value.casefold().startswith("mailto:"):
            found.add("mailto-historico")
            continue
        parsed = urlsplit(value)
        if parsed.scheme in {"http", "https"}:
            host = (parsed.hostname or "").casefold()
            if host.endswith("gov.br") or "caixa.gov.br" in host:
                found.add("link-governamental")
            elif host and not host.endswith("regularizeconsultorias.com.br"):
                found.add("link-outro-dominio")
    if re.search(r"https?://|www\.", text):
        found.add("url-escrita")
    return found


def _regions():
    prazo = PRAZO.read_text(encoding="utf-8")
    reg = REG.read_text(encoding="utf-8")
    comunicado = COM.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    cards = re.findall(r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>", index, flags=re.S)
    prazo_card = next(card for card in cards if "prazo-sifap-terminou" in card)
    reg_card = next(card for card in cards if "sifap-regularizacao-cadastral" in card)
    return {
        "prazo": main_html(prazo),
        "regularizacao": main_html(reg),
        "historico": historico_html(comunicado),
        "card-prazo": prazo_card,
        "card-regularizacao": reg_card,
    }


def test_paginas_e_registro_nao_tem_tutorial_nem_prazo_sem_prova():
    problems = {name: findings(html) for name, html in _regions().items()}
    assert problems == {name: set() for name in problems}, problems


def test_distincoes_obrigatorias_e_servico_privado():
    regions = _regions()
    for name in ("prazo", "regularizacao", "historico"):
        text = plain(regions[name])
        assert "maio de 2026" in text, name
        assert "não se confunde" in text, name
        assert "31/08/2026" in text, name
        assert "Portaria GM/MS nº 12.091/2026" in text, name
        assert "não cobram taxa" in text, name
        assert "não proíbe" in text, name
        assert "honorários" in text, name
        assert "golpe" in text, name
        assert "isoladamente, não comprova aprovação, desbloqueio" in text or "não comprova aprovação, desbloqueio" in text, name
    for name in ("prazo", "regularizacao"):
        assert "executa os serviços de regularização contratados" in plain(regions[name])
        assert 'href="/contato/"' in regions[name]
        assert 'href="/servicos/"' in regions[name]
    historico = regions["historico"]
    assert 'data-status="resolved"' in historico
    assert "ENCERRADO" in historico
    assert "URGENTE" not in historico
    assert "O que fazer agora" not in historico
    assert "Ver registro do ciclo" in historico
    assert "Ler o registro das pendências" in historico


def test_titulos_carimbo_ordem_e_contagens():
    prazo = PRAZO.read_text(encoding="utf-8")
    reg = REG.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    comunicado = COM.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")

    assert f"<title>{TITLE_PRAZO} | Regularize Consultoria</title>" in prazo
    assert f"<title>{TITLE_REG} | Regularize Consultoria</title>" in reg
    assert f'"headline":"{TITLE_PRAZO}"' in prazo
    assert f'"headline":"{TITLE_REG}"' in reg
    stamp = re.search(r'<meta property="article:modified_time" content="([^"]+)"', prazo).group(1)
    assert stamp == re.search(r'<meta property="article:modified_time" content="([^"]+)"', reg).group(1)
    assert f'"dateModified":"{stamp}"' in prazo
    assert f'"dateModified":"{stamp}"' in reg
    assert '"datePublished":"2026-05-18T09:00:00-03:00"' in prazo
    assert '"datePublished":"2026-05-10T09:00:00-03:00"' in reg
    day = stamp[:10]
    assert f"<loc>{PRAZO_URL}</loc>\n    <lastmod>{day}</lastmod>" in sitemap
    assert f"<loc>{REG_URL}</loc>\n    <lastmod>{day}</lastmod>" in sitemap

    cards = re.findall(r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>", index, flags=re.S)
    assert len(cards) == 83
    # 11/10/2026, 06h07: a atualização do CNES 09/2026 (prazo encerrado, item 48) leva aquele card ao 1º lugar; os cards das posições 1 a 31 descem uma.
    assert "prazo-sifap-terminou" in cards[23]
    assert "sifap-regularizacao-cadastral" in cards[24]
    # Modelo único (12/10/2026, R1): todos os cards levam news-card-compact; a posição não troca o formato.
    assert all("news-card-compact" in card.split(">", 1)[0] for card in cards)
    assert f'data-updated="{stamp}"' in cards[23]
    assert f'data-updated="{stamp}"' in cards[24]
    assert "Ler atualização" in cards[23] and "Ler atualização" in cards[24]
    assert TITLE_PRAZO in cards[23] and TITLE_REG in cards[24]

    items = re.findall(r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)"\}', index)
    assert len(items) == 83
    assert [int(position) for position, _ in items] == list(range(1, 84))
    assert items[23][1] == PRAZO_URL
    assert items[24][1] == REG_URL

    historico = historico_html(comunicado)
    assert 'datetime="2026-10-07T10:53:00-03:00"' in historico
    assert "ciclo de regularização cadastral de maio de 2026" in historico
    statuses = re.findall(r'<article\b[^>]*\bdata-status="([^"]+)"', comunicado)
    # 09/10/2026: o aviso do Edital 6/2026 passou ao histórico (7 ativos, 8 no histórico).
    # 11/10/2026: o aviso do CNES 09/2026 passou ao histórico (6 ativos, 9 no histórico).
    assert len([status for status in statuses if status != "resolved"]) == 6
    assert statuses.count("resolved") == 9
    assert ">6</span>" in prazo
    assert len(list((ROOT / "noticias").glob("*/index.html"))) == 83


SUSP_URL = "https://www.regularizeconsultorias.com.br/noticias/farmacia-popular-suspensao-temporaria-recadastramento-sifap/"
SUSP_PUBLISHED = "2026-05-20T13:00:00-03:00"
HEADLINE_SUSP = "Farmácia Popular: suspensão por recadastramento pendente deve ser analisada no contexto atual"
CARD_TITLE_SUSP = "Farmácia Popular: suspensão de maio/2026"
SUMMARY_SUSP = "Avisos de suspensão por recadastramento pendente no SIFAP ocorreram em maio de 2026. A situação atual deve ser analisada à luz das regras vigentes do Farmácia Popular."

CASES = (
    (
        "instrucao-acesso-assinatura",
        "prazo",
        "<p>O responsável legal deve acessar o SIFAP e realizar a assinatura.</p>",
    ),
    (
        "tutorial-status",
        "prazo",
        "<p>O que fazer em cada status do SIFAP? Corrija os documentos e reenvie.</p>",
    ),
    (
        "prazo-atual",
        "regularizacao",
        "<p>O SIFAP reabre agora e o prazo permanece aberto.</p>",
    ),
    (
        "data-sem-prova",
        "regularizacao",
        "<p>O único marco oficial universal é 13/05/2026.</p>",
    ),
    (
        "associacao-3108",
        "regularizacao",
        "<p>A janela de maio segue até 31/08/2026 no mesmo calendário.</p>",
    ),
    (
        "rta-liberacao",
        "prazo",
        "<p>A assinatura do RTA garante a aprovação e o desbloqueio.</p>",
    ),
    (
        "link-governamental",
        "regularizacao",
        '<p><a href="https://www.gov.br/saude/pt-br/composicao/sectics/farmacia-popular/">página oficial</a></p>',
    ),
    (
        "link-outro-dominio",
        "regularizacao",
        '<p><a href="https://example.com/guia">guia externo</a></p>',
    ),
    (
        "mailto-historico",
        "historico",
        '<p><a href="mailto:analise.fpopular@saude.gov.br">escreva</a></p>',
    ),
    (
        "taxa-consultoria",
        "regularizacao",
        "<p>A consultoria privada é golpe e é proibido contratar.</p>",
    ),
)


def _cards(index):
    return re.findall(r"<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>", index, flags=re.S)


def _card_moment(card):
    # Data só com o dia (AAAA-MM-DD): início do dia em Brasília (-03:00), a regra de assets/js/main.js (12/10/2026).
    def _parse(value):
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            value += "T00:00:00-03:00"
        return datetime.fromisoformat(value)

    updated = re.search(r'\bdata-updated="([^"]+)"', card)
    if updated:
        return _parse(updated.group(1))
    published = re.search(r'<time\b[^>]*datetime="([^"]+)"', card)
    assert published, "card sem carimbo"
    return _parse(published.group(1))


def _card_hrefs(cards):
    hrefs = []
    for card in cards:
        match = re.search(r'href="(/noticias/[^"]+/)"', card)
        assert match, "card sem href interno"
        hrefs.append("https://www.regularizeconsultorias.com.br" + match.group(1))
    return hrefs


def region_with_snippet(target, snippet):
    """Insere o erro em HTML válido e devolve a mesma região usada na página real."""
    if target == "prazo":
        return main_html(PRAZO.read_text(encoding="utf-8").replace("</main>", snippet + "</main>", 1))
    if target == "regularizacao":
        return main_html(REG.read_text(encoding="utf-8").replace("</main>", snippet + "</main>", 1))
    if target != "historico":
        raise AssertionError(target)
    page = COM.read_text(encoding="utf-8")
    marker = 'id="aviso-historico-sifap"'
    index = page.find(marker)
    assert index != -1
    open_end = page.find(">", index)
    between = page[index:open_end]
    assert open_end != -1 and "<" not in between and "data-aviso-history-content" in between
    mutated = page[: open_end + 1] + snippet + page[open_end + 1 :]
    region = historico_html(mutated)
    assert snippet in region
    assert region.startswith("<article")
    assert 'id="aviso-historico-sifap" data-aviso-history-content' in region
    return region


def test_suspensao_registra_a_correcao_material_com_datas_e_ordem_coerentes():
    suspensao = SUSP.read_text(encoding="utf-8")
    index = INDEX.read_text(encoding="utf-8")
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert f"<title>{HEADLINE_SUSP} | Regularize Consultoria</title>" in suspensao
    assert f"<h1" in suspensao and HEADLINE_SUSP in suspensao
    assert f'article:published_time" content="{SUSP_PUBLISHED}"' in suspensao
    assert f'"datePublished": "{SUSP_PUBLISHED}"' in suspensao
    assert f'<time datetime="{SUSP_PUBLISHED}">20/05/2026</time> às 13h00' in suspensao
    stamp = re.search(r'<meta property="article:modified_time" content="([^"]+)"', suspensao).group(1)
    modified = datetime.fromisoformat(stamp)
    assert modified > datetime.fromisoformat("2026-10-07T11:13:00-03:00")
    assert modified <= datetime.now().astimezone()
    assert stamp.endswith("-03:00")
    assert "2026-08-15T09:32:08-03:00" not in suspensao
    assert f'"dateModified": "{stamp}"' in suspensao
    day = modified.strftime("%d/%m/%Y")
    hour = modified.strftime("%Hh%M")
    assert f'<time datetime="{stamp}">{day}</time> às {hour}' in suspensao
    assert "executa os serviços de regularização contratados" in suspensao
    assert "orientar os próximos passos" not in suspensao
    assert TITLE_PRAZO in suspensao

    cards = _cards(index)
    assert len(cards) == 83
    # 11/10/2026, 06h07: a atualização do CNES 09/2026 (prazo encerrado, item 48) leva aquele card ao 1º lugar; os cards das posições 1 a 31 descem uma.
    assert SUSP_URL.endswith(re.search(r'href="(/noticias/[^"]+/)"', cards[22]).group(1))
    assert f'data-updated="{stamp}"' in cards[22]
    assert f'<time datetime="{stamp}" class="leading-none">{day} • {hour}</time>' in cards[22]
    assert SUMMARY_SUSP in cards[22]
    assert f'data-title="{CARD_TITLE_SUSP}"' in cards[22]
    assert f">{CARD_TITLE_SUSP}</h2>" in cards[22]
    assert "<br" not in re.search(r"<h2\b[^>]*>.*?</h2>", cards[22], re.S).group(0).casefold()
    assert HEADLINE_SUSP not in cards[22]
    assert "prazo aberto" not in cards[22].casefold()
    assert "news-card-compact" in cards[22].split(">", 1)[0]
    assert cards == sorted(cards, key=_card_moment, reverse=True)
    items = re.findall(r'\{"@type":"ListItem","position":(\d+),"url":"([^"]+)"\}', index)
    assert [int(position) for position, _ in items] == list(range(1, 84))
    assert [url for _, url in items] == _card_hrefs(cards)
    assert items[22][1] == SUSP_URL
    assert f"<loc>{SUSP_URL}</loc>\n    <lastmod>{stamp[:10]}</lastmod>" in sitemap

    cuidados = CUIDADOS.read_text(encoding="utf-8")
    assert TITLE_PRAZO in cuidados
    assert "veja como acompanhar" not in cuidados
    assert stamp not in cuidados


def test_mutacoes_reais_sao_rejeitadas_pela_mesma_funcao():
    assert len(CASES) == 10
    for expected, target, snippet in CASES:
        found = findings(region_with_snippet(target, snippet))
        assert expected in found, (expected, found)
        assert found == {expected}, (expected, found)
