// Noun illustrations added for the 200 everyday noun cards
// Force refresh for corrected noun illustrations: Verspätung, Anschluss, Haltestelle, Fahrkartenautomat
'use strict';
// Refresh cached app shell and PWA manifest for the WortFlip name change.
const CACHE_NAME = 'wortspiel-pwa-v18-lookalikes-500';;
const CACHE_PREFIX = 'wortspiel-pwa-';
const ASSETS = [
  './', './index.html', './manifest.webmanifest', './audio/tracks.json',
  './icon-192.png', './icon-512.png',
  './icon-maskable-512.png', './apple-touch-icon.png',
  './images/l272.webp'
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
