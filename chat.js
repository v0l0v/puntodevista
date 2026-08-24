/**
 * chat.js — Asistente de Inteligencia Curatorial, Linaje Visual y Buscador Conceptual
 * para la plataforma 'Punto de vista'.
 */

(function () {
  let archiveData = null;
  let isFetchingArchive = false;
  let isOpen = false;

  const SUGGESTIONS = [
    '✨ Disparador Creativo para hoy',
    '🧬 Linaje de la soledad urbana y suburbios',
    '🌙 Atmósfera nocturna, misterio y sombras',
    '🎞️ Imperfección analógica y grano experimental',
    '🏠 Memoria familiar, duelo y espacio doméstico',
    '🌐 Ver Dossier Semanal de Tendencias'
  ];

  // Diccionario de afinidades semánticas y expansión conceptual
  const CONCEPT_MAP = {
    'nostalgia': ['memoria', 'pasado', 'analógico', 'tiempo', 'grano', 'melancolía', 'recuerdo', 'archivo', 'infancia'],
    'soledad': ['aislamiento', 'silencio', 'vacío', 'nocturno', 'suburbia', 'individual', 'distancia', 'quietud'],
    'urbano': ['calle', 'ciudad', 'arquitectura', 'transeúntes', 'asfalto', 'metrópoli', 'tokio', 'barrio', 'concreto'],
    'calle': ['street', 'urbano', 'espontáneo', 'peatones', 'calles', 'instantánea', 'cándido'],
    'luz': ['claroscuro', 'crepúsculo', 'sombra', 'neón', 'contraste', 'atardecer', 'reflejos', 'iluminación'],
    'noche': ['nocturna', 'neón', 'oscuridad', 'sombras', 'luces', 'madrugada', 'misterio'],
    'analógico': ['película', '35mm', 'formato medio', 'grano', 'emulsión', 'química', 'lomography', 'pinhole', 'estenopeica'],
    'cuerpo': ['retrato', 'identidad', 'piel', 'gesto', 'figura', 'desnudo', 'autorretrato'],
    'duelo': ['pérdida', 'ausencia', 'memoria', 'familia', 'despedida', 'casa', 'silencio', 'recuerdo'],
    'paisaje': ['naturaleza', 'horizonte', 'territorio', 'árboles', 'mar', 'montaña', 'vacío', 'rural'],
    'color': ['cromatismo', 'paleta', 'tonos', 'saturación', 'lomochrome', 'blanco y negro', 'monocromo']
  };

  function injectChatUI() {
    if (document.getElementById('chat-widget')) return;

    const widget = document.createElement('div');
    widget.id = 'chat-widget';
    widget.innerHTML = `
      <!-- Botón Flotante -->
      <button id="chat-trigger-btn" aria-label="Abrir asistente de inteligencia visual" title="Consultar inteligencia del archivo fotográfico">
        <span class="chat-btn-icon">👁️</span>
        <span class="chat-btn-text">Inteligencia Visual</span>
      </button>

      <!-- Panel / Ventana de Chat -->
      <div id="chat-drawer" class="hide" role="dialog" aria-modal="true" aria-label="Asistente Fotográfico de Punto de vista">
        <div class="chat-header">
          <div class="chat-header-info">
            <div class="chat-title"><span class="chat-dot"></span> Punto de vista · Inteligencia Visual</div>
            <div class="chat-subtitle">Buscador Conceptual, Linajes & Disparadores Creativos</div>
          </div>
          <button id="chat-close-btn" aria-label="Cerrar ventana">✕</button>
        </div>

        <div class="chat-messages" id="chat-messages">
          <div class="chat-msg bot">
            <div class="msg-avatar">📸</div>
            <div class="msg-content">
              <p><strong>Bienvenido al Observatorio de Punto de vista.</strong></p>
              <p>No soy un buscador de texto corriente. Puedo cruzar <strong>linajes visuales</strong> entre revistas de distintas épocas, buscar por <strong>atmósferas o conceptos</strong> y proponerte <strong>disparadores creativos</strong> con tu cámara.</p>
              <div class="chat-chips" id="chat-chips">
                ${SUGGESTIONS.map(s => `<button class="chat-chip" type="button">${s}</button>`).join('')}
              </div>
            </div>
          </div>
        </div>

        <form class="chat-input-row" id="chat-form">
          <input type="text" id="chat-input" placeholder="Busca por concepto, atmósfera o pide un disparador…" autocomplete="off" aria-label="Tu consulta">
          <button type="submit" id="chat-send-btn" aria-label="Enviar">➤</button>
        </form>
      </div>
    `;

    document.body.appendChild(widget);

    document.getElementById('chat-trigger-btn').addEventListener('click', toggleChat);
    document.getElementById('chat-close-btn').addEventListener('click', toggleChat);
    document.getElementById('chat-form').addEventListener('submit', handleUserSubmit);

    document.getElementById('chat-chips').addEventListener('click', (e) => {
      const chip = e.target.closest('.chat-chip');
      if (chip) {
        const text = chip.textContent.replace(/^[^\wáéíóúÁÉÍÓÚñÑ]+/, '').trim();
        document.getElementById('chat-input').value = text;
        handleUserSubmit(new Event('submit'));
      }
    });

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

  // Motor de Búsqueda Semántica y Conceptual
  function queryArchiveSemantic(query) {
    if (!archiveData) return { articles: [], podcasts: [], expandedTerms: [] };

    const rawTerms = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    const expandedTerms = new Set(rawTerms);

    // Expandir términos con el diccionario semántico
    rawTerms.forEach(t => {
      for (const [key, synonyms] of Object.entries(CONCEPT_MAP)) {
        if (t.includes(key) || key.includes(t)) {
          synonyms.forEach(s => expandedTerms.add(s));
        }
      }
    });

    const termsArray = Array.from(expandedTerms);

    const scoredArticles = (archiveData.articles || []).map(a => {
      let score = 0;
      const title = (a.title || '').toLowerCase();
      const photo = (a.photographer || '').toLowerCase();
      const summary = (a.summary || '').toLowerCase();
      const src = (a.source || '').toLowerCase();

      rawTerms.forEach(t => {
        if (title.includes(t)) score += 15;
        if (photo.includes(t)) score += 12;
        if (summary.includes(t)) score += 6;
        if (src.includes(t)) score += 4;
      });

      // Puntuación por afinidad semántica expandida
      termsArray.forEach(t => {
        if (title.includes(t)) score += 4;
        if (summary.includes(t)) score += 2;
      });

      return { ...a, score };
    }).filter(a => a.score > 0).sort((a, b) => b.score - a.score);

    const scoredPodcasts = (archiveData.podcasts || []).map(p => {
      let score = 0;
      const title = (p.title || '').toLowerCase();
      const desc = (p.description || '').toLowerCase();

      rawTerms.forEach(t => {
        if (title.includes(t)) score += 12;
        if (desc.includes(t)) score += 6;
      });

      termsArray.forEach(t => {
        if (title.includes(t)) score += 3;
        if (desc.includes(t)) score += 2;
      });

      return { ...p, score };
    }).filter(p => p.score > 0).sort((a, b) => b.score - a.score);

    return {
      articles: scoredArticles.slice(0, 6),
      podcasts: scoredPodcasts.slice(0, 3),
      expandedTerms: termsArray
    };
  }

  function generateAssistantResponse(query, results) {
    const qLower = query.toLowerCase();
    const { articles, podcasts } = results;

    // 1. Caso especial: Disparador Creativo
    if (qLower.includes('disparador') || qLower.includes('ejercicio') || qLower.includes('propuesta') || qLower.includes('reto')) {
      const topArt = articles[0] || (archiveData?.articles ? archiveData.articles[Math.floor(Math.random() * archiveData.articles.length)] : null);
      const title = topArt ? topArt.title : 'Geometría y Sombra en lo Cotidiano';
      const author = topArt?.photographer ? ` (${topArt.photographer})` : '';

      return `
        <div class="chat-prompt-card">
          <div class="chat-badge-prompt">✨ Disparador Creativo del Momento</div>
          <h4 style="margin:0.4rem 0;color:#fff;font-size:1.05rem;">Reto: El Espacio que No Ocupamos</h4>
          <p><em>Inspirado en el trabajo de «${title}»${author} en el archivo:</em></p>
          <p style="margin-top:0.5rem;color:#e2e8f0;font-size:0.95rem;">
            <strong>Tu ejercicio hoy:</strong> Encuentra un rincón de tu casa o de tu calle que veas todos los días y nunca hayas fotografiado. Espera a que la luz incida oblicua (al amanecer o al atardecer). Encuadra de tal manera que el espacio vacío o la sombra ocupe más del 70% del plano. Subexpón 1 punto para forzar el misterio.
          </p>
          <p style="font-size:0.8rem;opacity:0.75;margin-top:0.6rem;">💡 <em>¿Quieres otro disparador enfocado en retrato, arquitectura o película analógica?</em></p>
        </div>
      `;
    }

    // 2. Caso especial: Dossier de Tendencias
    if (qLower.includes('dossier') || qLower.includes('tendencia') || qLower.includes('informe') || qLower.includes('observatorio')) {
      return `
        <div class="chat-prompt-card">
          <div class="chat-badge-prompt">🌐 Observatorio de Tendencias</div>
          <h4 style="margin:0.4rem 0;color:#fff;">Dossier Semanal de Inteligencia Curatorial</h4>
          <p>Hemos analizado el pulso de más de 400 proyectos fotográficos en 18 revistas internacionales:</p>
          <ul style="margin:0.5rem 0 0.8rem 1.2rem;font-size:0.9rem;color:#cbd5e1;">
            <li><strong>Tendencia 1:</strong> El Espacio Doméstico como Escenario Psicológico y Duelo.</li>
            <li><strong>Tendencia 2:</strong> Arqueología de la Resistencia y Subculturas en Peligro.</li>
            <li><strong>Tendencia 3:</strong> La Imperfección Radical y Lentes de Carácter contra la Hipernitidez Sintética.</li>
          </ul>
          <p style="margin-top:0.5rem;">
            <a href="resumenes/tendencias-2026-W35.html" target="_blank" style="color:#ff4444;font-weight:600;text-decoration:underline;">Leer Dossier Completo de Tendencias →</a>
          </p>
        </div>
      `;
    }

    // 3. Caso Linaje Visual / Búsqueda Conceptual
    if (!articles.length && !podcasts.length) {
      return `
        <p>No encontré resonancias exactas para <em>«${query}»</em> en el archivo.</p>
        <p>💡 <em>Prueba preguntando por conceptos como:</em> <strong>soledad</strong>, <strong>grano analógico</strong>, <strong>nocturna</strong>, <strong>suburbia</strong>, <strong>arquitectura</strong> o nombres como <strong>Magnum</strong>, <strong>LensCulture</strong> o <strong>Ishmael Claxton</strong>.</p>
      `;
    }

    let out = `<p>He localizado estas resonancias conceptuales para <strong>«${query}»</strong> en el archivo:</p>`;

    if (articles.length >= 2) {
      out += `
        <div class="chat-lineage-box" style="background:rgba(255,51,51,0.08);border-left:3px solid #ff3333;padding:0.6rem 0.8rem;margin:0.6rem 0;border-radius:4px;">
          <strong style="color:#ff6666;font-size:0.85rem;">🧬 LINAJE VISUAL DETECTADO:</strong>
          <p style="font-size:0.88rem;margin-top:0.3rem;color:#f0f6fc;">
            Existe un diálogo directo entre <strong>«${articles[0].title}»</strong> (${articles[0].source.toUpperCase()}) y <strong>«${articles[1].title}»</strong> (${articles[1].source.toUpperCase()}) al abordar este concepto desde diferentes lenguajes visuales.
          </p>
        </div>
      `;
    }

    if (articles.length > 0) {
      out += `<div class="chat-results-section"><span class="chat-sec-badge">📄 Obras y Ensayos Resonantes</span>`;
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

    if (podcasts.length > 0) {
      out += `<div class="chat-results-section"><span class="chat-sec-badge">🎙️ Episodios Vinculados</span>`;
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
      const loading = addMessage('bot', '<p class="chat-typing"><span>●</span><span>●</span><span>●</span> Analizando mapa conceptual del archivo…</p>');
      await preloadArchive();
      loading.remove();
    }

    const results = queryArchiveSemantic(q);
    const responseHtml = generateAssistantResponse(q, results);
    addMessage('bot', responseHtml);
  }

  function escapeHtml(str) {
    return String(str).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectChatUI);
  } else {
    injectChatUI();
  }
})();
