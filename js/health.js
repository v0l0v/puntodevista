/**
 * js/health.js — Monitor Editorial del Archivo y Panel de Observabilidad Privado
 */

import { esc } from './utils.js';
import { SOURCE_LABELS } from './constants.js';

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
  // De cara al usuario, el estado es verde y elegante si hay publicaciones cargadas
  if (data.feeds?.total_entries > 0) {
    dot.textContent = '●';
    if (txt) txt.textContent = 'archivo al día';
  } else {
    dot.classList.add('error');
    dot.textContent = '●';
    if (txt) txt.textContent = 'sincronizando';
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
      <div class="modal-article"><p>Cargando información del archivo…</p></div>
    `;
    modal.classList.remove('hide');
    fetchHealth().then(data => {
      if (data) renderEditorialReport(body, data);
      else {
        body.innerHTML = `
          <div class="modal-tools">
            <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
          </div>
          <div class="modal-article"><p>No se pudo consultar el estado del archivo.</p></div>
        `;
      }
    });
    return;
  }

  renderEditorialReport(body, _cachedHealth);
  modal.classList.remove('hide');
}

function renderEditorialReport(body, data) {
  // Verificamos si el visitante tiene el parámetro privado de telemetría (?telemetry=1 o ?admin=1)
  const isPrivateAdmin = location.search.includes('telemetry=1') || location.search.includes('admin=1');

  const lastUpdate = data.pipeline?.last_feeds_update 
    ? new Date(data.pipeline.last_feeds_update).toLocaleString('es', { day: 'numeric', month: 'short', hour: '2-digit', minute: '2-digit' }) 
    : 'Hoy';

  const sourcesRows = Object.entries(data.feeds?.sources_breakdown || {})
    .sort((a, b) => b[1] - a[1])
    .map(([src, count]) => {
      const label = SOURCE_LABELS[src] || src;
      return `
        <div style="display:flex; justify-content:space-between; align-items:center; padding:0.45rem 0; border-bottom:1px solid rgba(255,255,255,0.06); font-size:0.85rem;">
          <span style="color:#eee;">${esc(label)}</span>
          <span style="font-weight:600; color:#aaa; font-size:0.8rem;">${count} fotos</span>
        </div>
      `;
    }).join('');

  // Sección técnica privada (SOLO visible si ?telemetry=1 o ?admin=1)
  let adminSection = '';
  if (isPrivateAdmin) {
    const statusColors = { healthy: '#00ff66', degraded: '#ffaa00', error: '#ff0100' };
    const color = statusColors[data.status] || '#888';
    adminSection = `
      <div style="margin-top:2.5rem; padding:1.2rem; background:rgba(255,255,255,0.02); border-radius:8px; border:1px dashed rgba(255,255,255,0.15);">
        <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:0.8rem;">
          <span style="font-size:0.75rem; text-transform:uppercase; letter-spacing:0.1em; color:#aaa;">🔒 Telemetría de Servidor (Privada)</span>
          <span style="color:${color}; font-size:0.8rem; font-weight:700; text-transform:uppercase;">Estado: ${data.status}</span>
        </div>
        <div style="display:grid; grid-template-columns:repeat(auto-fit, minmax(160px, 1fr)); gap:0.8rem; font-size:0.8rem; color:#888;">
          <div>Proxy WARP: <strong style="color:#ddd;">${data.pipeline?.warp_proxy_active ? 'Activo (SOCKS5)' : 'Directo'}</strong></div>
          <div>Circuit Breaker: <strong style="color:#ddd;">${data.pipeline?.circuit_breaker?.state || 'CLOSED'}</strong></div>
          <div>Disco Libre: <strong style="color:#ddd;">${data.system?.disk?.free_gb || '--'} GB (${data.system?.disk?.free_percent || '--'}%)</strong></div>
          <div>Última sinc ISO: <strong style="color:#ddd;">${data.pipeline?.last_feeds_update?.slice(11, 19) || '--'}</strong></div>
        </div>
      </div>
    `;
  }

  body.innerHTML = `
    <div class="modal-tools">
      <button class="modal-tool-btn" onclick="closeModal()" style="margin-left:auto">← Volver</button>
    </div>
    <div class="modal-title-group">
      <div style="display:flex; align-items:center; gap:0.6rem; margin-bottom:0.4rem;">
        <span style="font-size:1.1rem; color:#00ff66;">●</span>
        <h2 class="modal-title" style="margin:0;">Acerca del Archivo y Red Editorial</h2>
      </div>
      <div class="modal-meta">
        <span class="modal-source">Punto de Vista · Monitor de Curaduría</span>
        <span class="modal-sep">·</span>
        <span class="modal-date">Actualizado: ${lastUpdate}</span>
      </div>
    </div>
    <div class="modal-article" style="line-height:1.65;">
      <p style="color:#bbb; font-size:0.95rem; margin-bottom:1.5rem;">
        Punto de Vista rastrea, unifica y traduce periódicamente las publicaciones más destacadas de las principales revistas, agencias y colectivos de fotografía artística y documental del mundo.
      </p>

      <div style="display:grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap:1rem; margin:1.5rem 0;">
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">En Portada</div>
          <div style="font-size:1.8rem; font-weight:700; color:#fff; margin-top:0.2rem;">${data.feeds?.total_entries || 0}</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">publicaciones recientes</div>
        </div>
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">Archivo Histórico</div>
          <div style="font-size:1.8rem; font-weight:700; color:#fff; margin-top:0.2rem;">${data.database?.articles_total || 0}</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">obras indexadas</div>
        </div>
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">Podcast Diario</div>
          <div style="font-size:1.8rem; font-weight:700; color:#fff; margin-top:0.2rem;">${data.podcast?.total_episodes || 0}</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">episodios de análisis</div>
        </div>
        <div style="background:rgba(255,255,255,0.03); padding:1rem; border-radius:8px; border:1px solid rgba(255,255,255,0.06);">
          <div style="font-size:0.75rem; color:#888; text-transform:uppercase; letter-spacing:0.08em;">Medios Rastreados</div>
          <div style="font-size:1.8rem; font-weight:700; color:#fff; margin-top:0.2rem;">${data.feeds?.sources_tracked || 0}</div>
          <div style="font-size:0.8rem; color:#aaa; margin-top:0.2rem;">cabeceras globales</div>
        </div>
      </div>

      <h3 style="font-size:1rem; margin:1.8rem 0 0.8rem; color:#fff; font-weight:600;">Cabeceras y Artículos en Archivo</h3>
      <div style="display:grid; grid-template-columns: repeat(auto-fill, minmax(230px, 1fr)); gap:0.4rem 1.5rem; max-height:300px; overflow-y:auto; padding-right:0.5rem;">
        ${sourcesRows}
      </div>

      ${adminSection}
    </div>
  `;
}

// Window bindings
window.openHealthModal = openHealthModal;
window.fetchHealth = fetchHealth;
