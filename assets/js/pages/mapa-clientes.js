/* ================================================================
   Mapa de clientes da home (01/11/2026)
   ----------------------------------------------------------------
   O Brasil por estado vem no HTML e funciona sem este script. Com ele:
   - passar o mouse num estado ou numa cidade mostra o nome e quantas
     cidades têm clientes; no toque, a dica aparece onde o dedo tocou;
   - tocar num estado (ou, com o foco no mapa, escolher pelas setas e
     apertar Enter) aproxima
     o mapa até ele e abre as cidades, lidas de
     /assets/data/mapa/uf-<código>.json, com as cidades com clientes em
     destaque; "‹ Brasil" (ou Esc) volta;
   - +, − e o botão de mapa inteiro; duplo clique ou duplo toque e pinça
     aproximam; com o mapa aproximado, arrastar move o mapa.
   Os números da legenda contam até o valor novo. Com movimento reduzido,
   tudo muda sem animação. Os dados são só cidade e estado.
   ================================================================ */
(function () {
  'use strict';

  var figura = document.querySelector('[data-mapa-clientes]');
  if (!figura || !window.fetch || !window.Promise || !window.requestAnimationFrame) return;

  var NS = 'http://www.w3.org/2000/svg';
  var ZOOM_MAXIMO = 10;
  var PASSO = 1.6;
  var calmo = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  /* Texto de ajuda conforme o aparelho: toque (celular, tablet) ou mouse. */
  var toque = window.matchMedia && window.matchMedia('(hover: none), (pointer: coarse)').matches;

  var svg = figura.querySelector('.home-hero-mapa__svg');
  var area = figura.querySelector('.home-hero-mapa__area');
  var brasil = figura.querySelector('.home-hero-mapa__brasil');
  var voltar = figura.querySelector('.home-hero-mapa__voltar');
  var titulo = figura.querySelector('.home-hero-mapa__titulo');
  var legenda = figura.querySelector('.home-hero-mapa__item');
  var status = figura.querySelector('.home-hero-mapa__status');
  var dica = figura.querySelector('.home-hero-mapa__dica');
  var caixaZoom = figura.querySelector('.home-hero-mapa__zoom');
  var numeroA = figura.querySelector('[data-mapa-numero="a"]');
  var numeroB = figura.querySelector('[data-mapa-numero="b"]');
  var rotuloA = figura.querySelector('[data-mapa-rotulo="a"]');
  var rotuloB = figura.querySelector('[data-mapa-rotulo="b"]');
  var versao = figura.getAttribute('data-versao') || '';

  var BRASIL = {
    titulo: titulo.textContent,
    legenda: legenda.textContent,
    status: toque
      ? 'Toque num estado para ver as cidades onde temos clientes.'
      : 'Clique num estado para ver as cidades onde temos clientes.',
    a: Number(numeroA.textContent),
    rotuloA: rotuloA.textContent,
    b: Number(numeroB.textContent),
    rotuloB: rotuloB.textContent
  };

  var vbBrasil = svg.getAttribute('viewBox').split(/\s+/).map(Number);
  var inteiro = vbBrasil.slice();
  var atual = vbBrasil.slice();
  var escala = 1;
  var grupoEstado = null;
  var cidadeAtiva = null;
  var cache = {};
  var pedido = 0;
  var animacao = 0;

  function plural(n, um, varios) {
    return n.toLocaleString('pt-BR') + ' ' + (n === 1 ? um : varios);
  }

  /* ---------- Enquadramento, zoom e animação ---------- */

  function aplicar() {
    svg.setAttribute('viewBox', atual.join(' '));
    var ampliado = escala > 1.001;
    figura.classList.toggle('home-hero-mapa--ampliado', ampliado);
    caixaZoom.querySelector('[data-mapa-zoom="mais"]').disabled = escala >= ZOOM_MAXIMO - 0.001;
  }

  /* A janela aproximada nunca sai do enquadramento de referência. */
  function limitar() {
    atual[2] = inteiro[2] / escala;
    atual[3] = inteiro[3] / escala;
    atual[0] = Math.min(Math.max(atual[0], inteiro[0]), inteiro[0] + inteiro[2] - atual[2]);
    atual[1] = Math.min(Math.max(atual[1], inteiro[1]), inteiro[1] + inteiro[3] - atual[3]);
  }

  function suave(t) {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  /* Leva o viewBox até "destino" em "ms" e chama "depois" no fim. */
  function animarPara(destino, ms, depois) {
    var meu = ++animacao;
    var inicio = atual.slice();
    if (calmo || !ms) {
      atual = destino.slice();
      svg.setAttribute('viewBox', atual.join(' '));
      if (depois) depois();
      return;
    }
    var t0 = null;
    function quadro(agora) {
      if (meu !== animacao) return;
      if (t0 === null) t0 = agora;
      var t = Math.min(1, (agora - t0) / ms);
      var k = suave(t);
      for (var i = 0; i < 4; i++) atual[i] = inicio[i] + (destino[i] - inicio[i]) * k;
      svg.setAttribute('viewBox', atual.join(' '));
      if (t < 1) requestAnimationFrame(quadro);
      else if (depois) depois();
    }
    requestAnimationFrame(quadro);
  }

  /* Aproxima (fator > 1) ou afasta mantendo o ponto (px, py) do viewBox
     parado na tela; sem ponto, usa o centro. */
  function aproximar(fator, px, py, ms) {
    var antes = atual.slice();
    if (px === undefined) {
      px = antes[0] + antes[2] / 2;
      py = antes[1] + antes[3] / 2;
    }
    var rx = (px - antes[0]) / antes[2];
    var ry = (py - antes[1]) / antes[3];
    escala = Math.min(ZOOM_MAXIMO, Math.max(1, escala * fator));
    var destino = [0, 0, inteiro[2] / escala, inteiro[3] / escala];
    destino[0] = px - rx * destino[2];
    destino[1] = py - ry * destino[3];
    var salvo = atual;
    atual = destino;
    limitar();
    destino = atual;
    atual = salvo;
    aplicar();
    animarPara(destino, ms === undefined ? 260 : ms);
  }

  function enquadrar(vb, ms, depois) {
    inteiro = vb.slice();
    escala = 1;
    aplicar();
    animarPara(vb, ms, depois);
  }

  /* Ponto da tela -> coordenadas do viewBox atual. */
  function noMapa(clientX, clientY) {
    var r = svg.getBoundingClientRect();
    return [atual[0] + (clientX - r.left) / r.width * atual[2], atual[1] + (clientY - r.top) / r.height * atual[3]];
  }

  /* ---------- Números da legenda ---------- */

  function contar(elemento, valor) {
    var de = Number(elemento.textContent.replace(/\D/g, '')) || 0;
    if (calmo || de === valor) {
      elemento.textContent = valor.toLocaleString('pt-BR');
      return;
    }
    var t0 = null;
    function quadro(agora) {
      if (t0 === null) t0 = agora;
      var t = Math.min(1, (agora - t0) / 500);
      elemento.textContent = Math.round(de + (valor - de) * suave(t)).toLocaleString('pt-BR');
      if (t < 1) requestAnimationFrame(quadro);
    }
    requestAnimationFrame(quadro);
  }

  function numeros(a, rotA, b, rotB) {
    contar(numeroA, a);
    contar(numeroB, b);
    rotuloA.textContent = rotA;
    rotuloB.textContent = rotB;
  }

  /* ---------- Dica ---------- */

  var dicaTimer = 0;

  function linha(tag, texto) {
    var elemento = document.createElement(tag);
    elemento.textContent = texto;
    return elemento;
  }

  function preencherDica(alvo) {
    while (dica.firstChild) dica.removeChild(dica.firstChild);
    if (alvo.hasAttribute('data-municipio')) {
      dica.appendChild(linha('strong', alvo.getAttribute('data-municipio')));
      if (alvo.hasAttribute('data-clientes')) dica.appendChild(linha('span', 'Cidade com clientes'));
      return;
    }
    var n = Number(alvo.getAttribute('data-clientes'));
    dica.appendChild(linha('strong', alvo.getAttribute('data-nome')));
    dica.appendChild(linha('span', n ? 'Clientes em ' + plural(n, 'cidade', 'cidades') : 'Sem clientes ainda'));
  }

  function mostrarDica(alvo, clientX, clientY, segundos) {
    clearTimeout(dicaTimer);
    preencherDica(alvo);
    dica.hidden = false;
    var r = area.getBoundingClientRect();
    var x = clientX - r.left;
    var y = clientY - r.top;
    var largura = dica.offsetWidth;
    var esquerda = Math.min(Math.max(x - largura / 2, 4), r.width - largura - 4);
    var topo = y - dica.offsetHeight - 14;
    if (topo < 4) topo = y + 18;
    dica.style.transform = 'translate(' + Math.round(esquerda) + 'px,' + Math.round(topo) + 'px)';
    if (segundos) dicaTimer = setTimeout(esconderDica, segundos * 1000);
  }

  function esconderDica() {
    clearTimeout(dicaTimer);
    dica.hidden = true;
  }

  /* ---------- Estados e cidades ---------- */

  function marcarCidade(caminho) {
    if (cidadeAtiva) cidadeAtiva.classList.remove('home-hero-mapa__municipio--ativo');
    cidadeAtiva = caminho;
    if (!caminho) return;
    caminho.classList.add('home-hero-mapa__municipio--ativo');
    var nome = caminho.getAttribute('data-municipio');
    status.textContent = caminho.hasAttribute('data-clientes')
      ? nome + ': cidade com clientes da Regularize.'
      : nome + ': ainda sem clientes nesta cidade.';
  }

  function fecharEstado() {
    if (grupoEstado) grupoEstado.parentNode.removeChild(grupoEstado);
    grupoEstado = null;
    cidadeAtiva = null;
  }

  /* Enquadramento quadrado com folga; a sobra horizontal fica mais à
     direita, onde ficam os botões de zoom. */
  function quadroDoEstado(vb) {
    var lado = Math.max(vb[2], vb[3]) * 1.06 / 0.86;
    var sobra = lado - vb[2];
    return [vb[0] - sobra * 0.3, vb[1] + vb[3] / 2 - lado / 2, lado, lado];
  }

  function desenharEstado(codigo, dados) {
    fecharEstado();
    var grupo = document.createElementNS(NS, 'g');
    grupo.setAttribute('class', 'home-hero-mapa__estado');
    var escalaIbge = document.createElementNS(NS, 'g');
    escalaIbge.setAttribute('transform', 'scale(0.0001,-0.0001)');
    var comClientes = [];
    dados.municipios.forEach(function (m) {
      var caminho = document.createElementNS(NS, 'path');
      caminho.setAttribute('d', m.d);
      caminho.setAttribute('class', 'home-hero-mapa__municipio' + (m.k ? ' home-hero-mapa__municipio--clientes' : ''));
      caminho.setAttribute('data-municipio', m.n);
      if (m.k) {
        caminho.setAttribute('data-clientes', '');
        comClientes.push(caminho);
      } else {
        escalaIbge.appendChild(caminho);
      }
    });
    /* As cidades com clientes por último: o contorno claro fica por cima. */
    comClientes.forEach(function (caminho) { escalaIbge.appendChild(caminho); });
    grupo.appendChild(escalaIbge);
    svg.appendChild(grupo);
    grupoEstado = grupo;
    brasil.style.display = 'none';

    figura.classList.add('home-hero-mapa--estado');
    voltar.hidden = false;
    titulo.textContent = dados.nome;
    legenda.textContent = 'Cidades com clientes';
    var ajuda = toque
      ? 'Toque numa cidade para ver o nome. Use dois dedos ou o + para aproximar.'
      : 'Passe o mouse numa cidade para ver o nome. Use o + ou dois cliques para aproximar.';
    status.textContent = dados.clientes ? ajuda : 'Ainda não temos clientes em ' + dados.nome + '. ' + ajuda;
    numeros(dados.clientes, dados.clientes === 1 ? 'cidade com clientes' : 'cidades com clientes',
      dados.municipios.length, 'cidades no estado');
  }

  function abrirEstado(codigo, caminhoEstado) {
    var meu = ++pedido;
    esconderDica();
    status.textContent = 'Carregando as cidades…';
    var dados = cache[codigo]
      ? Promise.resolve(cache[codigo])
      : fetch('/assets/data/mapa/uf-' + codigo + '.json' + (versao ? '?v=' + versao : ''))
        .then(function (resposta) {
          if (!resposta.ok) throw new Error('HTTP ' + resposta.status);
          return resposta.json();
        })
        .then(function (json) {
          cache[codigo] = json;
          return json;
        });

    /* Enquanto carrega, o mapa do Brasil voa até o estado tocado. */
    var voo = new Promise(function (pronto) {
      if (!caminhoEstado) return pronto();
      figura.classList.add('home-hero-mapa--voando');
      caminhoEstado.classList.add('home-hero-mapa__uf--escolhido');
      var caixa = caminhoEstado.getBBox();
      var vb = quadroDoEstado([caixa.x / 10000, -(caixa.y + caixa.height) / 10000, caixa.width / 10000, caixa.height / 10000]);
      escala = 1;
      animarPara(vb, 520, pronto);
    });

    Promise.all([dados, voo]).then(function (resultado) {
      if (meu !== pedido) return;
      if (caminhoEstado) caminhoEstado.classList.remove('home-hero-mapa__uf--escolhido');
      figura.classList.remove('home-hero-mapa--voando');
      var json = resultado[0];
      desenharEstado(codigo, json);
      var quadro = quadroDoEstado(json.viewBox);
      inteiro = quadro.slice();
      escala = 1;
      aplicar();
      animarPara(quadro, 200);
    }).catch(function () {
      if (meu !== pedido) return;
      figura.classList.remove('home-hero-mapa--voando');
      if (caminhoEstado) caminhoEstado.classList.remove('home-hero-mapa__uf--escolhido');
      status.textContent = 'Não foi possível carregar as cidades agora. Tente de novo em instantes.';
      enquadrar(vbBrasil, 300);
    });
  }

  function voltarAoBrasil() {
    pedido++;
    esconderDica();
    fecharEstado();
    brasil.style.display = '';
    figura.classList.remove('home-hero-mapa--estado');
    voltar.hidden = true;
    titulo.textContent = BRASIL.titulo;
    legenda.textContent = BRASIL.legenda;
    status.textContent = BRASIL.status;
    numeros(BRASIL.a, BRASIL.rotuloA, BRASIL.b, BRASIL.rotuloB);
    enquadrar(vbBrasil, 480);
  }

  /* ---------- Ponteiro: arrastar, pinça, dica e toque ---------- */

  var ponteiros = {};
  var gesto = null;
  var arrastou = false;
  var ultimoToque = 0;

  function quantos() {
    return Object.keys(ponteiros).length;
  }

  function iniciarGesto() {
    var ids = Object.keys(ponteiros);
    if (ids.length === 1) {
      var p = ponteiros[ids[0]];
      gesto = { tipo: 'arrastar', x: p.x, y: p.y, vx: atual[0], vy: atual[1] };
    } else if (ids.length >= 2) {
      var a = ponteiros[ids[0]];
      var b = ponteiros[ids[1]];
      gesto = {
        tipo: 'pinca',
        distancia: Math.hypot(a.x - b.x, a.y - b.y) || 1,
        escala: escala,
        centro: noMapa((a.x + b.x) / 2, (a.y + b.y) / 2)
      };
    }
  }

  svg.addEventListener('pointerdown', function (evento) {
    if (evento.button > 0) return;
    ponteiros[evento.pointerId] = { x: evento.clientX, y: evento.clientY };
    if (quantos() === 1) arrastou = false;
    iniciarGesto();
  });

  svg.addEventListener('pointermove', function (evento) {
    var p = ponteiros[evento.pointerId];
    if (!p) {
      if (evento.pointerType === 'mouse') {
        var alvo = evento.target.closest ? evento.target.closest('[data-codigo], [data-municipio]') : null;
        if (alvo) mostrarDica(alvo, evento.clientX, evento.clientY);
        else esconderDica();
      }
      return;
    }
    p.x = evento.clientX;
    p.y = evento.clientY;
    if (!gesto) return;
    if (gesto.tipo === 'pinca' && quantos() >= 2) {
      var ids = Object.keys(ponteiros);
      var a = ponteiros[ids[0]];
      var b = ponteiros[ids[1]];
      var fator = Math.hypot(a.x - b.x, a.y - b.y) / gesto.distancia;
      animacao++;
      var nova = Math.min(ZOOM_MAXIMO, Math.max(1, gesto.escala * fator));
      var r = svg.getBoundingClientRect();
      var cx = (a.x + b.x) / 2;
      var cy = (a.y + b.y) / 2;
      escala = nova;
      atual[2] = inteiro[2] / escala;
      atual[3] = inteiro[3] / escala;
      atual[0] = gesto.centro[0] - (cx - r.left) / r.width * atual[2];
      atual[1] = gesto.centro[1] - (cy - r.top) / r.height * atual[3];
      limitar();
      aplicar();
      arrastou = true;
      esconderDica();
      return;
    }
    if (gesto.tipo !== 'arrastar' || escala <= 1.001) return;
    var dx = evento.clientX - gesto.x;
    var dy = evento.clientY - gesto.y;
    if (!arrastou) {
      if (Math.abs(dx) + Math.abs(dy) < 5) return;
      arrastou = true;
      figura.classList.add('home-hero-mapa--arrastando');
      esconderDica();
      if (svg.setPointerCapture) svg.setPointerCapture(evento.pointerId);
    }
    animacao++;
    var unidade = atual[2] / (svg.getBoundingClientRect().width || 1);
    atual[0] = gesto.vx - dx * unidade;
    atual[1] = gesto.vy - dy * unidade;
    limitar();
    aplicar();
  });

  function soltar(evento) {
    if (!ponteiros[evento.pointerId]) return;
    delete ponteiros[evento.pointerId];
    if (quantos()) iniciarGesto();
    else {
      gesto = null;
      figura.classList.remove('home-hero-mapa--arrastando');
    }
  }

  svg.addEventListener('pointerup', soltar);
  svg.addEventListener('pointercancel', soltar);
  svg.addEventListener('pointerleave', function (evento) {
    if (evento.pointerType === 'mouse') esconderDica();
  });

  svg.addEventListener('click', function (evento) {
    if (arrastou) {
      arrastou = false;
      return;
    }
    var alvo = evento.target.closest ? evento.target.closest('[data-codigo], [data-municipio]') : null;
    if (!alvo) return;
    if (alvo.hasAttribute('data-municipio')) {
      marcarCidade(alvo);
      mostrarDica(alvo, evento.clientX, evento.clientY, 2.5);
    } else if (!grupoEstado) {
      abrirEstado(alvo.getAttribute('data-codigo'), alvo);
    }
  });

  /* Duplo clique ou duplo toque: aproxima no ponto, com o estado aberto. */
  svg.addEventListener('dblclick', function (evento) {
    if (!grupoEstado) return;
    evento.preventDefault();
    var ponto = noMapa(evento.clientX, evento.clientY);
    aproximar(PASSO * 1.25, ponto[0], ponto[1]);
  });

  /* ---------- Teclado e botões ---------- */

  /* O SVG é um ponto de foco só. No Brasil, as setas passam pelos estados
     com clientes (de oeste para leste) e Enter ou espaço abre o escolhido;
     com o estado aberto, as setas movem o mapa, + e − aproximam e Esc
     volta ao Brasil. */
  var estadosTeclado = [].slice.call(brasil.querySelectorAll('[data-codigo]'))
    .filter(function (caminho) { return Number(caminho.getAttribute('data-clientes')) > 0; })
    .sort(function (a, b) { return a.getBBox().x - b.getBBox().x; });
  var indiceTeclado = -1;

  function destacarEstado(indice) {
    var anterior = estadosTeclado[indiceTeclado];
    if (anterior) anterior.classList.remove('home-hero-mapa__uf--foco');
    indiceTeclado = (indice + estadosTeclado.length) % estadosTeclado.length;
    var caminho = estadosTeclado[indiceTeclado];
    caminho.classList.add('home-hero-mapa__uf--foco');
    var r = caminho.getBoundingClientRect();
    mostrarDica(caminho, r.left + r.width / 2, r.top + r.height / 2);
    var n = Number(caminho.getAttribute('data-clientes'));
    status.textContent = caminho.getAttribute('data-nome') + ': clientes em ' + plural(n, 'cidade', 'cidades') +
      '. Enter para ver as cidades.';
  }

  function limparDestaque() {
    var atualCaminho = estadosTeclado[indiceTeclado];
    if (atualCaminho) atualCaminho.classList.remove('home-hero-mapa__uf--foco');
    indiceTeclado = -1;
  }

  svg.setAttribute('tabindex', '0');
  svg.setAttribute('aria-describedby', 'home-hero-mapa-teclado');
  var ajudaTeclado = document.createElement('p');
  ajudaTeclado.id = 'home-hero-mapa-teclado';
  ajudaTeclado.className = 'sr-only';
  ajudaTeclado.textContent = 'Use as setas para escolher um estado e Enter para ver as cidades. Esc volta ao Brasil.';
  area.appendChild(ajudaTeclado);

  svg.addEventListener('keydown', function (evento) {
    var tecla = evento.key;
    if (!grupoEstado) {
      if (tecla === 'ArrowRight' || tecla === 'ArrowDown') destacarEstado(indiceTeclado + 1);
      else if (tecla === 'ArrowLeft' || tecla === 'ArrowUp') destacarEstado(indiceTeclado < 0 ? -1 : indiceTeclado - 1);
      else if ((tecla === 'Enter' || tecla === ' ') && estadosTeclado.length) {
        var caminho = estadosTeclado[indiceTeclado < 0 ? 0 : indiceTeclado];
        limparDestaque();
        abrirEstado(caminho.getAttribute('data-codigo'), caminho);
      } else return;
      evento.preventDefault();
      return;
    }
    var passo = atual[2] * 0.15;
    if (tecla === 'ArrowRight') atual[0] += passo;
    else if (tecla === 'ArrowLeft') atual[0] -= passo;
    else if (tecla === 'ArrowDown') atual[1] += passo;
    else if (tecla === 'ArrowUp') atual[1] -= passo;
    else if (tecla === '+' || tecla === '=') { aproximar(PASSO); evento.preventDefault(); return; }
    else if (tecla === '-') { aproximar(1 / PASSO); evento.preventDefault(); return; }
    else return;
    evento.preventDefault();
    animacao++;
    limitar();
    aplicar();
  });

  svg.addEventListener('blur', function () {
    limparDestaque();
    esconderDica();
  });

  figura.addEventListener('keydown', function (evento) {
    if (evento.key === 'Escape' && grupoEstado) {
      voltarAoBrasil();
      svg.focus();
    }
  });

  caixaZoom.addEventListener('click', function (evento) {
    var botao = evento.target.closest('[data-mapa-zoom]');
    if (!botao || botao.disabled) return;
    var tipo = botao.getAttribute('data-mapa-zoom');
    if (tipo === 'mais') aproximar(PASSO);
    else if (tipo === 'menos') aproximar(1 / PASSO);
    else enquadrar(inteiro, 320);
  });

  voltar.addEventListener('click', voltarAoBrasil);

  figura.classList.add('home-hero-mapa--interativo');
  caixaZoom.hidden = false;
  status.textContent = BRASIL.status;
  aplicar();
})();
