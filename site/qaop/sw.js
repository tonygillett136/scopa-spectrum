// no-op service worker (Qaop registers /qaop/sw.js); intentionally empty to avoid caching
self.addEventListener("install",()=>self.skipWaiting());
self.addEventListener("activate",e=>e.waitUntil(self.clients.claim()));
