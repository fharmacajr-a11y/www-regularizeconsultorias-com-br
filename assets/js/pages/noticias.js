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
   ================================================================= */
(function () {
  'use strict';

  var column = document.querySelector('aside .news-sidebar');
  var floating = document.querySelector('.floating-buttons');

  if (!column || !floating) return;

  var GAP = 16;

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

  // A rolagem é tratada no próprio evento, antes da pintura do quadro.
  window.addEventListener('scroll', update, { passive: true });
  window.addEventListener('resize', update);
  window.addEventListener('load', update);
  floating.addEventListener('focusin', update);
  // Na saída do foco o destino ainda não está focado: mede depois.
  floating.addEventListener('focusout', function () {
    window.setTimeout(update, 0);
  });

  // Filtros, busca e "Ver mais" mudam a altura da lista e movem a coluna.
  if ('ResizeObserver' in window) {
    new ResizeObserver(update).observe(document.body);
  }

  update();
})();
