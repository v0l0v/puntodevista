const WP_API = 'https://www.thisiscolossal.com/wp-json/wp/v2/posts?categories=496&per_page=20';
const POST_API = 'https://www.thisiscolossal.com/wp-json/wp/v2/posts';

const BOOM_FEEDS = ['https://www.booooooom.com/blog/photo/feed/'];
const TPJ_FEEDS = [
  'https://thephotographicjournal.com/essays/rss',
  'https://thephotographicjournal.com/interviews/feed',
  'https://thephotographicjournal.com/features/feed',
];
const HUCK_FEEDS = ['https://www.huckmag.com/topic/photography/feed'];
const LENSCULTURE_FEEDS = ['https://www.lensculture.com/feeds/feed.rss'];
const ODLP_FEEDS = ['https://loeildelaphotographie.com/en/feed/'];

const RSS_PROXIES = [
  u => 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u),
  u => 'https://api.codetabs.com/v1/proxy?quest=' + encodeURIComponent(u),
];
const REFRESH_MS = 10 * 60 * 1000;
let ALL_SOURCES = [
  'colossal', 'lomography', 'booooooom', 'tpj', 'swan', 'huck', 'lensculture', 'odlp', 'magnum', 'shootitwithfilm',
  '35mmc', 'kosmofoto', 'casualphotophile', 'phroom', 'c41', 'featureshoot', 'aintbad', 'emulsive'
];
let SOURCE_LABELS = {
  colossal: 'Colossal · Fotografía',
  lomography: 'Lomography Magazine',
  booooooom: 'Booooooom',
  tpj: 'The Photographic Journal',
  swan: 'Swann Galleries',
  huck: 'Huck Magazine',
  lensculture: 'LensCulture',
  odlp: "L'Œil de la Photographie",
  magnum: 'Magnum Photos',
  shootitwithfilm: 'Shoot It With Film',
  '35mmc': '35mmc',
  kosmofoto: 'Kosmo Foto',
  casualphotophile: 'Casual Photophile',
  phroom: 'Phroom Magazine',
  c41: 'C41 Magazine',
  featureshoot: 'Feature Shoot',
  aintbad: "Ain't-Bad",
  emulsive: 'EMULSIVE'
};
const SOURCES_KEY = 'feedfoto.sources';
const PODCAST_RELEASE = 'https://github.com/v0l0v/puntodevista/releases/download/episodios';
const PODCAST_COVER = 'podcast-cover.jpg';

const CLICK_OPEN = ['assets/mp3/click1.mp3', 'assets/mp3/click2.mp3', 'assets/mp3/click3.mp3', 'assets/mp3/click4.mp3'];
let _clickLast = -1;

function playClickOpen() {
  try {
    let idx;
    do {
      idx = Math.floor(Math.random() * CLICK_OPEN.length);
    } while (idx === _clickLast && CLICK_OPEN.length > 1);
    _clickLast = idx;
    const a = new Audio(CLICK_OPEN[idx]);
    a.volume = 0.12;
    a.play().catch(() => {});
  } catch (e) {}
}

let __sharedAudio = null;

function updateAllPodcastPlayersUI() {
  if (!__sharedAudio) return;
  const isPlaying = !__sharedAudio.paused;
  const cur = Math.floor(__sharedAudio.currentTime || 0);
  const dur = Math.floor(__sharedAudio.duration || 0);
  const pct = (dur > 0) ? ((__sharedAudio.currentTime / __sharedAudio.duration) * 100) + '%' : '0%';
  const timeText = fmtDur(cur) + ' / ' + fmtDur(dur);

  document.querySelectorAll('.podcast-player').forEach(p => {
    const btn = p.querySelector('.podcast-play');
    const fill = p.querySelector('.podcast-progress-fill');
    const time = p.querySelector('.podcast-time');
    if (btn) btn.textContent = isPlaying ? '⏸' : '▶';
    if (fill) fill.style.width = pct;
    if (time && dur > 0) time.textContent = timeText;
    if (isPlaying) p.classList.add('is-playing');
    else p.classList.remove('is-playing');
  });
}

function selectHeroPodcastEntry(entry) {
  if (!entry) return;
  const hero = document.getElementById('podcast-hero');
  if (!hero) return;
  const img = document.getElementById('podcast-hero-img');
  const title = document.getElementById('podcast-hero-title');
  const meta = document.getElementById('podcast-hero-meta');
  const resumen = document.getElementById('podcast-hero-resumen');
  const player = document.getElementById('podcast-hero-player');

  if (img) setPodcastImage(img, entry);
  if (title) title.textContent = entry.podcast_title || entry.title;
  if (meta) meta.textContent = 'episodio ' + (entry.num || '') + ' · ' + fmtDate(new Date((entry.date || '') + 'T00:00:00')) + ' · ' + fmtDur(entry.duration);
  if (resumen) resumen.onclick = (e) => { e.preventDefault(); openPodcastResumen(entry); };
  
  if (player) {
    player.dataset.url = entry.link;
  }
  hero.classList.remove('hide');

  const audio = getSharedPodcastAudio(entry.link, entry);
  audio.play().catch(() => {});
}

function getSharedPodcastAudio(url, entry) {
  if (__sharedAudio && __sharedAudio._url === url) {
    return __sharedAudio;
  }
  if (__sharedAudio) {
    __sharedAudio.pause();
    __sharedAudio.src = '';
  }
  const audio = new Audio(url);
  audio.preload = 'none';
  audio._url = url;
  audio.addEventListener('timeupdate', updateAllPodcastPlayersUI);
  audio.addEventListener('loadedmetadata', updateAllPodcastPlayersUI);
  audio.addEventListener('playing', updateAllPodcastPlayersUI);
  audio.addEventListener('pause', updateAllPodcastPlayersUI);
  audio.addEventListener('ended', () => {
    updateAllPodcastPlayersUI();
  });
  __sharedAudio = audio;
  return audio;
}

function initPodcastPlayers() {
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('.podcast-play');
    if (btn) {
      const player = btn.closest('.podcast-player');
      if (!player) return;
      const url = player.dataset.url;
      if (!url) return;
      
      const entries = window.__podcastEntries || [];
      const entry = entries.find(x => x.link === url) || entries[entries.length - 1];
      const audio = getSharedPodcastAudio(url, entry);

      if (audio.paused) {
        audio.play().catch(() => {});
      } else {
        audio.pause();
      }
      return;
    }

    const bar = e.target.closest('.podcast-progress');
    if (bar) {
      if (!__sharedAudio || !__sharedAudio.duration) return;
      const rect = bar.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      __sharedAudio.currentTime = pct * __sharedAudio.duration;
      return;
    }
  });

  document.body.addEventListener('input', (e) => {
    const vol = e.target.closest('.podcast-volume');
    if (vol && __sharedAudio) {
      const v = parseFloat(vol.value);
      __sharedAudio.volume = v;
      document.querySelectorAll('.podcast-volume').forEach(inp => { if (inp !== vol) inp.value = v; });
    }
  });
}

