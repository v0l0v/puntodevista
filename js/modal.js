/**
 * Visualización de artículos en Modal, parseo de contenido HTML y métricas de lectura
 */

import { state } from './state.js';
import { fmtDate, fetchDataJson } from './utils.js';
import { getSourceLabel } from './cards.js';
import { playClickOpen, playPodcastInBar } from './audio.js';
import { closeGallery } from './gallery.js';

export function forceEagerImages() {
  const body = document.getElementById('modal-body');
  if (!body) return;
  body.querySelectorAll('img[loading="lazy"]').forEach(img => img.removeAttribute('loading'));
}

export function cleanContent(html) {
  const doc = new DOMParser().parseFromString(`<div id="__root">${html}</div>`, 'text/html');
  const root = doc.getElementById('__root');
  root.querySelectorAll('div.entry-header, div.post-title, div.post-meta, div.post-share-group, .wp-block-spacer, div[style*="height:"], div[aria-hidden="true"]').forEach(el => el.remove());
  return root.innerHTML;
}

export function extractImages(html) {
  if (!html) return [];
  const items = [];
  const seen = new Set();
  try {
    const doc = new DOMParser().parseFromString(`<div>${html}</div>`, 'text/html');
    doc.querySelectorAll('img').forEach(img => {
      const url = img.getAttribute('src') || img.getAttribute('data-src') || img.getAttribute('srcset')?.split(' ')?.[0];
      if (!url || seen.has(url) || url.startsWith('data:')) return;
      seen.add(url);
      const figure = img.closest('figure');
      let caption = '';
      if (figure) {
        caption = figure.querySelector('figcaption')?.textContent?.trim() || '';
      }
      if (!caption) {
        caption = img.getAttribute('alt')?.trim() || '';
      }
      items.push({ url, caption });
    });
  } catch (e) {
    const imgRe = /<img[^>]+src=["']([^"']+)["']/g;
    let m;
    while ((m = imgRe.exec(html)) !== null) {
      const url = m[1];
      if (!seen.has(url)) {
        seen.add(url);
        items.push({ url, caption: '' });
      }
    }
  }
  return items;
}

