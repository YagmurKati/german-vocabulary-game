'use strict';
// Refresh cached app shell and PWA manifest for the WortFlip name change.
const CACHE_NAME = 'wortspiel-pwa-v5-illustrations-phase3';
const CACHE_PREFIX = 'wortspiel-pwa-';
const ASSETS = [
  './', './index.html', './manifest.webmanifest', './audio/tracks.json',
  './icon-192.png', './icon-512.png',
  './icon-maskable-512.png', './apple-touch-icon.png',
  './images/e000.webp',   './images/e001.webp',   './images/e002.webp',   './images/e004.webp',
  './images/e006.webp',   './images/e008.webp',   './images/e009.webp',   './images/e012.webp',
  './images/e013.webp',   './images/e016.webp',   './images/e017.webp',   './images/e020.webp',
  './images/e021.webp',   './images/e024.webp',   './images/e025.webp',   './images/e029.webp',
  './images/e030.webp',   './images/e031.webp',   './images/e038.webp',   './images/e040.webp',
  './images/e041.webp',   './images/e042.webp',   './images/e046.webp',   './images/e047.webp',
  './images/e048.webp',   './images/e049.webp',   './images/e050.webp',   './images/e055.webp',
  './images/e070.webp',   './images/e079.webp',   './images/e082.webp',   './images/e086.webp',
  './images/e087.webp',   './images/e094.webp',   './images/e116.webp',   './images/e120.webp',
  './images/e123.webp',   './images/e128.webp',   './images/e131.webp',   './images/e137.webp',
  './images/e147.webp',   './images/e148.webp',   './images/e155.webp',   './images/e210.webp',
  './images/e211.webp',   './images/e226.webp',   './images/e232.webp',   './images/e236.webp',
  './images/e240.webp',   './images/e244.webp',   './images/e257.webp',   './images/e264.webp',
  './images/e275.webp',   './images/e282.webp',   './images/e287.webp',   './images/e363.webp',
  './images/e364.webp',   './images/e365.webp',   './images/e367.webp',   './images/e368.webp',
  './images/e369.webp',   './images/e377.webp',   './images/e383.webp',   './images/e387.webp',
  './images/e391.webp',   './images/l000.webp',   './images/l002.webp',   './images/l006.webp',
  './images/l007.webp',   './images/l015.webp',   './images/l017.webp',   './images/l023.webp',
  './images/l031.webp',   './images/l035.webp',   './images/l040.webp',   './images/l046.webp',
  './images/l058.webp',   './images/l059.webp',   './images/l062.webp',   './images/l088.webp',
  './images/l099.webp',   './images/l101.webp',   './images/l129.webp',   './images/l266.webp',
  './images/l271.webp',   './images/l272.webp'
];
const APP_ROOT = new URL('./', self.registration.scope);

self.addEventListener('install', event => {
  event.waitUntil((async () => {
    const cache = await caches.open(CACHE_NAME);
    await cache.addAll(ASSETS.map(path => new URL(path, APP_ROOT).href));
    await self.skipWaiting();
  })());
});

self.addEventListener('activate', event => {
  event.waitUntil((async () => {
    const names = await caches.keys();
    await Promise.all(names.filter(name => name.startsWith(CACHE_PREFIX) && name !== CACHE_NAME).map(name => caches.delete(name)));
    await self.clients.claim();
  })());
});

// Chrome on Android often uses Range requests for MP3, including for local cached audio.
// A normal 200-response from CacheStorage must be converted to a valid 206 response.
async function serveAudio(request) {
  const range = request.headers.get('range');
  const fullUrl = request.url;
  const cached = await caches.match(fullUrl);
  if (cached && cached.ok && cached.status === 200) {
    if (!range) return cached;
    const match = /^bytes=(\d+)-(\d*)$/i.exec(range);
    if (match) {
      const bytes = await cached.arrayBuffer();
      const total = bytes.byteLength;
      const start = Number(match[1]);
      const end = match[2] ? Math.min(Number(match[2]), total - 1) : total - 1;
      if (start >= total || end < start) {
        return new Response(null, {status: 416, headers: {'Content-Range': `bytes */${total}`}});
      }
      const headers = new Headers({
        'Content-Type': cached.headers.get('Content-Type') || 'audio/mpeg',
        'Accept-Ranges': 'bytes',
        'Content-Range': `bytes ${start}-${end}/${total}`,
        'Content-Length': String(end - start + 1)
      });
      return new Response(bytes.slice(start, end + 1), {status: 206, headers});
    }
  }
  try {
    const response = await fetch(request);
    // Save only complete files; partial 206 responses must not poison the cache.
    if (response.ok && response.status === 200 && !range && response.type === 'basic') {
      const cache = await caches.open(CACHE_NAME);
      await cache.put(fullUrl, response.clone());
    }
    return response;
  } catch (_) {
    return cached || Response.error();
  }
}

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== APP_ROOT.origin || !url.pathname.startsWith(APP_ROOT.pathname)) return;

  if (/\.mp3$/i.test(url.pathname)) {
    event.respondWith(serveAudio(request));
    return;
  }

  // The audio track manifest changes after the workflow publishes 400 new tracks.
  // Fetch it online first; offline, fall back to the saved copy.
  if (url.pathname.endsWith('/audio/tracks.json')) {
    event.respondWith((async () => {
      const cache = await caches.open(CACHE_NAME);
      try {
        const response = await fetch(request);
        if (response.ok) {
          await cache.put(request, response.clone());
          return response;
        }
      } catch (_) { /* Offline: use cached manifest */ }
      return (await cache.match(request)) || Response.error();
    })());
    return;
  }

  if (request.mode === 'navigate') {
    event.respondWith((async () => {
      try {
        const response = await fetch(request);
        if (response.ok && response.type === 'basic') {
          const cache = await caches.open(CACHE_NAME);
          await cache.put(new URL('./index.html', APP_ROOT).href, response.clone());
          return response;
        }
      } catch (_) { /* No network: use offline app shell */ }
      const cache = await caches.open(CACHE_NAME);
      return (await cache.match(new URL('./index.html', APP_ROOT).href)) || Response.error();
    })());
    return;
  }
  event.respondWith((async () => {
    const cached = await caches.match(request);
    if (cached) return cached;
    try {
      const response = await fetch(request);
      if (response.ok && response.type === 'basic') {
        const cache = await caches.open(CACHE_NAME);
        await cache.put(request, response.clone());
      }
      return response;
    } catch (_) {
      return Response.error();
    }
  })());
});
