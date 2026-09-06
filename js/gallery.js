/**
 * Visualizador de galería de imágenes y control de pantalla completa
 */

export function openGallery() {
  const body = document.getElementById('modal-body');
  if (!body) return;
  const article = body.querySelector('.modal-article');
  const titleGroup = body.querySelector('.modal-title-group');
  let images;
  if (body.dataset.lomoImages) {
    images = JSON.parse(body.dataset.lomoImages);
  } else if (article) {
    if (typeof window.extractImages === 'function') {
      images = window.extractImages(article.querySelector('.modal-article-content')?.innerHTML || '');
    }
  }
  if (!images || !images.length) return;

  if (article) article.style.display = 'none';
  if (titleGroup) titleGroup.style.display = 'none';
  body.dataset.mode = 'gallery';
  const tools = body.querySelector('.modal-tools');
  if (tools) tools.style.display = 'none';

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
    else if (e.key === 'Escape') {
      closeGallery();
      if (typeof window.closeModal === 'function') window.closeModal();
    }
  };
  document.addEventListener('keydown', keyHandler);
  body.__galleryKeyHandler = keyHandler;
}

export function navGallery(dir) {
  const state = window.__galleryState;
  if (!state) return;
  const newIdx = state.currentIdx + dir;
  if (newIdx < 0 || newIdx >= state.images.length) return;
  state.currentIdx = newIdx;
  state.updateGallery();
}

export function closeGallery() {
  const body = document.getElementById('modal-body');
  if (!body) return;
  const gallery = body.querySelector('.modal-gallery');
  if (gallery) gallery.remove();
  const article = body.querySelector('.modal-article');
  if (article) article.style.display = '';
  const titleGroup = body.querySelector('.modal-title-group');
  if (titleGroup) titleGroup.style.display = '';
  const tools = body.querySelector('.modal-tools');
  if (tools) tools.style.display = '';
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

export function toggleFullscreen() {
  const el = document.documentElement;
  const rq = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen || el.mozRequestFullScreen;
  const ex = document.exitFullscreen || document.webkitExitFullscreen || document.msExitFullscreen || document.mozCancelFullScreen;
  if (!document.fullscreenElement && !document.webkitFullscreenElement && !document.msFullscreenElement && !document.mozFullScreen) {
    rq?.call(el).catch(() => {});
  } else {
    ex?.call(document).catch(() => {});
  }
}

export function updateFullscreenBtn() {
  const btn = document.getElementById('fullscreen-btn');
  if (!btn) return;
  const fs = !!(document.fullscreenElement || document.webkitFullscreenElement || document.msFullscreenElement || document.mozFullScreen);
  btn.textContent = fs ? '\u26E7' : '\u26F6';
  btn.setAttribute('aria-label', fs ? 'Salir de pantalla completa' : 'Pantalla completa');
}

export function initFullscreen() {
  document.addEventListener('fullscreenchange', updateFullscreenBtn);
  document.addEventListener('webkitfullscreenchange', updateFullscreenBtn);
  document.addEventListener('msfullscreenchange', updateFullscreenBtn);
  document.addEventListener('mozfullscreenchange', updateFullscreenBtn);
  updateFullscreenBtn();
  if (sessionStorage.getItem('fs')) {
    const el = document.documentElement;
    const rq = el.requestFullscreen || el.webkitRequestFullscreen || el.msRequestFullscreen || el.mozRequestFullScreen;
    rq?.call(el).catch(() => {});
  }
}

// Window bindings
window.openGallery = openGallery;
window.navGallery = navGallery;
window.closeGallery = closeGallery;
window.toggleFullscreen = toggleFullscreen;
window.updateFullscreenBtn = updateFullscreenBtn;
window.initFullscreen = initFullscreen;
