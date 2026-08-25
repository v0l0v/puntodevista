/**
 * chat.js — Asistente de Inteligencia Curatorial, Linaje Visual y Buscador Conceptual
 * Diseño estilo Gemini Chat (Panel inferior de media pantalla con tarjetas visuales e interactividad).
 */

(function () {
  let archiveData = null;
  let isFetchingArchive = false;
  let isOpen = false;
  let isExpanded = false;

  const SUGGESTIONS = [
    '🌅 Atardeceres junto al agua y luces doradas',
    '✨ Disparador Creativo para hoy',
    '🧬 Linaje de la soledad urbana y suburbios',
    '🌙 Atmósfera nocturna, misterio y sombras',
    '🎞️ Imperfección analógica y grano experimental',
    '🏠 Memoria familiar, duelo y espacio doméstico',
    '🌐 Ver Dossier Semanal de Tendencias'
  ];

  // Diccionario semántico ampliado para fallback estático
  const CONCEPT_MAP = {
    'agua': ['mar', 'playa', 'océano', 'costa', 'río', 'lago', 'olas', 'surf', 'water', 'beach', 'sea', 'ocean'],
    'atardecer': ['puesta de sol', 'crepúsculo', 'sunset', 'golden hour', 'luz dorada', 'anochecer', 'sol', 'cielo'],
    'atardeceres': ['puesta de sol', 'crepúsculo', 'sunset', 'golden hour', 'luz dorada', 'mar', 'agua', 'sol'],
    'mar': ['agua', 'playa', 'costa', 'océano', 'surf', 'litoral', 'puerto'],
    'nostalgia': ['memoria', 'pasado', 'analógico', 'tiempo', 'grano', 'melancolía', 'recuerdo', 'archivo', 'infancia'],
    'soledad': ['aislamiento', 'silencio', 'vacío', 'nocturno', 'suburbia', 'individual', 'distancia', 'quietud'],
    'urbano': ['calle', 'ciudad', 'arquitectura', 'transeúntes', 'asfalto', 'metrópoli', 'tokio', 'barrio', 'concreto'],
    'calle': ['street', 'urbano', 'espontáneo', 'peatones', 'calles', 'instantánea', 'cándido'],
    'luz': ['claroscuro', 'crepúsculo', 'sombra', 'neón', 'contraste', 'atardecer', 'reflejos', 'iluminación'],
    'noche': ['nocturna', 'neón', 'oscuridad', 'sombras', 'luces', 'madrugada', 'misterio'],
    'analógico': ['película', '35mm', 'formato medio', 'grano', 'emulsión', 'química', 'lomography', 'pinhole', 'estenopeica', 'nikkor', 'leica'],
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
      <button id="chat-trigger-btn" aria-label="Abrir Inteligencia Visual" title="Consultar inteligencia del archivo fotográfico">
        <span class="chat-btn-sparkle">✨</span>
        <span class="chat-btn-text">Inteligencia Visual</span>
      </button>

      <!-- Panel Inferior Estilo Gemini Chat (Media Pantalla) -->
      <div id="chat-drawer" class="hide" role="dialog" aria-modal="true" aria-label="Gemini · Inteligencia Visual">
        
        <!-- Barra de arrastre / Handle superior -->
        <div class="chat-drag-handle" title="Arrastrar o cambiar tamaño"></div>

        <!-- Cabecera Gemini -->
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="gemini-badge-glow">✨ Gemini</div>
            <div class="chat-header-info">
              <div class="chat-title">Inteligencia Visual & Curaduría</div>
              <div class="chat-subtitle">Buscador Conceptual · 860+ Obras · Linajes & Podcasts</div>
            </div>
          </div>
          <div class="chat-header-actions">
            <button id="chat-clear-btn" class="chat-tool-btn" title="Limpiar conversación">🗑️</button>
            <button id="chat-expand-btn" class="chat-tool-btn" title="Expandir/Reducir ventana">⛶</button>
            <button id="chat-close-btn" class="chat-tool-btn" title="Cerrar panel">✕</button>
          </div>
        </div>

        <!-- Sugerencias de consulta tipo Chips Horizontales -->
        <div class="chat-chips-scroll" id="chat-chips">
          ${SUGGESTIONS.map(s => `<button class="gemini-chip" type="button">${s}</button>`).join('')}
        </div>

        <!-- Zona de Mensajes del Chat -->
        <div class="chat-messages" id="chat-messages">
          <div class="chat-msg bot">
            <div class="msg-avatar-gemini">✨</div>
            <div class="msg-content">
              <p class="gemini-greeting"><strong>Hola. Soy el asistente de Inteligencia Visual de <em>Punto de vista</em>.</strong></p>
              <p>Exploro las conexiones conceptuales, estéticas y técnicas a través de los <strong>867 artículos y 22 podcasts</strong> del archivo histórico.</p>
              <p style="margin-top:0.4rem;font-size:0.85rem;color:#cbd5e1;">Pídeme encontrar proyectos por <strong>atmósferas</strong> (<em>«atardeceres junto al agua»</em>, <em>«luces de neón en la niebla»</em>), descubrir <strong>linajes entre fotógrafos</strong> o un <strong>disparador creativo</strong> para salir hoy a hacer fotos.</p>
            </div>
          </div>
        </div>

        <!-- Barra de Input Flotante Estilo Gemini -->
        <form class="gemini-input-container" id="chat-form">
          <div class="gemini-input-wrapper">
            <span class="gemini-input-icon">✨</span>
            <input type="text" id="chat-input" placeholder="Pregunta sobre una atmósfera, autor, concepto o técnica…" autocomplete="off" aria-label="Escribe tu consulta">
            <button type="submit" id="chat-send-btn" aria-label="Enviar consulta">
              <svg width="18" height="18" viewBox="0 0 24 24" fill="currentColor">
                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
              </svg>
            </button>
          </div>
        </form>
      </div>
    `;

    document.body.appendChild(widget);

    document.getElementById('chat-trigger-btn').addEventListener('click', toggleChat);
    document.getElementById('chat-close-btn').addEventListener('click', toggleChat);
    document.getElementById('chat-expand-btn').addEventListener('click', toggleExpand);
    document.getElementById('chat-clear-btn').addEventListener('click', clearChat);
    document.getElementById('chat-form').addEventListener('submit', handleUserSubmit);

    document.getElementById('chat-chips').addEventListener('click', (e) => {
      const chip = e.target.closest('.gemini-chip');
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
      if (window.__allEntries && window.__allEntries.length > 0) {
        archiveData = { articles: window.__allEntries, podcasts: window.__podcastEntries || [] };
      } else {
        const resp = await fetch('feeds.json');
        if (resp.ok) {
          const d = await resp.json();
          archiveData = { articles: d.items || [], podcasts: [] };
        }
      }
    } catch (e) {
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
      setTimeout(() => document.getElementById('chat-input')?.focus(), 150);
    }
  }

  function toggleExpand() {
    isExpanded = !isExpanded;
    const drawer = document.getElementById('chat-drawer');
    const expandBtn = document.getElementById('chat-expand-btn');
    if (!drawer) return;
    drawer.classList.toggle('expanded', isExpanded);
    if (expandBtn) expandBtn.textContent = isExpanded ? '⇣' : '⛶';
  }

  function clearChat() {
    const container = document.getElementById('chat-messages');
    if (!container) return;
    container.innerHTML = `
      <div class="chat-msg bot">
        <div class="msg-avatar-gemini">✨</div>
        <div class="msg-content">
          <p><strong>Conversación reiniciada.</strong></p>
          <p style="color:#cbd5e1;font-size:0.85rem;">¿Qué concepto visual o proyecto fotográfico te gustaría explorar ahora?</p>
        </div>
      </div>
    `;
  }

  function addMessage(sender, htmlContent) {
    const container = document.getElementById('chat-messages');
    if (!container) return;

    const row = document.createElement('div');
    row.className = `chat-msg ${sender}`;
    const avatar = sender === 'bot' 
      ? '<div class="msg-avatar-gemini">✨</div>' 
      : '<div class="msg-avatar-user">👤</div>';

    row.innerHTML = `
      ${avatar}
      <div class="msg-content">${htmlContent}</div>
    `;

    container.appendChild(row);
    container.scrollTop = container.scrollHeight;
    return row;
  }

  // Motor de Búsqueda Semántica y Conceptual (sqlite-vec + Gemini Embeddings con fallback)
  async function queryArchiveSemantic(query) {
    // 1. Intentar consultar el motor vectorial real en el backend (/api/search)
    try {
      const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}&mode=hybrid&limit=8`);
      if (resp.ok) {
        const data = await resp.json();
        if (data.status === 'ok' && data.items && data.items.length > 0) {
          const articles = data.items.map(item => ({
            id: item.id,
            title: item.title,
            photographer: item.photographer,
            source: item.source || item._source || '',
            url: item.url || item.link,
            published_date: item.published_date || item.date,
            summary: item.summary || item.excerpt || '',
            image: item.image_url || item.thumbnail || item.image || '',
            score: item.score || 10,
            rank_type: 'Vectorial (sqlite-vec + Gemini)'
          }));

          let podcasts = [];
          try {
            const podResp = await fetch(`/api/search?q=${encodeURIComponent(query)}&mode=podcast&limit=3`);
            if (podResp.ok) {
              const podData = await podResp.json();
              if (podData.status === 'ok' && podData.items) {
                podcasts = podData.items.map(p => ({
                  id: p.id,
                  title: p.title,
                  date: p.date,
                  description: p.description,
                  duration: p.duration,
                  audio_url: p.audio_url || p.link
                }));
              }
            }
          } catch {}

          return {
            articles,
            podcasts,
            mode: 'vectorial_real'
          };
        }
      }
    } catch {}

    // 2. Fallback enriquecido sobre todos los artículos cargados
    const dataset = (window.__allEntries && window.__allEntries.length > 0) 
      ? window.__allEntries 
      : (archiveData?.articles || []);

    const rawTerms = query.toLowerCase().split(/\s+/).filter(w => w.length > 2);
    const expandedTerms = new Set(rawTerms);

    // Expandir con el mapa semántico
    rawTerms.forEach(t => {
      for (const [key, synonyms] of Object.entries(CONCEPT_MAP)) {
        if (t.includes(key) || key.includes(t)) {
          synonyms.forEach(s => expandedTerms.add(s));
        }
      }
    });

    const termsArray = Array.from(expandedTerms);

    const scoredArticles = dataset.map(a => {
      let score = 0;
      const title = (a.title || '').toLowerCase();
      const photo = (a.photographer || '').toLowerCase();
      const summary = (a.summary || a.excerpt || a.content || '').toLowerCase();
      const src = (a._source || a.source || '').toLowerCase();

      rawTerms.forEach(t => {
        if (title.includes(t)) score += 20;
        if (photo.includes(t)) score += 15;
        if (summary.includes(t)) score += 8;
        if (src.includes(t)) score += 5;
      });

      termsArray.forEach(t => {
        if (title.includes(t)) score += 6;
        if (summary.includes(t)) score += 3;
      });

      return {
        id: a._id || a.id || a.link,
        title: a.title,
        photographer: a.photographer,
        source: a._source || a.source,
        url: a.link || a.url,
        published_date: a.date || a._parsedDate,
        summary: a.summary || a.excerpt || '',
        image: a.image || a.thumbnail || '',
        score,
        rank_type: 'Semántica Heurística'
      };
    }).filter(a => a.score > 0).sort((a, b) => b.score - a.score);

    const podcastsDataset = window.__podcastEntries || archiveData?.podcasts || [];
    const scoredPodcasts = podcastsDataset.map(p => {
      let score = 0;
      const title = (p.title || p.podcast_title || '').toLowerCase();
      const desc = (p.description || '').toLowerCase();

      rawTerms.forEach(t => {
        if (title.includes(t)) score += 15;
        if (desc.includes(t)) score += 8;
      });

      termsArray.forEach(t => {
        if (title.includes(t)) score += 5;
        if (desc.includes(t)) score += 3;
      });

      return { ...p, score };
    }).filter(p => p.score > 0).sort((a, b) => b.score - a.score);

    return {
      articles: scoredArticles.slice(0, 8),
      podcasts: scoredPodcasts.slice(0, 3),
      mode: 'fallback'
    };
  }

  function generateAssistantResponse(query, results) {
    const qLower = query.toLowerCase();
    const { articles, podcasts } = results;

    // 1. Caso especial: Disparador Creativo
    if (qLower.includes('disparador') || qLower.includes('ejercicio') || qLower.includes('propuesta') || qLower.includes('reto')) {
      const topArt = articles[0] || (window.__allEntries ? window.__allEntries[Math.floor(Math.random() * window.__allEntries.length)] : null);
      const title = topArt ? topArt.title : 'Geometría y Sombra en lo Cotidiano';
      const author = topArt?.photographer ? ` (${topArt.photographer})` : '';

      return `
        <div class="gemini-response-box">
          <div class="gemini-badge-sparkle">✨ Disparador Creativo del Día</div>
          <h4 style="margin:0.5rem 0;color:#fff;font-size:1.1rem;font-family:'Playfair Display',serif;">Reto: El Espacio que No Ocupamos</h4>
          <p style="color:#cbd5e1;font-size:0.92rem;line-height:1.5;">
            Inspirado en el lenguaje visual de <strong>«${escapeHtml(title)}»</strong>${author}:
          </p>
          <div style="background:rgba(255,1,0,0.08);border-left:3px solid #ff0100;padding:0.8rem;margin:0.8rem 0;border-radius:4px;color:#f8fafc;font-size:0.92rem;">
            <strong>Tu ejercicio hoy:</strong> Encuentra un rincón cotidiano donde la luz incida oblicua (al amanecer o al atardecer). Encuadra dejando que la sombra o el espacio negativo ocupe más del 70% del encuadre. Dispara en manual y subexpón 1 punto para forzar el misterio.
          </div>
          <p style="font-size:0.8rem;opacity:0.8;margin-top:0.4rem;">💡 <em>¿Te apetece otro disparador enfocado en retrato callejero o formato analógico?</em></p>
        </div>
      `;
    }

    // 2. Caso especial: Dossier de Tendencias
    if (qLower.includes('dossier') || qLower.includes('tendencia') || qLower.includes('informe') || qLower.includes('observatorio')) {
      return `
        <div class="gemini-response-box">
          <div class="gemini-badge-sparkle">🌐 Observatorio de Tendencias</div>
          <h4 style="margin:0.5rem 0;color:#fff;font-size:1.05rem;">Dossier Semanal de Inteligencia Curatorial</h4>
          <p style="color:#cbd5e1;font-size:0.9rem;">Hemos analizado el pulso de más de 850 proyectos fotográficos:</p>
          <ul style="margin:0.5rem 0 0.8rem 1.2rem;font-size:0.88rem;color:#cbd5e1;line-height:1.5;">
            <li><strong>Tendencia 1:</strong> El Espacio Doméstico como Escenario Psicológico.</li>
            <li><strong>Tendencia 2:</strong> Arqueología Visual de Subculturas y Comunidades.</li>
            <li><strong>Tendencia 3:</strong> La Imperfección Analógica frente a la Hipernitidez Sintética.</li>
          </ul>
          <p style="margin-top:0.6rem;">
            <a href="resumenes/tendencias-2026-W35.html" target="_blank" class="gemini-btn-primary">Leer Dossier Completo →</a>
          </p>
        </div>
      `;
    }

    // 3. Respuesta Curatorial para búsqueda conceptual
    if (!articles.length && !podcasts.length) {
      return `
        <div class="gemini-response-box">
          <p>No encontré obras que resuenen directamente con <em>«${escapeHtml(query)}»</em> en el archivo.</p>
          <p style="margin-top:0.5rem;font-size:0.88rem;color:#94a3b8;">
            💡 <em>Prueba preguntando por:</em> <strong>atardeceres junto al agua</strong>, <strong>soledad urbana</strong>, <strong>luz de neón nocturna</strong>, <strong>grano analógico</strong>, <strong>arquitectura brutalista</strong> o medios como <strong>Magnum</strong> o <strong>35mmc</strong>.
          </p>
        </div>
      `;
    }

    let out = `
      <div class="gemini-response-box">
        <p style="color:#e2e8f0;font-size:0.95rem;line-height:1.5;">
          He analizado el archivo y seleccionado estas resonancias para <strong>«${escapeHtml(query)}»</strong>:
        </p>
    `;

    // Linaje si hay múltiples artículos
    if (articles.length >= 2) {
      const a1 = articles[0];
      const a2 = articles[1];
      out += `
        <div class="gemini-lineage-banner">
          <div class="gemini-lineage-title">🧬 Linaje Visual Detectado</div>
          <div class="gemini-lineage-desc">
            Existe un diálogo estético notable entre <strong>«${escapeHtml(a1.title)}»</strong> (${(a1.source || '').toUpperCase()}) y <strong>«${escapeHtml(a2.title)}»</strong> (${(a2.source || '').toUpperCase()}) al abordar la atmósfera desde miradas complementarias.
          </div>
        </div>
      `;
    }

    // Grid de Tarjetas Visuales de Artículos
    if (articles.length > 0) {
      out += `
        <div class="gemini-section-header">
          <span>📸 Obras & Ensayos Seleccionados (${articles.length})</span>
        </div>
        <div class="gemini-cards-grid">
      `;

      articles.forEach(a => {
        const photo = a.photographer ? ` · <em>${escapeHtml(a.photographer)}</em>` : '';
        const thumb = a.image ? `<img src="${a.image}" alt="" class="gemini-card-thumb" loading="lazy" onerror="this.style.display='none'">` : '';
        const sourceName = (a.source || 'ARCHIVO').toUpperCase();
        const articleId = escapeHtml(String(a.id || a.url));
        const sourceSafe = escapeHtml(String(a.source || ''));

        out += `
          <div class="gemini-card">
            ${thumb}
            <div class="gemini-card-body">
              <div class="gemini-card-badge">${sourceName}${photo}</div>
              <h5 class="gemini-card-title">${escapeHtml(a.title)}</h5>
              <p class="gemini-card-snippet">${escapeHtml((a.summary || '').slice(0, 140))}…</p>
              <div class="gemini-card-actions">
                <button class="gemini-card-btn view-btn" onclick="window.openArticleModalById('${articleId}', '${sourceSafe}')" title="Abrir artículo completo con galería">
                  👁️ Abrir en Lector
                </button>
                <a href="${a.url}" target="_blank" rel="noopener noreferrer" class="gemini-card-btn ext-btn" title="Ir al sitio original">
                  Original ↗
                </a>
              </div>
            </div>
          </div>
        `;
      });

      out += `</div>`;
    }

    // Podcasts Vinculados
    if (podcasts.length > 0) {
      out += `
        <div class="gemini-section-header" style="margin-top:1.2rem">
          <span>🎙️ Episodios del Podcast Relacionados</span>
        </div>
        <div class="gemini-podcasts-list">
      `;

      podcasts.forEach(p => {
        const durationMin = p.duration ? `${Math.floor(p.duration / 60)} min` : '';
        const dateStr = p.date || '';
        const audioUrl = p.audio_url || p.link || '';

        out += `
          <div class="gemini-podcast-card">
            <div class="gemini-podcast-icon">🎙️</div>
            <div class="gemini-podcast-content">
              <div class="gemini-podcast-title">${escapeHtml(p.title || 'Resumen Diario')}</div>
              <div class="gemini-podcast-meta">Fecha: ${dateStr} ${durationMin ? `· ${durationMin}` : ''}</div>
              <div class="gemini-podcast-desc">${escapeHtml((p.description || '').slice(0, 150))}…</div>
              <div class="gemini-podcast-actions">
                ${audioUrl ? `<button class="gemini-pod-btn play" onclick="window.playPodcastByUrl('${audioUrl}')">▶ Reproducir Episodio</button>` : ''}
                <a href="episodios.html" target="_blank" class="gemini-pod-btn">Ver Todos →</a>
              </div>
            </div>
          </div>
        `;
      });

      out += `</div>`;
    }

    out += `</div>`;
    return out;
  }

  async function handleUserSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const q = (input?.value || '').trim();
    if (!q) return;

    input.value = '';
    addMessage('user', `<p>${escapeHtml(q)}</p>`);

    const loading = addMessage('bot', `
      <div class="gemini-typing-indicator">
        <span class="sparkle-spin">✨</span> Consultando archivo vectorial y cruzando linajes…
      </div>
    `);

    try {
      const results = await queryArchiveSemantic(q);
      loading.remove();
      const responseHtml = generateAssistantResponse(q, results);
      addMessage('bot', responseHtml);
    } catch (err) {
      loading.remove();
      addMessage('bot', `<p style="color:#ef4444">Ocurrió un error al procesar tu consulta. Inténtalo de nuevo.</p>`);
    }
  }

  function escapeHtml(str) {
    return String(str || '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#039;');
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', injectChatUI);
  } else {
    injectChatUI();
  }
})();

