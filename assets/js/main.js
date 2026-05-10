/**
 * Regularize Consultoria – main.js
 * -----------------------------------------------------------------
 * Responsabilidades:
 *   1. Adicionar sombra na navbar ao fazer scroll
 *   2. Toggle do menu mobile (botão hamburguer)
 *   3. Marcar o link da página atual como "ativo" na navbar
 * -----------------------------------------------------------------
 */

(function () {
  'use strict';

  /* =================================================================
     1. NAVBAR: adiciona classe "scrolled" ao fazer scroll
        → custom.css aplica box-shadow quando #navbar tem .scrolled
     ================================================================= */
  var navbar = document.getElementById('navbar');

  if (navbar) {
    var handleScroll = function () {
      if (window.scrollY > 10) {
        navbar.classList.add('scrolled');
      } else {
        navbar.classList.remove('scrolled');
      }
    };

    // Listener de scroll com passive:true para melhor performance
    window.addEventListener('scroll', handleScroll, { passive: true });

    // Executar uma vez ao carregar (caso a página já comece com scroll)
    handleScroll();
  }

  /* =================================================================
     2. MENU MOBILE: toggle ao clicar no botão hamburguer
        Alterna visibilidade do #mobile-menu e troca os ícones
     ================================================================= */
  var menuToggle    = document.getElementById('menu-toggle');
  var mobileMenu    = document.getElementById('mobile-menu');
  var iconHamburger = document.getElementById('icon-hamburger');
  var iconClose     = document.getElementById('icon-close');

  if (menuToggle && mobileMenu) {

    menuToggle.addEventListener('click', function () {
      var isOpen = !mobileMenu.classList.contains('hidden');

      if (isOpen) {
        // ---------- Fechar menu ----------
        mobileMenu.classList.add('hidden');
        iconHamburger.classList.remove('hidden');
        iconClose.classList.add('hidden');
        menuToggle.setAttribute('aria-expanded', 'false');
      } else {
        // ---------- Abrir menu ----------
        mobileMenu.classList.remove('hidden');
        iconHamburger.classList.add('hidden');
        iconClose.classList.remove('hidden');
        menuToggle.setAttribute('aria-expanded', 'true');
      }
    });

    // Fechar automaticamente ao clicar em qualquer link do menu mobile
    mobileMenu.querySelectorAll('a').forEach(function (link) {
      link.addEventListener('click', function () {
        mobileMenu.classList.add('hidden');
        iconHamburger.classList.remove('hidden');
        iconClose.classList.add('hidden');
        menuToggle.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* =================================================================
     3. LINK ATIVO: detecta a página atual e adiciona classe "active"
        ao link correspondente na navbar
        → custom.css aplica cor e font-weight no link .active
     ================================================================= */
  function normalizeInternalPath(path) {
    path = (path || '/').replace(/\\/g, '/');

    if (path.charAt(0) !== '/') {
      path = '/' + path;
    }

    if (path !== '/' && path.charAt(path.length - 1) !== '/') {
      path += '/';
    }

    return path;
  }

  function getInternalLinkPath(href) {
    var parser = document.createElement('a');
    parser.href = href;

    if (parser.hostname && parser.hostname !== window.location.hostname) {
      return '';
    }

    return normalizeInternalPath(parser.pathname || href);
  }

  var currentPath = normalizeInternalPath(window.location.pathname);
  var isNoticiasArticle = currentPath.indexOf('/noticias/') === 0 && currentPath !== '/noticias/';

  document.querySelectorAll('#navbar nav a[href]').forEach(function (link) {
    var href = link.getAttribute('href');
    var linkPath = href ? getInternalLinkPath(href) : '';

    if (
      linkPath === currentPath ||
      (isNoticiasArticle && linkPath === '/noticias/')
    ) {
      link.classList.add('active');
    }
  });

  /* =================================================================
     4. BADGE DE AVISOS: sincroniza contagem entre todas as páginas
        - Na página de comunicados: conta avisos reais (sem data-placeholder)
          e salva no localStorage.
        - Nas demais páginas: usa fallback imediato na primeira visita
          e sincroniza a contagem real a partir da página de comunicados.
        O badge some automaticamente quando não há avisos reais.
     ================================================================= */
  var avisoLista = document.getElementById('avisos-lista');
  var AVISOS_COUNT = 0;
  var AVISOS_FALLBACK_COUNT = 0;
  var AVISOS_STORAGE_KEY = 'avisos_count';
  var AVISOS_STORAGE_VERSION_KEY = 'avisos_count_version';
  var AVISOS_STORAGE_VERSION = '2026-04-28-normalizado';

  function normalizeAvisoStatus(value) {
    return (value || '').toLowerCase().trim();
  }

  function normalizeAvisosCount(value) {
    var parsedCount = parseInt(value, 10);
    return isNaN(parsedCount) || parsedCount < 0 ? 0 : parsedCount;
  }

  function renderAvisosCount(count) {
    AVISOS_COUNT = normalizeAvisosCount(count);

    document.querySelectorAll('.aviso-badge').forEach(function (badge) {
      badge.textContent = AVISOS_COUNT;
      badge.style.display = 'flex';
    });
  }

  function persistAvisosCount(count) {
    try {
      localStorage.setItem(AVISOS_STORAGE_KEY, normalizeAvisosCount(count));
      localStorage.setItem(AVISOS_STORAGE_VERSION_KEY, AVISOS_STORAGE_VERSION);
    } catch (e) {}
  }

  function readPersistedAvisosCount() {
    try {
      var storedVersion = localStorage.getItem(AVISOS_STORAGE_VERSION_KEY);

      if (storedVersion !== AVISOS_STORAGE_VERSION) {
        return null;
      }

      var storedCount = localStorage.getItem(AVISOS_STORAGE_KEY);
      return storedCount === null ? null : normalizeAvisosCount(storedCount);
    } catch (e) {
      return null;
    }
  }

  function isAvisoAtivo(article) {
    if (!article || article.hasAttribute('data-placeholder')) {
      return false;
    }

    var articleStatus = normalizeAvisoStatus(article.getAttribute('data-status'));

    return articleStatus !== 'resolved' && articleStatus !== 'normalizado';
  }

  function countAvisos(listElement) {
    var avisosCount = 0;

    if (!listElement) {
      return avisosCount;
    }

    listElement.querySelectorAll('article').forEach(function (article) {
      if (isAvisoAtivo(article)) {
        avisosCount += 1;
      }
    });

    return avisosCount;
  }

  function syncAvisosCountFromComunicado() {
    var comunicadoPath = '/comunicado/';

    fetch(comunicadoPath, { cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) {
          throw new Error('Falha ao carregar a página de comunicados');
        }

        return response.text();
      })
      .then(function (html) {
        var parser = new DOMParser();
        var comunicadoDoc = parser.parseFromString(html, 'text/html');
        var comunicadoLista = comunicadoDoc.getElementById('avisos-lista');
        var comunicadoCount = countAvisos(comunicadoLista);

        renderAvisosCount(comunicadoCount);
        persistAvisosCount(comunicadoCount);
      })
      .catch(function () {
        // Mantem fallback/localStorage caso a sincronizacao falhe.
      });
  }

  function renderAvisoMeta(metaNode, valueNode, value) {
    if (!metaNode || !valueNode) {
      return;
    }

    if (!value) {
      valueNode.textContent = '';
      metaNode.classList.add('hidden');
      metaNode.classList.remove('flex');
      return;
    }

    valueNode.textContent = value;
    metaNode.classList.remove('hidden');
    metaNode.classList.add('flex');
  }

  function renderAvisoUpdates() {
    document.querySelectorAll('#avisos-lista article').forEach(function (article) {
      var articleStatus = normalizeAvisoStatus(article.getAttribute('data-status'));
      var updatedAt = article.getAttribute('data-updated-at');
      var resolvedAt = articleStatus === 'resolved' || articleStatus === 'normalizado'
        ? article.getAttribute('data-resolved-at')
        : '';
      var updatedMeta = article.querySelector('[data-aviso-updated]');
      var updatedAtNode = article.querySelector('[data-aviso-updated-at]');
      var resolvedMeta = article.querySelector('[data-aviso-resolved]');
      var resolvedAtNode = article.querySelector('[data-aviso-resolved-at]');

      renderAvisoMeta(updatedMeta, updatedAtNode, updatedAt);
      renderAvisoMeta(resolvedMeta, resolvedAtNode, resolvedAt);
    });
  }

  if (avisoLista) {
    // Estamos na página de comunicados: calcula e persiste a contagem
    renderAvisosCount(countAvisos(avisoLista));
    persistAvisosCount(AVISOS_COUNT);
  } else {
    // Outra página: aplica fallback imediato e sincroniza com a página de comunicados
    var persistedCount = readPersistedAvisosCount();
    renderAvisosCount(persistedCount === null ? AVISOS_FALLBACK_COUNT : persistedCount);
    syncAvisosCountFromComunicado();
  }

  renderAvisoUpdates();

  /* =================================================================
     5. AVISOS COM RESUMO: cards com conteudo expansivel
     ================================================================= */
  function initializeAvisoHistoryToggles() {
    document.querySelectorAll('[data-aviso-history-card]').forEach(function (article) {
      var toggle = article.querySelector('[data-aviso-history-toggle]');
      var toggleLabel = article.querySelector('[data-aviso-history-toggle-label]');
      var toggleIcon = article.querySelector('[data-aviso-history-toggle-icon]');
      var content = article.querySelector('[data-aviso-history-content]');
      var expandLabel = toggle ? toggle.getAttribute('data-aviso-history-expand-label') : '';
      var collapseLabel = toggle ? toggle.getAttribute('data-aviso-history-collapse-label') : '';

      if (!toggle || !toggleLabel || !content) {
        return;
      }

      expandLabel = expandLabel || 'Ver histórico completo';
      collapseLabel = collapseLabel || 'Ocultar histórico';

      var setExpandedState = function (expanded) {
        content.classList.toggle('hidden', !expanded);
        toggle.setAttribute('aria-expanded', expanded ? 'true' : 'false');
        toggleLabel.textContent = expanded ? collapseLabel : expandLabel;

        if (toggleIcon) {
          toggleIcon.classList.toggle('rotate-180', expanded);
        }
      };

      setExpandedState(toggle.getAttribute('aria-expanded') === 'true');

      toggle.addEventListener('click', function () {
        var expanded = toggle.getAttribute('aria-expanded') === 'true';
        setExpandedState(!expanded);
      });
    });
  }

  initializeAvisoHistoryToggles();

  /* =================================================================
     6. BLOG: busca e filtros da página de notícias
     ================================================================= */
  function initializeBlogFilters() {
    var blogList = document.getElementById('blog-article-list');
    var searchInput = document.getElementById('blog-search');
    var filterButtons = document.querySelectorAll('[data-blog-category]');
    var resultCount = document.getElementById('blog-result-count');
    var emptyState = document.getElementById('blog-empty-state');
    var sortButtons = document.querySelectorAll('[data-blog-sort]');

    if (!blogList || !searchInput || !filterButtons.length || !resultCount || !emptyState) {
      return;
    }

    var articleCards = Array.prototype.slice.call(blogList.querySelectorAll('[data-blog-card]'));
    var activeCategory = 'Todos';
    var activeSort = 'desc';

    function normalizeText(value) {
      return (value || '')
        .toString()
        .toLowerCase()
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .trim();
    }

    function getCardTimestamp(card) {
      var time = card.querySelector('time[datetime]');
      var timestamp = time ? Date.parse(time.getAttribute('datetime')) : 0;
      return Number.isNaN(timestamp) ? 0 : timestamp;
    }

    function sortArticles() {
      var direction = activeSort === 'asc' ? 1 : -1;

      articleCards.sort(function (firstCard, secondCard) {
        return (getCardTimestamp(firstCard) - getCardTimestamp(secondCard)) * direction;
      });

      articleCards.forEach(function (card) {
        blogList.appendChild(card);
      });
    }

    function updateResults() {
      var query = normalizeText(searchInput.value);
      var normalizedCategory = normalizeText(activeCategory);
      var visibleCount = 0;

      articleCards.forEach(function (card) {
        var cardCategory = card.getAttribute('data-category') || '';
        var haystack = normalizeText([
          card.getAttribute('data-title'),
          card.getAttribute('data-summary'),
          card.getAttribute('data-category'),
          card.getAttribute('data-keywords'),
          card.textContent
        ].join(' '));
        var matchesSearch = !query || haystack.indexOf(query) !== -1;
        var matchesCategory = activeCategory === 'Todos' || normalizeText(cardCategory) === normalizedCategory;
        var isVisible = matchesSearch && matchesCategory;

        card.classList.toggle('hidden', !isVisible);

        if (isVisible) {
          visibleCount += 1;
        }
      });

      resultCount.textContent = visibleCount === 1
        ? '1 artigo encontrado'
        : visibleCount + ' artigos encontrados';
      emptyState.classList.toggle('hidden', visibleCount !== 0);
    }

    searchInput.addEventListener('input', updateResults);

    sortButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        activeSort = button.getAttribute('data-blog-sort') || 'desc';

        sortButtons.forEach(function (item) {
          item.setAttribute('aria-pressed', item === button ? 'true' : 'false');
        });

        sortArticles();
        updateResults();
      });
    });

    filterButtons.forEach(function (button) {
      button.addEventListener('click', function () {
        activeCategory = button.getAttribute('data-blog-category') || 'Todos';

        filterButtons.forEach(function (item) {
          item.setAttribute('aria-pressed', item === button ? 'true' : 'false');
        });

        updateResults();
      });
    });

    sortArticles();
    updateResults();
  }

  initializeBlogFilters();

  /* =================================================================
     7. IMAGEM DO AVISO: abre ampliada na propria pagina
     ================================================================= */
  var avisoImageTriggers = document.querySelectorAll('[data-aviso-image-trigger]');
  var avisoImageModal = document.getElementById('aviso-imagem-modal');
  var avisoImageClose = avisoImageModal ? avisoImageModal.querySelector('[data-aviso-image-close]') : null;
  var avisoImageModalTitle = avisoImageModal ? avisoImageModal.querySelector('#aviso-imagem-modal-titulo') : null;
  var avisoImageModalImage = avisoImageModal ? avisoImageModal.querySelector('[data-aviso-image-modal]') : null;
  var lastFocusedElement = null;

  if (avisoImageTriggers.length && avisoImageModal && avisoImageClose && avisoImageModalTitle && avisoImageModalImage) {
    var openAvisoImageModal = function (trigger) {
      var previewImage = trigger.querySelector('img');
      var modalImageSrc = trigger.getAttribute('data-aviso-image-src') || (previewImage ? previewImage.getAttribute('src') : '');
      var modalImageAlt = previewImage ? previewImage.getAttribute('alt') : '';
      var modalImageTitle = trigger.getAttribute('data-aviso-image-title') || modalImageAlt || 'Imagem de referência do aviso';

      lastFocusedElement = trigger;
      avisoImageModalTitle.textContent = modalImageTitle;
      avisoImageModalImage.setAttribute('src', modalImageSrc);
      avisoImageModalImage.setAttribute('alt', modalImageAlt);
      avisoImageModal.classList.remove('hidden');
      avisoImageModal.classList.add('flex');
      document.body.classList.add('overflow-hidden');
      avisoImageClose.focus();
    };

    var closeAvisoImageModal = function () {
      avisoImageModal.classList.add('hidden');
      avisoImageModal.classList.remove('flex');
      document.body.classList.remove('overflow-hidden');

      if (lastFocusedElement && typeof lastFocusedElement.focus === 'function') {
        lastFocusedElement.focus();
      }
    };

    avisoImageTriggers.forEach(function (trigger) {
      trigger.addEventListener('click', function () {
        openAvisoImageModal(trigger);
      });
    });
    avisoImageClose.addEventListener('click', closeAvisoImageModal);

    avisoImageModal.addEventListener('click', function (event) {
      if (event.target === avisoImageModal) {
        closeAvisoImageModal();
      }
    });

    document.addEventListener('keydown', function (event) {
      if (event.key === 'Escape' && !avisoImageModal.classList.contains('hidden')) {
        closeAvisoImageModal();
      }
    });
  }

  /* =================================================================
     5. BOTÃO VOLTAR AO TOPO: exibe após 300 px de scroll e rola suavemente
        → custom.css controla a transição via .is-visible em .floating-btn--top
     ================================================================= */
  var btnVoltarTopo = document.getElementById('btn-voltar-topo');

  if (btnVoltarTopo) {
    var handleScrollTop = function () {
      if (window.scrollY > 300) {
        btnVoltarTopo.classList.add('is-visible');
      } else {
        btnVoltarTopo.classList.remove('is-visible');
      }
    };

    window.addEventListener('scroll', handleScrollTop, { passive: true });
    handleScrollTop();

    btnVoltarTopo.addEventListener('click', function () {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
  }

})();
