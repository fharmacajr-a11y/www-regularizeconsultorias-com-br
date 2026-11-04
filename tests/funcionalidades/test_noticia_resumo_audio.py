"""Botão "Ouvir resumo" das notícias no navegador (piloto de 04/11/2026).

assets/js/pages/noticia-resumo.js lê o resumo do topo da notícia com a síntese de voz do navegador. O Chromium dos
testes não tem voz instalada, então a síntese é trocada, antes da carga, por uma imitação que registra as falas e
deixa o teste disparar o início, o fim e o erro de cada uma. O teste confere, em 390x844 com toque:
- com suporte, o botão aparece; o clique enfileira, em pt-BR e com a voz pt-BR da lista, o texto de data-leitura
  (título e três itens, nessa ordem), em falas de até 180 caracteres; o botão vira "Parar áudio" e o item lido
  fica destacado; no fim da última fala, volta a "Ouvir resumo";
- "Parar áudio" cancela a síntese e devolve o botão;
- velocidade (pedido do Jr em 04/11/2026): 1x de saída; 2x antes de ouvir vale para todas as falas; 3x durante a
  leitura recomeça da fala em que estava, já em 3x; a escolha fica guardada e volta ao reabrir a página;
- num erro da síntese, o botão volta e o aviso (role="status") diz que o resumo segue em texto;
- sem a síntese de voz (speechSynthesis ausente), o botão e a velocidade continuam ocultos e nada quebra.

Roda num subprocesso, como os outros testes de navegador: o Playwright síncrono não abre uma segunda sessão no
mesmo processo enquanto a da consulta do Farmácia Popular (fixture de sessão) está aberta.
"""
import json
import subprocess
import sys
import threading
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

import pytest

from support import SITE_DIR, subprocess_env


PILOTOS = (
    "/noticias/rdc-1000-2025-anvisa-prorroga-prazo-sncr/",
    "/noticias/anvisa-suspende-medicamento-proibe-produtos-irregulares/",
    "/noticias/mapa-portaria-1617-2026-aditivos-antimicrobianos-alimentacao-animal/",
)

