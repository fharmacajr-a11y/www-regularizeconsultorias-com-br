(function () {
  'use strict';

  function onReady(fn) {
    if (document.readyState !== 'loading') {
      fn();
    } else {
      document.addEventListener('DOMContentLoaded', fn);
    }
  }

  onReady(function () {
    var grid = document.getElementById('manuals-catalog-grid');
    if (!grid) return;

    var cards = Array.prototype.slice.call(grid.querySelectorAll('.manuals-catalog-card')) || [];
    var initialVisible = 3;

    if (cards.length <= initialVisible) {
      // nothing to do — keep all cards visible and no button
      return;
    }

    var extras = cards.slice(initialVisible);

    // hide extras initially
    extras.forEach(function (card) {
      try { card.hidden = true; } catch (e) {}
    });

    // create controls wrapper
    var controls = document.createElement('div');
    controls.className = 'manuals-catalog-controls pt-4 border-t border-slate-200 flex justify-center lg:pt-6';

    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'manuals-catalog-toggle inline-flex items-center gap-2 py-2 text-brand text-sm font-semibold hover:text-brand-dark underline-offset-4 hover:underline transition-colors duration-200 focus:outline-none focus:underline';
    btn.setAttribute('aria-expanded', 'false');
    btn.setAttribute('aria-controls', 'manuals-catalog-grid');

    var label = document.createElement('span');
    label.className = 'manuals-catalog-button-label';
    label.textContent = 'Ver mais documentos';

    // create svg icon
    var svgNS = 'http://www.w3.org/2000/svg';
    var svg = document.createElementNS(svgNS, 'svg');
    svg.setAttribute('class', 'w-4 h-4 flex-shrink-0 manuals-catalog-toggle-icon');
    svg.setAttribute('fill', 'none');
    svg.setAttribute('stroke', 'currentColor');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('aria-hidden', 'true');
    var path = document.createElementNS(svgNS, 'path');
    path.setAttribute('stroke-linecap', 'round');
    path.setAttribute('stroke-linejoin', 'round');
    path.setAttribute('stroke-width', '2');
    path.setAttribute('d', 'M19 9l-7 7-7-7');
    svg.appendChild(path);

    btn.appendChild(label);
    btn.appendChild(svg);
    controls.appendChild(btn);

    // insert controls after grid
    try {
      grid.parentNode.insertBefore(controls, grid.nextSibling);
    } catch (e) {}

    var expanded = false;

    function setExpandedState(isExpanded) {
      expanded = !!isExpanded;
      extras.forEach(function (card) {
        try { card.hidden = !isExpanded; } catch (e) {}
      });
      btn.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
      label.textContent = isExpanded ? 'Ver menos documentos' : 'Ver mais documentos';
    }

    setExpandedState(false);

    btn.addEventListener('click', function (e) {
      e.preventDefault();
      setExpandedState(!expanded);
    });

    btn.addEventListener('keydown', function (e) {
      if (e.key === 'Enter' || e.key === ' ') {
        e.preventDefault();
        setExpandedState(!expanded);
      }
    });
  });
})();
