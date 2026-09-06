import { CLICK_OPEN } from './constants.js';
import { state } from './state.js';

export function fmtDur(sec) {
  sec = parseInt(sec || 0, 10);
  if (!sec) return '';
  const h = Math.floor(sec / 3600);
  const m = Math.floor((sec % 3600) / 60);
  const s = sec % 60;
  const mm = String(m).padStart(2, '0');
  const ss = String(s).padStart(2, '0');
  return h ? `${h}:${mm}:${ss}` : `${m}:${ss}`;
}

export function playClickOpen() {
  try {
    let idx;
    do {
      idx = Math.floor(Math.random() * CLICK_OPEN.length);
    } while (idx === state.clickLast && CLICK_OPEN.length > 1);
    state.clickLast = idx;
    const a = new Audio(CLICK_OPEN[idx]);
    a.volume = 0.12;
    a.play().catch(() => {});
  } catch (e) {}
}

export function updateAllPodcastPlayersUI() {
  if (!state.sharedAudio) return;
  const isPlaying = !state.sharedAudio.paused;
  const cur = Math.floor(state.sharedAudio.currentTime || 0);
  const dur = Math.floor(state.sharedAudio.duration || 0);
  const pct = (dur > 0) ? ((state.sharedAudio.currentTime / state.sharedAudio.duration) * 100) + '%' : '0%';
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

export function getSharedPodcastAudio(url, entry) {
  if (state.sharedAudio && state.sharedAudio._url === url) {
    return state.sharedAudio;
  }
  if (state.sharedAudio) {
    state.sharedAudio.pause();
    state.sharedAudio.src = '';
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
  state.sharedAudio = audio;
  window.__sharedAudio = audio;
  return audio;
}

export function selectHeroPodcastEntry(entry) {
  if (!entry) return;
  const hero = document.getElementById('podcast-hero');
  if (!hero) return;
  const img = document.getElementById('podcast-hero-img');
  const title = document.getElementById('podcast-hero-title');
  const meta = document.getElementById('podcast-hero-meta');
  const resumen = document.getElementById('podcast-hero-resumen');
  const player = document.getElementById('podcast-hero-player');

  if (img && window.setPodcastImage) window.setPodcastImage(img, entry);
  if (title) title.textContent = entry.podcast_title || entry.title;
  if (meta && window.fmtDate) {
    meta.textContent = 'episodio ' + (entry.num || '') + ' · ' + window.fmtDate(new Date((entry.date || '') + 'T00:00:00')) + ' · ' + fmtDur(entry.duration);
  }
  if (resumen) resumen.onclick = (e) => { e.preventDefault(); if (window.openPodcastResumen) window.openPodcastResumen(entry); };
  
  if (player) {
    player.dataset.url = entry.link;
  }
  hero.classList.remove('hide');

  const audio = getSharedPodcastAudio(entry.link, entry);
  audio.play().catch(() => {});
}

export function playPodcastInBar(entry) {
  if (!entry) return;
  selectHeroPodcastEntry(entry);
}

export function closePlayerBar() {
  const bar = document.getElementById('podcast-player-bar');
  if (bar) bar.classList.add('hide');
}

export function initPodcastPlayers() {
  document.body.addEventListener('click', (e) => {
    const btn = e.target.closest('.podcast-play');
    if (btn) {
      const player = btn.closest('.podcast-player');
      if (!player) return;
      const url = player.dataset.url;
      if (!url) return;
      
      const entries = state.podcastEntries || [];
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
      if (!state.sharedAudio || !state.sharedAudio.duration) return;
      const rect = bar.getBoundingClientRect();
      const pct = (e.clientX - rect.left) / rect.width;
      state.sharedAudio.currentTime = pct * state.sharedAudio.duration;
      return;
    }
  });

  document.body.addEventListener('input', (e) => {
    const vol = e.target.closest('.podcast-volume');
    if (vol && state.sharedAudio) {
      const v = parseFloat(vol.value);
      state.sharedAudio.volume = v;
      document.querySelectorAll('.podcast-volume').forEach(inp => { if (inp !== vol) inp.value = v; });
    }
  });
}

// Registro global
window.playClickOpen = playClickOpen;
window.updateAllPodcastPlayersUI = updateAllPodcastPlayersUI;
window.selectHeroPodcastEntry = selectHeroPodcastEntry;
window.getSharedPodcastAudio = getSharedPodcastAudio;
window.playPodcastInBar = playPodcastInBar;
window.closePlayerBar = closePlayerBar;
window.fmtDur = fmtDur;
