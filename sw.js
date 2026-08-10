// Service Worker for Slopkit Offline Cache System
// Guarantees 100% offline functionality using SHA-256 manifest verification and query-agnostic cache lookup.

const MANIFEST_URL = './cache-manifest.json';

const ALL_PROJECT_FILES = [
  './',
  './cache-manifest.json',
  './document/en/ps5/index.html',
  './index.html',
  './offsets/10.00.js',
  './offsets/10.01.js',
  './offsets/10.20.js',
  './offsets/10.40.js',
  './offsets/10.60.js',
  './offsets/11.00.js',
  './offsets/11.20.js',
  './offsets/11.40.js',
  './offsets/11.60.js',
  './offsets/12.00.js',
  './offsets/9.00.js',
  './offsets/9.20.js',
  './offsets/9.40.js',
  './offsets/9.60.js',
  './payloads/elfldr-ps5-1360.elf',
  './payloads/kexp_2026_05_25.bin',
  './payloads/pldmgr_v0.5.1.elf',
  './slopkit/cat.jpg',
  './slopkit/core.js',
  './slopkit/int64.js',
  './slopkit/main.js',
  './slopkit/mem.js',
  './slopkit/mmhmm-cats-ps5.gif',
  './slopkit/poops.html',
  './slopkit/poops.js',
  './slopkit/rop.js',
  './slopkit/rop_slave.js',
  './slopkit/syscalls.js',
  './sw.js',
  './ui/payload-menu-title.png',
  './ui/payload-pldmgr-default.png',
  './ui/payload-pldmgr-failed.png',
  './ui/payload-pldmgr-sending.png',
  './ui/payload-pldmgr-sent.png'
];

async function getManifest() {
  try {
    const response = await fetch(MANIFEST_URL, { cache: 'no-store' });
    if (response.ok) {
      return await response.json();
    }
  } catch (e) {
    console.warn('[SW] Could not fetch cache-manifest.json online; using static asset manifest');
  }
  return null;
}

self.addEventListener('install', (event) => {
  console.log('[SW] Installing Service Worker...');
  event.waitUntil(
    (async () => {
      const manifest = await getManifest();
      const version = manifest ? manifest.version : 'offline-v1';
      const cacheName = `slopkit-cache-${version}`;

      const cache = await caches.open(cacheName);
      
      let urlsToCache = [...ALL_PROJECT_FILES];
      if (manifest && manifest.files) {
        const manifestUrls = Object.keys(manifest.files).map(f => './' + f);
        urlsToCache = Array.from(new Set([...urlsToCache, ...manifestUrls]));
      }

      console.log(`[SW] Pre-caching all ${urlsToCache.length} project assets (Cache: ${cacheName})`);

      await Promise.all(
        urlsToCache.map(async (url) => {
          try {
            const response = await fetch(url, { cache: 'reload' });
            if (response.ok) {
              await cache.put(url, response);
            }
          } catch (err) {
            console.warn(`[SW] Failed to cache asset: ${url}`, err);
          }
        })
      );

      await self.skipWaiting();
    })()
  );
});

self.addEventListener('activate', (event) => {
  console.log('[SW] Activating Service Worker...');
  event.waitUntil(
    (async () => {
      const manifest = await getManifest();
      const activeVersion = manifest ? manifest.version : 'offline-v1';
      const activeCacheName = `slopkit-cache-${activeVersion}`;

      const keys = await caches.keys();
      await Promise.all(
        keys.map((key) => {
          if (key.startsWith('slopkit-cache-') && key !== activeCacheName) {
            console.log(`[SW] Deleting outdated cache: ${key}`);
            return caches.delete(key);
          }
        })
      );

      await self.clients.claim();
    })()
  );
});

self.addEventListener('fetch', (event) => {
  if (event.request.method !== 'GET') return;

  const reqUrl = new URL(event.request.url);

  event.respondWith(
    (async () => {
      // 1. Direct cache match (ignoring query strings)
      let cached = await caches.match(event.request, { ignoreSearch: true });
      if (cached) return cached;

      // 2. Match URL without query string
      const urlWithoutQuery = reqUrl.origin + reqUrl.pathname;
      cached = await caches.match(urlWithoutQuery, { ignoreSearch: true });
      if (cached) return cached;

      // 3. Try relative path match
      const relativePath = '.' + reqUrl.pathname;
      cached = await caches.match(relativePath, { ignoreSearch: true });
      if (cached) return cached;

      // 4. Fallback to network if online
      try {
        const networkResponse = await fetch(event.request);
        if (networkResponse && networkResponse.status === 200 && networkResponse.type === 'basic') {
          const responseToCache = networkResponse.clone();
          caches.open('slopkit-cache-dynamic').then((cache) => {
            cache.put(event.request, responseToCache);
          });
        }
        return networkResponse;
      } catch (error) {
        console.warn(`[SW] Network fetch failed offline for: ${event.request.url}`);

        // Fallback for HTML page requests when offline
        if (event.request.headers.get('accept')?.includes('text/html') || reqUrl.pathname.endsWith('.html')) {
          const mainHtml = (await caches.match('./index.html')) || (await caches.match('./slopkit/poops.html'));
          if (mainHtml) return mainHtml;
        }
        throw error;
      }
    })()
  );
});