document.addEventListener('DOMContentLoaded', async () => {
  loadSources();

  // ── Panel Fuentes ──────────────────────────────────────────────────
  const sourcesBtn = document.getElementById('sources-btn');
  const sourcesPanel = document.getElementById('sources-panel');
  const dateBtn = document.getElementById('date-btn');
  const datePanel = document.getElementById('date-panel');

  function closeAllPanels() {
    sourcesPanel.classList.add('hide');
    sourcesBtn.classList.remove('active');
    sourcesBtn.setAttribute('aria-expanded', 'false');
    datePanel.classList.add('hide');
    dateBtn.classList.remove('active');
    dateBtn.setAttribute('aria-expanded', 'false');
  }

  sourcesBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const wasOpen = !sourcesPanel.classList.contains('hide');
    closeAllPanels();
    if (!wasOpen) {
      sourcesPanel.classList.remove('hide');
      sourcesBtn.classList.add('active');
      sourcesBtn.setAttribute('aria-expanded', 'true');
    }
  });

  // ── Panel Fecha ────────────────────────────────────────────────────
  dateBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    const wasOpen = !datePanel.classList.contains('hide');
    closeAllPanels();
    if (!wasOpen) {
      buildMonthsGrid();
      datePanel.classList.remove('hide');
      dateBtn.classList.add('active');
      dateBtn.setAttribute('aria-expanded', 'true');
    }
  });

  document.addEventListener('click', (e) => {
    if (!sourcesPanel.classList.contains('hide') &&
        !sourcesPanel.contains(e.target) && e.target !== sourcesBtn) {
      sourcesPanel.classList.add('hide');
      sourcesBtn.classList.remove('active');
      sourcesBtn.setAttribute('aria-expanded', 'false');
    }
    if (!datePanel.classList.contains('hide') &&
        !datePanel.contains(e.target) && e.target !== dateBtn) {
      datePanel.classList.add('hide');
      dateBtn.classList.remove('active');
      dateBtn.setAttribute('aria-expanded', 'false');
    }
  });

  // Filas de período (todo, año, mes, semana, hoy)
  datePanel.querySelectorAll('.date-row').forEach(row => {
    row.addEventListener('click', () => {
      const period = row.dataset.period;
      if (period === 'year') return; // "Este año" solo sirve como cabecera del grid
      setDateFilter(period, null);
      closeAllPanels();
    });
  });

  // ── Inicialización de fuentes y feeds ──────────────────────────────
  const searchClear = document.getElementById('search-clear');
  let _searchTimer = null;

  if (searchInput) {
    searchInput.addEventListener('input', (e) => {
      __searchQuery = e.target.value.trim();
      if (searchClear) searchClear.classList.toggle('visible', !!__searchQuery);
      applyFilter();

      // Consultar sqlite-vec vía /api/search si la query tiene profundidad conceptual
      clearTimeout(_searchTimer);
      if (__searchQuery.length >= 3) {
        _searchTimer = setTimeout(async () => {
          try {
            const resp = await fetch(`/api/search?q=${encodeURIComponent(__searchQuery)}&limit=30`);
            if (resp.ok) {
              const data = await resp.json();
              if (data.status === 'ok' && data.items && data.items.length > 0) {
                const currentUrls = new Set((window.__allEntries || []).map(x => x.link || x.url));
                let added = false;
                for (const item of data.items) {
                  const u = item.url || item.link;
                  if (!currentUrls.has(u)) {
                    item._source = item.source || item._source || 'archivo';
                    item.link = u;
                    item.image = item.image_url || '';
                    item._parsedDate = item.published_date ? new Date(item.published_date).getTime() : 0;
                    window.__allEntries.push(item);
                    currentUrls.add(u);
                    added = true;
                  }
                }
                if (added) applyFilter();
              }
            }
          } catch (err) {
            // Modo offline / estático: el filtro local continúa funcionando normalmente
          }
        }, 350);
      }
    });

    if (searchClear) {
      searchClear.addEventListener('click', () => {
        searchInput.value = '';
        __searchQuery = '';
        searchClear.classList.remove('visible');
        searchInput.focus();
        applyFilter();
      });
    }
  }

  loadSources();
  loadCachedFeeds();
  await loadSourcesConfig();
  setupSourcesUI();
  sortSourcesUI();
  loadFeeds();
  fetchPodcastMeta();
  initPodcastPlayers();
  setInterval(() => { if (!document.hidden) refreshFeeds(); }, REFRESH_MS);

  // Abrir panel si se llega desde otra página (?panel=date|sources)
  const params = new URLSearchParams(location.search);
  const panel = params.get('panel');
  if (panel === 'sources') {
    sourcesBtn.click();
  } else if (panel === 'date') {
    dateBtn.click();
  }
});

// ── Estado del filtro de fecha ─────────────────────────────────────────────
// period: 'all' | 'year' | 'month' | 'week' | 'day' | 'month-specific'
// value:  null  | null   | null    | null   | null  | Date (primer día del mes)
let __dateFilter = { period: 'month', value: null };

const MONTH_NAMES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];

function setDateFilter(period, value) {
  __dateFilter = { period, value };
  applyFilter();
  updateDateBtnLabel();
  // Actualizar estado visual del panel
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

function updateDateBtnLabel() {
  const { period, value } = __dateFilter;
  const labels = {
    all: 'todas', year: 'este año', month: 'este mes',
    week: 'esta semana', day: 'hoy'
  };
  let label = labels[period] || 'todas';
  if (period === 'month-specific' && value) {
    label = `${MONTH_NAMES[value.getMonth()]} ${value.getFullYear()}`;
  }
  document.getElementById('date-btn-label').textContent = label;
  const isFiltered = period !== 'all';
  document.getElementById('date-btn').classList.toggle('active', isFiltered);
}

function getDateRange() {
  const now = new Date();
  const { period, value } = __dateFilter;
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

function isDateVisible(entry) {
  const range = getDateRange();
  if (!range) return true;
  const t = entry._parsedDate || 0;
  return t >= range.from && t <= range.to;
}

function buildMonthsGrid() {
  const container = document.getElementById('date-months');
  container.innerHTML = '';
  const now = new Date();
  const entries = window.__allEntries || [];

  // Generar los 12 últimos meses (del más reciente al más antiguo)
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

    if (__dateFilter.period === 'month-specific' && __dateFilter.value &&
        __dateFilter.value.getFullYear() === y && __dateFilter.value.getMonth() === m) {
      btn.classList.add('active');
    }

    if (count > 0) {
      btn.addEventListener('click', () => {
        setDateFilter('month-specific', new Date(y, m, 1));
        document.getElementById('date-panel').classList.add('hide');
        document.getElementById('date-btn').classList.remove('active');
        document.getElementById('date-btn').setAttribute('aria-expanded', 'false');
      });
    }
    container.appendChild(btn);
  }
}


let __allChecked = true;
let __sources = new Set();

function loadSources() {
  try {
    const saved = JSON.parse(localStorage.getItem(SOURCES_KEY));
    if (Array.isArray(saved)) {
      if (saved.length === 0) {
        __allChecked = true;
        __sources = new Set();
      } else {
        __allChecked = false;
        __sources = new Set(saved);
      }
    }
  } catch {}
}

function saveSources() {
  localStorage.setItem(SOURCES_KEY, JSON.stringify([...__sources]));
}

async function loadSourcesConfig() {
  try {
    const resp = await fetch('sources.json', { cache: 'no-store' });
    const data = await resp.json();
    if (Array.isArray(data) && data.length) {
      ALL_SOURCES = data.filter(s => s.enabled !== false).map(s => s.id);
      for (const s of data) {
        if (s.name) SOURCE_LABELS[s.id] = s.name;
      }
    }
  } catch {}
}

function setupSourcesUI() {
  const panel = document.getElementById('sources-panel');
  if (!panel) return;
  
  panel.innerHTML = '';
  const allRow = document.createElement('label');
  allRow.className = 'source-row all';
  allRow.id = 'source-all-row';
  allRow.innerHTML = `<input type="checkbox" id="chk-all" ${__allChecked ? 'checked' : ''}><span>Todas las fuentes</span><span class="src-count" id="count-all">0</span>`;
  panel.appendChild(allRow);

  const chkAll = allRow.querySelector('input');
  if (chkAll) {
    chkAll.addEventListener('change', (e) => {
      __allChecked = e.target.checked;
      __sources.clear();
      saveSources();
      applyFilter();
    });
  }

  ALL_SOURCES.forEach(src => {
    const labelText = getSourceLabel(src);
    const row = document.createElement('label');
    row.className = 'source-row';
    row.dataset.src = src;
    row.innerHTML = `<input type="checkbox" data-src="${src}"><span>${labelText}</span><span class="src-count" id="count-${src}">0</span>`;
    
    const input = row.querySelector('input');
    input.checked = isSourceVisible(src);
    input.addEventListener('change', (e) => {
      if (__allChecked) {
        __allChecked = false;
        ALL_SOURCES.forEach(s => {
          if (s !== src) __sources.add(s);
        });
      } else {
        if (e.target.checked) {
          __sources.add(src);
          if (__sources.size === ALL_SOURCES.length) {
            __allChecked = true;
            __sources.clear();
          }
        } else {
          __sources.delete(src);
        }
      }
      saveSources();
      applyFilter();
    });

    panel.appendChild(row);
  });
}

function normalizeGenericSource(sourceId) {
  return function(items) {
    return (items || []).map(i => ({
      _source: sourceId,
      _id: i.link || i._id || `${sourceId}-${i.title}`,
      _parsedDate: (i.date || i._parsedDate || i.pubDate) ? new Date(i.date || i._parsedDate || i.pubDate) : null,
      link: i.link,
      title: i.title,
      content: i.content || i.excerpt || i.description || '',
      thumbnail: i.thumbnail || ''
    }));
  };
}

const CUSTOM_FETCHERS = {
  colossal: fetchColossal,
  lomography: fetchLomography,
  booooooom: fetchBooooooom,
  tpj: fetchTpj,
  swan: fetchSwan,
  huck: fetchHuck,
  lensculture: fetchLensCulture,
  odlp: fetchOdlp,
  magnum: fetchMagnum,
  shootitwithfilm: fetchShootItWithFilm,
};

const CACHED_ENTRIES_KEY = 'feedfoto.cached_entries';

function loadCachedFeeds() {
  try {
    const raw = localStorage.getItem(CACHED_ENTRIES_KEY);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (Array.isArray(parsed) && parsed.length) {
        window.__rawEntries = parsed.map(i => ({
          ...i,
          _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null
        }));
        combineAndSortAllEntries();
      }
    }
  } catch {}
}

