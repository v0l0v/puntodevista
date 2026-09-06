/**
 * Normalizadores de datos para feeds RSS y APIs específicas
 */

export function normalizeGenericSource(sourceId) {
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

export function extractRssThumb(html) {
  const m = (html || '').match(/<img[^>]+src="([^"]+)"/);
  if (!m) return null;
  if (/facebook\.com|google|tracking/.test(m[1].toLowerCase())) return null;
  return m[1];
}

export function enrichContent(live, fallback) {
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

export function normalizeLomo(items) {
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

export function normalizeBoom(items) {
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

export function normalizeTpj(items) {
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

export function normalizeSwan(items) {
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

export function normalizeHuck(items) {
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

export function normalizeLensCulture(items) {
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

export function normalizeOdlp(items) {
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

export function normalizeMagnum(items) {
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

export function normalizeShootItWithFilm(items) {
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

export function extractImg(post) {
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

// Window bindings
window.normalizeGenericSource = normalizeGenericSource;
window.extractRssThumb = extractRssThumb;
window.enrichContent = enrichContent;
window.normalizeLomo = normalizeLomo;
window.normalizeBoom = normalizeBoom;
window.normalizeTpj = normalizeTpj;
window.normalizeSwan = normalizeSwan;
window.normalizeHuck = normalizeHuck;
window.normalizeLensCulture = normalizeLensCulture;
window.normalizeOdlp = normalizeOdlp;
window.normalizeMagnum = normalizeMagnum;
window.normalizeShootItWithFilm = normalizeShootItWithFilm;
window.extractImg = extractImg;
