// Cache names
const STATIC_CACHE = 'jamsite-static-v7';
const PDF_CACHE = 'pdf-cache';

// Files to cache on install
const STATIC_FILES = [
  '/css/normalize.css',
  '/css/skeleton.css',
  '/css/custom.css',
  '/css/menu.css',
  '/css/offline.css',
  '/js/search_data.js',
  '/js/song_table.js',
  '/js/filter.js',
  '/js/search.js',
  '/js/playlist.js',
  '/js/random.js',
  '/js/diagnostics.js',
  '/js/broadcast.js',
  '/js/song_actions.js',
  '/js/menu.js',
  '/js/offline_preferences.js',
  '/js/sync_worker.js',
  '/js/qr_code.js',
  '/js/site.js'
];

// Install event - cache static files, always skip waiting
self.addEventListener('install', event => {
  self.skipWaiting();
  event.waitUntil(
    caches.open(STATIC_CACHE)
      .then(cache => {
        console.log('Caching static files');
        return cache.addAll(STATIC_FILES.map(url => new Request(url, { cache: 'reload' })));
      })
  );
});

// Activate event - clean up old caches
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(cacheNames => {
      return Promise.all(
        cacheNames.map(cacheName => {
          if (cacheName !== STATIC_CACHE && cacheName !== PDF_CACHE) {
            console.log('Deleting old cache:', cacheName);
            return caches.delete(cacheName);
          }
        })
      );
    }).then(() => self.clients.claim())
  );
});

// Fetch event - handle requests
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);
  
  // Never cache or intercept API/SSE requests
  if (url.pathname.startsWith('/api/')) {
    return;
  }

  // Handle PDF files specially
  if (url.pathname.startsWith('/songs/') && url.pathname.endsWith('.pdf')) {
    event.respondWith(handlePdfRequest(event.request));
    return;
  }
  
  // songs.json changes on every deploy - always fetch fresh, fall back to cache
  if (url.pathname === '/songs.json') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          const responseToCache = response.clone();
          caches.open(STATIC_CACHE).then(cache => cache.put(event.request, responseToCache));
          return response;
        })
        .catch(() => caches.match(event.request))
    );
    return;
  }

  // Special handling for index.html - always try network first, but cache for offline use
  if (url.pathname === '/' || url.pathname === '/index.html') {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // Clone the response as it can only be consumed once
          const responseToCache = response.clone();
          
          // Cache the response for offline use
          caches.open(STATIC_CACHE)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });
            
          return response;
        })
        .catch(() => {
          // If network fails, try the cache
          return caches.match(event.request)
            .then(cachedResponse => {
              if (cachedResponse) {
                return cachedResponse;
              }
              
              // If no cached version exists, return a simple offline page
              return new Response(
                '<!DOCTYPE html><html><head><title>Jam Songs - Offline</title><style>body{font-family:sans-serif;text-align:center;padding:20px;}</style></head><body><h1>Jam Songs</h1><p>You are offline. Please connect to the internet to access this site.</p></body></html>',
                { headers: { 'Content-Type': 'text/html' } }
              );
            });
        })
    );
    return;
  }
  
  // For all other requests, try the cache first, then network
  event.respondWith(
    caches.match(event.request)
      .then(response => {
        // Return cached response if found
        if (response) {
          return response;
        }
        
        // Otherwise fetch from network
        return fetch(event.request).then(response => {
          // Don't cache non-GET requests or non-successful responses
          if (event.request.method !== 'GET' || !response || response.status !== 200) {
            return response;
          }
          
          // Clone the response as it can only be consumed once
          const responseToCache = response.clone();
          
          // Cache the response
          caches.open(STATIC_CACHE)
            .then(cache => {
              cache.put(event.request, responseToCache);
            });
            
          return response;
        });
      })
  );
});

// Special handler for PDF requests
async function handlePdfRequest(request) {
  const pdfCache = await caches.open(PDF_CACHE);
  // Extract UUID from both /songs/{uuid}.pdf and /songs/{uuid}/{slug}.pdf
  const pathParts = new URL(request.url).pathname.replace('/songs/', '').split('/');
  const uuid = pathParts[0].split('.')[0];
  const cachedResponse = await pdfCache.match(`/pdfs/${uuid}`);  
  if (cachedResponse) {
    // Create new response with original URL path
    return new Response(cachedResponse.body, {
        status: cachedResponse.status,
        statusText: cachedResponse.statusText,
        headers: cachedResponse.headers,
        url: request.url
    });
  }
  
  // If not in cache, try to fetch from network
  try {
    const networkResponse = await fetch(request);
    if (networkResponse.ok) {
      // We don't cache the PDF here - that's handled by the sync worker
      return networkResponse;
    }
  } catch (error) {
    console.error('Error fetching PDF from network:', error);
  }
  
  // If all else fails, return a 404
  return new Response('PDF not found', { status: 404 });
}