PROBE = r'''
import json
import sys

from playwright.sync_api import sync_playwright

import support

base, rotas = sys.argv[1], json.loads(sys.argv[2])
SINTESE_IMITADA = """
(() => {
  const registro = { falas: [], canceladas: 0 };
  const sintese = {
    speaking: false, pending: false, paused: false,
    getVoices: () => [{ lang: 'en-US', name: 'Inglês' }, { lang: 'pt_BR', name: 'Português do Brasil' }],
    speak(fala) { registro.falas.push(fala); this.pending = true; },
    cancel() { registro.canceladas++; registro.falas = []; this.speaking = false; this.pending = false; },
    resume() {},
    addEventListener() {},
  };
  Object.defineProperty(window, 'speechSynthesis', { value: sintese, configurable: true });
  window.SpeechSynthesisUtterance = function (texto) { this.text = texto; };
  window.__sintese = registro;
  window.__falar = (indice, evento) => {
    const fala = registro.falas[indice];
    if (evento === 'inicio') { sintese.speaking = true; fala.onstart && fala.onstart({}); }
    if (evento === 'fim') { fala.onend && fala.onend({}); }
    if (evento === 'erro') { fala.onerror && fala.onerror({ error: 'synthesis-failed' }); }
  };
})();
"""
SEM_SINTESE = "Object.defineProperty(window, 'speechSynthesis', { value: undefined, configurable: true });"
ESTADO = """() => {
  const botao = document.querySelector('[data-resumo-ouvir]');
  const r = botao.getBoundingClientRect();
  return {
    visivel: !botao.hidden && getComputedStyle(botao).display !== 'none' && r.width > 0 && r.height > 0,
    atributoHidden: botao.hasAttribute('hidden'),
    rotulo: botao.innerText.trim(),
    tocando: botao.classList.contains('is-tocando'),
    destacados: [...document.querySelectorAll('[data-noticia-resumo] .is-lendo')].map(
      n => n.tagName + ':' + ((n.querySelector('.noticia-resumo__item-titulo') || {}).textContent || '')),
    aviso: document.querySelector('[data-resumo-aviso]').textContent,
    avisoRole: document.querySelector('[data-resumo-aviso]').getAttribute('role'),
    canceladas: window.__sintese ? window.__sintese.canceladas : null,
    velocidadeVisivel: !document.querySelector('[data-resumo-velocidades]').hidden,
    velocidades: [...document.querySelectorAll('[data-velocidade]')].map(
      b => b.textContent + (b.getAttribute('aria-pressed') === 'true' ? '*' : '')),
  };
}"""
FALAS = ("() => window.__sintese.falas.map(f => ({texto: f.text, idioma: f.lang, voz: f.voice && f.voice.name, "
         "ritmo: f.rate}))")
LEITURAS = "() => [...document.querySelectorAll('[data-noticia-resumo] [data-leitura]')].map(n => n.dataset.leitura)"

saida = {}
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(headless=True)

    def abrir(rota, script):
        context = support.new_context(browser, viewport={"width": 390, "height": 844}, has_touch=True, is_mobile=True)
        context.add_init_script(script)
        page = context.new_page()
        erros = []
        page.on("pageerror", lambda erro: erros.append(str(erro)))
        page.goto(base + rota, wait_until="load")
        return context, page, erros

    for rota in rotas:
        r = saida.setdefault(rota, {})
        # Leitura completa.
        context, page, erros = abrir(rota, SINTESE_IMITADA)
        r["antes"] = page.evaluate(ESTADO)
        page.locator("[data-resumo-ouvir]").click()
        r["falas"] = page.evaluate(FALAS)
        r["leituras"] = page.evaluate(LEITURAS)
        r["tocando"] = page.evaluate(ESTADO)
        primeira = next((i for i, fala in enumerate(r["falas"]) if fala["texto"].startswith("O que mudou.")), 0)
        page.evaluate(f"window.__falar({primeira}, 'inicio')")
        r["no_primeiro_item"] = page.evaluate(ESTADO)
        page.evaluate(f"window.__falar({len(r['falas']) - 1}, 'fim')")
        r["no_fim"] = page.evaluate(ESTADO)
        r["erros_leitura"] = erros
        context.close()

        # Velocidade: 2x antes de ouvir, 3x no meio da leitura e a escolha guardada.
        context, page, erros = abrir(rota, SINTESE_IMITADA)
        page.locator('[data-velocidade="2"]').click()
        r["vel_2x"] = page.evaluate(ESTADO)
        page.locator("[data-resumo-ouvir]").click()
        r["falas_2x"] = page.evaluate(FALAS)
        page.evaluate("window.__falar(3, 'inicio')")
        canceladas = page.evaluate("window.__sintese.canceladas")
        page.locator('[data-velocidade="3"]').click()
        r["falas_3x"] = page.evaluate(FALAS)
        r["vel_3x"] = page.evaluate(ESTADO)
        r["canceladas_na_troca"] = page.evaluate("window.__sintese.canceladas") - canceladas
        page.reload(wait_until="load")
        r["vel_ao_reabrir"] = page.evaluate(ESTADO)
        r["erros_velocidade"] = erros
        context.close()

        # Parar no meio.
        context, page, erros = abrir(rota, SINTESE_IMITADA)
        page.locator("[data-resumo-ouvir]").click()
        page.evaluate("window.__falar(0, 'inicio')")
        r["antes_de_parar"] = page.evaluate(ESTADO)
        page.locator("[data-resumo-ouvir]").click()
        r["parado"] = page.evaluate(ESTADO)
        r["erros_parar"] = erros
        context.close()

        # Erro da síntese.
        context, page, erros = abrir(rota, SINTESE_IMITADA)
        page.locator("[data-resumo-ouvir]").click()
        page.evaluate("window.__falar(0, 'erro')")
        r["com_erro"] = page.evaluate(ESTADO)
        r["erros_falha"] = erros
        context.close()

        # Sem síntese de voz.
        context, page, erros = abrir(rota, SEM_SINTESE)
        r["sem_sintese"] = page.evaluate(ESTADO)
        r["sem_sintese_api"] = page.evaluate("typeof window.speechSynthesis")
        r["resumo_visivel_sem_sintese"] = page.locator("[data-noticia-resumo]").is_visible()
        r["erros_sem_sintese"] = erros
        context.close()
    browser.close()
print(json.dumps(saida, ensure_ascii=False))
'''


class _QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, _format, *_args):
        pass


