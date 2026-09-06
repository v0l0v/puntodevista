/**
 * Punto de Vista - Entry point modular de la aplicación frontend
 */

import { REFRESH_MS } from './constants.js';
import { state } from './state.js';
import './utils.js';
import './normalizers.js';
import {
  loadSources,
  loadSourcesConfig,
  setupSourcesUI,
  setDateFilter,
  buildMonthsGrid,
  applyFilter
} from './filters.js';
import {
  loadCachedFeeds,
  loadFeeds,
  fetchPodcastMeta,
  refreshFeeds,
  combineAndSortAllEntries
} from './feeds.js';
import {
  initPodcastPlayers,
  selectHeroPodcastEntry,
  getSharedPodcastAudio,
  playPodcastInBar,
  closePlayerBar
} from './audio.js';
import {
  render,
  renderCard,
  initCardTilt,
  imgLoaded,
  imgError,
  setupInfiniteScroll
} from './cards.js';
import {
  openModal,
  closeModal,
  closeTop,
  sortSourcesUI,
  incrementReadCount
} from './modal.js';
import {
  openGallery,
  navGallery,
  closeGallery,
  toggleFullscreen,
  initFullscreen
} from './gallery.js';
import {
  fetchHealth,
  openHealthModal
} from './health.js';

// API pública en window para extensiones, integraciones y handlers inline
window.openArticleModal = function(entry) {
  if (!entry) return;
  openModal(entry, entry._source || entry.source);
};

window.openArticleModalById = function(idOrLink, source) {
  const all = state.allEntries || [];
  const targetId = String(idOrLink || '');
  const entry = all.find(e => 
    String(e._id) === targetId || 
    String(e.id) === targetId || 
    e.link === targetId || 
    (e.url && e.url === targetId)
  ) || { _id: targetId, link: targetId, _source: source, source: source, title: 'Artículo' };
  openModal(entry, source);
};

window.playPodcastByUrl = function(url, podcastEntry) {
  const entries = state.podcastEntries || [];
  const entry = podcastEntry || entries.find(x => x.link === url || x.url === url) || { link: url, url: url, title: 'Podcast' };
  const audio = getSharedPodcastAudio(url, entry);
  if (audio) {
    audio.play().catch(() => {});
  }
  selectHeroPodcastEntry(entry);
};

// Listeners principales en DOMContentLoaded
document.addEventListener('DOMContentLoaded', async () => {
  loadSources();

  // ── Panel Fuentes ──────────────────────────────────────────────────
  const sourcesBtn = document.getElementById('sources-btn');
  const sourcesPanel = document.getElementById('sources-panel');
  const dateBtn = document.getElementById('date-btn');
  const datePanel = document.getElementById('date-panel');

  function closeAllPanels() {
    if (sourcesPanel) {
      sourcesPanel.classList.add('hide');
      sourcesBtn?.classList.remove('active');
      sourcesBtn?.setAttribute('aria-expanded', 'false');
    }
    if (datePanel) {
      datePanel.classList.add('hide');
      dateBtn?.classList.remove('active');
      dateBtn?.setAttribute('aria-expanded', 'false');
    }
  }

  if (sourcesBtn && sourcesPanel) {
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
  }

  // ── Panel Fecha ────────────────────────────────────────────────────
  if (dateBtn && datePanel) {
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
  }

  document.addEventListener('click', (e) => {
    if (sourcesPanel && !sourcesPanel.classList.contains('hide') &&
        !sourcesPanel.contains(e.target) && e.target !== sourcesBtn) {
      sourcesPanel.classList.add('hide');
      sourcesBtn?.classList.remove('active');
      sourcesBtn?.setAttribute('aria-expanded', 'false');
    }
    if (datePanel && !datePanel.classList.contains('hide') &&
        !datePanel.contains(e.target) && e.target !== dateBtn) {
      datePanel.classList.add('hide');
      dateBtn?.classList.remove('active');
      dateBtn?.setAttribute('aria-expanded', 'false');
    }
  });

  // Filas de período (todo, año, mes, semana, hoy)
  if (datePanel) {
    datePanel.querySelectorAll('.date-row').forEach(row => {
      row.addEventListener('click', () => {
        const period = row.dataset.period;
        if (period === 'year') return; // "Este año" solo sirve como cabecera del grid
        setDateFilter(period, null);
        closeAllPanels();
      });
    });
  }

  // Backdrop del modal
  const backdrop = document.getElementById('modal-backdrop');
  if (backdrop) {
    backdrop.addEventListener('click', closeTop);
  }

  // Atajo de teclado Escape
  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      closeModal();
      const fs = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement || document.mozFullScreen);
      if (fs) {
        const rq = document.documentElement.requestFullscreen || document.documentElement.webkitRequestFullscreen || document.documentElement.msRequestFullscreen || document.documentElement.mozRequestFullScreen;
        rq?.call(document.documentElement).catch(() => {});
      }
    }
  });

  // ── Inicialización de módulos y datos ──────────────────────────────
  loadSources();
  loadCachedFeeds();
  await loadSourcesConfig();
  setupSourcesUI();
  sortSourcesUI();
  loadFeeds();
  fetchPodcastMeta();
  initPodcastPlayers();
  initFullscreen();
  initCardTilt();
  fetchHealth();

  setInterval(() => {
    if (!document.hidden) {
      refreshFeeds();
      fetchHealth();
    }
  }, REFRESH_MS);

  // Abrir panel si se llega desde otra página (?panel=date|sources)
  const params = new URLSearchParams(location.search);
  const panel = params.get('panel');
  if (panel === 'sources' && sourcesBtn) {
    sourcesBtn.click();
  } else if (panel === 'date' && dateBtn) {
    dateBtn.click();
  }
});
