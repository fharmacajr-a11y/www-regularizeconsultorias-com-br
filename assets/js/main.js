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
  var currentFile = window.location.pathname.split('/').pop() || 'index.html';

  document.querySelectorAll('#navbar nav a[href]').forEach(function (link) {
    var href = link.getAttribute('href');

    // Considera "/" ou "" como index.html
    if (
      href === currentFile ||
      (currentFile === '' && href === 'index.html')
    ) {
      link.classList.add('active');
    }
  });

  /* =================================================================
     4. BADGE DE AVISOS: sincroniza contagem entre todas as páginas
        - Em comunicado.html: conta avisos reais (sem data-placeholder)
          e salva no localStorage.
        - Nas demais páginas: usa fallback imediato na primeira visita
          e sincroniza a contagem real a partir de comunicado.html.
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
    fetch('comunicado.html', { cache: 'no-store' })
      .then(function (response) {
        if (!response.ok) {
          throw new Error('Falha ao carregar comunicado.html');
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
    // Estamos em comunicado.html: calcula e persiste a contagem
    renderAvisosCount(countAvisos(avisoLista));
    persistAvisosCount(AVISOS_COUNT);
  } else {
    // Outra página: aplica fallback imediato e sincroniza com comunicado.html
    var persistedCount = readPersistedAvisosCount();
    renderAvisosCount(persistedCount === null ? AVISOS_FALLBACK_COUNT : persistedCount);
    syncAvisosCountFromComunicado();
  }

  renderAvisoUpdates();

  /* =================================================================
     5. IMAGEM DO AVISO: abre ampliada na propria pagina
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
      var modalImageTitle = trigger.getAttribute('data-aviso-image-title') || modalImageAlt || 'Imagem de referencia do aviso';

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

})();
