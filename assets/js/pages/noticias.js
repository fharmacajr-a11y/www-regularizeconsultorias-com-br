/* =================================================================
   Notícias: controles flutuantes recolhidos sobre a coluna lateral
   Abaixo de 1024 px a coluna lateral (pesquisa, categorias, ordenação e
   atendimento) vem depois da lista, na largura toda do miolo, e a coluna
   fixa de voltar ao topo e WhatsApp cobriria a borda direita dela, onde
   ficam as contagens das categorias. Enquanto as duas se cruzam (com 1rem
   de folga), a coluna fixa recebe o atributo inert e os botões recolhem
   (pages/noticias.css); ao sair, voltam. No desktop a lateral fica à
   esquerda e nunca cruza a coluna fixa.
   Recolher muda só opacidade e visibilidade: a caixa da coluna fixa
   continua no mesmo lugar, então a medida não depende do próprio estado e
   não há ida e volta na borda. Com inert, os botões saem da ordem do Tab e
   o navegador tira deles o foco de mouse deixado por um clique. Um botão
   com foco de teclado não some.
   A medida vem depois do main.js, que reposiciona a coluna fixa (ancorada
   ou não acima dos créditos do rodapé) num requestAnimationFrame. Medida no
   próprio evento de rolagem, ela lia a posição do quadro anterior: num salto
   do rodapé até a lateral, a coluna ainda ancorada parecia longe dela.
   ================================================================= */
(function () {
  'use strict';

  var column = document.querySelector('aside .news-sidebar');
  var floating = document.querySelector('.floating-buttons');

  if (!column || !floating) return;

  var GAP = 16;
  var frame = 0;

  var keyboardFocusInside = function () {
    var active = document.activeElement;

    if (!active || !floating.contains(active)) return false;
    try {
      return active.matches(':focus-visible');
    } catch (error) {
      return true;
    }
  };

  var update = function () {
    var area = column.getBoundingClientRect();
    var group = floating.getBoundingClientRect();
    var crossing = area.height > 0 &&
      area.left < group.right + GAP && area.right > group.left - GAP &&
      area.top < group.bottom + GAP && area.bottom > group.top - GAP;

    floating.toggleAttribute('inert', crossing && !keyboardFocusInside());
  };

  // Uma medida por quadro, só quando algum evento pede. Os ouvintes do
  // main.js foram registrados antes (o script dele carrega primeiro), e os
  // pedidos de quadro rodam na ordem em que foram feitos: o reposicionamento
  // dele vem antes desta medida, ainda antes da pintura.
  var requestUpdate = function () {
    if (!frame) {
      frame = window.requestAnimationFrame(function () {
        frame = 0;
        update();
      });
    }
  };

  window.addEventListener('scroll', requestUpdate, { passive: true });
  window.addEventListener('resize', requestUpdate);
  window.addEventListener('load', requestUpdate);
  floating.addEventListener('focusin', requestUpdate);
  // Na saída do foco o destino ainda não está focado; no quadro, já está.
  floating.addEventListener('focusout', requestUpdate);

  // Filtros, busca e "Ver mais" mudam a altura da lista e movem a coluna. O
  // observador do main.js, criado antes, já reposicionou a coluna fixa neste
  // mesmo ciclo; a medida vem na hora, sem esperar outro quadro.
  if ('ResizeObserver' in window) {
    new ResizeObserver(update).observe(document.body);
  }

  update();
})();
