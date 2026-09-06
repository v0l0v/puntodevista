import { DEFAULT_SOURCES, DEFAULT_SOURCE_LABELS, PAGE_SIZE } from './constants.js';

export const state = {
  allSources: [...DEFAULT_SOURCES],
  sourceLabels: { ...DEFAULT_SOURCE_LABELS },
  allChecked: true,
  sources: new Set(),
  searchQuery: '',
  visibleLimit: PAGE_SIZE,
  currentFilteredEntries: [],
  scrollObserver: null,
  dateFilter: { period: 'month', value: null },
  rawEntries: [],
  allEntries: [],
  podcastEntries: [],
  activePodcastEntry: null,
  sharedAudio: null,
  sourceJsonCache: {},
  clickLast: -1,
  galleryImages: [],
  galleryIndex: 0
};

// Vinculación bidireccional con window para máxima compatibilidad
window.__allSources = state.allSources;
window.__sourceLabels = state.sourceLabels;
window.__sources = state.sources;
window.__dateFilter = state.dateFilter;
window.__sourceJsonCache = state.sourceJsonCache;

Object.defineProperty(window, '__allChecked', {
  get: () => state.allChecked,
  set: (val) => { state.allChecked = val; },
  configurable: true
});

Object.defineProperty(window, '__searchQuery', {
  get: () => state.searchQuery,
  set: (val) => { state.searchQuery = val; },
  configurable: true
});

Object.defineProperty(window, '__visibleLimit', {
  get: () => state.visibleLimit,
  set: (val) => { state.visibleLimit = val; },
  configurable: true
});

Object.defineProperty(window, '__currentFilteredEntries', {
  get: () => state.currentFilteredEntries,
  set: (val) => { state.currentFilteredEntries = val; },
  configurable: true
});

Object.defineProperty(window, '__scrollObserver', {
  get: () => state.scrollObserver,
  set: (val) => { state.scrollObserver = val; },
  configurable: true
});

Object.defineProperty(window, '__allEntries', {
  get: () => state.allEntries,
  set: (val) => { state.allEntries = val; },
  configurable: true
});

Object.defineProperty(window, '__rawEntries', {
  get: () => state.rawEntries,
  set: (val) => { state.rawEntries = val; },
  configurable: true
});

Object.defineProperty(window, '__podcastEntries', {
  get: () => state.podcastEntries,
  set: (val) => { state.podcastEntries = val; },
  configurable: true
});

Object.defineProperty(window, '__activePodcastEntry', {
  get: () => state.activePodcastEntry,
  set: (val) => { state.activePodcastEntry = val; },
  configurable: true
});

Object.defineProperty(window, '__galleryImages', {
  get: () => state.galleryImages,
  set: (val) => { state.galleryImages = val; },
  configurable: true
});

Object.defineProperty(window, '__galleryIndex', {
  get: () => state.galleryIndex,
  set: (val) => { state.galleryIndex = val; },
  configurable: true
});
