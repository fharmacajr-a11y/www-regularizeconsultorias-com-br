/* ================================================================
   Mapa de clientes da home (01/11/2026)
   ----------------------------------------------------------------
   O Brasil por estado vem no HTML e funciona sem este script. Com ele:
   - tocar num estado (ou escolher no select) abre as cidades do estado,
     lidas de /assets/data/mapa/uf-<código>.json, com as cidades com
     clientes em destaque; tocar numa cidade mostra o nome dela;
   - os botões + e − aproximam e afastam, e o terceiro volta ao mapa
     inteiro; com o mapa aproximado, arrastar move o mapa;
   - "‹ Brasil" volta aos estados.
   Os dados do mapa são só cidade e estado (nada de nome de cliente).
   ================================================================ */
(function () {
  'use strict';

  var figura = document.querySelector('[data-mapa-clientes]');
  if (!figura || !window.fetch || !window.Promise) return;

  var NS = 'http://www.w3.org/2000/svg';
  var ZOOM_MAXIMO = 8;
  var PASSO = 1.6;

  var svg = figura.querySelector('.home-hero-mapa__svg');
  var brasil = figura.querySelector('.home-hero-mapa__brasil');
  var voltar = figura.querySelector('.home-hero-mapa__voltar');
  var titulo = figura.querySelector('.home-hero-mapa__titulo');
  var legenda = figura.querySelector('.home-hero-mapa__item');
  var status = figura.querySelector('.home-hero-mapa__status');
  var caixaZoom = figura.querySelector('.home-hero-mapa__zoom');
  var escolha = figura.querySelector('.home-hero-mapa__escolha');
  var select = escolha.querySelector('select');
  var botaoMais = caixaZoom.querySelector('[data-mapa-zoom="mais"]');
  var botaoMenos = caixaZoom.querySelector('[data-mapa-zoom="menos"]');
  var botaoInteiro = caixaZoom.querySelector('[data-mapa-zoom="inteiro"]');
  var versao = figura.getAttribute('data-versao') || '';

  var TITULO_BRASIL = titulo.textContent;
  var LEGENDA_BRASIL = legenda.textContent;
  var STATUS_BRASIL = 'Toque num estado para ver as cidades onde temos clientes.';

  var vbBrasil = svg.getAttribute('viewBox').split(/\s+/).map(Number);
  var inteiro = vbBrasil.slice();
  var atual = vbBrasil.slice();
  var escala = 1;
  var grupoEstado = null;
  var cidadeAtiva = null;
  var cache = {};
  var pedido = 0;

  function plural(n, um, varios) {
    return n + ' ' + (n === 1 ? um : varios);
  }

  function aplicar() {
    svg.setAttribute('viewBox', atual.join(' '));
    var ampliado = escala > 1.001;
    figura.classList.toggle('home-hero-mapa--ampliado', ampliado);
    botaoMenos.disabled = !ampliado;
    botaoInteiro.disabled = !ampliado;
    botaoMais.disabled = escala >= ZOOM_MAXIMO - 0.001;
  }

  /* A janela aproximada nunca sai do enquadramento de referência. */
  function limitar() {
    atual[2] = inteiro[2] / escala;
    atual[3] = inteiro[3] / escala;
    atual[0] = Math.min(Math.max(atual[0], inteiro[0]), inteiro[0] + inteiro[2] - atual[2]);
    atual[1] = Math.min(Math.max(atual[1], inteiro[1]), inteiro[1] + inteiro[3] - atual[3]);
  }

  function aproximar(fator) {
    var cx = atual[0] + atual[2] / 2;
    var cy = atual[1] + atual[3] / 2;
    escala = Math.min(ZOOM_MAXIMO, Math.max(1, escala * fator));
    atual[0] = cx - inteiro[2] / escala / 2;
    atual[1] = cy - inteiro[3] / escala / 2;
    limitar();
    aplicar();
  }

  function enquadrar(vb) {
    inteiro = vb.slice();
    atual = vb.slice();
    escala = 1;
    aplicar();
  }

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

  function textoEstado(dados) {
    return dados.clientes
      ? dados.nome + ': clientes em ' + plural(dados.clientes, 'cidade', 'cidades') + '. Toque numa cidade ou use o +.'
      : dados.nome + ': nenhuma cidade com clientes ainda. Toque numa cidade ou use o +.';
  }

  function fecharEstado() {
    if (grupoEstado) grupoEstado.parentNode.removeChild(grupoEstado);
    grupoEstado = null;
    cidadeAtiva = null;
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
      if (m.k) caminho.setAttribute('data-clientes', '');
      var dica = document.createElementNS(NS, 'title');
      dica.textContent = m.n + (m.k ? ': cidade com clientes' : '');
      caminho.appendChild(dica);
      /* As cidades com clientes por último: o contorno claro fica por cima. */
      if (m.k) comClientes.push(caminho);
      else escalaIbge.appendChild(caminho);
    });
    comClientes.forEach(function (caminho) { escalaIbge.appendChild(caminho); });
    grupo.appendChild(escalaIbge);
    svg.appendChild(grupo);
    grupoEstado = grupo;

    brasil.style.display = 'none';
    figura.classList.add('home-hero-mapa--estado');
    voltar.hidden = false;
    titulo.textContent = dados.nome;
    legenda.textContent = 'Cidades com clientes';
    status.textContent = textoEstado(dados);
    select.value = codigo;

    /* Enquadramento quadrado com folga; a sobra horizontal fica mais à
       direita, onde ficam os botões de zoom, para eles não cobrirem o
       estado inteiro na primeira vista. */
    var vb = dados.viewBox;
    var lado = Math.max(vb[2], vb[3]) * 1.06 / 0.86;
    var sobra = lado - vb[2];
    enquadrar([vb[0] - sobra * 0.3, vb[1] + vb[3] / 2 - lado / 2, lado, lado]);
  }

  function abrirEstado(codigo) {
    var meu = ++pedido;
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
    dados.then(function (json) {
      if (meu === pedido) desenharEstado(codigo, json);
    }).catch(function () {
      if (meu === pedido) status.textContent = 'Não foi possível carregar as cidades agora. Tente de novo em instantes.';
    });
  }

  function voltarAoBrasil() {
    pedido++;
    fecharEstado();
    brasil.style.display = '';
    figura.classList.remove('home-hero-mapa--estado');
    voltar.hidden = true;
    titulo.textContent = TITULO_BRASIL;
    legenda.textContent = LEGENDA_BRASIL;
    status.textContent = STATUS_BRASIL;
    select.value = '';
    enquadrar(vbBrasil);
  }

  /* Arrastar: só com o mapa aproximado. Um toque sem movimento continua
     sendo um clique no estado ou na cidade. */
  var arrasto = null;
  var arrastou = false;

  svg.addEventListener('pointerdown', function (evento) {
    if (escala <= 1.001 || evento.button > 0) return;
    arrasto = { id: evento.pointerId, x: evento.clientX, y: evento.clientY, vx: atual[0], vy: atual[1] };
    arrastou = false;
  });

  svg.addEventListener('pointermove', function (evento) {
    if (!arrasto || evento.pointerId !== arrasto.id) return;
    var dx = evento.clientX - arrasto.x;
    var dy = evento.clientY - arrasto.y;
    if (!arrastou) {
      if (Math.abs(dx) + Math.abs(dy) < 5) return;
      arrastou = true;
      figura.classList.add('home-hero-mapa--arrastando');
      if (svg.setPointerCapture) svg.setPointerCapture(evento.pointerId);
    }
    var unidade = atual[2] / (svg.getBoundingClientRect().width || 1);
    atual[0] = arrasto.vx - dx * unidade;
    atual[1] = arrasto.vy - dy * unidade;
    limitar();
    aplicar();
  });

  function soltar(evento) {
    if (!arrasto || evento.pointerId !== arrasto.id) return;
    arrasto = null;
    figura.classList.remove('home-hero-mapa--arrastando');
  }

  svg.addEventListener('pointerup', soltar);
  svg.addEventListener('pointercancel', soltar);

  svg.addEventListener('click', function (evento) {
    if (arrastou) {
      arrastou = false;
      return;
    }
    var alvo = evento.target.closest ? evento.target.closest('[data-codigo], [data-municipio]') : null;
    if (!alvo) return;
    if (alvo.hasAttribute('data-municipio')) marcarCidade(alvo);
    else if (!grupoEstado) abrirEstado(alvo.getAttribute('data-codigo'));
  });

  botaoMais.addEventListener('click', function () { aproximar(PASSO); });
  botaoMenos.addEventListener('click', function () { aproximar(1 / PASSO); });
  botaoInteiro.addEventListener('click', function () { enquadrar(inteiro); });

  voltar.addEventListener('click', function () {
    voltarAoBrasil();
    select.focus();
  });

  select.addEventListener('change', function () {
    if (select.value) abrirEstado(select.value);
    else voltarAoBrasil();
  });

  figura.classList.add('home-hero-mapa--interativo');
  caixaZoom.hidden = false;
  escolha.hidden = false;
  status.textContent = STATUS_BRASIL;
  aplicar();
})();
