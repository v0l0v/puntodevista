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
    'Atardeceres junto al agua y luz dorada',
    'Disparador creativo para hoy',
    'Linaje de la soledad urbana y suburbios',
    'Atmósfera nocturna, misterio y sombras',
    'Imperfección analógica y grano experimental',
    'Memoria familiar, duelo y espacio doméstico',
    'Dossier de Tendencias Visuales'
  ];

  // Diccionario semántico ampliado para fallback estático
  const CONCEPT_MAP = {
    'tren': ['tren', 'trenes', 'train', 'viaje', 'viajes', 'viajar', 'viajare', 'journey', 'tránsito', 'transit', 'estación', 'station', 'metro', 'subway', 'railway', 'andén', 'vagón', 'ventanilla', 'pasajeros', 'velocidad', 'movimiento'],
    'trenes': ['tren', 'trenes', 'train', 'viaje', 'journey', 'tránsito', 'transit', 'estación', 'station', 'railway', 'andén', 'vagón', 'ventanilla', 'pasajeros'],
    'viaje': ['viaje', 'viajes', 'viajar', 'viajare', 'journey', 'travel', 'trip', 'trayecto', 'ruta', 'desplazamiento', 'carretera', 'tren', 'estación', 'tránsito'],
    'viajar': ['viaje', 'viajes', 'viajar', 'viajare', 'journey', 'travel', 'trip', 'trayecto', 'tren', 'estación'],
    'lluvia': ['lluvia', 'rain', 'tormenta', 'niebla', 'fog', 'charcos', 'paraguas', 'gotas', 'cristal', 'mojado'],
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
      <button id="chat-trigger-btn" aria-label="Abrir Estenopo · Inteligencia Visual" title="Consultar a Estenopo sobre el archivo fotográfico">
        <span class="chat-btn-text">Estenopo</span>
      </button>

      <!-- Panel Lateral Vertical Estenopo -->
      <div id="chat-drawer" class="hide" role="dialog" aria-modal="true" aria-label="Estenopo · Inteligencia Visual">
        
        <!-- Cabecera Estenopo -->
        <div class="chat-header">
          <div class="chat-header-left">
            <div class="chat-badge-glow">Estenopo</div>
            <div class="chat-header-info">
              <div class="chat-title">Inteligencia Visual & Curaduría</div>
              <div class="chat-subtitle">Ensayos · Linajes · Resonancias Visuales</div>
            </div>
          </div>
          <div class="chat-header-actions">
            <button id="chat-clear-btn" class="chat-tool-btn" title="Reiniciar vista">↺</button>
            <button id="chat-expand-btn" class="chat-tool-btn" title="Expandir/Reducir ancho">⛶</button>
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
            <div class="msg-avatar-estenopo">E</div>
            <div class="msg-content" id="chat-intro-content">
              ${getIntroWelcomeHtml()}
            </div>
          </div>
        </div>

        <!-- Barra de Input Flotante Estenopo -->
        <form class="gemini-input-container" id="chat-form">
          <div class="gemini-input-wrapper">
            <input type="text" id="chat-input" placeholder="Pregunta sobre atmósferas de luz, conceptos, autores o etiquetas…" autocomplete="off" aria-label="Escribe tu consulta">
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
        const text = chip.textContent.replace(/^[^\wáéíóúÁÉÍÓÚñÑ#]+/, '').trim();
        document.getElementById('chat-input').value = text;
        handleUserSubmit(new Event('submit'));
      }
    });

    preloadArchive();
  }

  function getIntroWelcomeHtml() {
    return `
      <p class="gemini-greeting"><strong>Estenopo · Inteligencia Visual</strong></p>
      <p style="color:#cbd5e1;font-size:0.875rem;line-height:1.5;margin:0.35rem 0 0.85rem;">
        Escribe en el chat cualquier idea, sensación o autor, o pulsa en uno de los accesos rápidos para <strong>enfocar tu búsqueda</strong> en el archivo:
      </p>

      <div class="estenopo-intro-grid">
        <div class="estenopo-intro-card card-atmosphere" role="button" tabindex="0" onclick="window.askEstenopoQuery('Atardeceres junto al agua y luz dorada', event)" title="Pulsa para enfocar por atmósfera y luz">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">Atmósferas & Luz</span>
            <span class="estenopo-card-action">Enfocar luz →</span>
          </div>
          <strong>Buscar por tono y sensación</strong>
          <p>Escribe cómo te sientes o la luz que buscas: <em>«luces de neón en la niebla»</em>, <em>«atardecer junto al mar»</em> o <em>«penumbra»</em>.</p>
        </div>

        <div class="estenopo-intro-card card-lineage" role="button" tabindex="0" onclick="window.askEstenopoQuery('Linaje de la soledad urbana y suburbios', event)" title="Pulsa para contrastar miradas y linajes">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">Linajes Visuales</span>
            <span class="estenopo-card-action">Cruzar miradas →</span>
          </div>
          <strong>Diálogo entre fotógrafos</strong>
          <p>Compara cómo distintos autores y publicaciones abordan un mismo tema estético a lo largo del tiempo.</p>
        </div>

        <div class="estenopo-intro-card card-spark" role="button" tabindex="0" onclick="window.askEstenopoQuery('Disparador creativo para hoy', event)" title="Pulsa para pedir un reto fotográfico">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">Disparador Creativo</span>
            <span class="estenopo-card-action">Pedir reto →</span>
          </div>
          <strong>Un ejercicio para salir hoy</strong>
          <p>Pide un reto técnico y poético adaptado a tu plan: <em>«viajo en tren»</em>, <em>«día de lluvia»</em> o <em>«retrato sin rostro»</em>.</p>
        </div>

        <div class="estenopo-intro-card card-taxonomy">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">Constelaciones</span>
            <span class="estenopo-card-action">Filtrar tag</span>
          </div>
          <strong>Filtrar por etiquetas clave</strong>
          <div class="estenopo-intro-tags">
            <button type="button" onclick="window.askEstenopoTag('#calle', event)" class="estenopo-tag-badge">#calle</button>
            <button type="button" onclick="window.askEstenopoTag('#analógico', event)" class="estenopo-tag-badge">#analógico</button>
            <button type="button" onclick="window.askEstenopoTag('#intimidad', event)" class="estenopo-tag-badge">#intimidad</button>
            <button type="button" onclick="window.askEstenopoTag('#marina', event)" class="estenopo-tag-badge">#marina</button>
            <button type="button" onclick="window.askEstenopoTag('#nocturna', event)" class="estenopo-tag-badge">#nocturna</button>
            <button type="button" onclick="window.askEstenopoTag('#viaje', event)" class="estenopo-tag-badge">#viaje</button>
          </div>
        </div>
      </div>
    `;
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
        <div class="msg-avatar-estenopo">📷</div>
        <div class="msg-content">
          ${getIntroWelcomeHtml()}
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
      ? '<div class="msg-avatar-estenopo">📷</div>' 
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

    const stopwords = new Set([
      'junto', 'los', 'las', 'del', 'con', 'para', 'por', 'sobre', 'una', 'uno', 'unas', 'unos',
      'que', 'como', 'and', 'the', 'for', 'with', 'gustaria', 'gustaría', 'mañana', 'hoy', 'dia',
      'día', 'quiero', 'dame', 'disparador', 'creativo', 'ejercicio', 'reto', 'propuesta', 'ideas',
      'idea', 'hacer', 'fotos', 'fotografia', 'fotografía', 'hacia', 'desde', 'este', 'esta'
    ]);
    const rawTerms = query.toLowerCase().split(/\s+/).filter(w => w.length > 2 && !stopwords.has(w));
    const expandedTerms = new Set(rawTerms);

    // Expandir con el mapa semántico
    rawTerms.forEach(t => {
      for (const [key, synonyms] of Object.entries(CONCEPT_MAP)) {
        if (t === key || key.includes(t)) {
          synonyms.forEach(s => expandedTerms.add(s.toLowerCase()));
        }
      }
    });

    const termsArray = Array.from(expandedTerms);

    const scoredArticles = dataset.map(a => {
      let aTags = [];
      if (Array.isArray(a.tags)) aTags = a.tags;
      else if (typeof a.tags === 'string') {
        try { aTags = JSON.parse(a.tags); } catch { aTags = []; }
      }

      rawTerms.forEach(t => {
        const cleanT = t.replace(/^#/, '');
        if (aTags.some(tag => tag.toLowerCase().replace(/^#/, '') === cleanT)) {
          score += 35;
        }
        if (matchWordInText(rawTitle, t)) score += 20;
        if (matchWordInText(rawPhoto, t)) score += 15;
        if (matchWordInText(rawSummary, t)) score += 8;
        if (matchWordInText(rawSrc, t)) score += 5;
      });

      termsArray.forEach(t => {
        const cleanT = t.replace(/^#/, '');
        if (aTags.some(tag => tag.toLowerCase().replace(/^#/, '') === cleanT)) {
          score += 15;
        }
        if (matchWordInText(rawTitle, t)) score += 6;
        if (matchWordInText(rawSummary, t)) score += 3;
      });

      return {
        id: a._id || a.id || a.link,
        title: rawTitle,
        photographer: rawPhoto,
        source: rawSrc,
        url: a.link || a.url,
        published_date: a.date || a._parsedDate,
        summary: rawSummary,
        image: a.image || a.thumbnail || '',
        tags: aTags,
        score,
        rank_type: 'Semántica Heurística'
      };
    }).filter(a => a.score > 0).sort((a, b) => b.score - a.score);

    const podcastsDataset = window.__podcastEntries || archiveData?.podcasts || [];
    const scoredPodcasts = podcastsDataset.map(p => {
      let score = 0;
      const title = decodeHtmlEntities(p.title || p.podcast_title || '');
      const desc = decodeHtmlEntities(p.description || '');

      rawTerms.forEach(t => {
        if (matchWordInText(title, t)) score += 15;
        if (matchWordInText(desc, t)) score += 8;
      });

      termsArray.forEach(t => {
        if (matchWordInText(title, t)) score += 5;
        if (matchWordInText(desc, t)) score += 3;
      });

      return { ...p, title, description: desc, score };
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

    // 1. Caso especial: Disparador Creativo Contextualizado
    if (qLower.includes('disparador') || qLower.includes('ejercicio') || qLower.includes('propuesta') || qLower.includes('reto')) {
      const topArt = articles[0] || (window.__allEntries ? window.__allEntries[Math.floor(Math.random() * window.__allEntries.length)] : null);
      const title = topArt ? (topArt.title || 'Geometría y Sombra en lo Cotidiano') : 'Geometría y Sombra en lo Cotidiano';
      const articleId = topArt ? escapeHtml(String(topArt.id || topArt._id || topArt.url || topArt.link || '')) : '';
      const sourceSafe = topArt ? escapeHtml(String(topArt.source || topArt._source || '')) : '';
      const sourceName = topArt ? escapeHtml(String(topArt.source || topArt._source || 'ARCHIVO').toUpperCase()) : 'ARCHIVO';
      const url = topArt?.url || topArt?.link || '#';
      const photo = topArt?.photographer ? escapeHtml(topArt.photographer) : '';

      let topTags = [];
      if (topArt) {
        if (Array.isArray(topArt.tags)) topTags = topArt.tags;
        else if (typeof topArt.tags === 'string') {
          try { topTags = JSON.parse(topArt.tags); } catch { topTags = []; }
        }
      }
      const topTagsHtml = topTags.length > 0
        ? `<div class="estenopo-tags-row">${topTags.map(t => `<button type="button" class="estenopo-tag-badge" onclick="window.askEstenopoTag('${escapeHtml(t)}', event)">${escapeHtml(t)}</button>`).join('')}</div>`
        : '';

      // Generar reto contextual analizando la intención del usuario y la obra de referencia
      const tLow = title.toLowerCase();
      let retoTitulo = 'El Espacio que No Ocupamos';
      let retoTexto = 'Encuentra un rincón cotidiano donde la luz incida oblicua (amanecer o atardecer). Encuadra dejando que la sombra o el espacio negativo ocupe más del 70% del encuadre. Dispara en manual y subexpón 1 punto para forzar el misterio.';

      if (qLower.includes('tren') || qLower.includes('viaj') || qLower.includes('trayect') || qLower.includes('estacion') || qLower.includes('estación') || qLower.includes('transit') || tLow.includes('train') || tLow.includes('journey') || tLow.includes('rail')) {
        retoTitulo = 'La Ventanilla: Umbral entre Intimidad y Velocidad (Tren & Tránsito)';
        retoTexto = `
          <strong>1. Doble Exposición en el Cristal:</strong> Enfoca en manual a la superficie de la ventanilla. Superpón el reflejo del interior (la mirada o las manos de un pasajero) con el paisaje exterior que corre a gran velocidad.<br><br>
          <strong>2. Contraste Cinético:</strong> Apoya la cámara firme en el reposabrazos o tu rodilla y dispara a <strong>1/15s – 1/30s</strong>: el interior del vagón quedará nítido mientras el exterior se convertirá en un barrido de líneas cinéticas abstractas.<br><br>
          <strong>3. El No-Lugar:</strong> En las paradas intermedias, captura el instante fugaz en que alguien espera en el andén o se despide a través del cristal.
        `;
      } else if (qLower.includes('lluvia') || qLower.includes('niebla') || qLower.includes('tormenta') || tLow.includes('rain') || tLow.includes('fog')) {
        retoTitulo = 'Atmósferas Difusas y Superficies Húmedas';
        retoTexto = 'Aprovecha las gotas en cristales o los reflejos en el asfalto mojado. Dispara a máxima apertura (f/1.8 – f/2.8) enfocando en una sola gota para convertir las luces de fondo en bokeh de color cinematográfico.';
      } else if (qLower.includes('noche') || qLower.includes('nocturn') || qLower.includes('neon') || qLower.includes('neón') || tLow.includes('night') || tLow.includes('shadow')) {
        retoTitulo = 'Claroscuro y Luces Aisladas';
        retoTexto = 'Encuentra una única fuente de luz artificial (farola, escaparate o neón). Mide la exposición en las altas luces y deja que las sombras caigan en negro profundo para forzar la intriga psicológica.';
      } else if (tLow.includes('street') || tLow.includes('calle') || tLow.includes('urban') || tLow.includes('city') || qLower.includes('calle')) {
        retoTitulo = 'La Coincidencia Involuntaria (Street Photography)';
        retoTexto = 'Sal a una calle transitada, busca un fondo con fuerte contraste geométrico o color plano y espera inmóvil a que un transeúnte complete la composición con su postura, sombra o vestimenta. Prioriza el instante decisivo.';
      } else if (tLow.includes('portrait') || tLow.includes('retrato') || tLow.includes('body') || tLow.includes('cuerpo') || qLower.includes('retrato')) {
        retoTitulo = 'Retrato sin Mirada';
        retoTexto = 'Fotografía a una persona cercana sin mostrar directamente sus ojos: concéntrate en la tensión de las manos, el gesto de la espalda o la silueta contra una ventana en penumbra.';
      } else if (tLow.includes('sea') || tLow.includes('water') || tLow.includes('mar') || tLow.includes('ocean') || tLow.includes('landscape') || tLow.includes('nature') || qLower.includes('mar') || qLower.includes('agua')) {
        retoTitulo = 'Textura Líquida y Línea de Horizonte';
        retoTexto = 'Busca agua en movimiento o niebla matutina. Reduce la velocidad de obturación a 1/8s – 1/2s para capturar el flujo sin perder la estructura geométrica del entorno.';
      }

      return `
        <div class="gemini-response-box">
          <div class="gemini-badge-sparkle">Disparador Creativo</div>
          <h4 style="margin:0.5rem 0 0.3rem;color:#fff;font-size:1.05rem;font-family:'Playfair Display',serif;">Reto: ${retoTitulo}</h4>
          <p style="color:#cbd5e1;font-size:0.86rem;line-height:1.4;margin-bottom:0.4rem;">
            Inspirado en el lenguaje visual de esta obra del archivo:
          </p>
          
          <div class="estenopo-link-item" style="margin: 0.5rem 0 0.75rem;">
            <div class="estenopo-link-meta">
              <span>${sourceName}</span>
              ${photo ? `<span class="estenopo-link-author">· ${photo}</span>` : ''}
            </div>
            <a href="javascript:void(0)" onclick="window.openArticleModalById('${articleId}', '${sourceSafe}')" class="estenopo-link-title" title="Abrir en Lector">
              ${escapeHtml(title)}
            </a>
            ${topTagsHtml}
            <div class="estenopo-link-actions">
              <button class="estenopo-mini-btn view" onclick="window.openArticleModalById('${articleId}', '${sourceSafe}')" title="Abrir en Lector">
                Abrir en Lector
              </button>
              ${url !== '#' ? `<a href="${url}" target="_blank" rel="noopener noreferrer" class="estenopo-mini-btn" title="Ir a fuente original">Original ↗</a>` : ''}
            </div>
          </div>

          <div style="background:rgba(255,68,68,0.06);border-left:3px solid #ff4444;padding:0.75rem;margin:0.75rem 0;border-radius:4px;color:#f8fafc;font-size:0.88rem;line-height:1.5;">
            <strong>Tu ejercicio para el trayecto:</strong><br>${retoTexto}
          </div>
          <p style="font-size:0.78rem;opacity:0.8;margin-top:0.4rem;color:#94a3b8;"><em>¿Quieres ajustar el reto a blanco y negro, película analógica o fotografía de viaje?</em></p>
        </div>
      `;
    }

    // 2. Caso especial: Dossier de Tendencias
    if (qLower.includes('dossier') || qLower.includes('tendencia') || qLower.includes('informe') || qLower.includes('observatorio')) {
      return `
        <div class="gemini-response-box">
          <div class="gemini-badge-sparkle">Observatorio de Tendencias</div>
          <h4 style="margin:0.5rem 0;color:#fff;font-size:1.02rem;">Dossier de Inteligencia Curatorial</h4>
          <p style="color:#cbd5e1;font-size:0.86rem;">Patrones y resonancias visuales identificadas en el archivo:</p>
          <ul style="margin:0.5rem 0 0.8rem 1.2rem;font-size:0.84rem;color:#cbd5e1;line-height:1.5;">
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
          <p style="margin-top:0.5rem;font-size:0.85rem;color:#94a3b8;">
            <em>Prueba buscando por:</em> <strong>atardeceres junto al agua</strong>, <strong>soledad urbana</strong>, <strong>luz de neón nocturna</strong>, <strong>grano analógico</strong>, <strong>arquitectura brutalista</strong> o etiquetas como <strong>#calle</strong> o <strong>#analógico</strong>.
          </p>
        </div>
      `;
    }

    let out = `
      <div class="gemini-response-box">
        <p style="color:#e2e8f0;font-size:0.9rem;line-height:1.5;">
          Resonancias seleccionadas para <strong>«${escapeHtml(query)}»</strong>:
        </p>
    `;

    // Linaje si hay múltiples artículos
    if (articles.length >= 2) {
      const a1 = articles[0];
      const a2 = articles[1];
      const id1 = escapeHtml(String(a1.id || a1.url));
      const src1 = escapeHtml(String(a1.source || ''));
      const id2 = escapeHtml(String(a2.id || a2.url));
      const src2 = escapeHtml(String(a2.source || ''));

      out += `
        <div class="gemini-lineage-banner">
          <div class="gemini-lineage-title">Linaje Visual Detectado</div>
          <div class="gemini-lineage-desc">
            Diálogo estético entre <a href="javascript:void(0)" onclick="window.openArticleModalById('${id1}', '${src1}')" style="color:#ff8a65;text-decoration:underline;">«${escapeHtml(a1.title)}»</a> (${src1.toUpperCase()}) y <a href="javascript:void(0)" onclick="window.openArticleModalById('${id2}', '${src2}')" style="color:#ff8a65;text-decoration:underline;">«${escapeHtml(a2.title)}»</a> (${src2.toUpperCase()}).
          </div>
        </div>
      `;
    }

    // Lista de Enlaces Sombreados para Artículos con Etiquetas
    if (articles.length > 0) {
      out += `
        <div class="gemini-section-header">
          <span>Obras & Ensayos Seleccionados</span>
        </div>
        <div class="estenopo-links-list">
      `;

      articles.forEach(a => {
        const photo = a.photographer ? escapeHtml(a.photographer) : '';
        const sourceName = escapeHtml((a.source || 'ARCHIVO').toUpperCase());
        const articleId = escapeHtml(String(a.id || a.url));
        const sourceSafe = escapeHtml(String(a.source || ''));
        const tagsList = a.tags || [];
        const tagsHtml = tagsList.length > 0
          ? `<div class="estenopo-tags-row">${tagsList.map(t => `<button type="button" class="estenopo-tag-badge" onclick="window.askEstenopoTag('${escapeHtml(t)}', event)">${escapeHtml(t)}</button>`).join('')}</div>`
          : '';

        out += `
          <div class="estenopo-link-item">
            <div class="estenopo-link-meta">
              <span>${sourceName}</span>
              ${photo ? `<span class="estenopo-link-author">· ${photo}</span>` : ''}
            </div>
            <a href="javascript:void(0)" onclick="window.openArticleModalById('${articleId}', '${sourceSafe}')" class="estenopo-link-title" title="Abrir en Lector">
              ${escapeHtml(a.title)}
            </a>
            ${tagsHtml}
            <div class="estenopo-link-actions">
              <button class="estenopo-mini-btn view" onclick="window.openArticleModalById('${articleId}', '${sourceSafe}')" title="Abrir artículo completo en lector">
                Lector
              </button>
              <a href="${a.url}" target="_blank" rel="noopener noreferrer" class="estenopo-mini-btn" title="Ir a la publicación original">
                Original ↗
              </a>
            </div>
          </div>
        `;
      });

      out += `</div>`;
    }

    // Podcasts Vinculados en formato Enlaces Sombreados
    if (podcasts.length > 0) {
      out += `
        <div class="gemini-section-header" style="margin-top:1rem">
          <span>Episodios & Podcasts Relacionados</span>
        </div>
        <div class="estenopo-podcasts-list">
      `;

      podcasts.forEach(p => {
        const durationMin = p.duration ? `${Math.floor(p.duration / 60)} min` : '';
        const dateStr = p.date || '';
        const audioUrl = p.audio_url || p.link || '';

        out += `
          <div class="estenopo-podcast-item">
            <div class="estenopo-podcast-meta">${dateStr} ${durationMin ? `· ${durationMin}` : ''}</div>
            <div class="estenopo-podcast-title">${escapeHtml(p.title || 'Resumen Diario')}</div>
            <div class="estenopo-link-actions">
              ${audioUrl ? `<button class="estenopo-mini-btn view" onclick="window.playPodcastByUrl('${audioUrl}')">Escuchar</button>` : ''}
              <a href="episodios.html" target="_blank" class="estenopo-mini-btn">Ver Todos →</a>
            </div>
          </div>
        `;
      });

      out += `</div>`;
    }

    out += `</div>`;
    return out;
  }

  window.askEstenopoTag = function(tag, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = tag;
      handleUserSubmit(new Event('submit'));
    }
  };

  window.askEstenopoQuery = function(query, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const input = document.getElementById('chat-input');
    if (input) {
      input.value = query;
      handleUserSubmit(new Event('submit'));
    }
  };

  async function handleUserSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const q = (input?.value || '').trim();
    if (!q) return;

    input.value = '';
    addMessage('user', `<p>${escapeHtml(q)}</p>`);

    const loading = addMessage('bot', `
      <div class="gemini-typing-indicator">
        <span class="sparkle-spin">📷</span> Estenopo está consultando el archivo…
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

  function decodeHtmlEntities(str) {
    if (!str) return '';
    const txt = document.createElement('textarea');
    txt.innerHTML = str;
    return txt.value
      .replace(/&#8217;/g, "'")
      .replace(/&#8216;/g, "'")
      .replace(/&#8220;/g, '"')
      .replace(/&#8221;/g, '"')
      .replace(/&#8211;/g, '–')
      .replace(/&#8212;/g, '—')
      .replace(/&#039;/g, "'")
      .replace(/&amp;/g, '&')
      .replace(/&quot;/g, '"')
      .replace(/&lt;/g, '<')
      .replace(/&gt;/g, '>');
  }

  function matchWordInText(text, term) {
    if (!text || !term) return false;
    const escaped = term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    const regex = new RegExp(`(^|[^\\p{L}\\p{N}])${escaped}($|[^\\p{L}\\p{N}])`, 'iu');
    return regex.test(text);
  }

  function escapeHtml(str) {
    const clean = decodeHtmlEntities(String(str || ''));
    return clean
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

