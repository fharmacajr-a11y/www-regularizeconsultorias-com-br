/* =================================================================
   Notícias: faixa de filtros abaixo de 1024 px e "Ver mais notícias"
   Abaixo de 1024 px a coluna de filtros (pesquisa e faixa de categorias e
   ordenação, pages/noticias.css) vem antes da lista, como no HTML.
   1. Botão focado inteiro na faixa. O Chromium só rola a faixa até o botão
      focado quando ele está todo fora dela: um botão cortado pela borda, sob
      o esmaecido, ficava como estava. Com nearest e o scroll-padding-inline
      da faixa (ou do carrossel, com mouse), ele aparece inteiro, antes do
      esmaecido e das setas.
   2. Resultado do filtro à vista. Com a faixa no pé da janela, uma categoria
      ou a ordenação mudava a lista abaixo da dobra, sem nada à vista. Depois
      do clique (pelo mouse, pelo toque ou por Enter e Espaço), se o topo do
      1º card não aparece na janela, a página rola de uma vez até a faixa
      ficar logo abaixo do cabeçalho (o scroll-padding-top do html), com o 1º
      card logo depois dela. O foco continua no botão usado. O ouvinte fica na
      faixa e recebe o clique depois do ouvinte do próprio botão no main.js,
      que já atualizou a lista.
   3. Carrossel das categorias com mouse (desde 23/10/2026). Com hover e
      ponteiro fino, abaixo de 1024 px, as categorias rolam na horizontal
      dentro de .news-filters__carousel. Cada seta aparece só quando há
      categorias escondidas daquele lado e rola cerca de 80% da largura
      visível (de uma vez com movimento reduzido). As setas ficam fora do Tab
      (tabindex="-1" e aria-hidden="true") e não tomam o foco no clique. Os
      atributos data-more-start e data-more-end põem o esmaecido só do lado
      que tem categorias escondidas. Com toque, as setas não aparecem.
   4. Contagem do "Ver mais notícias": quantas notícias do resultado ainda
      não aparecem (o total de #news-result-count menos os cards à vista),
      recalculada sempre que o main.js atualiza a lista.
   A partir de 1024 px a faixa não rola, a lista fica ao lado da coluna e
   nada muda. Sem JavaScript a faixa continua visível e rola pelo dedo.
   Até 21/10/2026 este arquivo recolhia voltar ao topo e WhatsApp enquanto
   eles passavam pela coluna, que vinha depois da lista. Agora a pesquisa e a
   faixa reservam a faixa da coluna fixa e os botões não recolhem.
   ================================================================= */
(function () {
  'use strict';

  var column = document.querySelector('main aside');
  var filters = document.querySelector('.news-filters');
  var strip = document.querySelector('.news-filters__strip');
  var list = document.getElementById('news-article-list');
  var navbar = document.getElementById('navbar');

  if (!column || !filters || !strip || !list) return;

  var carousel = filters.querySelector('.news-filters__carousel');
  var categories = carousel ? carousel.querySelector('.news-filters__categories') : null;

  var overflows = function (element) {
    return !!element && element.scrollWidth > element.clientWidth;
  };

  strip.addEventListener('focusin', function (event) {
    if (overflows(strip) || overflows(categories)) {
      event.target.scrollIntoView({ block: 'nearest', inline: 'nearest', behavior: 'instant' });
    }
  });

  // Quanto do 1º card precisa aparecer acima do fim da janela: a linha de
  // selos e data e o começo do título.
  var VISIBLE = 96;

  var firstCard = function () {
    var cards = list.querySelectorAll('[data-news-card]');

    for (var index = 0; index < cards.length; index += 1) {
      if (cards[index].getClientRects().length) return cards[index];
    }
    return null;
  };

  var revealResults = function () {
    // Lado a lado (1024 px ou mais): a lista começa no topo da coluna.
    if (column.getBoundingClientRect().bottom > list.getBoundingClientRect().top + 1) return;

    var card = firstCard();
    if (!card) return;

    var top = card.getBoundingClientRect().top;
    var header = navbar ? navbar.getBoundingClientRect().bottom : 0;

    if (top >= header && top <= window.innerHeight - VISIBLE) return;
    filters.scrollIntoView({ block: 'start', behavior: 'instant' });
  };

  filters.addEventListener('click', function (event) {
    if (event.target.closest('[data-news-category], [data-news-sort]')) revealResults();
  });

  // 3. Carrossel das categorias com mouse.
  if (carousel && categories) {
    var arrows = carousel.querySelectorAll('[data-news-scroll]');
    var mouse = window.matchMedia('(max-width: 1023px) and (hover: hover) and (pointer: fine)');
    var reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

    var updateArrows = function () {
      var hidden = categories.scrollWidth - categories.clientWidth;
      var start = mouse.matches && hidden > 1 && categories.scrollLeft > 1;
      var end = mouse.matches && hidden > 1 && categories.scrollLeft < hidden - 1;

      arrows.forEach(function (arrow) {
        arrow.hidden = Number(arrow.getAttribute('data-news-scroll')) < 0 ? !start : !end;
      });
      carousel.toggleAttribute('data-more-start', start);
      carousel.toggleAttribute('data-more-end', end);
    };

    arrows.forEach(function (arrow) {
      // O clique rola sem tirar o foco de onde ele estava.
      arrow.addEventListener('mousedown', function (event) {
        event.preventDefault();
      });
      arrow.addEventListener('click', function () {
        categories.scrollBy({
          left: Number(arrow.getAttribute('data-news-scroll')) * categories.clientWidth * 0.8,
          behavior: reducedMotion.matches ? 'instant' : 'smooth'
        });
      });
    });

    categories.addEventListener('scroll', updateArrows, { passive: true });
    window.addEventListener('resize', updateArrows);
    window.addEventListener('load', updateArrows);
    if (mouse.addEventListener) mouse.addEventListener('change', updateArrows);
    if (window.ResizeObserver) new ResizeObserver(updateArrows).observe(categories);
    if (document.fonts && document.fonts.ready) document.fonts.ready.then(updateArrows);
    updateArrows();
  }

  // 4. Contagem do "Ver mais notícias".
  var remaining = document.querySelector('#btn-carregar-mais [data-news-remaining]');
  var resultCount = document.getElementById('news-result-count');

  if (remaining && resultCount) {
    var updateRemaining = function () {
      var total = parseInt(resultCount.textContent, 10) || 0;
      var shown = list.querySelectorAll('[data-news-card]:not(.hidden)').length;
      var missing = Math.max(total - shown, 0);
      var text = missing ? '(' + missing + ')' : '';

      // O botão fica dentro da lista (o main.js o põe depois do último card à
      // vista): só escreve quando muda, para não disparar o observador de novo.
      if (remaining.textContent !== text) remaining.textContent = text;
    };

    new MutationObserver(updateRemaining).observe(list, { attributes: true, attributeFilter: ['class'], subtree: true, childList: true });
    new MutationObserver(updateRemaining).observe(resultCount, { characterData: true, childList: true, subtree: true });
    updateRemaining();
  }
})();
