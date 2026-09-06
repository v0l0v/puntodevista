/**
 * js/health.js — Módulo de observabilidad y pulso del sistema
 */

import { esc, fmtDate } from './utils.js';

let _cachedHealth = null;

export async function fetchHealth() {
  try {
    const resp = await fetch('health.json', { cache: 'no-store' });
    if (resp.ok) {
      _cachedHealth = await resp.json();
      updateHealthUI(_cachedHealth);
      return _cachedHealth;
    }
  } catch {}
  return null;
}

export function updateHealthUI(data) {
  const dot = document.getElementById('health-dot');
  const txt = document.getElementById('health-text');
  if (!dot || !data) return;

  dot.classList.remove('degraded', 'error');
  if (data.status === 'healthy') {
    dot.textContent = '●';
    if (txt) txt.textContent = 'pulso ok';
  } else if (data.status === 'degraded') {
    dot.classList.add('degraded');
    dot.textContent = '●';
    if (txt) txt.textContent = 'degradado';
  } else {
    dot.classList.add('error');
    dot.textContent = '●';
    if (txt) txt.textContent = 'alerta';
  }
}

export function openHealthModal() {
  const body = document.getElementById('modal-body');
  const modal = document.getElementById('modal');
  if (!body || !modal) return;

  if (!_cachedHealth) {
    body.innerHTML = `
      <div class="modal-tools">
        <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
      </div>
      <div class="modal-article"><p>Cargando métricas de observabilidad…</p></div>
    `;
    modal.classList.remove('hide');
    fetchHealth().then(data => {
      if (data) renderHealthReport(body, data);
      else {
        body.innerHTML = `
          <div class="modal-tools">
            <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
          </div>
          <div class="modal-article"><p>No se pudo obtener el reporte de salud.</p></div>
        `;
      }
    });
    return;
  }

  renderHealthReport(body, _cachedHealth);
  modal.classList.remove('hide');
}

function renderHealthReport(body, data) {
  const statusColors = {
    healthy: '#00ff66',
    degraded: '#ffaa00',
    error: '#ff0100'
  };
  const color = statusColors[data.status] || '#888';

  const lastUpdate = data.pipeline?.last_feeds_update 
    ? new Date(data.pipeline.last_feeds_update).toLocaleString('es') 
    : 'Desconocido';

  const sourcesRows = Object.entries(data.feeds?.sources_breakdown || {})
    .sort((a, b) => b[1] - a[1])
    .map(([src, count]) => `
      <div style="display:flex; justify-content:space-between; padding:0.35rem 0; border-bottom:1px solid rgba(255,255,255,0.05); font-size:0.85rem;">
        <span style="color:#ddd;">${esc(src)}</span>
        <span style="font-weight:600; color:#fff;">${count}</span>
      </div>
    `).join('');

  const issuesHTML = data.issues && data.issues.length 
    ? `<div style="background:rgba(255,170,0,0.1); border-left:3px solid #ffaa00; padding:0.8rem; margin:1rem 0; font-size:0.85rem;">
        <strong>Incidencias detectadas:</strong>
        <ul style="margin:0.4rem 0 0 1.2rem; padding:0;">
          ${data.issues.map(i => `<li>${esc(i)}</li>`).join('')}
        </ul>
      </div>` 
    : '';

  body.innerHTML = `
    <div class="modal-tools">
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    <div class="modal-title-group">
      <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.4rem;">
        <span style="font-size:1.2rem; color:${color};">●</span>
        <h2 class="modal-title" style="margin:0;">Pulso del Sistema y Observabilidad</h2>
      </div>
      <div class="modal-meta">
        <span class="modal-source">Estado: <strong style="color:${color}; text-transform:uppercase;">${data.status}</strong></span>
        <span class="modal-sep">·</span>
        <span class="modal-date">Última sinc: ${lastUpdate}</span>
      </div>
    </div>
    <div class="modal-article" style="line-height:1.6;">
      ${issuesHTML}
      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:1rem; margin:1.5rem 0;">
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">Artículos en Vivo</div>
          <div style="font-size:1.8rem; font-weight:700; color:#fff; margin-top:0.2rem;">${data.feeds?.total_entries || 0}</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">${data.feeds?.sources_tracked || 0} revistas rastreadas</div>
        </div>
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">Archivo Histórico</div>
          <div style="font-size:1.8rem; font-weight:700; color:#fff; margin-top:0.2rem;">${data.database?.articles_total || 0}</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">${data.database?.podcasts_total || 0} podcasts vectorizados</div>
        </div>
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">IA & Circuit Breaker</div>
          <div style="font-size:1.4rem; font-weight:700; color:#fff; margin-top:0.4rem;">${data.pipeline?.circuit_breaker?.state || 'CLOSED'}</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">Proxy WARP: ${data.pipeline?.warp_proxy_active ? 'Activo (SOCKS5)' : 'Directo'}</div>
        </div>
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">Almacenamiento VPS</div>
          <div style="font-size:1.4rem; font-weight:700; color:#fff; margin-top:0.4rem;">${data.system?.disk?.free_gb || '--'} GB libres</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">${data.system?.disk?.free_percent || '--'}% disponible</div>
        </div>
      </div>

      <h3 style="font-size:1.05rem; margin:1.8rem 0 0.8rem; color:#fff;">Desglose de Publicaciones por Revista</h3>
      <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(220px, 1fr)); gap:0.6rem 1.5rem; max-height:320px; overflow-y:auto; padding-right:0.5rem;">
        ${sourcesRows}
      </div>
    </div>
  `;
}

// Window bindings
window.openHealthModal = openHealthModal;
window.fetchHealth = fetchHealth;