async function loadFeeds() {
  // 1. Carga inmediata desde caché local del navegador (0 ms)
  loadCachedFeeds();

  // 2. Carga ultra rápida del bundle consolidado feeds.json (~100 ms)
  let currentEntries = window.__rawEntries || [];
  try {
    const resp = await fetch('feeds.json', { cache: 'no-store' });
    if (resp.ok) {
      const data = await resp.json();
      if (data && Array.isArray(data.items) && data.items.length) {
        currentEntries = data.items.map(i => ({
          ...i,
          _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null
        }));
        window.__rawEntries = currentEntries;
        combineAndSortAllEntries();
        try {
          localStorage.setItem(CACHED_ENTRIES_KEY, JSON.stringify(data.items.slice(0, 200)));
        } catch {}
      }
    }
  } catch {}

  // 3. Autorecuperación: si alguna fuente de ALL_SOURCES no está en feeds.json, cargar su archivo individual en segundo plano
  const loadedSources = new Set(currentEntries.map(e => e._source));
  const missingSources = ALL_SOURCES.filter(s => !loadedSources.has(s));

  if (missingSources.length > 0) {
    const fetchers = missingSources.map(src => {
      if (CUSTOM_FETCHERS[src]) return CUSTOM_FETCHERS[src]();
      return fetchApiOrJson(`/api/${src}`, `${src}.json`, normalizeGenericSource(src));
    });
    const results = await Promise.allSettled(fetchers);
    const dynamicLoaded = results.flatMap(r => (r.status === 'fulfilled' && Array.isArray(r.value)) ? r.value : []);
    if (dynamicLoaded.length) {
      const seen = new Set(currentEntries.map(e => e._id || e.link));
      const newItems = dynamicLoaded.filter(e => !seen.has(e._id || e.link));
      if (newItems.length) {
        window.__rawEntries = [...currentEntries, ...newItems];
        combineAndSortAllEntries();
      }
    }
  }
}

function combineAndSortAllEntries() {
  const raw = window.__rawEntries || [];
  window.__allEntries = [...raw].sort((a, b) => (b._parsedDate || 0) - (a._parsedDate || 0));
  if (!window.__allEntries.length) { document.getElementById('loader').classList.add('hide'); return; }
  applyFilter();
}

async function refreshFeeds() {
  const scroll = window.scrollY;
  const modalOpen = !document.getElementById('modal').classList.contains('hide');
  await loadFeeds();
  if (!modalOpen) window.scrollTo(0, scroll);
}

async function fetchPodcastMeta() {
  try {
    const resp = await fetch('podcast_meta.json', { cache: 'no-store' });
    const data = await resp.json();
    if (!Array.isArray(data) || !data.length) return;
    const sorted = [...data].sort((a, b) => String(a.date).localeCompare(String(b.date)));
    
    window.__podcastEntries = sorted.map((e, idx) => {
      const num = idx + 1;
      return {
        _source: 'podcast',
        _id: 'podcast-' + e.date,
        _parsedDate: new Date(e.date + 'T00:00:00'),
        date: e.date,
        title: `Episodio ${num} · ${e.podcast_title || 'Resumen Diario'}`,
        podcast_title: e.podcast_title || 'Resumen Diario',
        description: e.description || '',
        num: num,
        duration: e.duration,
        images: e.images || [],
        image: e.image || PODCAST_COVER,
        link: `${PODCAST_RELEASE}/podcast-${e.date}.mp3`,
        is_podcast_entry: true
      };
    });
    
    combineAndSortAllEntries();
    renderPodcastHero();
  } catch {}
}

function setPodcastImage(imgEl, entry) {
  if (!imgEl || !entry) return;
  const date = entry.date || '';
  let stage = 0;
  
  imgEl.onerror = function() {
    stage++;
    if (stage === 1 && date) {
      this.src = 'assets/covers/podcast-cover-' + date + '.jpg';
      return;
    }
    if (stage === 2 && entry.image && entry.image !== this.src) {
      this.src = entry.image;
      return;
    }
    if (stage <= 3) {
      this.src = PODCAST_COVER;
      return;
    }
    this.onerror = null;
  };

  const releaseCover = `${PODCAST_RELEASE}/podcast-cover-${date}.jpg`;
  imgEl.src = releaseCover;
}

function renderPodcastHero() {
  const hero = document.getElementById('podcast-hero');
  const entries = window.__podcastEntries || [];
  if (!hero || !entries.length) return;
  const latest = entries[entries.length - 1];
  const img = document.getElementById('podcast-hero-img');
  if (img) setPodcastImage(img, latest);
  const title = document.getElementById('podcast-hero-title');
  if (title) title.textContent = latest.podcast_title;
  const meta = document.getElementById('podcast-hero-meta');
  if (meta) meta.textContent = 'episodio ' + latest.num + ' · ' + fmtDate(new Date(latest.date + 'T00:00:00')) + ' · ' + fmtDur(latest.duration);
  const resumen = document.getElementById('podcast-hero-resumen');
  if (resumen) resumen.onclick = (e) => { e.preventDefault(); openPodcastResumen(latest); };
  const player = document.getElementById('podcast-hero-player');
  if (player) {
    player.dataset.url = latest.link;
    const time = player.querySelector('.podcast-time');
    if (time) time.textContent = '0:00 / ' + (latest.duration ? fmtDur(latest.duration) : '--:--');
  }
  hero.classList.remove('hide');
}

function openPodcastResumen(e) {
  const body = document.getElementById('modal-body');
  if (!body) return;
  body.innerHTML =
    '<div class="modal-tools">' +
    '<button class="modal-tool-btn" onclick="closeModal()">← Volver</button>' +
    '</div>' +
    '<div class="modal-title-group">' +
    '<h2 class="modal-title">' + esc(e.podcast_title || 'Resumen Diario') + '</h2>' +
    '<div class="modal-meta"><span class="modal-source">Podcast · Punto de vista</span></div>' +
    '</div>' +
    '<div class="modal-article"><div class="modal-article-content">' +
    (e.description ? fmtDesc(e.description) : '<p style="opacity:0.4">Sin descripción</p>') +
    '</div></div>';
  document.getElementById('modal').classList.remove('hide');
}

async function fetchColossal() {
  const all = new Map();
  for (let page = 1; page <= 3; page++) {
    let data;
    try { data = await (await fetch(`${WP_API}&page=${page}`)).json(); } catch {}
    if (!Array.isArray(data) || !data.length) break;
    for (const p of data) {
      if (all.has(p.id)) continue;
      all.set(p.id, {
        _source: 'colossal',
        _id: p.id,
        _parsedDate: new Date(p.date),
        link: p.link,
        title: p.title.rendered,
        content: p.content.rendered
      });
    }
  }
  return [...all.values()];
}

async function fetchLomography() {
  return fetchApiOrJson('/api/lomography', 'lomography.json', normalizeLomo);
}

function normalizeLomo(items) {
  return items.map(i => ({
    _source: 'lomography',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchWithTimeout(url, ms) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { signal: ctrl.signal });
  } finally {
    clearTimeout(t);
  }
}

function extractRssThumb(html) {
  const m = (html || '').match(/<img[^>]+src="([^"]+)"/);
  if (!m) return null;
  if (/facebook\.com|google|tracking/.test(m[1].toLowerCase())) return null;
  return m[1];
}

