/* =================================================================
   Resumo da notícia: botão "Ouvir resumo" (piloto de 04/11/2026)
   Lê em voz alta o resumo do topo da notícia com a síntese de voz do
   próprio navegador (speechSynthesis, da Web Speech API), em português do
   Brasil. Nada é enviado a serviço externo e nada é gravado.
   O texto falado vem de data-leitura: a versão do resumo escrita para ser
   ouvida, com as siglas soletradas e os números e datas por extenso
   ("R D C número mil e quarenta e seis, de dois mil e vinte e seis"). O
   texto visível não muda. tests/conteudo/test_noticias_resumo.py confere
   que a versão falada traz as mesmas datas e números do texto visível.
   - Sem suporte à síntese de voz, o botão e a velocidade continuam ocultos
     (hidden do HTML).
   - Cada frase vira uma fala: no Chrome, falas longas podem parar no meio.
   - Enquanto lê, o botão vira "Parar áudio" e o item lido fica destacado.
   - Velocidade: 1x, 1,5x, 2x e 3x (rate da fala). Trocar durante a leitura
     recomeça da frase em que estava, já na velocidade nova. A escolha fica
     guardada neste navegador (localStorage), se ele permitir.
   - Se o navegador não tocar (sem voz instalada ou erro), o botão volta a
     "Ouvir resumo" e um aviso diz que o resumo segue em texto.
   ================================================================= */
