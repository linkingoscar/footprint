// Service Worker for PWA
const CACHE_NAME = 'footprint-v6';
const APP_SHELL = [
    './',
    './index.html',
    './settings.html',
    './guide.html',
    './manifest.json',
    './css/base.css',
    './css/components.css',
    './css/couple.css',
    './css/map.css',
    './js/api.js',
    './js/state.js',
    './js/ui.js',
    './js/map.js',
    './js/i18n.js',
    './js/storage.js',
    './js/replay.js',
    './js/dialog.js',
    './js/quick-catch.js',
    './js/food-wheel.js',
    './js/couple-pair.js',
    './js/globe-conquest.js',
    './js/passport.js',
    './js/badges.js',
    './js/packing-list.js',
    './js/love-capsule.js',
    './js/icons.js',
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
    const scopePath = self.registration ? new URL(self.registration.scope).pathname : '/';

    // 动态判断当前作用域下的 API 及媒体上传请求，避免 SW 缓存动态业务接口与二进制媒体
    const isApi = url.pathname.includes('/api/') || url.pathname.startsWith(scopePath + 'api/');
    const isUpload = url.pathname.includes('/uploads/') || url.pathname.startsWith(scopePath + 'uploads/');

    if (isApi || isUpload || request.method !== 'GET') {
        return;
    }

    if (request.mode === 'navigate') {
        event.respondWith(
            fetch(request)
                .then(response => {
                    const copy = response.clone();
                    caches.open(CACHE_NAME).then(cache => {
                        // 准确缓存实际请求的导航目标，杜绝将 settings.html/guide.html 错写至 index.html
                        cache.put(request, copy);
                    });
                    return response;
                })
                .catch(() => caches.match(request).then(res => res || caches.match('./index.html').then(r => r || caches.match('index.html'))))
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
