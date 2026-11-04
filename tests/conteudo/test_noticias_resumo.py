"""Resumo do topo das notícias e a versão dele para ouvir (piloto de 04/11/2026).

Desde 04/11/2026, três notícias (SNCR, irregulares e MAPA) têm, logo abaixo do cartão "Publicado em / Atualizado
em" e antes do corpo, o bloco "Resumo da notícia": três pontos (o que mudou, desde quando e o que a farmácia ou a
empresa deve fazer) e o botão "Ouvir resumo", que lê o resumo com a síntese de voz do próprio navegador
(assets/js/pages/noticia-resumo.js), com velocidade de 1x, 1,5x, 2x ou 3x. O texto falado vem do atributo data-leitura de cada item: a mesma informação,
escrita para ser ouvida, com as siglas soletradas ("R D C") e os números e as datas por extenso.

O teste confere:
- o resumo acompanha a última atualização da notícia: o <time> do resumo ("Conferido com a atualização de ...") é o
  mesmo dateModified do JSON-LD, do article:modified_time e do "Atualizado em" do cartão. Quando a notícia ganha
  atualização nova e o resumo fica para trás, o teste falha e diz o que revisar;
- a versão falada não tem algarismo, "nº", barra nem sigla colada (duas maiúsculas seguidas) e traz, por extenso,
  cada data, cada número de ato ("nº 1.046/2026") e cada número do texto visível do item;
- o bloco não tem link (regra das notícias, CLAUDE.md), o botão e a velocidade nascem ocultos (só o JavaScript os
  mostra, e só com suporte à síntese de voz) e as páginas com resumo carregam o CSS e o script dele, e só elas.
O funcionamento do botão no navegador está em tests/funcionalidades/test_noticia_resumo_audio.py.
"""
import html as html_lib
import json
import re

import pytest

from support import ROOT


NEWS_DIRECTORY = ROOT / "noticias"
CSS = "/assets/css/pages/noticia-resumo.css"
JS = "/assets/js/pages/noticia-resumo.js"
PILOTOS = {
    "rdc-1000-2025-anvisa-prorroga-prazo-sncr": "O que a farmácia deve fazer",
    "anvisa-suspende-medicamento-proibe-produtos-irregulares": "O que a farmácia deve fazer",
    "mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal": "O que a empresa deve fazer",
}
MESES = ("janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto", "setembro", "outubro",
         "novembro", "dezembro")
UNIDADES = ("zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze",
            "treze", "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove")