@pytest.fixture(scope="module")
def resultados():
    server = ThreadingHTTPServer(("127.0.0.1", 0), partial(_QuietHandler, directory=str(SITE_DIR)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        completed = subprocess.run(
            [sys.executable, "-c", PROBE, f"http://127.0.0.1:{server.server_port}", json.dumps(PILOTOS)],
            capture_output=True, text=True, encoding="utf-8", timeout=180, env=subprocess_env(),
        )
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert completed.returncode == 0, completed.stderr[-3000:]
    return json.loads(completed.stdout.strip().splitlines()[-1])


@pytest.mark.parametrize("rota", PILOTOS)
def test_ouvir_resumo_le_a_versao_falada_em_portugues(resultados, rota):
    r = resultados[rota]
    assert r["antes"]["visivel"] and r["antes"]["rotulo"] == "Ouvir resumo" and not r["antes"]["tocando"]
    assert r["antes"]["velocidadeVisivel"] and r["antes"]["velocidades"] == ["1x*", "1,5x", "2x", "3x"]

    falas, leituras = r["falas"], r["leituras"]
    assert len(leituras) == 4 and leituras[0] == "Resumo da notícia."
    assert [leitura.split(".", 1)[0] for leitura in leituras[1:3]] == ["O que mudou", "Desde quando"]
    assert " ".join(fala["texto"] for fala in falas) == " ".join(" ".join(leitura.split()) for leitura in leituras)
    assert all(len(fala["texto"]) <= 180 for fala in falas), [len(fala["texto"]) for fala in falas]
    assert {fala["idioma"] for fala in falas} == {"pt-BR"}
    assert {fala["voz"] for fala in falas} == {"Português do Brasil"}
    assert {fala["ritmo"] for fala in falas} == {1}

    assert r["tocando"]["rotulo"] == "Parar áudio" and r["tocando"]["tocando"]
    # O destaque acompanha a fala: a primeira fala do 1º item destaca o 1º item, e só ele.
    assert r["no_primeiro_item"]["destacados"] == ["LI:O que mudou"]
    assert r["no_fim"]["rotulo"] == "Ouvir resumo" and not r["no_fim"]["tocando"]
    assert r["no_fim"]["destacados"] == []
    assert not r["erros_leitura"], r["erros_leitura"]


@pytest.mark.parametrize("rota", PILOTOS)
def test_velocidade_vale_para_a_leitura_e_fica_guardada(resultados, rota):
    r = resultados[rota]
    assert r["vel_2x"]["velocidades"] == ["1x", "1,5x", "2x*", "3x"]
    assert {fala["ritmo"] for fala in r["falas_2x"]} == {2}
    # Troca no meio: cancela e recomeça da 4ª fala (a que estava tocando), em 3x, até o fim.
    assert r["canceladas_na_troca"] == 1
    assert [fala["texto"] for fala in r["falas_3x"]] == [fala["texto"] for fala in r["falas_2x"]][3:]
    assert {fala["ritmo"] for fala in r["falas_3x"]} == {3}
    assert r["vel_3x"]["velocidades"] == ["1x", "1,5x", "2x", "3x*"] and r["vel_3x"]["rotulo"] == "Parar áudio"
    assert r["vel_ao_reabrir"]["velocidades"] == ["1x", "1,5x", "2x", "3x*"]
    assert not r["erros_velocidade"], r["erros_velocidade"]


@pytest.mark.parametrize("rota", PILOTOS)
def test_parar_audio_cancela_a_leitura(resultados, rota):
    r = resultados[rota]
    assert r["antes_de_parar"]["rotulo"] == "Parar áudio"
    assert r["parado"]["canceladas"] == r["antes_de_parar"]["canceladas"] + 1
    assert r["parado"]["rotulo"] == "Ouvir resumo" and not r["parado"]["tocando"]
    assert r["parado"]["destacados"] == [] and r["parado"]["aviso"] == ""
    assert not r["erros_parar"], r["erros_parar"]


@pytest.mark.parametrize("rota", PILOTOS)
def test_erro_da_sintese_devolve_o_botao_e_avisa(resultados, rota):
    r = resultados[rota]["com_erro"]
    assert r["rotulo"] == "Ouvir resumo" and not r["tocando"]
    assert r["avisoRole"] == "status"
    assert r["aviso"] == "Não foi possível tocar o áudio neste navegador. O resumo continua aqui, em texto."
    assert not resultados[rota]["erros_falha"], resultados[rota]["erros_falha"]


@pytest.mark.parametrize("rota", PILOTOS)
def test_sem_sintese_de_voz_o_botao_fica_oculto(resultados, rota):
    r = resultados[rota]
    assert r["sem_sintese_api"] == "undefined"
    assert r["resumo_visivel_sem_sintese"]
    assert not r["sem_sintese"]["visivel"] and r["sem_sintese"]["atributoHidden"]
    assert not r["sem_sintese"]["velocidadeVisivel"]
    assert not r["erros_sem_sintese"], r["erros_sem_sintese"]
