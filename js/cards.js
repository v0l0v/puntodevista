/**
 * Renderizado de tarjetas fotográficas en el grid, scroll infinito y efectos visuales
 */

import { SOURCE_LABELS, ALL_SOURCES, PAGE_SIZE } from './constants.js';
import { state } from './state.js';
import { fmtDate } from './utils.js';
import { extractImg } from './normalizers.js';

export function getSourceLabel(src) {
  return state.sourceLabels[src] || SOURCE_LABELS[src] || src;
}

export function podcastCardHTML() {
  return '';
}

export function renderCard(e) {
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

export function render(entries) {
  const el = document.getElementById('entries');
  if (!el) return;
  const all = state.allEntries || [];
  const displayItems = entries.slice(0, state.visibleLimit);

  let html = podcastCardHTML() + displayItems.map(renderCard).join('');
  
  if (entries.length > state.visibleLimit) {
    html += `
      <div id="scroll-sentinel" class="scroll-sentinel" style="grid-column: 1 / -1; text-align: center; padding: 2.5rem 0; color: #888; font-size: 0.9rem;">
        <span style="color:#ff0100">●</span> Cargando más publicaciones del archivo…
      </div>
    `;
  } else if (entries.length > 0 && state.dateFilter.period !== 'all') {
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
  const loader = document.getElementById('loader');
  if (loader) loader.classList.add('hide');

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

export function setupInfiniteScroll() {
  if (state.scrollObserver) {
    state.scrollObserver.disconnect();
    state.scrollObserver = null;
  }
  const sentinel = document.getElementById('scroll-sentinel');
  if (!sentinel) return;

  state.scrollObserver = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting) {
      if (state.visibleLimit < state.currentFilteredEntries.length) {
        state.visibleLimit += PAGE_SIZE;
        render(state.currentFilteredEntries);
      }
    }
  }, { rootMargin: '350px' });

  state.scrollObserver.observe(sentinel);
}

export function imgLoaded(img) {
  img.classList.add('loaded');
  const card = img.closest('.card');
  card?.querySelector('.card-skeleton')?.remove();
  if (card && card.dataset.color === '?') {
    card.dataset.color = '0';
  }
}

export function imgError(img) {
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

export function initCardTilt() {
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

  const container = document.getElementById('entries');
  if (!container) return;

  container.addEventListener('mousemove', (e) => {
    const card = e.target.closest('.card');
    if (!card) return;

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
    const dx = (e.clientX - cx) / (rect.width / 2);
    const dy = (e.clientY - cy) / (rect.height / 2);

    targetRy =  dx * MAX_ANGLE;
    targetRx = -dy * MAX_ANGLE;
    targetTx =  dx * 15;
    targetTy =  dy * 15;
  }, { passive: true });

  container.addEventListener('mouseleave', () => {
    if (!activeCard) return;
    cancelAnimationFrame(rafId);
    const cardToReset = activeCard;
    activeCard = null;
    resetCard(cardToReset);
  });

  container.addEventListener('mouseout', (e) => {
    const card = e.target.closest('.card');
    if (!card || activeCard !== card) return;
    if (card.contains(e.relatedTarget)) return;
    cancelAnimationFrame(rafId);
    const cardToReset = activeCard;
    activeCard = null;
    resetCard(cardToReset);
  }, { passive: true });
}

// Window bindings
window.getSourceLabel = getSourceLabel;
window.podcastCardHTML = podcastCardHTML;
window.renderCard = renderCard;
window.render = render;
window.setupInfiniteScroll = setupInfiniteScroll;
window.imgLoaded = imgLoaded;
window.imgError = imgError;
window.initCardTilt = initCardTilt;
