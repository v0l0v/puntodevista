import { SOURCES_KEY, MONTH_NAMES, PAGE_SIZE } from './constants.js';
import { state } from './state.js';

export function isMobile() {
  return window.matchMedia('(max-width: 720px)').matches;
}

export function isSourceVisible(src) {
  if (state.allChecked) return true;
  return state.sources.has(src);
}

export function isSearchMatch(e, q) {
  if (!q) return true;
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  const photo = e.photographer || (e.photographers ? e.photographers.join(' ') : '');
  const text = `${e.title || ''} ${photo} ${e.summary || ''} ${e.excerpt || ''} ${e.content || ''} ${e._source || ''}`.toLowerCase();
  return terms.every(t => text.includes(t));
}

export function getDateRange() {
  const now = new Date();
  const { period, value } = state.dateFilter;
  if (period === 'all') return null;
  if (period === 'day') {
    const start = new Date(now); start.setHours(0,0,0,0);
    return { from: start.getTime(), to: Infinity };
  }
  if (period === 'week') {
    const start = new Date(now);
    start.setDate(start.getDate() - 6); start.setHours(0,0,0,0);
    return { from: start.getTime(), to: Infinity };
  }
  if (period === 'month') {
    const start = new Date(now.getFullYear(), now.getMonth(), 1);
    return { from: start.getTime(), to: Infinity };
  }
  if (period === 'year') {
    const start = new Date(now.getFullYear(), 0, 1);
    return { from: start.getTime(), to: Infinity };
  }
  if (period === 'month-specific' && value) {
    const start = new Date(value.getFullYear(), value.getMonth(), 1);
    const end   = new Date(value.getFullYear(), value.getMonth() + 1, 0, 23, 59, 59, 999);
    return { from: start.getTime(), to: end.getTime() };
  }
  return null;
}

export function isDateVisible(entry) {
  const range = getDateRange();
  if (!range) return true;
  if (!entry) return false;
  let t = 0;
  if (entry._parsedDate instanceof Date && !isNaN(entry._parsedDate)) {
    t = entry._parsedDate.getTime();
  } else if (typeof entry._parsedDate === 'number') {
    t = entry._parsedDate;
  } else if (entry._parsedDate || entry.date) {
    const d = new Date(entry._parsedDate || entry.date);
    if (!isNaN(d)) t = d.getTime();
  }
  if (!t) return true;
  return t >= range.from && t <= range.to;
}

export function updateDateBtnLabel() {
  const { period, value } = state.dateFilter;
  const labels = {
    all: 'todas', year: 'este año', month: 'este mes',
    week: 'esta semana', day: 'hoy'
  };
  let label = labels[period] || 'todas';
  if (period === 'month-specific' && value) {
    label = `${MONTH_NAMES[value.getMonth()]} ${value.getFullYear()}`;
  }
  const dateBtnLabel = document.getElementById('date-btn-label');
  if (dateBtnLabel) dateBtnLabel.textContent = label;
  const isFiltered = period !== 'all';
  const dateBtn = document.getElementById('date-btn');
  if (dateBtn) dateBtn.classList.toggle('active', isFiltered);
}

export function setDateFilter(period, value) {
  state.dateFilter = { period, value };
  window.__dateFilter = state.dateFilter;
  applyFilter();
  updateDateBtnLabel();
  
  document.querySelectorAll('.date-row').forEach(r => {
    const isActive = r.dataset.period === period && period !== 'month-specific';
    r.classList.toggle('active', isActive);
    r.setAttribute('aria-pressed', isActive ? 'true' : 'false');
  });
  document.querySelectorAll('.date-month-btn').forEach(b => {
    const isActive = period === 'month-specific' &&
      value && b.dataset.year === String(value.getFullYear()) &&
      b.dataset.month === String(value.getMonth());
    b.classList.toggle('active', isActive);
  });
}

export function buildMonthsGrid() {
  const container = document.getElementById('date-months');
  if (!container) return;
  container.innerHTML = '';
  const now = new Date();
  const entries = state.allEntries || [];

  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const y = d.getFullYear();
    const m = d.getMonth();
    const count = entries.filter(e => {
      if (!e._parsedDate) return false;
      const ed = new Date(e._parsedDate);
      return ed.getFullYear() === y && ed.getMonth() === m;
    }).length;

    const btn = document.createElement('button');
    btn.className = 'date-month-btn' + (count > 0 ? ' has-entries' : ' empty');
    btn.dataset.year = y;
    btn.dataset.month = m;
    btn.setAttribute('aria-label', `${MONTH_NAMES[m]} ${y}: ${count} artículos`);
    btn.innerHTML = `<span>${MONTH_NAMES[m]}</span><br><span style="opacity:.5;font-size:.5rem">${y}</span>`;

    if (state.dateFilter.period === 'month-specific' && state.dateFilter.value &&
        state.dateFilter.value.getFullYear() === y && state.dateFilter.value.getMonth() === m) {
      btn.classList.add('active');
    }

    if (count > 0) {
      btn.addEventListener('click', () => {
        setDateFilter('month-specific', new Date(y, m, 1));
        document.getElementById('date-panel')?.classList.add('hide');
        const dBtn = document.getElementById('date-btn');
        if (dBtn) {
          dBtn.classList.remove('active');
          dBtn.setAttribute('aria-expanded', 'false');
        }
      });
    }
    container.appendChild(btn);
  }
}