async function fetchRssLive(source, feedUrls) {
  for (const proxy of RSS_PROXIES) {
    try {
      const items = [];
      const seen = new Set();
      for (const url of feedUrls) {
        const resp = await fetchWithTimeout(proxy(url), 12000);
        if (!resp.ok) continue;
        const text = await resp.text();
        const doc = new DOMParser().parseFromString(text, 'application/xml');
        for (const el of [...doc.querySelectorAll('item')]) {
          const title = el.querySelector('title')?.textContent?.trim();
          const link = el.querySelector('link')?.textContent?.trim();
          if (!title || !link) continue;
          const key = title.toLowerCase().replace(/[^a-z0-9]/g, '').slice(0, 40);
          if (seen.has(key)) continue;
          seen.add(key);
          const pub = el.querySelector('pubDate')?.textContent?.trim();
          const content = el.querySelector('content\\:encoded, description')?.textContent || '';
          items.push({
            _source: source,
            _id: link,
            _parsedDate: pub ? new Date(pub) : null,
            link,
            title,
            content,
            thumbnail: extractRssThumb(content)
          });
        }
      }
      if (items.length) return items;
    } catch {}
  }
  return null;
}

async function fetchApiOrJson(apiPath, jsonFile, normalize) {
  try {
    const resp = await fetch(apiPath);
    const data = await resp.json();
    if (data && data.status === 'ok' && data.items.length) return normalize(data.items);
  } catch {}
  try {
    const resp = await fetch(jsonFile, { cache: 'no-store' });
    const data = await resp.json();
    if (data && data.items) return normalize(data.items);
  } catch {}
  return [];
}

function enrichContent(live, fallback) {
  const byLink = new Map((fallback || []).map(i => [i.link, i]));
  return live.map(i => {
    const f = byLink.get(i.link);
    if (!f) return i;
    const merged = { ...i };
    if ((f.content || '').length > (i.content || '').length) merged.content = f.content;
    if (!merged.thumbnail && f.thumbnail) merged.thumbnail = f.thumbnail;
    return merged;
  });
}

async function fetchBooooooom() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('booooooom', BOOM_FEEDS),
    fetchApiOrJson('/api/booooooom', 'booooooom.json', normalizeBoom),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

