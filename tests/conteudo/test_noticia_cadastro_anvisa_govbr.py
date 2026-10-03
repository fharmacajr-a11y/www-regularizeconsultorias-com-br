import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
PAGE = ROOT / "noticias" / "cadastro-anvisa-govbr-transicao-sistemas" / "index.html"
NEWS_INDEX = ROOT / "noticias" / "index.html"
SITEMAP = ROOT / "sitemap.xml"
URL = "https://www.regularizeconsultorias.com.br/noticias/cadastro-anvisa-govbr-transicao-sistemas/"
UPDATED = "2026-09-30T17:49:00-03:00"
TITLE = "Cadastro Anvisa integra quatro cadastros e autentica pelo Gov.br"
SUMMARY = "O Cadastro Anvisa foi criado para integrar quatro cadastros e autentica o acesso pelo Gov.br. Dados e vínculos corretos interessam às empresas reguladas. A nota do Solicita, de 14/04/2026, trata do registro de novas empresas."


def _body(html):
    return re.search(r'<section class="article-body">(.*?)</section>', html, re.DOTALL).group(1)


def test_cadastro_anvisa_revision_keeps_publication_and_records_the_update():
    html = PAGE.read_text(encoding="utf-8")
    assert f'"datePublished":"2026-05-19T19:00:00-03:00"' in html
    assert f'"dateModified":"{UPDATED}"' in html
    assert f'article:published_time" content="2026-05-19T19:00:00-03:00"' in html
    assert f'article:modified_time" content="{UPDATED}"' in html
    assert f'<time datetime="2026-05-19">19/05/2026</time> às 19h00' in html
    assert f'<time datetime="{UPDATED}">30/09/2026</time> às 17h49' in html
    assert f"<h1 class=\"text-3xl sm:text-4xl md:text-5xl font-extrabold tracking-tight leading-tight text-white mb-5\">{TITLE}</h1>" in html
    assert f'content="{SUMMARY}"' in html
    assert f'"headline":"{TITLE}"' in html
    assert f'"description":"{SUMMARY}"' in html
    assert "Atualização" in html
    assert "article-hero-informativo" not in html
    assert "article-badge-informativo" not in html


def test_cadastro_anvisa_body_states_the_confirmed_scope_without_an_access_script():
    body = _body(PAGE.read_text(encoding="utf-8"))
    folded = body.casefold()
    for term in (
        "sistema de cadastramento de empresas",
        "sistema de segurança",
        "cadastro de instituições",
        "cadastro de usuários",
        "14 de abril de 2026",
        "empresas que já estavam cadastradas",
        "cadastro antigo",
        "divergências nos dados ou nos vínculos podem exigir regularização cadastral",
        "dificuldades de acesso também podem envolver autenticação ou indisponibilidade técnica",
        "a análise de cada caso permite identificar a situação encontrada e as providências cabíveis",
        "25 de setembro de 2026",
        "atualizada em 29 de setembro de 2026",
        "etapa preliminar",
        "30 de setembro de 2026",
        "março de 2026",
        "prata ou ouro",
        "estrangeiros",
        "e-mail e senha",
        "essas orientações dizem respeito ao sei-anvisa",
        "regras próprias de cada sistema",
        "executa as etapas contratadas",
        "ato pessoal do responsável legal",
        "escopo e orçamento próprios",
        "eventuais alterações de prazo dependem das regras e das comunicações oficiais",
    ):
        assert term in folded, term
    assert "href=" not in body
    for banned in (
        "duas etapas",
        "prorrogação geral",
        "passo a passo",
        "clique",
        "cadastre",
        "acesse",
        "gestores de cadastro",
        "sncr-farmácia",
        "bloqueio",
        "instabilidades",
        "até o momento",
        "http",
        "não afirma",
        "não diagnostica",
        "não percorre",
        "não se estendem",
        "não estende essa regra",
        "instabilidade à transição",
        "fontes usadas nesta revisão",
    ):
        assert banned not in folded, banned


def test_cadastro_anvisa_card_stays_fourth_in_the_listing_and_sitemap():
    index = NEWS_INDEX.read_text(encoding="utf-8")
    cards = re.findall(r"(<article\b[^>]*\bdata-news-card\b[^>]*>.*?</article>)", index, re.DOTALL)
    assert len(cards) == 83
    card = cards[3]
    opening = card.split(">", 1)[0]
    assert f'href="/noticias/cadastro-anvisa-govbr-transicao-sistemas/"' in card
    assert "news-card-compact" not in opening
    assert f'data-updated="{UPDATED}"' in opening
    assert f'data-title="{TITLE}"' in opening
    assert f'data-summary="{SUMMARY}"' in opening
    assert 'data-category="anvisa"' in opening
    assert ">Atualização</span>" in card
    assert "Ler atualização" in card
    assert f'<time datetime="{UPDATED}" class="leading-none">30/09/2026 • 17h49</time>' in card
    assert index.count(f'href="/noticias/cadastro-anvisa-govbr-transicao-sistemas/"') == 1
    assert '>Todos</span><span class="text-xs text-slate-400">83<' in index
    assert '>ANVISA</span><span class="text-xs text-slate-400">54<' in index
    assert f'"position":4,"url":"https://www.regularizeconsultorias.com.br/noticias/cadastro-anvisa-govbr-transicao-sistemas/"' in index
    sitemap = SITEMAP.read_text(encoding="utf-8")
    assert f"<loc>https://www.regularizeconsultorias.com.br/noticias/cadastro-anvisa-govbr-transicao-sistemas/</loc>\n    <lastmod>2026-09-30</lastmod>" in sitemap


def test_cadastro_anvisa_service_block_keeps_the_executor_position():
    html = PAGE.read_text(encoding="utf-8")
    assert "Organizar o cadastro da empresa" in html
    assert "Solicitar análise cadastral" in html
    assert "Conhecer os serviços da Regularize" in html
    assert 'href="/contato/"' in html
    assert 'href="/servicos/"' in html
    assert "Ol%C3%A1%21%20Li%20a%20not%C3%ADcia%20da%20Regularize%20sobre%20o%20Cadastro%20Anvisa" in html
    assert html.count('class="category-chip category-chip--anvisa') >= 2
