(function () {
  'use strict';

  var state = { records: [], filtered: [], page: 1, pageSize: 25 };
  var ids = ['fp-search', 'fp-uf', 'fp-status', 'fp-clear', 'fp-table-body', 'fp-result-count', 'fp-loading', 'fp-empty', 'fp-error', 'fp-pagination', 'fp-prev', 'fp-next', 'fp-page-info', 'fp-page-size'];
  var el = {};
  ids.forEach(function (id) { el[id] = document.getElementById(id); });
  var tableContainer = el['fp-table-body'].closest('.fp-table-scroll');

  function normalize(value) {
    return String(value || '').toLocaleLowerCase('pt-BR').normalize('NFD').replace(/[\u0300-\u036f]/g, '').replace(/['\u2019]/g, '').replace(/[-\s]+/g, ' ').trim();
  }
  function formatNumber(value) { return new Intl.NumberFormat('pt-BR').format(value); }
  function formatDate(value) {
    var parts = String(value || '').split('-');
    return parts.length === 3 ? parts[2] + '/' + parts[1] + '/' + parts[0] : '—';
  }
  function setText(id, value) { var node = document.getElementById(id); if (node) node.textContent = value; }
  function setFatalError(message, error) {
    state.records = [];
    state.filtered = [];
    state.page = 1;
    el['fp-table-body'].replaceChildren();
    tableContainer.classList.add('hidden');
    tableContainer.hidden = true;
    el['fp-empty'].classList.add('hidden');
    el['fp-pagination'].classList.add('hidden');
    el['fp-pagination'].hidden = true;
    el['fp-result-count'].textContent = 'Consulta indisponível.';
    el['fp-page-info'].textContent = '';
    ['fp-search', 'fp-uf', 'fp-status', 'fp-clear', 'fp-prev', 'fp-next', 'fp-page-size'].forEach(function (id) { el[id].disabled = true; });
    resetIndicators();
    el['fp-error'].textContent = message;
    el['fp-error'].classList.remove('hidden');
    el['fp-loading'].classList.add('hidden');
    if (error) console.error(error);
  }
  function calculateTotals(records) {
    return records.reduce(function (result, record) { result.total += record.vagas_totais; result.filled += record.vagas_preenchidas; result.available += record.vagas_disponiveis; return result; }, { total: 0, filled: 0, available: 0 });
  }
  function resetIndicators() {
    ['fp-total-municipios', 'fp-vagas-totais', 'fp-vagas-preenchidas', 'fp-vagas-disponiveis', 'fp-indicator-date'].forEach(function (id) { setText(id, '—'); });
  }
  function validRecord(record) {
    if (!record || typeof record.codigo_ibge !== 'string' || !/^\d{7}$/.test(record.codigo_ibge) || typeof record.uf !== 'string' || !/^[A-Za-z]{2}$/.test(record.uf) || typeof record.municipio_exibicao !== 'string' || !record.municipio_exibicao.trim() || typeof record.municipio_fonte_ms !== 'string' || !record.municipio_fonte_ms.trim()) return false;
    if (!['vagas_totais', 'vagas_preenchidas', 'vagas_disponiveis'].every(function (key) { return Number.isInteger(record[key]) && record[key] >= 0; })) return false;
    return record.vagas_preenchidas <= record.vagas_totais && record.vagas_disponiveis <= record.vagas_totais && record.vagas_preenchidas + record.vagas_disponiveis === record.vagas_totais;
  }
  function validRecords(records) {
    if (!Array.isArray(records) || !records.length) return false;
    var codes = new Set();
    return records.every(function (record) {
      if (!validRecord(record) || codes.has(record.codigo_ibge)) return false;
      codes.add(record.codigo_ibge);
      return true;
    });
  }
  function createCell(row, value, className) { var cell = document.createElement('td'); if (className) cell.className = className; cell.textContent = value; row.appendChild(cell); }
  function renderTable() {
    var totalPages = Math.max(1, Math.ceil(state.filtered.length / state.pageSize));
    state.page = Math.min(state.page, totalPages);
    var start = (state.page - 1) * state.pageSize;
    var visible = state.filtered.slice(start, start + state.pageSize);
    el['fp-table-body'].replaceChildren();
    visible.forEach(function (record) {
      var row = document.createElement('tr');
      var available = record.vagas_disponiveis > 0;
      createCell(row, record.uf);
      createCell(row, record.municipio_exibicao);
      createCell(row, formatNumber(record.vagas_totais), 'fp-number-cell');
      createCell(row, formatNumber(record.vagas_preenchidas), 'fp-number-cell');
      createCell(row, formatNumber(record.vagas_disponiveis), 'fp-number-cell');
      var statusCell = document.createElement('td'); var badge = document.createElement('span'); badge.className = 'fp-status ' + (available ? 'fp-status--available' : 'fp-status--unavailable'); badge.textContent = available ? 'Com vagas' : 'Sem vagas disponíveis'; statusCell.appendChild(badge); row.appendChild(statusCell);
      el['fp-table-body'].appendChild(row);
    });
    el['fp-result-count'].textContent = state.filtered.length === 1 ? '1 município encontrado' : formatNumber(state.filtered.length) + ' municípios encontrados';
    el['fp-empty'].classList.toggle('hidden', state.filtered.length !== 0);
    el['fp-pagination'].classList.toggle('hidden', state.filtered.length === 0);
    el['fp-pagination'].hidden = state.filtered.length === 0;
    el['fp-prev'].disabled = state.page === 1;
    el['fp-next'].disabled = state.page === totalPages;
    el['fp-page-info'].textContent = 'Página ' + state.page + ' de ' + totalPages;
  }
  function applyFilters() {
    var search = normalize(el['fp-search'].value); var uf = el['fp-uf'].value; var status = el['fp-status'].value;
    state.filtered = state.records.filter(function (record) {
      var names = normalize(record.municipio_exibicao + ' ' + record.municipio_fonte_ms);
      var matchesStatus = !status || (status === 'available' && record.vagas_disponiveis > 0) || (status === 'unavailable' && record.vagas_disponiveis === 0) || (status === 'filled' && record.vagas_preenchidas > 0);
      return (!search || names.indexOf(search) !== -1) && (!uf || record.uf === uf) && matchesStatus;
    });
    state.page = 1; renderTable();
  }
  function populateUfs() {
    Array.from(new Set(state.records.map(function (record) { return record.uf; }))).sort().forEach(function (uf) { var option = document.createElement('option'); option.value = uf; option.textContent = uf; el['fp-uf'].appendChild(option); });
  }
  function renderIndicators(records, metadata) {
    var totals = calculateTotals(records);
    setText('fp-total-municipios', formatNumber(records.length)); setText('fp-vagas-totais', formatNumber(totals.total)); setText('fp-vagas-preenchidas', formatNumber(totals.filled)); setText('fp-vagas-disponiveis', formatNumber(totals.available));
    if (!metadata) return true;
    setText('fp-indicator-date', formatDate(metadata.data_oficial)); return true;
  }
  function isConsistent(records, metadata, totals) {
    var ufCount = new Set(records.map(function (record) { return record.uf; })).size;
    return metadata.quantidade_registros === records.length && metadata.quantidade_ufs === ufCount && metadata.totais_vagas && metadata.totais_vagas.vagas_totais === totals.total && metadata.totais_vagas.vagas_preenchidas === totals.filled && metadata.totais_vagas.vagas_disponiveis === totals.available;
  }
  function renderMetadata(metadata) {
    if (!metadata || typeof metadata !== 'object') throw new Error('Metadados inválidos.');
    setText('fp-source-title', metadata.titulo_oficial || 'Base oficial de municípios'); setText('fp-source-org', metadata.orgao_origem || '—'); setText('fp-official-date', formatDate(metadata.data_oficial)); setText('fp-import-date', formatDate(metadata.data_importacao)); setText('fp-ibge-version', metadata.data_ou_versao_referencia_ibge || '—');
    var link = document.getElementById('fp-official-link'); if (link && /^https:\/\//.test(metadata.url_oficial_visualizacao || '')) link.href = metadata.url_oficial_visualizacao;
  }
  function fetchJson(url) { return fetch(url, { cache: 'no-store' }).then(function (response) { if (!response.ok) throw new Error('Falha ao carregar ' + url); return response.json(); }); }
  function initializeEvents() {
    ['fp-search', 'fp-uf', 'fp-status'].forEach(function (id) { el[id].addEventListener(id === 'fp-search' ? 'input' : 'change', applyFilters); });
    el['fp-clear'].addEventListener('click', function () { el['fp-search'].value = ''; el['fp-uf'].value = ''; el['fp-status'].value = ''; applyFilters(); el['fp-search'].focus(); });
    el['fp-page-size'].addEventListener('change', function () { state.pageSize = Number(el['fp-page-size'].value); state.page = 1; renderTable(); });
    el['fp-prev'].addEventListener('click', function () { if (state.page > 1) { state.page -= 1; renderTable(); } });
    el['fp-next'].addEventListener('click', function () { if (state.page * state.pageSize < state.filtered.length) { state.page += 1; renderTable(); } });
  }
  document.addEventListener('DOMContentLoaded', function () {
    initializeEvents();
    fetchJson('/data/farmacia-popular/vagas-2026-07-28.json').then(function (records) {
      if (!validRecords(records)) throw new Error('A lista de municípios está em formato inválido.');
      return fetchJson('/data/farmacia-popular/metadados.json').then(function (metadata) {
        renderMetadata(metadata);
        var totals = calculateTotals(records);
        if (!isConsistent(records, metadata, totals)) {
          setFatalError('Não foi possível validar a consistência da base carregada. Consulte a fonte oficial.', 'Inconsistência entre a lista de vagas e os metadados: ' + JSON.stringify({ quantidade_calculada: records.length, quantidade_ufs_calculada: new Set(records.map(function (record) { return record.uf; })).size, quantidade_declarada: metadata.quantidade_registros, quantidade_ufs_declarada: metadata.quantidade_ufs, totais_calculados: totals, totais_declarados: metadata.totais_vagas }));
          return;
        }
        state.records = records; populateUfs(); applyFilters(); renderIndicators(records, metadata); el['fp-loading'].classList.add('hidden');
      }).catch(function (error) {
        console.error(error); document.getElementById('fp-meta-fallback').classList.remove('hidden'); state.records = records; populateUfs(); applyFilters(); renderIndicators(records, null); el['fp-loading'].classList.add('hidden');
      });
    }).catch(function (error) { setFatalError('Não foi possível carregar a consulta de municípios neste momento. Tente novamente mais tarde ou consulte a fonte oficial.', error); });
  });
})();