function normalizeBoom(items) {
  return items.map(i => ({
    _source: 'booooooom',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchTpj() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('tpj', TPJ_FEEDS),
    fetchApiOrJson('/api/tpj', 'tpj.json', normalizeTpj),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

function normalizeTpj(items) {
  return items.map(i => ({
    _source: 'tpj',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchSwan() {
  return fetchApiOrJson('/api/swan', 'swan.json', normalizeSwan);
}

function normalizeSwan(items) {
  return items.map(i => ({
    _source: 'swan',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchHuck() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('huck', HUCK_FEEDS),
    fetchApiOrJson('/api/huck', 'huck.json', normalizeHuck),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

function normalizeHuck(items) {
  return items.map(i => ({
    _source: 'huck',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchLensCulture() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('lensculture', LENSCULTURE_FEEDS),
    fetchApiOrJson('/api/lensculture', 'lensculture.json', normalizeLensCulture),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

function normalizeLensCulture(items) {
  return items.map(i => ({
    _source: 'lensculture',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchOdlp() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('odlp', ODLP_FEEDS),
    fetchApiOrJson('/api/odlp', 'odlp.json', normalizeOdlp),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

function normalizeOdlp(items) {
  return items.map(i => ({
    _source: 'odlp',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchMagnum() {
  const fallback = await fetchApiOrJson('/api/magnum', 'magnum.json', normalizeMagnum);
  return fallback;
}

function normalizeMagnum(items) {
  return items.map(i => ({
    _source: 'magnum',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

async function fetchShootItWithFilm() {
  return fetchApiOrJson('/api/shootitwithfilm', 'shootitwithfilm.json', normalizeShootItWithFilm);
}

function normalizeShootItWithFilm(items) {
  return items.map(i => ({
    _source: 'shootitwithfilm',
    _id: i.link || i._id,
    _parsedDate: (i.date || i._parsedDate) ? new Date(i.date || i._parsedDate) : null,
    link: i.link,
    title: i.title,
    content: i.content || i.excerpt,
    thumbnail: i.thumbnail
  }));
}

function extractImg(post) {
  let img = post.thumbnail;
  if (!img) {
    const m = (post.content || '').match(/<img[^>]+src=["']([^"']+)["']/i);
    img = m ? m[1] : null;
  }
  if (!img) {
    const m = (post.content || '').match(/data-orig-file=["']([^"']+)["']/i) ||
              (post.content || '').match(/srcset=["']([^"'\s,]+)/i);
    img = m ? m[1] : null;
  }
  if (img && img.includes('kosmofoto.com') && !img.includes('i0.wp.com')) {
    img = 'https://i0.wp.com/' + img.replace(/^https?:\/\//, '');
  }
  return img;
}

function isSourceVisible(src) {
  if (__allChecked) return true;
  return __sources.has(src);
}

function isMobile() {
  return window.matchMedia('(max-width: 720px)').matches;
}

let __searchQuery = '';

function isSearchMatch(e, q) {
  if (!q) return true;
  const terms = q.toLowerCase().split(/\s+/).filter(Boolean);
  const photo = e.photographer || (e.photographers ? e.photographers.join(' ') : '');
  const text = `${e.title || ''} ${photo} ${e.summary || ''} ${e.excerpt || ''} ${e.content || ''} ${e._source || ''}`.toLowerCase();
  return terms.every(t => text.includes(t));
}

let __visibleLimit = 36;
const PAGE_SIZE = 36;
let __currentFilteredEntries = [];
let __scrollObserver = null;

function applyFilter(resetLimit = true) {
  if (resetLimit) {
    __visibleLimit = PAGE_SIZE;
  }
  const entries = (window.__allEntries || [])
    .filter(e => isSourceVisible(e._source))
    .filter(e => isDateVisible(e))
    .filter(e => isSearchMatch(e, __searchQuery));
  __currentFilteredEntries = entries;
  render(entries);

  const chkAll = document.getElementById('chk-all');
  if (chkAll) chkAll.checked = __allChecked;

  ALL_SOURCES.forEach(src => {
    const el = document.querySelector(`.source-row[data-src="${src}"] input`);
    if (el) el.checked = isSourceVisible(src);
  });

  const countEl = document.getElementById('sources-btn-count');
  if (countEl) {
    countEl.textContent = __allChecked
      ? 'todas'
      : (__sources.size === 0 ? 'ninguna' : (__sources.size === 1 ? getSourceLabel([...__sources][0]) : `${__sources.size} activas`));
  }
  const sb = document.getElementById('sources-btn');
  if (sb) sb.classList.toggle('active', !__allChecked && __sources.size > 0);
}

function forceEagerImages() {
  const body = document.getElementById('modal-body');
  if (!body) return;
  body.querySelectorAll('img[loading="lazy"]').forEach(img => img.removeAttribute('loading'));
}

function esc(s) {
  return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function splitItems(desc) {
  if (!desc) return [];
  return desc.split(/\n{2,}|(?=\*\*)/).map(s => s.trim()).filter(Boolean);
}

function fmtDesc(desc) {
  const items = splitItems(desc);
  if (items.length <= 1) return esc(desc);
  return items.map(i => '<p style="margin:0 0 0.6rem">' + esc(i) + '</p>').join('');
}

function fmtDur(sec) {
  sec = parseInt(sec || 0, 10);
  if (!sec) return '';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

function podcastCardHTML() {
  return '';
}

function getSourceLabel(src) {
  return SOURCE_LABELS[src] || src;
}

function renderCard(e) {
  const isPodcast = e.is_podcast_entry;
  const src = isPodcast ? e.image : extractImg(e);
  const sourceLabel = isPodcast ? 'Podcast · Punto de vista' : getSourceLabel(e._source);
  const linkHref = isPodcast ? '#' : e.link;
  const cardId = String(e._id || e.link || `${e._source}-${e.title}`);
  return `<div class="card" data-color="?" data-id="${encodeURIComponent(cardId)}" data-source="${e._source}" onclick="openModal(this)">
    <div class="card-inner">
      <div class="card-skeleton"></div>
      ${src ? `<img class="card-image" src="${src}" alt="" loading="lazy" referrerpolicy="no-referrer" onload="imgLoaded(this)" onerror="imgError(this)">` : ''}
      <div class="card-overlay"></div>
    </div>
    <div class="card-info">
      <div class="card-source">${sourceLabel}</div>
      <div class="card-title"><a href="${linkHref}" target="_blank" rel="noopener" onclick="event.stopPropagation()">${e.title}</a></div>
      <div class="card-meta">
        <span class="card-date">${e._parsedDate ? fmtDate(e._parsedDate) : ''}</span>
      </div>
    </div>
  </div>`;
}

function render(entries) {
  const el = document.getElementById('entries');
  const all = window.__allEntries || [];
  const displayItems = entries.slice(0, __visibleLimit);

  let html = podcastCardHTML() + displayItems.map(renderCard).join('');
  
  if (entries.length > __visibleLimit) {
    html += `
      <div id="scroll-sentinel" class="scroll-sentinel" style="grid-column: 1 / -1; text-align: center; padding: 2.5rem 0; color: #888; font-size: 0.9rem;">
        <span style="color:#ff0100">●</span> Cargando más publicaciones del archivo…
      </div>
    `;
  } else if (entries.length > 0 && __dateFilter.period !== 'all') {
    html += `
      <div class="archive-end-notice" style="grid-column: 1 / -1; text-align: center; padding: 2.5rem 1rem; color: #888; font-size: 0.9rem; border-top: 1px solid rgba(255,255,255,0.06); margin-top: 2rem;">
        <p style="margin-bottom: 0.8rem; color: #aaa;">Has visto todas las publicaciones de este período (${entries.length} fotografías)</p>
        <button type="button" class="sources-btn" style="display:inline-block; margin:0 auto; cursor:pointer;" onclick="setDateFilter('all', null)">
          Explorar todo el archivo histórico completo (860+ fotos) →
        </button>
      </div>
    `;
  }

  el.innerHTML = html;
  document.getElementById('loader').classList.add('hide');

  setupInfiniteScroll();

  // Contadores globales por cada fuente
  const counts = {};
  for (const e of all) {
    if (e._source) counts[e._source] = (counts[e._source] || 0) + 1;
  }
  for (const src of ALL_SOURCES) {
    const countEl = document.getElementById(`count-${src}`);
    if (countEl) countEl.textContent = String(counts[src] || 0);
  }
  const elAll = document.getElementById('count-all');
  if (elAll) elAll.textContent = String(all.length);
  const elFooter = document.getElementById('footer-info');
  if (elFooter) elFooter.textContent = displayItems.length + ' de ' + entries.length + ' fotografías';
}

function setupInfiniteScroll() {
  if (__scrollObserver) {
    __scrollObserver.disconnect();
    __scrollObserver = null;
  }
  const sentinel = document.getElementById('scroll-sentinel');
  if (!sentinel) return;

  __scrollObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      if (__visibleLimit < __currentFilteredEntries.length) {
        __visibleLimit += PAGE_SIZE;
        render(__currentFilteredEntries);
      }
    }
  }, { rootMargin: '350px' });

  __scrollObserver.observe(sentinel);
}

function fmtDate(d) {
  return d.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });
}

function fmtDateLong(d) {
  return d.toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' });
}

function imgLoaded(img) {
  img.classList.add('loaded');
  const card = img.closest('.card');
  card.querySelector('.card-skeleton')?.remove();
  const overlay = card.querySelector('.card-overlay');
  if (card.dataset.color === '?') {
    card.dataset.color = '0';
  }
}

function imgError(img) {
  if (!img.dataset.retried) {
    img.dataset.retried = '1';
    const src = img.src;
    if (src && !src.includes('i0.wp.com') && (src.includes('kosmofoto.com') || src.includes('wp-content'))) {
      img.src = 'https://i0.wp.com/' + src.replace(/^https?:\/\//, '');
      return;
    }
  }
  img.remove();
  const card = img.closest('.card');
  card?.querySelector('.card-skeleton')?.remove();
  card?.querySelector('.card-overlay')?.remove();
  const info = card?.querySelector('.card-info');
  if (info) info.style.opacity = '1';
  if (card && card.dataset.color === '?') {
    card.dataset.color = '1';
  }
}


function cleanContent(html) {
  const doc = new DOMParser().parseFromString(`<div id="__root">${html}</div>`, 'text/html');
  const root = doc.getElementById('__root');
  root.querySelectorAll('div.entry-header, div.post-title, div.post-meta, div.post-share-group, .wp-block-spacer, div[style*="height:"], div[aria-hidden="true"]').forEach(el => el.remove());
  return root.innerHTML;
}

function extractImages(html) {
  const items = [];
  const seen = new Set();
  const imgRe = /<img[^>]+src="([^"]+)"/g;
  let m;
  while ((m = imgRe.exec(html)) !== null) {
    const url = m[1];
    if (seen.has(url)) continue;
    seen.add(url);
    const before = html.substring(0, m.index);
    const inFigure = before.lastIndexOf('<figure') > before.lastIndexOf('</figure>');
    let caption = '';
    if (inFigure) {
      const after = html.substring(m.index);
      const capMatch = after.match(/<figcaption[^>]*>([\s\S]*?)<\/figcaption>/);
      if (capMatch && capMatch.index < (after.indexOf('</figure>') === -1 ? Infinity : after.indexOf('</figure>'))) {
        caption = capMatch[1].replace(/<[^>]+>/g, '').trim();
      }
    }
    items.push({ url, caption });
  }
  return items;
}

function extractColossalPhotographers(html) {
  const doc = new DOMParser().parseFromString(html, 'text/html');
  const list = [];
  const seen = new Set();
  doc.querySelectorAll('figcaption a[href]').forEach(a => {
    const name = a.textContent.trim();
    const href = a.getAttribute('href');
    if (name && href && !seen.has(name.toLowerCase())) {
      seen.add(name.toLowerCase());
      list.push({ name, url: href });
    }
  });
  return list;
}

function isShareLink(url) {
  return /facebook\.com\/(?:sharer|sharing|dialog\/share|plugins|login|share)/.test(url.toLowerCase());
}

function isOwnDomain(href) {
  try {
    const h = new URL(href).hostname.toLowerCase();
    return h.endsWith('thisiscolossal.com') || h.endsWith('lomography.com') || h.endsWith('booooooom.com');
  } catch {
    return false;
  }
}

const WEBSITE_TEXT_RE = /\b(?:web[\s-]*site|web[\s-]*shop|portfolio)\b|\bweb\b|\bsite\b/i;

function extractSocialLinks(html) {
  const doc = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html');
  const links = [];
  const seen = new Set();
  const seenYT = new Set();
  doc.querySelectorAll('a[href]').forEach(a => {
    const href = a.getAttribute('href');
    const text = a.textContent.trim();
    if (!href || !text) return;
    let url = href;
    const h = href.toLowerCase();
    if (h.includes('instagram.com')) {
      const m = href.match(/instagram\.com\/([^/?]+)/);
      const label = m ? m[1] : 'Instagram';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'instagram', text: label, url }); }
    } else if (h.includes('youtube.com') || h.includes('youtu.be')) {
      let channel, label;
      const atM = href.match(/youtube\.com\/@([^/?]+)/);
      const userM = href.match(/youtube\.com\/user\/([^/?]+)/);
      const cM = href.match(/youtube\.com\/c\/([^/?]+)/);
      const chM = href.match(/youtube\.com\/channel\/([^/?]+)/);
      if (atM) { channel = atM[1].toLowerCase(); label = atM[1]; }
      else if (userM) { channel = userM[1].toLowerCase(); label = userM[1]; }
      else if (cM) { channel = cM[1].toLowerCase(); label = 'Canal'; }
      else if (chM) { channel = chM[1]; label = 'Canal'; }
      else if (href.match(/youtube\.com\/watch\b/) || href.match(/youtu\.be\//)) { label = 'Video'; }
      if (channel && seenYT.has(channel)) return;
      if (channel) seenYT.add(channel);
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'youtube', text: label || 'YouTube', url }); }
    } else if (h.includes('twitter.com') || h.includes('x.com')) {
      const m = href.match(/(?:twitter|x)\.com\/([^/?]+)/);
      const label = m ? m[1] : 'X';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'x', text: label, url }); }
    } else if (h.includes('vimeo.com')) {
      const m = href.match(/vimeo\.com\/([^/?]+)/);
      const label = m ? m[1] : 'Vimeo';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'vimeo', text: label, url }); }
    } else if (h.includes('flickr.com')) {
      const m = href.match(/flickr\.com\/([^/?]+)/);
      const label = m ? m[1] : 'Flickr';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'flickr', text: label, url }); }
    } else if (h.includes('tiktok.com')) {
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'tiktok', text: 'TikTok', url }); }
    } else if (h.includes('facebook.com')) {
      if (isShareLink(url)) return;
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'facebook', text: text, url }); }
    } else if (h.includes('bsky.app')) {
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'bluesky', text: text, url }); }
    } else if (h.includes('threads.net')) {
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'threads', text: text, url }); }
    } else if (h.includes('smugmug.com')) {
      const m = href.match(/([a-zA-Z0-9_-]+)\.smugmug\.com/i);
      const label = m ? m[1] : 'SmugMug';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'web', text: `Portfolio · ${label}`, url }); }
    } else if (h.includes('behance.net')) {
      const m = href.match(/behance\.net\/([^/?]+)/i);
      const label = m ? m[1] : 'Behance';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'web', text: `Behance · ${label}`, url }); }
    } else if (h.includes('500px.com')) {
      const m = href.match(/500px\.com\/p\/([^/?]+)/i) || href.match(/500px\.com\/([^/?]+)/i);
      const label = m ? m[1] : '500px';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'web', text: `500px · ${label}`, url }); }
    } else if (h.includes('vsco.co')) {
      const m = href.match(/vsco\.co\/([^/?]+)/i);
      const label = m ? m[1] : 'VSCO';
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'web', text: `VSCO · ${label}`, url }); }
    } else if (WEBSITE_TEXT_RE.test(text) && /^https?:\/\//i.test(href) && !isOwnDomain(href)) {
      try { url = new URL(href).origin + '/'; } catch { return; }
      if (!seen.has(url)) { seen.add(url); links.push({ platform: 'web', text: 'Web', url }); }
    } else if (/^https?:\/\/[^\s<>"']+/i.test(text.trim()) && !isOwnDomain(href)) {
      // Si el texto del link es la propia URL cruda, extraer como botón Web
      if (!seen.has(url)) {
        try {
          const uObj = new URL(url);
          const domainLabel = uObj.hostname.replace(/^www\./, '');
          links.push({ platform: 'web', text: `Web · ${domainLabel}`, url });
        } catch {
          links.push({ platform: 'web', text: 'Web', url });
        }
        seen.add(url);
      }
    }
  });
  const order = ['instagram', 'youtube', 'x', 'vimeo', 'flickr', 'tiktok', 'facebook', 'bluesky', 'threads', 'web'];
  links.sort((a, b) => order.indexOf(a.platform) - order.indexOf(b.platform));
  return links;
}