(function () {
  'use strict';

  var resumo = document.querySelector('[data-noticia-resumo]');
  if (!resumo) return;
  var botao = resumo.querySelector('[data-resumo-ouvir]');
  var rotulo = resumo.querySelector('[data-resumo-ouvir-rotulo]');
  var aviso = resumo.querySelector('[data-resumo-aviso]');
  var grupoVelocidade = resumo.querySelector('[data-resumo-velocidades]');
  var opcoesVelocidade = grupoVelocidade ? grupoVelocidade.querySelectorAll('[data-velocidade]') : [];
  if (!botao || !rotulo) return;

  var sintese = window.speechSynthesis;
  if (!sintese || typeof sintese.speak !== 'function' || typeof window.SpeechSynthesisUtterance !== 'function') return;

  var ROTULO_OUVIR = 'Ouvir resumo';
  var ROTULO_PARAR = 'Parar áudio';
  var AVISO_FALHA = 'Não foi possível tocar o áudio neste navegador. O resumo continua aqui, em texto.';
  var LIMITE_FALA = 180;
  var ESPERA_INICIO = 6000;
  var VELOCIDADES = [1, 1.5, 2, 3];
  var CHAVE_VELOCIDADE = 'rc-resumo-velocidade';
  var lendo = false;
  var sessao = 0;
  var vigia = null;
  var falaAtual = 0;
  var velocidade = lerVelocidade();

  function lerVelocidade() {
    try {
      var guardada = parseFloat(window.localStorage.getItem(CHAVE_VELOCIDADE));
      return VELOCIDADES.indexOf(guardada) >= 0 ? guardada : 1;
    } catch (erro) {
      return 1;
    }
  }

  function guardarVelocidade() {
    try {
      window.localStorage.setItem(CHAVE_VELOCIDADE, String(velocidade));
    } catch (erro) {
      // Sem armazenamento (janela privada ou dados bloqueados): a escolha vale só nesta página.
    }
  }

  function marcarVelocidade() {
    for (var i = 0; i < opcoesVelocidade.length; i++) {
      var valor = parseFloat(opcoesVelocidade[i].getAttribute('data-velocidade'));
      opcoesVelocidade[i].setAttribute('aria-pressed', valor === velocidade ? 'true' : 'false');
    }
  }

  function vozEmPortugues() {
    var vozes = typeof sintese.getVoices === 'function' ? sintese.getVoices() || [] : [];
    var brasil = null;
    var portugues = null;
    for (var i = 0; i < vozes.length; i++) {
      var idioma = String(vozes[i].lang || '').replace('_', '-').toLowerCase();
      if (!brasil && idioma === 'pt-br') brasil = vozes[i];
      if (!portugues && idioma.indexOf('pt') === 0) portugues = vozes[i];
    }
    return brasil || portugues;
  }

  // Junta pedaços (separados por espaço no texto original) em falas de até LIMITE_FALA caracteres.
  function juntar(pedacos) {
    var partes = [];
    var atual = '';
    pedacos.forEach(function (pedaco) {
      if (atual && (atual + ' ' + pedaco).length > LIMITE_FALA) {
        partes.push(atual);
        atual = pedaco;
      } else {
        atual = atual ? atual + ' ' + pedaco : pedaco;
      }
    });
    if (atual) partes.push(atual);
    return partes;
  }

  // Uma fala por frase; a frase longa é dividida nas vírgulas e, se ainda passar do limite, entre palavras.
  function dividir(texto) {
    var partes = [];
    (texto.match(/[^.!?]+[.!?]*/g) || [texto]).forEach(function (frase) {
      frase = frase.trim();
      if (!frase) return;
      if (frase.length <= LIMITE_FALA) {
        partes.push(frase);
        return;
      }
      var trechos = frase.split(/,\s+/).map(function (trecho, indice, todos) {
        return indice < todos.length - 1 ? trecho + ',' : trecho;
      });
      juntar(trechos).forEach(function (parte) {
        if (parte.length <= LIMITE_FALA) partes.push(parte);
        else partes.push.apply(partes, juntar(parte.split(/\s+/)));
      });
    });
    return partes;
  }

  function falas() {
    var lista = [];
    var nos = resumo.querySelectorAll('[data-leitura]');
    for (var i = 0; i < nos.length; i++) {
      var texto = String(nos[i].getAttribute('data-leitura') || '').replace(/\s+/g, ' ').trim();
      dividir(texto).forEach(function (parte) {
        lista.push({ no: nos[i], texto: parte });
      });
    }
    return lista;
  }

  function destacar(no) {
    var lidos = resumo.querySelectorAll('.is-lendo');
    for (var i = 0; i < lidos.length; i++) lidos[i].classList.remove('is-lendo');
    if (no && no.tagName === 'LI') no.classList.add('is-lendo');
  }

  // O aviso é uma região role="status" sempre presente (vazia, sem margem): o leitor de tela anuncia o texto novo.
  function avisar(texto) {
    if (aviso) aviso.textContent = texto;
  }

  function mostrarParado() {
    lendo = false;
    clearTimeout(vigia);
    destacar(null);
    botao.classList.remove('is-tocando');
    rotulo.textContent = ROTULO_OUVIR;
  }

  function parar() {
    sessao++;
    mostrarParado();
    sintese.cancel();
  }

  function falhar(daSessao) {
    if (daSessao !== sessao) return;
    parar();
    avisar(AVISO_FALHA);
  }

  // Lê da fala aPartirDe (0: do começo) até o fim, na velocidade escolhida.
  function ouvir(aPartirDe) {
    var lista = falas();
    var inicio = Math.min(aPartirDe || 0, lista.length - 1);
    if (!lista.length) return;
    sessao++;
    var daSessao = sessao;
    clearTimeout(vigia);
    if (sintese.speaking || sintese.pending) sintese.cancel();
    var voz = vozEmPortugues();
    var comecou = false;
    lendo = true;
    falaAtual = inicio;
    avisar('');
    botao.classList.add('is-tocando');
    rotulo.textContent = ROTULO_PARAR;

    lista.slice(inicio).forEach(function (item, posicao) {
      var indice = inicio + posicao;
      var fala = new window.SpeechSynthesisUtterance(item.texto);
      fala.lang = 'pt-BR';
      if (voz) fala.voice = voz;
      fala.rate = velocidade;
      fala.onstart = function () {
        if (daSessao !== sessao) return;
        comecou = true;
        falaAtual = indice;
        clearTimeout(vigia);
        destacar(item.no);
      };
      fala.onend = function () {
        if (daSessao === sessao && indice === lista.length - 1) mostrarParado();
      };
      fala.onerror = function (evento) {
        var erro = evento && evento.error;
        if (erro === 'interrupted' || erro === 'canceled') return;
        falhar(daSessao);
      };
      sintese.speak(fala);
    });
    if (sintese.paused && typeof sintese.resume === 'function') sintese.resume();

    // Sem voz instalada, alguns navegadores não começam a falar nem avisam erro.
    vigia = setTimeout(function () {
      if (!comecou && !sintese.speaking) falhar(daSessao);
    }, ESPERA_INICIO);
  }

  botao.addEventListener('click', function () {
    if (lendo) parar();
    else ouvir(0);
  });
  for (var i = 0; i < opcoesVelocidade.length; i++) {
    opcoesVelocidade[i].addEventListener('click', function (evento) {
      var escolhida = parseFloat(evento.currentTarget.getAttribute('data-velocidade'));
      if (VELOCIDADES.indexOf(escolhida) < 0 || escolhida === velocidade) return;
      velocidade = escolhida;
      marcarVelocidade();
      guardarVelocidade();
      if (lendo) ouvir(falaAtual);
    });
  }
  window.addEventListener('pagehide', function () {
    if (lendo) parar();
  });
  // No Chrome, a lista de vozes chega depois da carga; pedir agora adianta o carregamento.
  if (typeof sintese.getVoices === 'function') sintese.getVoices();
  marcarVelocidade();
  botao.hidden = false;
  if (grupoVelocidade) grupoVelocidade.hidden = false;
})();