export function extractColossalPhotographers(html) {
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

export function isShareLink(url) {
  return /facebook\.com\/(?:sharer|sharing|dialog\/share|plugins|login|share)/.test(url.toLowerCase());
}

export function isOwnDomain(href) {
  try {
    const h = new URL(href).hostname.toLowerCase();
    return h.endsWith('thisiscolossal.com') ||
           h.endsWith('lomography.com') ||
           h.endsWith('booooooom.com') ||
           h.endsWith('thephotographicjournal.com') ||
           h.endsWith('huckmag.com') ||
           h.endsWith('lensculture.com') ||
           h.endsWith('loeildelaphotographie.com') ||
           h.endsWith('magnumphotos.com') ||
           h.endsWith('shootitwithfilm.com') ||
           h.endsWith('35mmc.com') ||
           h.endsWith('kosmofoto.com') ||
           h.endsWith('casualphotophile.com') ||
           h.endsWith('phroommagazine.com') ||
           h.endsWith('c41magazine.com') ||
           h.endsWith('featureshoot.com') ||
           h.endsWith('aint-bad.com') ||
           h.endsWith('emulsive.org') ||
           h.endsWith('blind-magazine.com') ||
           h.endsWith('aperture.org') ||
           h.endsWith('americansuburbx.com') ||
           h.endsWith('1854.photography') ||
           h.endsWith('clavoardiendo-magazine.com');
  } catch {
    return false;
  }
}

const WEBSITE_TEXT_RE = /\b(?:web[\s-]*site|web[\s-]*shop|portfolio)\b|\bweb\b|\bsite\b/i;

export function extractSocialLinks(html) {
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

export function renderLomoArticle(body, entry, data) {
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

export function renderLensCultureArticle(body, entry, data) {
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

export function renderOdlpArticle(body, entry, data) {
  const images = data.images || [];
  const rawContent = data.content || '';
  const socialLinks = rawContent ? extractSocialLinks(rawContent) : [];
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';

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

export function renderMagnumArticle(body, entry, data) {
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

export function renderBoomArticle(body, entry, data) {
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

export function renderTpjArticle(body, entry, data) {
  const content = (data && data.content) ? data.content : cleanContent(entry.content || '');
  const images = (data && data.images && data.images.length) ? data.images : extractImages(content);
  const socialLinks = (data && data.credits && data.credits.length) ? data.credits.map(c => ({ url: c.url, text: c.name, platform: 'instagram' })) : extractSocialLinks(content);
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + (l.platform || 'link') + '">' + l.text + '</a>').join('') + '</div>' : '';
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
  body.dataset.lomoImages = JSON.stringify(images.map(i => ({ url: i.url, caption: i.caption || i.alt || '' })));
}

export function renderSwanArticle(body, entry, data) {
  const images = data.images || [];
  const thumb = data.thumbnail || entry.thumbnail;
  const thumbHTML = (!images.length && thumb) ? `<div class="modal-article" style="padding-bottom:0"><img src="${thumb}" alt="" class="modal-swan-thumb" loading="lazy"></div>` : '';
  const socialLinks = data.content ? extractSocialLinks(data.content) : [];
  const linksHTML = socialLinks.length ? '<div class="modal-links">' + socialLinks.map(l => '<a href="' + l.url + '" target="_blank" rel="noopener" class="modal-link-tag link-' + l.platform + '">' + l.text + '</a>').join('') + '</div>' : '';
  body.innerHTML = `
    <div class="modal-tools">
      ${images.length ? `<button class="modal-tool-btn" onclick="openGallery()">Galería (${images.length})</button>` : ''}
      <button class="modal-tool-btn" onclick="toggleFullscreen()">Pantalla completa</button>
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    ${linksHTML}
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

export function renderHuckArticle(body, entry) {
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

export function renderShootItWithFilmArticle(body, entry) {
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

export function renderGenericArticle(body, entry) {
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

export function renderCachedArticle(body, entry, data, sourceLabel) {
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

export async function openModal(cardOrEntry, directSource) {
  let rawId = '';
  let source = directSource || '';
  let entry = null;

  if (cardOrEntry && typeof cardOrEntry === 'object' && !(cardOrEntry instanceof HTMLElement)) {
    entry = cardOrEntry;
    rawId = String(entry._id || entry.id || entry.link || entry.url || '');
    source = entry.source || entry._source || source;
  } else if (cardOrEntry instanceof HTMLElement) {
    rawId = decodeURIComponent(cardOrEntry.dataset.id || '');
    source = cardOrEntry.dataset.source || '';
    const cardTitle = cardOrEntry.querySelector('.card-title a')?.textContent?.trim() || '';
    const all = state.allEntries || [];
    entry = all.find(e => 
      (e._id != null && String(e._id) === rawId) || 
      (e.link && String(e.link) === rawId) ||
      (String(e._id || e.link) === rawId) ||
      (cardTitle && e.title && e.title.trim() === cardTitle)
    );
  }

  if (source) incrementReadCount(source);
  const body = document.getElementById('modal-body');
  if (!body) return;
  body.innerHTML = '<div class="modal-loading">cargando…</div>';
  const modal = document.getElementById('modal');
  if (modal) modal.classList.remove('hide');
  setTimeout(forceEagerImages, 0);

  if (source === 'podcast') {
    if (modal) modal.classList.add('hide');
    if (entry) playPodcastInBar(entry);
    return;
  }

  playClickOpen();

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

  // Enriquecer contenido desde su dataset fuente (${source}.json) si viene solo con excerpt o sin fotos
  if (source && (!entry.content || entry.content.length < 500 || !entry.content.includes('<img'))) {
    try {
      if (!state.sourceJsonCache) state.sourceJsonCache = {};
      let items = state.sourceJsonCache[source];
      if (!items) {
        const resp = await fetchDataJson(`${source}.json`);
        if (resp.ok) {
          const data = await resp.json();
          items = data.items || (Array.isArray(data) ? data : []);
          state.sourceJsonCache[source] = items;
        }
      }
      if (items && Array.isArray(items)) {
        const found = items.find(i => 
          (i.link && i.link === entry.link) || 
          (i._id != null && String(i._id) === String(entry._id)) ||
          (i.title && i.title.trim().toLowerCase() === (entry.title || '').trim().toLowerCase())
        );
        if (found) {
          if (found.content && (!entry.content || found.content.length > entry.content.length)) {
            entry.content = found.content;
          }
          if (found.thumbnail && !entry.thumbnail) {
            entry.thumbnail = found.thumbnail;
          }
          if (found.images && found.images.length) {
            entry.images = found.images;
          }
        }
      }
    } catch {}
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
        const resp = await fetchDataJson('lomography_articles.json');
        if (resp.ok) {
          const cache = await resp.json();
          const cached = (cache.articles || cache)[entry.link];
          if (cached && cached.status === 'ok') data = cached;
        }
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
        const resp = await fetchDataJson('booooooom_articles.json');
        if (resp.ok) {
          const cache = await resp.json();
          const cached = (cache.articles || cache)[entry.link];
          if (cached && cached.status === 'ok') data = cached;
        }
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
    let data = null;
    try {
      const resp = await fetch(`/api/tpj/article?url=${encodeURIComponent(entry.link)}`);
      const d = await resp.json();
      if (d.status === 'ok') data = d;
    } catch {}
    if (!data) {
      try {
        const resp = await fetchDataJson('tpj_articles.json');
        if (resp.ok) {
          const cache = await resp.json();
          const cached = (cache.articles || cache)[entry.link];
          if (cached && cached.status === 'ok') data = cached;
        }
      } catch {}
    }
    if (data) {
      renderTpjArticle(body, entry, data);
      return;
    }
    renderTpjArticle(body, entry);
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
        const resp = await fetchDataJson('lensculture_articles.json');
        if (resp.ok) {
          const cache = await resp.json();
          const cached = (cache.articles || cache)[entry.link];
          if (cached && cached.status === 'ok') data = cached;
        }
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
        const resp = await fetchDataJson('odlp_articles.json');
        if (resp.ok) {
          const cache = await resp.json();
          const cached = (cache.articles || cache)[entry.link];
          if (cached && cached.status === 'ok') data = cached;
        }
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
        const resp = await fetchDataJson('magnum_articles.json');
        if (resp.ok) {
          const cache = await resp.json();
          const cached = (cache.articles || cache)[entry.link];
          if (cached && cached.status === 'ok') data = cached;
        }
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
        const resp = await fetchDataJson(`${source}_articles.json`);
        if (resp.ok) {
          const cache = await resp.json();
          const cached = (cache.articles || cache)[entry.link];
          if (cached && cached.status === 'ok') data = cached;
        }
      } catch {}
    }
    if (data) {
      renderCachedArticle(body, entry, data, getSourceLabel(source));
      return;
    }
    renderGenericArticle(body, entry);
    return;
  }

  // Todas las demás fuentes genéricas
  renderGenericArticle(body, entry);
}

export function closeModal() {
  const body = document.getElementById('modal-body');
  if (body) {
    if (body.__galleryKeyHandler) {
      document.removeEventListener('keydown', body.__galleryKeyHandler);
      delete body.__galleryKeyHandler;
    }
    body.innerHTML = '';
    body.dataset.mode = '';
    delete body.dataset.lomoImages;
  }
  if (window.__galleryState) {
    clearTimeout(window.__galleryState.autoTimer);
    delete window.__galleryState;
  }
  const modal = document.getElementById('modal');
  if (modal) modal.classList.add('hide');
}

export function closeTop() {
  const body = document.getElementById('modal-body');
  if (body && body.dataset.mode === 'gallery') closeGallery();
  else closeModal();
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

// Window bindings
window.forceEagerImages = forceEagerImages;
window.cleanContent = cleanContent;
window.extractImages = extractImages;
window.extractColossalPhotographers = extractColossalPhotographers;
window.isShareLink = isShareLink;
window.isOwnDomain = isOwnDomain;
window.extractSocialLinks = extractSocialLinks;
window.renderLomoArticle = renderLomoArticle;
window.renderLensCultureArticle = renderLensCultureArticle;
window.renderOdlpArticle = renderOdlpArticle;
window.renderMagnumArticle = renderMagnumArticle;
window.renderBoomArticle = renderBoomArticle;
window.renderTpjArticle = renderTpjArticle;
window.renderSwanArticle = renderSwanArticle;
window.renderHuckArticle = renderHuckArticle;
window.renderShootItWithFilmArticle = renderShootItWithFilmArticle;
window.renderGenericArticle = renderGenericArticle;
window.renderCachedArticle = renderCachedArticle;
window.openModal = openModal;
window.closeModal = closeModal;
window.closeTop = closeTop;
window.getReadCounts = getReadCounts;
window.incrementReadCount = incrementReadCount;
window.sortSourcesUI = sortSourcesUI;
