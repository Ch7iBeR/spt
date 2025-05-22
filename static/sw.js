const CACHE_NAME = 'bullet-detection-v1';
const urlsToCache = [
    '/static/js/chart.min.js',
    '/static/js/chart.js',
    '/static/js/dashboard.js',
    '/static/css/style.css',
    '/static/models/best.pt'
];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME)
            .then(cache => cache.addAll(urlsToCache))
    );
});

self.addEventListener('fetch', event => {
    event.respondWith(
        caches.match(event.request)
            .then(response => response || fetch(event.request))
    );
});