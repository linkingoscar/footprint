// Service Worker for PWA
const CACHE_NAME = 'footprint-v4';
const APP_SHELL = [
    './',
    './index.html',
    './settings.html',
    './guide.html',
    './manifest.json',
    './js/i18n.js',
    './js/storage.js',
    './js/replay.js',
    './js/dialog.js',
    './js/quick-catch.js',
    './js/food-wheel.js',
    './js/couple-pair.js',
    './js/globe-conquest.js',
    './icons/icon-192.svg',
    './icons/icon-512.svg',
    './icons/shortcut-add.svg'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(APP_SHELL))
            .then(() => self.skipWaiting())
    );
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys()
            .then(names => Promise.all(names.filter(name => name !== CACHE_NAME).map(name => caches.delete(name))))
            .then(() => self.clients.claim())
    );
});

self.addEventListener('fetch', event => {
    const request = event.request;
    const url = new URL(request.url);

    if (url.pathname.startsWith('/api/') || request.method !== 'GET') {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then(response => {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then(cache => cache.put('./index.html', copy));
                    return response;
                })
                .catch(() => caches.match('./index.html').then(res => res || caches.match('index.html')))
        );
        return;
    }

    event.respondWith(
        caches.match(request).then(cached => {
            if (cached) return cached;
            return fetch(request).then(response => {
                if (!response || response.status !== 200 || response.type !== 'basic') {
                    return response;
                }
                const copy = response.clone();
                caches.open(CACHE_NAME).then(cache => cache.put(request, copy));
                return response;
            });
        })
    );
});
