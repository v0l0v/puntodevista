export const WP_API = 'https://www.thisiscolossal.com/wp-json/wp/v2/posts?categories=496&per_page=20';
export const POST_API = 'https://www.thisiscolossal.com/wp-json/wp/v2/posts';

export const BOOM_FEEDS = ['https://www.booooooom.com/blog/photo/feed/'];
export const TPJ_FEEDS = [
  'https://thephotographicjournal.com/essays/rss',
  'https://thephotographicjournal.com/interviews/feed',
  'https://thephotographicjournal.com/features/feed',
];
export const HUCK_FEEDS = ['https://www.huckmag.com/topic/photography/feed'];
export const LENSCULTURE_FEEDS = ['https://www.lensculture.com/feeds/feed.rss'];
export const ODLP_FEEDS = ['https://loeildelaphotographie.com/en/feed/'];

export const RSS_PROXIES = [
  u => 'https://api.allorigins.win/raw?url=' + encodeURIComponent(u),
  u => 'https://api.codetabs.com/v1/proxy?quest=' + encodeURIComponent(u),
];

export const REFRESH_MS = 10 * 60 * 1000;
export const PAGE_SIZE = 36;
export const MONTH_NAMES = ['ene','feb','mar','abr','may','jun','jul','ago','sep','oct','nov','dic'];
export const CLICK_OPEN = ['assets/mp3/click1.mp3', 'assets/mp3/click2.mp3', 'assets/mp3/click3.mp3', 'assets/mp3/click4.mp3'];

export const PODCAST_URL = 'podcast';
export const PODCAST_COVER = 'podcast-cover.jpg';
export const SOURCES_KEY = 'feedfoto.sources';
export const CACHED_ENTRIES_KEY = 'feedfoto.cached_entries';
export const READ_COUNTS_KEY = 'feedfoto.read_counts';

export const DEFAULT_SOURCES = [
  'colossal', 'lomography', 'booooooom', 'tpj', 'huck', 'lensculture', 'odlp', 'magnum', 'shootitwithfilm',
  '35mmc', 'kosmofoto', 'casualphotophile', 'phroom', 'c41', 'featureshoot', 'aintbad', 'emulsive',
  'aperture', 'blind', 'asx', '1854', 'clavoardiendo'
];

export const DEFAULT_SOURCE_LABELS = {
  colossal: 'Colossal · Fotografía',
  lomography: 'Lomography Magazine',
  booooooom: 'Booooooom',
  tpj: 'The Photographic Journal',
  huck: 'Huck Magazine',
  lensculture: 'LensCulture',
  odlp: "L'Œil de la Photographie",
  magnum: 'Magnum Photos',
  shootitwithfilm: 'Shoot It With Film',
  '35mmc': '35mmc',
  kosmofoto: 'Kosmo Foto',
  casualphotophile: 'Casual Photophile',
  phroom: 'Phroom Magazine',
  c41: 'C41 Magazine',
  featureshoot: 'Feature Shoot',
  aintbad: "Ain't-Bad",
  emulsive: 'EMULSIVE',
  aperture: 'Aperture',
  blind: 'Blind Magazine',
  asx: 'American Suburb X',
  '1854': 'British Journal of Photography',
  clavoardiendo: 'Clavoardiendo Magazine'
};

// Alias para compatibilidad con código que use ALL_SOURCES y SOURCE_LABELS
export const ALL_SOURCES = DEFAULT_SOURCES;
export const SOURCE_LABELS = DEFAULT_SOURCE_LABELS;

// Window bindings
window.ALL_SOURCES = ALL_SOURCES;
window.SOURCE_LABELS = SOURCE_LABELS;
window.REFRESH_MS = REFRESH_MS;
