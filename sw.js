'use strict';
// Bump this version whenever you release a new website to refresh the offline cache.
const CACHE_NAME = 'wortspiel-pwa-v2';
const CACHE_PREFIX = 'wortspiel-pwa-';
const ASSETS = [
  './', './index.html', './manifest.webmanifest', './audio/tracks.json',
  './icon-192.png', './icon-512.png',
  './icon-maskable-512.png', './apple-touch-icon.png'
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

self.addEventListener('fetch', event => {
  const request = event.request;
  if (request.method !== 'GET') return;
  const url = new URL(request.url);
  if (url.origin !== APP_ROOT.origin || !url.pathname.startsWith(APP_ROOT.pathname)) return;

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
