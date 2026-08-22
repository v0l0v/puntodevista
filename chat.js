/**
 * chat.js — Asistente Fotográfico y Buscador IA para Punto de vista
 * Permite buscar y conversar interactivamente sobre el archivo histórico (475+ artículos y 19 podcasts).
 */

(function () {
  let archiveData = null;
  let isFetchingArchive = false;
  let isOpen = false;

  const SUGGESTIONS = [
    '📷 Cámaras de medio formato y Olympus Pen',
    '🌙 Fotografía nocturna y luces de neón',
    '🎞️ Película Phoenix 200 y emulsiones analógicas',
    '🏙️ Fotografía callejera en Japón y Tokio',
    '🎙️ ¿Qué podcasts hablan de sueños y memoria?',
    '🖼️ Fotógrafos destacados en Lomography y Huck'
  ];

  // Inyectar HTML del widget de chat
  function injectChatUI() {
    if (document.getElementById('chat-widget')) return;

    const widget = document.createElement('div');
    widget.id = 'chat-widget';
    widget.innerHTML = `
      <!-- Botón Flotante -->
      <button id="chat-trigger-btn" aria-label="Abrir asistente de conversación fotográfica" title="Preguntar al archivo fotográfico">
        <span class="chat-btn-icon">💬</span>
        <span class="chat-btn-text">Preguntar al Archivo</span>
      </button>

      <!-- Panel / Ventana de Chat -->
      <div id="chat-drawer" class="hide" role="dialog" aria-modal="true" aria-label="Asistente Fotográfico">
        <div class="chat-header">
          <div class="chat-header-info">
            <div class="chat-title"><span class="chat-dot"></span> Asistente Punto de vista</div>
            <div class="chat-subtitle">Archivo histórico · 475 artículos y 19 podcasts</div>
          </div>
          <button id="chat-close-btn" aria-label="Cerrar chat">✕</button>
        </div>

        <div class="chat-messages" id="chat-messages">
          <div class="chat-msg bot">
            <div class="msg-avatar">📸</div>
            <div class="msg-content">
              <p><strong>¡Hola!</strong> Soy tu asistente del archivo de <em>Punto de vista</em>. Puedo buscar, resumir y cruzar información de todo nuestro histórico de fotografía analógica, fotolibros, autores, cámaras y episodios de podcast.</p>
              <div class="chat-chips" id="chat-chips">
                ${SUGGESTIONS.map(s => `<button class="chat-chip" type="button">${s}</button>`).join('')}
              </div>
            </div>
          </div>
        </div>

        <form class="chat-input-row" id="chat-form">
          <input type="text" id="chat-input" placeholder="Pregunta sobre fotógrafos, cámaras, temas…" autocomplete="off" aria-label="Tu mensaje">
          <button type="submit" id="chat-send-btn" aria-label="Enviar">➤</button>
        </form>
      </div>
    `;

    document.body.appendChild(widget);

    // Eventos
    document.getElementById('chat-trigger-btn').addEventListener('click', toggleChat);
    document.getElementById('chat-close-btn').addEventListener('click', toggleChat);
    document.getElementById('chat-form').addEventListener('submit', handleUserSubmit);

    document.getElementById('chat-chips').addEventListener('click', (e) => {
      const chip = e.target.closest('.chat-chip');
      if (chip) {
        const text = chip.textContent.replace(/^[^\wáéíóúÁÉÍÓÚ]+/, '').trim();
        document.getElementById('chat-input').value = text;
        handleUserSubmit(new Event('submit'));
      }
    });

    // Carga anticipada del índice histórico
    preloadArchive();
  }

  async function preloadArchive() {
    if (archiveData || isFetchingArchive) return;
    isFetchingArchive = true;
    try {
      const resp = await fetch('archive_index.json');
      if (resp.ok) {
        archiveData = await resp.json();
      }
    } catch (e) {
      console.warn('No se pudo cargar archive_index.json:', e);
    } finally {
      isFetchingArchive = false;
    }
  }

  function toggleChat() {
    isOpen = !isOpen;
    const drawer = document.getElementById('chat-drawer');
    const trigger = document.getElementById('chat-trigger-btn');
    if (!drawer) return;

    drawer.classList.toggle('hide', !isOpen);
    trigger.classList.toggle('active', isOpen);

    if (isOpen) {
      preloadArchive();
      setTimeout(() => document.getElementById('chat-input')?.focus(), 100);
    }
  }

  function addMessage(sender, htmlContent) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const row = document.createElement('div');
    row.className = `chat-msg ${sender}`;
    const avatar = sender === 'bot' ? '📸' : '👤';

    row.innerHTML = `
      <div class="msg-avatar">${avatar}</div>
      <div class="msg-content">${htmlContent}</div>
    `;

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
    return row;
  }

  // Motor de Búsqueda y Razonamiento Contextual
  function queryArchive(query) {
    if (!archiveData) return { articles: [], podcasts: [] };

    const terms = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    if (!terms.length) return { articles: [], podcasts: [] };

    // Puntuación de artículos
    const scoredArticles = (archiveData.articles || []).map(a => {
      let score = 0;
      const title = (a.title || '').toLowerCase();
      const photo = (a.photographer || '').toLowerCase();
      const summary = (a.summary || '').toLowerCase();
      const src = (a.source || '').toLowerCase();

      terms.forEach(t => {
        if (title.includes(t)) score += 10;
        if (photo.includes(t)) score += 8;
        if (summary.includes(t)) score += 4;
        if (src.includes(t)) score += 3;
      });

      return { ...a, score };
    }).filter(a => a.score > 0).sort((a, b) => b.score - a.score);

    // Puntuación de podcasts
    const scoredPodcasts = (archiveData.podcasts || []).map(p => {
      let score = 0;
      const title = (p.title || '').toLowerCase();
      const desc = (p.description || '').toLowerCase();
      const date = (p.date || '').toLowerCase();

      terms.forEach(t => {
        if (title.includes(t)) score += 12;
        if (desc.includes(t)) score += 5;
        if (date.includes(t)) score += 6;
      });

      return { ...p, score };
    }).filter(p => p.score > 0).sort((a, b) => b.score - a.score);

    return {
      articles: scoredArticles.slice(0, 5),
      podcasts: scoredPodcasts.slice(0, 3)
    };
  }

  function generateAssistantResponse(query, results) {
    const { articles, podcasts } = results;

    if (!articles.length && !podcasts.length) {
      return `
        <p>No encontré artículos ni podcasts que coincidan exactamente con <em>«${query}»</em> en el archivo histórico.</p>
        <p>💡 <em>Sugerencia:</em> Prueba buscando por nombre de autor (ej. <strong>Mario Giovanni</strong>, <strong>David Slegers</strong>), cámara (<strong>Olympus Pen</strong>, <strong>Diana F+</strong>) o fuente (<strong>Colossal</strong>, <strong>Lomography</strong>).</p>
      `;
    }

    let out = `<p>Encontré los siguientes registros relevantes en nuestro archivo histórico sobre <strong>«${query}»</strong>:</p>`;

    if (podcasts.length > 0) {
      out += `<div class="chat-results-section"><span class="chat-sec-badge">🎙️ Episodios de Podcast</span>`;
      podcasts.forEach(p => {
        out += `
          <div class="chat-result-card podcast">
            <div class="chat-card-title"><a href="episodios.html" target="_blank">${p.title || 'Resumen Diario'}</a></div>
            <div class="chat-card-meta">Fecha: ${p.date} · ${Math.floor((p.duration || 0)/60)} min</div>
            <div class="chat-card-desc">${(p.description || '').slice(0, 160)}…</div>
          </div>
        `;
      });
      out += `</div>`;
    }

    if (articles.length > 0) {
      out += `<div class="chat-results-section"><span class="chat-sec-badge">📄 Artículos y Ensayos</span>`;
      articles.forEach(a => {
        const photo = a.photographer ? ` · <em>${a.photographer}</em>` : '';
        out += `
          <div class="chat-result-card article">
            <div class="chat-card-source">${a.source?.toUpperCase()}${photo} · ${a.published_date || ''}</div>
            <div class="chat-card-title"><a href="${a.url}" target="_blank" rel="noopener noreferrer">${a.title} ↗</a></div>
            <div class="chat-card-desc">${(a.summary || '').slice(0, 180)}…</div>
          </div>
        `;
      });
      out += `</div>`;
    }

    out += `<p style="font-size:0.75rem;opacity:0.7;margin-top:0.6rem">¿Te gustaría profundizar sobre alguno de estos autores o conceptos?</p>`;
    return out;
  }

  async function handleUserSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const q = (input?.value || '').trim();
    if (!q) return;

    input.value = '';
    addMessage('user', `<p>${escapeHtml(q)}</p>`);

    if (!archiveData) {
      const loading = addMessage('bot', '<p class="chat-typing"><span>●</span><span>●</span><span>●</span> Consultando base de datos histórica…</p>');
      await preloadArchive();
      loading.remove();
    }

    const results = queryArchive(q);
    const responseHtml = generateAssistantResponse(q, results);
    addMessage('bot', responseHtml);
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  // Inicializar al cargar el DOM
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectChatUI);
  } else {
    injectChatUI();
  }
})();