function renderLomoArticle(body, entry, data) {
  const images = data.images || [];
  const cleanContent = (data.content || '')
    .replace(/!Image\s*\d+/g, '')
    .replace(/©\s*toms\.portra\s*\|.*$/gm, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();
  const creditsHTML = (data.credits && data.credits.length) ? '<div class="modal-photographers"><span class="photographer-label">Fotógrafos</span>' + data.credits.map(c => '<a href="' + c.url + '" target="_blank" rel="noopener" class="photographer-link">' + c.name + '</a>').join(', ') + '</div>' : '';
  const lomoLinks = data.content ? extractSocialLinks(data.content) : [];
  const linksHTML = lomoLinks.length ? '<div class="modal-links">' + lomoLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  const galleryCaption = '© toms.portra | Camera: Lomo MC-A | Film: LomoChrome Color \'92 Sun-kissed ISO 400 | Model: lynjunei';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">Lomography Magazine</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${cleanContent}</div>
      ${creditsHTML}
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.alt || galleryCaption })));
}

function renderLensCultureArticle(body, entry, data) {
  const images = data.images || [];
  const socialLinks = data.content ? extractSocialLinks(data.content) : [];
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">LensCulture</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${data.content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.alt || '' })));
}

function renderOdlpArticle(body, entry, data) {
  const images = data.images || [];
  const rawContent = data.content || '';
  const socialLinks = rawContent ? extractSocialLinks(rawContent) : [];
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';

  // Limpiar enlaces crudos que ya se muestran en los botones superiores y coletillas
  const cleanContent = rawContent
    .replace(/<p>\s*<a[^>]+href="https?:\/\/[^"]+"[^>]*>https?:\/\/[^<]+<\/a>\s*<\/p>/gi, '')
    .replace(/(?:^|\n)\s*https?:\/\/[^\s<>"']+\s*(?:\n|$)/gi, '\n')
    .replace(/Cet article [^.]+ est apparu en premier sur The Eye of Photography Magazine\.?/gi, '')
    .replace(/\n{3,}/g, '\n\n')
    .trim();

  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">L'Œil de la Photographie</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${cleanContent}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.alt || '' })));
}

function renderMagnumArticle(body, entry, data) {
  const images = data.images || [];
  const socialLinks = data.content ? extractSocialLinks(data.content) : [];
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">Magnum Photos</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${data.content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.alt || '' })));
}

function renderBoomArticle(body, entry, data) {
  const images = data.images || [];
  const creditLinks = (data.credits || []).filter(c => !isShareLink(c.url)).map(c => ({ platform: c.platform || 'web', text: c.name, url: c.url }));
  const socialLinks = data.content ? extractSocialLinks(data.content) : [];
  const boomLinks = [...creditLinks, ...socialLinks];
  const linksHTML = boomLinks.length ? '<div class="modal-links">' + boomLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">Booooooom</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${data.content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.alt || '' })));
}

function renderTpjArticle(body, entry) {
  const content = cleanContent(entry.content || '');
  const images = extractImages(content);
  const socialLinks = extractSocialLinks(content);
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">The Photographic Journal</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.caption || '' })));
}

function renderSwanArticle(body, entry, data) {
  const images = data.images || [];
  const thumb = data.thumbnail || entry.thumbnail;
  const thumbHTML = (!images.length && thumb) ? `<div class="modal-article" style="padding-bottom:0"><img src="${thumb}" alt="" class="modal-swan-thumb" loading="lazy"></div>` : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${thumbHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">Swann Galleries</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${data.content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.alt || '' })));
}

function renderHuckArticle(body, entry) {
  const content = cleanContent(entry.content || '');
  const images = extractImages(content);
  const socialLinks = extractSocialLinks(content);
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">Huck Magazine</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.caption || '' })));
}

function renderShootItWithFilmArticle(body, entry) {
  const content = cleanContent(entry.content || '');
  const images = extractImages(content);
  const socialLinks = extractSocialLinks(content);
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">Shoot It With Film</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.caption || '' })));
}

function renderGenericArticle(body, entry) {
  const content = cleanContent(entry.content || entry.excerpt || '');
  const images = extractImages(content);
  if (!images.length && entry.thumbnail) {
    images.push({ url: entry.thumbnail, caption: '' });
  }
  const socialLinks = extractSocialLinks(content);
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  const sourceName = getSourceLabel(entry._source);
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">${sourceName}</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${content || '<p>Contenido completo disponible en el sitio web original.</p>'}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.caption || '' })));
}

async function openModal(card) {
  const rawId = decodeURIComponent(card.dataset.id || '');
  const source = card.dataset.source;
  incrementReadCount(source);
  const body = document.getElementById('modal-body');
  body.innerHTML = '<div class="modal-loading">cargando…</div>';
  document.getElementById('modal').classList.remove('hide');
  setTimeout(forceEagerImages, 0);

  if (source === 'podcast') {
    document.getElementById('modal').classList.add('hide');
    const entry = window.__allEntries?.find(e => String(e._id) === rawId || e.link === rawId);
    if (entry) playPodcastInBar(entry);
    return;
  }

  playClickOpen();

  // Buscar el artículo de forma robusta por _id, por link o por título exacto
  const cardTitle = card.querySelector('.card-title a')?.textContent?.trim() || '';
  const entry = window.__allEntries?.find(e => 
    (e._id != null && String(e._id) === rawId) || 
    (e.link && String(e.link) === rawId) ||
    (String(e._id || e.link) === rawId) ||
    (cardTitle && e.title && e.title.trim() === cardTitle)
  );

  if (!entry) {
    body.innerHTML = `
      <div class="modal-tools">
        <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
      </div>
      <div class="modal-article">
        <p class="modal-error">No se pudo localizar el artículo seleccionado.</p>
      </div>
    `;
    return;
  }

  // Lomography
  if (source === 'lomography') {
    let data = null;
    try {
      const resp = await fetch(`/api/lomography/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetch('lomography_articles.json');
        const cache = await resp.json();
        const cached = (cache.articles || cache)[entry.link];
        if (cached && cached.status === 'ok') data = cached;
      } catch {}
    }
    if (data) {
      renderLomoArticle(body, entry, data);
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // Booooooom
  if (source === 'booooooom') {
    let data = null;
    try {
      const resp = await fetch(`/api/booooooom/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetch('booooooom_articles.json');
        const cache = await resp.json();
        const cached = (cache.articles || cache)[entry.link];
        if (cached && cached.status === 'ok') data = cached;
      } catch {}
    }
    if (data) {
      renderBoomArticle(body, entry, data);
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // The Photographic Journal
  if (source === 'tpj') {
    renderTpjArticle(body, entry);
    return;
  }

  // Swann Galleries
  if (source === 'swan') {
    let data = null;
    try {
      const resp = await fetch(`/api/swan/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetch('swan_articles.json');
        const cache = await resp.json();
        const cached = (cache.articles || cache)[entry.link];
        if (cached && cached.status === 'ok') data = cached;
      } catch {}
    }
    if (data) {
      renderSwanArticle(body, entry, data);
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // Huck Magazine
  if (source === 'huck') {
    renderHuckArticle(body, entry);
    return;
  }

  // LensCulture
  if (source === 'lensculture') {
    let data = null;
    try {
      const resp = await fetch(`/api/lensculture/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetch('lensculture_articles.json');
        const cache = await resp.json();
        const cached = (cache.articles || cache)[entry.link];
        if (cached && cached.status === 'ok') data = cached;
      } catch {}
    }
    if (data) {
      renderLensCultureArticle(body, entry, data);
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // L'Œil de la Photographie
  if (source === 'odlp') {
    let data = null;
    try {
      const resp = await fetch(`/api/odlp/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetch('odlp_articles.json');
        const cache = await resp.json();
        const cached = (cache.articles || cache)[entry.link];
        if (cached && cached.status === 'ok') data = cached;
      } catch {}
    }
    if (data) {
      renderOdlpArticle(body, entry, data);
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // Magnum Photos
  if (source === 'magnum') {
    let data = null;
    try {
      const resp = await fetch(`/api/magnum/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetch('magnum_articles.json');
        const cache = await resp.json();
        const cached = (cache.articles || cache)[entry.link];
        if (cached && cached.status === 'ok') data = cached;
      } catch {}
    }
    if (data) {
      renderMagnumArticle(body, entry, data);
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // Colossal
  if (source === 'colossal') {
    if (entry.content) {
      const images = extractImages(entry.content);
      const cleaned = cleanContent(entry.content);
      const photographers = extractColossalPhotographers(entry.content);
      const photoHTML = photographers.length ? '<div class="modal-photographers"><span class="photographer-label">Fotógrafos</span>' + photographers.map(p => '<a href="' + p.url + '" target="_blank" rel="noopener" class="photographer-link">' + p.name + '</a>').join(', ') + '</div>' : '';
      const colossalLinks = extractSocialLinks(entry.content);
      const linksHTML = colossalLinks.length ? '<div class="modal-links">' + colossalLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
      
      body.innerHTML = `
        <div class="modal-tools">
          ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
          <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
          <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
        </div>
        ${photoHTML}
        ${linksHTML}
        <div class="modal-title-group">
          <h2 class="modal-title">${entry.title}</h2>
          <div class="modal-meta">
            <span class="modal-source">Colossal · Fotografía</span>
            <span class="modal-sep">·</span>
            <span class="modal-date">${entry._parsedDate ? fmtDate(entry._parsedDate) : ''}</span>
          </div>
        </div>
        <div class="modal-article">
          <div class="modal-article-content">${cleaned}</div>
          <div class="modal-footer" style="padding-top:2rem">
            <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
          </div>
        </div>
      `;
      body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.caption || '' })));
      return;
    }
  // 35mmc, EMULSIVE, Huck, Phroom
  if (['35mmc', 'emulsive', 'huck', 'phroom'].includes(source)) {
    let data = null;
    try {
      const resp = await fetch(`/api/${source}/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetch(`${source}_articles.json`);
        const cache = await resp.json();
        const cached = (cache.articles || cache)[entry.link];
        if (cached && cached.status === 'ok') data = cached;
      } catch {}
    }
    if (data) {
      renderCachedArticle(body, entry, data, getSourceLabel(source));
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // Todas las demás fuentes (Shoot It With Film, Kosmo Foto, C41, Feature Shoot, Ain't-Bad, etc.)
  renderGenericArticle(body, entry);
}

function renderCachedArticle(body, entry, data, sourceLabel) {
  const content = cleanContent(data.content || entry.content || entry.excerpt || '');
  const images = (data.images && data.images.length) ? data.images : extractImages(content);
  if (!images.length && (data.thumbnail || entry.thumbnail)) {
    images.push({ url: data.thumbnail || entry.thumbnail, alt: '' });
  }
  const socialLinks = extractSocialLinks(content);
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';

  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
    <div class="modal-title-group">
      <h2 class="modal-title">${entry.title}</h2>
      <div class="modal-meta">
        <span class="modal-source">${sourceLabel || getSourceLabel(entry._source)}</span>
        ${entry._parsedDate ? '<span class="modal-sep">·</span><span class="modal-date">' + fmtDate(entry._parsedDate) + '</span>' : ''}
      </div>
    </div>
    <div class="modal-article">
      <div class="modal-article-content">${content}</div>
      <div class="modal-footer" style="padding-top:2rem">
        <a href="${entry.link}" target="_blank" rel="noopener" class="modal-link-tag">Ver original →</a>
      </div>
    </div>
  `;
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url || i, caption: i.alt || i.caption || '' })));
}

function openGallery() {
  const body = document.getElementById('modal-body');
  const article = body.querySelector('.modal-article');
  const titleGroup = body.querySelector('.modal-title-group');
  let images;
  if (body.dataset.lomoImages) {
    images = JSON.parse(body.dataset.lomoImages);
  } else if (article) {
    images = extractImages(article.querySelector('.modal-article-content')?.innerHTML || '');
  }
  if (!images || !images.length) return;

  article.style.display = 'none';
  titleGroup.style.display = 'none';
  body.dataset.mode = 'gallery';
  body.querySelector('.modal-tools').style.display = 'none';

  const gallery = document.createElement('div');
  gallery.className = 'modal-gallery';

  window.__galleryState = { currentIdx: 0, images };

  const updateGallery = () => {
    const s = window.__galleryState;
    if (!s) return;
    const img = s.images[s.currentIdx];
    gallery.innerHTML = `
      <div class="gallery-top">
        <button class="gallery-back" onclick="closeGallery()">← Volver</button>
        <span class="gallery-counter">${s.currentIdx + 1} / ${s.images.length}</span>
      </div>
      <div class="gallery-stage">
        <button class="gallery-nav gallery-prev" onclick="navGallery(-1)" ${s.currentIdx === 0 ? 'style="opacity:0.2;pointer-events:none"' : ''}>‹</button>
        <div class="gallery-frame">
          <img src="${img.url}" alt="" class="gallery-img" loading="lazy">
          ${img.caption ? `<div class="gallery-caption">${img.caption}</div>` : ''}
        </div>
        <button class="gallery-nav gallery-next" onclick="navGallery(1)" ${s.currentIdx === s.images.length - 1 ? 'style="opacity:0.2;pointer-events:none"' : ''}>›</button>
      </div>
    `;
    resetAuto();
  };

  const resetAuto = () => {
    clearTimeout(window.__galleryState.autoTimer);
    window.__galleryState.autoTimer = setTimeout(() => {
      const s = window.__galleryState;
      if (!s) return;
      if (s.currentIdx >= s.images.length - 1) {
        closeGallery();
        return;
      }
      navGallery(1);
    }, 3000);
  };

  window.__galleryState.updateGallery = updateGallery;
  updateGallery();
  body.appendChild(gallery);

  gallery.addEventListener('mouseenter', () => {
    clearTimeout(window.__galleryState?.autoTimer);
  });
  gallery.addEventListener('mouseleave', () => {
    if (window.__galleryState) resetAuto();
  });

  const keyHandler = (e) => {
    if (!window.__galleryState) return;
    if (e.key === 'ArrowLeft') navGallery(-1);
    else if (e.key === 'ArrowRight') navGallery(1);
    else if (e.key === 'Escape') { closeGallery(); closeModal(); }
  };
  document.addEventListener('keydown', keyHandler);
  body.__galleryKeyHandler = keyHandler;
}

function navGallery(dir) {
  const state = window.__galleryState;
  if (!state) return;
  const newIdx = state.currentIdx + dir;
  if (newIdx < 0 || newIdx >= state.images.length) return;
  state.currentIdx = newIdx;
  state.updateGallery();
}

function closeGallery() {
  const body = document.getElementById('modal-body');
  const gallery = body.querySelector('.modal-gallery');
  if (gallery) gallery.remove();
  body.querySelector('.modal-article').style.display = '';
  body.querySelector('.modal-title-group').style.display = '';
  body.querySelector('.modal-tools').style.display = '';
  body.dataset.mode = '';
  if (body.__galleryKeyHandler) {
    document.removeEventListener('keydown', body.__galleryKeyHandler);
    delete body.__galleryKeyHandler;
  }
  if (window.__galleryState) {
    clearTimeout(window.__galleryState.autoTimer);
  }
  delete window.__galleryState;
}

function closeModal() {
  const body = document.getElementById('modal-body');
  if (body.__galleryKeyHandler) {
    document.removeEventListener('keydown', body.__galleryKeyHandler);
    delete body.__galleryKeyHandler;
  }
  if (window.__galleryState) {
    clearTimeout(window.__galleryState.autoTimer);
  }
  delete window.__galleryState;
  body.innerHTML = '';
  body.dataset.mode = '';
  delete body.dataset.lomoImages;
  document.getElementById('modal').classList.add('hide');
}

function toggleFullscreen() {
  const el = document.documentElement;
  const rq = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen || el.mozRequestFullScreen;
  const ex = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen || document.mozCancelFullScreen;
  if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement && !document.mozFullScreen) {
    rq.call(el).catch(() => {});
  } else {
    ex.call(document).catch(() => {});
  }
}

function updateFullscreenBtn() {
  const btn = document.getElementById('fullscreen-btn');
  if (!btn) return;
  const fs = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement || document.mozFullScreen);
  btn.textContent = fs ? '\u26E7' : '\u26F6';
  btn.setAttribute('aria-label', fs ? 'Salir de pantalla completa' : 'Pantalla completa');
}

document.addEventListener('fullscreenchange', updateFullscreenBtn);
document.addEventListener('webkitfullscreenchange', updateFullscreenBtn);
document.addEventListener('msfullscreenchange', updateFullscreenBtn);
document.addEventListener('mozfullscreenchange', updateFullscreenBtn);
updateFullscreenBtn();
if (sessionStorage.getItem('fs')) {
  const el = document.documentElement;
  const rq = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen || el.mozRequestFullScreen;
  rq.call(el).catch(() => {});
}

function closeTop() {
  const body = document.getElementById('modal-body');
  if (body.dataset.mode === 'gallery') closeGallery();
  else closeModal();
}
document.getElementById('modal-backdrop').addEventListener('click', closeTop);

document.addEventListener('keydown', e => {
  if (e.key === 'Escape') {
    closeModal();
    const fs = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement || document.mozFullScreen);
    if (fs) {
      const rq = document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen || document.documentElement.msRequestFullscreen || document.documentElement.mozRequestFullScreen;
      rq.call(document.documentElement).catch(() => {});
    }
  }
});

function getReadCounts() {
  try {
    return JSON.parse(localStorage.getItem('feedfoto.read_counts')) || {};
  } catch {
    return {};
  }
}

function incrementReadCount(source) {
  if (!source) return;
  const counts = getReadCounts();
  counts[source] = (counts[source] || 0) + 1;
  localStorage.setItem('feedfoto.read_counts', JSON.stringify(counts));
  sortSourcesUI();
}

function sortSourcesUI() {
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

function playPodcastInBar(entry) {
  if (!entry) return;
  selectHeroPodcastEntry(entry);
}

function closePlayerBar() {
  const bar = document.getElementById('podcast-player-bar');
  if (bar) bar.classList.add('hide');
}

// ─── Card Tilt / Parallax ─────────────────────────────────────────────────────
(function initCardTilt() {
  const MAX_ANGLE = 12; // grados máximos de rotación
  let rafId = null;
  let activeCard = null;
  let targetRx = 0, targetRy = 0, targetTx = 0, targetTy = 0;
  let currentRx = 0, currentRy = 0, currentTx = 0, currentTy = 0;

  function lerp(a, b, t) { return a + (b - a) * t; }

  function animate() {
    if (!activeCard) return;

    const speed = 0.12;
    currentRx = lerp(currentRx, targetRx, speed);
    currentRy = lerp(currentRy, targetRy, speed);
    currentTx = lerp(currentTx, targetTx, speed);
    currentTy = lerp(currentTy, targetTy, speed);

    activeCard.style.setProperty('--rx', `${currentRx.toFixed(3)}deg`);
    activeCard.style.setProperty('--ry', `${currentRy.toFixed(3)}deg`);
    activeCard.style.setProperty('--tx', `${currentTx.toFixed(3)}`);
    activeCard.style.setProperty('--ty', `${currentTy.toFixed(3)}`);

    rafId = requestAnimationFrame(animate);
  }

  function resetCard(card) {
    if (!card) return;
    targetRx = 0; targetRy = 0; targetTx = 0; targetTy = 0;

    // Esperamos a que el lerp llegue a ~0 y luego quitamos la clase
    const reset = () => {
      currentRx = lerp(currentRx, 0, 0.2);
      currentRy = lerp(currentRy, 0, 0.2);
      currentTx = lerp(currentTx, 0, 0.2);
      currentTy = lerp(currentTy, 0, 0.2);

      card.style.setProperty('--rx', `${currentRx.toFixed(3)}deg`);
      card.style.setProperty('--ry', `${currentRy.toFixed(3)}deg`);
      card.style.setProperty('--tx', `${currentTx.toFixed(3)}`);
      card.style.setProperty('--ty', `${currentTy.toFixed(3)}`);

      if (Math.abs(currentRx) > 0.05 || Math.abs(currentRy) > 0.05) {
        requestAnimationFrame(reset);
      } else {
        card.classList.remove('is-tilting');
        card.style.removeProperty('--rx');
        card.style.removeProperty('--ry');
        card.style.removeProperty('--tx');
        card.style.removeProperty('--ty');
      }
    };
    requestAnimationFrame(reset);
  }

  // Delegamos en el contenedor para no crear listeners por card
  const container = document.getElementById('entries');
  if (!container) return;

  container.addEventListener('mousemove', (e) => {
    const card = e.target.closest('.card');
    if (!card) return;

    // Cambiamos de card
    if (activeCard && activeCard !== card) {
      resetCard(activeCard);
      cancelAnimationFrame(rafId);
    }

    if (activeCard !== card) {
      activeCard = card;
      currentRx = 0; currentRy = 0;
      currentTx = 0; currentTy = 0;
      card.classList.add('is-tilting');
      rafId = requestAnimationFrame(animate);
    }

    const rect = card.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    const dx = (e.clientX - cx) / (rect.width / 2);   // -1 … 1
    const dy = (e.clientY - cy) / (rect.height / 2);  // -1 … 1

    targetRy =  dx * MAX_ANGLE;
    targetRx = -dy * MAX_ANGLE;
    targetTx =  dx * 15;  // px para parallax de la imagen
    targetTy =  dy * 15;
  }, { passive: true });

  container.addEventListener('mouseleave', (e) => {
    const leaving = e.target.closest?.('.card');
    if (!activeCard) return;
    cancelAnimationFrame(rafId);
    const cardToReset = activeCard;
    activeCard = null;
    resetCard(cardToReset);
  });

  // También al salir de cada card individualmente
  container.addEventListener('mouseout', (e) => {
    const card = e.target.closest('.card');
    if (!card || activeCard !== card) return;
    // Chequeamos si el destino está dentro de la misma card
    if (card.contains(e.relatedTarget)) return;
    cancelAnimationFrame(rafId);
    const cardToReset = activeCard;
    activeCard = null;
    resetCard(cardToReset);
  }, { passive: true });
})();
// ─────────────────────────────────────────────────────────────────────────────
