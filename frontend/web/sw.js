// BHOOMI V2 Service Worker
self.addEventListener('install', (e) => self.skipWaiting());
self.addEventListener('activate', (e) => clients.claim());
self.addEventListener('fetch', (e) => {
    if (e.request.url.includes('/api/')) return;
});
