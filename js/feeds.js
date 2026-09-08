/**
 * Carga y sincronización de feeds RSS, JSON locales y podcast
 */

import {
  ALL_SOURCES,
  WP_API,
  RSS_PROXIES,
  BOOM_FEEDS,
  TPJ_FEEDS,
  HUCK_FEEDS,
  LENSCULTURE_FEEDS,
  ODLP_FEEDS,
  PODCAST_URL,
  PODCAST_COVER
} from './constants.js';

import {
  esc,
  fmtDesc,
  fmtDur,
  fmtDate,
  fetchWithTimeout,
  fetchDataJson
} from './utils.js';

import {
  normalizeGenericSource,
  normalizeLomo,
  normalizeBoom,
  normalizeTpj,
  normalizeSwan,
  normalizeHuck,
  normalizeLensCulture,
  normalizeOdlp,
  normalizeMagnum,
  normalizeShootItWithFilm,
  enrichContent,
  extractRssThumb
} from './normalizers.js';

import { applyFilter } from './filters.js';

export const CACHED_ENTRIES_KEY = 'feedfoto.cached_entries';

export async function fetchRssLive(source, feedUrls) {
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

export async function fetchApiOrJson(apiPath, jsonFile, normalize) {
  try {
    const resp = await fetch(apiPath);
    const data = await resp.json();
    if (data && data.status === 'ok' && data.items.length) return normalize(data.items);
  } catch {}
  try {
    const resp = await fetchDataJson(jsonFile);
    if (resp.ok) {
      const data = await resp.json();
      if (data && data.items) return normalize(data.items);
    }
  } catch {}
  return [];
}

export async function fetchColossal() {
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

export async function fetchLomography() {
  return fetchApiOrJson('/api/lomography', 'lomography.json', normalizeLomo);
}

export async function fetchBooooooom() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('booooooom', BOOM_FEEDS),
    fetchApiOrJson('/api/booooooom', 'booooooom.json', normalizeBoom),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

export async function fetchTpj() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('tpj', TPJ_FEEDS),
    fetchApiOrJson('/api/tpj', 'tpj.json', normalizeTpj),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

export async function fetchSwan() {
  return fetchApiOrJson('/api/swan', 'swan.json', normalizeSwan);
}

export async function fetchHuck() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('huck', HUCK_FEEDS),
    fetchApiOrJson('/api/huck', 'huck.json', normalizeHuck),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

export async function fetchLensCulture() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('lensculture', LENSCULTURE_FEEDS),
    fetchApiOrJson('/api/lensculture', 'lensculture.json', normalizeLensCulture),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

export async function fetchOdlp() {
  const [live, fallback] = await Promise.all([
    fetchRssLive('odlp', ODLP_FEEDS),
    fetchApiOrJson('/api/odlp', 'odlp.json', normalizeOdlp),
  ]);
  if (live && live.length) return enrichContent(live, fallback);
  return fallback;
}

export async function fetchMagnum() {
  const fallback = await fetchApiOrJson('/api/magnum', 'magnum.json', normalizeMagnum);
  return fallback;
}

export async function fetchShootItWithFilm() {
  return fetchApiOrJson('/api/shootitwithfilm', 'shootitwithfilm.json', normalizeShootItWithFilm);
}

export const CUSTOM_FETCHERS = {
  colossal: fetchColossal,
  lomography: fetchLomography,
  booooooom: fetchBooooooom,
  tpj: fetchTpj,
  huck: fetchHuck,
  lensculture: fetchLensCulture,
  odlp: fetchOdlp,
  magnum: fetchMagnum,
  shootitwithfilm: fetchShootItWithFilm,
};

export function loadCachedFeeds() {
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

export async function loadFeeds() {
  // 1. Carga inmediata desde caché local del navegador (0 ms)
  loadCachedFeeds();

  // 2. Carga ultra rápida del bundle consolidado feeds.json (~100 ms)
  let currentEntries = window.__rawEntries || [];
  try {
    const resp = await fetchDataJson('feeds.json');
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

export function combineAndSortAllEntries() {
  const raw = window.__rawEntries || [];
  window.__allEntries = [...raw].sort((a, b) => (b._parsedDate || 0) - (a._parsedDate || 0));
  if (!window.__allEntries.length) {
    const loader = document.getElementById('loader');
    if (loader) loader.classList.add('hide');
    return;
  }
  applyFilter();
}

export async function refreshFeeds() {
  const scroll = window.scrollY;
  const modal = document.getElementById('modal');
  const modalOpen = modal && !modal.classList.contains('hide');
  await loadFeeds();
  if (!modalOpen) window.scrollTo(0, scroll);
}

export async function fetchPodcastMeta() {
  try {
    const resp = await fetchDataJson('podcast_meta.json');
    if (!resp.ok) return;
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
        link: `${PODCAST_URL}/podcast-${e.date}.mp3`,
        is_podcast_entry: true
      };
    });
    
    combineAndSortAllEntries();
    renderPodcastHero();
  } catch {}
}

export function setPodcastImage(imgEl, entry) {
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

  const releaseCover = `${PODCAST_URL}/podcast-cover-${date}.jpg`;
  imgEl.src = releaseCover;
}

export function renderPodcastHero() {
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

export function openPodcastResumen(e) {
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

// Window bindings
window.fetchRssLive = fetchRssLive;
window.fetchApiOrJson = fetchApiOrJson;
window.fetchColossal = fetchColossal;
window.fetchLomography = fetchLomography;
window.fetchBooooooom = fetchBooooooom;
window.fetchTpj = fetchTpj;
window.fetchSwan = fetchSwan;
window.fetchHuck = fetchHuck;
window.fetchLensCulture = fetchLensCulture;
window.fetchOdlp = fetchOdlp;
window.fetchMagnum = fetchMagnum;
window.fetchShootItWithFilm = fetchShootItWithFilm;
window.CUSTOM_FETCHERS = CUSTOM_FETCHERS;
window.loadCachedFeeds = loadCachedFeeds;
window.loadFeeds = loadFeeds;
window.combineAndSortAllEntries = combineAndSortAllEntries;
window.refreshFeeds = refreshFeeds;
window.fetchPodcastMeta = fetchPodcastMeta;
window.setPodcastImage = setPodcastImage;
window.renderPodcastHero = renderPodcastHero;
window.openPodcastResumen = openPodcastResumen;
