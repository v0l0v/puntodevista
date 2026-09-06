/**
 * Funciones de utilidad comunes (formato, escape HTML, fetch timeouts)
 */

export function esc(s) {
  return String(s || '').replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

export function splitItems(desc) {
  if (!desc) return [];
  return desc.split(/\n{2,}|(?=\*\*)/).map(s => s.trim()).filter(Boolean);
}

export function fmtDesc(desc) {
  const items = splitItems(desc);
  if (items.length <= 1) return esc(desc);
  return items.map(i => '<p style="margin:0 0 0.6rem">' + esc(i) + '</p>').join('');
}

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

export function fmtDate(d) {
  if (!d || !(d instanceof Date) || isNaN(d)) return '';
  return d.toLocaleDateString('es', { day: 'numeric', month: 'short', year: 'numeric' });
}

export function fmtDateLong(d) {
  if (!d || !(d instanceof Date) || isNaN(d)) return '';
  return d.toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' });
}

export async function fetchWithTimeout(url, ms) {
  const ctrl = new AbortController();
  const t = setTimeout(() => ctrl.abort(), ms);
  try {
    return await fetch(url, { signal: ctrl.signal });
  } finally {
    clearTimeout(t);
  }
}

// Window bindings
window.esc = esc;
window.splitItems = splitItems;
window.fmtDesc = fmtDesc;
window.fmtDur = fmtDur;
window.fmtDate = fmtDate;
window.fmtDateLong = fmtDateLong;
window.fetchWithTimeout = fetchWithTimeout;