export function loadSources() {
  try {
    const saved = JSON.parse(localStorage.getItem(SOURCES_KEY));
    if (Array.isArray(saved)) {
      if (saved.length === 0) {
        state.allChecked = true;
        state.sources = new Set();
      } else {
        state.allChecked = false;
        state.sources = new Set(saved);
      }
    }
  } catch {}
  window.__allChecked = state.allChecked;
  window.__sources = state.sources;
}

export function saveSources() {
  localStorage.setItem(SOURCES_KEY, JSON.stringify([...state.sources]));
}

export async function loadSourcesConfig() {
  try {
    const resp = await fetch('sources.json', { cache: 'no-store' });
    const data = await resp.json();
    if (Array.isArray(data) && data.length) {
      state.allSources = data.filter(s => s.enabled !== false).map(s => s.id);
      for (const s of data) {
        if (s.name) state.sourceLabels[s.id] = s.name;
      }
      window.__allSources = state.allSources;
      window.__sourceLabels = state.sourceLabels;
    }
  } catch {}
}

export function getReadCounts() {
  try {
    return JSON.parse(localStorage.getItem('feedfoto.read_counts')) || {};
  } catch {
    return {};
  }
}

export function incrementReadCount(source) {
  if (!source) return;
  const counts = getReadCounts();
  counts[source] = (counts[source] || 0) + 1;
  localStorage.setItem('feedfoto.read_counts', JSON.stringify(counts));
  sortSourcesUI();
}

export function sortSourcesUI() {
  const panel = document.getElementById('sources-panel');
  if (!panel) return;
  const counts = getReadCounts();
  const rows = Array.from(panel.querySelectorAll('.source-row:not(.all)'));
  
  rows.sort((a, b) => {
    const srcA = a.dataset.src;
    const srcB = b.dataset.src;
    const countA = counts[srcA] || 0;
    const countB = counts[srcB] || 0;
    return countB - countA;
  });
  
  rows.forEach(row => panel.appendChild(row));
}

export function setupSourcesUI() {
  const panel = document.getElementById('sources-panel');
  if (!panel) return;
  
  panel.innerHTML = '';
  const allRow = document.createElement('label');
  allRow.className = 'source-row all';
  allRow.id = 'source-all-row';
  allRow.innerHTML = `<input type="checkbox" id="chk-all" ${state.allChecked ? 'checked' : ''}><span>Todas las fuentes</span><span class="src-count" id="count-all">0</span>`;
  panel.appendChild(allRow);

  const chkAll = allRow.querySelector('input');
  if (chkAll) {
    chkAll.addEventListener('change', (e) => {
      state.allChecked = e.target.checked;
      window.__allChecked = state.allChecked;
      state.sources.clear();
      saveSources();
      applyFilter();
    });
  }

  state.allSources.forEach(src => {
    const labelText = window.getSourceLabel ? window.getSourceLabel(src) : (state.sourceLabels[src] || src);
    const row = document.createElement('label');
    row.className = 'source-row';
    row.dataset.src = src;
    row.innerHTML = `<input type="checkbox" data-src="${src}"><span>${labelText}</span><span class="src-count" id="count-${src}">0</span>`;
    
    const input = row.querySelector('input');
    if (input) {
      input.checked = isSourceVisible(src);
      input.addEventListener('change', (e) => {
        if (state.allChecked) {
          state.allChecked = false;
          state.allSources.forEach(s => {
            if (s !== src) state.sources.add(s);
          });
        } else {
          if (e.target.checked) {
            state.sources.add(src);
            if (state.sources.size === state.allSources.length) {
              state.allChecked = true;
              state.sources.clear();
            }
          } else {
            state.sources.delete(src);
          }
        }
        window.__allChecked = state.allChecked;
        saveSources();
        applyFilter();
      });
    }
    panel.appendChild(row);
  });
  sortSourcesUI();
}

export function applyFilter(resetLimit = true) {
  if (resetLimit) {
    state.visibleLimit = PAGE_SIZE;
  }
  const entries = (state.allEntries || [])
    .filter(e => isSourceVisible(e._source))
    .filter(e => isDateVisible(e))
    .filter(e => isSearchMatch(e, state.searchQuery));
  
  state.currentFilteredEntries = entries;
  if (window.render) {
    window.render(entries);
  }

  const chkAll = document.getElementById('chk-all');
  if (chkAll) chkAll.checked = state.allChecked;

  state.allSources.forEach(src => {
    const el = document.querySelector(`.source-row[data-src="${src}"] input`);
    if (el) el.checked = isSourceVisible(src);
  });

  const countEl = document.getElementById('sources-btn-count');
  if (countEl) {
    countEl.textContent = state.allChecked
      ? 'todas'
      : (state.sources.size === 0 ? 'ninguna' : `${state.sources.size}/${state.allSources.length}`);
  }
}

// Registro global
window.setDateFilter = setDateFilter;
window.updateDateBtnLabel = updateDateBtnLabel;
window.buildMonthsGrid = buildMonthsGrid;
window.isSourceVisible = isSourceVisible;
window.isDateVisible = isDateVisible;
window.isSearchMatch = isSearchMatch;
window.applyFilter = applyFilter;
window.loadSources = loadSources;
window.saveSources = saveSources;
window.setupSourcesUI = setupSourcesUI;
window.getReadCounts = getReadCounts;
window.incrementReadCount = incrementReadCount;
window.sortSourcesUI = sortSourcesUI;
