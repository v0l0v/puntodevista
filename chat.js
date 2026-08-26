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

  // Diccionario Semántico Bilingüe Visual (ES <-> EN)
  const CONCEPT_MAP = {
    // Autores Canónicos
    'doisneau': ['doisneau', 'robert doisneau', 'street', 'calle', 'paris', 'parís', 'humanist', 'humanismo', 'black and white', 'blanco y negro', 'candid', 'pedestrian', 'instantánea'],
    'bresson': ['bresson', 'cartier-bresson', 'henri cartier-bresson', 'magnum', 'decisive moment', 'instante decisivo', 'street', 'calle', 'geometry', 'geometría', 'black and white'],
    'leiter': ['leiter', 'saul leiter', 'color', 'street', 'calle', 'reflections', 'reflejos', 'condensation', 'gotas', 'glass', 'cristales', 'abstract', 'abstracción', 'intimacy', 'intimidad'],
    'frank': ['frank', 'robert frank', 'the americans', 'road trip', 'carretera', 'journey', 'viaje', 'subculture', 'subcultura', 'solitude', 'soledad', 'black and white'],
    'arbus': ['arbus', 'diane arbus', 'portrait', 'retrato', 'identity', 'identidad', 'body', 'cuerpo', 'subculture', 'marginal', 'intimacy', 'intimidad', 'black and white'],
    'linaje': ['linaje', 'linajes', 'lineage', 'dialogue', 'diálogo', 'connection', 'conexión', 'resonance', 'resonancia', 'influence', 'influencia', 'tradition', 'tradición', 'masters', 'maestros'],

    // Paisaje, Naturaleza & Territorio (ES -> EN)
    'paisaje': ['landscape', 'landscapes', 'scenery', 'wilderness', 'terrain', 'territorio', 'horizon', 'horizonte', 'nature', 'naturaleza', 'solitude', 'quietude', 'rural'],
    'paisajes': ['landscape', 'landscapes', 'scenery', 'wilderness', 'terrain', 'territorio', 'horizon', 'horizonte', 'nature', 'naturaleza', 'solitude', 'quietude', 'rural'],
    'campo': ['field', 'fields', 'meadow', 'countryside', 'pasture', 'farmland', 'rural', 'terrain', 'earth', 'tierra', 'landscape'],
    'campos': ['field', 'fields', 'meadow', 'countryside', 'pasture', 'farmland', 'rural', 'terrain', 'earth', 'tierra', 'landscape'],
    'arbol': ['tree', 'trees', 'forest', 'woods', 'woodland', 'branches', 'canopy', 'foliage', 'botanical', 'flora', 'nature'],
    'arboles': ['tree', 'trees', 'forest', 'woods', 'woodland', 'branches', 'canopy', 'foliage', 'botanical', 'flora', 'nature'],
    'árbol': ['tree', 'trees', 'forest', 'woods', 'woodland', 'branches', 'canopy', 'foliage', 'botanical', 'flora', 'nature'],
    'árboles': ['tree', 'trees', 'forest', 'woods', 'woodland', 'branches', 'canopy', 'foliage', 'botanical', 'flora', 'nature'],
    'bosque': ['forest', 'woods', 'woodland', 'grove', 'trees', 'árboles', 'nature', 'fog', 'niebla'],
    'montaña': ['mountain', 'mountains', 'peaks', 'hills', 'alpine', 'rocky', 'elevation', 'landscape'],
    'montañas': ['mountain', 'mountains', 'peaks', 'hills', 'alpine', 'rocky', 'elevation', 'landscape'],
    'desierto': ['desert', 'sand', 'dunes', 'arid', 'barren', 'wasteland', 'isolation'],

    // Agua, Mar & Costa (ES -> EN)
    'mar': ['sea', 'ocean', 'coast', 'coastal', 'beach', 'playa', 'waves', 'olas', 'shore', 'shoreline', 'water', 'tide', 'marina', 'marine'],
    'playa': ['beach', 'shore', 'coast', 'sand', 'ocean', 'sea', 'mar', 'surf', 'surfing', 'waves'],
    'agua': ['water', 'ocean', 'sea', 'river', 'lake', 'stream', 'aquatic', 'liquid', 'reflection', 'waves'],
    'olas': ['waves', 'surf', 'surfing', 'ocean', 'swell', 'tide', 'sea', 'breakwater'],

    // Atmósfera, Clima & Luz (ES -> EN)
    'luz': ['light', 'sunlight', 'illumination', 'glow', 'chiaroscuro', 'shadow', 'shadows', 'radiance', 'claroscuro', 'ray'],
    'sombra': ['shadow', 'shadows', 'shade', 'darkness', 'silhouette', 'silueta', 'obscurity', 'penumbra', 'noir'],
    'sombras': ['shadow', 'shadows', 'shade', 'darkness', 'silhouette', 'silueta', 'obscurity', 'penumbra', 'noir'],
    'niebla': ['fog', 'mist', 'haze', 'misty', 'foggy', 'atmospheric', 'diffuse', 'vapor', 'obscurity', 'quietude'],
    'lluvia': ['rain', 'raining', 'rainy', 'wet', 'puddle', 'raindrops', 'storm', 'downpour', 'slick', 'mojado'],
    'atardecer': ['sunset', 'dusk', 'twilight', 'golden hour', 'sundown', 'evening', 'crepuscular', 'crepúsculo', 'glow'],
    'atardeceres': ['sunset', 'dusk', 'twilight', 'golden hour', 'sundown', 'evening', 'crepuscular', 'crepúsculo', 'glow'],
    'amanecer': ['sunrise', 'dawn', 'daybreak', 'morning', 'early morning', 'first light'],
    'noche': ['night', 'nocturnal', 'darkness', 'midnight', 'neon', 'shadows', 'noir', 'twilight', 'nocturna'],
    'nocturna': ['night', 'nocturnal', 'darkness', 'neon', 'shadows', 'noir', 'nighttime', 'midnight'],

    // Espacio Urbano & Calle (ES -> EN)
    'calle': ['street', 'streets', 'urban', 'sidewalk', 'pedestrian', 'crosswalk', 'city', 'avenue', 'candid', 'flaneur'],
    'calles': ['street', 'streets', 'urban', 'sidewalk', 'pedestrian', 'crosswalk', 'city', 'avenue', 'candid'],
    'urbano': ['urban', 'city', 'metropolis', 'cityscape', 'downtown', 'asphalt', 'buildings', 'metropolitan', 'barrio'],
    'ciudad': ['city', 'urban', 'metropolis', 'skyline', 'downtown', 'capital', 'streets', 'tokyo', 'new york', 'paris', 'london'],
    'suburbios': ['suburb', 'suburbs', 'suburbia', 'suburban', 'periphery', 'outskirts', 'neighborhood', 'residential'],
    'tren': ['train', 'railway', 'railroad', 'transit', 'subway', 'station', 'commute', 'wagon', 'carriage', 'window', 'passenger', 'journey'],
    'trenes': ['train', 'railway', 'railroad', 'transit', 'subway', 'station', 'commute', 'wagon', 'carriage', 'window', 'passenger', 'journey'],
    'viaje': ['journey', 'travel', 'trip', 'transit', 'voyage', 'road trip', 'commute', 'wanderlust', 'itinerary', 'destination'],
    'viajar': ['travel', 'journey', 'trip', 'roam', 'wander', 'transit', 'voyage'],

    // Emoción, Memoria & Soledad (ES -> EN)
    'soledad': ['solitude', 'solitary', 'lonely', 'loneliness', 'isolation', 'quietude', 'silence', 'stillness', 'remote', 'empty', 'abandoned'],
    'solitario': ['solitary', 'lonely', 'isolated', 'lone', 'alone', 'quiet', 'remote', 'single', 'abandoned', 'silent'],
    'solitarios': ['solitary', 'lonely', 'isolated', 'lone', 'alone', 'quiet', 'remote', 'abandoned', 'silent'],
    'silencio': ['silence', 'quiet', 'stillness', 'calm', 'peace', 'tranquil', 'serene', 'soundless'],
    'memoria': ['memory', 'nostalgia', 'past', 'recollection', 'remember', 'archive', 'remembrance', 'heritage', 'time'],
    'nostalgia': ['nostalgia', 'nostalgic', 'memory', 'melancholy', 'past', 'longing', 'vintage', 'analogue'],
    'duelo': ['grief', 'loss', 'mourning', 'bereavement', 'absence', 'sorrow', 'memory'],
    'intimidad': ['intimacy', 'intimate', 'domestic', 'home', 'house', 'room', 'interior', 'privacy', 'personal', 'bedroom'],
    'familia': ['family', 'parents', 'mother', 'father', 'childhood', 'children', 'generations', 'domestic'],

    // Retrato & Forma Humana (ES -> EN)
    'retrato': ['portrait', 'portraits', 'portraiture', 'face', 'gaze', 'mirada', 'headshot', 'expression', 'person'],
    'retratos': ['portrait', 'portraits', 'portraiture', 'faces', 'gaze', 'headshot', 'people'],
    'cuerpo': ['body', 'bodies', 'figure', 'nude', 'skin', 'flesh', 'gesture', 'human form', 'anatomy', 'movement'],
    'mirada': ['gaze', 'look', 'eyes', 'glance', 'stare', 'expression', 'portrait', 'eye contact'],
    'identidad': ['identity', 'gender', 'queer', 'trans', 'self', 'belonging', 'individuality', 'roots'],

    // Estética, Técnica & Formato (ES -> EN)
    'blanco y negro': ['black and white', 'b&w', 'monochrome', 'monochromatic', 'grayscale', 'silver gelatin'],
    'color': ['color', 'colour', 'palette', 'chromatic', 'vibrant', 'saturated', 'kodachrome', 'tones', 'hues'],
    'analógico': ['analogue', 'analog', 'film', '35mm', 'grain', 'darkroom', 'emulsion', 'medium format', 'chemical', 'grainy'],
    'grano': ['grain', 'grainy', 'texture', 'film grain', 'noise', 'emulsion', 'roughness'],
    'fotolibro': ['photobook', 'photo book', 'monograph', 'zine', 'fanzine', 'publication', 'publishing']
  };

  function injectChatUI() {
    if (document.getElementById('chat-widget')) return;

    const widget = document.createElement('div');
    widget.id = 'chat-widget';
    widget.innerHTML = `
      <!-- Botón Flotante Superior Derecho (Logo Estenopo Círculo / Pastilla Expandible) -->
      <button id="chat-trigger-btn" aria-label="Abrir Buscador · Inteligencia Visual" title="Buscador | Inteligencia Visual">
        <span class="estenopo-logo-wrapper">
          <img src="assets/logos/logoFpdv.png" alt="Estenopo" class="estenopo-cover-img">
        </span>
        <span class="chat-btn-text">Buscador | Inteligencia Visual</span>
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
        Escribe en el chat cualquier autor, idea o sensación en español, o elige un modo de búsqueda directa:
      </p>

      <div class="estenopo-intro-grid">
        <!-- 1. Clima y Atmósfera Visual -->
        <div class="estenopo-intro-card card-atmosphere" role="button" tabindex="0" onclick="window.askEstenopoCard('atmosphere', 'Atardeceres junto al agua y luz dorada', event)" title="Buscar fotografías por clima, luz y estado de ánimo">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">1. Clima & Luz</span>
            <span class="estenopo-card-action">Buscar clima →</span>
          </div>
          <strong>Sensación y Atmósfera</strong>
          <p>Busca por iluminación y estado de ánimo: <em>«niebla matutina»</em>, <em>«luces de neón»</em>, <em>«luz crepuscular»</em> o <em>«penumbra»</em>.</p>
        </div>

        <!-- 2. Cruces entre Fotógrafos / Genealogías -->
        <div class="estenopo-intro-card card-lineage" role="button" tabindex="0" onclick="window.askEstenopoCard('lineage', 'Linaje de la soledad urbana y suburbios', event)" title="Comparar cómo distintos fotógrafos abordan un mismo tema">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">2. Cruces & Autores</span>
            <span class="estenopo-card-action">Cruzar miradas →</span>
          </div>
          <strong>Diálogo entre Fotógrafos</strong>
          <p>Compara cómo distintos autores conectan entre sí: <em>«ecos de Saul Leiter»</em>, <em>«soledad en la metrópoli»</em> o <em>«mirada humanista»</em>.</p>
        </div>

        <!-- 3. Reto para Salir a Disparar -->
        <div class="estenopo-intro-card card-spark" role="button" tabindex="0" onclick="window.askEstenopoCard('spark', 'Disparador creativo para hoy', event)" title="Obtén un ejercicio fotográfico adaptado a tu situación de hoy">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">3. Reto para Disparar</span>
            <span class="estenopo-card-action">Pedir ejercicio →</span>
          </div>
          <strong>Inspiración para Salir Hoy</strong>
          <p>Pide un reto técnico y poético según tu plan: <em>«viajo en tren»</em>, <em>«día de lluvia»</em>, <em>«paseo nocturno»</em> o <em>«retrato sin rostro»</em>.</p>
        </div>

        <!-- 4. Exploración por Géneros y Técnicas -->
        <div class="estenopo-intro-card card-taxonomy">
          <div class="estenopo-card-header">
            <span class="estenopo-card-label">4. Temáticas & Géneros</span>
            <span class="estenopo-card-action">Filtrar tema</span>
          </div>
          <strong>Explorar el Archivo</strong>
          <div class="estenopo-intro-tags">
            <button type="button" onclick="window.askEstenopoTag('#calle', event)" class="estenopo-tag-badge">#calle</button>
            <button type="button" onclick="window.askEstenopoTag('#paisaje', event)" class="estenopo-tag-badge">#paisaje</button>
            <button type="button" onclick="window.askEstenopoTag('#analógico', event)" class="estenopo-tag-badge">#analógico</button>
            <button type="button" onclick="window.askEstenopoTag('#intimidad', event)" class="estenopo-tag-badge">#intimidad</button>
            <button type="button" onclick="window.askEstenopoTag('#documental', event)" class="estenopo-tag-badge">#documental</button>
            <button type="button" onclick="window.askEstenopoTag('#nocturna', event)" class="estenopo-tag-badge">#nocturna</button>
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

  const TAXONOMY_PATTERNS = {
    '#calle': /\b(?:street|calle|calles|peaton(?:es)?|transeunte(?:s)?|candid|flaneur)\b/i,
    '#retrato': /\b(?:portrait(?:s)?|retrato(?:s)?|face(?:s)?|rostro(?:s)?|mirada(?:s)?|autorretrato)\b/i,
    '#cuerpo': /\b(?:body|bodies|cuerpo(?:s)?|nude|desnudo(?:s)?|skin|piel|figura)\b/i,
    '#paisaje': /\b(?:landscape(?:s)?|paisaje(?:s)?|horizon(?:te)?|mountain(?:s)?|montaña(?:s)?|territorio|valle|campo(?:s)?)\b/i,
    '#marina': /\b(?:ocean|sea|mar|surf|surfing|beach|playa|coast|costa|olas|waves|litoral|submarina)\b/i,
    '#naturaleza': /\b(?:nature|naturaleza|forest|bosque|trees|árboles|arboles|flora|plantas?|garden|jardín)\b/i,
    '#fauna': /\b(?:wildlife|fauna|animal(?:s|es)?|birds?|aves?|pájaro(?:s)?|insects?|insectos?)\b/i,
    '#arquitectura': /\b(?:architecture|arquitectura|building(?:s)?|edificio(?:s)?|brutalismo|fachada|facade)\b/i,
    '#espacio-urbano': /\b(?:city|ciudad|urban|urbano|metropolis|metrópoli|barrio|tokyo|asfalto)\b/i,
    '#viaje': /\b(?:journey|travel|viaje|viajar|road\s+trip|train|tren|estación|station|tránsito|transit|carretera)\b/i,
    '#intimidad': /\b(?:intimacy|intimidad|domestic|doméstico|home|hogar|casa|habitación|quietud|vida\s+cotidiana)\b/i,
    '#memoria': /\b(?:memory|memoria|grief|duelo|loss|pérdida|nostalgia|recuerdo(?:s)?|pasado|soledad|solitario(?:s)?|silencio)\b/i,
    '#identidad': /\b(?:identity|identidad|gender|género|queer|trans|lgbtq|raíces)\b/i,
    '#comunidad': /\b(?:community|comunidad|colectivo|vecindario|indígena|tradición)\b/i,
    '#sociedad': /\b(?:society|sociedad|social|protest|protesta|activismo|política|derechos)\b/i,
    '#nocturna': /\b(?:night|nocturn(?:a|o)|darkness|oscuridad|neon|neón|sombras?|shadows?|crepúsculo|atardecer)\b/i,
    '#color': /\b(?:color|colour|cromatismo|paleta|saturación|kodachrome|lomochrome)\b/i,
    '#blanco-y-negro': /\b(?:black\s+and\s+white|b&w|blanco\s+y\s+negro|monochrome|monocromo|bw)\b/i,
    '#claroscuro': /\b(?:chiaroscuro|claroscuro|contraste|silueta(?:s)?|luz\s+y\s+sombra)\b/i,
    '#minimalismo': /\b(?:minimalis(?:m|ta)|espacio\s+negativo|geometría|líneas)\b/i,
    '#experimental': /\b(?:experimental|abstracción|abstract|desenfoque|doble\s+exposición|pinhole)\b/i,
    '#analógico': /\b(?:analogue|analog|film|película|pelicula|darkroom|grano|química|lomography|35mm)\b/i,
    '#35mm': /\b(?:35mm|135\s+film|point\s+and\s+shoot|telemétrica)\b/i,
    '#formato-medio': /\b(?:120\s+film|medium\s+format|formato\s+medio|6x6|6x7|hasselblad|mamiya)\b/i,
    '#cámaras-y-equipo': /\b(?:camera\s+review|lens|cámara|nikon|canon|leica|olympus|fujifilm)\b/i,
    '#fotolibro': /\b(?:photobook|fotolibro|monografía|fanzine|zine|publicación)\b/i,
    '#documental': /\b(?:documentar(?:y|io)|reportage|reportaje|ensayo|crónica|testimonio)\b/i,
    '#entrevista': /\b(?:interview|entrevista|conversación|charla|diálogo)\b/i,
    '#exposición': /\b(?:exhibition|exposición|gallery|galería|museo|retrospectiva)\b/i,
    '#fotografía-histórica': /\b(?:vintage|historical|siglo\s+xix|siglo\s+xx|archivo|maestro(?:s)?|clásico)\b/i
  };

  function inferQueryTags(q) {
    if (!q) return [];
    const queryStr = String(q);
    const explicit = (queryStr.match(/#[a-záéíóúñ0-9-]+/gi) || []).map(t => t.toLowerCase());
    const inferred = new Set(explicit);
    for (const [tag, pat] of Object.entries(TAXONOMY_PATTERNS)) {
      if (pat.test(queryStr)) {
        inferred.add(tag.toLowerCase());
      }
    }
    return Array.from(inferred);
  }

  // Motor de Búsqueda Semántica y Conceptual (sqlite-vec + Gemini Embeddings con fallback)
  async function queryArchiveSemantic(query, mode = 'general') {
    // Asegurar que los datos del archivo estén listos antes de buscar
    if (!archiveData && (!window.__allEntries || window.__allEntries.length === 0)) {
      await preloadArchive();
    }

    // 1. Intentar consultar el motor vectorial real en el backend (/api/search)
    try {
      const resp = await fetch(`/api/search?q=${encodeURIComponent(query)}&mode=hybrid&limit=8`);
      if (resp.ok) {
        const data = await resp.json();
        if (data && data.status === 'ok' && Array.isArray(data.items) && data.items.length > 0) {
          const articles = data.items.map(item => ({
            id: item.id || item.link || item.url,
            title: item.title || '',
            photographer: item.photographer || '',
            source: item.source || item._source || '',
            url: item.url || item.link || '#',
            published_date: item.published_date || item.date || '',
            summary: item.summary || item.excerpt || '',
            image: item.image_url || item.thumbnail || item.image || '',
            score: item.score || 10,
            tags: Array.isArray(item.tags) ? item.tags : [],
            rank_type: 'Vectorial (sqlite-vec + Gemini)'
          }));

          let podcasts = [];
          try {
            const podResp = await fetch(`/api/search?q=${encodeURIComponent(query)}&mode=podcast&limit=3`);
            if (podResp.ok) {
              const podData = await podResp.json();
              if (podData && podData.status === 'ok' && Array.isArray(podData.items)) {
                podcasts = podData.items.map(p => ({
                  id: p.id || p.link,
                  title: p.title || '',
                  date: p.date || '',
                  description: p.description || '',
                  duration: p.duration || 0,
                  audio_url: p.audio_url || p.link || ''
                }));
              }
            }
          } catch {}

          return {
            articles,
            podcasts,
            queryTags: inferQueryTags(query),
            mode: 'vectorial_real'
          };
        }
      }
    } catch {}

    // 2. Motor de Intersección Taxonómica Curatorial y Resonancias
    const dataset = (window.__allEntries && window.__allEntries.length > 0) 
      ? window.__allEntries 
      : (archiveData?.articles || []);

    const queryTags = inferQueryTags(query);

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
      const cleanT = t.replace(/^#/, '');
      for (const [key, synonyms] of Object.entries(CONCEPT_MAP)) {
        if (cleanT === key || key === cleanT + 's' || cleanT === key + 's') {
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

      // 1. Intersección de Etiquetas: Coincidencias exactas (Nivel 3, 2 o 1)
      const matchingTags = aTags.filter(t => queryTags.includes(t.toLowerCase()));
      const tagCoincidences = matchingTags.length;

      // Base jerárquica: Tier 3 (300 pts), Tier 2 (200 pts), Tier 1 (100 pts)
      let score = tagCoincidences * 100;

      const rawTitle = decodeHtmlEntities(a.title || '');
      const rawPhoto = decodeHtmlEntities(a.photographer || '');
      const rawSummary = decodeHtmlEntities(a.summary || a.excerpt || a.content || '');
      const rawSrc = decodeHtmlEntities(a._source || a.source || '');

      rawTerms.forEach(t => {
        const cleanT = t.replace(/^#/, '');
        if (matchWordInText(rawPhoto, t)) score += 35;
        if (matchWordInText(rawTitle, t)) score += 25;
        if (matchWordInText(rawSummary, t)) score += 8;
        if (matchWordInText(rawSrc, t)) score += 5;
      });

      termsArray.forEach(t => {
        if (matchWordInText(rawPhoto, t)) score += 15;
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
        matchingTags,
        tagCoincidences,
        score,
        rank_type: tagCoincidences > 0 ? `Afinidad (${tagCoincidences} coincidencia${tagCoincidences > 1 ? 's' : ''})` : 'Semántica Heurística'
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
      queryTags,
      mode: 'tag_hierarchical'
    };
  }

  function generateAssistantResponse(query, results, mode = 'general') {
    const qLower = String(query || '').toLowerCase();
    const { articles = [], podcasts = [], queryTags = [] } = results || {};
    const articlesList = Array.isArray(articles) ? articles : [];
    const podcastsList = Array.isArray(podcasts) ? podcasts : [];
    const queryTagsList = Array.isArray(queryTags) ? queryTags : [];

    // 1. Caso especial: Disparador Creativo Contextualizado
    if (mode === 'spark' || qLower.includes('disparador') || qLower.includes('ejercicio') || qLower.includes('propuesta') || qLower.includes('reto')) {
      const allEnts = (window.__allEntries && window.__allEntries.length > 0) ? window.__allEntries : (archiveData?.articles || []);
      const topArt = articlesList[0] || (allEnts.length > 0 ? allEnts[Math.floor(Math.random() * allEnts.length)] : null);
      const title = topArt ? (topArt.title || 'Geometría y Sombra en lo Cotidiano') : 'Geometría y Sombra en lo Cotidiano';
      const articleId = topArt ? escapeHtml(String(topArt.id || topArt._id || topArt.url || topArt.link || '')) : '';
      const sourceSafe = topArt ? escapeHtml(String(topArt.source || topArt._source || '')) : '';
      const sourceName = topArt ? escapeHtml(String(topArt.source || topArt._source || 'ARCHIVO').toUpperCase()) : 'ARCHIVO';
      const url = topArt?.url || topArt?.link || '#';
      const photo = topArt?.photographer ? escapeHtml(topArt.photographer) : '';
      const topTags = Array.isArray(topArt?.tags) ? topArt.tags : [];
      const topTagsHtml = topTags.length > 0
        ? `<div class="estenopo-tags-row">${topTags.map(t => {
            const tagStr = String(t || '');
            const isMatched = queryTagsList.includes(tagStr.toLowerCase());
            return `<button type="button" class="estenopo-tag-badge ${isMatched ? 'matched' : ''}" onclick="window.askEstenopoTag('${escapeHtml(tagStr)}', event)">${escapeHtml(tagStr)}</button>`;
          }).join('')}</div>`
        : '';

      const tLow = (title + ' ' + (topArt?.summary || '')).toLowerCase();
      let retoTitulo = 'El Espacio que No Ocupamos';
      let retoTexto = 'Encuentra un rincón cotidiano donde la luz incida oblicua. Encuadra dejando que la sombra o el espacio negativo ocupe más del 70% del encuadre. Dispara en manual para forzar el misterio.';

      if (qLower.includes('tren') || qLower.includes('viaj') || tLow.includes('train') || tLow.includes('journey')) {
        retoTitulo = 'La Ventanilla: Umbral entre Intimidad y Velocidad (Tren & Tránsito)';
        retoTexto = `
          <strong>1. Doble Exposición en el Cristal:</strong> Enfoca en manual a la superficie de la ventanilla. Superpón el reflejo del interior (la mirada o las manos de un pasajero) con el paisaje exterior que corre a gran velocidad.<br><br>
          <strong>2. Contraste Cinético:</strong> Apoya la cámara firme en el reposabrazos o tu rodilla y dispara a <strong>1/15s – 1/30s</strong>: el interior del vagón quedará nítido mientras el exterior se convertirá en un barrido de líneas cinéticas abstractas.<br><br>
          <strong>3. El No-Lugar:</strong> En las paradas intermedias, captura el instante fugaz en que alguien espera en el andén o se despide a través del cristal.
        `;
      } else if (qLower.includes('lluvia') || qLower.includes('niebla') || tLow.includes('rain') || tLow.includes('fog')) {
        retoTitulo = 'Atmósferas Difusas y Superficies Húmedas';
        retoTexto = 'Aprovecha las gotas en cristales o los reflejos en el asfalto mojado. Dispara a máxima apertura (f/1.8 – f/2.8) enfocando en una sola gota para convertir las luces de fondo en bokeh de color cinematográfico.';
      } else if (qLower.includes('noche') || qLower.includes('nocturn') || tLow.includes('night') || tLow.includes('shadow')) {
        retoTitulo = 'Claroscuro y Luces Aisladas';
        retoTexto = 'Encuentra una única fuente de luz artificial (farola, escaparate o neón). Mide la exposición en las altas luces y deja que las sombras caigan en negro profundo para forzar la intriga psicológica.';
      } else if (tLow.includes('street') || tLow.includes('calle') || tLow.includes('urban') || tLow.includes('city') || qLower.includes('calle')) {
        retoTitulo = 'La Coincidencia Involuntaria (Street Photography)';
        retoTexto = 'Sal a una calle transitada, busca un fondo con fuerte contraste geométrico o color plano y espera inmóvil a que un transeúnte complete la composición con su postura, sombra o vestimenta. Prioriza el instante decisivo.';
      } else if (tLow.includes('portrait') || tLow.includes('retrato') || tLow.includes('body') || tLow.includes('cuerpo') || qLower.includes('retrato')) {
        retoTitulo = 'Retrato sin Mirada';
        retoTexto = 'Fotografía a una persona cercana sin mostrar directamente sus ojos: concéntrate en la tensión de las manos, el gesto de la espalda o la silueta contra una ventana en penumbra.';
      } else if (tLow.includes('sea') || tLow.includes('water') || tLow.includes('mar') || tLow.includes('ocean') || tLow.includes('landscape') || tLow.includes('nature') || qLower.includes('mar') || qLower.includes('agua') || qLower.includes('campo') || qLower.includes('arbol')) {
        retoTitulo = 'Textura del Paisaje y Soledad Territorial';
        retoTexto = 'Busca la tensión entre un horizonte amplio y un elemento solitario (un árbol, una piedra, una casa rural aislada). Dispara con diafragma medio (f/5.6 – f/8) para preservar el grano y la textura del terreno.';
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
            <a href="javascript:void(0)" onclick="window.openArticleAndCloseEstenopo('${articleId}', '${sourceSafe}')" class="estenopo-link-title" title="Abrir en Lector">
              ${escapeHtml(title)}
            </a>
            ${topTagsHtml}
            <div class="estenopo-link-actions">
              <button class="estenopo-mini-btn view" onclick="window.openArticleAndCloseEstenopo('${articleId}', '${sourceSafe}')" title="Abrir en Lector">
                Abrir en Lector
              </button>
              ${url !== '#' ? `<a href="${url}" target="_blank" rel="noopener noreferrer" class="estenopo-mini-btn" title="Ir a fuente original">Original ↗</a>` : ''}
            </div>
          </div>

          <div style="background:rgba(255,68,68,0.06);border-left:3px solid #ff4444;padding:0.75rem;margin:0.75rem 0;border-radius:4px;color:#f8fafc;font-size:0.88rem;line-height:1.5;">
            <strong>Tu ejercicio:</strong><br>${retoTexto}
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
    if (!articlesList.length && !podcastsList.length) {
      return `
        <div class="gemini-response-box">
          <p style="color:#e2e8f0;font-size:0.9rem;line-height:1.5;">
            No encontré obras que coincidan directamente con <em>«${escapeHtml(query)}»</em>.
          </p>
          <p style="margin:0.5rem 0 0.8rem;font-size:0.85rem;color:#cbd5e1;">
            ¿Hacia dónde te gustaría <strong>enfocar</strong> la mirada? Elige una de estas opciones:
          </p>
          ${getIntroWelcomeHtml()}
        </div>
      `;
    }

    // Análisis curatorial del tono y temas detectados
    let tesisCuratorial = '';
    if (queryTagsList.includes('#paisaje') || queryTagsList.includes('#naturaleza')) {
      tesisCuratorial = 'Las obras recuperadas abordan la tensión entre el territorio, la escala humana y el silencio del horizonte.';
    } else if (queryTagsList.includes('#calle') || queryTagsList.includes('#espacio-urbano')) {
      tesisCuratorial = 'Una exploración del pulso callejero, la arquitectura cotidiana y los instantes fortuitos de la ciudad.';
    } else if (queryTagsList.includes('#retrato') || queryTagsList.includes('#cuerpo') || queryTagsList.includes('#intimidad')) {
      tesisCuratorial = 'Enfoque centrado en la mirada íntima, la vulnerabilidad del cuerpo y la memoria de los espacios habitados.';
    } else if (queryTagsList.includes('#nocturna') || queryTagsList.includes('#claroscuro')) {
      tesisCuratorial = 'Investigación sobre la luz artificial, las penumbras densas y la intriga psicológica de la noche.';
    } else if (queryTagsList.includes('#analógico') || queryTagsList.includes('#35mm')) {
      tesisCuratorial = 'Resonancias que celebran la materialidad del grano, la química de la emulsión y la textura del celuloide.';
    } else {
      tesisCuratorial = 'Diálogo visual entre distintas publicaciones y autores del archivo que exploran esta misma búsqueda formal.';
    }

    let out = `
      <div class="gemini-response-box">
        <div style="margin-bottom:0.75rem;">
          <p style="color:#e2e8f0;font-size:0.92rem;line-height:1.5;margin-bottom:0.35rem;">
            <strong>Estenopo:</strong> ${tesisCuratorial}
          </p>
          ${queryTagsList.length > 0 ? `
            <div style="font-size:0.75rem;color:#94a3b8;display:flex;align-items:center;gap:0.35rem;flex-wrap:wrap;">
              <span>Afinidades detectadas:</span>
              ${queryTagsList.map(t => `<span class="estenopo-tag-badge matched" style="font-size:0.62rem;">${escapeHtml(t)}</span>`).join('')}
            </div>
          ` : ''}
        </div>
    `;

    // Linaje si hay múltiples artículos
    if (articlesList.length >= 2) {
      const a1 = articlesList[0];
      const a2 = articlesList[1];
      const id1 = escapeHtml(String(a1.id || a1.url));
      const src1 = escapeHtml(String(a1.source || ''));
      const id2 = escapeHtml(String(a2.id || a2.url));
      const src2 = escapeHtml(String(a2.source || ''));

      // Etiquetas comunes entre los dos artículos
      const a1Tags = Array.isArray(a1.tags) ? a1.tags : [];
      const a2Tags = Array.isArray(a2.tags) ? a2.tags : [];
      const commonLinajeTags = a1Tags.filter(t => a2Tags.includes(t));
      const tagDesc = commonLinajeTags.length > 0
        ? `a través de ${commonLinajeTags.join(' y ')}`
        : 'por afinidad estética y conceptual';

      out += `
        <div class="gemini-lineage-banner">
          <div class="gemini-lineage-title">Genealogía & Linaje Visual</div>
          <div class="gemini-lineage-desc">
            Diálogo estético entre <a href="javascript:void(0)" onclick="window.openArticleAndCloseEstenopo('${id1}', '${src1}')" style="color:#ff8a65;text-decoration:underline;">«${escapeHtml(a1.title)}»</a> (${src1.toUpperCase()}) y <a href="javascript:void(0)" onclick="window.openArticleAndCloseEstenopo('${id2}', '${src2}')" style="color:#ff8a65;text-decoration:underline;">«${escapeHtml(a2.title)}»</a> (${src2.toUpperCase()}) ${tagDesc}.
          </div>
        </div>
      `;
    }

    // Lista de Enlaces Sombreados para Artículos con Etiquetas
    if (articlesList.length > 0) {
      out += `
        <div class="gemini-section-header">
          <span>Obras & Ensayos Seleccionados</span>
        </div>
        <div class="estenopo-links-list">
      `;

      articlesList.forEach(a => {
        const photo = a.photographer ? escapeHtml(a.photographer) : '';
        const sourceName = escapeHtml((a.source || 'ARCHIVO').toUpperCase());
        const articleId = escapeHtml(String(a.id || a.url));
        const sourceSafe = escapeHtml(String(a.source || ''));
        const tagsList = Array.isArray(a.tags) ? a.tags : [];
        const tagsHtml = tagsList.length > 0
          ? `<div class="estenopo-tags-row">${tagsList.map(t => {
              const tagStr = String(t || '');
              const isMatched = queryTagsList.includes(tagStr.toLowerCase());
              return `<button type="button" class="estenopo-tag-badge ${isMatched ? 'matched' : ''}" onclick="window.askEstenopoTag('${escapeHtml(tagStr)}', event)">${escapeHtml(tagStr)}</button>`;
            }).join('')}</div>`
          : '';

        out += `
          <div class="estenopo-link-item">
            <div class="estenopo-link-meta">
              <span>${sourceName}</span>
              ${photo ? `<span class="estenopo-link-author">· ${photo}</span>` : ''}
              ${a.tagCoincidences ? `<span style="color:#10b981;font-weight:600;margin-left:auto;">${a.tagCoincidences}/3 coincidencias</span>` : ''}
            </div>
            <a href="javascript:void(0)" onclick="window.openArticleAndCloseEstenopo('${articleId}', '${sourceSafe}')" class="estenopo-link-title" title="Abrir en Lector">
              ${escapeHtml(a.title)}
            </a>
            ${tagsHtml}
            <div class="estenopo-link-actions">
              <button class="estenopo-mini-btn view" onclick="window.openArticleAndCloseEstenopo('${articleId}', '${sourceSafe}')" title="Abrir artículo completo en lector">
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

    // Botones de Ramificación Dinámica (Follow-up Sparks)
    const cleanEscapedQuery = escapeHtml(query);
    out += `
      <div style="margin-top:1.1rem;padding-top:0.75rem;border-top:1px solid rgba(255,255,255,0.07);">
        <div style="font-size:0.72rem;text-transform:uppercase;letter-spacing:0.06em;color:#94a3b8;margin-bottom:0.4rem;font-weight:600;">
          Continuar explorando con Estenopo:
        </div>
        <div style="display:flex;flex-wrap:wrap;gap:0.4rem;">
          <button type="button" class="gemini-chip" onclick="window.askEstenopoCard('spark', 'Disparador creativo: ${cleanEscapedQuery}', event)">
            ✨ Pedir reto para fotografiar esto
          </button>
          <button type="button" class="gemini-chip" onclick="window.askEstenopoCard('lineage', 'Linaje visual de ${cleanEscapedQuery}', event)">
            🔗 Cruzar con otros fotógrafos
          </button>
          <button type="button" class="gemini-chip" onclick="window.askEstenopoTag('#analógico', event)">
            🎞️ Filtrar en analógico
          </button>
        </div>
      </div>
    `;

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

  window.openArticleAndCloseEstenopo = function(id, source) {
    if (typeof window.openArticleModalById === 'function') {
      window.openArticleModalById(id, source);
    }
    if (isOpen) {
      toggleChat();
    }
  };

  window.askEstenopoCard = function(mode, defaultText, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const input = document.getElementById('chat-input');
    const userTyped = (input?.value || '').trim();

    let displayQuery = '';
    let internalQuery = '';

    if (userTyped) {
      displayQuery = userTyped;
      if (mode === 'atmosphere') {
        internalQuery = `${userTyped} luz sombras atmósfera atardecer`;
      } else if (mode === 'lineage') {
        internalQuery = `${userTyped} linaje diálogo influencia`;
      } else if (mode === 'spark') {
        internalQuery = `${userTyped} disparador reto creativo`;
      } else {
        internalQuery = userTyped;
      }
    } else {
      displayQuery = defaultText;
      internalQuery = defaultText;
    }

    executeEstenopoSearch(displayQuery, internalQuery, mode);
  };

  window.askEstenopoTag = function(tag, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const input = document.getElementById('chat-input');
    const userTyped = (input?.value || '').trim();

    let displayQuery = tag;
    let internalQuery = tag;

    if (userTyped && !userTyped.includes(tag)) {
      displayQuery = `${userTyped} ${tag}`;
      internalQuery = `${userTyped} ${tag}`;
    }

    executeEstenopoSearch(displayQuery, internalQuery, 'tag');
  };

  window.askEstenopoQuery = function(query, e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    executeEstenopoSearch(query, query, 'general');
  };

  async function handleUserSubmit(e) {
    e.preventDefault();
    const input = document.getElementById('chat-input');
    const q = (input?.value || '').trim();
    executeEstenopoSearch(q, q, 'general');
  }

  async function executeEstenopoSearch(displayQuery, internalQuery, mode = 'general') {
    const cleanDisplay = (displayQuery || '').trim();
    const cleanInternal = (internalQuery || cleanDisplay).trim();
    if (!cleanDisplay) {
      addMessage('bot', `
        <div class="gemini-response-box">
          <p style="color:#e2e8f0;font-size:0.9rem;margin-bottom:0.6rem;">
            ¿Hacia dónde te gustaría <strong>enfocar</strong> tu búsqueda? Pulsa en una opción o escribe una sensación o autor:
          </p>
          ${getIntroWelcomeHtml()}
        </div>
      `);
      return;
    }

    const input = document.getElementById('chat-input');
    if (input) input.value = '';

    addMessage('user', `<p>${escapeHtml(cleanDisplay)}</p>`);

    const loading = addMessage('bot', `
      <div class="gemini-typing-indicator">
        <span class="sparkle-spin">📷</span> Estenopo está consultando el archivo…
      </div>
    `);

    try {
      const results = await queryArchiveSemantic(cleanInternal, mode);
      loading.remove();
      const responseHtml = generateAssistantResponse(cleanDisplay, results, mode);
      addMessage('bot', responseHtml);
    } catch (err) {
      console.error('Error al procesar consulta en Estenopo:', err);
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
    try {
      const escaped = String(term).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
      const regex = new RegExp(`(^|[^\\p{L}\\p{N}])${escaped}($|[^\\p{L}\\p{N}])`, 'iu');
      return regex.test(String(text));
    } catch (e) {
      return String(text).toLowerCase().includes(String(term).toLowerCase());
    }
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