DEZENAS = ("", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa")
CENTENAS = ("", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos",
            "oitocentos", "novecentos")
# O bloco é um <div role="region"> (não <section>: os testes das notícias tratam o 1º </section> como o fim do corpo) e
# termina sempre no aviso (role="status").
RESUMO = re.compile(r'<div class="noticia-resumo"[^>]*\bdata-noticia-resumo\b[^>]*>(.*?<p class="noticia-resumo__aviso"'
                    r'[^>]*></p>)\s*</div>', re.DOTALL)
ITEM = re.compile(
    r'<li class="noticia-resumo__item" data-leitura="([^"]*)"><span class="noticia-resumo__item-titulo">([^<]*)</span>'
    r'<span class="noticia-resumo__item-texto">(.*?)</span></li>',
    re.DOTALL,
)
DATA = re.compile(r"\b(\d{2})/(\d{2})/(\d{4})\b")
ATO = re.compile(r"\bnº (\d{1,3}(?:\.\d{3})*)/(\d{4})\b")
NUMERO = re.compile(r"\b\d{1,3}(?:\.\d{3})+\b|\b\d+\b")


def _ate_mil(numero):
    if numero < 20:
        return UNIDADES[numero]
    if numero < 100:
        dezena, unidade = divmod(numero, 10)
        return DEZENAS[dezena] + (f" e {UNIDADES[unidade]}" if unidade else "")
    if numero == 100:
        return "cem"
    centena, resto = divmod(numero, 100)
    return CENTENAS[centena] + (f" e {_ate_mil(resto)}" if resto else "")


def por_extenso(numero):
    """Número por extenso em português do Brasil, até 999.999 ("mil e quarenta e seis", "mil seiscentos e dezessete")."""
    numero = int(str(numero).replace(".", ""))
    if numero < 1000:
        return _ate_mil(numero)
    milhar, resto = divmod(numero, 1000)
    texto = "mil" if milhar == 1 else f"{_ate_mil(milhar)} mil"
    if not resto:
        return texto
    return texto + (" e " if resto < 100 or resto % 100 == 0 else " ") + _ate_mil(resto)


def data_por_extenso(dia, mes, ano):
    dia = int(dia)
    return f"{'primeiro' if dia == 1 else por_extenso(dia)} de {MESES[int(mes) - 1]} de {por_extenso(ano)}"


def _texto(trecho):
    return " ".join(html_lib.unescape(re.sub(r"<[^>]+>", " ", trecho)).split())


def _paginas_com_resumo():
    return sorted(path for path in NEWS_DIRECTORY.glob("*/index.html")
                  if "data-noticia-resumo" in path.read_text(encoding="utf-8"))


def _resumo(html):
    blocos = RESUMO.findall(html)
    assert len(blocos) == 1, f"{len(blocos)} blocos de resumo"
    return blocos[0]


def _itens(bloco):
    return [(html_lib.unescape(leitura), titulo, _texto(texto)) for leitura, titulo, texto in ITEM.findall(bloco)]


def falhas_de_atualizacao(slug, html):
    """O que impede o resumo de valer para a versão atual da notícia (lista vazia: está em dia)."""
    bloco = _resumo(html)
    conferido = re.search(r'Conferido com a atualização de <time datetime="([^"]+)">(\d{2}/\d{2}/\d{4})</time>, '
                          r'às (\d{2}h\d{2})</p>', bloco)
    if not conferido:
        return [f"{slug}: o resumo não diz com que atualização foi conferido"]
    resumo, dia, hora = conferido.groups()
    artigos = [bloco for bloco in (json.loads(texto) for texto in re.findall(
        r'<script type="application/ld\+json">\s*(.*?)\s*</script>', html, re.DOTALL)) if bloco.get("@type") == "NewsArticle"]
    modificado = artigos[0]["dateModified"] if len(artigos) == 1 else None
    meta = re.findall(r'<meta (?:property="article:modified_time" content="([^"]+)"|content="([^"]+)" '
                      r'property="article:modified_time")', html)
    cartao = re.findall(r'Atualizado em:</span> <time datetime="([^"]+)">', html)
    falhas = []
    if modificado is None:
        return [f"{slug}: sem NewsArticle com dateModified"]
    if resumo != modificado:
        falhas.append(
            f"{slug}: o resumo foi conferido com a atualização de {resumo}, mas a notícia foi atualizada em "
            f"{modificado}. Revise os três itens e a versão falada (data-leitura) e passe o <time> do resumo para "
            f"{modificado}."
        )
    if [a or b for a, b in meta] != [modificado]:
        falhas.append(f"{slug}: article:modified_time {meta} diferente do dateModified {modificado}")
    if cartao != [modificado]:
        falhas.append(f"{slug}: 'Atualizado em' do cartão {cartao} diferente do dateModified {modificado}")
    esperado = f"{resumo[8:10]}/{resumo[5:7]}/{resumo[:4]}", f"{resumo[11:13]}h{resumo[14:16]}"
    if (dia, hora) != esperado:
        falhas.append(f"{slug}: o texto do resumo diz {dia}, às {hora}, e o datetime, {esperado[0]}, às {esperado[1]}")
    return falhas


def falhas_da_leitura(titulo, texto, leitura):
    """O que falta ou sobra na versão falada de um item, em relação ao texto visível."""
    falhas = []
    if not leitura.startswith(f"{titulo}. "):
        falhas.append(f"não começa por '{titulo}. '")
    for proibido, motivo in ((r"\d", "algarismo"), (r"nº|º|ª", "'nº' ou ordinal"), (r"/", "barra"),
                             (r"\b[A-ZÀ-Ý]{2,}", "sigla colada (soletre: 'R D C')")):
        achado = re.search(proibido, leitura)
        if achado:
            falhas.append(f"{motivo}: '{achado.group(0)}'")
    resto = texto
    for dia, mes, ano in DATA.findall(texto):
        if data_por_extenso(dia, mes, ano) not in leitura:
            falhas.append(f"falta a data {dia}/{mes}/{ano} por extenso ('{data_por_extenso(dia, mes, ano)}')")
    resto = DATA.sub(" ", resto)
    for numero, ano in ATO.findall(resto):
        esperado = f"número {por_extenso(numero)}, de {por_extenso(ano)}"
        if esperado not in leitura:
            falhas.append(f"falta o ato nº {numero}/{ano} por extenso ('{esperado}')")
    resto = ATO.sub(" ", resto)
    for numero in NUMERO.findall(resto):
        if not re.search(rf"\b{por_extenso(numero)}\b", leitura):
            falhas.append(f"falta o número {numero} por extenso ('{por_extenso(numero)}')")
    return falhas


def test_por_extenso_segue_a_escrita_dos_atos():
    assert por_extenso("1.046") == "mil e quarenta e seis"
    assert por_extenso("1.617") == "mil seiscentos e dezessete"
    assert por_extenso("4.246") == "quatro mil duzentos e quarenta e seis"
    assert por_extenso(2026) == "dois mil e vinte e seis"
    assert por_extenso(1998) == "mil novecentos e noventa e oito"
    assert por_extenso(1200) == "mil e duzentos"
    assert por_extenso(100) == "cem" and por_extenso(206) == "duzentos e seis"
    assert data_por_extenso("01", "10", "2026") == "primeiro de outubro de dois mil e vinte e seis"
    assert data_por_extenso("03", "03", "2027") == "três de março de dois mil e vinte e sete"


@pytest.mark.parametrize("slug", sorted(PILOTOS))
def test_noticias_do_piloto_tem_o_resumo_logo_depois_das_datas(slug):
    html = (NEWS_DIRECTORY / slug / "index.html").read_text(encoding="utf-8")
    bloco = _resumo(html)
    abertura = re.search(r'<div class="noticia-resumo"[^>]*>', html).group(0)

    # Topo da notícia: depois do cartão de datas e antes do corpo (e dos quadros de atualização).
    assert html.index('class="article-meta-card') < html.index(abertura) < html.index('<section class="article-body">')
    assert html.index(abertura) < html.index("<aside data-news-update-callout")
    assert abertura == ('<div class="noticia-resumo" role="region" aria-labelledby="noticia-resumo-titulo" '
                        'data-noticia-resumo>')
    assert ('<h2 id="noticia-resumo-titulo" class="noticia-resumo__titulo" data-leitura="Resumo da notícia.">'
            'Resumo da notícia</h2>') in bloco

    itens = _itens(bloco)
    assert [titulo for _, titulo, _ in itens] == ["O que mudou", "Desde quando", PILOTOS[slug]]
    assert bloco.count("<li") == 3
    for leitura, titulo, texto in itens:
        assert texto and leitura, (slug, titulo)
        # Duas ou três linhas no computador: o item é resumo, não um segundo corpo da notícia.
        assert len(texto) <= 360, (slug, titulo, len(texto))

    # Regra das notícias: nenhum link, nem interno, no resumo.
    assert "<a " not in bloco and "href=" not in bloco and "http" not in bloco

    # O botão nasce oculto; o script só o mostra com suporte à síntese de voz.
    botao = re.search(r"<button\b[^>]*>", bloco).group(0)
    assert botao == ('<button type="button" class="botao botao--secundario noticia-resumo__ouvir" data-resumo-ouvir '
                     'hidden>')
    assert "<span data-resumo-ouvir-rotulo>Ouvir resumo</span></button>" in bloco
    # Velocidade da voz (pedido do Jr em 04/11/2026): 1x, 1,5x, 2x e 3x, oculta até o script ver suporte; 1x escolhida.
    velocidades = re.search(r'(<div class="noticia-resumo__velocidades"[^>]*>)(.*?)</div>', bloco, re.DOTALL)
    assert velocidades.group(1) == ('<div class="noticia-resumo__velocidades" role="group" '
                                    'aria-labelledby="noticia-resumo-velocidade" data-resumo-velocidades hidden>')
    assert '<span id="noticia-resumo-velocidade" class="noticia-resumo__velocidade-rotulo">Velocidade</span>' in \
        velocidades.group(2)
    opcoes = re.findall(r'<button type="button" class="noticia-resumo__velocidade" data-velocidade="([^"]+)" '
                        r'aria-pressed="(true|false)">([^<]+)</button>', velocidades.group(2))
    assert opcoes == [("1", "true", "1x"), ("1.5", "false", "1,5x"), ("2", "false", "2x"), ("3", "false", "3x")]
    assert '<p class="noticia-resumo__aviso" data-resumo-aviso role="status"></p>' in bloco

    # CSS antes do botoes.css (que é quem estiliza o botão) e script no fim da página.
    folhas = re.findall(r'<link[^>]*href="(/assets/css/[^"?]+)', html)
    assert CSS in folhas and folhas.index(CSS) < folhas.index("/assets/css/botoes.css"), folhas
    assert re.search(rf'<script src="{JS}\?v=[^"]+"></script>\s*</body>', html)


def test_resumo_acompanha_a_ultima_atualizacao_da_noticia():
    paginas = _paginas_com_resumo()
    assert {path.parent.name for path in paginas} >= set(PILOTOS)
    falhas = []
    for path in paginas:
        falhas += falhas_de_atualizacao(path.parent.name, path.read_text(encoding="utf-8"))
    assert not falhas, "\n".join(falhas)


def test_atualizacao_nova_sem_revisar_o_resumo_e_apontada():
    # Simulação: a notícia do MAPA ganha atualização em 05/11/2026 às 09h00 (JSON-LD, meta e cartão) e o resumo fica.
    slug = "mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal"
    html = (NEWS_DIRECTORY / slug / "index.html").read_text(encoding="utf-8")
    atual = re.search(r'"dateModified": "([^"]+)"', html).group(1)
    novo = "2026-11-05T09:00:00-03:00"
    atualizada = (html.replace(f'"dateModified": "{atual}"', f'"dateModified": "{novo}"')
                  .replace(f'property="article:modified_time" content="{atual}"',
                           f'property="article:modified_time" content="{novo}"')
                  .replace(f'Atualizado em:</span> <time datetime="{atual}">',
                           f'Atualizado em:</span> <time datetime="{novo}">'))
    assert falhas_de_atualizacao(slug, html) == []
    falhas = falhas_de_atualizacao(slug, atualizada)
    assert len(falhas) == 1
    assert falhas[0].startswith(f"{slug}: o resumo foi conferido com a atualização de {atual}, mas a notícia foi "
                                f"atualizada em {novo}.")


def test_versao_falada_escreve_siglas_numeros_e_datas_por_extenso():
    falhas = []
    for path in _paginas_com_resumo():
        for leitura, titulo, texto in _itens(_resumo(path.read_text(encoding="utf-8"))):
            falhas += [f"{path.parent.name} / {titulo}: {falha}" for falha in falhas_da_leitura(titulo, texto, leitura)]
    assert not falhas, "\n".join(falhas)


def test_conferencia_da_versao_falada_aponta_o_que_falta():
    texto = "A RDC nº 1.046/2026 vale desde 03/11/2026, página 244."
    certa = ("O que mudou. A R D C número mil e quarenta e seis, de dois mil e vinte e seis, vale desde três de "
             "novembro de dois mil e vinte e seis, página duzentos e quarenta e quatro.")
    assert falhas_da_leitura("O que mudou", texto, certa) == []
    errada = "O que mudou. A RDC nº 1.046/2026 vale desde três de novembro."
    falhas = " | ".join(falhas_da_leitura("O que mudou", texto, errada))
    for parte in ("algarismo", "'nº'", "barra", "sigla colada", "falta a data 03/11/2026",
                  "falta o ato nº 1.046/2026", "falta o número 244"):
        assert parte in falhas, parte


def test_so_as_paginas_com_resumo_carregam_o_css_e_o_script():
    com_resumo = set(_paginas_com_resumo())
    for path in sorted(ROOT.rglob("*.html")):
        html = path.read_text(encoding="utf-8")
        carrega = CSS in html or JS in html
        relativo = path.relative_to(ROOT).as_posix()
        if path in com_resumo:
            assert CSS in html and JS in html, relativo
        else:
            assert not carrega, f"{relativo} carrega o resumo sem ter o bloco"
